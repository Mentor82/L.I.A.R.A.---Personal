"""
Mood System API Router.

Endpoints für Liara's dynamisches Stimmungssystem.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from liara_engine.memory.mood_system import (
    get_mood_system,
    MoodState,
    InteractionType
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
def get_mood_status():
    """
    🌙 Hole aktuellen Mood-Status.
    
    Returns:
        Aktueller Mood, Intensity, Trait-Modifiers
    """
    mood_system = get_mood_system()
    return mood_system.get_mood_status()


@router.post("/update")
def update_mood(request: MoodUpdateRequest):
    """
    🔄 Update Mood manuell.
    
    Args:
        request: Interaktions-Typ und Intensität
        
    Returns:
        Neuer Mood-Status
    """
    mood_system = get_mood_system()
    
    new_mood = mood_system.update_mood(
        interaction_type=request.interaction_type,
        intensity=request.intensity
    )
    
    return {
        "new_mood": new_mood.value,
        "status": mood_system.get_mood_status()
    }


@router.post("/detect")
def detect_mood_from_message(request: MoodDetectRequest):
    """
    🔍 Erkenne Interaktions-Typ aus Message.
    
    Args:
        request: User-Message
        
    Returns:
        Erkannter Interaktions-Typ
    """
    mood_system = get_mood_system()
    
    interaction_type = mood_system.detect_interaction_type(request.message)
    
    return {
        "message": request.message,
        "detected_interaction": interaction_type.value,
        "current_mood": mood_system.context.current_mood.value
    }


@router.get("/modifiers")
def get_trait_modifiers():
    """
    📊 Hole aktuelle Trait-Modifiers.
    
    Returns:
        Trait-Intensitäten basierend auf Mood
    """
    mood_system = get_mood_system()
    
    return {
        "current_mood": mood_system.context.current_mood.value,
        "trait_modifiers": mood_system.get_trait_modifiers(),
        "system_prompt_modifier": mood_system.get_system_prompt_modifier()
    }


@router.post("/reset")
def reset_mood():
    """
    🔄 Reset Mood zu Neutral.
    
    Returns:
        Bestätigung
    """
    mood_system = get_mood_system()
    mood_system.reset_mood()
    
    return {
        "status": "reset",
        "mood": mood_system.get_mood_status()
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
            "playful": "Humorvoll und kreativ"
        }
    }


@router.get("/history")
def get_mood_history(limit: int = 10):
    """
    📜 Hole Mood-History (neueste zuerst).
    
    Args:
        limit: Max Anzahl Einträge (default: 10, max: 50)
        
    Returns:
        Liste von Mood-Einträgen mit Confidence
    """
    mood_system = get_mood_system()
    limit = min(limit, 50)  # Max 50
    
    return {
        "history": mood_system.get_mood_history(limit=limit),
        "total_entries": len(mood_system.mood_history)
    }

