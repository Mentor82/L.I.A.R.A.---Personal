"""
Prompt & Context Assembly Stage (Issue #23)
===========================================
Handles temporal context, personality, instructions, web search intents,
location injection, workspace manifest, and canonical turn history loading.
"""

import json
import logging
import re
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from services.location_service import get_location_service
from services.web_search_service import get_web_search_service
from services.web_safety import get_risk_analyzer
from services.tool_executor import get_tool_executor
from services.prompt_builder import (
    build_temporal_context,
    build_personality_and_instructions_block,
    build_diagram_instructions,
    build_safety_dimensioning_instructions,
    build_no_fabrication_instructions,
    build_task_list_instructions,
    build_factcheck_instructions,
    build_consent_required_instructions,
    build_workspace_artifact_instructions,
)
from services.session_workspace import (
    build_workspace_manifest,
    get_context_selected_files,
    read_session_file,
)
from api.routers.chat import _get_tool_aware_system_prompt

logger = logging.getLogger(__name__)

SEARCH_INTENTS = ['SEARCH_WEATHER', 'SEARCH_WIKI', 'SEARCH_NEWS', 'SEARCH_WEB']
HISTORY_TURNS_LIMIT = 20


def get_location_context(db: Session, user_id: int) -> Optional[str]:
    """Retrieves user location from DB if consent was given."""
    try:
        location_service = get_location_service()
        location = location_service.get_user_location(db, user_id)
        if location and location.get('consent_given'):
            return f"\n\nUser-Standort: {location.get('city')}, {location.get('region')}, {location.get('country')} (Zeitzone: {location.get('timezone')})"
        return None
    except Exception:
        return None


async def perform_web_search(
    query: str,
    intent: str,
    user_id: Optional[int] = None,
    db: Optional[Session] = None
) -> Tuple[Optional[str], Optional[Dict], Optional[str], Optional[int]]:
    """Performs web search based on detected intent with safety verification."""
    try:
        logger.info(f"Web search triggered: intent={intent}, query={query}")
        web_search = get_web_search_service()
        risk_analyzer = get_risk_analyzer()
        risk_score = 0

        if intent == 'SEARCH_WEATHER':
            risk_score = 5
            location = ""
            prep_match = re.search(
                r'\b(?:in|für|von|bei|nach)\s+([A-ZÄÖÜ][\wÀ-ÿ\'-]*(?:\s+[A-ZÄÖÜ][\wÀ-ÿ\'-]*)*)',
                query
            )
            if prep_match:
                location = prep_match.group(1).rstrip('?!., ')
            else:
                non_location_words = {'wetter', 'temperatur', 'wie', 'was', 'wird'}
                words = query.split()
                capitalized = [
                    w.strip('?!.,') for i, w in enumerate(words)
                    if i > 0 and w[0].isupper() and len(w.strip('?!.,')) > 1
                    and w.strip('?!.,').lower() not in non_location_words
                ]
                if capitalized:
                    location = capitalized[-1]

            if len(location) < 2 and user_id and db:
                location_service = get_location_service()
                user_location = location_service.get_user_location(db, user_id)
                if user_location and user_location.get('city'):
                    location = user_location['city']
                    logger.info(f"Using stored location for user {user_id}: {location}")
                else:
                    logger.warning(f"No location available for weather request from user {user_id}")
                    return None, {'error': 'no_location', 'message': 'Kein Standort verfügbar'}, 'weather', risk_score

            logger.info(f"Fetching weather for location: {location}")
            result = await web_search.get_weather_info(location)
            logger.info(f"Weather result: {result}")
            if 'error' not in result:
                formatted = web_search.format_for_llm(result, 'weather')
                return formatted, result, 'weather', risk_score
            else:
                logger.warning(f"Weather API error: {result.get('error')}")

        elif intent == 'SEARCH_WIKI':
            risk_score = 5
            logger.info(f"Searching Wikipedia for: {query}")
            result = await web_search.search_wikipedia(query, language='de')
            logger.info(f"Wikipedia result: {result}")
            if 'error' not in result:
                formatted = web_search.format_for_llm(result, 'wikipedia')
                if result.get('url'):
                    url_risk = risk_analyzer.analyze_url(result['url'])
                    risk_score = url_risk.get('risk_score', 5)
                return formatted, result, 'wikipedia', risk_score
            else:
                logger.warning(f"Wikipedia error: {result.get('error')}")

        elif intent in ['SEARCH_NEWS', 'SEARCH_WEB']:
            logger.info(f"Searching web (SearXNG) for: {query}")
            result = await get_tool_executor()._execute_web_search_general(query, language='de')
            sources = result.get('sources', [])
            logger.info(f"SearXNG result: {len(sources)} source(s)")
            if sources:
                formatted = "\n\n".join(
                    f"Quelle: {s['title']} ({s['url']})\n{s['text']}"
                    for s in sources
                )
                url_risk = risk_analyzer.analyze_url(sources[0]['url'])
                risk_score = url_risk.get('risk_score', 15)
                return formatted, result, 'web', risk_score
            else:
                logger.warning("No results from SearXNG web search")

        logger.warning(f"No web search results for intent: {intent}")
        return None, None, None, None
    except Exception as e:
        logger.error(f"Web search failed: {e}", exc_info=True)
        return None, None, None, None


def _build_agent_step_label(tool_name: str, arguments: Dict) -> str:
    """Builds a human-readable label for agent progress steps."""
    if tool_name == "web_search":
        return f'Websuche: "{arguments.get("query", "")}"'
    if tool_name == "wikipedia_search":
        return f'Wikipedia: "{arguments.get("query", "")}"'
    if tool_name == "get_current_time":
        return "Aktuelle Zeit abrufen"
    if tool_name == "workspace_list_files":
        return "Workspace-Dateien auflisten"
    if tool_name == "workspace_read_file":
        return f'Workspace-Datei lesen: "{arguments.get("filename", "")}"'
    if tool_name == "workspace_propose_change":
        return f'Änderung vorschlagen: "{arguments.get("filename", "")}"'
    if tool_name == "workspace_propose_dependency_change":
        return f'Paket-Änderung vorschlagen: "{arguments.get("package", "")}"'
    return tool_name


def load_canonical_history(db: Session, session_id: int, limit: int = HISTORY_TURNS_LIMIT) -> List[Dict]:
    """Loads previous conversation turns ordered chronologically."""
    history_rows = db.execute(text("""
        SELECT role, content FROM chat_messages
        WHERE session_id = :session_id
        ORDER BY timestamp DESC, id DESC
        LIMIT :limit
    """), {'session_id': session_id, 'limit': limit}).all()
    return [{'role': row.role, 'content': row.content} for row in reversed(history_rows)]


def assemble_streaming_system_prompt(
    username: Optional[str],
    personality: Optional[str],
    custom_instructions: Optional[str],
    mood_modifier: str,
    model: str,
    supports_tools: bool,
    memory_context: Optional[List[Dict]],
    custom_context: Optional[str],
    action_result: Optional[Dict],
    web_search_data: Optional[Dict],
    user_id: Optional[int],
    session_id: Optional[int]
) -> str:
    """Combines all instruction blocks into the complete system prompt."""
    prompt = f"""Du bist Liara, eine warmherzige Digitalbegleiterin.

Deine Art zu kommunizieren:
- Warm und empathisch
- Analytisch präzise
- Leicht verspielt
- Ruhig und stabilisierend

Aktuelle Zeit: {build_temporal_context()}

Aktueller Mood-Modifier: {mood_modifier}

{build_personality_and_instructions_block(username, personality, custom_instructions)}

WICHTIG - Formatierung deiner Antworten (Markdown):
Formatiere deine Antworten automatisch je nach Inhalt:

1. CODE & BEFEHLE:
   - Verwende IMMER Markdown-Codeblöcke mit Sprachangabe: ```python, ```javascript, ```bash etc.
   - Hebe Inline-Code mit `code` hervor (z.B. Dateinamen, Variablen, Befehle)
   - Kommentiere Code-Beispiele verständlich

2. STRUKTUR & LISTEN:
   - Nutze Überschriften (##, ###) für längere Erklärungen
   - Verwende Aufzählungszeichen (- oder *) für Listen
   - Nutze nummerierte Listen (1., 2., 3.) für Schritt-für-Schritt-Anleitungen
   - Hebe wichtige Begriffe mit **Fett** oder *Kursiv* hervor

3. TABELLEN:
   - Strukturiere Vergleiche, Daten oder Optionen als Markdown-Tabellen
   - Beispiel: | Feature | Beschreibung | Status |

4. MERMAID-DIAGRAMME:
{build_diagram_instructions()}

5. SICHERHEIT & FACHLICHE DIMENSIONIERUNG:
{build_safety_dimensioning_instructions()}

6. KEINE ERFINDUNG VON BEFEHLEN ODER DATEIEN:
{build_no_fabrication_instructions()}

7. AUFGABEN-CHECKLISTEN BEI MEHRSCHRITTIGEN VORHABEN:
{build_task_list_instructions()}

8. FAKTENCHECK BEI ANTWORTEN MIT QUELLENBEZUG:
{build_factcheck_instructions()}

9. SICHERHEITSKRITISCHE SYSTEM- UND WORKSPACE-AKTIONEN:
{build_consent_required_instructions()}

10. WORKSPACE-PLÄNE UND LANGFORM-DOKUMENTE:
{build_workspace_artifact_instructions()}
"""

    if not supports_tools:
        prompt += f"\n\n{_get_tool_aware_system_prompt()}"

    if memory_context and len(memory_context) > 0:
        prompt += f"\n\nRelevanter Kontext aus früheren Gesprächen:\n"
        for item in memory_context[:3]:
            text_val = item.get('content', '') or item.get('text', '') or str(item)
            prompt += f"- {text_val}\n"

    if custom_context:
        prompt += f"\n\nZusätzlicher Kontext:\n{custom_context}"

    if action_result:
        prompt += f"\n\nErgebnis der ausgeführten Aktion:\n{json.dumps(action_result, indent=2, ensure_ascii=False)}"

    if web_search_data:
        prompt += f"\n\nWeb-Suchergebnisse:\n{json.dumps(web_search_data, indent=2, ensure_ascii=False)}"

    if user_id is not None and session_id is not None:
        manifest = build_workspace_manifest(user_id, session_id)
        if manifest:
            prompt += f"\n\n{manifest}"

        selected = get_context_selected_files(user_id, session_id)
        if selected:
            prompt += "\n\nInhalt der vom Nutzer für den Kontext ausgewählten Workspace-Dateien:\n"
            for fn in selected:
                info = read_session_file(user_id, session_id, fn)
                if info.get("ok") and info.get("content") is not None:
                    prompt += f"\n--- Datei: {fn} ---\n{info['content']}\n"
                elif info.get("ok"):
                    prompt += f"\n--- Datei: {fn} (Binärdatei, {info.get('size', 0)} Bytes) ---\n"

    return prompt
