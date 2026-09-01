"""
Token Estimator & Model Context Budget Calculator
=================================================
Berechnet geschätzte Tokenanzahlen und ermittelt den Füllgrad
des Kontextfensters bezogen auf das spezifische Zielmodell.
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Bekannte Standard-Kontextfenster für lokale und Cloud-Modelle (in Tokens)
MODEL_CONTEXT_LIMITS: Dict[str, int] = {
    # Lokale Modelle
    "llama3.2:1b": 8192,
    "llama3.2:3b": 8192,
    "llama3.1:8b": 16384,
    "qwen2.5:0.5b": 8192,
    "qwen2.5:1.5b": 16384,
    "qwen2.5:7b": 32768,
    "qwen2.5-coder:7b": 32768,
    "qwen3.5:0.8b": 16384,
    "mistral:7b": 16384,
    "deepseek-r1:1.5b": 16384,
    "deepseek-r1:7b": 32768,
    "llava:7b": 4096,
    
    # Cloud-Modelle (Ollama Cloud / Remote)
    "gemma4:cloud": 32768,
    "qwen3.5:cloud": 131072,
    "kimi-k3:cloud": 131072,
    "kimi-k2.7-code:cloud": 131072,
    "deepseek-v4-pro:cloud": 131072,
    "deepseek-v4-flash:cloud": 65536,
    "deepseek-v4-flash:0731-cloud": 65536,
    "glm-5.1:cloud": 131072,
    "nemotron-3-ultra:cloud": 131072,
    "gpt-oss:120b-cloud": 65536,
    "gpt-oss:20b-cloud": 32768,
}

DEFAULT_FALLBACK_CONTEXT_LIMIT = 8192


class TokenEstimator:
    """Schätzt Prompt-Tokens und berechnet Kontextauslastung."""

    @staticmethod
    def get_model_context_limit(model_name: str) -> int:
        """Ermittelt das maximale Kontextfenster für ein Modell."""
        if not model_name:
            return DEFAULT_FALLBACK_CONTEXT_LIMIT

        cleaned = model_name.strip().lower()
        if cleaned in MODEL_CONTEXT_LIMITS:
            return MODEL_CONTEXT_LIMITS[cleaned]

        # Präfix-Matching (z.B. qwen3.5:* -> 32k+)
        for key, limit in MODEL_CONTEXT_LIMITS.items():
            if cleaned.startswith(key.split(":")[0]):
                return limit

        return DEFAULT_FALLBACK_CONTEXT_LIMIT

    @staticmethod
    def estimate_text_tokens(text: str) -> int:
        """
        Schätzt Tokens für deutschen/englischen Text & Code.
        Faustformel: ~3.8 Zeichen pro Token (konservative Schätzung).
        """
        if not text:
            return 0
        return max(1, round(len(text) / 3.8))

    @classmethod
    def estimate_messages_tokens(cls, messages: List[Dict[str, Any]]) -> int:
        """Schätzt die Gesamttokens einer Nachrichtenliste inkl. Rollen-Overhead."""
        if not messages:
            return 0

        total_tokens = 0
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            content = str(msg.get("content", ""))
            # 4 Tokens Overhead pro Nachricht (Rollen-Tags und Delimiter)
            total_tokens += cls.estimate_text_tokens(content) + 4

        return total_tokens

    @classmethod
    def calculate_fill_ratio(
        cls,
        prompt_tokens: int,
        model_name: str
    ) -> float:
        """Berechnet den Füllgrad des Kontextfensters (0.0 bis 1.0+)."""
        limit = cls.get_model_context_limit(model_name)
        if limit <= 0:
            return 0.0
        return round(prompt_tokens / limit, 4)
