"""
Chat Sessions API
Manages chat conversation sessions and message history
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from core.dependencies import require_active_user
from core.database import get_db
from api.models.base_models import User
from services.session_workspace import delete_session_workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat Sessions"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "Neue Konversation"


class ChatSessionUpdate(BaseModel):
    title: str


class ChatMessageCreate(BaseModel):
    session_id: int
    role: str
    content: str
    model: Optional[str] = None
    mood: Optional[str] = None


class ChatMessage(BaseModel):
    id: int
    role: str
    content: str
    model: Optional[str]
    mood: Optional[str]
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
            (
                SELECT content 
                FROM chat_messages 
                WHERE session_id = cs.id 
                ORDER BY timestamp DESC 
                LIMIT 1
            ) as last_message,
            (
                SELECT timestamp 
                FROM chat_messages 
                WHERE session_id = cs.id 
                ORDER BY timestamp DESC 
                LIMIT 1
            ) as last_message_time
        FROM chat_sessions cs
        LEFT JOIN chat_messages cm ON cs.id = cm.session_id
        WHERE cs.user_id = :user_id
        GROUP BY cs.id, cs.user_id, cs.title, cs.created_at, cs.updated_at
        ORDER BY COALESCE(
            (SELECT timestamp FROM chat_messages WHERE session_id = cs.id ORDER BY timestamp DESC LIMIT 1),
            cs.updated_at
        ) DESC
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
    
    result = db.execute(text("""
        SELECT id, role, content, model, mood, timestamp
        FROM chat_messages
        WHERE session_id = :session_id
        ORDER BY timestamp ASC
    """), {'session_id': session_id})
    
    messages = []
    for row in result:
        messages.append({
            'id': row.id,
            'role': row.role,
            'content': row.content,
            'model': row.model,
            'mood': row.mood,
            'timestamp': row.timestamp
        })
    
    return messages


@router.post("/messages/", response_model=ChatMessage)
async def create_chat_message(
    message: ChatMessageCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """
    Neue Message zu einer Session hinzufügen
    """
    # Verify session belongs to user
    session_check = db.execute(text("""
        SELECT id FROM chat_sessions 
        WHERE id = :session_id AND user_id = :user_id
    """), {'session_id': message.session_id, 'user_id': current_user.id}).first()
    
    if not session_check:
        raise HTTPException(status_code=404, detail="Session not found or access denied")
    
    # Insert message
    result = db.execute(text("""
        INSERT INTO chat_messages (session_id, role, content, model, mood, timestamp)
        VALUES (:session_id, :role, :content, :model, :mood, CURRENT_TIMESTAMP)
        RETURNING id, role, content, model, mood, timestamp
    """), {
        'session_id': message.session_id,
        'role': message.role,
        'content': message.content,
        'model': message.model,
        'mood': message.mood
    })
    db.commit()
    
    row = result.first()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create message")
    
    # Update session timestamp
    db.execute(text("""
        UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = :session_id
    """), {'session_id': message.session_id})
    db.commit()
    
    return {
        'id': row.id,
        'role': row.role,
        'content': row.content,
        'model': row.model,
        'mood': row.mood,
        'timestamp': row.timestamp
    }


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
