from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ReturnScanRequest(BaseModel):
    """Request body for scanning books in return box"""
    epc_tags: List[str] = Field(..., min_items=1, description="List of RFID EPC tags from scanned books")
    return_box_id: Optional[int] = Field(None, description="ID of the return box being used")

class ReturnItemBase(BaseModel):
    copy_id: int
    condition_on_return: Optional[str] = Field("good", pattern="^(good|fair|poor|damaged)$")
    notes: Optional[str] = None

class ReturnItemResponse(BaseModel):
    id: str
    returnId: str
    copyId: str
    loanId: Optional[str] = None
    conditionOnReturn: str
    fineAmount: float
    notes: Optional[str] = None
    copy: Optional[dict] = None
    book: Optional[dict] = None
    
    class Config:
        from_attributes = True

class ReturnTransactionResponse(BaseModel):
    id: str
    userId: str
    returnBoxId: Optional[str] = None
    returnDate: datetime
    status: str
    processedBy: Optional[str] = None
    processedAt: Optional[datetime] = None
    totalFines: float
    notes: Optional[str] = None
    items: List[ReturnItemResponse] = []
    
    class Config:
        from_attributes = True

class ReturnProcessRequest(BaseModel):
    """Request to process a return transaction"""
    return_id: int
    notes: Optional[str] = None
