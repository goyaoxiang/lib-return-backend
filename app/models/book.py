from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Library(Base):
    __tablename__ = "library"
    
    library_id = Column(Integer, primary_key=True, autoincrement=True)
    library_name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    status = Column(String(50), default='active', nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    return_boxes = relationship("ReturnBox", back_populates="library")
    book_copies = relationship("BookCopy", back_populates="library")
    
    def to_dict(self):
        return {
            "id": str(self.library_id),
            "name": self.library_name,
            "location": self.location,
            "status": self.status,
        }

class ReturnBox(Base):
    __tablename__ = "return_box"
    
    return_box_id = Column(Integer, primary_key=True, autoincrement=True)
    return_box_name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    library_id = Column(Integer, ForeignKey("library.library_id", ondelete="SET NULL"), nullable=True)
    fridge_id = Column(Integer, nullable=True)  # Reference to ESP32 device
    status = Column(String(50), default='active', nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    library = relationship("Library", back_populates="return_boxes")
    return_transactions = relationship("ReturnTransaction", back_populates="return_box")
    
    def to_dict(self):
        return {
            "id": str(self.return_box_id),
            "name": self.return_box_name,
            "location": self.location,
            "libraryId": str(self.library_id) if self.library_id else None,
            "fridgeId": str(self.fridge_id) if self.fridge_id else None,
            "status": self.status,
        }

class Book(Base):
    __tablename__ = "book"
    
    book_id = Column(Integer, primary_key=True, autoincrement=True)
    isbn = Column(String(20), unique=True, nullable=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    publisher = Column(String(255), nullable=True)
    publication_year = Column(Integer, nullable=True)
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    copies = relationship("BookCopy", back_populates="book", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": str(self.book_id),
            "isbn": self.isbn,
            "title": self.title,
            "author": self.author,
            "publisher": self.publisher,
            "publicationYear": self.publication_year,
            "category": self.category,
            "description": self.description,
        }

class BookCopy(Base):
    __tablename__ = "book_copy"
    
    copy_id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("book.book_id", ondelete="CASCADE"), nullable=False, index=True)
    copy_number = Column(Integer, nullable=False)
    book_epc = Column(String(100), unique=True, nullable=False, index=True)  # RFID tag
    status = Column(String(50), default='available', nullable=False, index=True)
    condition = Column(String(50), default='good', nullable=False)
    library_id = Column(Integer, ForeignKey("library.library_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    book = relationship("Book", back_populates="copies")
    library = relationship("Library", back_populates="book_copies")
    loans = relationship("Loan", back_populates="copy")
    return_items = relationship("ReturnItem", back_populates="copy")
    
    def to_dict(self):
        return {
            "id": str(self.copy_id),
            "bookId": str(self.book_id),
            "copyNumber": self.copy_number,
            "epc": self.book_epc,
            "status": self.status,
            "condition": self.condition,
            "libraryId": str(self.library_id) if self.library_id else None,
            "book": self.book.to_dict() if self.book else None,
        }
