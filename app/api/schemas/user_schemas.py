"""
Pydantic Schemas für User & Authentication
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from api.models.base_models import UserRole


class UserBase(BaseModel):
    """Base User Schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)  # Pflichtfeld
    phone: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[datetime] = None
    newsletter_opt_in: Optional[bool] = False


class UserCreate(UserBase):
    """User Creation Schema"""
    password: str = Field(..., min_length=8)
    privacy_accepted: bool = Field(True)  # DSGVO Pflichtfeld


class UserUpdate(BaseModel):
    """User Update Schema"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """User Response Schema"""
    id: int
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Login Request Schema"""
    username: str
    password: str


class Token(BaseModel):
    """JWT Token Response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh Token Request"""
    refresh_token: str


class TokenData(BaseModel):
    """JWT Token Payload"""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[UserRole] = None
