"""
User Management API Router - Admin-only user CRUD operations
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime

from core.database import get_db
from core.dependencies import require_admin, get_current_user
from api.models.base_models import User, UserRole
from api.schemas.user_schemas import (
    UserResponse, UserCreate, UserUpdate
)

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("/", response_model=List[UserResponse])
def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip N results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    List all users (Admin only).
    
    Filter options:
    - **role**: Filter by user role (admin/user/guest)
    - **is_active**: Filter by active status
    - **limit**: Max number of results
    - **offset**: Pagination offset
    """
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    users = query.offset(offset).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user by ID.
    
    - Admins can view any user
    - Regular users can only view themselves
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    # Check permissions
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user information.
    
    - Admins can update any user
    - Regular users can only update themselves (except role and is_active)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    # Check permissions
    is_admin = current_user.role == UserRole.ADMIN
    is_self = current_user.id == user_id
    
    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Apply updates
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Non-admins can't change role or active status
    if not is_admin:
        update_data.pop('is_active', None)
        # Note: role is not in UserUpdate schema, so no need to remove
    
    # Update password if provided - also ends every existing session (issue
    # #11 item 3): a stolen token surviving a password change would defeat
    # the point of changing it.
    if 'password' in update_data and update_data['password']:
        from core.security import hash_password, invalidate_sessions
        user.hashed_password = hash_password(update_data.pop('password'))
        invalidate_sessions(user)
    
    # Update other fields
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete user (Admin only).
    
    - Cannot delete yourself (admin)
    - Cascades to user's tasks, events, notes
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    db.delete(user)
    db.commit()
    return None


@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Activate user account (Admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    user.is_active = True
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Deactivate user account (Admin only).
    
    - Cannot deactivate yourself (admin)
    - Deactivated users cannot login
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400, 
            detail="Cannot deactivate your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user


@router.put("/{user_id}/role", response_model=UserResponse)
def change_user_role(
    user_id: int,
    new_role: UserRole,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Change user role (Admin only).
    
    - Cannot change your own role
    - Available roles: admin, user, guest
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400, 
            detail="Cannot change your own role"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    user.role = new_role
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user
