from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from api.models.chat_message import ChatMessage
from api.schemas.chat_message_schemas import ChatMessageCreate, ChatMessageResponse
from core.database import get_db
from core.dependencies import get_current_user
from api.models.base_models import User

router = APIRouter(prefix="/chat/messages", tags=["chat_messages"])


@router.post("/", response_model=ChatMessageResponse)
def create_chat_message(
    message: ChatMessageCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new chat message for current user"""
    message_data = message.dict()
    message_data['user_id'] = current_user.id
    
    db_message = ChatMessage(**message_data)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # Ensure timestamp is returned as string
    response = db_message.__dict__.copy()
    if isinstance(response.get("timestamp"), (str, type(None))):
        pass
    else:
        response["timestamp"] = response["timestamp"].isoformat()
    return response


@router.get("/session/{session_id}", response_model=list[ChatMessageResponse])
def list_chat_messages(
    session_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all messages for a session (user-filtered)"""
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.user_id == current_user.id
    ).order_by(ChatMessage.timestamp.asc()).all()
    
    result = []
    for msg in messages:
        msg_dict = msg.__dict__.copy()
        if isinstance(msg_dict.get("timestamp"), (str, type(None))):
            pass
        else:
            msg_dict["timestamp"] = msg_dict["timestamp"].isoformat()
        result.append(msg_dict)
    return result

@router.delete("/{message_id}")
def delete_chat_message(message_id: int, db: Session = Depends(get_db)):
    message = db.query(ChatMessage).get(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    db.delete(message)
    db.commit()
    return {"ok": True}
