"""
User Preferences API Router

Backs the frontend Preferences page (ai_model/language/theme/notifications/
sound_effects), plus the personalization features layered on top of chat:
custom instructions, personality preset, and memory creation opt-in/out.

Before this router existed, the frontend called GET/PUT /api/user/preferences
against a route that was never implemented - none of these settings actually
persisted.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
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
    workspace_enabled: bool


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
    workspace_enabled: Optional[bool] = None


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


# Below this many outcome-tagged replies, an average is too noisy to
# call "the personality that works best for you" - just show the raw
# number instead of highlighting it.
MIN_OUTCOME_SAMPLES = 5


@router.get("/preferences/personality-insights")
def get_preferences_personality_insights(
    current_user: User = Depends(get_current_user)
):
    """
    Insight-only: how Liara's replies have landed with this user so far
    ("Wirkung der Antwort"), based on the sentiment of the message that
    followed each reply (see chat_streaming.py's outcome-tagging).
    Broken down both by personality alone and by personality+mood pair,
    since the situation (mood) is often what actually determines whether
    a given personality lands well. Nothing reads this back to change
    Liara's behavior - it's purely for the user to look at.
    """
    neo4j = get_neo4j_service()
    try:
        effectiveness = neo4j.get_personality_effectiveness(current_user.id)
    except Exception:
        effectiveness = []

    try:
        combinations = neo4j.get_personality_mood_effectiveness(current_user.id)
    except Exception:
        combinations = []

    qualified = [e for e in effectiveness if e['sample_count'] >= MIN_OUTCOME_SAMPLES]
    best_personality = qualified[0]['personality'] if len(qualified) >= 2 else None

    # Personality+mood pairs are a narrower bucket than personality alone,
    # so naturally collect fewer samples each - same threshold, but only
    # requires one qualifying combination to surface (there's no single
    # "always active" combination to compare it against, unlike personality).
    qualified_combos = [c for c in combinations if c['sample_count'] >= MIN_OUTCOME_SAMPLES]
    best_combination = qualified_combos[0] if qualified_combos else None

    return {
        "personalities": effectiveness,
        "combinations": combinations,
        "min_samples_required": MIN_OUTCOME_SAMPLES,
        "best_personality": best_personality,
        "best_combination": best_combination
    }


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
                 custom_instructions, personality, memory_enabled, tool_memory_enabled,
                 workspace_enabled)
            VALUES
                (:user_id, :ai_model, :language, :theme, :notifications, :sound_effects,
                 :custom_instructions, :personality, :memory_enabled, :tool_memory_enabled,
                 :workspace_enabled)
        """), {"user_id": current_user.id, **merged})
        db.commit()

    return get_user_preferences(db, current_user.id)


@router.delete("/memories")
def delete_memories(
    response: Response,
    confirm: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete all chat memory data: the Neo4j concept graph (Message/Concept
    nodes) and the semantic_metadata/temporal_index rows in Postgres.
    Does not touch chat_sessions/chat_messages themselves (that's the
    separate DSGVO "delete all data" action) or search history.

    Postgres and Neo4j are separate stores with no shared transaction, so
    one can succeed while the other fails. Rather than a blanket 500 that
    would hide a real partial deletion, both outcomes are reported
    explicitly; the call is safe to retry (deleting an already-empty store
    is a no-op).
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required. Set confirm=true")

    postgres_deleted = False
    postgres_error = None
    try:
        db.execute(text("DELETE FROM semantic_metadata WHERE user_id = :user_id"), {"user_id": current_user.id})
        db.execute(text("DELETE FROM temporal_index WHERE user_id = :user_id"), {"user_id": current_user.id})
        db.commit()
        postgres_deleted = True
    except Exception as e:
        db.rollback()
        postgres_error = str(e)

    neo4j_deleted = False
    neo4j_nodes_deleted = 0
    neo4j_error = None
    try:
        neo4j = get_neo4j_service()
        neo4j_nodes_deleted = neo4j.delete_user_memory(current_user.id)
        neo4j_deleted = True
    except Exception as e:
        neo4j_error = str(e)

    complete = postgres_deleted and neo4j_deleted
    response.status_code = 200 if complete else 207

    result = {
        "success": complete,
        "complete": complete,
        "postgres_deleted": postgres_deleted,
        "neo4j_deleted": neo4j_deleted,
        "neo4j_nodes_deleted": neo4j_nodes_deleted,
        "message": "Erinnerungen wurden gelöscht" if complete else "Erinnerungen wurden nur teilweise gelöscht - bitte erneut versuchen",
    }
    if postgres_error:
        result["postgres_error"] = postgres_error
    if neo4j_error:
        result["neo4j_error"] = neo4j_error
    return result
