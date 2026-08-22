"""
User Preferences API Router

Backs the frontend Preferences page (ai_model/language/theme/notifications/
sound_effects), plus the personalization features layered on top of chat:
custom instructions, personality preset, and memory creation opt-in/out.

Before this router existed, the frontend called GET/PUT /api/user/preferences
against a route that was never implemented - none of these settings actually
persisted.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field
from typing import Optional

from core.database import get_db
from core.dependencies import get_current_user
from api.models.base_models import User
from services.user_preferences_service import get_user_preferences, DEFAULT_PREFERENCES
from services.neo4j_service import get_neo4j_service
from liara_engine.personality import get_personality_choices, is_valid_personality

router = APIRouter(prefix="/user", tags=["User Preferences"])


class PreferencesResponse(BaseModel):
    ai_model: str
    language: str
    theme: str
    notifications: bool
    sound_effects: bool
    custom_instructions: Optional[str] = None
    personality: str
    memory_enabled: bool
    tool_memory_enabled: bool


class PreferencesUpdateRequest(BaseModel):
    ai_model: Optional[str] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    notifications: Optional[bool] = None
    sound_effects: Optional[bool] = None
    custom_instructions: Optional[str] = Field(None, max_length=4000)
    personality: Optional[str] = None
    memory_enabled: Optional[bool] = None
    tool_memory_enabled: Optional[bool] = None


@router.get("/preferences", response_model=PreferencesResponse)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_user_preferences(db, current_user.id)


@router.get("/preferences/personality-options")
def get_preferences_personality_options():
    """Available personality presets for the settings dropdown."""
    return {"options": get_personality_choices()}


@router.put("/preferences", response_model=PreferencesResponse)
def update_preferences(
    request: PreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if request.personality is not None and not is_valid_personality(request.personality):
        raise HTTPException(status_code=400, detail=f"Unbekannte Personality: {request.personality}")

    updates = request.dict(exclude_unset=True)

    existing = db.execute(
        text("SELECT id FROM user_preferences WHERE user_id = :user_id"),
        {"user_id": current_user.id}
    ).first()

    if existing:
        if updates:
            set_clause = ", ".join(f"{key} = :{key}" for key in updates)
            db.execute(
                text(f"UPDATE user_preferences SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = :user_id"),
                {**updates, "user_id": current_user.id}
            )
            db.commit()
    else:
        merged = {**DEFAULT_PREFERENCES, **updates}
        db.execute(text("""
            INSERT INTO user_preferences
                (user_id, ai_model, language, theme, notifications, sound_effects,
                 custom_instructions, personality, memory_enabled, tool_memory_enabled)
            VALUES
                (:user_id, :ai_model, :language, :theme, :notifications, :sound_effects,
                 :custom_instructions, :personality, :memory_enabled, :tool_memory_enabled)
        """), {"user_id": current_user.id, **merged})
        db.commit()

    return get_user_preferences(db, current_user.id)


@router.delete("/memories")
def delete_memories(
    confirm: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete all chat memory data: the Neo4j concept graph (Message/Concept
    nodes) and the semantic_metadata/temporal_index rows in Postgres.
    Does not touch chat_sessions/chat_messages themselves (that's the
    separate DSGVO "delete all data" action) or search history.
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required. Set confirm=true")

    try:
        db.execute(text("DELETE FROM semantic_metadata WHERE user_id = :user_id"), {"user_id": current_user.id})
        db.execute(text("DELETE FROM temporal_index WHERE user_id = :user_id"), {"user_id": current_user.id})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete memory metadata: {str(e)}")

    neo4j_deleted = 0
    try:
        neo4j = get_neo4j_service()
        neo4j_deleted = neo4j.delete_user_memory(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete graph memory: {str(e)}")

    return {"success": True, "message": "Erinnerungen wurden gelöscht", "neo4j_nodes_deleted": neo4j_deleted}
