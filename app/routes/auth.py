from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.config import settings
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin, UserResponse, Token
from app.services.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.user_email == user_data.user_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        user_fname=user_data.user_fname,
        user_lname=user_data.user_lname,
        user_email=user_data.user_email,
        user_password_hash=hashed_password,
        phone_number=user_data.phone_number,
        payment_status='active',
        user_role=user_data.user_role or 'student'
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(db_user.user_id)}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
        id=str(db_user.user_id),
        name=f"{db_user.user_fname} {db_user.user_lname}",
        fname=db_user.user_fname,
        lname=db_user.user_lname,
        email=db_user.user_email,
        phoneNumber=db_user.phone_number,
        paymentStatus=db_user.payment_status,
        role=db_user.user_role
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login and get access token."""
    user = db.query(User).filter(User.user_email == user_data.user_email).first()
    if not user or not verify_password(user_data.password, user.user_password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.user_id)}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
        id=str(user.user_id),
        name=f"{user.user_fname} {user.user_lname}",
        fname=user.user_fname,
        lname=user.user_lname,
        email=user.user_email,
        phoneNumber=user.phone_number,
        paymentStatus=user.payment_status,
        role=user.user_role
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return UserResponse(
        id=str(current_user.user_id),
        name=f"{current_user.user_fname} {current_user.user_lname}",
        fname=current_user.user_fname,
        lname=current_user.user_lname,
        email=current_user.user_email,
        phoneNumber=current_user.phone_number,
        paymentStatus=current_user.payment_status,
        role=current_user.user_role
    )
