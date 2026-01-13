from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class LoanBase(BaseModel):
    copy_id: int
    due_date: datetime

class LoanCreate(LoanBase):
    user_id: int

class LoanResponse(BaseModel):
    id: str
    userId: str
    copyId: str
    checkoutDate: datetime
    dueDate: datetime
    returnDate: Optional[datetime] = None
    status: str
    fineAmount: float
    finePaid: bool
    notes: Optional[str] = None
    bookCopy: Optional[dict] = None  # Renamed from 'copy' to avoid shadowing BaseModel.copy()
    book: Optional[dict] = None
    
    class Config:
        from_attributes = True

class LoanUpdate(BaseModel):
    return_date: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(active|returned|overdue|lost)$")
    fine_amount: Optional[float] = None
    fine_paid: Optional[bool] = None
    notes: Optional[str] = None
