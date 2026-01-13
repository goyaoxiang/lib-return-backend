from sqlalchemy import Column, String, DateTime, Integer, Numeric, Boolean, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Loan(Base):
    __tablename__ = "loan"
    
    loan_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False, index=True)
    copy_id = Column(Integer, ForeignKey("book_copy.copy_id", ondelete="RESTRICT"), nullable=False, index=True)
    checkout_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False, index=True)
    return_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default='active', nullable=False, index=True)
    fine_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    fine_paid = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="loans")
    copy = relationship("BookCopy", back_populates="loans")
    return_items = relationship("ReturnItem", back_populates="loan")
    
    __table_args__ = (
        CheckConstraint("status IN ('active', 'returned', 'overdue', 'lost')", name="chk_loan_status"),
    )
    
    def to_dict(self):
        return {
            "id": str(self.loan_id),
            "userId": str(self.user_id),
            "copyId": str(self.copy_id),
            "checkoutDate": self.checkout_date.isoformat() if self.checkout_date else None,
            "dueDate": self.due_date.isoformat() if self.due_date else None,
            "returnDate": self.return_date.isoformat() if self.return_date else None,
            "status": self.status,
            "fineAmount": float(self.fine_amount),
            "finePaid": self.fine_paid,
            "notes": self.notes,
            "bookCopy": self.copy.to_dict() if self.copy else None,  # Renamed from 'copy'
            "book": self.copy.book.to_dict() if self.copy and self.copy.book else None,
        }
