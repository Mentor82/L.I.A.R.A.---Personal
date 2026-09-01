"""
Turn Persistence Stage (Issue #23)
==================================
Handles atomic database persistence for user messages, canonical history,
assistant turns, 4D memory integration, and Neo4j concept relations under the session lock.
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import SessionLocal
from services.memory_integration import store_in_4d_memory, store_message_with_concepts
from services.neo4j_service import get_neo4j_service

logger = logging.getLogger(__name__)


def persist_user_turn_under_lock(
    user_id: int,
    session_id: int,
    message: str,
    model: str,
    mood_snapshot: Dict[str, Any],
    memory_enabled: bool = True,
    used_tools: bool = False
) -> Optional[int]:
    """
    Persists the incoming user turn message and triggers 4D memory integration.
    Must be called under the acquired session lock to ensure strict ordering.
    """
    db = SessionLocal()
    user_message_id = None
    try:
        message_insert = text("""
            INSERT INTO chat_messages 
                (user_id, session_id, role, content, model, mood, timestamp)
            VALUES 
                (:user_id, :session_id, 'user', :content, :model, :mood, CURRENT_TIMESTAMP)
            RETURNING id
        """)
        result = db.execute(message_insert, {
            'user_id': user_id,
            'session_id': session_id,
            'content': message,
            'model': model,
            'mood': mood_snapshot.get("mood", "neutral")
        })
        db.commit()
        user_message_id = result.scalar()

        db.execute(text("""
            UPDATE chat_sessions 
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = :session_id
        """), {'session_id': session_id})
        db.commit()

        logger.info(f"Persisted user message {user_message_id} in session {session_id}")

        if memory_enabled and not used_tools and user_message_id:
            try:
                store_message_with_concepts(
                    user_id=user_id,
                    message_id=user_message_id,
                    content=message,
                    role='user',
                    timestamp=datetime.now(timezone.utc),
                    session_id=session_id
                )
            except Exception as e:
                logger.error(f"Concept extraction failed: {e}")

            def store_memory_async(u_id, m_id, s_id, c_mood, e_level):
                db_async = SessionLocal()
                try:
                    store_in_4d_memory(
                        db=db_async,
                        user_id=u_id,
                        content_type='message',
                        content_id=m_id,
                        content_text=message,
                        session_id=s_id,
                        mood=c_mood,
                        energy_level=e_level,
                        additional_context={'model': model}
                    )
                except Exception as ex:
                    logger.error(f"4D Memory async storage failed: {ex}")
                finally:
                    db_async.close()

            threading.Thread(
                target=store_memory_async,
                args=(user_id, user_message_id, session_id, mood_snapshot.get("mood", "neutral"), mood_snapshot.get("intensity", 1.0)),
                daemon=True
            ).start()

        return user_message_id
    except Exception as e:
        logger.error(f"Failed to persist user turn in session {session_id}: {e}")
        return None
    finally:
        db.close()


def persist_assistant_turn(
    user_id: Optional[int],
    session_id: Optional[int],
    full_response_text: str,
    full_thinking_text: Optional[str],
    model: str,
    mood_snapshot: Dict[str, Any],
    user_message_id: Optional[int] = None,
    personality: Optional[str] = None,
    memory_enabled: bool = True,
    used_tools: bool = False,
    interrupted: bool = False
) -> bool:
    """
    Persists the completed or interrupted assistant turn message and updates Neo4j relationships.
    """
    if user_id is None or session_id is None:
        return False

    db = SessionLocal()
    try:
        insert_result = db.execute(text("""
            INSERT INTO chat_messages
                (user_id, session_id, role, content, model, mood, thinking, timestamp)
            VALUES
                (:user_id, :session_id, 'assistant', :content, :model, :mood, :thinking, CURRENT_TIMESTAMP)
            RETURNING id
        """), {
            'user_id': user_id,
            'session_id': session_id,
            'content': full_response_text,
            'model': f"{model} (interrupted)" if interrupted else model,
            'mood': mood_snapshot.get("mood", "neutral"),
            'thinking': full_thinking_text or None
        })
        db.commit()
        assistant_message_id = insert_result.scalar()

        db.execute(text("""
            UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = :session_id
        """), {'session_id': session_id})
        db.commit()

        if memory_enabled and assistant_message_id:
            try:
                store_message_with_concepts(
                    user_id=user_id,
                    message_id=assistant_message_id,
                    content=full_response_text,
                    role='assistant',
                    timestamp=datetime.now(timezone.utc),
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
                            'mood': mood_snapshot.get("mood", "neutral"),
                            'model': model,
                            'used_tools': used_tools,
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
        db.close()
