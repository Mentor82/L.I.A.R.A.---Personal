"""
Memory Verification - Widerspruchs-Erkennung & Konfidenz-gewichtetes,
bi-temporales Gedächtnis (Issue: "Hartnäckigkeit" / Neo4j-Memory-Poisoning,
2026-09-03).

Hintergrund: Jede Chat-Antwort wird automatisch ins Neo4j-4D-Gedächtnis
indexiert (persistence_stage.py) und später - unabhängig von Session/Alter -
per Embedding-Similarity in neue Gespräche zurückgeholt (memory_integration.py's
get_relevant_context). Bis zum chat_streaming.py-Fix vom 2026-09-03 wurde dabei
nicht unterschieden, OB eine gespeicherte Aussage überhaupt noch stimmt - eine
falsche Vorbehauptung des Modells wurde stundenlang als Fakt wiederholt.

Dieses Modul ist der nächste Schritt: statt nur zu warnen ("könnte veraltet
sein"), wird jede Erinnerung mit einem Epistemic State + Konfidenz +
Gültigkeits-Fenster versehen (bi-temporal: nichts wird gelöscht, nur
invalidiert), und Widersprüche lösen eine echte Nachprüfung statt eines
Blind-Overwrites aus - weder eine frühere KI-Aussage noch eine bloße
Nutzer-Behauptung "das ist falsch" gilt für sich allein als Wahrheit, sondern
nur ein tatsächlich verifiziertes Ergebnis (Tool-Call-Resultat).

Terminologie bewusst deckungsgleich mit dem Schwester-Repo C:/ai/LIARA's
ADR-007 ("AI-Brain Epistemic Subgraph", docs/05_decisions/adr-007-ai-brain-
epistemic-subgraph-capability.md, ai_brain/schema.py) - dort existiert exakt
dasselbe Konzept bereits ausgereifter (inkl. Visitor-Pass-Autorisierung für
externe Agenten, hier nicht gebraucht). Diese Datei übernimmt nur die
EpistemicState-Werte und Feldnamen (confidence/valid_from/source_type) für
künftige Konsistenz - kein Code-Import aus dem Schwester-Repo, da eigenständiges
Deployment.

Drei Verifikations-Trigger (siehe MEMORY_VERIFICATION_TRIGGERS unten für die
Zuordnung zu den Aufrufstellen):
  a) Automatisch bei Tool-Widerspruch (tool_executor.py) - stärkster Trigger,
     der Tool-Call selbst ist der Beleg, invalidiert die alte Erinnerung
     sofort hart (-> CONTRADICTED).
  b) Nutzer-Widerspruch (chat_streaming.py) - erkannt per Heuristik hier,
     löst eine echte Nachprüfung aus statt sofort zu überschreiben.
  c) Explizites Korrektur-Kommando (productivity_tools.py's correct_memory
     Tool) - höchste Priorität, aber nur auf bewusste Anforderung.
"""

import re
import logging
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# EPISTEMIC STATE (== ai_brain/schema.py's EpistemicState, ADR-007)
# ============================================================================
class EpistemicState(str, Enum):
    USER_CONFIRMED = "USER_CONFIRMED"  # Vom Nutzer direkt geäußert/bestätigt (confidence = 1.0)
    VERIFIED = "VERIFIED"              # Durch einen echten Tool-Call/Test belegt
    INFERENCE = "INFERENCE"            # Algorithmische KI-Aussage, unbestätigt (bleibt so markiert)
    HYPOTHESIS = "HYPOTHESIS"          # Explorativ/spekulativ
    CONTRADICTED = "CONTRADICTED"      # Mit explizitem Gegenbeleg versehen
    SUPERSEDED = "SUPERSEDED"          # Historisch sichtbar, aber nicht mehr aktueller Stand


# Relation-Typen für die Neo4j-Kanten zwischen Erinnerungen - Teilmenge von
# ADR-007's SemanticRelation/EvolutionRelation, nur was hier gebraucht wird.
class MemoryRelation(str, Enum):
    CONTRADICTS = "CONTRADICTS"
    SUPERSEDES = "SUPERSEDES"


# ============================================================================
# TRUST-HIERARCHIE (Ausgangs-Epistemic-State + Konfidenz je nach Quelle)
# ============================================================================
# Kein Freifahrtschein - nur der Startwert bei der Speicherung. Ein Tool-
# Ergebnis startet als VERIFIED, weil der Tool-Call selbst der Beleg ist. Eine
# frühere KI-Antwort startet als INFERENCE mit niedriger Konfidenz, weil sie
# (wie der Auslöse-Vorfall zeigte) falsch oder inzwischen veraltet sein kann,
# ohne dass irgendetwas das je geprüft hat.
SOURCE_TYPE_TO_EPISTEMIC_STATE = {
    "tool_result": EpistemicState.VERIFIED,
    "user_statement": EpistemicState.USER_CONFIRMED,
    "assistant_reply": EpistemicState.INFERENCE,
}

EPISTEMIC_STATE_CONFIDENCE = {
    EpistemicState.USER_CONFIRMED: 1.0,
    EpistemicState.VERIFIED: 0.95,
    EpistemicState.INFERENCE: 0.3,
    EpistemicState.HYPOTHESIS: 0.15,
    EpistemicState.CONTRADICTED: 0.1,
    EpistemicState.SUPERSEDED: 0.0,
}

DEFAULT_EPISTEMIC_STATE = EpistemicState.INFERENCE  # unbekannte/alte Message-Knoten ohne source_type (Migration)

# Ab dieser Konfidenz-Differenz gilt eine neue Info als eindeutig vertrauens-
# würdiger als eine bestehende Erinnerung zum selben Konzept (Trigger a).
AUTO_INVALIDATE_TRUST_DELTA = 0.3

# Wie stark die Konfidenz einer Erinnerung sinkt, wenn ein Nutzer-Widerspruch
# erkannt wurde, aber keine echte Nachprüfung möglich war (reine Meinungs-
# sache, kein zugehöriger Tool-Call) - BeliefMem-Gedanke: Unsicherheit halten
# statt hart auf invalid/valid zu springen.
UNVERIFIED_CONTRADICTION_PENALTY = 0.3


# ============================================================================
# HEURISTISCHE WIDERSPRUCHS-/KORREKTUR-ERKENNUNG
# ============================================================================
# Gleiches Muster wie app/liara_engine/nlp/sentiment_analyzer.py (Keywords +
# Regex-Patterns, gewichtet zu einem Score) - dort für emotionale Tonlage,
# hier für "widerspricht/korrigiert der Nutzer eine vorherige Aussage".
# Bewusst nur Heuristik (schnell, kostenlos, läuft bei jeder Nachricht) - ein
# LLM-Klassifikationsschritt ist nur als Fallback vorgesehen, falls sich die
# Heuristik in der Praxis als zu ungenau erweist (noch nicht gebaut).

class CorrectionMarkers:
    """Schlüsselwörter/Muster, die auf einen Widerspruch zu einer früheren Aussage hindeuten."""

    DIRECT_NEGATION = {
        "keywords": [
            "das stimmt nicht", "stimmt nicht", "das ist falsch", "ist falsch",
            "nicht richtig", "nicht korrekt", "das ist nicht wahr", "nicht wahr",
            "quatsch", "unsinn", "das ist quatsch",
            "that's wrong", "that's incorrect", "not true", "not correct",
            "incorrect", "that's false",
        ],
        "patterns": [
            r"^\s*nein[,.!]",  # Satzanfang "Nein, ..."
            r"^\s*no[,.!]",
            r"\bdas\s+ist\s+(nicht|kein)\b",
        ],
        "weight": 1.0,
    }

    CORRECTION_PHRASING = {
        "keywords": [
            "eigentlich ist es", "tatsächlich ist es", "in wahrheit",
            "korrektur:", "das war falsch", "du hast dich geirrt",
            "du irrst dich", "das ist ein irrtum", "das war ein fehler",
            "du liegst falsch", "das hast du falsch verstanden",
            "actually,", "correction:", "you're wrong", "you were wrong",
            "that was a mistake", "you made a mistake",
        ],
        "patterns": [
            r"\bnicht\s+\w+,?\s+sondern\b",  # "nicht X, sondern Y" - klassisches Korrektur-Muster
            r"\bnot\s+\w+,?\s+but\s+\w+\b",
        ],
        "weight": 1.0,
    }

    CAPABILITY_DENIAL_ECHO = {
        # Spezifisch für den Auslöse-Fall: der Nutzer zitiert/wiederholt eine
        # KI-Behauptung über eine (Nicht-)Fähigkeit, um sie zu bestreiten -
        # z.B. "du kannst das doch", "das Tool gibt es doch", "es geht doch".
        "keywords": [
            "das geht doch", "das kannst du doch", "gibt es doch",
            "das funktioniert doch", "doch möglich", "ist doch möglich",
        ],
        "patterns": [],
        "weight": 0.7,
    }


# Fähigkeits-Verneinung in einer früheren KI-Antwort ("das unterstützt das
# Tool nicht", "das kann ich nicht") - für Trigger a (tool_executor.py):
# wenn danach genau der verneinte Tool-Call erfolgreich durchläuft, ist der
# Tool-Call selbst der Beleg, dass die alte Verneinung falsch war/ist. Das
# ist der exakte Auslöse-Fall dieses ganzen Systems (siehe Modul-Docstring -
# "web_search unterstützt nur die Modi instant, web und wikipedia", obwohl
# der images-Modus längst existierte).
CAPABILITY_DENIAL_PATTERNS = [
    r"kann(?:st|te)?\s+(?:ich|das|du)?\s*(?:leider\s+)?nicht",
    r"unterstützt\s+(?:das\s+)?(?:aktuell\s+|derzeit\s+)?nicht",
    r"nicht\s+möglich",
    r"nicht\s+unterstützt",
    r"geht\s+(?:das\s+)?(?:leider\s+)?nicht",
    r"can'?t\b",
    r"does(?:n't|\s+not)\s+support",
    r"not\s+(?:possible|supported)",
]


def detect_capability_denial(text: str) -> bool:
    """Grobe Heuristik: enthält der Text eine Fähigkeits-Verneinung?"""
    if not text:
        return False
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in CAPABILITY_DENIAL_PATTERNS)


def detect_correction_signal(text: str) -> Dict:
    """
    Prüft, ob eine Nachricht Signale für einen Widerspruch/eine Korrektur zu
    einer früheren Aussage enthält. Reiner Text-Heuristik-Schritt, kein
    Datenbank-Zugriff - schnell genug für jede einzelne Nutzer-Nachricht.

    Returns:
        {
            'is_correction': bool,
            'confidence': float (0.0-1.0),
            'indicators': List[str],
        }
    """
    if not text or len(text.strip()) < 3:
        return {"is_correction": False, "confidence": 0.0, "indicators": []}

    text_lower = text.lower()
    indicators: List[str] = []
    weighted_score = 0.0

    for marker_set in (
        CorrectionMarkers.DIRECT_NEGATION,
        CorrectionMarkers.CORRECTION_PHRASING,
        CorrectionMarkers.CAPABILITY_DENIAL_ECHO,
    ):
        for keyword in marker_set["keywords"]:
            if keyword in text_lower:
                indicators.append(keyword)
                weighted_score += marker_set["weight"]

        for pattern in marker_set["patterns"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                indicators.append(f"pattern:{pattern[:30]}")
                weighted_score += marker_set["weight"] * 1.2  # Patterns wiegen etwas mehr, wie im Sentiment-Vorbild

    # 2+ unabhängige Indikatoren = klar erkennbarer Widerspruch. Ein einzelnes
    # schwaches Signal (z.B. nur "nicht gut" irgendwo im Satz) reicht nicht -
    # das wäre zu unpräzise und würde harmlose Nachrichten fälschlich als
    # Korrektur werten.
    confidence = min(1.0, weighted_score / 2.0)
    is_correction = confidence >= 0.5

    return {
        "is_correction": is_correction,
        "confidence": round(confidence, 2),
        "indicators": indicators[:5],
    }


def classify_source_type(role: str, via_tool_result: bool = False) -> str:
    """
    Leitet den source_type für einen neuen Message-Knoten ab - Grundlage für
    den Epistemic State beim Speichern (siehe SOURCE_TYPE_TO_EPISTEMIC_STATE
    oben). String bleibt das gespeicherte Feld (source_type), da bestehende
    Aufrufer/Migrationen darauf aufbauen; epistemic_state_for() übersetzt es
    bei Bedarf in den ADR-007-Enum-Wert.
    """
    if via_tool_result:
        return "tool_result"
    if role == "user":
        return "user_statement"
    return "assistant_reply"


def epistemic_state_for(source_type: str) -> EpistemicState:
    return SOURCE_TYPE_TO_EPISTEMIC_STATE.get(source_type, DEFAULT_EPISTEMIC_STATE)


def initial_confidence_for(source_type: str) -> float:
    state = epistemic_state_for(source_type)
    return EPISTEMIC_STATE_CONFIDENCE[state]
