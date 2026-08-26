"""
Security utilities for JWT and password handling
"""

import hashlib
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from api.models.base_models import UserRole, User
from api.models.auth_session import AuthSession

# JWT Configuration - Load from environment. Fail closed (issue #6): no
# default fallback. A deployment that omits LIARA_SECRET_KEY, or still has
# the known development placeholder, would otherwise start successfully
# while signing every access/refresh token with a secret that's public in
# this repository - anyone could forge valid tokens, including admin ones.
_KNOWN_PLACEHOLDER = "your-secret-key-change-in-production-use-env-var"
_MIN_SECRET_LENGTH = 32  # HS256 wants at least 256 bits of key material

SECRET_KEY = os.getenv("LIARA_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "LIARA_SECRET_KEY must be configured (no default fallback) - "
        "generate one with e.g. `openssl rand -hex 32` and set it in .env"
    )
if SECRET_KEY == _KNOWN_PLACEHOLDER:
    raise RuntimeError(
        "LIARA_SECRET_KEY is still set to the known development placeholder "
        "- generate a real secret with e.g. `openssl rand -hex 32`"
    )
if len(SECRET_KEY) < _MIN_SECRET_LENGTH:
    raise RuntimeError(
        f"LIARA_SECRET_KEY is too short ({len(SECRET_KEY)} chars, need at "
        f"least {_MIN_SECRET_LENGTH}) - generate one with e.g. "
        "`openssl rand -hex 32`"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour (reduced from 7 days)
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days

# Password hashing with Argon2id (more secure than bcrypt)
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],  # Argon2 primary, bcrypt for legacy
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,  # 3 iterations
    argon2__parallelism=4  # 4 threads
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Payload data (username, user_id, role)
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[dict]:
    """
    Verify access token and check type (issue #11) - without this, a valid
    refresh token (30 days) passes generic verify_token() and authenticates
    normal requests as if it were a 60-minute access token.

    Args:
        token: Access token string

    Returns:
        Decoded payload or None if invalid/not an access token
    """
    payload = verify_token(token)
    if payload and payload.get("type") == "access":
        return payload
    return None


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token with longer expiration
    
    Args:
        data: Payload data (user_id, username)
        
    Returns:
        Encoded refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    # jti (issue #11 item 4): exp only has 1-second resolution, and every
    # other claim is identical across a rotation of the same session (same
    # user_id/username/token_version/sid) - two refresh tokens issued for
    # the same session within the same wall-clock second would otherwise be
    # byte-identical JWTs, silently defeating reuse detection in exactly
    # the fast-succession case (rapid legitimate retry, or an attacker
    # replaying right after the real client rotates) that matters most.
    to_encode.update({"exp": expire, "type": "refresh", "jti": str(uuid.uuid4())})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_refresh_token(token: str) -> Optional[dict]:
    """
    Verify refresh token and check type

    Args:
        token: Refresh token string

    Returns:
        Decoded payload or None if invalid/not refresh token
    """
    payload = verify_token(token)
    if payload and payload.get("type") == "refresh":
        return payload
    return None


def hash_refresh_token(token: str) -> str:
    """SHA-256 digest of a refresh token, for at-rest storage (issue #11 item 5)."""
    return hashlib.sha256(token.encode()).hexdigest()


def token_version_matches(payload: dict, current_version: int) -> bool:
    """
    Compares a decoded JWT's token_version claim against the user's current
    value (issue #11 items 2/3). Tokens issued before this field existed
    carry no claim at all - treated as version 0, matching the column's own
    default, so already-issued tokens keep working right after this ships
    and only a future logout/password-change (which bumps the column)
    actually revokes anything.
    """
    return payload.get("token_version", 0) == current_version


def invalidate_sessions(db: Session, user: User) -> None:
    """
    Bumps user.token_version (issue #11 items 2/3) so every access/refresh
    JWT issued before this call - each carries the token_version active at
    issuance - stops authenticating from now on, without needing a token
    blocklist. Also revokes every one of the user's AuthSession rows
    (issue #11 items 4/5) so an outstanding refresh attempt on any device
    fails immediately via its own revoked_at check rather than only via its
    token_version claim.

    This is a "log out everywhere" operation, not per-device - matches the
    logout endpoint's documented semantics and is the correct blast radius
    for a password change (a stolen token surviving its own password reset
    would defeat the point of changing it).

    Call sites: logout, password change (self-service, admin reset-via-
    token, and the reset_password.py CLI tool). Caller still owns
    db.commit().
    """
    user.token_version = (user.token_version or 0) + 1
    db.query(AuthSession).filter(
        AuthSession.user_id == user.id,
        AuthSession.revoked_at.is_(None)
    ).update({"revoked_at": datetime.utcnow()})
