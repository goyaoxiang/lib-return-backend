from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import timedelta
from app.database import get_db
from app.models.user import User
from app.models.book import BookCopy, ReturnBox
from app.models.loan import Loan
from app.models.return_transaction import ReturnTransaction, ReturnItem
from app.services.auth import get_current_user
from app.services.mqtt_service import mqtt_service
from app.schemas.return_transaction import (
    ReturnScanRequest,
    ReturnTransactionResponse,
    ReturnProcessRequest
)
from app.utils.timezone import now_gmt8

router = APIRouter(prefix="/api/library/return", tags=["Library Returns"])

@router.post("/scan", response_model=ReturnTransactionResponse, status_code=status.HTTP_201_CREATED)
async def scan_return_books(
    request: ReturnScanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Scan books in return box and create return transaction.
    This endpoint is called when RFID reader detects books in the return box."""
    print(f"[RETURN] Return scan - User: {current_user.user_id}, EPC tags: {len(request.epc_tags)}, Return Box: {request.return_box_id}")
    
    if not request.epc_tags:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No EPC tags provided"
        )
    
    # Verify return box exists if provided
    return_box = None
    if request.return_box_id:
        return_box = db.query(ReturnBox).filter(ReturnBox.return_box_id == request.return_box_id).first()
        if not return_box:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Return box {request.return_box_id} not found"
            )
    
    # Create return transaction
    return_transaction = ReturnTransaction(
        user_id=current_user.user_id,
        return_box_id=request.return_box_id,
        status='pending',
        total_fines=0.00
    )
    db.add(return_transaction)
    db.commit()
    db.refresh(return_transaction)
    
    # Process each EPC tag
    return_date = now_gmt8()
    
    for epc_tag in request.epc_tags:
        # Find book copy by EPC
        book_copy = db.query(BookCopy).filter(BookCopy.book_epc == epc_tag).first()
        
        if not book_copy:
            print(f"[RETURN] WARNING - Book copy with EPC {epc_tag} not found in database")
            continue
        
        # Find active loan for this copy and user
        loan = db.query(Loan).filter(
            Loan.copy_id == book_copy.copy_id,
            Loan.user_id == current_user.user_id,
            Loan.status == 'active'
        ).first()
        
        # Update loan status if loan exists
        if loan:
            loan.return_date = return_date
            loan.status = 'returned'
            loan.fine_amount = 0.00  # No fine calculation
            db.commit()
        
        # Create return item
        return_item = ReturnItem(
            return_id=return_transaction.return_id,
            copy_id=book_copy.copy_id,
            loan_id=loan.loan_id if loan else None,
            condition_on_return='good',  # Default, can be updated during processing
            fine_amount=0.00  # No fine calculation
        )
        db.add(return_item)
        
        # Update book copy status
        book_copy.status = 'returned'
    
    # Update return transaction (fines remain 0.00)
    return_transaction.total_fines = 0.00
    db.commit()
    db.refresh(return_transaction)
    
    print(f"[RETURN] Return transaction {return_transaction.return_id} created - {len(request.epc_tags)} books")
    
    return ReturnTransactionResponse.model_validate(return_transaction)

@router.get("/{return_id}", response_model=ReturnTransactionResponse)
async def get_return_transaction(
    return_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get return transaction details."""
    return_transaction = db.query(ReturnTransaction).filter(
        ReturnTransaction.return_id == return_id,
        ReturnTransaction.user_id == current_user.user_id
    ).first()
    
    if not return_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return transaction not found"
        )
    
    return ReturnTransactionResponse.model_validate(return_transaction)

@router.get("/", response_model=List[ReturnTransactionResponse])
async def get_user_returns(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all return transactions for current user."""
    query = db.query(ReturnTransaction).filter(
        ReturnTransaction.user_id == current_user.user_id
    )
    
    if status_filter:
        query = query.filter(ReturnTransaction.status == status_filter)
    
    returns = query.order_by(ReturnTransaction.return_date.desc()).all()
    return [ReturnTransactionResponse.model_validate(r) for r in returns]

@router.get("/status/{return_box_id}")
async def get_return_status(
    return_box_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get current return status for a return box (for HTTP polling).
    Returns EPC tags and book information in real-time."""
    if not mqtt_service.is_running():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MQTT service is not connected"
        )
    
    status_data = mqtt_service.get_return_status(return_box_id)
    
    if status_data is None:
        # No active return session
        return {
            "return_box_id": return_box_id,
            "status": "idle",
            "epc_tags": [],
            "books": []
        }
    
    return {
        "return_box_id": return_box_id,
        "status": status_data['status'],
        "epc_tags": status_data['epc_tags'],
        "books": status_data.get('books', []),
        "timestamp": status_data['timestamp'].isoformat() if 'timestamp' in status_data else None
    }

@router.post("/{return_id}/process", response_model=ReturnTransactionResponse)
async def process_return(
    return_id: int,
    request: Optional[ReturnProcessRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process a return transaction (mark as processed/completed).
    Typically called by library staff."""
    # Check if user is librarian or admin
    if current_user.user_role not in ['librarian', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only librarians and admins can process returns"
        )
    
    return_transaction = db.query(ReturnTransaction).filter(
        ReturnTransaction.return_id == return_id
    ).first()
    
    if not return_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return transaction not found"
        )
    
    # Update return items - set book copies back to available
    for return_item in return_transaction.return_items:
        book_copy = return_item.copy
        if book_copy:
            book_copy.status = 'available'
    
    # Update return transaction
    return_transaction.status = 'completed'
    return_transaction.processed_by = current_user.user_id
    return_transaction.processed_at = now_gmt8()
    
    if request and request.notes:
        return_transaction.notes = request.notes
    
    db.commit()
    db.refresh(return_transaction)
    
    return ReturnTransactionResponse.model_validate(return_transaction)
