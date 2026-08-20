"""
Calendar API Router - CRUD Operations für Kalender & Terminplanung.
"""

from datetime import datetime, timedelta, time
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from core.database import get_db
from core.dependencies import get_current_user, require_user_or_admin
from api.models.base_models import CalendarEvent, User, UserRole
from api.schemas.calendar_schemas import (
    CalendarEventCreate, CalendarEventUpdate, CalendarEventResponse, 
    CalendarEventList, ConflictCheck, FreeSlots
)
from services.memory_integration import store_in_4d_memory


router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.post("/", response_model=CalendarEventResponse, status_code=201)
def create_event(
    event: CalendarEventCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Erstelle ein neues Kalenderereignis + speichere in 4D Memory.
    
    - **title**: Event-Titel (erforderlich)
    - **start_time**: Startzeit (erforderlich)
    - **end_time**: Endzeit (erforderlich, muss nach start_time sein)
    - **description**: Beschreibung (optional)
    - **location**: Ort (optional)
    - **event_type**: meeting, reminder, appointment (default: meeting)
    - **all_day**: Ganztägiges Event (default: false)
    - **recurrence**: Wiederholungsregeln (optional)
    """
    db_event = CalendarEvent(**event.model_dump(), user_id=current_user.id)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    # Store in 4D Memory
    try:
        content_text = f"{event.title}. {event.description or ''}"
        if event.location:
            content_text += f" Ort: {event.location}"
        
        store_in_4d_memory(
            db=db,
            user_id=current_user.id,
            content_type='event',
            content_id=db_event.id,
            content_text=content_text,
            additional_context={
                'event_type': event.event_type,
                'start_time': str(event.start_time),
                'end_time': str(event.end_time),
                'location': event.location,
                'all_day': event.all_day
            }
        )
    except Exception as e:
        print(f"4D Memory storage failed for event {db_event.id}: {e}")
    
    return db_event


@router.get("/", response_model=CalendarEventList)
def get_events(
    start_date: Optional[datetime] = Query(None, description="Filter events from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter events until this date"),
    event_type: Optional[str] = Query(None, pattern="^(meeting|reminder|appointment)$", description="Filter by type"),
    search: Optional[str] = Query(None, description="Search in title/description/location"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip N results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Liste alle Kalendereinträge mit optionalen Filtern.
    
    Filter-Optionen:
    - **start_date**: Events ab diesem Datum
    - **end_date**: Events bis zu diesem Datum
    - **event_type**: meeting/reminder/appointment
    - **search**: Suche in Titel/Beschreibung/Ort
    - **limit**: Anzahl der Ergebnisse (max 500)
    - **offset**: Pagination-Offset
    """
    query = db.query(CalendarEvent)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(CalendarEvent.user_id == current_user.id)
    
    # Apply date filters
    if start_date:
        query = query.filter(CalendarEvent.start_time >= start_date)
    
    if end_date:
        query = query.filter(CalendarEvent.end_time <= end_date)
    
    if event_type:
        query = query.filter(CalendarEvent.event_type == event_type)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                CalendarEvent.title.ilike(search_pattern),
                CalendarEvent.description.ilike(search_pattern),
                CalendarEvent.location.ilike(search_pattern)
            )
        )
    
    total = query.count()
    events = query.order_by(CalendarEvent.start_time.asc()).offset(offset).limit(limit).all()
    
    return {
        "events": events,
        "total": total
    }


@router.get("/today", response_model=CalendarEventList)
def get_today_events(db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Hole alle Events für heute.
    """
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    query = db.query(CalendarEvent).filter(
        and_(
            CalendarEvent.start_time >= today_start,
            CalendarEvent.start_time < today_end
        )
    )
    
    if current_user.role != UserRole.ADMIN:
        query = query.filter(CalendarEvent.user_id == current_user.id)
    
    events = query.order_by(CalendarEvent.start_time.asc()).all()
    
    return {
        "events": events,
        "total": len(events)
    }


@router.get("/week", response_model=CalendarEventList)
def get_week_events(db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Hole alle Events für diese Woche (nächsten 7 Tage).
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = today + timedelta(days=7)
    
    query = db.query(CalendarEvent).filter(
        and_(
            CalendarEvent.start_time >= today,
            CalendarEvent.start_time < week_end
        )
    )
    
    if current_user.role != UserRole.ADMIN:
        query = query.filter(CalendarEvent.user_id == current_user.id)
    
    events = query.order_by(CalendarEvent.start_time.asc()).all()
    
    return {
        "events": events,
        "total": len(events)
    }


@router.get("/conflicts", response_model=ConflictCheck)
def check_conflicts(
    start_time: datetime = Query(..., description="Proposed event start time"),
    end_time: datetime = Query(..., description="Proposed event end time"),
    exclude_id: Optional[int] = Query(None, description="Exclude event with this ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Prüfe ob ein Zeitraum mit existierenden Events kollidiert.
    
    Nützlich vor dem Erstellen eines neuen Events.
    """
    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")
    
    query = db.query(CalendarEvent)
    
    if current_user.role != UserRole.ADMIN:
        query = query.filter(CalendarEvent.user_id == current_user.id)
    
    query = query.filter(
        or_(
            # New event starts during existing event
            and_(
                CalendarEvent.start_time <= start_time,
                CalendarEvent.end_time > start_time
            ),
            # New event ends during existing event
            and_(
                CalendarEvent.start_time < end_time,
                CalendarEvent.end_time >= end_time
            ),
            # New event completely contains existing event
            and_(
                CalendarEvent.start_time >= start_time,
                CalendarEvent.end_time <= end_time
            )
        )
    )
    
    if exclude_id:
        query = query.filter(CalendarEvent.id != exclude_id)
    
    conflicts = query.all()
    
    return {
        "has_conflict": len(conflicts) > 0,
        "conflicting_events": conflicts,
        "message": f"Found {len(conflicts)} conflicting event(s)" if conflicts else "No conflicts"
    }


@router.get("/free", response_model=FreeSlots)
def get_free_slots(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    work_start: str = Query("09:00", description="Work day start time HH:MM"),
    work_end: str = Query("18:00", description="Work day end time HH:MM"),
    min_duration: int = Query(30, description="Minimum slot duration in minutes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Finde freie Zeitfenster an einem bestimmten Tag.
    
    Nützlich für Terminplanung.
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Parse work hours
    try:
        work_start_time = datetime.strptime(work_start, "%H:%M").time()
        work_end_time = datetime.strptime(work_end, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")
    
    # Get events for this day
    day_start = datetime.combine(target_date, work_start_time)
    day_end = datetime.combine(target_date, work_end_time)
    
    query = db.query(CalendarEvent).filter(
        and_(
            CalendarEvent.start_time >= day_start,
            CalendarEvent.end_time <= day_end
        )
    )
    
    if current_user.role != UserRole.ADMIN:
        query = query.filter(CalendarEvent.user_id == current_user.id)
    
    events = query.order_by(CalendarEvent.start_time.asc()).all()
    
    # Calculate free slots
    free_slots = []
    current_time = day_start
    
    for event in events:
        if event.start_time > current_time:
            duration = (event.start_time - current_time).total_seconds() / 60
            if duration >= min_duration:
                free_slots.append({
                    "start": current_time.strftime("%H:%M"),
                    "end": event.start_time.strftime("%H:%M"),
                    "duration_minutes": int(duration)
                })
        current_time = max(current_time, event.end_time)
    
    # Check final slot
    if day_end > current_time:
        duration = (day_end - current_time).total_seconds() / 60
        if duration >= min_duration:
            free_slots.append({
                "start": current_time.strftime("%H:%M"),
                "end": day_end.strftime("%H:%M"),
                "duration_minutes": int(duration)
            })
    
    total_free = sum(slot["duration_minutes"] for slot in free_slots)
    
    return {
        "date": date,
        "free_slots": free_slots,
        "total_free_minutes": total_free
    }


@router.get("/{event_id}", response_model=CalendarEventResponse)
def get_event(event_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Hole ein einzelnes Event per ID.
    """
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    if current_user.role != UserRole.ADMIN and event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return event


@router.put("/{event_id}", response_model=CalendarEventResponse)
def update_event(event_id: int, event_update: CalendarEventUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Update ein Kalenderevent.
    
    Alle Felder sind optional - nur angegebene Felder werden aktualisiert.
    """
    db_event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    if current_user.role != UserRole.ADMIN and db_event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = event_update.model_dump(exclude_unset=True)
    
    # Validate time relationship if both are being updated
    if "start_time" in update_data and "end_time" in update_data:
        if update_data["end_time"] <= update_data["start_time"]:
            raise HTTPException(status_code=400, detail="end_time must be after start_time")
    
    for field, value in update_data.items():
        setattr(db_event, field, value)
    
    db.commit()
    db.refresh(db_event)
    return db_event


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Lösche ein Kalenderevent.
    """
    db_event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    if current_user.role != UserRole.ADMIN and db_event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    
    db.delete(db_event)
    db.commit()
    return None
