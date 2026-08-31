"""
Chat Streaming Router - Server-Sent Events (SSE) für Liara.

Implementiert:
- Streaming Responses via SSE
- Strukturiertes Error-Handling
- Timeout-Management
- Memory-System Integration
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator, List, Dict
import httpx
import requests
import json
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from core.mirko_logger import get_mirko_logger, should_log_for_user
from liara_engine.memory.mood_system import MoodSystem
from liara_engine.actions.intent_detector import get_intent_detector
from liara_engine.actions.action_executor import ActionExecutor
from core.dependencies import require_active_user
from core.database import get_db
from api.models.base_models import User
from services.chat_persistence import persist_assistant_message
from services.redis_service import get_redis_service
from services.memory_integration import store_in_4d_memory, store_message_with_concepts, get_relevant_context
from services.neo4j_service import get_neo4j_service
from services.embedding_service import get_embedding_service
from services.web_search_service import get_web_search_service
from services.location_service import get_location_service
from services.web_safety import get_risk_analyzer, get_content_filter
from services.user_preferences_service import get_user_preferences
from services.prompt_builder import build_temporal_context, build_personality_and_instructions_block, build_diagram_instructions, build_safety_dimensioning_instructions, build_no_fabrication_instructions, build_task_list_instructions, build_factcheck_instructions
from services.session_workspace import build_workspace_manifest, get_context_selected_files, read_session_file
from services.thinking_splitter import ThinkingSplitter
from services.task_splitter import TaskBlockExtractor, parse_task_items
from services.factcheck_splitter import FactCheckBlockExtractor, parse_factcheck_items
from services.ollama_capabilities import model_supports_tools, model_has_thinking_capability
from services.tool_registry import get_tool_registry
from services.tool_executor import get_tool_executor
from services.tool_parser import ToolCall, get_tool_parser
from services.toolcall_splitter import ToolCallBlockExtractor
from services.linep_provider import get_linep_provider, linep_enabled, LinepUnavailableError
from api.routers.chat import _get_tool_aware_system_prompt, _format_tool_result_for_llm
from sqlalchemy.orm import Session
from sqlalchemy import text

router = APIRouter(prefix="/chat", tags=["Chat Streaming"])
mlogger = get_mirko_logger()

# Web search intent list
SEARCH_INTENTS = ['SEARCH_WEATHER', 'SEARCH_WIKI', 'SEARCH_NEWS', 'SEARCH_WEB']

# How many prior messages of the current session to include as real
# conversation turns (not just long-term semantic-memory retrieval) in every
# request to the model - see the comment at its usage for why this exists.
HISTORY_TURNS_LIMIT = 20

# issue #13 item 2: generously above the worst-case generation time (280s
# Ollama read timeout * up to MAX_AGENT_ITERATIONS+1 rounds - see the agent
# loop below), so a crashed/never-released lock can't wedge a session shut
# indefinitely, while a legitimately slow turn never gets its lock yanked
# out from under it mid-generation.
SESSION_GENERATION_LOCK_TTL = 1200  # seconds

# Deliberately much shorter than SESSION_GENERATION_LOCK_TTL above: this is
# how long a NEW request waits trying to acquire an already-held lock, not
# how long a held lock lives. This wait happens before StreamingResponse
# even exists, so the SSE keep-alive wrapper can't send anything during it -
# every second here is a second of dead air Cloudflare's ~100s edge timeout
# is counting down against. Blocking anywhere near the old value (which
# reused SESSION_GENERATION_LOCK_TTL for both) guaranteed a 524 the moment a
# previous turn's lock was still held for any reason (crash, a genuinely
# slow generation, or a cleanup bug like the one this file's keep-alive
# wrapper had). Proceeding lock-less after this timeout just reopens the
# pre-fix race (see _acquire_session_lock's docstring) instead of blocking
# past the point where the connection is doomed anyway.
SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT = 15  # seconds


def _acquire_session_lock(session_id: int):
    """
    Best-effort Redis lock serializing one active /chat/stream generation
    per session (issue #13 item 2). Without this, two concurrent requests
    for the SAME session could both read the same pre-turn history and
    generate independently, letting assistant-completion order diverge
    from user-message order (a slower first request's reply could get
    persisted after a faster second request's).

    A Redis lock rather than an in-process asyncio.Lock (the pattern
    code_exec_router.py uses for issue #8) because gunicorn runs multiple
    worker processes - an in-process lock only serializes requests that
    happen to land on the same worker, not the two that actually race.

    Blocks (via the caller's asyncio.to_thread) for up to
    SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT waiting for a concurrent turn on
    the same session to finish, matching "serialize" rather than "reject"
    semantics - but only briefly, since this wait happens before any bytes
    can be sent to the client (see that constant's own comment).

    Returns None (never raises) if Redis is unavailable or the wait times
    out - matching this file's existing "storage/memory side-effects are
    best-effort, never block the actual reply" posture (see the bare
    `except Exception` around this function's caller). Proceeding without
    the lock just reopens the pre-fix race, it doesn't break chat.
    """
    try:
        lock = get_redis_service().client.lock(
            f"chat_stream_lock:{session_id}",
            timeout=SESSION_GENERATION_LOCK_TTL,
            blocking_timeout=SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT,
        )
        return lock if lock.acquire(blocking=True) else None
    except Exception as e:
        logger.warning(f"Session generation lock unavailable for session {session_id}: {e}")
        return None


def _release_session_lock(lock) -> None:
    if lock is None:
        return
    try:
        lock.release()
    except Exception as e:
        # e.g. LockNotOwnedError if the TTL already expired and someone else
        # acquired it in the meantime - not our lock to release anymore,
        # not an error worth surfacing above debug.
        logger.debug(f"Session generation lock release skipped: {e}")


SSE_KEEPALIVE_INTERVAL = 10.0  # seconds - extra margin under Cloudflare's ~100s edge timeout


async def _with_sse_keepalive(source, interval: float = SSE_KEEPALIVE_INTERVAL):
    """
    Interleaves ': keep-alive\\n\\n' SSE comment lines into `source` whenever
    nothing real has been yielded for `interval` seconds.

    The reverse-proxy chain in front of this app (Cloudflare's free-tier
    edge has a ~100s idle timeout) drops the connection with a 524 if no
    bytes arrive for that long - which happened routinely during the agent
    loop's tool-calling turns: nothing is yielded between the initial
    'metadata' event and the first real 'content' chunk while the model is
    deciding on/executing a tool call, easily exceeding 100s. A comment
    line (anything starting with ':') is part of the SSE spec precisely
    for this - EventSource and this app's own hand-rolled SSE parsers both
    silently ignore any line that isn't 'data: ...', so this is invisible
    to every consumer.

    Keeps the SAME pending __anext__() task across keep-alive ticks rather
    than re-issuing it - a keep-alive tick must not cancel/restart whatever
    the source was actually waiting on.
    """
    it = source.__aiter__()
    pending = None
    try:
        while True:
            if pending is None:
                pending = asyncio.ensure_future(it.__anext__())
            done, _ = await asyncio.wait({pending}, timeout=interval)
            if pending in done:
                task, pending = pending, None
                try:
                    yield task.result()
                except StopAsyncIteration:
                    break
            else:
                yield ": keep-alive\n\n"
    finally:
        # `pending.cancel()` only *requests* cancellation - without awaiting
        # it, `source`'s own `__anext__()` hasn't actually unwound yet, so
        # calling `source.aclose()` right after (as this used to) could hit
        # "aclose(): asynchronous generator is already running" and abort
        # before `source`'s own finally block (which releases the per-session
        # Redis lock, see _release_session_lock above) has run - leaving that
        # lock orphaned for up to SESSION_GENERATION_LOCK_TTL on every client
        # disconnect / Cloudflare 524, observed live as stuck
        # chat_stream_lock:* keys blocking a session's next message. Awaiting
        # the cancellation first lets `source`'s finally complete before we
        # touch it again.
        if pending is not None:
            pending.cancel()
            try:
                await pending
            except (asyncio.CancelledError, StopAsyncIteration, Exception):
                pass
        aclose = getattr(source, "aclose", None)
        if aclose is not None:
            try:
                await aclose()
            except Exception:
                pass


def get_location_context(db: Session, user_id: int) -> Optional[str]:
    """
    Holt User Location aus DB (wenn Consent gegeben)
    
    Returns:
        Location context string oder None
    """
    try:
        location_service = get_location_service()
        location = location_service.get_user_location(db, user_id)
        
        if location and location.get('consent_given'):
            return f"\n\nUser-Standort: {location.get('city')}, {location.get('region')}, {location.get('country')} (Zeitzone: {location.get('timezone')})"
        
        return None
    except Exception:
        return None


async def perform_web_search(query: str, intent: str, user_id: Optional[int] = None, db: Optional[Session] = None) -> tuple[Optional[str], Optional[Dict], Optional[str], Optional[int]]:
    """
    Führt Web-Suche basierend auf Intent aus mit Safety-Check
    
    Args:
        query: User query
        intent: Detected intent (SEARCH_WEATHER, SEARCH_WIKI, etc.)
        user_id: User ID for location fallback
        db: Database session for location lookup
    
    Returns:
        Tuple of (formatted_text, raw_data, search_type, risk_score)
    """
    try:
        logger.info(f"Web search triggered: intent={intent}, query={query}")
        web_search = get_web_search_service()
        risk_analyzer = get_risk_analyzer()
        
        # Default risk score for safe APIs
        risk_score = 0
        
        if intent == 'SEARCH_WEATHER':
            # Weather APIs sind immer sicher (open-meteo.com ist whitelisted)
            risk_score = 5  # Minimal risk
            
            # Extract location from query. City names are reliably capitalized
            # in German, so pull out whatever follows a preposition
            # (in/für/von/bei/nach) rather than trying to strip every possible
            # question phrasing - stripping broke on any wording the regex
            # didn't anticipate (e.g. "aktuelle" in "das aktuelle Wetter").
            import re
            location = ""
            prep_match = re.search(
                r'\b(?:in|für|von|bei|nach)\s+([A-ZÄÖÜ][\wÀ-ÿ\'-]*(?:\s+[A-ZÄÖÜ][\wÀ-ÿ\'-]*)*)',
                query
            )
            if prep_match:
                location = prep_match.group(1).rstrip('?!., ')
            else:
                # Fallback: a capitalized word that isn't just the first word
                # of the sentence (which is capitalized regardless of being a
                # place name, e.g. "Wie ist das Wetter?").
                non_location_words = {'wetter', 'temperatur', 'wie', 'was', 'wird'}
                words = query.split()
                capitalized = [
                    w.strip('?!.,') for i, w in enumerate(words)
                    if i > 0 and w[0].isupper() and len(w.strip('?!.,')) > 1
                    and w.strip('?!.,').lower() not in non_location_words
                ]
                if capitalized:
                    location = capitalized[-1]
            
            # FALLBACK: Wenn keine Location aus Query extrahiert, nutze gespeicherte Location
            if len(location) < 2 and user_id and db:
                location_service = get_location_service()
                user_location = location_service.get_user_location(db, user_id)
                if user_location and user_location.get('city'):
                    location = user_location['city']
                    logger.info(f"Using stored location for user {user_id}: {location}")
                else:
                    # Keine Location verfügbar - LLM soll nachfragen
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
            # Wikipedia ist immer sicher (whitelisted)
            risk_score = 5  # Minimal risk
            
            # Wikipedia search
            logger.info(f"Searching Wikipedia for: {query}")
            result = await web_search.search_wikipedia(query, language='de')
            logger.info(f"Wikipedia result: {result}")
            if 'error' not in result:
                formatted = web_search.format_for_llm(result, 'wikipedia')
                # Analyze Wikipedia URL if present
                if result.get('url'):
                    url_risk = risk_analyzer.analyze_url(result['url'])
                    risk_score = url_risk.get('risk_score', 5)
                return formatted, result, 'wikipedia', risk_score
            else:
                logger.warning(f"Wikipedia error: {result.get('error')}")
        
        elif intent in ['SEARCH_NEWS', 'SEARCH_WEB']:
            # DuckDuckGo Instant Answer
            logger.info(f"Searching DuckDuckGo for: {query}")
            result = await web_search.search_instant_answer(query)
            logger.info(f"DuckDuckGo result: {result}")
            if result.get('abstract') or result.get('answer'):
                formatted = web_search.format_for_llm(result, 'search')
                
                # Analyze result URLs for risk
                url_to_check = result.get('abstract_url') or result.get('url')
                if url_to_check:
                    url_risk = risk_analyzer.analyze_url(url_to_check)
                    risk_score = url_risk.get('risk_score', 30)
                    logger.info(f"Risk analysis for {url_to_check}: score={risk_score}")
                else:
                    risk_score = 15  # DuckDuckGo ohne externe URL ist relativ sicher
                
                return formatted, result, 'general', risk_score
            else:
                logger.warning("No results from DuckDuckGo")
        
        logger.warning(f"No web search results for intent: {intent}")
        return None, None, None, None
    except Exception as e:
        logger.error(f"Web search failed: {e}", exc_info=True)
        return None, None, None, None


def _build_agent_step_label(tool_name: str, arguments: Dict) -> str:
    """
    Human-readable label for an agent_steps SSE item - always built here,
    server-side, from the tool name/arguments actually invoked. Never from
    model text: that's the whole point of this being a separate event from
    the model-authored 'tasks' block (see task_splitter.py's docstring).
    """
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


class StreamChatRequest(BaseModel):
    """Request für Streaming Chat."""
    message: str
    model: Optional[str] = "llama3.2:3b"
    temperature: float = 0.7
    context: Optional[str] = None
    max_tokens: Optional[int] = 2000
    session_id: Optional[int] = None  # NEW: Session ID for history tracking


class ChatError(BaseModel):
    """Strukturiertes Error-Format."""
    error_type: str
    message: str
    timestamp: str
    recoverable: bool
    suggestion: Optional[str] = None


def _flatten_messages_for_linep(messages: List[Dict], include_tools: bool) -> str:
    """Turns the OpenAI-style messages list into a single prompt string for
    LiNeP's GENERATE profile - the wire protocol has no structured
    messages/tools channel, only a plain payload string (see
    linep_provider.py). Tool instructions/results reuse chat.py's existing
    prompt-based tool-calling convention
    (_get_tool_aware_system_prompt/_format_tool_result_for_llm) instead of
    inventing a second one for this transport - see the LiNeP-switch plan.
    """
    parts = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content") or ""
        if role == "system":
            if include_tools:
                content = f"{content}\n\n{_get_tool_aware_system_prompt()}"
            parts.append(content)
        elif role == "tool":
            try:
                tool_result = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                tool_result = {"result": content}
            parts.append(f"Tool-Ergebnis:\n{_format_tool_result_for_llm(tool_result)}")
        elif role == "assistant":
            if content:
                parts.append(f"Assistant: {content}")
        else:  # user
            parts.append(f"User: {content}")
    parts.append("Assistant:")
    return "\n\n".join(parts)


def _append_linep_tool_call(turn_tool_calls: List[Dict], raw_block: str) -> None:
    """Parses a completed <tool_call> block (from ToolCallBlockExtractor,
    tags already stripped) via the existing tool_parser and, if valid,
    appends it to turn_tool_calls in the SAME shape Ollama's native
    tool_calls use ({"function": {"name", "arguments"}}) - so the
    tool-execution loop below needs no transport-specific branching at all.
    Re-wrapping in tags to reuse ToolCallParser.extract_tool_call()'s full
    match/fallback chain rather than duplicating its JSON parsing here.
    """
    parsed = get_tool_parser().extract_tool_call(f"<tool_call>{raw_block}</tool_call>")
    if parsed:
        turn_tool_calls.append({"function": {"name": parsed.tool_name, "arguments": parsed.parameters}})


async def stream_ollama_response(
    message: str,
    model: str = "llama3.2:3b",
    temperature: float = 0.7,
    context: Optional[str] = None,
    web_search_intent: Optional[str] = None,
    web_search_type: Optional[str] = None,
    web_search_data: Optional[Dict] = None,
    web_search_risk_score: Optional[int] = None,
    action_result: Optional[Dict] = None,
    memory_context: Optional[List[Dict]] = None,
    session_id: Optional[int] = None,  # NEW: Session ID for frontend
    user_id: int = None,
    username: Optional[str] = None,
    personality: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    user_message_id: Optional[int] = None,
    memory_enabled: bool = True,
    used_tools: bool = False,
    conversation_history: Optional[List[Dict]] = None,
    session_lock=None,  # issue #13 item 2 - released in this function's finally
) -> AsyncGenerator[str, None]:
    """
    Streame Ollama-Response via Server-Sent Events.

    Yields:
        Server-Sent Event formatted strings
    """
    # Mood-Detection und System-Prompt (per-user, DB-backed)
    mood_system = MoodSystem(user_id)
    interaction_type = MoodSystem.detect_interaction_type(message)
    mood_snapshot = mood_system.get_snapshot()
    mood_modifier = mood_snapshot["modifier"]
    
    # System Prompt mit Mood
    system_prompt = f"""Du bist Liara, eine warmherzige Digitalbegleiterin.

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

1. **Code-Blöcke** mit Syntax-Highlighting:
   ```python
   def beispiel():
       return "Code"
   ```
   Unterstützte Sprachen: python, javascript, php, html, css, sql, bash, json, xml, yaml, etc.

2. **Tabellen** für strukturierte Daten:
   | Spalte 1 | Spalte 2 | Spalte 3 |
   |----------|----------|----------|
   | Wert 1   | Wert 2   | Wert 3   |

3. **Listen** für Aufzählungen:
   - Ungeordnete Listen mit `-`
   - Oder nummerierte Listen mit `1.`

4. **Inline-Code** für kleine Code-Snippets: `variable = wert`

5. **Hervorhebungen**:
   - **Fett** für wichtige Begriffe
   - *Kursiv* für Betonungen
   - > Blockquotes für Zitate

6. **Überschriften** für Struktur:
   ### Abschnitt 1
   #### Unterabschnitt

{build_diagram_instructions()}

{build_safety_dimensioning_instructions()}

{build_no_fabrication_instructions()}

{build_task_list_instructions()}

{build_factcheck_instructions()}

Wähle die Formatierung automatisch basierend auf dem Inhalt:
- Code → Code-Block mit korrekter Sprache
- Vergleiche → Tabelle
- Schritte/Anleitungen → Nummerierte Liste
- Optionen → Ungeordnete Liste
- Technische Begriffe → Inline-Code

WICHTIG - Umgang mit Web-Informationen:
Wenn du aktuelle Informationen (Wetter, Wikipedia, etc.) im Context findest, formuliere sie 
in natürlicher, benutzerfreundlicher Sprache um. Zeige die Informationen klar und strukturiert,
ohne die rohen Datenfelder zu wiederholen. Sei präzise aber freundlich.

WICHTIG - Bei fehlenden Standort-Daten:
Wenn ein User nach Wetter fragt aber KEIN Standort verfügbar ist (weder in der Frage noch gespeichert),
frage freundlich nach: "Für welchen Ort möchtest du die Wettervorhersage wissen?" 
Erkläre kurz, dass du den Standort speichern kannst für zukünftige Anfragen (mit Consent).

{context or ''}
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        *(conversation_history or []),
        {"role": "user", "content": message}
    ]

    # Native Ollama tool-calling (see the "Agent" plan) - only attached when
    # the selected model actually supports it (confirmed live: passing
    # `tools` to a model that doesn't is a hard HTTP 400, not a graceful
    # ignore) and only the tools ToolExecutor's consent stub doesn't
    # unconditionally deny (get_tools_for_ollama filters to privacy_level
    # == "low").
    ollama_tools = None
    if await model_supports_tools(model):
        ollama_tools = get_tool_registry().get_tools_for_ollama()

    # Defined here, not inside the try (issue #7 item 3), and initialized
    # before it so both are always in scope for the finally block below,
    # regardless of where inside the try a disconnect/exception happens.
    full_response_text = ""
    persisted_attempted = False

    def persist_assistant_turn(interrupted: bool = False) -> bool:
        from core.database import SessionLocal
        db_final = SessionLocal()
        try:
            insert_result = db_final.execute(text("""
                INSERT INTO chat_messages
                    (user_id, session_id, role, content, model, mood, timestamp)
                VALUES
                    (:user_id, :session_id, 'assistant', :content, :model, :mood, CURRENT_TIMESTAMP)
                RETURNING id
            """), {
                'user_id': user_id,
                'session_id': session_id,
                'content': full_response_text,
                # Tags interrupted-turn rows distinctly (issue #7 item 3's
                # "completed vs interrupted must be distinguishable") without
                # a schema migration - greppable via the existing model column.
                'model': f"{model} (interrupted)" if interrupted else model,
                'mood': mood_snapshot["mood"]
            })
            db_final.commit()
            assistant_message_id = insert_result.scalar()

            db_final.execute(text("""
                UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = :session_id
            """), {'session_id': session_id})
            db_final.commit()

            if memory_enabled and assistant_message_id:
                try:
                    store_message_with_concepts(
                        user_id=user_id,
                        message_id=assistant_message_id,
                        content=full_response_text,
                        role='assistant',
                        timestamp=datetime.utcnow(),
                        session_id=session_id
                    )
                except Exception as e:
                    logger.error(f"Assistant concept storage failed: {e}")

                if user_message_id:
                    try:
                        get_neo4j_service().create_relationship(
                            source_type='Message', source_id=user_message_id,
                            target_type='Message', target_id=assistant_message_id,
                            relation_type='RESULTED_IN', user_id=user_id,
                            properties={
                                'personality': personality,
                                'mood': mood_snapshot["mood"],
                                'model': model,
                                # Agent's own tool_calls loop can use tools even when the
                                # pre-LLM heuristics (used_tools, computed by the caller
                                # before this generator even runs) found none.
                                'used_tools': used_tools or agent_tool_used,
                                'interrupted': interrupted,
                            }
                        )
                    except Exception as e:
                        logger.error(f"RESULTED_IN relationship failed: {e}")
            return True
        except Exception as e:
            logger.error(f"Assistant message persistence failed: {e}")
            return False
        finally:
            db_final.close()

    try:
        # Sende Metadata Event with session_id
        metadata = {
            'type': 'metadata',
            'model': model,
            'mood': mood_snapshot["mood"]
        }
        if session_id:
            metadata['session_id'] = session_id
        yield f"data: {json.dumps(metadata)}\n\n"
        
        # ✨ Send Memory Context if available
        if memory_context:
            yield f"data: {json.dumps({'type': 'memory_context', 'data': memory_context})}\n\n"
        
        # If action was executed, send result
        if action_result:
            yield f"data: {json.dumps({'type': 'action_result', 'result': action_result})}\n\n"
            
            # If action was successful, send success message and done
            if action_result.get('success'):
                confirmation_text = action_result.get('message', 'Aktion erfolgreich ausgeführt')

                # issue #13 item 3: this shortcut used to return before ever
                # reaching persist_assistant_turn() below, so the user's
                # message (already inserted by the route handler) got saved
                # but this confirmation never did - a reload showed the
                # question with no reply. Assistant-only, not
                # persist_chat_turn() - the user row already exists here.
                #
                # Own short-lived session (issue #13 item 6) rather than the
                # route handler's request-scoped one, which callers of this
                # generator no longer pass in at all.
                if user_id and session_id:
                    from core.database import SessionLocal
                    db_shortcut = SessionLocal()
                    try:
                        persist_assistant_message(db_shortcut, session_id, user_id, confirmation_text)
                    finally:
                        db_shortcut.close()

                yield f"data: {json.dumps({'type': 'content', 'text': confirmation_text})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'action_executed': True})}\n\n"
                return  # Don't call LLM if action was successful
        
        # If web search was triggered, send event
        if web_search_intent:
            yield f"data: {json.dumps({'type': 'web_search', 'intent': web_search_intent, 'search_type': web_search_type})}\n\n"
            
            # Send web search results
            if web_search_data:
                yield f"data: {json.dumps({'type': 'web_results', 'results': web_search_data, 'search_type': web_search_type, 'risk_score': web_search_risk_score or 0})}\n\n"
        
        # Agent tool-calling loop: bounded re-invocation of Ollama so the
        # model can call a real tool and see its actual result, instead of
        # only ever getting one shot per user message. Each iteration is one
        # full Ollama call; the last iteration always omits `tools`, forcing
        # a model that still wants another tool call to instead answer with
        # whatever tool results it already has - this is what guarantees the
        # loop always ends in a real answer rather than cutting off mid-plan.
        MAX_AGENT_ITERATIONS = 3
        agent_tool_used = False
        agent_steps: List[Dict] = []

        # Experimental LiNeP transport switch (see the LiNeP-switch plan) -
        # determined once per request, not per iteration, so a mid-turn
        # tool-calling round-trip doesn't jump transports. Health-gated: a
        # LiNeP outage falls back to the proven Ollama-HTTP path instead of
        # breaking chat outright - this flag (LINEP_ENABLED env var) is off
        # by default.
        transport = "ollama"
        # print(), not logger.info()/warning(): confirmed live that this
        # app's stdlib logging never reaches journalctl at all (no
        # logging.basicConfig anywhere in main.py, root logger has no
        # handler) - print() is unconditionally captured by systemd's
        # journal regardless, needed while diagnosing this experimental
        # switch's transport selection.
        print(f"[LiNeP-Switch] linep_enabled()={linep_enabled()}", flush=True)
        if linep_enabled():
            # LiNeP uses Ollama's /api/generate (RuntimeProfile.GENERATE), not
            # /api/chat - it never gets Ollama's native thinking/content split
            # for reasoning models. Confirmed live: nemotron-3-nano:4b's whole
            # reasoning trace streamed as plain visible content instead of a
            # separate 'thinking' event. Excluding thinking-capable models
            # from LiNeP entirely (falls back to the Ollama-HTTP branch,
            # which handles them correctly) until GENERATE gets an equivalent
            # split or the branch switches to a chat-style profile.
            if await model_has_thinking_capability(model):
                print(f"[LiNeP-Switch] Modell {model} hat thinking-Capability - LiNeP übersprungen (keine native Denkprozess-Trennung über GENERATE)", flush=True)
            elif await get_linep_provider().health():
                transport = "linep"
                print(f"[LiNeP-Switch] Chat-Turn (session={session_id}) läuft über LiNeP-Transport", flush=True)
            else:
                print("[LiNeP-Switch] LINEP_ENABLED, aber linep-server nicht erreichbar - Fallback auf Ollama-HTTP", flush=True)

        for iteration in range(MAX_AGENT_ITERATIONS + 1):
            iteration_tools = ollama_tools if iteration < MAX_AGENT_ITERATIONS else None

            if iteration_tools is None and ollama_tools:
                # Forced final turn after using up the tool budget. Without
                # an explicit nudge, a reasoning model can just keep
                # reasoning about which tool it wishes it could call next
                # and never emit real content before hitting num_predict -
                # observed live with gpt-oss:120b-cloud. Telling it plainly
                # that no more tools are available reliably gets a real
                # answer instead of a silent, content-less turn.
                messages.append({
                    "role": "user",
                    "content": "Es sind keine weiteren Tool-Aufrufe mehr möglich. Bitte beantworte die ursprüngliche Frage jetzt direkt mit den bisher erhaltenen Informationen."
                })

            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": 2000
                }
            }
            if iteration_tools:
                payload["tools"] = iteration_tools

            thinking_splitter = ThinkingSplitter()
            task_extractor = TaskBlockExtractor()
            factcheck_extractor = FactCheckBlockExtractor()
            toolcall_extractor = ToolCallBlockExtractor() if transport == "linep" else None
            turn_content = ""
            turn_tool_calls = []

            if transport == "linep":
                # Experimental: LiNeP's wire protocol has no structured
                # messages/tools channel (see linep_provider.py), so the full
                # conversation + tool instructions are flattened into one
                # prompt string, and a <tool_call> block is parsed back out
                # via the same prompt-based convention chat.py's sync path
                # already teaches models (ToolRegistry.get_tool_descriptions_for_llm
                # + tool_parser.py) - see the LiNeP-switch plan for why no new
                # tool-calling mechanism was invented here.
                prompt_text = _flatten_messages_for_linep(messages, bool(iteration_tools))
                # No try/except here for LinepUnavailableError - it's left
                # to propagate to this function's own outer try/except
                # (below, near the httpx.ConnectError handler), which already
                # emits a proper SSE error event AND releases the session
                # lock in its finally - a local catch-and-return here would
                # silently skip both.
                async for content in get_linep_provider().generate_stream(prompt_text, model, 2000):
                    thinking_part, content_part = thinking_splitter.feed(content)
                    if thinking_part:
                        yield f"data: {json.dumps({'type': 'thinking', 'text': thinking_part})}\n\n"

                    if content_part:
                        content_part, completed_task_blocks = task_extractor.feed(content_part)
                        for raw_block in completed_task_blocks:
                            yield f"data: {json.dumps({'type': 'tasks', 'items': parse_task_items(raw_block)})}\n\n"

                    if content_part:
                        content_part, completed_factcheck_blocks = factcheck_extractor.feed(content_part)
                        for raw_block in completed_factcheck_blocks:
                            yield f"data: {json.dumps({'type': 'factcheck', 'items': parse_factcheck_items(raw_block)})}\n\n"

                    if content_part:
                        content_part, completed_toolcall_blocks = toolcall_extractor.feed(content_part)
                        for raw_block in completed_toolcall_blocks:
                            _append_linep_tool_call(turn_tool_calls, raw_block)

                    if content_part:
                        turn_content += content_part
                        full_response_text += content_part
                        try:
                            if username and should_log_for_user(username):
                                mlogger.log_sse_chunk("content", content=content_part)
                        except:
                            pass  # Logging-Fehler ignorieren
                        yield f"data: {json.dumps({'type': 'content', 'text': content_part})}\n\n"

                # LiNeP has no explicit 'done' chunk - the generator ending
                # above IS done. Same flush/leftover-routing chain as the
                # Ollama branch below (kept separate rather than shared, to
                # avoid touching that already-verified path for this
                # experimental transport - mirror any future change to one
                # into the other), extended with toolcall_extractor.
                leftover_thinking, leftover_content = thinking_splitter.flush()
                if leftover_thinking:
                    yield f"data: {json.dumps({'type': 'thinking', 'text': leftover_thinking})}\n\n"
                if leftover_content:
                    leftover_content, leftover_task_blocks = task_extractor.feed(leftover_content)
                    for raw_block in leftover_task_blocks:
                        yield f"data: {json.dumps({'type': 'tasks', 'items': parse_task_items(raw_block)})}\n\n"
                    if leftover_content:
                        leftover_content, leftover_factcheck_blocks = factcheck_extractor.feed(leftover_content)
                        for raw_block in leftover_factcheck_blocks:
                            yield f"data: {json.dumps({'type': 'factcheck', 'items': parse_factcheck_items(raw_block)})}\n\n"
                        if leftover_content:
                            leftover_content, leftover_toolcall_blocks = toolcall_extractor.feed(leftover_content)
                            for raw_block in leftover_toolcall_blocks:
                                _append_linep_tool_call(turn_tool_calls, raw_block)
                            if leftover_content:
                                turn_content += leftover_content
                                full_response_text += leftover_content
                                yield f"data: {json.dumps({'type': 'content', 'text': leftover_content})}\n\n"

                final_task_content = task_extractor.flush()
                if final_task_content:
                    final_task_content, final_task_factcheck_blocks = factcheck_extractor.feed(final_task_content)
                    for raw_block in final_task_factcheck_blocks:
                        yield f"data: {json.dumps({'type': 'factcheck', 'items': parse_factcheck_items(raw_block)})}\n\n"
                    if final_task_content:
                        final_task_content, final_task_toolcall_blocks = toolcall_extractor.feed(final_task_content)
                        for raw_block in final_task_toolcall_blocks:
                            _append_linep_tool_call(turn_tool_calls, raw_block)
                        if final_task_content:
                            turn_content += final_task_content
                            full_response_text += final_task_content
                            yield f"data: {json.dumps({'type': 'content', 'text': final_task_content})}\n\n"

                final_factcheck_content = factcheck_extractor.flush()
                if final_factcheck_content:
                    final_factcheck_content, final_fc_toolcall_blocks = toolcall_extractor.feed(final_factcheck_content)
                    for raw_block in final_fc_toolcall_blocks:
                        _append_linep_tool_call(turn_tool_calls, raw_block)
                    if final_factcheck_content:
                        turn_content += final_factcheck_content
                        full_response_text += final_factcheck_content
                        yield f"data: {json.dumps({'type': 'content', 'text': final_factcheck_content})}\n\n"

                final_toolcall_content = toolcall_extractor.flush()
                if final_toolcall_content:
                    turn_content += final_toolcall_content
                    full_response_text += final_toolcall_content
                    yield f"data: {json.dumps({'type': 'content', 'text': final_toolcall_content})}\n\n"

                # Fallback for a model that emits the JSON but skips the
                # literal <tool_call> tag (observed live: nemotron-3-nano:4b
                # closed with </tool_call> but never opened it, so the tag
                # extractor above never entered "in_block" and the raw JSON
                # streamed through as visible content). tool_parser's own
                # JSON_TOOL_PATTERN already handles bare "{tool, parameters}"
                # JSON without tags - reused here as a last resort over the
                # full turn so the tool still gets executed even though the
                # raw JSON already reached the client this one time.
                if not turn_tool_calls and iteration_tools:
                    fallback_call = get_tool_parser().extract_tool_call(turn_content)
                    if fallback_call:
                        turn_tool_calls.append({
                            "function": {"name": fallback_call.tool_name, "arguments": fallback_call.parameters}
                        })

            else:

                # Streaming Request zu Ollama via httpx (NO buffering).
                # A flat 90s timeout here used to apply to EVERY read (the gap
                # between successive streamed chunks), not just the initial
                # connect - on CPU-only inference, a long/detailed answer can
                # legitimately have a quiet stretch (large context processing,
                # slow token generation under load) exceeding 90s well before
                # nginx's own 300s proxy_read_timeout on /api/chat/stream would
                # ever be the limiting factor, so long responses were cut off by
                # our own client, not by anything downstream. Connect stays
                # short (Ollama not even accepting a connection should fail
                # fast); read is raised to just under nginx's ceiling.
                ollama_timeout = httpx.Timeout(connect=10.0, read=280.0, write=10.0, pool=10.0)
                async with httpx.AsyncClient(timeout=ollama_timeout) as client:
                    async with client.stream(
                        "POST",
                        "http://localhost:11434/api/chat",
                        json=payload
                    ) as response:
                        response.raise_for_status()

                        # Stream Response Chunks - line by line
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    chunk = json.loads(line)

                                    if "message" in chunk:
                                        # Native tool_calls can arrive on a chunk
                                        # with done:false (confirmed live) -
                                        # accumulate across the whole turn, act
                                        # once done:true arrives below.
                                        if chunk["message"].get("tool_calls"):
                                            turn_tool_calls.extend(chunk["message"]["tool_calls"])

                                        # Ollama separates reasoning-model output into
                                        # its own `message.thinking` field natively
                                        # (confirmed live: deepseek-r1 chunks arrive
                                        # as {"content": "", "thinking": "..."} while
                                        # reasoning, then plain {"content": "..."}
                                        # once it's done - no <think> tags in content
                                        # at all here). thinking_splitter below is a
                                        # fallback for setups where a model inlines
                                        # the tags in content instead.
                                        native_thinking = chunk["message"].get("thinking", "")
                                        if native_thinking:
                                            yield f"data: {json.dumps({'type': 'thinking', 'text': native_thinking})}\n\n"

                                        content = chunk["message"].get("content", "")
                                        if content:
                                            thinking_part, content_part = thinking_splitter.feed(content)

                                            if thinking_part:
                                                yield f"data: {json.dumps({'type': 'thinking', 'text': thinking_part})}\n\n"

                                            if content_part:
                                                # <tasks> blocks (see build_task_list_instructions) are
                                                # stripped out of content_part here and re-emitted as
                                                # their own 'tasks' event instead - a model-authored plan
                                                # display, not a verified execution record (see
                                                # task_splitter.py's module docstring).
                                                content_part, completed_task_blocks = task_extractor.feed(content_part)
                                                for raw_block in completed_task_blocks:
                                                    yield f"data: {json.dumps({'type': 'tasks', 'items': parse_task_items(raw_block)})}\n\n"

                                            if content_part:
                                                # <factcheck> blocks (see build_factcheck_instructions)
                                                # get the same treatment - stripped out and re-emitted
                                                # as their own 'factcheck' event.
                                                content_part, completed_factcheck_blocks = factcheck_extractor.feed(content_part)
                                                for raw_block in completed_factcheck_blocks:
                                                    yield f"data: {json.dumps({'type': 'factcheck', 'items': parse_factcheck_items(raw_block)})}\n\n"

                                            if content_part:
                                                turn_content += content_part
                                                # Updated here, not just once at the end of the
                                                # iteration (issue #7 item 3): a disconnect/exception
                                                # mid-stream would otherwise see full_response_text
                                                # still empty even though several 'content' events
                                                # (this one included) already reached the browser.
                                                full_response_text += content_part
                                                # Mirko Debug Logging
                                                try:
                                                    if username and should_log_for_user(username):
                                                        mlogger.log_sse_chunk("content", content=content_part)
                                                except:
                                                    pass  # Logging-Fehler ignorieren

                                                # SSE Format: data: {json}\n\n
                                                yield f"data: {json.dumps({'type': 'content', 'text': content_part})}\n\n"

                                    # Check if done
                                    if chunk.get("done", False):
                                        # Flush anything the splitter is still holding
                                        # (e.g. a <think> block that never closed).
                                        leftover_thinking, leftover_content = thinking_splitter.flush()
                                        if leftover_thinking:
                                            yield f"data: {json.dumps({'type': 'thinking', 'text': leftover_thinking})}\n\n"
                                        if leftover_content:
                                            leftover_content, leftover_task_blocks = task_extractor.feed(leftover_content)
                                            for raw_block in leftover_task_blocks:
                                                yield f"data: {json.dumps({'type': 'tasks', 'items': parse_task_items(raw_block)})}\n\n"
                                            if leftover_content:
                                                leftover_content, leftover_factcheck_blocks = factcheck_extractor.feed(leftover_content)
                                                for raw_block in leftover_factcheck_blocks:
                                                    yield f"data: {json.dumps({'type': 'factcheck', 'items': parse_factcheck_items(raw_block)})}\n\n"
                                                if leftover_content:
                                                    turn_content += leftover_content
                                                    full_response_text += leftover_content
                                                    yield f"data: {json.dumps({'type': 'content', 'text': leftover_content})}\n\n"
                                        # Anything the extractor itself still had buffered (plain
                                        # trailing content, or an incomplete <tasks>/<factcheck> block
                                        # - the latter discarded per each extractor's flush() contract).
                                        #
                                        # task_extractor's own held-back "safe tail" bytes (its
                                        # defense against a <tasks> tag split across chunks) can
                                        # themselves be the START of a <factcheck> tag - e.g. "<fact"
                                        # held back by task_extractor while "check>...</factcheck>"
                                        # already went out the door separately. Observed live: without
                                        # routing final_task_content through factcheck_extractor too,
                                        # that fragment ("check>") leaked as literal visible text
                                        # instead of ever being recognized as the tag it was part of.
                                        final_task_content = task_extractor.flush()
                                        if final_task_content:
                                            final_task_content, final_task_factcheck_blocks = factcheck_extractor.feed(final_task_content)
                                            for raw_block in final_task_factcheck_blocks:
                                                yield f"data: {json.dumps({'type': 'factcheck', 'items': parse_factcheck_items(raw_block)})}\n\n"
                                            if final_task_content:
                                                turn_content += final_task_content
                                                full_response_text += final_task_content
                                                yield f"data: {json.dumps({'type': 'content', 'text': final_task_content})}\n\n"
                                        final_factcheck_content = factcheck_extractor.flush()
                                        if final_factcheck_content:
                                            turn_content += final_factcheck_content
                                            full_response_text += final_factcheck_content
                                            yield f"data: {json.dumps({'type': 'content', 'text': final_factcheck_content})}\n\n"
                                        break

                                except json.JSONDecodeError:
                                    continue

            if turn_tool_calls and iteration < MAX_AGENT_ITERATIONS:
                agent_tool_used = True
                messages.append({
                    "role": "assistant",
                    "content": turn_content,
                    "tool_calls": turn_tool_calls
                })

                tool_executor = get_tool_executor()
                for tc in turn_tool_calls:
                    fn = tc.get("function", {})
                    tool_name = fn.get("name", "")
                    arguments = fn.get("arguments") or {}

                    agent_steps.append({
                        "id": f"step-{len(agent_steps)}",
                        "label": _build_agent_step_label(tool_name, arguments),
                        "status": "running"
                    })
                    yield f"data: {json.dumps({'type': 'agent_steps', 'items': agent_steps})}\n\n"

                    tool_call = ToolCall(tool_name=tool_name, parameters=arguments, raw_text="", confidence=1.0)
                    try:
                        tool_result = await tool_executor.execute(tool_call, user_id or 0, session_id=session_id)
                    except Exception as e:
                        logger.error(f"Agent tool execution failed: {tool_name}: {e}")
                        tool_result = {"success": False, "error": str(e)}

                    agent_steps[-1]["status"] = "done" if tool_result.get("success") else "error"
                    yield f"data: {json.dumps({'type': 'agent_steps', 'items': agent_steps})}\n\n"

                    # Structured source-card UI (issue #4 phase 2) - the
                    # model already cites sources in its own prose, but this
                    # gives a reliable, structured display independent of
                    # how well it happens to cite in any given answer.
                    # Replaces wholesale on a later web_search("web") call
                    # in the same response, same contract as agent_steps.
                    inner_result = tool_result.get("result") or {}
                    if tool_result.get("success") and inner_result.get("type") == "web":
                        web_source_items = [
                            {
                                "id": f"source-{i}",
                                "title": s.get("title", ""),
                                "url": s.get("url", ""),
                                "domain": s.get("domain", ""),
                                "published_at": s.get("published_at"),
                                "dated": s.get("dated", False)
                            }
                            for i, s in enumerate(inner_result.get("sources", []))
                        ]
                        yield f"data: {json.dumps({'type': 'web_sources', 'items': web_source_items})}\n\n"

                    # Structured proposal card (Workspace Agent-Vorbereitung
                    # v1) - same pattern as web_sources above: the tool result
                    # already tells the model what happened, this gives the
                    # frontend a reliable, structured event to render a "review
                    # in Workspace" card from, independent of chat prose.
                    if tool_name == "workspace_propose_change" and tool_result.get("success") and inner_result.get("proposed"):
                        yield f"data: {json.dumps({'type': 'workspace_proposal', 'proposal_id': inner_result.get('proposal_id'), 'filename': inner_result.get('filename'), 'action': inner_result.get('action'), 'session_id': session_id})}\n\n"

                    # Same structured card as above, package spec standing in
                    # for `filename` - the frontend's WorkspaceProposalsBlock
                    # only ever reads {filename, action}, so no separate event
                    # shape/consumer is needed for this second proposal kind.
                    if tool_name == "workspace_propose_dependency_change" and tool_result.get("success") and inner_result.get("proposed"):
                        yield f"data: {json.dumps({'type': 'workspace_proposal', 'proposal_id': inner_result.get('proposal_id'), 'filename': inner_result.get('package'), 'action': inner_result.get('action'), 'session_id': session_id})}\n\n"

                    tool_message = {"role": "tool", "content": json.dumps(tool_result)}
                    if tc.get("id"):
                        tool_message["tool_call_id"] = tc["id"]
                    messages.append(tool_message)

                # full_response_text no longer needs a bulk merge here (issue
                # #6/#7 item 3): it's now updated incrementally at each
                # 'content' yield above, in this iteration and every earlier
                # one, rather than only once at the end of a completed
                # iteration - which used to mean a mid-stream disconnect saw
                # it still empty even after several 'content' events had
                # already reached the browser.
                continue

            break

        # Mirko Debug Logging
        try:
            if username and should_log_for_user(username):
                mlogger.log_sse_chunk("done", metadata={"mood_updated": True})
        except:
            pass  # Logging-Fehler ignorieren

        # Update Mood nach Antwort
        if user_id is not None:
            mood_system.update_mood(interaction_type, intensity=0.5)

        # Persist Liara's reply - this used to only
        # happen client-side (POST /chat/messages/),
        # which never set user_id and meant this
        # server-side session_id/message_id (used
        # for concept extraction and the RESULTED_IN
        # link below) never matched what the user
        # actually saw.
        if user_id is not None and session_id is not None and full_response_text:
            # Marks that the normal path is about to attempt persistence
            # (issue #7 item 3) - the finally block below only falls back to
            # its own best-effort persist when this never got set, i.e. when
            # a disconnect/exception happened before we even got here.
            persisted_attempted = True

            # 'done' fires immediately, same as before - the UI shouldn't
            # wait on persistence to know the reply finished streaming.
            yield f"data: {json.dumps({'type': 'done', 'mood_updated': True})}\n\n"

            # asyncio.to_thread (not a bare threading.Thread) so this stays
            # awaitable: a reload/navigation right after 'done' could race
            # ahead of the DB commit if persistence were truly fire-and-forget
            # (observed live: a tester reloaded ~immediately after streaming
            # looked finished and briefly worried the reply hadn't saved).
            # 'persisted' gives a caller that cares a real signal to wait for.
            persisted_ok = False
            try:
                persisted_ok = await asyncio.to_thread(persist_assistant_turn)
            except Exception as e:
                logger.error(f"Assistant message persistence task failed: {e}")
            yield f"data: {json.dumps({'type': 'persisted', 'success': persisted_ok})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'done', 'mood_updated': True})}\n\n"

    except httpx.TimeoutException:
        error = ChatError(
            error_type="timeout",
            message="Ollama antwortet nicht (Timeout nach 280s)",
            timestamp=datetime.now().isoformat(),
            recoverable=True,
            suggestion="Versuche es mit einem schnelleren Modell (z.B. llama3.2:1b)"
        )
        yield f"data: {json.dumps({'type': 'error', 'error': error.dict()})}\n\n"
    
    except httpx.ConnectError:
        error = ChatError(
            error_type="connection_error",
            message="Kann nicht mit Ollama verbinden",
            timestamp=datetime.now().isoformat(),
            recoverable=True,
            suggestion="Prüfe ob Ollama läuft: systemctl status ollama"
        )
        yield f"data: {json.dumps({'type': 'error', 'error': error.dict()})}\n\n"

    except LinepUnavailableError as e:
        # Experimental LiNeP transport (LINEP_ENABLED) failed mid-stream -
        # the pre-iteration health check passed but the runtime broke
        # during generation. Surfaced like any other transport failure;
        # session_lock is still released via the finally below either way.
        logger.error(f"LiNeP transport failed mid-stream: {e}")
        error = ChatError(
            error_type="linep_error",
            message="LiNeP-Transport nicht erreichbar (experimentell)",
            timestamp=datetime.now().isoformat(),
            recoverable=True,
            suggestion="Erneut versuchen - fällt bei Bedarf auf Ollama-HTTP zurück"
        )
        yield f"data: {json.dumps({'type': 'error', 'error': error.dict()})}\n\n"

    except httpx.HTTPStatusError as e:
        error = ChatError(
            error_type="http_error",
            message=f"Ollama HTTP Error: {e.response.status_code}",
            timestamp=datetime.now().isoformat(),
            recoverable=False,
            suggestion="Model existiert möglicherweise nicht. Prüfe mit: ollama list"
        )
        yield f"data: {json.dumps({'type': 'error', 'error': error.dict()})}\n\n"
    
    except Exception as e:
        error = ChatError(
            error_type="unknown_error",
            message=f"Unbekannter Fehler: {str(e)}",
            timestamp=datetime.now().isoformat(),
            recoverable=False,
            suggestion="Kontaktiere System-Admin"
        )
        yield f"data: {json.dumps({'type': 'error', 'error': error.dict()})}\n\n"

    finally:
        # issue #13 item 2 - covers every exit from the try above: the
        # action-shortcut early return, the normal completion path, and all
        # four except branches, including a client disconnecting mid-stream
        # (Starlette closes the generator, which runs this finally too).
        _release_session_lock(session_lock)

        # issue #7 item 3: the normal path above only persists the
        # assistant's reply after the whole agent loop finishes. A
        # disconnect or exception at any point before that (timeout,
        # Ollama connection error, client navigating away mid-stream) used
        # to silently drop whatever had already been streamed to and shown
        # in the user's browser - persisted_attempted stays False in every
        # one of those cases, so this is a last-chance best-effort save of
        # that partial reply, distinguishable from a normal turn via the
        # "(interrupted)" model suffix persist_assistant_turn() adds.
        if not persisted_attempted and full_response_text and user_id is not None and session_id is not None:
            try:
                await asyncio.to_thread(persist_assistant_turn, True)
            except Exception as e:
                logger.error(f"Interrupted-turn persistence failed: {e}")


@router.post("/stream")
async def stream_chat(
    request: StreamChatRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """
    🌊 Streaming Chat mit Server-Sent Events + 4D Memory + Web Search Integration.
    
    Returns:
        StreamingResponse mit SSE
        
    Event Types:
        - metadata: Model + Mood Info
        - web_search: Web search triggered
        - content: Text-Chunks
        - done: Response komplett
        - error: Fehler aufgetreten
    """
    # Mirko Debug Logging
    if should_log_for_user(current_user.username):
        mlogger.log_request_start(
            user_id=current_user.id,
            username=current_user.username,
            message=request.message,
            session_id=request.session_id
        )
    
    # Per-User Preferences: Personality, Individuelle Anweisungen, Memory-Opt-in
    user_prefs = get_user_preferences(db, current_user.id)

    # Tag the previous turn's outcome (capture-only, no automatic behavior
    # change yet) using this new message's sentiment as a rough "how did
    # that response land" proxy - only meaningful when continuing an
    # existing conversation, and only when memory is enabled.
    if request.session_id and user_prefs['memory_enabled']:
        try:
            from liara_engine.nlp.sentiment_analyzer import get_sentiment_analyzer
            neo4j_outcome = get_neo4j_service()
            last_assistant_id = neo4j_outcome.get_last_assistant_message_id(current_user.id, request.session_id)
            if last_assistant_id:
                sentiment = get_sentiment_analyzer().analyze_sentiment(request.message)
                neo4j_outcome.tag_message_outcome(
                    current_user.id, last_assistant_id,
                    sentiment.get('category', 'neutral'), sentiment.get('score', 0.0)
                )
        except Exception as e:
            logger.warning(f"Outcome tagging failed: {e}")

    # Store user message in 4D Memory BEFORE streaming response
    session_id = f"chat_{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    mood_system = MoodSystem(current_user.id)
    mood_snapshot = mood_system.get_snapshot()
    current_mood = mood_snapshot["mood"]
    energy = mood_snapshot["intensity"]
    
    # OPTIMIZATION: Run intent detection in parallel (non-blocking)
    message_lower = request.message.lower()
    
    # Fast keyword-based pre-check for web search (skip embedding if not needed)
    search_keywords = ['wetter', 'weather', 'temperatur', 'news', 'nachrichten', 'wikipedia', 'was ist', 'google', 'suche']
    needs_web_search = any(kw in message_lower for kw in search_keywords)
    
    # Fast keyword-based pre-check for actions
    action_keywords = ['erstell', 'create', 'neue task', 'neue notiz', 'neuer termin']
    # "Zeig mir meine Aufgaben" etc. never triggered execute_list_* here at
    # all - only chat.py's non-streaming fallback wired these up, so the
    # default (streaming) path always fell through to the LLM, which could
    # only mention items it happened to have in semantic memory context
    # rather than reliably listing everything.
    list_keywords = ['zeig mir meine', 'zeig meine', 'liste meine', 'welche aufgaben', 'welche termine',
                      'welche notizen', 'meine aufgaben', 'meine tasks', 'meine termine', 'meine notizen']
    needs_action_check = any(kw in message_lower for kw in action_keywords) or any(kw in message_lower for kw in list_keywords)

    # Only run expensive intent detection if keywords match
    search_intent = None
    action_intent = None
    action_result = None

    if needs_web_search:
        embedding_service = get_embedding_service()
        search_intent = embedding_service.detect_intent(request.message)

    if needs_action_check:
        intent_detector = get_intent_detector()
        action_intent = intent_detector.detect(request.message)

    # Execute action if detected
    if action_intent and action_intent.startswith('create_'):
        executor = ActionExecutor(db)

        if action_intent == 'create_event':
            details = intent_detector.extract_event_details(request.message)
            details['user_id'] = current_user.id
            action_result = await executor.execute_create_event(details)
        elif action_intent == 'create_task':
            details = intent_detector.extract_task_details(request.message)
            details['user_id'] = current_user.id
            action_result = await executor.execute_create_task(details)
        elif action_intent == 'create_note':
            details = intent_detector.extract_note_details(request.message)
            details['user_id'] = current_user.id
            action_result = await executor.execute_create_note(details)
    elif action_intent and action_intent.startswith('list_'):
        executor = ActionExecutor(db)

        if action_intent == 'list_tasks':
            action_result = await executor.execute_list_tasks(current_user.id)
        elif action_intent == 'list_events':
            action_result = await executor.execute_list_events(current_user.id)
        elif action_intent == 'list_notes':
            action_result = await executor.execute_list_notes(current_user.id)
    
    # Build enhanced context
    enhanced_context = request.context or ""
    
    # 1. Add Location Context (if consent given)
    location_context = get_location_context(db, current_user.id)
    if location_context:
        enhanced_context += location_context

    # 1b. Session Workspace manifest (files the "Run" button has generated in
    # this session) - a directory on disk isn't "visible to the LLM" by
    # itself, this is what actually surfaces it.
    if request.session_id:
        try:
            workspace_manifest = build_workspace_manifest(current_user.id, request.session_id)
            if workspace_manifest:
                enhanced_context += f"\n\n{workspace_manifest}"
        except Exception as e:
            logger.warning(f"Workspace manifest lookup failed: {e}")

        # 1c. Files the user explicitly marked "add to chat context" in the
        # Workspace tab - inlines actual content (not just name/size like the
        # manifest above), same size/text-type cap read_session_file already
        # enforces. Opt-in per file, never the whole workspace automatically.
        try:
            selected_files = get_context_selected_files(current_user.id, request.session_id)
            for filename in selected_files:
                file_data = read_session_file(current_user.id, request.session_id, filename)
                if file_data.get("found") and file_data.get("content"):
                    enhanced_context += (
                        f"\n\n--- Workspace-Datei (vom Nutzer als Kontext markiert): {filename} ---\n"
                        f"{file_data['content']}"
                    )
        except Exception as e:
            logger.warning(f"Workspace context-selection lookup failed: {e}")

    # ✨ 2. NEU: Add Semantic Context from Neo4j (Top-5 similar concepts)
    # Gated by memory_enabled too, not just memory *creation* below - if a
    # user turns "Erinnerung" off, retrieving old memories into context
    # would still be using memory, just not adding to it.
    relevant_concepts = None
    if user_prefs['memory_enabled']:
        try:
            relevant_concepts = get_relevant_context(
                user_id=current_user.id,
                query_text=request.message,
                limit=5
            )

            if relevant_concepts:
                enhanced_context += "\n\n### Relevante Erinnerungen (basierend auf früheren Gesprächen):\n"
                for concept_item in relevant_concepts:
                    concept = concept_item['concept']
                    similarity = concept_item['similarity']
                    mentions = concept_item['mentions']
                    messages = concept_item['related_messages']

                    enhanced_context += f"\n**Konzept: {concept}** (Similarity: {similarity:.2f}, erwähnt: {mentions}x)\n"
                    for msg in messages[:2]:  # Max 2 Messages pro Concept
                        enhanced_context += f"  - {msg['role']}: {msg['content'][:100]}...\n"

                logger.info(f"Added {len(relevant_concepts)} relevant concepts to context")
        except Exception as e:
            logger.warning(f"Semantic context retrieval failed: {e}")
            # Continue without semantic context
    
    # 3. Check for Web Search Intent
    web_search_result = None
    web_search_data = None
    web_search_type = None
    web_search_risk_score = None
    
    if search_intent in ['SEARCH_WEATHER', 'SEARCH_WIKI', 'SEARCH_NEWS', 'SEARCH_WEB']:
        web_search_result, web_search_data, web_search_type, web_search_risk_score = await perform_web_search(
            request.message,
            search_intent,
            user_id=current_user.id,
            db=db
        )
        
        # Check if location is missing for weather request
        if web_search_data and web_search_data.get('error') == 'no_location':
            enhanced_context += "\n\n### HINWEIS: Kein Standort verfügbar für Wetterabfrage. Bitte den User nach seinem Standort fragen."
        elif web_search_result:
            enhanced_context += f"\n\n### Aktuelle Web-Information:\n{web_search_result}"
            
            # Store search in history if user has consent
            try:
                privacy_check = db.execute(
                    text("SELECT store_search_history FROM user_privacy_settings WHERE user_id = :user_id"),
                    {'user_id': current_user.id}
                ).first()
                
                if privacy_check and privacy_check.store_search_history:
                    # Store search with consent
                    result_summary = web_search_result[:500] if len(web_search_result) > 500 else web_search_result
                    db.execute(text("""
                        INSERT INTO user_search_history 
                            (user_id, query, search_type, result_summary, stored_with_consent, can_be_used_for_training, searched_at)
                        VALUES 
                            (:user_id, :query, :search_type, :result_summary, true, false, CURRENT_TIMESTAMP)
                    """), {
                        'user_id': current_user.id,
                        'query': request.message,
                        'search_type': web_search_type,
                        'result_summary': result_summary
                    })
                    db.commit()
                    logger.info(f"Search history stored for user {current_user.id}")
            except Exception as e:
                logger.error(f"Failed to store search history: {e}")
                # Continue even if storage fails
    
    # Safe defaults in case the storage block below fails before setting
    # these - stream_ollama_response() must never NameError on them.
    message_id = None
    used_tools = False
    conversation_history = []
    # issue #13 item 2: only ever acquired for an EXISTING session (below) -
    # a brand-new session's very first message has no prior history/turn
    # for a second request to race against, since nothing else can
    # reference a session_id that doesn't exist yet.
    session_lock = None

    try:
        # Get or create session_id
        if not request.session_id:
            # Create new session with title from first message
            title = request.message[:50] + "..." if len(request.message) > 50 else request.message
            session_result = db.execute(text("""
                INSERT INTO chat_sessions (user_id, title, created_at, updated_at)
                VALUES (:user_id, :title, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """), {'user_id': current_user.id, 'title': title})
            db.commit()
            session_id = session_result.scalar()
        else:
            # Verify session belongs to user
            session_check = db.execute(text("""
                SELECT id FROM chat_sessions 
                WHERE id = :session_id AND user_id = :user_id
            """), {'session_id': request.session_id, 'user_id': current_user.id}).first()
            
            if not session_check:
                raise HTTPException(status_code=404, detail="Session not found or access denied")

            session_id = request.session_id

            # issue #13 item 2: serialize this session's turns from here -
            # the history read immediately below through the assistant
            # persistence at the end of stream_ollama_response() - before a
            # second concurrent request for this same session can read the
            # same pre-turn history this one is about to.
            session_lock = await asyncio.to_thread(_acquire_session_lock, session_id)

        # Short-term conversational history: without this, every request sent
        # only (system prompt + the single current message) with no prior
        # turns at all - the model had zero visibility into anything said
        # earlier in the same session beyond whatever the *long-term* Neo4j
        # semantic-similarity search (min_similarity=0.6) happened to surface,
        # which a short/generic follow-up often doesn't clear. Confirmed live:
        # telling Liara a custom nickname, then one message later asking for
        # it back, got answered with "Liara" instead of the actual name.
        history_rows = db.execute(text("""
            SELECT role, content FROM chat_messages
            WHERE session_id = :session_id
            ORDER BY timestamp DESC, id DESC
            LIMIT :limit
        """), {'session_id': session_id, 'limit': HISTORY_TURNS_LIMIT}).all()
        conversation_history = [
            {'role': row.role, 'content': row.content} for row in reversed(history_rows)
        ]

        # Create message record in PostgreSQL
        message_insert = text("""
            INSERT INTO chat_messages 
                (user_id, session_id, role, content, model, mood, timestamp)
            VALUES 
                (:user_id, :session_id, 'user', :content, :model, :mood, CURRENT_TIMESTAMP)
            RETURNING id
        """)
        
        result = db.execute(message_insert, {
            'user_id': current_user.id,
            'session_id': session_id,
            'content': request.message,
            'model': request.model,
            'mood': current_mood
        })
        db.commit()
        message_id = result.scalar()
        
        # Update session timestamp
        db.execute(text("""
            UPDATE chat_sessions 
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = :session_id
        """), {'session_id': session_id})
        db.commit()
        
        logger.info(f"Created message {message_id} for user {current_user.id} in session {session_id}")

        # Memory creation opt-in/out (Präferenzen > Erinnerung): tool-assisted
        # messages (web search or an executed action) are separately gated by
        # tool_memory_enabled, since that content is more likely to include
        # third-party/external data the user may not want remembered.
        used_tools = bool(web_search_result) or bool(action_result)
        should_store_memory = user_prefs['memory_enabled'] and (not used_tools or user_prefs['tool_memory_enabled'])

        if should_store_memory:
            # ✨ NEU: Store in Neo4j with auto-concept extraction (sync für Testing)
            try:
                store_message_with_concepts(
                    user_id=current_user.id,
                    message_id=message_id,
                    content=request.message,
                    role='user',
                    timestamp=datetime.utcnow(),
                    session_id=session_id
                )
                logger.info(f"Stored concepts for message {message_id}")
            except Exception as e:
                logger.error(f"Concept extraction failed: {e}")

            # Store in 4D Memory ASYNC (non-blocking) - don't wait for completion
            import threading

            def store_memory_async():
                """Async Memory Storage mit eigener DB-Session"""
                from core.database import SessionLocal
                db_async = SessionLocal()
                try:
                    store_in_4d_memory(
                        db=db_async,
                        user_id=current_user.id,
                        content_type='message',
                        content_id=message_id,
                        content_text=request.message,
                        session_id=session_id,
                        mood=current_mood,
                        energy_level=energy,
                        additional_context={
                            'model': request.model,
                            'temperature': request.temperature,
                            'search_intent': search_intent,
                            'action_intent': action_intent,
                            'web_search_used': web_search_result is not None
                        }
                    )
                except Exception as e:
                    logger.error(f"4D Memory async storage failed: {e}")
                finally:
                    db_async.close()

            threading.Thread(target=store_memory_async, daemon=True).start()

    except HTTPException:
        # The session-ownership check above deliberately raises 404 for a
        # session the user doesn't own - without this, the bare except
        # below swallowed it as a mere "storage failed" log line and chat
        # continued anyway, so a request for someone else's session_id
        # would silently degrade instead of actually failing.
        raise
    except Exception as e:
        logger.error(f"Message storage failed: {e}")
        # Continue with chat even if message storage fails
    
    return StreamingResponse(
        _with_sse_keepalive(stream_ollama_response(
            message=request.message,
            model=request.model,
            temperature=request.temperature,
            context=enhanced_context,
            web_search_intent=search_intent if web_search_result else None,
            web_search_type=web_search_type,
            web_search_data=web_search_data,
            web_search_risk_score=web_search_risk_score,
            action_result=action_result,
            memory_context=relevant_concepts,
            conversation_history=conversation_history,
            session_id=session_id,  # NEW: Send session_id to frontend
            user_id=current_user.id,
            username=current_user.username,
            personality=user_prefs['personality'],
            custom_instructions=user_prefs['custom_instructions'],
            user_message_id=message_id,
            memory_enabled=user_prefs['memory_enabled'],
            used_tools=used_tools,
            session_lock=session_lock
        )),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/stream/test")
async def test_stream():
    """Test SSE Streaming."""
    async def test_generator():
        for i in range(5):
            yield f"data: {json.dumps({'count': i, 'message': f'Test {i}'})}\n\n"
            await asyncio.sleep(0.5)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        test_generator(),
        media_type="text/event-stream"
    )


@router.get("/health")
async def chat_health():
    """
    Health-Check für Chat-System.
    
    Returns:
        Status von Ollama + Models + Mood-System + Memory
    """
    # Check Ollama
    ollama_available = False
    model_count = 0
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            ollama_available = True
            model_count = len(response.json().get("models", []))
    except:
        pass
    
    # Check Mood System (system-wide count only - mood itself is per-user now)
    from core.database import SessionLocal
    from api.models.mood_state import MoodHistoryEntry
    db = SessionLocal()
    try:
        mood_history_total = db.query(MoodHistoryEntry).count()
    finally:
        db.close()

    return {
        "status": "healthy" if ollama_available else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "ollama": {
                "available": ollama_available,
                "models_loaded": model_count
            },
            "mood_system": {
                "available": True,
                "scope": "per_user",
                "history_entries_total": mood_history_total
            }
        },
        "capabilities": {
            "streaming": True,
            "error_recovery": True,
            "mood_detection": True
        }
    }


# ============================================
# GUEST STREAMING ENDPOINT
# ============================================

class GuestStreamRequest(BaseModel):
    message: str

async def stream_guest_response(
    query: str,
    model: str = "llama3.2:1b"
) -> AsyncGenerator[str, None]:
    """
    Streaming Response für Guest-Modus.
    Unterstützt Web-Search für einfache Anfragen.
    """
    try:
        # Detect intent for web search
        embedding_service = get_embedding_service()
        intent = embedding_service.detect_intent(query)
        
        # Web search if needed
        web_search_result = None
        web_search_data = None
        web_search_type = None
        
        if intent in SEARCH_INTENTS:
            yield f"data: {json.dumps({'type': 'web_search', 'intent': intent})}\n\n"
            web_search_result, web_search_data, web_search_type, _ = await perform_web_search(query, intent)
            
            if web_search_data:
                yield f"data: {json.dumps({'type': 'web_results', 'results': web_search_data, 'search_type': web_search_type})}\n\n"
        
        # Einfacher System-Prompt für Gäste
        guest_prompt = """Du bist Liara, eine freundliche Digitalbegleiterin.
        
Du sprichst mit einem Gast. Sei hilfsbereit und kurz (max 150 Wörter).
Bei Fragen zu Features erkläre, dass erweiterte Funktionen nur für registrierte Nutzer verfügbar sind."""

        # Build context
        context = guest_prompt
        if web_search_result:
            context += f"\n\nAktuelle Information:\n{web_search_result}"
        
        # Stream Ollama response
        ollama_url = "http://localhost:11434/api/generate"
        payload = {
            "model": model,
            "prompt": f"{context}\n\nUser: {query}\nLiara:",
            "stream": True,
            "options": {
                "temperature": 0.7,
                "num_predict": 300  # Kürzere Antworten für Gäste
            }
        }
        
        response = requests.post(ollama_url, json=payload, stream=True, timeout=60)
        response.raise_for_status()

        guest_thinking_splitter = ThinkingSplitter()

        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    if chunk.get('done'):
                        leftover_thinking, leftover_content = guest_thinking_splitter.flush()
                        if leftover_thinking:
                            yield f"data: {json.dumps({'type': 'thinking', 'text': leftover_thinking})}\n\n"
                        if leftover_content:
                            yield f"data: {json.dumps({'type': 'content', 'text': leftover_content})}\n\n"
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        break

                    native_thinking = chunk.get('thinking', '')
                    if native_thinking:
                        yield f"data: {json.dumps({'type': 'thinking', 'text': native_thinking})}\n\n"

                    content = chunk.get('response', '')
                    if content:
                        thinking_part, content_part = guest_thinking_splitter.feed(content)
                        if thinking_part:
                            yield f"data: {json.dumps({'type': 'thinking', 'text': thinking_part})}\n\n"
                        if content_part:
                            yield f"data: {json.dumps({'type': 'content', 'text': content_part})}\n\n"

                except json.JSONDecodeError:
                    continue
                    
    except requests.Timeout:
        yield f"data: {json.dumps({'type': 'error', 'error': 'Timeout - Anfrage dauerte zu lange'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


@router.post("/guest/stream")
async def guest_stream_chat(request: GuestStreamRequest):
    """
    🌙 Guest-Chat mit SSE Streaming.
    
    Schnellere Antworten durch:
    - Kleines Modell (1b)
    - Kürzere Antworten (max 300 tokens)
    - Web-Search Support für Wetter, Wikipedia, etc.
    
    Limitierungen:
    - Max 500 Zeichen Input
    - Kein Memory über Session hinaus
    - Vereinfachter System-Prompt
    """
    message = request.message.strip()
    
    if not message:
        raise HTTPException(status_code=400, detail="Nachricht darf nicht leer sein")
    
    if len(message) > 500:
        raise HTTPException(
            status_code=400,
            detail=f"Nachricht zu lang. Maximum: 500 Zeichen. Du hast {len(message)} Zeichen."
        )
    
    return StreamingResponse(
        _with_sse_keepalive(stream_guest_response(message)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


