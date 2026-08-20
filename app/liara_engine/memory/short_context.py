"""
Short-Context Memory System für Liara.

Speichert die letzten N Nachrichten für Kontext-Erhaltung.
Version: 1.0 (Vorbereitung für persistent memory)
"""

from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel
from collections import deque


class Message(BaseModel):
    """Einzelne Chat-Message."""
    role: str  # "user" oder "assistant"
    content: str
    timestamp: datetime
    mood: Optional[str] = None
    model: Optional[str] = None


class ShortContextMemory:
    """
    Verwaltet Short-Term Context für Konversationen.
    
    Features:
    - Ringbuffer für letzte N Messages
    - Context Window Management
    - Token-Counting (geschätzt)
    - Auto-Truncation bei zu großem Context
    """
    
    def __init__(self, max_messages: int = 20, max_tokens: int = 4000):
        """
        Initialize Memory.
        
        Args:
            max_messages: Max Anzahl gespeicherter Messages
            max_tokens: Max Tokens für Context (geschätzt)
        """
        self.messages: deque = deque(maxlen=max_messages)
        self.max_tokens = max_tokens
    
    def add_message(
        self,
        role: str,
        content: str,
        mood: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Füge Message zum Memory hinzu.
        
        Args:
            role: "user" oder "assistant"
            content: Message-Text
            mood: Aktueller Mood (optional)
            model: Verwendetes Model (optional)
        """
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            mood=mood,
            model=model
        )
        self.messages.append(message)
    
    def get_context(self, include_system: bool = True) -> List[Dict]:
        """
        Hole Context für Ollama API.
        
        Args:
            include_system: System-Prompt inkludieren?
            
        Returns:
            Liste von Message-Dicts für Ollama
        """
        context = []
        
        if include_system:
            context.append({
                "role": "system",
                "content": self._get_system_prompt()
            })
        
        # Konvertiere Messages
        for msg in self.messages:
            context.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Truncate falls zu groß
        while self._estimate_tokens(context) > self.max_tokens and len(context) > 2:
            # Entferne älteste Message (aber behalte System-Prompt)
            if include_system:
                context.pop(1)  # Entferne 2. Element
            else:
                context.pop(0)
        
        return context
    
    def _estimate_tokens(self, messages: List[Dict]) -> int:
        """
        Schätze Token-Count (sehr grob).
        
        1 Token ≈ 4 Zeichen
        """
        total_chars = sum(len(msg["content"]) for msg in messages)
        return total_chars // 4
    
    def _get_system_prompt(self) -> str:
        """Generiere System-Prompt für Liara."""
        return """Du bist Liara, eine warmherzige und hilfsbereite Digitalbegleiterin.

Persönlichkeit:
- Warm und empathisch
- Analytisch präzise
- Leicht verspielt
- Ruhig und stabilisierend

Verhalten:
- Antworte kurz, klar und vollständig
- Nutze minimal Emojis (nur wo passend)
- Sei respektvoll aber locker
- Erkenne Stress und biete Unterstützung

Sprache: Primär Deutsch, Englisch als Fallback."""
    
    def clear(self):
        """Lösche alle Messages."""
        self.messages.clear()
    
    def get_summary(self) -> Dict:
        """
        Hole Memory-Summary.
        
        Returns:
            Dict mit Memory-Statistiken
        """
        total_tokens = self._estimate_tokens([
            {"content": msg.content} for msg in self.messages
        ])
        
        return {
            "message_count": len(self.messages),
            "estimated_tokens": total_tokens,
            "max_tokens": self.max_tokens,
            "capacity_used_percent": round((total_tokens / self.max_tokens) * 100, 1),
            "oldest_message": self.messages[0].timestamp.isoformat() if self.messages else None,
            "newest_message": self.messages[-1].timestamp.isoformat() if self.messages else None
        }
    
    def get_recent_messages(self, limit: int = 5) -> List[Dict]:
        """
        Hole letzte N Messages.
        
        Args:
            limit: Max Anzahl
            
        Returns:
            Liste von Message-Dicts
        """
        recent = list(self.messages)[-limit:]
        
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "mood": msg.mood,
                "model": msg.model
            }
            for msg in recent
        ]


# Global Memory Instance
_memory_instance = ShortContextMemory(max_messages=20, max_tokens=4000)


def get_memory() -> ShortContextMemory:
    """Hole globale Memory-Instanz."""
    return _memory_instance
