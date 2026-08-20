"""Model Router - Intelligente Model-Auswahl für verschiedene Tasks."""
from typing import Dict, Optional
from liara_engine.nlp.ollama_client import ModelType


class ModelRouter:
    """Intelligente Model-Auswahl basierend auf Task und Kontext."""
    
    # Task-Keywords für automatische Erkennung
    TASK_KEYWORDS = {
        ModelType.CODE: [
            "code", "python", "javascript", "programmier", "funktion",
            "class", "api", "route", "fastapi", "react", "bug", "fehler"
        ],
        ModelType.REASONING: [
            "warum", "wieso", "erkläre", "analyse", "vergleich",
            "unterschied", "logik", "berechne", "optimiere"
        ],
        ModelType.MULTILANG: [
            "übersetze", "translate", "english", "französisch",
            "spanisch", "italienisch"
        ],
        ModelType.INTENT: [
            "schnell", "kurz", "ja", "nein", "check", "status"
        ]
    }
    
    @staticmethod
    def detect_task_type(message: str) -> ModelType:
        """
        Erkenne Task-Typ aus User-Nachricht.
        
        Args:
            message: User-Input
            
        Returns:
            Passender ModelType
        """
        message_lower = message.lower()
        
        # Prüfe Keywords
        for model_type, keywords in ModelRouter.TASK_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                return model_type
        
        # Default: Konversation
        return ModelType.CONVERSATION
    
    @staticmethod
    def get_best_model(
        message: str,
        user_preference: Optional[str] = None,
        context_length: int = 0
    ) -> str:
        """
        Wähle bestes Modell basierend auf mehreren Faktoren.
        
        Args:
            message: User-Nachricht
            user_preference: User hat spezifisches Modell gewählt
            context_length: Länge des Kontexts (für RAM-Management)
            
        Returns:
            Model-Name
        """
        # User-Präferenz hat Priorität
        if user_preference:
            return user_preference
        
        # Erkenne Task-Typ
        task_type = ModelRouter.detect_task_type(message)
        
        # Bei langem Kontext: kleineres Modell
        if context_length > 5000:
            if task_type == ModelType.CONVERSATION:
                return "llama3.2:3b"  # Statt größeres Modell
        
        # Standard-Routing
        from liara_engine.nlp.ollama_client import OllamaClient
        return OllamaClient.MODEL_ROUTING.get(
            task_type,
            "llama3.2:3b"  # Fallback
        )
    
    @staticmethod
    def get_model_info() -> Dict[str, Dict]:
        """
        Gibt Info über alle verfügbaren Modelle zurück.
        
        Returns:
            Dict mit Model-Infos
        """
        return {
            "llama3.2:1b": {
                "size": "1.3 GB",
                "ram": "2-3 GB",
                "speed": "⚡⚡⚡",
                "use_case": "Schnelle Intent-Erkennung"
            },
            "llama3.2:3b": {
                "size": "2.0 GB",
                "ram": "4-5 GB",
                "speed": "⚡⚡",
                "use_case": "Standard Konversation"
            },
            "phi3:mini": {
                "size": "2.2 GB",
                "ram": "4 GB",
                "speed": "⚡⚡",
                "use_case": "Code-Generierung"
            },
            "qwen2.5:7b": {
                "size": "4.7 GB",
                "ram": "8 GB",
                "speed": "⚡",
                "use_case": "Multi-Language Support"
            },
            "mistral:7b": {
                "size": "4.4 GB",
                "ram": "8 GB",
                "speed": "⚡",
                "use_case": "Hochwertige Texte"
            },
            "deepseek-r1:7b": {
                "size": "4.7 GB",
                "ram": "8 GB",
                "speed": "⚡",
                "use_case": "Logisches Denken & Reasoning"
            },
            "llama3.1:8b": {
                "size": "4.9 GB",
                "ram": "10 GB",
                "speed": "⚡",
                "use_case": "Beste Balance"
            },
            "gemma2:9b": {
                "size": "5.4 GB",
                "ram": "10 GB",
                "speed": "⚡",
                "use_case": "Google Premium Qualität"
            },
            "gpt-oss:20b": {
                "size": "13 GB",
                "ram": "14 GB",
                "speed": "🐌",
                "use_case": "Komplexe Code-Aufgaben"
            }
        }
