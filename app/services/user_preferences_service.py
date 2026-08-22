"""
User Preferences Service

Shared read helper for app/api/routers/chat.py and chat_streaming.py, so
both system-prompt-building code paths pick up the same per-user custom
instructions, personality, and memory settings.

Deliberately does not INSERT a default row on a cache miss - this is read
on every chat message (a hot path), and the row only needs to exist once
the user actually saves preferences via PUT /user/preferences.
"""

from typing import Optional, TypedDict
from sqlalchemy.orm import Session
from sqlalchemy import text

from liara_engine.personality import DEFAULT_PERSONALITY


class UserPreferences(TypedDict):
    ai_model: str
    language: str
    theme: str
    notifications: bool
    sound_effects: bool
    custom_instructions: Optional[str]
    personality: str
    memory_enabled: bool
    tool_memory_enabled: bool


DEFAULT_PREFERENCES: UserPreferences = {
    "ai_model": "llama3.2:3b",
    "language": "de",
    "theme": "dark",
    "notifications": True,
    "sound_effects": False,
    "custom_instructions": None,
    "personality": DEFAULT_PERSONALITY,
    "memory_enabled": True,
    "tool_memory_enabled": True,
}


def get_user_preferences(db: Session, user_id: int) -> UserPreferences:
    row = db.execute(text("""
        SELECT ai_model, language, theme, notifications, sound_effects,
               custom_instructions, personality, memory_enabled, tool_memory_enabled
        FROM user_preferences
        WHERE user_id = :user_id
    """), {"user_id": user_id}).first()

    if not row:
        return dict(DEFAULT_PREFERENCES)

    return {
        "ai_model": row.ai_model,
        "language": row.language,
        "theme": row.theme,
        "notifications": row.notifications,
        "sound_effects": row.sound_effects,
        "custom_instructions": row.custom_instructions,
        "personality": row.personality,
        "memory_enabled": row.memory_enabled,
        "tool_memory_enabled": row.tool_memory_enabled,
    }
