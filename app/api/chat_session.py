
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from api.models.chat_session import ChatSession
from api.schemas.chat_session_schemas import ChatSessionCreate
from core.database import get_db
from api.models.base_models import User
from fastapi import status
from fastapi.security import OAuth2PasswordBearer
from api.routers.auth_router import get_current_user

router = APIRouter(prefix="/chat/sessions", tags=["chat_sessions"])


@router.post("/")
def create_chat_session(
    session: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        db_session = ChatSession(
            user_id=current_user.id,
            title=session.title or "Neue Konversation"
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        print(f"DEBUG: Session erfolgreich erstellt: id={db_session.id}")
        response = {
            "id": db_session.id,
            "user_id": db_session.user_id,
            "title": db_session.title,
            "created_at": db_session.created_at.isoformat() if db_session.created_at else None,
            "updated_at": db_session.updated_at.isoformat() if db_session.updated_at else None
        }
        from fastapi.responses import JSONResponse
        return JSONResponse(content=response)
    except Exception as e:
        print(f"ERROR: Session-Erstellung fehlgeschlagen: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def list_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all chat sessions for current user"""
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.updated_at.desc()).all()
    
    result = []
    for s in sessions:
        result.append({
            "id": s.id,
            "user_id": s.user_id,
            "title": s.title,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        })
    from fastapi.responses import JSONResponse
    return JSONResponse(content=result)

@router.delete("/{session_id}")
def delete_chat_session(
    session_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chat session (user-owned only)"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    return {"ok": True}


@router.patch("/{session_id}")
def update_chat_session(
    session_id: int,
    title: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update session title"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.title = title
    db.commit()
    db.refresh(session)
    
    return {
        "id": session.id,
        "title": session.title,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None
    }
