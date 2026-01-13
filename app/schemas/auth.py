from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    user_fname: str = Field(..., min_length=1, max_length=100)
    user_lname: str = Field(..., min_length=1, max_length=100)
    user_email: EmailStr
    password: str = Field(..., min_length=6)
    phone_number: Optional[str] = Field(None, max_length=20)
    user_role: Optional[str] = Field("student", pattern="^(student|librarian|admin)$")

class UserLogin(BaseModel):
    user_email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    fname: str
    lname: str
    email: str
    phoneNumber: Optional[str]
    paymentStatus: str
    role: str
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
