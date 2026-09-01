"""
ChatMessage Model for persistent chat messages.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system', 'error'
    content = Column(Text, nullable=False)
    model = Column(String(100), nullable=True)
    mood = Column(String(50), nullable=True)
    thinking = Column(Text, nullable=True)
    tokens = Column(JSON, nullable=True)
    action_result = Column(JSON, nullable=True)
    web_search_results = Column(JSON, nullable=True)
    search_type = Column(String(50), nullable=True)
    risk_score = Column(String(20), nullable=True)
    timestamp = Column(DateTime, server_default=func.now())
    session = relationship("ChatSession", back_populates="messages")
