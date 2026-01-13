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
from app.schemas.return_transaction import (
    ReturnScanRequest,
    ReturnTransactionResponse,
    ReturnProcessRequest
)
from app.config import settings
from app.utils.timezone import now_gmt8

router = APIRouter(prefix="/api/library/return", tags=["Library Returns"])

def calculate_fine(due_date, return_date, daily_rate=0.50, max_fine=10.00):
    """Calculate fine for overdue book."""
    if not return_date or return_date <= due_date:
        return 0.00
    
    days_overdue = (return_date - due_date).days
    fine = days_overdue * daily_rate
    
    # Cap maximum fine
    if fine > max_fine:
        fine = max_fine
    
    return fine

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
    total_fines = 0.00
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
        
        # Calculate fine if loan exists and is overdue
        fine_amount = 0.00
        if loan:
            fine_amount = calculate_fine(
                loan.due_date,
                return_date,
                settings.daily_fine_rate,
                settings.max_fine_amount
            )
            
            # Update loan status
            loan.return_date = return_date
            loan.status = 'returned'
            loan.fine_amount = fine_amount
            db.commit()
        
        # Create return item
        return_item = ReturnItem(
            return_id=return_transaction.return_id,
            copy_id=book_copy.copy_id,
            loan_id=loan.loan_id if loan else None,
            condition_on_return='good',  # Default, can be updated during processing
            fine_amount=fine_amount
        )
        db.add(return_item)
        
        # Update book copy status
        book_copy.status = 'returned'
        
        total_fines += fine_amount
    
    # Update return transaction total fines
    return_transaction.total_fines = total_fines
    db.commit()
    db.refresh(return_transaction)
    
    print(f"[RETURN] Return transaction {return_transaction.return_id} created - {len(request.epc_tags)} books, Total fines: ${total_fines}")
    
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
