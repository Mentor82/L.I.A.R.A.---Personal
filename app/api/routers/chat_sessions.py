"""
Chat Sessions API
Manages chat conversation sessions and message history
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from core.dependencies import require_active_user
from core.database import get_db
from api.models.base_models import User
from services.session_workspace import delete_session_workspace
from services.context import TokenEstimator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat Sessions"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "Neue Konversation"


class ChatSessionUpdate(BaseModel):
    title: str


class ChatMessage(BaseModel):
    id: int
    role: str
    content: str
    model: Optional[str]
    mood: Optional[str]
    thinking: Optional[str] = None
    tokens: Optional[Dict[str, Any]] = None
    tasks: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ChatSession(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message: Optional[str] = None  # Preview der letzten Nachricht
    last_message_time: Optional[datetime] = None  # Zeitstempel letzte Nachricht
    
    class Config:
        from_attributes = True


class ChatSessionWithMessages(ChatSession):
    messages: List[ChatMessage]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/sessions", response_model=List[ChatSession])
async def get_chat_sessions(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """
    Alle Chat-Sessions des Users abrufen mit Preview und letzter Message
    """
    result = db.execute(text("""
        SELECT
            cs.id,
            cs.user_id,
            cs.title,
            cs.created_at,
            cs.updated_at,
            COUNT(cm.id) as message_count,
            lm.content as last_message,
            lm.timestamp as last_message_time
        FROM chat_sessions cs
        LEFT JOIN chat_messages cm ON cs.id = cm.session_id
        LEFT JOIN LATERAL (
            SELECT content, timestamp
            FROM chat_messages
            WHERE session_id = cs.id
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
        ) lm ON true
        WHERE cs.user_id = :user_id
        GROUP BY cs.id, cs.user_id, cs.title, cs.created_at, cs.updated_at, lm.content, lm.timestamp
        ORDER BY COALESCE(lm.timestamp, cs.updated_at) DESC, cs.id DESC
    """), {'user_id': current_user.id})
    
    sessions = []
    for row in result:
        # Truncate last_message to 60 characters for preview
        last_msg = row.last_message
        if last_msg and len(last_msg) > 60:
            last_msg = last_msg[:60] + '...'
        
        sessions.append({
            'id': row.id,
            'user_id': row.user_id,
            'title': row.title,
            'created_at': row.created_at,
            'updated_at': row.updated_at,
            'message_count': row.message_count or 0,
            'last_message': last_msg,
            'last_message_time': row.last_message_time
        })
    
    return sessions


@router.post("/sessions", response_model=ChatSession)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """
    Neue Chat-Session erstellen
    """
    result = db.execute(text("""
        INSERT INTO chat_sessions (user_id, title, created_at, updated_at)
        VALUES (:user_id, :title, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id, user_id, title, created_at, updated_at
    """), {
        'user_id': current_user.id,
        'title': session_data.title
    })
    db.commit()
    
    row = result.first()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create session")
    
    return {
        'id': row.id,
        'user_id': row.user_id,
        'title': row.title,
        'created_at': row.created_at,
        'updated_at': row.updated_at,
        'message_count': 0
    }


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
async def get_session_messages(
    session_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """
    Alle Messages einer Session abrufen
    """
    # Verify session belongs to user
    session_check = db.execute(text("""
        SELECT id FROM chat_sessions 
        WHERE id = :session_id AND user_id = :user_id
    """), {'session_id': session_id, 'user_id': current_user.id}).first()
    
    if not session_check:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        result = db.execute(text("""
            SELECT id, role, content, model, mood, thinking, tokens, tasks, timestamp
            FROM chat_messages
            WHERE session_id = :session_id
            ORDER BY timestamp ASC, id ASC
        """), {'session_id': session_id})
        has_tokens_col = True
    except Exception:
        db.rollback()
        result = db.execute(text("""
            SELECT id, role, content, model, mood, thinking, timestamp
            FROM chat_messages
            WHERE session_id = :session_id
            ORDER BY timestamp ASC, id ASC
        """), {'session_id': session_id})
        has_tokens_col = False

    messages = []
    for row in result:
        tok_data = None
        if has_tokens_col and getattr(row, 'tokens', None):
            raw_tok = row.tokens
            if isinstance(raw_tok, dict):
                tok_data = raw_tok
            elif isinstance(raw_tok, str):
                try:
                    tok_data = json.loads(raw_tok)
                except Exception:
                    tok_data = None

        # Fallback-Berechnung für ältere / unvollständige Messages
        if not tok_data and row.role == 'assistant' and (row.content or getattr(row, 'thinking', None)):
            tok_data = TokenEstimator.estimate_turn_tokens(
                response_text=row.content or "",
                thinking_text=getattr(row, 'thinking', "") or ""
            )

        tasks_data = None
        if has_tokens_col and getattr(row, 'tasks', None):
            raw_tasks = row.tasks
            if isinstance(raw_tasks, list):
                tasks_data = raw_tasks
            elif isinstance(raw_tasks, str):
                try:
                    tasks_data = json.loads(raw_tasks)
                except Exception:
                    tasks_data = None

        messages.append({
            'id': row.id,
            'role': row.role,
            'content': row.content,
            'model': row.model,
            'mood': row.mood,
            'thinking': getattr(row, 'thinking', None),
            'tokens': tok_data,
            'tasks': tasks_data,
            'timestamp': row.timestamp
        })

    return messages


class TaskItemUpdate(BaseModel):
    item_id: str
    done: bool


@router.patch("/messages/{message_id}/tasks")
async def update_message_task_item(
    message_id: int,
    update: TaskItemUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """
    Toggles a single item's done-state on a persisted assistant message's
    <tasks> checklist (issue: model-authored plans/todos disappeared after
    navigating away and back, and the checkboxes were read-only). Ownership
    checked via a join on chat_sessions.user_id, same pattern as every other
    per-message endpoint - a message_id alone says nothing about who owns it.
    """
    row = db.execute(text("""
        SELECT cm.tasks FROM chat_messages cm
        JOIN chat_sessions cs ON cs.id = cm.session_id
        WHERE cm.id = :message_id AND cs.user_id = :user_id
    """), {'message_id': message_id, 'user_id': current_user.id}).first()

    if not row:
        raise HTTPException(status_code=404, detail="Message not found")

    try:
        tasks = json.loads(row.tasks) if row.tasks else []
    except Exception:
        tasks = []

    item_found = False
    for item in tasks:
        if str(item.get('id')) == str(update.item_id):
            item['done'] = update.done
            item_found = True
            break

    if not item_found:
        raise HTTPException(status_code=404, detail="Task item not found")

    db.execute(text("""
        UPDATE chat_messages SET tasks = :tasks WHERE id = :message_id
    """), {'tasks': json.dumps(tasks), 'message_id': message_id})
    db.commit()

    return {"success": True, "tasks": tasks}


@router.put("/sessions/{session_id}", response_model=ChatSession)
async def update_chat_session(
    session_id: int,
    session_data: ChatSessionUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """
    Session-Titel aktualisieren
    """
    result = db.execute(text("""
        UPDATE chat_sessions
        SET title = :title, updated_at = CURRENT_TIMESTAMP
        WHERE id = :session_id AND user_id = :user_id
        RETURNING id, user_id, title, created_at, updated_at
    """), {
        'session_id': session_id,
        'user_id': current_user.id,
        'title': session_data.title
    })
    db.commit()
    
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get message count
    count_result = db.execute(text("""
        SELECT COUNT(*) as count FROM chat_messages WHERE session_id = :session_id
    """), {'session_id': session_id})
    message_count = count_result.scalar()
    
    return {
        'id': row.id,
        'user_id': row.user_id,
        'title': row.title,
        'created_at': row.created_at,
        'updated_at': row.updated_at,
        'message_count': message_count or 0
    }


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """
    Session löschen (inkl. aller Messages)
    """
    owned = db.execute(text("""
        SELECT id FROM chat_sessions WHERE id = :session_id AND user_id = :user_id
    """), {'session_id': session_id, 'user_id': current_user.id}).first()

    if not owned:
        raise HTTPException(status_code=404, detail="Session not found")

    # No ON DELETE CASCADE on chat_messages.session_id, so messages must be
    # removed explicitly before the session, or the FK constraint rejects it.
    db.execute(text("""
        DELETE FROM chat_messages WHERE session_id = :session_id
    """), {'session_id': session_id})

    db.execute(text("""
        DELETE FROM chat_sessions WHERE id = :session_id
    """), {'session_id': session_id})

    db.commit()

    # Best-effort - a workspace cleanup failure shouldn't block the session
    # delete the user actually asked for.
    if not delete_session_workspace(current_user.id, session_id):
        logger.warning(f"Failed to delete workspace for session {session_id} (user {current_user.id})")

    return {"message": "Session deleted successfully"}


@router.post("/sessions/{session_id}/archive-to-workspace")
async def archive_chat_session_endpoint(
    session_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """
    Archiviert eine Chat-Sitzung persistent als strukturierte Markdown-Datei
    im Workspace des Benutzers (unter chat_archives/).
    """
    from services.chat_archive_service import archive_session_to_workspace
    result = archive_session_to_workspace(current_user.id, session_id, db)
    if not result.get("ok"):
        raise HTTPException(status_code=404 if "nicht gefunden" in result.get("error", "") else 400, detail=result.get("error", "Archivierung fehlgeschlagen"))
    return result


@router.get("/sessions/{session_id}/export")
async def export_chat_session_endpoint(
    session_id: int,
    format: str = "markdown",
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """
    Exportiert eine Chat-Sitzung direkt als Markdown- oder JSON-Datei zum Download.
    """
    from fastapi.responses import Response
    from api.models.chat_session import ChatSession as DBChatSession
    from api.models.chat_message import ChatMessage as DBChatMessage
    from services.chat_archive_service import format_session_as_markdown, format_session_as_json, sanitize_filename

    session = db.query(DBChatSession).filter(
        DBChatSession.id == session_id,
        DBChatSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(DBChatMessage).filter(
        DBChatMessage.session_id == session_id
    ).order_by(DBChatMessage.timestamp.asc(), DBChatMessage.id.asc()).all()

    clean_title = sanitize_filename(session.title or "chat")
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format.lower() == "json":
        data = format_session_as_json(session, messages)
        filename = f"{clean_title}_{session_id}_{now_str}.json"
        import json
        return Response(
            content=json.dumps(data, indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    else:
        content = format_session_as_markdown(session, messages)
        filename = f"{clean_title}_{session_id}_{now_str}.md"
        return Response(
            content=content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
