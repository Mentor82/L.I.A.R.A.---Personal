"""
Authentication Router - Login, Register, User Info
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import (
    verify_password, hash_password, create_access_token, create_refresh_token,
    verify_refresh_token, token_version_matches, invalidate_sessions,
    hash_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
)
from core.dependencies import get_current_user, require_active_user
from api.models.base_models import User, UserRole
from api.models.auth_session import AuthSession
from api.schemas.user_schemas import UserCreate, UserLogin, Token, UserResponse, RefreshTokenRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _issue_new_session(db: Session, user: User) -> tuple[str, str]:
    """
    Creates a new AuthSession row plus a matching access+refresh token pair
    (issue #11 items 4/5). Each call is an independent device session - unlike
    the old single `user.refresh_token` column, this never overwrites another
    device's still-valid session. The refresh token embeds the new session's
    `sid` so /refresh can look the row up directly instead of scanning by hash.
    """
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash="",  # placeholder until the token below exists
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    db.flush()  # populates session.id without committing yet

    access_token = create_access_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value,
            "token_version": user.token_version,
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "token_version": user.token_version,
            "sid": session.id,
        }
    )
    session.refresh_token_hash = hash_refresh_token(refresh_token)
    db.commit()
    return access_token, refresh_token


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

    access_token, refresh_token = _issue_new_session(db, new_user)

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

    access_token, refresh_token = _issue_new_session(db, user)

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
    Logout user - invalidate refresh token AND every already-issued access
    token (issue #11 item 2).

    Previously this only cleared the stored refresh token, so future
    /auth/refresh calls failed but any access JWT issued before logout kept
    authenticating normally until its own 60-minute expiry. Bumping
    token_version (see core.security.invalidate_sessions) makes logout
    actually end the session immediately, not just block its renewal.

    This ends every device's session, not just the caller's (issue #11
    items 4/5) - invalidate_sessions() revokes every AuthSession row for
    the user, matching the already-documented "log out everywhere" scope
    of the token_version bump it performs alongside.
    """
    invalidate_sessions(db, current_user)
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

    Each refresh token is tied to one AuthSession row (issue #11 items 4/5),
    identified by the token's `sid` claim, rotated in place on every use.
    A token that doesn't match its session's current hash means that
    session already rotated past it - i.e. this exact token was already
    used once before. That's either the legitimate client retrying a stale
    copy after a dropped response, or a stolen token being replayed after
    the real client already rotated past it - either way we can't tell
    which, so the session is revoked outright rather than silently
    accepted or just rejected with a generic mismatch.
    """
    payload = verify_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    session_id = payload.get("sid")
    user_id = payload.get("user_id")
    if session_id is None or user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload"
        )

    session = db.query(AuthSession).filter(
        AuthSession.id == session_id,
        AuthSession.user_id == user_id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh session not found"
        )

    if session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked (session invalidated)"
        )

    if session.expires_at < datetime.utcnow():
        session.revoked_at = datetime.utcnow()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired - please login again"
        )

    if hash_refresh_token(request.refresh_token) != session.refresh_token_hash:
        session.revoked_at = datetime.utcnow()
        db.commit()
        logger.warning(
            f"Refresh token reuse detected for session {session.id} "
            f"(user {user_id}) - session revoked"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token already used - session revoked, please login again"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Belt-and-suspenders alongside the session checks above (issue #11
    # items 2/3): covers logout/password-change, which bump token_version
    # instead of (only) revoking sessions individually.
    if not token_version_matches(payload, user.token_version):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked (session invalidated)"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Generate new tokens (token rotation) - same session row/id, new hash
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value,
            "token_version": user.token_version
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    new_refresh_token = create_refresh_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "token_version": user.token_version,
            "sid": session.id,
        }
    )

    session.refresh_token_hash = hash_refresh_token(new_refresh_token)
    session.expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    session.last_used_at = datetime.utcnow()
    db.commit()

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )
