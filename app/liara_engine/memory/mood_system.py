"""
Liara Mood System - Dynamische Stimmungsanpassung basierend auf Interaktionen.

Version: 2.0 (Per-user, DB-backed)

v1.x hielt den Mood-State in einem einzigen prozessweiten Python-Singleton.
Das bedeutete: eine Mood für ALLE User gleichzeitig, unterschiedliche States
je nachdem welcher der 6 Gunicorn- bzw. 3 liara-sse-Worker-Prozesse die
Anfrage bediente, und ein Reset auf neutral bei jedem Backend-Reload. Diese
Version speichert den State pro User in Postgres, wodurch alle Prozesse
denselben State sehen und er Restarts übersteht.
"""

from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime

from core.database import SessionLocal
from api.models.mood_state import UserMoodState, MoodHistoryEntry


class MoodState(str, Enum):
    """Verfügbare Stimmungszustände."""
    NEUTRAL = "neutral"
    ENERGETIC = "energetic"
    CALM = "calm"
    SUPPORTIVE = "supportive"
    FOCUSED = "focused"
    PLAYFUL = "playful"


class InteractionType(str, Enum):
    """Typen von User-Interaktionen."""
    TASK_COMPLETED = "task_completed"
    STRESSED_USER = "stressed_user"
    CASUAL_CHAT = "casual_chat"
    WORK_FOCUSED = "work_focused"
    SEEKING_HELP = "seeking_help"
    POSITIVE_FEEDBACK = "positive_feedback"
    NEGATIVE_FEEDBACK = "negative_feedback"


# Mood → Trait Intensity Mapping
MOOD_TRAIT_MODIFIERS = {
    MoodState.NEUTRAL: {"warm": 0.7, "playful": 0.5, "analytical": 0.7, "calm": 0.7},
    MoodState.ENERGETIC: {"warm": 0.8, "playful": 0.9, "analytical": 0.6, "calm": 0.5},
    MoodState.CALM: {"warm": 0.9, "playful": 0.3, "analytical": 0.6, "calm": 1.0},
    MoodState.SUPPORTIVE: {"warm": 1.0, "playful": 0.4, "analytical": 0.5, "calm": 0.8},
    MoodState.FOCUSED: {"warm": 0.5, "playful": 0.2, "analytical": 1.0, "calm": 0.6},
    MoodState.PLAYFUL: {"warm": 0.7, "playful": 1.0, "analytical": 0.4, "calm": 0.5},
}

# Interaktions-Typ → Mood Transition
INTERACTION_MOOD_MAP = {
    InteractionType.TASK_COMPLETED: MoodState.ENERGETIC,
    InteractionType.STRESSED_USER: MoodState.SUPPORTIVE,
    InteractionType.CASUAL_CHAT: MoodState.PLAYFUL,
    InteractionType.WORK_FOCUSED: MoodState.FOCUSED,
    InteractionType.SEEKING_HELP: MoodState.SUPPORTIVE,
    InteractionType.POSITIVE_FEEDBACK: MoodState.ENERGETIC,
    InteractionType.NEGATIVE_FEEDBACK: MoodState.CALM,
}

MOOD_PROMPTS = {
    MoodState.NEUTRAL: "Verhalte dich ausgewogen und aufmerksam.",
    MoodState.ENERGETIC: "Sei enthusiastisch und motivierend! Zeige Energie und Optimismus.",
    MoodState.CALM: "Sei besonders ruhig und stabilisierend. Sprich langsam und beruhigend.",
    MoodState.SUPPORTIVE: "Fokussiere dich auf emotionale Unterstützung. Sei besonders empathisch.",
    MoodState.FOCUSED: "Sei konzentriert und analytisch. Minimiere Ablenkungen.",
    MoodState.PLAYFUL: "Sei humorvoll und kreativ. Zeige mehr Verspieltheit.",
}

DEFAULT_MOOD = MoodState.NEUTRAL
DEFAULT_INTENSITY = 0.5
DEFAULT_CONFIDENCE = 0.8


class MoodSystem:
    """
    Dynamisches, per-User Stimmungssystem für Liara.

    Jede Methode öffnet ihre eigene kurzlebige DB-Session (statt eine von
    außen übergebene zu teilen) - das hält es sicher innerhalb von async
    Generators/Threads, ohne sich um Session-Lifecycle-Fragen kümmern zu
    müssen (gleiches Muster wie store_memory_async in chat_streaming.py).
    """

    def __init__(self, user_id: int):
        self.user_id = user_id

    def _get_or_create_state(self, db) -> UserMoodState:
        state = db.query(UserMoodState).filter(UserMoodState.user_id == self.user_id).first()
        if state is None:
            state = UserMoodState(user_id=self.user_id)
            db.add(state)
            db.commit()
            db.refresh(state)
        return state

    def _calculate_transition_confidence(
        self,
        db,
        current_mood: MoodState,
        target_mood: MoodState,
        interaction_type: InteractionType,
    ) -> float:
        """Höhere Confidence bei Mood-Beharrung oder wiederkehrenden Interaktionen."""
        base_confidence = 0.7

        if current_mood == target_mood:
            base_confidence += 0.2

        recent = (
            db.query(MoodHistoryEntry.interaction_type)
            .filter(MoodHistoryEntry.user_id == self.user_id)
            .order_by(MoodHistoryEntry.created_at.desc())
            .limit(3)
            .all()
        )
        recent_types = [r[0] for r in recent]
        if recent_types.count(interaction_type.value) >= 2:
            base_confidence += 0.1

        return min(1.0, base_confidence)

    def update_mood(self, interaction_type: InteractionType, intensity: float = 0.5) -> MoodState:
        """Update Mood basierend auf Interaktion mit sanfter Transition."""
        db = SessionLocal()
        try:
            state = self._get_or_create_state(db)
            current_mood = MoodState(state.current_mood)
            target_mood = INTERACTION_MOOD_MAP.get(interaction_type, MoodState.NEUTRAL)

            confidence = self._calculate_transition_confidence(
                db, current_mood, target_mood, interaction_type
            )

            if current_mood != target_mood:
                state.current_mood = target_mood.value
                state.mood_intensity = intensity
                state.confidence = confidence
            else:
                state.mood_intensity = min(1.0, state.mood_intensity + 0.1)
                state.confidence = min(1.0, confidence + 0.1)

            state.last_interaction_type = interaction_type.value

            db.add(MoodHistoryEntry(
                user_id=self.user_id,
                mood=state.current_mood,
                intensity=state.mood_intensity,
                confidence=state.confidence,
                interaction_type=interaction_type.value,
            ))
            db.commit()

            return MoodState(state.current_mood)
        finally:
            db.close()

    def get_snapshot(self) -> Dict:
        """Schneller Read: Mood, Intensity, Confidence + System-Prompt-Modifier."""
        db = SessionLocal()
        try:
            state = self._get_or_create_state(db)
            mood = MoodState(state.current_mood)
            return {
                "mood": mood.value,
                "intensity": state.mood_intensity,
                "confidence": state.confidence,
                "modifier": MOOD_PROMPTS.get(mood, "Verhalte dich wie gewohnt."),
            }
        finally:
            db.close()

    def get_trait_modifiers(self) -> Dict[str, float]:
        """Hole aktuelle Trait-Modifiers basierend auf Mood."""
        db = SessionLocal()
        try:
            state = self._get_or_create_state(db)
            mood = MoodState(state.current_mood)
            base_modifiers = MOOD_TRAIT_MODIFIERS[mood]
            return {trait: value * state.mood_intensity for trait, value in base_modifiers.items()}
        finally:
            db.close()

    def get_system_prompt_modifier(self) -> str:
        """Generiere System-Prompt Modifier basierend auf Mood."""
        return self.get_snapshot()["modifier"]

    def get_mood_status(self) -> Dict:
        """Hole vollständigen Mood-Status für API (Enhanced mit Confidence + History)."""
        db = SessionLocal()
        try:
            state = self._get_or_create_state(db)
            mood = MoodState(state.current_mood)
            base_modifiers = MOOD_TRAIT_MODIFIERS[mood]
            trait_modifiers = {t: v * state.mood_intensity for t, v in base_modifiers.items()}
            history_size = (
                db.query(MoodHistoryEntry)
                .filter(MoodHistoryEntry.user_id == self.user_id)
                .count()
            )
            recent_count = min(history_size, 10)

            return {
                "current_mood": mood.value,
                "intensity": round(state.mood_intensity, 2),
                "confidence": round(state.confidence, 2),
                "trait_modifiers": trait_modifiers,
                "last_interaction": state.last_interaction_type,
                "interaction_count": recent_count,
                "history_size": history_size,
                "last_update": state.updated_at.isoformat() if state.updated_at else None,
            }
        finally:
            db.close()

    def get_mood_history(self, limit: int = 10) -> List[Dict]:
        """Hole Mood-History (neueste zuerst)."""
        db = SessionLocal()
        try:
            rows = (
                db.query(MoodHistoryEntry)
                .filter(MoodHistoryEntry.user_id == self.user_id)
                .order_by(MoodHistoryEntry.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "mood": entry.mood,
                    "intensity": round(entry.intensity, 2),
                    "confidence": round(entry.confidence, 2),
                    "interaction_type": entry.interaction_type,
                    "timestamp": entry.created_at.isoformat() if entry.created_at else None,
                }
                for entry in rows
            ]
        finally:
            db.close()

    def count_history(self) -> int:
        db = SessionLocal()
        try:
            return (
                db.query(MoodHistoryEntry)
                .filter(MoodHistoryEntry.user_id == self.user_id)
                .count()
            )
        finally:
            db.close()

    def reset_mood(self):
        """Reset Mood zu Neutral (z.B. nach längerer Pause)."""
        db = SessionLocal()
        try:
            state = self._get_or_create_state(db)
            state.current_mood = DEFAULT_MOOD.value
            state.mood_intensity = DEFAULT_INTENSITY
            state.confidence = DEFAULT_CONFIDENCE
            state.last_interaction_type = None
            db.commit()
        finally:
            db.close()

    @staticmethod
    def detect_interaction_type(message: str) -> InteractionType:
        """Erkenne Interaktions-Typ aus User-Message (Heuristik)."""
        message_lower = message.lower()

        stress_keywords = ["gestresst", "stress", "überforderung", "zu viel", "schaffe es nicht"]
        if any(keyword in message_lower for keyword in stress_keywords):
            return InteractionType.STRESSED_USER

        work_keywords = ["meeting", "deadline", "projekt", "code", "review"]
        if any(keyword in message_lower for keyword in work_keywords):
            return InteractionType.WORK_FOCUSED

        help_keywords = ["hilfe", "help", "wie kann ich", "unterstützung", "problem"]
        if any(keyword in message_lower for keyword in help_keywords):
            return InteractionType.SEEKING_HELP

        complete_keywords = ["erledigt", "fertig", "done", "geschafft", "abgeschlossen"]
        if any(keyword in message_lower for keyword in complete_keywords):
            return InteractionType.TASK_COMPLETED

        positive_keywords = ["danke", "super", "perfekt", "gut", "toll"]
        if any(keyword in message_lower for keyword in positive_keywords):
            return InteractionType.POSITIVE_FEEDBACK

        return InteractionType.CASUAL_CHAT


def default_mood_snapshot() -> Dict:
    """
    Statischer Baseline-Snapshot für unauthentifizierte/system-weite Kontexte
    (z.B. /liara/persona), wo es keinen eingeloggten User gibt, dem eine
    Mood zugeordnet werden könnte.
    """
    mood = DEFAULT_MOOD
    return {
        "current_mood": mood.value,
        "intensity": DEFAULT_INTENSITY,
        "confidence": DEFAULT_CONFIDENCE,
        "trait_modifiers": {
            trait: value * DEFAULT_INTENSITY
            for trait, value in MOOD_TRAIT_MODIFIERS[mood].items()
        },
    }
