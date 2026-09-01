"""
Structured Incremental Compactor
================================
Verdichtet ältere Konversations-Turns inkrementell in einen strukturierten
JSON-State unter strikter Einhaltung der 'Never Remove'-Regeln.
"""
import logging
import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

COMPACTOR_SYSTEM_PROMPT = """Du bist der strukturierte Context-Kompaktor für L.I.A.R.A.
Deine Aufgabe ist es, ältere Chat-Turns in einen sauberen, strukturierten JSON-Zustand zu überführen.

### STRIKTE SCHUTZREGELN (NEVER REMOVE):
1. Lösche NIEMALS explizite Architekturentscheidungen oder Einigungen.
2. Lösche NIEMALS Benutzer-Vorgaben (Constraints), No-Gos oder Korrekturen.
3. Lösche NIEMALS noch offene Todos, Aufgaben oder ungeklärte Fragen.
4. Behalte stets konkrete technische Identifikatoren (Ports, Pfade, Dateinamen, Modell-Namen, Hashes).

Antworte AUSSCHLIESSLICH mit einem validen JSON-Objekt mit folgender Struktur:
{
  "active_topics": ["Thema 1", "Thema 2"],
  "decisions": ["Entscheidung 1 mit Begründung", "Entscheidung 2"],
  "user_constraints": ["Benutzer-Regel 1", "Einschränkung 2"],
  "open_tasks": ["Offene Aufgabe 1"],
  "technical_state": ["Technischer Stand (z.B. Endpoints, Versionen, Konfiguration)"],
  "uncertainties": ["Ungeklärte Punkte"]
}"""


@dataclass
class StructuredSessionState:
    """Verdichteter Zustand der bisherigen Konversation."""
    active_topics: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    user_constraints: List[str] = field(default_factory=list)
    open_tasks: List[str] = field(default_factory=list)
    technical_state: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    last_compacted_turn_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuredSessionState":
        if not isinstance(data, dict):
            return cls()
        return cls(
            active_topics=list(data.get("active_topics") or []),
            decisions=list(data.get("decisions") or []),
            user_constraints=list(data.get("user_constraints") or []),
            open_tasks=list(data.get("open_tasks") or []),
            technical_state=list(data.get("technical_state") or []),
            uncertainties=list(data.get("uncertainties") or []),
            last_compacted_turn_index=int(data.get("last_compacted_turn_index") or 0)
        )

    def is_empty(self) -> bool:
        return not (
            self.active_topics
            or self.decisions
            or self.user_constraints
            or self.open_tasks
            or self.technical_state
            or self.uncertainties
        )

    def format_context_block(self) -> str:
        """Formatiert den strukturierten State als sauberen Markdown-Kontextblock."""
        if self.is_empty():
            return ""

        lines = ["\n[STRUCTURED SESSION STATE (Verdichtete Gesprächs- & Beschlusslage)]:\n```json\n" + json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n```\n(Hinweis: Diese Beschlüsse und Constraints sind verbindliche Richtlinien für deine Antwort.)\n"]
        return "".join(lines)


class StructuredCompactor:
    """Führt deterministische und inkrementelle Verdichtung durch."""

    @classmethod
    def extract_heuristic_facts(cls, turns: List[Dict[str, Any]], current_state: StructuredSessionState) -> StructuredSessionState:
        """
        Extrahierte Fakten aus Turns anhand deterministischer Heuristiken
        (schnell, 0ms LLM-Latenz, robust gegen Vergessen).
        """
        state = StructuredSessionState.from_dict(current_state.to_dict())

        decision_patterns = [
            re.compile(r"(?:wir nutzen|wir verwenden|wir nehmen|beschlossen|festgelegt|entschieden|standard ist)\s+([^\.\n]+)", re.IGNORECASE),
            re.compile(r"(?:fallback ist|primaer ist|standard:\s*)([^\.\n]+)", re.IGNORECASE)
        ]
        constraint_patterns = [
            re.compile(r"(?:bitte nur|niemals|auf keinen fall|wichtig:\s*immer|kein\s+\w+|nur auf deutsch)\s*([^\.\n]+)?", re.IGNORECASE)
        ]

        for turn in turns:
            content = str(turn.get("content", "") or turn.get("text", ""))
            if not content:
                continue

            for pat in decision_patterns:
                match = pat.search(content)
                if match:
                    val = match.group(0).strip()
                    if val and val not in state.decisions and len(val) < 140:
                        state.decisions.append(val)

            for pat in constraint_patterns:
                match = pat.search(content)
                if match:
                    val = match.group(0).strip()
                    if val and val not in state.user_constraints and len(val) < 140:
                        state.user_constraints.append(val)

        return state
