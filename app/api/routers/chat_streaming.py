"""
Chat Streaming Router - Server-Sent Events (SSE) für Liara (Issue #23).
========================================================================
Declarative router orchestrating the chat streaming stages:
- LockGuard (Redis leasing, watchdog, zero-lag race cancellation, keepalives)
- PromptStage (personality, temporal, memory context, search intent, workspace manifest)
- GeneratorStage (LiNeP & Ollama-HTTP streaming, splitter pipeline, tool execution)
- PersistenceStage (atomic turn saving under lock, 4D memory, concept graph relations)
"""

import json
import logging
from datetime import datetime
from typing import Optional, AsyncGenerator, List, Dict

import requests
import httpx
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import get_db, SessionLocal
from core.dependencies import require_active_user
from core.mirko_logger import get_mirko_logger, should_log_for_user
from api.models.base_models import User
from api.models.mood_state import MoodHistoryEntry
from liara_engine.actions.action_executor import ActionExecutor
from liara_engine.actions.intent_detector import get_intent_detector
from liara_engine.nlp.sentiment_analyzer import get_sentiment_analyzer
from liara_engine.memory.mood_system import MoodSystem
from services.config_service import get_config_service
from services.embedding_service import get_embedding_service
from services.memory_integration import get_relevant_context, invalidate_message
from services.memory_verification import detect_correction_signal
from services.neo4j_service import get_neo4j_service
from services.ollama_capabilities import get_model_num_predict
from services.redis_service import get_redis_service
from services.thinking_splitter import ThinkingSplitter
from services.user_preferences_service import get_user_preferences

# Modular Chat Stream Stages (Issue #23)
from services.chat_stream.lock_guard import (
    SessionLockError,
    SessionLockTimeoutError,
    SessionLockUnavailableError,
    SessionLockLostError,
    _acquire_session_lock,
    _renew_session_lock,
    _session_lock_watchdog,
    _release_session_lock,
    _race_with_lock_lost,
    _with_lock_lost_guard,
    _with_sse_keepalive,
    SESSION_GENERATION_LOCK_TTL,
    SESSION_GENERATION_LOCK_RENEW_INTERVAL,
    SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT,
    SSE_KEEPALIVE_INTERVAL,
)
from services.chat_stream.prompt_stage import (
    SEARCH_INTENTS,
    HISTORY_TURNS_LIMIT,
    get_location_context,
    perform_web_search,
    _build_agent_step_label,
)
from services.chat_stream.generator_stage import stream_ollama_response

logger = logging.getLogger(__name__)
mlogger = get_mirko_logger()
router = APIRouter(prefix="/chat", tags=["Chat Streaming"])


class StreamChatRequest(BaseModel):
    """Request für Streaming Chat."""
    message: str
    model: Optional[str] = "llama3.2:3b"
    temperature: float = 0.7
    context: Optional[str] = None
    max_tokens: Optional[int] = 2000
    session_id: Optional[int] = None
    images: Optional[List[str]] = None


class GuestStreamRequest(BaseModel):
    """Request für Guest-Streaming."""
    message: str


class ChatError(BaseModel):
    """Strukturiertes Error-Format."""
    error_type: str
    message: str
    timestamp: str
    recoverable: bool
    suggestion: Optional[str] = None


@router.post("/stream")
async def stream_chat(
    request: StreamChatRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """🌊 Streaming Chat mit Server-Sent Events + 4D Memory + Tool Integration."""
    if should_log_for_user(current_user.username):
        mlogger.log_request_start(
            user_id=current_user.id,
            username=current_user.username,
            message=request.message,
            session_id=request.session_id
        )

    user_prefs = get_user_preferences(db, current_user.id)

    if request.session_id and user_prefs['memory_enabled']:
        try:
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

    message_lower = request.message.lower()
    search_keywords = ['wetter', 'weather', 'temperatur', 'news', 'nachrichten', 'wikipedia', 'was ist', 'google', 'suche']
    needs_web_search = any(kw in message_lower for kw in search_keywords)

    action_keywords = [
        'erstell', 'create', 'neue task', 'neue aufgabe', 'neue notiz', 'neuer termin', 'neues event',
        'erinner', 'reminder', 'merk dir', 'merke dir', 'merk es', 'speicher', 'schreib auf', 'trag ein',
        'trage ein', 'notier', 'plan', 'setz', 'to-do', 'todo'
    ]
    list_keywords = [
        'zeig mir meine', 'zeig meine', 'liste meine', 'welche aufgaben', 'welche termine',
        'welche notizen', 'meine aufgaben', 'meine tasks', 'meine termine', 'meine notizen',
        'meine erinnerungen', 'welche erinnerungen', 'was steht an', 'was habe ich vor',
        'was ist zu tun', 'was muss ich', 'heute an', 'morgen an'
    ]
    needs_action_check = any(kw in message_lower for kw in action_keywords) or any(kw in message_lower for kw in list_keywords)

    search_intent = None
    action_intent = None
    action_result = None

    if needs_web_search:
        search_intent = get_embedding_service().detect_intent(request.message)

    if needs_action_check:
        intent_detector = get_intent_detector()
        action_intent = intent_detector.detect(request.message)

    if action_intent:
        executor = ActionExecutor(db)
        if action_intent.startswith('create_'):
            intent_detector = get_intent_detector()
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
                details['session_id'] = request.session_id
                action_result = await executor.execute_create_note(details)
        elif action_intent.startswith('list_'):
            if action_intent == 'list_tasks':
                action_result = await executor.execute_list_tasks(current_user.id)
            elif action_intent == 'list_events':
                action_result = await executor.execute_list_events(current_user.id)
            elif action_intent == 'list_notes':
                action_result = await executor.execute_list_notes(current_user.id)

    enhanced_context = request.context or ""
    location_context = get_location_context(db, current_user.id)
    if location_context:
        enhanced_context += location_context

    relevant_concepts = None
    if user_prefs['memory_enabled']:
        try:
            relevant_concepts = get_relevant_context(user_id=current_user.id, query_text=request.message, limit=5)

            # Trigger b (siehe memory_verification.py): der Nutzer widerspricht
            # gerade einer früheren Erinnerung, die semantisch zu seiner neuen
            # Nachricht passt. Kein Blind-Overwrite - re-run des ursprünglichen
            # Tool-Calls wäre der starke Beleg (Trigger a), ist hier aber nicht
            # möglich: welcher Tool-Call (falls überhaupt einer) eine gegebene
            # Assistant-Message erzeugt hat, wird aktuell nicht mitgespeichert.
            # Ohne diesen Beleg bleibt nur die schwache, weiche Abwertung
            # (UNVERIFIED_CONTRADICTION_PENALTY) statt eines harten Invalidierens
            # - BeliefMem-Gedanke: Unsicherheit halten, nicht raten.
            if relevant_concepts:
                correction = detect_correction_signal(request.message)
                if correction['is_correction']:
                    for item in relevant_concepts:
                        for msg in item['related_messages']:
                            if msg['role'] == 'assistant' and msg.get('epistemic_state') != 'CONTRADICTED':
                                try:
                                    invalidate_message(
                                        user_id=current_user.id,
                                        message_id=msg['message_id'],
                                        reason=f"user correction signal (indicators: {correction['indicators']})"
                                    )
                                except Exception as inv_err:
                                    logger.warning(f"invalidate_message failed: {inv_err}")
                                break
                        else:
                            continue
                        break

                enhanced_context += "\n\n### Relevante Erinnerungen (basierend auf früheren Gesprächen):\n"
                for item in relevant_concepts:
                    enhanced_context += f"\n**Konzept: {item['concept']}** (Similarity: {item['similarity']:.2f})\n"
                    for msg in item['related_messages'][:2]:
                        # Every assistant reply gets auto-indexed into this same
                        # graph (persistence_stage.py), with no distinction from
                        # user-stated facts - a past refusal/error/capability
                        # claim ("this tool doesn't support X") got replayed as
                        # if it were ground truth in brand-new sessions,
                        # confirmed live via a stale "web_search doesn't support
                        # images" reply resurfacing hours later. User-authored
                        # content stays trustworthy; assistant-authored content
                        # is explicitly flagged as non-authoritative so the
                        # model re-verifies (e.g. via an actual tool call)
                        # instead of repeating its own possibly-outdated words.
                        if msg.get('epistemic_state') == 'CONTRADICTED':
                            enhanced_context += (
                                f"  - (frühere Antwort, VOM NUTZER BEREITS ALS FALSCH MARKIERT "
                                f"- NICHT wiederholen, sondern neu prüfen): {msg['content'][:100]}...\n"
                            )
                        elif msg['role'] == 'assistant':
                            enhanced_context += (
                                f"  - (deine eigene frühere Antwort - KEINE verifizierte Tatsache, "
                                f"insbesondere zu Tool-/System-Fähigkeiten ggf. veraltet; im Zweifel "
                                f"neu prüfen statt zu wiederholen): {msg['content'][:100]}...\n"
                            )
                        else:
                            enhanced_context += f"  - Nutzer sagte früher: {msg['content'][:100]}...\n"
        except Exception as e:
            logger.warning(f"Semantic context retrieval failed: {e}")

    web_search_result = None
    web_search_data = None
    web_search_type = None
    web_search_risk_score = None

    if search_intent in SEARCH_INTENTS:
        web_search_result, web_search_data, web_search_type, web_search_risk_score = await perform_web_search(
            request.message, search_intent, user_id=current_user.id, db=db
        )
        if web_search_data and web_search_data.get('error') == 'no_location':
            enhanced_context += "\n\n### HINWEIS: Kein Standort verfügbar für Wetterabfrage. Bitte den User nach seinem Standort fragen."
        elif web_search_result:
            enhanced_context += f"\n\n### Aktuelle Web-Information:\n{web_search_result}"

    used_tools = bool(web_search_result) or bool(action_result)

    if not request.session_id:
        title = request.message[:50] + "..." if len(request.message) > 50 else request.message
        session_result = db.execute(text("""
            INSERT INTO chat_sessions (user_id, title, created_at, updated_at)
            VALUES (:user_id, :title, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
        """), {'user_id': current_user.id, 'title': title})
        db.commit()
        session_id = session_result.scalar()
    else:
        session_check = db.execute(text("""
            SELECT id FROM chat_sessions WHERE id = :session_id AND user_id = :user_id
        """), {'session_id': request.session_id, 'user_id': current_user.id}).first()
        if not session_check:
            logger.info("Session %s not found or not owned by user %s. Creating fresh session.", request.session_id, current_user.id)
            title = request.message[:50] + "..." if len(request.message) > 50 else request.message
            session_result = db.execute(text("""
                INSERT INTO chat_sessions (user_id, title, created_at, updated_at)
                VALUES (:user_id, :title, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """), {'user_id': current_user.id, 'title': title})
            db.commit()
            session_id = session_result.scalar()
        else:
            session_id = request.session_id

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
            conversation_history=None,
            session_id=session_id,
            user_id=current_user.id,
            username=current_user.username,
            personality=user_prefs['personality'],
            custom_instructions=user_prefs['custom_instructions'],
            user_message_id=None,
            memory_enabled=user_prefs['memory_enabled'],
            used_tools=used_tools,
            session_lock=None,
            images=request.images
        )),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


async def stream_guest_response(query: str, model: str = "llama3.2:1b") -> AsyncGenerator[str, None]:
    """Streaming Response für Guest-Modus."""
    try:
        embedding_service = get_embedding_service()
        intent = embedding_service.detect_intent(query)
        web_search_result = None
        web_search_data = None
        web_search_type = None

        if intent in SEARCH_INTENTS:
            yield f"data: {json.dumps({'type': 'web_search', 'intent': intent})}\n\n"
            web_search_result, web_search_data, web_search_type, _ = await perform_web_search(query, intent)

            if web_search_type == 'web' and web_search_data:
                web_source_items = [
                    {
                        "id": f"source-{i}",
                        "title": s.get("title", ""),
                        "url": s.get("url", ""),
                        "domain": s.get("domain", ""),
                        "published_at": s.get("published_at"),
                        "dated": s.get("dated", False)
                    }
                    for i, s in enumerate(web_search_data.get("sources", []))
                ]
                yield f"data: {json.dumps({'type': 'web_sources', 'items': web_source_items})}\n\n"
            elif web_search_data:
                yield f"data: {json.dumps({'type': 'web_results', 'results': web_search_data, 'search_type': web_search_type})}\n\n"

        guest_prompt = """Du bist Liara, eine freundliche Digitalbegleiterin.
Du sprichst mit einem Gast. Sei hilfsbereit und kurz (max 150 Wörter).
Bei Fragen zu Features erkläre, dass erweiterte Funktionen nur für registrierte Nutzer verfügbar sind."""

        context = guest_prompt
        if web_search_result:
            context += f"\n\nAktuelle Information:\n{web_search_result}"

        payload = {
            "model": model,
            "prompt": f"{context}\n\nUser: {query}\nLiara:",
            "stream": True,
            "options": {
                "temperature": 0.7,
                "num_predict": 300,
                "repeat_penalty": 1.1
            }
        }

        response = requests.post("http://localhost:11434/api/generate", json=payload, stream=True, timeout=60)
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
    """🌙 Guest-Chat mit SSE Streaming."""
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Nachricht darf nicht leer sein")
    if len(message) > 500:
        raise HTTPException(status_code=400, detail=f"Nachricht zu lang. Maximum: 500 Zeichen.")

    return StreamingResponse(
        _with_sse_keepalive(stream_guest_response(message)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/stream/test")
async def test_stream():
    """Test SSE Streaming."""
    import asyncio
    async def test_generator():
        for i in range(5):
            yield f"data: {json.dumps({'count': i, 'message': f'Test {i}'})}\n\n"
            await asyncio.sleep(0.5)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(test_generator(), media_type="text/event-stream")


@router.get("/health")
async def chat_health():
    """Health-Check für Chat-System."""
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        ollama_available = resp.status_code == 200
        model_count = len(resp.json().get('models', [])) if ollama_available else 0
    except Exception:
        ollama_available = False
        model_count = 0

    db = SessionLocal()
    try:
        mood_history_total = db.query(MoodHistoryEntry).count()
    finally:
        db.close()

    return {
        "status": "healthy" if ollama_available else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "ollama": {"available": ollama_available, "models_loaded": model_count},
            "mood_system": {"available": True, "scope": "per_user", "history_entries_total": mood_history_total}
        },
        "capabilities": {"streaming": True, "error_recovery": True, "mood_detection": True}
    }
