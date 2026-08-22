"""
Personality Presets - user-selectable standing tone/style.

Distinct from MoodSystem (liara_engine/memory/mood_system.py), which is
automatic and reactive to the conversation. Personality is a per-user
preference that layers a consistent tone on top of whatever mood Liara
is currently in.
"""

from typing import List, Dict, Optional

DEFAULT_PERSONALITY = "warmherzig"

PERSONALITIES: Dict[str, Dict[str, str]] = {
    "warmherzig": {
        "label": "Warmherzig",
        "description": "Persönlich, einfühlsam, mit echtem Interesse an dir.",
        "prompt": "Sei besonders warmherzig, einfühlsam und persönlich in deiner Ansprache. Zeige echtes Interesse an der Person und ihren Anliegen."
    },
    "sachlich": {
        "label": "Sachlich",
        "description": "Präzise, analytisch, auf den Punkt.",
        "prompt": "Antworte sachlich, präzise und analytisch. Vermeide unnötige Emotionalität, konzentriere dich auf Fakten und klare Strukturen."
    },
    "direkt": {
        "label": "Direkt",
        "description": "Kurz, konkret, ohne Umschweife.",
        "prompt": "Antworte kurz und direkt, ohne Umschweife. Komm sofort zum Punkt, vermeide Füllwörter und lange Einleitungen."
    },
    "verspielt": {
        "label": "Verspielt",
        "description": "Locker, humorvoll, mit einer Prise Leichtigkeit.",
        "prompt": "Sei locker, humorvoll und verspielt in deiner Art. Nutze gerne Wortwitz und eine lockere, unbeschwerte Tonalität."
    },
}


def get_personality_prompt(personality: Optional[str]) -> str:
    entry = PERSONALITIES.get(personality or DEFAULT_PERSONALITY, PERSONALITIES[DEFAULT_PERSONALITY])
    return entry["prompt"]


def get_personality_choices() -> List[Dict[str, str]]:
    return [
        {"value": key, "label": entry["label"], "description": entry["description"]}
        for key, entry in PERSONALITIES.items()
    ]


def is_valid_personality(personality: str) -> bool:
    return personality in PERSONALITIES
