from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class BookBase(BaseModel):
    isbn: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None

class BookCreate(BookBase):
    pass

class BookResponse(BookBase):
    id: str
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class BookCopyBase(BaseModel):
    copy_number: int = Field(..., gt=0)
    book_epc: str = Field(..., min_length=1, max_length=100)
    status: Optional[str] = Field("available", pattern="^(available|checked_out|returned|damaged|lost)$")
    condition: Optional[str] = Field("good", pattern="^(good|fair|poor|damaged)$")
    library_id: Optional[int] = None

class BookCopyCreate(BookCopyBase):
    book_id: int

class BookCopyResponse(BookCopyBase):
    id: str
    bookId: str
    libraryId: Optional[str] = None
    book: Optional[BookResponse] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class LibraryBase(BaseModel):
    library_name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    status: Optional[str] = Field("active", pattern="^(active|inactive)$")

class LibraryCreate(LibraryBase):
    pass

class LibraryResponse(LibraryBase):
    id: str
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ReturnBoxBase(BaseModel):
    return_box_name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    library_id: Optional[int] = None
    fridge_id: Optional[int] = None
    status: Optional[str] = Field("active", pattern="^(active|maintenance|inactive)$")

class ReturnBoxCreate(ReturnBoxBase):
    pass

class ReturnBoxResponse(ReturnBoxBase):
    id: str
    libraryId: Optional[str] = None
    fridgeId: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
