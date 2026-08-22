"""
Mood System API Router.

Endpoints für Liara's dynamisches Stimmungssystem (pro User, DB-backed).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from core.dependencies import require_active_user
from api.models.base_models import User
from liara_engine.memory.mood_system import (
    MoodSystem,
    MoodState,
    InteractionType,
)


router = APIRouter(prefix="/mood", tags=["Mood System"])


class MoodUpdateRequest(BaseModel):
    """Request für manuelle Mood-Updates."""
    interaction_type: InteractionType
    intensity: Optional[float] = 0.5


class MoodDetectRequest(BaseModel):
    """Request für Mood-Detection aus Message."""
    message: str


@router.get("/status")
def get_mood_status(current_user: User = Depends(require_active_user)):
    """
    🌙 Hole aktuellen Mood-Status des eingeloggten Users.

    Returns:
        Aktueller Mood, Intensity, Trait-Modifiers
    """
    mood_system = MoodSystem(current_user.id)
    return mood_system.get_mood_status()


@router.post("/update")
def update_mood(
    request: MoodUpdateRequest,
    current_user: User = Depends(require_active_user),
):
    """
    🔄 Update Mood manuell.

    Args:
        request: Interaktions-Typ und Intensität

    Returns:
        Neuer Mood-Status
    """
    mood_system = MoodSystem(current_user.id)

    new_mood = mood_system.update_mood(
        interaction_type=request.interaction_type,
        intensity=request.intensity,
    )

    return {
        "new_mood": new_mood.value,
        "status": mood_system.get_mood_status(),
    }


@router.post("/detect")
def detect_mood_from_message(
    request: MoodDetectRequest,
    current_user: User = Depends(require_active_user),
):
    """
    🔍 Erkenne Interaktions-Typ aus Message.

    Args:
        request: User-Message

    Returns:
        Erkannter Interaktions-Typ
    """
    interaction_type = MoodSystem.detect_interaction_type(request.message)
    mood_system = MoodSystem(current_user.id)
    snapshot = mood_system.get_snapshot()

    return {
        "message": request.message,
        "detected_interaction": interaction_type.value,
        "current_mood": snapshot["mood"],
    }


@router.get("/modifiers")
def get_trait_modifiers(current_user: User = Depends(require_active_user)):
    """
    📊 Hole aktuelle Trait-Modifiers.

    Returns:
        Trait-Intensitäten basierend auf Mood
    """
    mood_system = MoodSystem(current_user.id)
    snapshot = mood_system.get_snapshot()

    return {
        "current_mood": snapshot["mood"],
        "trait_modifiers": mood_system.get_trait_modifiers(),
        "system_prompt_modifier": snapshot["modifier"],
    }


@router.post("/reset")
def reset_mood(current_user: User = Depends(require_active_user)):
    """
    🔄 Reset Mood zu Neutral.

    Returns:
        Bestätigung
    """
    mood_system = MoodSystem(current_user.id)
    mood_system.reset_mood()

    return {
        "status": "reset",
        "mood": mood_system.get_mood_status(),
    }


@router.get("/states")
def list_mood_states():
    """
    📋 Liste alle verfügbaren Mood-States.

    Returns:
        Verfügbare Moods und Interaktions-Typen
    """
    return {
        "available_moods": [state.value for state in MoodState],
        "interaction_types": [itype.value for itype in InteractionType],
        "mood_descriptions": {
            "neutral": "Ausgewogen und aufmerksam",
            "energetic": "Enthusiastisch und motivierend",
            "calm": "Ruhig und stabilisierend",
            "supportive": "Emotional unterstützend",
            "focused": "Konzentriert und analytisch",
            "playful": "Humorvoll und kreativ",
        },
    }


@router.get("/history")
def get_mood_history(
    limit: int = 10,
    current_user: User = Depends(require_active_user),
):
    """
    📜 Hole Mood-History (neueste zuerst).

    Args:
        limit: Max Anzahl Einträge (default: 10, max: 50)

    Returns:
        Liste von Mood-Einträgen mit Confidence
    """
    limit = min(limit, 50)  # Max 50
    mood_system = MoodSystem(current_user.id)

    return {
        "history": mood_system.get_mood_history(limit=limit),
        "total_entries": mood_system.count_history(),
    }
