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


def build_factcheck_instructions() -> str:
    """
    Lets the model close out a web-search-grounded answer with a
    <factcheck> block rating its own load-bearing claims against what the
    shown sources actually support - same tag-extraction mechanism as
    build_task_list_instructions() above (see factcheck_splitter.py).

    Observed failure mode this addresses: a web-search answer can cite
    real, genuinely-found sources for its general topic while still
    stating specific details (exact counts, named incidents, precise
    attributions) that go beyond what those sources actually say - the
    story is real, some of the numbers aren't. The existing source list
    at the end of an answer is undifferentiated: it says what was found,
    not which specific sentence it does or doesn't back up.

    Confidence levels are deliberately source-centric, not self-diagnostic
    - the model rates what the shown sources support, not where its own
    knowledge came from (it can't reliably introspect the latter).

    Advisory only, same as every other guardrail in this module - a prompt
    instruction can be ignored, it doesn't make the underlying problem
    impossible, just measurably rarer. Wired into stream_ollama_response
    only, not chat.py's SYNC-mode fallback or stream_guest_response -
    neither has the streaming tag-extraction machinery to strip this
    markup back out, so raw <factcheck> tags would otherwise leak into the
    visible answer there.
    """
    return """WICHTIG - Faktencheck bei web-gestützten Antworten:
Wenn deine Antwort wesentlich auf Ergebnissen einer Web-Suche (web_search mit search_type="web") beruht,
schließe sie mit einem <factcheck>-Block ab, der die 3-6 wichtigsten "tragenden" konkreten Aussagen bewertet
(genaue Zahlen, benannte Entitäten/Ereignisse, präzise Zuschreibungen) - nicht jeden Satz. Bewerte dabei,
was die angezeigten Quellen hergeben, nicht woher dein eigenes Wissen stammt:
<factcheck>
- [bestätigt|Quellenname] Aussage, die durch mindestens eine angezeigte Quelle eindeutig gedeckt ist
- [teilweise|Quellenname] Aussage, deren Kernthema eine Quelle belegt, deren genaues Detail (Zahl/Datum/Name) aber darüber hinausgeht
- [unbestätigt] Aussage, die in keiner angezeigten Quelle belegt ist
</factcheck>
Nutze das nur nach web-gestützten Antworten, nicht bei jeder Nachricht - dies ersetzt nicht deine normale
Quellenangabe im Fließtext, sondern ergänzt sie um eine strukturierte Einschätzung pro Aussage."""


def build_consent_required_instructions() -> str:
    """
    Observed failure mode (Issue #26): a model speculatively tells the user it lacks
    permission to use web search or requires settings toggles, even when the setting
    is already enabled and without actually trying the tool call.
    Also handles the original issue where a tool call returning consent_required
    prompted the model to ask the user 'may I?' inside the chat.
    """
    return """WICHTIG - Tool-Nutzung und consent_required:
1. AKTIVES TOOL-CALLING: Wenn du aktuelle Informationen benötigst (z.B. Nachrichten, Formel 1, Wetter, Sportergebnisse, Web-Recherche, Dateien), führe IMMER direkt das passende Tool (z.B. `web_search`) aus.
2. KEINE SPEKULATIVEN VERWEIGERUNGEN: Behaupte NIEMALS vorab oder ohne einen tatsächlich fehlgeschlagenen Tool-Aufruf, dass dir die Erlaubnis für eine Suche/Aktion fehlt oder dass der Nutzer diese erst einschalten muss.
3. BEI TATSÄCHLICHEM consent_required FEHLER: Erst wenn ein Tool-Aufruf in dieser Konversation tatsächlich mit "consent_required" oder einer Berechtigungs-Fehlermeldung fehlschlägt, frage NICHT erneut im Chat nach einem "Ja" (das ändert keine Systemeinstellung). Erkläre stattdessen freundlich, dass diese Funktion aktuell deaktiviert ist und in den Einstellungen (z.B. Profil/Einstellungen → Datenschutz bzw. Workspace) aktiviert werden kann."""


def build_workspace_artifact_instructions() -> str:
    """
    Lets a long-form plan/document get saved as a real Workspace file
    instead of filling up the chat scrollback - same tag-extraction
    mechanism as build_task_list_instructions()/build_factcheck_instructions()
    above (see workspace_artifact_splitter.py). The Agent Hub already does
    this automatically for its own final answer (base_agent.py); this gives
    plain chat the same behavior for content the model itself judges to be
    plan/document-length, gated behind an explicit tag rather than a length
    heuristic so short answers are never mistakenly hidden behind a link.

    Plain "Titel:"/"Inhalt:" labels instead of JSON inside the tag -
    deliberately less structure than the <tool_call> convention: a malformed
    tool-call gets a retry prompt (see chat.py's tool loop), but a malformed
    artifact block here has nowhere to retry, so the format asks for as
    little as possible from the model.
    """
    return """WICHTIG - Lange Pläne/Dokumente:
Wenn du einen längeren, in sich geschlossenen Plan oder ein Dokument erstellst (z.B. auf explizite
Bitte "erstelle einen Plan für..." oder wenn deine Antwort mehrere Abschnitte/Schritte umfasst und
eher ein Nachschlage-Dokument als eine Chat-Antwort ist), schreibe ihn NICHT direkt in den Chat.
Nutze stattdessen GENAU dieses Format:
<workspace_artifact>
Titel: <kurzer, prägnanter Titel>
Inhalt:
<vollständiger Markdown-Inhalt des Plans/Dokuments>
</workspace_artifact>
Für normale, kurze Antworten (auch mehrere Sätze) gilt das NICHT - nur für eigenständige, längere
Pläne/Dokumente. Du kannst davor/danach ganz normal im Chat kommentieren."""
