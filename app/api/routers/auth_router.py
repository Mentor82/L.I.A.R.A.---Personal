"""
Authentication Router - Login, Register, User Info
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import (
    verify_password, hash_password, create_access_token, create_refresh_token,
    verify_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
)
from core.dependencies import get_current_user, require_active_user
from api.models.base_models import User, UserRole
from api.schemas.user_schemas import UserCreate, UserLogin, Token, UserResponse, RefreshTokenRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register new user
    
    - Creates new user account
    - Returns JWT token for immediate login
    - Default role: USER
    """
    # Normalize username to lowercase
    username_normalized = user_data.username.lower().strip()
    email_normalized = user_data.email.lower().strip()
    
    # Check if username exists (case-insensitive)
    existing_user = db.query(User).filter(User.username == username_normalized).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists (case-insensitive)
    existing_email = db.query(User).filter(User.email == email_normalized).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user with normalized username/email
    hashed_pw = hash_password(user_data.password)
    new_user = User(
        username=username_normalized,
        email=email_normalized,
        full_name=user_data.full_name,
        phone=user_data.phone if user_data.phone else None,
        date_of_birth=user_data.date_of_birth if user_data.date_of_birth else None,
        hashed_password=hashed_pw,
        role=UserRole.USER,  # Default role
        is_active=True,
        is_verified=False,
        privacy_accepted=user_data.privacy_accepted,
        privacy_accepted_at=datetime.utcnow() if user_data.privacy_accepted else None,
        newsletter_opt_in=user_data.newsletter_opt_in if user_data.newsletter_opt_in else False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate JWT tokens
    access_token = create_access_token(
        data={
            "user_id": new_user.id,
            "username": new_user.username,
            "role": new_user.role.value
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    refresh_token = create_refresh_token(
        data={
            "user_id": new_user.id,
            "username": new_user.username
        }
    )
    
    # Store refresh token in database
    new_user.refresh_token = refresh_token
    new_user.refresh_token_expires = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.from_orm(new_user)
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login user
    
    - Authenticates with username and password
    - Returns JWT token
    - Updates last_login timestamp
    """
    # Find user by username (case-insensitive)
    username_normalized = credentials.username.lower().strip()
    user = db.query(User).filter(User.username == username_normalized).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last_login
    user.last_login = datetime.utcnow()
    
    # Generate JWT tokens
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    refresh_token = create_refresh_token(
        data={
            "user_id": user.id,
            "username": user.username
        }
    )
    
    # Store refresh token in database
    user.refresh_token = refresh_token
    user.refresh_token_expires = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user info
    
    - Requires valid JWT token
    - Returns user details
    """
    return UserResponse.from_orm(current_user)


@router.post("/logout")
async def logout(current_user: User = Depends(require_active_user), db: Session = Depends(get_db)):
    """
    Logout user - invalidate refresh token
    
    - Clears refresh token from database
    - Client should delete tokens from storage
    """
    # Clear refresh token from database
    current_user.refresh_token = None
    current_user.refresh_token_expires = None
    db.commit()
    
    return {
        "message": "Logged out successfully",
        "username": current_user.username
    }


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    - Validates refresh token
    - Issues new access token
    - Rotates refresh token for security
    """
    # Verify refresh token
    payload = verify_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Get user from database
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify stored refresh token matches
    if user.refresh_token != request.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token mismatch - possible security issue"
        )
    
    # Check if refresh token expired
    if user.refresh_token_expires and user.refresh_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired - please login again"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Generate new tokens (token rotation)
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    new_refresh_token = create_refresh_token(
        data={
            "user_id": user.id,
            "username": user.username
        }
    )
    
    # Update refresh token in database (rotation)
    user.refresh_token = new_refresh_token
    user.refresh_token_expires = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )
