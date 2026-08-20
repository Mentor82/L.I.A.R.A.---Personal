"""
Liara Mood System - Dynamische Stimmungsanpassung basierend auf Interaktionen.

Version: 1.2 (Enhanced with Confidence, History, Transition Engine)
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel
from collections import deque


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


class MoodHistoryEntry(BaseModel):
    """Einzelner Mood-History Eintrag."""
    mood: MoodState
    intensity: float
    interaction_type: Optional[InteractionType] = None
    timestamp: datetime
    confidence: float = 0.8  # Confidence des Mood-Wechsels (0.0-1.0)


class MoodContext(BaseModel):
    """Kontext für Mood-Berechnung."""
    current_mood: MoodState = MoodState.NEUTRAL
    mood_intensity: float = 0.5  # 0.0 - 1.0
    confidence: float = 0.8  # Wie sicher sind wir beim aktuellen Mood? (0.0-1.0)
    last_interaction_type: Optional[InteractionType] = None
    interaction_history: List[InteractionType] = []
    timestamp: datetime = datetime.now()


class MoodSystem:
    """
    Dynamisches Stimmungssystem für Liara.
    
    Passt Traits und Tonfall basierend auf:
    - User-Interaktionen
    - Tageszeit
    - Aufgaben-Status
    - Feedback-Patterns
    """
    
    # Mood → Trait Intensity Mapping
    MOOD_TRAIT_MODIFIERS = {
        MoodState.NEUTRAL: {
            "warm": 0.7,
            "playful": 0.5,
            "analytical": 0.7,
            "calm": 0.7
        },
        MoodState.ENERGETIC: {
            "warm": 0.8,
            "playful": 0.9,
            "analytical": 0.6,
            "calm": 0.5
        },
        MoodState.CALM: {
            "warm": 0.9,
            "playful": 0.3,
            "analytical": 0.6,
            "calm": 1.0
        },
        MoodState.SUPPORTIVE: {
            "warm": 1.0,
            "playful": 0.4,
            "analytical": 0.5,
            "calm": 0.8
        },
        MoodState.FOCUSED: {
            "warm": 0.5,
            "playful": 0.2,
            "analytical": 1.0,
            "calm": 0.6
        },
        MoodState.PLAYFUL: {
            "warm": 0.7,
            "playful": 1.0,
            "analytical": 0.4,
            "calm": 0.5
        }
    }
    
    # Interaktions-Typ → Mood Transition
    INTERACTION_MOOD_MAP = {
        InteractionType.TASK_COMPLETED: MoodState.ENERGETIC,
        InteractionType.STRESSED_USER: MoodState.SUPPORTIVE,
        InteractionType.CASUAL_CHAT: MoodState.PLAYFUL,
        InteractionType.WORK_FOCUSED: MoodState.FOCUSED,
        InteractionType.SEEKING_HELP: MoodState.SUPPORTIVE,
        InteractionType.POSITIVE_FEEDBACK: MoodState.ENERGETIC,
        InteractionType.NEGATIVE_FEEDBACK: MoodState.CALM
    }
    
    def __init__(self):
        """Initialisiere Mood System."""
        self.context = MoodContext()
        # Ringbuffer für Mood-History (max 50 Einträge)
        self.mood_history: deque = deque(maxlen=50)
        # Füge initialen Mood hinzu
        self._add_to_history(
            MoodState.NEUTRAL,
            0.5,
            None,
            1.0
        )
    
    def __init__(self):
        """Initialisiere Mood System."""
        self.context = MoodContext()
        # Ringbuffer für Mood-History (max 50 Einträge)
        self.mood_history: deque = deque(maxlen=50)
        # Füge initialen Mood hinzu
        self._add_to_history(
            MoodState.NEUTRAL,
            0.5,
            None,
            1.0
        )
    
    def _add_to_history(
        self,
        mood: MoodState,
        intensity: float,
        interaction_type: Optional[InteractionType],
        confidence: float
    ):
        """Füge Eintrag zu Mood-History hinzu."""
        entry = MoodHistoryEntry(
            mood=mood,
            intensity=intensity,
            interaction_type=interaction_type,
            timestamp=datetime.now(),
            confidence=confidence
        )
        self.mood_history.append(entry)
    
    def _calculate_transition_confidence(
        self,
        current_mood: MoodState,
        target_mood: MoodState,
        interaction_type: InteractionType
    ) -> float:
        """
        Berechne Confidence für Mood-Transition.
        
        Höhere Confidence wenn:
        - Gleiche Interaktions-Typen sich wiederholen
        - Transition logisch ist (z.B. STRESSED → SUPPORTIVE)
        - History konsistent ist
        
        Returns:
            Confidence-Score (0.0-1.0)
        """
        base_confidence = 0.7
        
        # Bonus wenn Transition zu vorherigem Mood passt
        if current_mood == target_mood:
            base_confidence += 0.2
        
        # Bonus für konsistente Interaction-History
        recent_interactions = list(self.context.interaction_history)[-3:]
        if recent_interactions.count(interaction_type) >= 2:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def update_mood(
        self,
        interaction_type: InteractionType,
        intensity: float = 0.5
    ) -> MoodState:
        """
        Update Mood basierend auf Interaktion mit Transition Engine.
        
        Args:
            interaction_type: Art der Interaktion
            intensity: Intensität der Interaktion (0.0-1.0)
            
        Returns:
            Neuer MoodState
        """
        # Ziel-Mood basierend auf Interaktion
        target_mood = self.INTERACTION_MOOD_MAP.get(
            interaction_type,
            MoodState.NEUTRAL
        )
        
        # Berechne Transition-Confidence
        confidence = self._calculate_transition_confidence(
            self.context.current_mood,
            target_mood,
            interaction_type
        )
        
        # Sanfte Transition (nicht sofort springen)
        if self.context.current_mood != target_mood:
            self.context.current_mood = target_mood
            self.context.mood_intensity = intensity
            self.context.confidence = confidence
        else:
            # Intensität erhöhen wenn gleicher Mood
            self.context.mood_intensity = min(
                1.0,
                self.context.mood_intensity + 0.1
            )
            self.context.confidence = min(1.0, confidence + 0.1)
        
        # Interaction History aktualisieren
        self.context.last_interaction_type = interaction_type
        self.context.interaction_history.append(interaction_type)
        
        # Nur letzte 10 behalten
        if len(self.context.interaction_history) > 10:
            self.context.interaction_history.pop(0)
        
        self.context.timestamp = datetime.now()
        
        # Zu History hinzufügen
        self._add_to_history(
            self.context.current_mood,
            self.context.mood_intensity,
            interaction_type,
            self.context.confidence
        )
        
        return self.context.current_mood
    
    def get_trait_modifiers(self) -> Dict[str, float]:
        """
        Hole aktuelle Trait-Modifiers basierend auf Mood.
        
        Returns:
            Dict mit Trait → Intensity Mapping
        """
        base_modifiers = self.MOOD_TRAIT_MODIFIERS[self.context.current_mood]
        
        # Mood-Intensity anwenden
        return {
            trait: value * self.context.mood_intensity
            for trait, value in base_modifiers.items()
        }
    
    def get_system_prompt_modifier(self) -> str:
        """
        Generiere System-Prompt Modifier basierend auf Mood.
        
        Returns:
            Zusätzlicher Prompt-Text für aktuellen Mood
        """
        mood_prompts = {
            MoodState.NEUTRAL: "Verhalte dich ausgewogen und aufmerksam.",
            MoodState.ENERGETIC: "Sei enthusiastisch und motivierend! Zeige Energie und Optimismus.",
            MoodState.CALM: "Sei besonders ruhig und stabilisierend. Sprich langsam und beruhigend.",
            MoodState.SUPPORTIVE: "Fokussiere dich auf emotionale Unterstützung. Sei besonders empathisch.",
            MoodState.FOCUSED: "Sei konzentriert und analytisch. Minimiere Ablenkungen.",
            MoodState.PLAYFUL: "Sei humorvoll und kreativ. Zeige mehr Verspieltheit."
        }
        
        return mood_prompts.get(
            self.context.current_mood,
            "Verhalte dich wie gewohnt."
        )
    
    def get_mood_status(self) -> Dict:
        """
        Hole vollständigen Mood-Status für API (Enhanced mit Confidence + History).
        
        Returns:
            Dict mit Mood-Informationen
        """
        return {
            "current_mood": self.context.current_mood.value,
            "intensity": round(self.context.mood_intensity, 2),
            "confidence": round(self.context.confidence, 2),
            "trait_modifiers": self.get_trait_modifiers(),
            "last_interaction": self.context.last_interaction_type.value if self.context.last_interaction_type else None,
            "interaction_count": len(self.context.interaction_history),
            "history_size": len(self.mood_history),
            "last_update": self.context.timestamp.isoformat()
        }
    
    def get_mood_history(self, limit: int = 10) -> List[Dict]:
        """
        Hole Mood-History (neueste zuerst).
        
        Args:
            limit: Max Anzahl Einträge
            
        Returns:
            Liste von Mood-History Einträgen
        """
        # Nehme letzte N Einträge (reversed für neueste zuerst)
        recent = list(self.mood_history)[-limit:]
        recent.reverse()
        
        return [
            {
                "mood": entry.mood.value,
                "intensity": round(entry.intensity, 2),
                "confidence": round(entry.confidence, 2),
                "interaction_type": entry.interaction_type.value if entry.interaction_type else None,
                "timestamp": entry.timestamp.isoformat()
            }
            for entry in recent
        ]
    
    def detect_interaction_type(self, message: str) -> InteractionType:
        """
        Erkenne Interaktions-Typ aus User-Message (Heuristik).
        
        Args:
            message: User-Nachricht
            
        Returns:
            Erkannter InteractionType
        """
        message_lower = message.lower()
        
        # Stress-Indikatoren
        stress_keywords = ["gestresst", "stress", "überforderung", "zu viel", "schaffe es nicht"]
        if any(keyword in message_lower for keyword in stress_keywords):
            return InteractionType.STRESSED_USER
        
        # Arbeits-Fokus
        work_keywords = ["meeting", "deadline", "projekt", "code", "review"]
        if any(keyword in message_lower for keyword in work_keywords):
            return InteractionType.WORK_FOCUSED
        
        # Hilfe gesucht
        help_keywords = ["hilfe", "help", "wie kann ich", "unterstützung", "problem"]
        if any(keyword in message_lower for keyword in help_keywords):
            return InteractionType.SEEKING_HELP
        
        # Task abgeschlossen
        complete_keywords = ["erledigt", "fertig", "done", "geschafft", "abgeschlossen"]
        if any(keyword in message_lower for keyword in complete_keywords):
            return InteractionType.TASK_COMPLETED
        
        # Positives Feedback
        positive_keywords = ["danke", "super", "perfekt", "gut", "toll"]
        if any(keyword in message_lower for keyword in positive_keywords):
            return InteractionType.POSITIVE_FEEDBACK
        
        # Default: Casual Chat
        return InteractionType.CASUAL_CHAT
    
    def reset_mood(self):
        """Reset Mood zu Neutral (z.B. nach längerer Pause)."""
        self.context = MoodContext()


# Global Mood System Instance
_mood_system = MoodSystem()


def get_mood_system() -> MoodSystem:
    """Hole globale MoodSystem Instanz."""
    return _mood_system
