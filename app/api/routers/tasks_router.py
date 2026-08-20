"""
Tasks API Router - CRUD Operations für Aufgabenverwaltung.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from core.database import get_db
from core.dependencies import get_current_user, require_user_or_admin
from api.models.base_models import Task, User, UserRole
from api.schemas.task_schemas import TaskCreate, TaskUpdate, TaskResponse, TaskList
from services.memory_integration import store_in_4d_memory


router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(
    task: TaskCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Erstelle eine neue Aufgabe + speichere in 4D Memory.
    
    - **title**: Aufgaben-Titel (erforderlich)
    - **description**: Detaillierte Beschreibung (optional)
    - **priority**: low, medium, high (default: medium)
    - **due_date**: Fälligkeitsdatum (optional)
    - **tags**: Liste von Tags (optional)
    """
    db_task = Task(**task.model_dump(), user_id=current_user.id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Store in 4D Memory
    try:
        content_text = f"{task.title}. {task.description or ''}"
        store_in_4d_memory(
            db=db,
            user_id=current_user.id,
            content_type='task',
            content_id=db_task.id,
            content_text=content_text,
            additional_context={
                'priority': task.priority,
                'due_date': str(task.due_date) if task.due_date else None,
                'tags': task.tags
            }
        )
    except Exception as e:
        print(f"4D Memory storage failed for task {db_task.id}: {e}")
        # Continue even if memory storage fails
    
    return db_task


@router.get("/", response_model=TaskList)
def get_tasks(
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    priority: Optional[str] = Query(None, pattern="^(low|medium|high)$", description="Filter by priority"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search in title/description"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip N results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Liste alle Aufgaben mit optionalen Filtern.
    
    Filter-Optionen:
    - **completed**: true/false - nur erledigte/offene Tasks
    - **priority**: low/medium/high - nach Priorität
    - **tag**: string - Tasks mit diesem Tag
    - **search**: string - Suche in Titel/Beschreibung
    - **limit**: Anzahl der Ergebnisse (max 500)
    - **offset**: Pagination-Offset
    """
    # Filter by user_id (admins can see all)
    query = db.query(Task)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Task.user_id == current_user.id)
    
    # Apply filters
    if completed is not None:
        query = query.filter(Task.completed == completed)
    
    if priority:
        query = query.filter(Task.priority == priority)
    
    if tag:
        query = query.filter(Task.tags.contains([tag]))
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_pattern),
                Task.description.ilike(search_pattern)
            )
        )
    
    # Get total counts (user-scoped)
    total = query.count()
    
    # Create count query with same user filter as main query
    count_query = db.query(Task)
    if current_user.role != UserRole.ADMIN:
        count_query = count_query.filter(Task.user_id == current_user.id)
    
    completed_count = count_query.filter(Task.completed == True).count()
    pending_count = count_query.filter(Task.completed == False).count()
    
    # Apply pagination
    tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "tasks": tasks,
        "total": total,
        "completed_count": completed_count,
        "pending_count": pending_count
    }


@router.get("/daily", response_model=TaskList)
def get_daily_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Hole alle Tasks für heute (fällig heute oder überfällig).
    """
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    query = db.query(Task).filter(
        and_(
            Task.completed == False,
            or_(
                and_(Task.due_date >= today_start, Task.due_date < today_end),
                Task.due_date < today_start  # Overdue tasks
            )
        )
    )
    
    # Filter by user_id
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Task.user_id == current_user.id)
    
    tasks = query.order_by(Task.priority.desc(), Task.due_date.asc()).all()
    
    return {
        "tasks": tasks,
        "total": len(tasks),
        "completed_count": 0,
        "pending_count": len(tasks)
    }


@router.get("/weekly", response_model=TaskList)
def get_weekly_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Hole alle Tasks für diese Woche.
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = today + timedelta(days=7)
    
    query = db.query(Task).filter(
        and_(
            Task.completed == False,
            Task.due_date.isnot(None),
            Task.due_date < week_end
        )
    )
    
    # Filter by user_id
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Task.user_id == current_user.id)
    
    tasks = query.order_by(Task.due_date.asc()).all()
    
    return {
        "tasks": tasks,
        "total": len(tasks),
        "completed_count": 0,
        "pending_count": len(tasks)
    }


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Hole eine einzelne Aufgabe per ID.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Check ownership (admins can access all)
    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return task


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int, 
    task_update: TaskUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Update eine Aufgabe.
    
    Alle Felder sind optional - nur angegebene Felder werden aktualisiert.
    """
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Check ownership
    if current_user.role != UserRole.ADMIN and db_task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update nur die angegebenen Felder
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin)
):
    """
    Lösche eine Aufgabe.
    """
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Check ownership
    if current_user.role != UserRole.ADMIN and db_task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete(db_task)
    db.commit()
    return None


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Markiere eine Aufgabe als erledigt.
    """
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Check ownership
    if current_user.role != UserRole.ADMIN and db_task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db_task.completed = True
    db.commit()
    db.refresh(db_task)
    return db_task


@router.post("/{task_id}/uncomplete", response_model=TaskResponse)
def uncomplete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_user_or_admin)):
    """
    Markiere eine erledigte Aufgabe als offen.
    """
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Check ownership
    if current_user.role != UserRole.ADMIN and db_task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db_task.completed = False
    db.commit()
    db.refresh(db_task)
    return db_task
