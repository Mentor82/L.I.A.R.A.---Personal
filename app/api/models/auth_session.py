"""
AuthSession Model - one row per issued refresh token (issue #11 items 4/5).

Replaces the single `users.refresh_token` column: login/register no longer
overwrite one shared slot, so multiple devices can hold independent,
concurrently-valid refresh sessions. Rotation happens in place on this same
row (see auth_router.refresh_access_token), which doubles as the "family" -
a refresh token presented after its session has already rotated past it is
a replay, detected by comparing against `refresh_token_hash`.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # SHA-256, not a slow password hash (issue #11 item 5) - the refresh
    # token itself is a high-entropy signed JWT, not a user-chosen secret,
    # so there's nothing here for a slow KDF to protect against; this only
    # needs to avoid storing the raw bearer token at rest.
    refresh_token_hash = Column(String(64), nullable=False)

    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, server_default=func.now())
    revoked_at = Column(DateTime, nullable=True)
