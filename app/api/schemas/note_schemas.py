"""
Pydantic Schemas für Notes API.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    """Base Note Schema."""
    title: str = Field(..., min_length=1, max_length=255, description="Note title")
    content: str = Field(..., min_length=1, description="Note content")
    category: Optional[str] = Field(None, max_length=100, description="Note category")
    tags: List[str] = Field(default_factory=list, description="List of tags")
    parent_id: Optional[int] = Field(None, description="Parent note ID for hierarchy")


class NoteCreate(NoteBase):
    """Schema for creating a new note."""
    pass


class NoteUpdate(BaseModel):
    """Schema for updating a note (all fields optional)."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None
    is_expanded: Optional[bool] = None
    parent_id: Optional[int] = None
    order_index: Optional[int] = None


class NoteResponse(NoteBase):
    """Schema for note response."""
    id: int
    # Only ever set server-side by the create_note tool when called from
    # within a chat - never client-provided, so it's on NoteResponse only,
    # not NoteBase/NoteCreate/NoteUpdate.
    session_id: Optional[int] = None
    is_pinned: bool
    is_archived: bool
    is_expanded: bool
    order_index: int
    created_at: datetime
    updated_at: datetime
    children: Optional[List['NoteResponse']] = None  # Recursive for tree structure
    
    class Config:
        from_attributes = True


class NoteList(BaseModel):
    """Schema for note list."""
    notes: List[NoteResponse]
    total: int
    pinned_count: int
    archived_count: int


class NoteSearchResult(BaseModel):
    """Schema for search results."""
    notes: List[NoteResponse]
    total: int
    query: str


# Rebuild model to resolve forward references
NoteResponse.model_rebuild()
