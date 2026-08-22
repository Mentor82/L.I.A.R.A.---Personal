"""
Per-user Mood State persistence.

Replaces the old process-global in-memory MoodSystem singleton, which had
three problems: mood was shared across all users, it diverged across the
app's separate worker processes (6 gunicorn workers + 3 liara-sse workers,
each with its own process memory), and it reset to neutral on every backend
reload/restart. Storing it in Postgres fixes all three at once since the DB
is the one thing every process actually shares.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base


class UserMoodState(Base):
    """Current mood snapshot, one row per user."""
    __tablename__ = "user_mood_state"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    current_mood = Column(String(20), nullable=False, default="neutral")
    mood_intensity = Column(Float, nullable=False, default=0.5)
    confidence = Column(Float, nullable=False, default=0.8)
    last_interaction_type = Column(String(30), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MoodHistoryEntry(Base):
    """Append-only mood transition log, per user."""
    __tablename__ = "mood_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mood = Column(String(20), nullable=False)
    intensity = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    interaction_type = Column(String(30), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
