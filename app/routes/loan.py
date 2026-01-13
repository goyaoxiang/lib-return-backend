from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import timedelta
from app.database import get_db
from app.models.user import User
from app.models.book import BookCopy
from app.models.loan import Loan
from app.services.auth import get_current_user
from app.schemas.loan import LoanResponse, LoanCreate, LoanUpdate
from app.config import settings
from app.utils.timezone import now_gmt8

router = APIRouter(prefix="/api/library/loans", tags=["Library Loans"])

@router.get("/active", response_model=List[LoanResponse])
async def get_active_loans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all active loans for current user."""
    loans = db.query(Loan).filter(
        Loan.user_id == current_user.user_id,
        Loan.status == 'active'
    ).order_by(Loan.due_date.asc()).all()
    
    return [LoanResponse.model_validate(loan) for loan in loans]

@router.get("/history", response_model=List[LoanResponse])
async def get_loan_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get loan history for current user."""
    loans = db.query(Loan).filter(
        Loan.user_id == current_user.user_id
    ).order_by(Loan.checkout_date.desc()).all()
    
    return [LoanResponse.model_validate(loan) for loan in loans]

@router.get("/overdue", response_model=List[LoanResponse])
async def get_overdue_loans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get overdue loans for current user."""
    current_date = now_gmt8()
    loans = db.query(Loan).filter(
        Loan.user_id == current_user.user_id,
        Loan.status == 'active',
        Loan.due_date < current_date
    ).order_by(Loan.due_date.asc()).all()
    
    # Update status to overdue
    for loan in loans:
        if loan.status != 'overdue':
            loan.status = 'overdue'
    
    db.commit()
    
    return [LoanResponse.model_validate(loan) for loan in loans]

@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific loan details."""
    loan = db.query(Loan).filter(
        Loan.loan_id == loan_id,
        Loan.user_id == current_user.user_id
    ).first()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )
    
    return LoanResponse.model_validate(loan)

@router.post("/", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def create_loan(
    loan_data: LoanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new loan (checkout a book).
    Typically called by library staff or automated system."""
    # Check if user is librarian/admin or if it's self-checkout
    if loan_data.user_id != current_user.user_id and current_user.user_role not in ['librarian', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only librarians and admins can create loans for other users"
        )
    
    # Verify book copy exists and is available
    book_copy = db.query(BookCopy).filter(BookCopy.copy_id == loan_data.copy_id).first()
    if not book_copy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book copy not found"
        )
    
    if book_copy.status != 'available':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Book copy is not available (status: {book_copy.status})"
        )
    
    # Check if user already has this book checked out
    existing_loan = db.query(Loan).filter(
        Loan.user_id == loan_data.user_id,
        Loan.copy_id == loan_data.copy_id,
        Loan.status == 'active'
    ).first()
    
    if existing_loan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has this book checked out"
        )
    
    # Create loan
    loan = Loan(
        user_id=loan_data.user_id,
        copy_id=loan_data.copy_id,
        checkout_date=now_gmt8(),
        due_date=loan_data.due_date,
        status='active',
        fine_amount=0.00
    )
    
    # Update book copy status
    book_copy.status = 'checked_out'
    
    db.add(loan)
    db.commit()
    db.refresh(loan)
    
    return LoanResponse.model_validate(loan)
