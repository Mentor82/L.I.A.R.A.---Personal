from pydantic import BaseModel
from typing import Optional

class ChatMessageCreate(BaseModel):
    session_id: int
    user_id: Optional[int] = None
    role: str
    content: str
    model: Optional[str] = None
    mood: Optional[str] = None
    action_result: Optional[dict] = None
    web_search_results: Optional[dict] = None
    search_type: Optional[str] = None
    risk_score: Optional[str] = None

class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    user_id: Optional[int]
    role: str
    content: str
    model: Optional[str]
    mood: Optional[str]
    action_result: Optional[dict]
    web_search_results: Optional[dict]
    search_type: Optional[str]
    risk_score: Optional[str]
    timestamp: str

    class Config:
        from_attributes = True
