"""
Pydantic Schemas für Tasks API.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    """Base Task Schema."""
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, description="Detailed description")
    priority: str = Field("medium", pattern="^(low|medium|high)$", description="Priority level")
    due_date: Optional[datetime] = Field(None, description="Due date and time")
    tags: List[str] = Field(default_factory=list, description="List of tags")


class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task (all fields optional)."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TaskResponse(TaskBase):
    """Schema for task response."""
    id: int
    completed: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # Enables ORM mode


class TaskList(BaseModel):
    """Schema for paginated task list."""
    tasks: List[TaskResponse]
    total: int
    completed_count: int
    pending_count: int
