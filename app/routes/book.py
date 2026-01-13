from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_
from app.database import get_db
from app.models.book import Book, BookCopy, Library, ReturnBox
from app.services.auth import get_current_user
from app.schemas.book import (
    BookResponse, BookCreate,
    BookCopyResponse, BookCopyCreate,
    LibraryResponse, LibraryCreate,
    ReturnBoxResponse, ReturnBoxCreate
)

router = APIRouter(prefix="/api/library", tags=["Library Books"])

# Book endpoints
@router.get("/books", response_model=List[BookResponse])
async def get_books(
    search: Optional[str] = Query(None, description="Search by title, author, or ISBN"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """Get list of books with optional search and filter."""
    query = db.query(Book)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Book.title.ilike(search_term),
                Book.author.ilike(search_term),
                Book.isbn.ilike(search_term)
            )
        )
    
    if category:
        query = query.filter(Book.category == category)
    
    books = query.order_by(Book.title).all()
    return [BookResponse.from_orm(book) for book in books]

@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: Session = Depends(get_db)):
    """Get book details by ID."""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    return BookResponse.from_orm(book)

@router.get("/books/{book_id}/copies", response_model=List[BookCopyResponse])
async def get_book_copies(book_id: int, db: Session = Depends(get_db)):
    """Get all copies of a book."""
    copies = db.query(BookCopy).filter(
        BookCopy.book_id == book_id
    ).order_by(BookCopy.copy_number).all()
    return [BookCopyResponse.from_orm(copy) for copy in copies]

# Book Copy endpoints
@router.get("/copies/by-epc/{epc}", response_model=BookCopyResponse)
async def get_copy_by_epc(epc: str, db: Session = Depends(get_db)):
    """Get book copy by RFID EPC tag."""
    copy = db.query(BookCopy).filter(BookCopy.book_epc == epc).first()
    if not copy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book copy not found"
        )
    return BookCopyResponse.from_orm(copy)

# Return Box endpoints
@router.get("/return-boxes", response_model=List[ReturnBoxResponse])
async def get_return_boxes(
    library_id: Optional[int] = Query(None, description="Filter by library"),
    db: Session = Depends(get_db)
):
    """Get list of return boxes."""
    query = db.query(ReturnBox).filter(ReturnBox.status == 'active')
    
    if library_id:
        query = query.filter(ReturnBox.library_id == library_id)
    
    boxes = query.all()
    return [ReturnBoxResponse.from_orm(box) for box in boxes]

@router.get("/return-boxes/{return_box_id}", response_model=ReturnBoxResponse)
async def get_return_box(return_box_id: int, db: Session = Depends(get_db)):
    """Get return box details."""
    box = db.query(ReturnBox).filter(ReturnBox.return_box_id == return_box_id).first()
    if not box:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return box not found"
        )
    return ReturnBoxResponse.from_orm(box)
