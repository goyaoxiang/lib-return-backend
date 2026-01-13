from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "user"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    user_fname = Column(String(100), nullable=False)
    user_lname = Column(String(100), nullable=False)
    user_email = Column(String(255), unique=True, nullable=False, index=True)
    user_password_hash = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)
    payment_status = Column(String(50), default='active', nullable=False)
    user_role = Column(String(50), default='student', nullable=False)  # student, librarian, admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    loans = relationship("Loan", back_populates="user", cascade="all, delete-orphan")
    return_transactions = relationship("ReturnTransaction", back_populates="user", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": str(self.user_id),
            "name": f"{self.user_fname} {self.user_lname}",
            "fname": self.user_fname,
            "lname": self.user_lname,
            "email": self.user_email,
            "phoneNumber": self.phone_number,
            "paymentStatus": self.payment_status,
            "role": self.user_role,
        }
