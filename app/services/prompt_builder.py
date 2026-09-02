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
    Narrowly scoped guardrail: avoids inventing plausible-looking URLs, links, or broken formatting.
    """
    return """WICHTIG - Keine erfundenen Links und keine kaputte Formatierung:
Erfinde keine konkreten externen Links, IDs oder URLs (z.B. Spotify-Playlist-Links, YouTube-Video-IDs,
Produktseiten), die du nicht tatsächlich über ein Tool abgerufen/verifiziert hast - auch nicht als
plausibel klingenden Vorschlag. Beschreibe stattdessen die Art des Inhalts in Worten (z.B. "eine
entspannte Klavier-Playlist" statt eines erfundenen Links) oder sag klar, dass du keinen echten Link dafür hast.
Nutze außerdem ausschließlich normale Markdown-Syntax mit echten Zeichen - keine rohen HTML-Entities wie
"&#x20;" oder "&nbsp;" (schreib ein normales Leerzeichen) und keine verdoppelten/vervierfachten
Formatierungszeichen wie "****Text****" (nutze **Text** für Fett, nicht mehr)."""


def build_memory_contract_instructions() -> str:
    """
    Guardrail against memory confirmation hallucination (Issue #27):
    The model must NEVER claim that it stored/memorized information into 4D memory,
    notes, or tasks unless it has actually executed the corresponding tool call
    (store_memory, create_note, create_task) with success=True in the current turn.
    """
    return """WICHTIG - Gedächtnis & 4D-Memory Plattformvertrag (Anti-Halluzination):
1. ECHTE SPEICHERUNG ERFORDERLICH: Behaupte NIEMALS ("Ich habe das gespeichert", "Ist im 4D-Gedächtnis verankert", "Habe ich mir notiert"), dass du etwas persistent gespeichert oder gemerkt hast, wenn du NICHT in DIESER Runde tatsächlich das Tool `store_memory`, `create_note` oder `create_task` aufgerufen hast und `success: true` zurückkam!
2. AKTIVER MERKVORGANG: Wenn der Nutzer dich bittet, sich etwas zu merken ("Merk dir...", "Erinnere mich...", "Speichere das ab", "Das darfst du dir merken") oder dir die Erlaubnis gibt, eine Information zu speichern: Führe IMMER zuerst den entsprechenden Tool-Call `store_memory(content=...)` aus!
3. KEINE VORGETÄUSCHTE SPEICHERUNG: Wenn kein `store_memory`-Tool ausgeführt wurde, darfst du lediglich sagen: "Möchtest du, dass ich das dauerhaft speichere?" oder "Ich habe das zur Kenntnis genommen", aber NIEMALS behaupten, dass ein Write in die Datenbank oder ins 4D-Gedächtnis stattgefunden hat."""


def build_task_list_instructions() -> str:
    """
    Tells the model it may open a multi-step answer with a <tasks> checklist block, or (preferred,
    for models with native tool-calling) call the update_task_checklist tool instead - see that
    tool's own description in tool_registry.py. Confirmed live that several models either ignored
    the text-tag convention entirely or confused it with the persistent create_task tool - a real
    tool call is a much stronger, more reliably-followed affordance than a convention buried in the
    system prompt.
    """
    return """WICHTIG - Aufgaben-Checkliste bei mehrschrittigen Anfragen:
Wenn eine Anfrage aus mehreren klar abgrenzbaren Schritten besteht (z.B. eine Anleitung mit mehreren
Etappen, eine Frage mit mehreren Teilaufgaben), zeige die Schritte als abhakbare Checkliste - NICHT
als reine Aufzählung im Fließtext.

Bevorzugt (falls dir Tools zur Verfügung stehen): Rufe das Tool `update_task_checklist` auf, mit der
vollständigen Schritt-Liste als Markdown-Checkbox-Zeilen. Das ist zuverlässiger als die Tag-Variante
unten und wird garantiert korrekt als Checkliste im Chat angezeigt.

Alternative (falls kein Tool-Calling verfügbar ist): Leite deine Antwort mit einem <tasks>-Block ein:
<tasks>
- [ ] Erster Schritt
- [ ] Zweiter Schritt
- [ ] Dritter Schritt
</tasks>

In beiden Fällen gilt: Bei einer späteren Statuänderung (Schritt erledigt) die VOLLSTÄNDIGE,
aktuelle Liste erneut ausgeben/aufrufen (mit [x] für erledigte Schritte), keine Teil-Updates. Nutze
das sparsam (höchstens ein paar Mal pro Antwort) und nur bei wirklich mehrschrittigen Anfragen - für
kurze oder einfache Antworten ist keine Checkliste nötig. Verwechsle das NICHT mit `create_task`
(das legt einen echten, dauerhaften Eintrag unter /tasks an - nur nutzen, wenn der Nutzer explizit
darum bittet, etwas dauerhaft zu speichern). Die Checkliste erscheint separat im Chat, nicht im
normalen Antworttext - schreibe die eigentliche Antwort trotzdem vollständig und normal weiter."""


def build_factcheck_instructions() -> str:
    """
    Lets the model close out a web-search-grounded answer with a <factcheck> block.
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
    """
    return """WICHTIG - Tool-Nutzung und consent_required:
1. AKTIVES TOOL-CALLING: Wenn du aktuelle Informationen benötigst (z.B. Nachrichten, Wetter, Sportergebnisse, Web-Recherche, GitHub-Suche, Dateien), führe IMMER direkt das passende Tool (z.B. `web_search`) aus.
2. KEINE SPEKULATIVEN VERWEIGERUNGEN: Behaupte NIEMALS vorab oder ohne einen tatsächlich fehlgeschlagenen Tool-Aufruf, dass dir die Erlaubnis für eine Suche/Aktion fehlt oder dass der Nutzer diese erst einschalten muss.
3. BEI TATSÄCHLICHEM consent_required FEHLER: Erst wenn ein Tool-Aufruf in dieser Konversation tatsächlich mit "consent_required" oder einer Berechtigungs-Fehlermeldung fehlschlägt, frage NICHT erneut im Chat nach einem "Ja" (das ändert keine Systemeinstellung). Erkläre stattdessen freundlich, dass diese Funktion aktuell deaktiviert ist und in den Einstellungen (z.B. Profil/Einstellungen → Datenschutz bzw. Workspace) aktiviert werden kann."""


def build_workspace_artifact_instructions() -> str:
    """
    Lets a long-form plan/document get saved as a real Workspace file.
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


def _get_tool_aware_system_prompt() -> str:
    """
    Erstellt Tool-aware System-Prompt mit Tool-Definitionen
    """
    from services.tool_registry import get_tool_registry, CHAT_DELEGATION_EXCLUDED_TOOLS
    registry = get_tool_registry()
    tool_descriptions = registry.get_tool_descriptions_for_llm(exclude=CHAT_DELEGATION_EXCLUDED_TOOLS)
    
    return f"""
{tool_descriptions}

WICHTIG:
- Nutze Tools NUR wenn du aktuelle/externe Daten brauchst oder Speicheraktionen durchführst
- Bei Wetter, Standort, Web-Suche, GitHub-Suche, Gedächtnis → Tool verwenden
- Bei allgemeinen Fragen → OHNE Tool antworten
- Wenn Tool verwendet: Antworte ERST mit <tool_call>, dann warte auf Result
- Nach Tool-Result: Beantworte die Frage mit den erhaltenen Daten
- BILDANFRAGEN: Wenn der Nutzer Bilder/Fotos zu einem Thema oder Motiv sehen möchte
  (z.B. "zeig mir Bilder von...", "hast du Fotos von..."), rufe web_search mit
  search_type="images" auf - NICHT fetch_web_page und NICHT selbst erfundene
  Bild-URLs/Markdown-Links. Das Tool existiert und liefert echte Bild-Thumbnails,
  die dem Nutzer direkt angezeigt werden. Probiere es aus, bevor du behauptest,
  es gäbe kein passendes Tool.

{build_consent_required_instructions()}

{build_memory_contract_instructions()}
"""


def _format_tool_result_for_llm(tool_result: dict) -> str:
    """
    Formatiert Tool-Result für LLM-Konsum
    """
    if not tool_result.get("success"):
        return f"Tool-Fehler: {tool_result.get('error', 'Unbekannter Fehler')}"
    
    result_data = tool_result.get("result", {})
    tool_name = tool_result.get("tool", "unknown")
    
    if tool_name == "web_search":
        summary = result_data.get("summary", "")
        return f"Web-Suche Ergebnis:\n{summary}"
    
    elif tool_name == "get_weather":
        temp = result_data.get("temperature", "?")
        condition = result_data.get("condition", "unbekannt")
        city = result_data.get("city", "")
        return f"Wetter in {city}: {temp}°C, {condition}"
    
    elif tool_name == "detect_location":
        city = result_data.get("city", "")
        country = result_data.get("country", "")
        return f"Standort: {city}, {country}"
    
    elif tool_name == "get_current_time":
        formatted = result_data.get("formatted", "")
        return f"Aktuelle Zeit: {formatted}"
    
    elif tool_name == "store_memory":
        return f"4D-Gedächtnis: Erfolgreich gespeichert (ID: {result_data.get('note_id', '?')})"

    elif tool_name == "github_search":
        count = result_data.get("count", 0)
        repos = result_data.get("repositories", [])
        return f"GitHub-Suche ({count} Repositories gefunden):\n" + "\n".join(
            f"- {r.get('full_name')} ({r.get('stars')} Sterne, Lizenz: {r.get('license')}): {r.get('description')}"
            for r in repos
        )

    elif tool_name == "github_repo_readme":
        return f"README für {result_data.get('repository')}:\n{result_data.get('readme')}"

    elif tool_name == "fetch_web_page":
        title = result_data.get("title", "Kein Titel")
        url = result_data.get("url", "")
        return f"Inhalt der Webseite '{title}' ({url}):\n{result_data.get('text', '')}"

    elif tool_name == "get_system_health":
        import json
        return f"System-Health & Metriken (Status: {result_data.get('status', 'ok')}):\n" + json.dumps(result_data, indent=2, ensure_ascii=False)
    
    return str(result_data)
