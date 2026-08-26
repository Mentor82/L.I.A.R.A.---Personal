"""
Shared server-side persistence for non-streaming chat turns (issue #13).

app/api/routers/chat_streaming.py already persists the user+assistant
message pair directly, server-side, for the SSE path. The non-streaming
endpoints (/chat/message, /vision/chat, /chat/hailo-vision) used to rely on
the CLIENT posting the assistant reply back to a generic, unrestricted
POST /chat/messages/ endpoint after receiving it - which meant a client
could post ANY role/content pair, not just an honest echo of what it was
just given. This module gives those endpoints the same "persist our own
answer, server-side, before responding" pattern chat_streaming.py already
uses, so that generic endpoint (and its unrestricted role field) can be
removed entirely instead of merely restricted.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def persist_chat_turn(
    db: Session,
    session_id: int,
    user_id: int,
    user_content: str,
    assistant_content: str,
    model: Optional[str] = None,
    mood: Optional[str] = None,
) -> bool:
    """
    Persists one user+assistant message pair for an existing chat session.

    Ownership-checked (same SELECT ... WHERE id = :session_id AND user_id =
    :user_id pattern already used by chat_sessions.py/chat_streaming.py) -
    returns False and logs rather than raising if the session doesn't
    belong to user_id, matching the existing "persistence is best-effort,
    never blocks the actual reply" behavior all three callers already had
    when they saved messages client-side.
    """
    owned = db.execute(
        text("SELECT id FROM chat_sessions WHERE id = :session_id AND user_id = :user_id"),
        {"session_id": session_id, "user_id": user_id},
    ).first()
    if not owned:
        logger.warning(
            f"chat_persistence: refusing to persist turn for session {session_id} "
            f"- not owned by user {user_id}"
        )
        return False

    db.execute(
        text("""
            INSERT INTO chat_messages (session_id, role, content, model, mood, timestamp)
            VALUES (:session_id, 'user', :content, NULL, NULL, CURRENT_TIMESTAMP)
        """),
        {"session_id": session_id, "content": user_content},
    )
    db.execute(
        text("""
            INSERT INTO chat_messages (session_id, role, content, model, mood, timestamp)
            VALUES (:session_id, 'assistant', :content, :model, :mood, CURRENT_TIMESTAMP)
        """),
        {"session_id": session_id, "content": assistant_content, "model": model, "mood": mood},
    )
    db.execute(
        text("UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = :session_id"),
        {"session_id": session_id},
    )
    db.commit()
    return True
