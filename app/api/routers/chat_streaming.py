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
import json
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from liara_engine.memory.mood_system import MoodSystem
from liara_engine.memory.short_context import get_memory
from liara_engine.actions.intent_detector import get_intent_detector
from liara_engine.actions.action_executor import ActionExecutor
from core.dependencies import require_active_user
from core.database import get_db
from api.models.base_models import User
from services.memory_integration import store_in_4d_memory, store_message_with_concepts, get_relevant_context
from services.embedding_service import get_embedding_service
from services.web_search_service import get_web_search_service
from services.location_service import get_location_service
from services.web_safety import get_risk_analyzer, get_content_filter
from sqlalchemy.orm import Session
from sqlalchemy import text

router = APIRouter(prefix="/chat", tags=["Chat Streaming"])

# Web search intent list
SEARCH_INTENTS = ['SEARCH_WEATHER', 'SEARCH_WIKI', 'SEARCH_NEWS', 'SEARCH_WEB']


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


def perform_web_search(query: str, intent: str, user_id: Optional[int] = None, db: Optional[Session] = None) -> tuple[Optional[str], Optional[Dict], Optional[str], Optional[int]]:
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
            result = web_search.get_weather_info(location)
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
            result = web_search.search_wikipedia(query, language='de')
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
            result = web_search.search_instant_answer(query)
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
    user_id: int = None
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

Aktueller Mood-Modifier: {mood_modifier}

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
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": 2000
        }
    }
    
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
                yield f"data: {json.dumps({'type': 'content', 'text': action_result.get('message', 'Aktion erfolgreich ausgeführt')})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'action_executed': True})}\n\n"
                return  # Don't call LLM if action was successful
        
        # If web search was triggered, send event
        if web_search_intent:
            yield f"data: {json.dumps({'type': 'web_search', 'intent': web_search_intent, 'search_type': web_search_type})}\n\n"
            
            # Send web search results
            if web_search_data:
                yield f"data: {json.dumps({'type': 'web_results', 'results': web_search_data, 'search_type': web_search_type, 'risk_score': web_search_risk_score or 0})}\n\n"
        
        # Streaming Request zu Ollama via httpx (NO buffering)
        async with httpx.AsyncClient(timeout=90.0) as client:
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
                                content = chunk["message"].get("content", "")
                                if content:
                                    # Mirko Debug Logging
                                    try:
                                        if should_log_for_user(current_user.username):
                                            mlogger.log_sse_chunk("content", content=content)
                                    except:
                                        pass  # Logging-Fehler ignorieren
                                    
                                    # SSE Format: data: {json}\n\n
                                    yield f"data: {json.dumps({'type': 'content', 'text': content})}\n\n"
                            
                            # Check if done
                            if chunk.get("done", False):
                                # Mirko Debug Logging
                                try:
                                    if should_log_for_user(current_user.username):
                                        mlogger.log_sse_chunk("done", metadata={"mood_updated": True})
                                except:
                                    pass  # Logging-Fehler ignorieren
                                
                                # Update Mood nach Antwort
                                if user_id is not None:
                                    mood_system.update_mood(interaction_type, intensity=0.5)
                                
                                yield f"data: {json.dumps({'type': 'done', 'mood_updated': True})}\n\n"
                                break
                        
                        except json.JSONDecodeError:
                            continue
        
    except httpx.TimeoutException:
        error = ChatError(
            error_type="timeout",
            message="Ollama antwortet nicht (Timeout nach 90s)",
            timestamp=datetime.now().isoformat(),
            recoverable=True,
            suggestion="Versuche es mit einem schnelleren Modell (z.B. llama3.2:1b)"
        )
        yield f"data: {json.dumps({'type': 'error', 'error': error.dict()})}\n\n"
    
    except requests.exceptions.ConnectionError:
        error = ChatError(
            error_type="connection_error",
            message="Kann nicht mit Ollama verbinden",
            timestamp=datetime.now().isoformat(),
            recoverable=True,
            suggestion="Prüfe ob Ollama läuft: systemctl status ollama"
        )
        yield f"data: {json.dumps({'type': 'error', 'error': error.dict()})}\n\n"
    
    except requests.exceptions.HTTPError as e:
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
    from core.mirko_logger import get_mirko_logger, should_log_for_user
    mlogger = get_mirko_logger()
    if should_log_for_user(current_user.username):
        mlogger.log_request_start(
            user_id=current_user.id,
            username=current_user.username,
            message=request.message,
            session_id=request.session_id
        )
    
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
    needs_action_check = any(kw in message_lower for kw in action_keywords)
    
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
    
    # Build enhanced context
    enhanced_context = request.context or ""
    
    # 1. Add Location Context (if consent given)
    location_context = get_location_context(db, current_user.id)
    if location_context:
        enhanced_context += location_context
    
    # ✨ 2. NEU: Add Semantic Context from Neo4j (Top-5 similar concepts)
    relevant_concepts = None
    try:
        relevant_concepts = get_relevant_context(
            user_id=current_user.id,
            query_text=request.message,
            limit=5,
            min_similarity=0.6
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
        web_search_result, web_search_data, web_search_type, web_search_risk_score = perform_web_search(
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
        
        # ✨ NEU: Store in Neo4j with auto-concept extraction (sync für Testing)
        try:
            store_message_with_concepts(
                user_id=current_user.id,
                message_id=message_id,
                content=request.message,
                role='user',
                timestamp=datetime.utcnow()
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
        
    except Exception as e:
        logger.error(f"Message storage failed: {e}")
        # Continue with chat even if message storage fails
    
    return StreamingResponse(
        stream_ollama_response(
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
            session_id=session_id,  # NEW: Send session_id to frontend
            user_id=current_user.id
        ),
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


# Error-Handling Utilities
class ChatErrorHandler:
    """Centralized Error-Handler für Chat-System."""
    
    @staticmethod
    def handle_ollama_error(error: Exception) -> ChatError:
        """
        Konvertiere Exception zu ChatError.
        
        Returns:
            Strukturierter ChatError
        """
        if isinstance(error, requests.exceptions.Timeout):
            return ChatError(
                error_type="timeout",
                message="Model-Antwort dauert zu lange",
                timestamp=datetime.now().isoformat(),
                recoverable=True,
                suggestion="Nutze kleineres Model oder erhöhe Timeout"
            )
        
        elif isinstance(error, requests.exceptions.ConnectionError):
            return ChatError(
                error_type="connection_error",
                message="Ollama Service nicht erreichbar",
                timestamp=datetime.now().isoformat(),
                recoverable=True,
                suggestion="Starte Ollama: sudo systemctl start ollama"
            )
        
        elif isinstance(error, requests.exceptions.HTTPError):
            return ChatError(
                error_type="http_error",
                message=f"HTTP {error.response.status_code}: {error.response.reason}",
                timestamp=datetime.now().isoformat(),
                recoverable=False,
                suggestion="Model nicht gefunden oder Ollama-Fehler"
            )
        
        else:
            return ChatError(
                error_type="unknown",
                message=str(error),
                timestamp=datetime.now().isoformat(),
                recoverable=False,
                suggestion="Prüfe Logs: journalctl -u ollama -n 50"
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

    # Check Memory System
    memory = get_memory()
    memory_status = memory.get_summary()
    
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
            },
            "memory_system": {
                "available": True,
                "messages_stored": memory_status["message_count"],
                "capacity_used": memory_status["capacity_used_percent"]
            }
        },
        "capabilities": {
            "streaming": True,
            "error_recovery": True,
            "mood_detection": True,
            "context_memory": True
        }
    }


@router.get("/memory/status")
async def get_memory_status():
    """
    📝 Hole Memory-Status.
    
    Returns:
        Memory-Statistiken
    """
    memory = get_memory()
    return memory.get_summary()


@router.get("/memory/messages")
async def get_recent_messages(limit: int = 10):
    """
    📜 Hole letzte Nachrichten aus Memory.
    
    Args:
        limit: Max Anzahl (default: 10)
        
    Returns:
        Liste der letzten Messages
    """
    memory = get_memory()
    limit = min(limit, 20)  # Max 20
    
    return {
        "messages": memory.get_recent_messages(limit=limit),
        "total_in_memory": len(memory.messages)
    }


@router.post("/memory/clear")
async def clear_memory(current_user: User = Depends(require_active_user)):
    """
    🗑️ Lösche Memory (Reset Konversation).
    
    Returns:
        Bestätigung
    """
    memory = get_memory()
    memory.clear()
    
    return {
        "status": "cleared",
        "message": "Conversation memory cleared",
        "timestamp": datetime.now().isoformat()
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
            web_search_result, web_search_data, web_search_type = perform_web_search(query, intent)
            
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
        
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    if chunk.get('done'):
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        break
                    
                    content = chunk.get('response', '')
                    if content:
                        yield f"data: {json.dumps({'type': 'content', 'text': content})}\n\n"
                        
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
        stream_guest_response(message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


