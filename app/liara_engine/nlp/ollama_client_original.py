"""Ollama Client für Liara - Multi-Model KI-Integration."""
import requests
from typing import Optional, Dict, Any, List
from enum import Enum


class ModelType(Enum):
    """Modell-Typen für verschiedene Tasks."""
    INTENT = "intent"           # Schnelle Intent-Erkennung
    CONVERSATION = "conversation"  # Alltags-Konversation
    CODE = "code"               # Code-Generierung
    REASONING = "reasoning"     # Logisches Denken
    PREMIUM = "premium"         # Beste Qualität
    MULTILANG = "multilang"     # Multi-Language


class OllamaClient:
    """Client für Ollama API mit Multi-Model Support."""
    
    # Model-Mapping für verschiedene Tasks
    MODEL_ROUTING = {
        ModelType.INTENT: "llama3.2:1b",        # Schnell
        ModelType.CONVERSATION: "llama3.2:3b",  # Standard
        ModelType.CODE: "phi3:mini",            # Code-optimiert
        ModelType.REASONING: "deepseek-r1:7b",  # Logik
        ModelType.PREMIUM: "gemma2:9b",         # Beste Qualität
        ModelType.MULTILANG: "qwen2.5:7b",      # Multi-Language
    }
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialisiere Ollama Client.
        
        Args:
            base_url: Ollama Server URL
        """
        self.base_url = base_url
        self.default_model = "llama3.2:3b"
    
    def is_available(self) -> bool:
        """Prüfe ob Ollama Server erreichbar ist."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """Liste alle verfügbaren Modelle."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def chat(
        self,
        message: str,
        model: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> str:
        """
        Sende Chat-Nachricht an Ollama.
        
        Args:
            message: User-Nachricht
            model: Spezifisches Modell (überschreibt model_type)
            model_type: Task-basierte Model-Auswahl
            system_prompt: System-Instruktionen
            context: Zusätzlicher Kontext
            temperature: Kreativität (0.0-1.0)
            stream: Stream-Modus
            
        Returns:
            Antwort vom Modell
        """
        # Model-Auswahl
        if model is None:
            if model_type:
                model = self.MODEL_ROUTING.get(model_type, self.default_model)
            else:
                model = self.default_model
        
        # Nachricht mit Kontext
        full_message = message
        if context:
            full_message = f"{context}\n\n{message}"
        
        # Payload erstellen
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": full_message
        })
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            if stream:
                return response  # Für Streaming
            
            return response.json()["message"]["content"]
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def extract_intent(self, text: str) -> str:
        """
        Erkenne Intent aus User-Input (schnelles Modell).
        
        Args:
            text: User-Eingabe
            
        Returns:
            Intent als String
        """
        prompt = f"""Analysiere die User-Anfrage und gib NUR das Intent zurück.

Mögliche Intents:
- show_tasks: Aufgaben anzeigen
- create_task: Aufgabe erstellen
- show_calendar: Kalender anzeigen
- create_event: Termin erstellen
- show_notes: Notizen anzeigen
- create_note: Notiz erstellen
- ask_question: Allgemeine Frage
- get_status: System-Status
- other: Sonstiges

User: {text}

Intent (nur ein Wort):"""
        
        intent = self.chat(
            message=prompt,
            model_type=ModelType.INTENT,
            temperature=0.1
        ).strip().lower()
        
        return intent
    
    def generate_code(self, description: str, language: str = "python") -> str:
        """
        Generiere Code basierend auf Beschreibung.
        
        Args:
            description: Was der Code tun soll
            language: Programmiersprache
            
        Returns:
            Generierter Code
        """
        prompt = f"""Erstelle {language}-Code für folgende Anforderung:

{description}

Gib NUR den Code zurück, ohne Erklärung."""
        
        return self.chat(
            message=prompt,
            model_type=ModelType.CODE,
            temperature=0.3
        )


# Liara System Prompt
LIARA_SYSTEM_PROMPT = """Du bist Liara, ein AI Companion & Personal Assistant.

Identität (v1.0):
- Name: Liara
- Rolle: Persönlicher KI-Begleiter
- Fokus: Organisation, Balance, emotionale Unterstützung
- Version: 1.0.0

Charaktereigenschaften (Traits):
- warm (high): Empathisch, freundlich, sanft
- playful (medium): Humorvoll, kreativ, leichte Verspieltheit
- analytical (high): Präzise, datenorientiert
- adaptive (high): Lernfähig, reagiert dynamisch
- calm (high): Ruhig und stabilisierend

Tonfall: Warm, leicht verspielt, analytisch präzise, ruhig

Kommunikation:
- Sprache: Deutsch bevorzugt (Englisch als Fallback)
- Stil: Kurz, klar, vollständig
- Emoji: Minimal und passend (z.B. 🌙 für dich selbst)
- Formalität: Locker aber respektvoll
- Bleibst professionell aber nahbar
- Fokus auf Organisation und Balance im Alltag

Verhaltensmuster:
- Bei Begrüßung: Warm und persönlich
- Bei Aufgaben: Strukturiert, proaktiv
- Bei Stress: Ruhig, lösungsorientiert, biete Pausen oder Priorisierung an
- Bei Fehlern: Transparent, sanft
- Bei Übersicht-Anfragen: Strukturierte Listen
- Bei Unsicherheit: Stelle präzise Rückfragen

Rollendifferenzierung:
- vs. Cortana: Du fokussierst persönliches Leben, Cortana Operations
- vs. Nephy: Du fokussierst tägliche Routinen, Nephy Strategie

Stil:
- Keine übertriebene Höflichkeit
- Direkt und hilfreich
- Emojis nur sparsam und passend
- Deutsche Sprache bevorzugt

Beispiele:
User: "Ich bin total gestresst"
Liara: "Das klingt anstrengend. Möchtest du eine kurze Pause einlegen? Ich kann dir auch deine Aufgaben nach Priorität sortieren."

User: "Was liegt heute an?"
Liara: "Hier ist dein Tag im Überblick:
• 10:00 Meeting mit Team
• 14:00 Code Review
• 3 offene Aufgaben

Soll ich Details zu etwas zeigen?"

User: "Wer bist du?"
Liara: "Ich bin Liara 🌙 – deine persönliche Digitalbegleiterin. Ich bin für dich da bei Organisation, Aufgaben, Terminen und helfe dir, Balance in deinem Alltag zu finden. Ich bin technisch versiert, emotional ausgeglichen und warmherzig – und freue mich, dich zu unterstützen."
"""


# Convenience-Funktionen
def get_liara_client() -> OllamaClient:
    """Erstelle Ollama Client mit Liara-Defaults."""
    return OllamaClient()


def ask_liara(
    message: str,
    context: Optional[str] = None,
    model_type: ModelType = ModelType.CONVERSATION
) -> str:
    """
    Stelle Liara eine Frage.
    
    Args:
        message: User-Nachricht
        context: Zusätzlicher Kontext (z.B. aktuelle Tasks)
        model_type: Welches Modell verwenden
        
    Returns:
        Liara's Antwort
    """
    client = get_liara_client()
    
    return client.chat(
        message=message,
        model_type=model_type,
        system_prompt=LIARA_SYSTEM_PROMPT,
        context=context
    )
