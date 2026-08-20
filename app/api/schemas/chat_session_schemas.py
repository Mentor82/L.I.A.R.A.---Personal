from pydantic import BaseModel
from typing import Optional

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "Neue Konversation"

class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: Optional[str]
    updated_at: Optional[str]

    model_config = {"from_attributes": True}
