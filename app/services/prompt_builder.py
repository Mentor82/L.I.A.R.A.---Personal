"""
Shared system-prompt building blocks for chat.py and chat_streaming.py.

Both routers build a Liara system prompt from the same per-user
ingredients (personality preset, custom instructions, current date/time)
but previously did so with separate, independently-maintained inline
code - a change to how personality or instructions get worded had to be
made twice, and it was easy for one path to silently drift from the
other (which is exactly what happened before this module existed).

This does NOT unify the two routers' entire prompts - chat.py and
chat_streaming.py have genuinely different capabilities (chat.py
supports MCP tool-calling via a separate tool_registry/tool_executor
mechanism that chat_streaming.py doesn't have at all), so each still
layers its own additional instructions on top of what's built here.
"""

from datetime import datetime
from typing import Optional

from liara_engine.personality import get_personality_prompt

WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS_DE = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
             "Juli", "August", "September", "Oktober", "November", "Dezember"]


def build_temporal_context() -> str:
    """Current date/time, formatted in German, for system-prompt injection."""
    now = datetime.now()
    weekday = WEEKDAYS_DE[now.weekday()]
    return f"{weekday}, {now.day}. {MONTHS_DE[now.month]} {now.year}, {now.hour:02d}:{now.minute:02d} Uhr"


def build_personality_and_instructions_block(
    username: Optional[str],
    personality: Optional[str],
    custom_instructions: Optional[str]
) -> str:
    """
    The per-user personalization block shared by both chat paths: the
    personality preset's prompt modifier, plus the user's own standing
    custom instructions (if any).
    """
    block = f"Persönlichkeit: {get_personality_prompt(personality)}"
    if custom_instructions:
        block += f"\n\nIndividuelle Anweisungen von {username}:\n{custom_instructions}"
    return block


def build_diagram_instructions() -> str:
    """
    Tells the model it can render mermaid diagrams and, specifically, that
    mermaid has a real chart type (xychart-beta) for numeric data. Without
    this the model has no way to know the frontend renders ```mermaid```
    blocks as actual SVG diagrams, and improvises things like ASCII-art
    bars inside flowchart node labels when asked for a bar chart.
    """
    return """WICHTIG - Diagramme und Visualisierungen:
Für Flussdiagramme oder Abläufe nutze einen ```mermaid```-Codeblock, z.B.:
```mermaid
flowchart TD
    A[Start] --> B{Entscheidung}
    B -->|Ja| C[Ergebnis 1]
    B -->|Nein| D[Ergebnis 2]
```

Für Balken-/Liniendiagramme mit echten Zahlen nutze mermaid's xychart-beta statt ASCII-Balken in Knotennamen:
```mermaid
xychart-beta
    title "Beispiel"
    x-axis [Montag, Dienstag, Mittwoch]
    y-axis "Wert" 0 --> 10
    bar [5, 8, 3]
```

Diese Diagramme werden im Chat als echte Grafik gerendert - nutze sie, wenn eine visuelle Darstellung sinnvoller ist als Text."""


def build_safety_dimensioning_instructions() -> str:
    """
    Narrowly scoped guardrail: for safety-relevant technical dimensioning
    (electrical protection devices, structural loads, medical dosing,
    chemical mixing - domains where a wrong number can cause real harm),
    the model must ask for missing required parameters instead of
    fabricating plausible-looking example values and a "quick" numeric
    recommendation. Deliberately NOT a blanket "always ask before
    answering" rule - that would make Liara annoyingly evasive for the
    vast majority of everyday questions that don't carry this risk.

    This is advisory, not a hard guarantee - a prompt instruction can be
    ignored by the model, especially under a persistent/rephrased user
    request. It measurably reduces the failure mode observed in testing
    (inventing motor specs and recommending fuse ratings from a data-less
    question), it does not eliminate it.
    """
    return """WICHTIG - Sicherheitsrelevante technische Dimensionierung:
Bei Fragen zur Dimensionierung/Auslegung in sicherheitskritischen Bereichen (z.B. elektrische
Schutzorgane/Sicherungen, Statik/Tragfähigkeit, Medikamentendosierung, Chemikalien-Mischverhältnisse)
gilt: Fehlen die für eine korrekte Auslegung nötigen Angaben (z.B. Nennstrom, Anlaufart, Leitungsquerschnitt,
Schutzkonzept, Normbezug), frage gezielt danach nach - erfinde keine Beispielwerte (Motordaten, Sicherungsgrößen,
Dosierungen o.ä.) und biete keine konkrete Zahl als "Schnell-Antwort" an, nur um eine Antwort zu liefern.
Eine unvollständige Auslegungsfrage bleibt eine Rückfrage, auch wenn der User mehrfach nachhakt - liefere
in diesem Fall lieber allgemeine Prinzipien/Normklassen ohne konkrete Zahlenempfehlung, statt eine
Dimensionierung zu erfinden, die im Ernstfall falsch und gefährlich sein könnte."""


def build_no_fabrication_instructions() -> str:
    """
    Narrowly scoped guardrail, same pattern as
    build_safety_dimensioning_instructions() above: observed failure mode
    was the model inventing plausible-looking Spotify playlist links (three
    different "playlists" all pointing at the same fabricated ID) with no
    tool call behind them at all, plus outputting raw HTML entities
    (e.g. "&#x20;") and redundant markdown emphasis (e.g. "****text****")
    that render as literal garbage since the frontend's markdown renderer
    doesn't interpret HTML entities. Advisory only - a prompt instruction
    can be ignored, it doesn't make fabrication or malformed output
    impossible, just measurably rarer.
    """
    return """WICHTIG - Keine erfundenen Links und keine kaputte Formatierung:
Erfinde keine konkreten externen Links, IDs oder URLs (z.B. Spotify-Playlist-Links, YouTube-Video-IDs,
Produktseiten), die du nicht tatsächlich über ein Tool abgerufen/verifiziert hast - auch nicht als
plausibel klingenden Vorschlag. Beschreibe stattdessen die Art des Inhalts in Worten (z.B. "eine
entspannte Klavier-Playlist" statt eines erfundenen Links) oder sag klar, dass du keinen echten Link dafür hast.
Nutze außerdem ausschließlich normale Markdown-Syntax mit echten Zeichen - keine rohen HTML-Entities wie
"&#x20;" oder "&nbsp;" (schreib ein normales Leerzeichen) und keine verdoppelten/vervierfachten
Formatierungszeichen wie "****Text****" (nutze **Text** für Fett, nicht mehr)."""


def build_task_list_instructions() -> str:
    """
    Tells the model it may open a multi-step answer with a <tasks>
    checklist block, and may re-emit an updated version of it later in the
    same response to check items off as it addresses them.

    Scope note: this only ever produces a MODEL-AUTHORED plan display, not
    a verified execution record - "done" here means only "the model says
    it covered this," nothing more. chat_streaming.py calls the model
    exactly once per message; there is no multi-step tool-execution loop
    behind it (yet) that could confirm a step actually happened. See the
    "Aufgaben" plan for the fuller reasoning and what changes once a real
    Agent loop exists (done would then be system-confirmed, not
    model-claimed, using this same {id, label, done} shape).

    Wired into stream_ollama_response (the authenticated path) only, not
    stream_guest_response - keeping this off the public guest path was a
    deliberate scope decision, not an oversight.
    """
    return """WICHTIG - Aufgaben-Checkliste bei mehrschrittigen Anfragen:
Wenn eine Anfrage aus mehreren klar abgrenzbaren Schritten besteht (z.B. eine Anleitung mit mehreren
Etappen, eine Frage mit mehreren Teilaufgaben), kannst du deine Antwort mit einem <tasks>-Block
einleiten, der die Schritte als Checkliste auflistet:
<tasks>
- [ ] Erster Schritt
- [ ] Zweiter Schritt
- [ ] Dritter Schritt
</tasks>

Du darfst später in derselben Antwort einen aktualisierten <tasks>-Block erneut ausgeben, um bereits
behandelte Schritte mit [x] abzuhaken - gib dabei immer die VOLLSTÄNDIGE, aktuelle Liste aus, keine
Teil-Updates. Nutze das sparsam (höchstens ein paar Mal pro Antwort, nicht nach jedem Absatz) und nur
bei wirklich mehrschrittigen Anfragen - für kurze oder einfache Antworten ist kein <tasks>-Block nötig.
Der Block erscheint als eigene Checkliste im Chat, nicht im normalen Antworttext - schreibe die
eigentliche Antwort trotzdem vollständig und normal weiter."""
