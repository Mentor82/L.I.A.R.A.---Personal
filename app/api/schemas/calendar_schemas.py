"""
Pydantic Schemas für Calendar API.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class CalendarEventBase(BaseModel):
    """Base CalendarEvent Schema."""
    title: str = Field(..., min_length=1, max_length=255, description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    location: Optional[str] = Field(None, max_length=255, description="Event location")
    event_type: str = Field("meeting", pattern="^(meeting|reminder|appointment)$", description="Event type")
    all_day: bool = Field(False, description="All-day event flag")
    recurrence: Optional[dict] = Field(None, description="Recurrence rules")
    
    @field_validator('end_time')
    @classmethod
    def end_after_start(cls, v, info):
        """Validate that end_time is after start_time."""
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class CalendarEventCreate(CalendarEventBase):
    """Schema for creating a new calendar event."""
    pass


class CalendarEventUpdate(BaseModel):
    """Schema for updating a calendar event (all fields optional)."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=255)
    event_type: Optional[str] = Field(None, pattern="^(meeting|reminder|appointment)$")
    all_day: Optional[bool] = None
    recurrence: Optional[dict] = None


class CalendarEventResponse(CalendarEventBase):
    """Schema for calendar event response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CalendarEventList(BaseModel):
    """Schema for event list."""
    events: List[CalendarEventResponse]
    total: int


class ConflictCheck(BaseModel):
    """Schema for conflict detection response."""
    has_conflict: bool
    conflicting_events: List[CalendarEventResponse] = []
    message: str


class FreeSlots(BaseModel):
    """Schema for free time slots."""
    date: str
    free_slots: List[dict]  # [{"start": "09:00", "end": "10:00"}, ...]
    total_free_minutes: int
