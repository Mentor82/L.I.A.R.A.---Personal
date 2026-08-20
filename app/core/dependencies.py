"""
FastAPI Dependencies for authentication and authorization
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from api.models.base_models import User, UserRole
from core.security import verify_token
from core.database import get_db

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Raises:
        HTTPException 401: Invalid or expired token
        HTTPException 404: User not found
    """
    token = credentials.credentials
    
    # Verify token
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user_id
    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


async def get_current_user_ws(
    websocket: WebSocket,
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from WebSocket connection
    Token can be in query params (?token=...) or Sec-WebSocket-Protocol header
    
    Raises:
        Exception: Invalid or expired token, user not found
    """
    # Try to get token from query params first
    token = websocket.query_params.get("token")
    
    # If not in query params, try Sec-WebSocket-Protocol header
    if not token:
        protocols = websocket.headers.get("sec-websocket-protocol", "")
        if protocols:
            # Token might be in protocol list
            token = protocols.split(",")[0].strip()
    
    if not token:
        raise Exception("No authentication token provided")
    
    # Verify token
    payload = verify_token(token)
    if payload is None:
        raise Exception("Invalid or expired token")
    
    # Extract user_id
    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise Exception("Invalid token payload")
    
    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise Exception("User not found")
    
    # Check if user is active
    if not user.is_active:
        raise Exception("Inactive user")
    
    # Check if user is admin
    if user.role != UserRole.ADMIN:
        raise Exception("Admin privileges required")
    
    return user


async def require_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Require user to be active
    
    Raises:
        HTTPException 403: User is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def require_admin(current_user: User = Depends(require_active_user)) -> User:
    """
    Require user to have ADMIN role
    
    Raises:
        HTTPException 403: User is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def require_user_or_admin(current_user: User = Depends(require_active_user)) -> User:
    """
    Require user to have USER or ADMIN role
    
    Raises:
        HTTPException 403: User is GUEST
    """
    if current_user.role == UserRole.GUEST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User or Admin privileges required"
        )
    return current_user


# Alias for backward compatibility
get_current_admin_user = require_admin
