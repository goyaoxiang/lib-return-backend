from sqlalchemy import Column, String, DateTime, Integer, Numeric, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class ReturnTransaction(Base):
    __tablename__ = "return_transaction"
    
    return_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False, index=True)
    return_box_id = Column(Integer, ForeignKey("return_box.return_box_id", ondelete="SET NULL"), nullable=True, index=True)
    return_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(50), default='pending', nullable=False, index=True)
    processed_by = Column(Integer, ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    total_fines = Column(Numeric(10, 2), default=0.00, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="return_transactions", foreign_keys=[user_id])
    return_box = relationship("ReturnBox", back_populates="return_transactions")
    processed_by_user = relationship("User", foreign_keys=[processed_by])
    return_items = relationship("ReturnItem", back_populates="return_transaction", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processed', 'completed', 'cancelled')", name="chk_return_status"),
    )
    
    def to_dict(self):
        return {
            "id": str(self.return_id),
            "userId": str(self.user_id),
            "returnBoxId": str(self.return_box_id) if self.return_box_id else None,
            "returnDate": self.return_date.isoformat() if self.return_date else None,
            "status": self.status,
            "processedBy": str(self.processed_by) if self.processed_by else None,
            "processedAt": self.processed_at.isoformat() if self.processed_at else None,
            "totalFines": float(self.total_fines),
            "notes": self.notes,
            "items": [item.to_dict() for item in self.return_items] if self.return_items else [],
        }

class ReturnItem(Base):
    __tablename__ = "return_item"
    
    return_item_id = Column(Integer, primary_key=True, autoincrement=True)
    return_id = Column(Integer, ForeignKey("return_transaction.return_id", ondelete="CASCADE"), nullable=False, index=True)
    copy_id = Column(Integer, ForeignKey("book_copy.copy_id", ondelete="RESTRICT"), nullable=False, index=True)
    loan_id = Column(Integer, ForeignKey("loan.loan_id", ondelete="SET NULL"), nullable=True, index=True)
    condition_on_return = Column(String(50), default='good', nullable=False)
    fine_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    return_transaction = relationship("ReturnTransaction", back_populates="return_items")
    copy = relationship("BookCopy", back_populates="return_items")
    loan = relationship("Loan", back_populates="return_items")
    
    def to_dict(self):
        return {
            "id": str(self.return_item_id),
            "returnId": str(self.return_id),
            "copyId": str(self.copy_id),
            "loanId": str(self.loan_id) if self.loan_id else None,
            "conditionOnReturn": self.condition_on_return,
            "fineAmount": float(self.fine_amount),
            "notes": self.notes,
            "copy": self.copy.to_dict() if self.copy else None,
            "book": self.copy.book.to_dict() if self.copy and self.copy.book else None,
        }
