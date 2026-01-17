from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User
from app.database import get_db
from app.utils.timezone import now_gmt8

# HTTP Bearer token - auto_error=False so we can handle errors ourselves
security = HTTPBearer(auto_error=False)

# Password hashing context - using bcrypt with automatic salt generation
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # Log error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Password verification error: {e}. Hash format may be invalid.")
        # If hash is not a valid bcrypt hash, return False
        return False

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = now_gmt8() + expires_delta
    else:
        expire = now_gmt8() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please provide a valid Authorization header with Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check if credentials were provided
    if credentials is None:
        import logging
        logger = logging.getLogger(__name__)
        auth_header = request.headers.get("Authorization")
        if auth_header:
            logger.warning(f"Authorization header present but invalid format: {auth_header[:50]}")
        else:
            logger.warning("Authorization header missing")
        raise credentials_exception
    
    try:
        token = credentials.credentials
        if not token:
            raise credentials_exception
        
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except JWTError as e:
        # Log JWT errors for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"JWT validation error: {str(e)}")
        raise credentials_exception
    except (ValueError, TypeError) as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Token parsing error: {str(e)}")
        raise credentials_exception
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise credentials_exception
    return user
