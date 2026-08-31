"""
Specialized Agent Router für L.I.A.R.A.
Verwaltet asynchrone Agent-Tasks und liefert Live-Events per Server-Sent Events (SSE).
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.dependencies import require_active_user
from core.database import get_db
from api.models.base_models import User
from services.agents.agent_registry import AgentRegistry
from services.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Specialized Agents"])

# In-Memory Task Registry für aktive und kürzlich beendete Agent-Läufe
# (Key: task_id -> Task-Status, Event-Queue, Result)
_ACTIVE_TASKS: Dict[str, Dict[str, Any]] = {}


class AgentRunRequest(BaseModel):
    agent_id: str = "code"
    task: str
    session_id: Optional[int] = None
    model: Optional[str] = None
    max_steps: Optional[int] = 12


class AgentTaskStatus(BaseModel):
    task_id: str
    agent_id: str
    status: str  # "running", "done", "error", "cancelled"
    task: str
    current_step: int = 0
    created_at: str
    finished_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    events: List[Dict[str, Any]] = []


@router.get("/types")
def get_available_agents():
    """Gibt alle verfügbaren Agenten-Profile und deren Fähigkeiten zurück."""
    return {
        "success": True,
        "agents": AgentRegistry.list_agents()
    }


async def _run_agent_task_worker(
    task_id: str,
    agent: BaseAgent,
    task_prompt: str,
    user_id: int,
    session_id: Optional[int]
):
    task_entry = _ACTIVE_TASKS.get(task_id)
    if not task_entry:
        return

    queue: asyncio.Queue = task_entry["queue"]

    async def event_callback(event: Dict[str, Any]):
        timestamp = datetime.now(timezone.utc).isoformat()
        event_payload = {**event, "timestamp": timestamp}
        task_entry["events"].append(event_payload)
        
        if "step" in event.get("data", {}):
            task_entry["current_step"] = event["data"]["step"]
        
        await queue.put(event_payload)

    try:
        task_entry["status"] = "running"
        result = await agent.run(
            task=task_prompt,
            user_id=user_id,
            session_id=session_id,
            callback=event_callback
        )

        task_entry["finished_at"] = datetime.now(timezone.utc).isoformat()
        if result.get("success"):
            task_entry["status"] = "done"
            task_entry["result"] = result.get("answer")
        else:
            task_entry["status"] = "error"
            task_entry["error"] = result.get("error")

    except asyncio.CancelledError:
        task_entry["status"] = "cancelled"
        task_entry["finished_at"] = datetime.now(timezone.utc).isoformat()
        await queue.put({"event": "cancelled", "data": {"message": "Task durch Benutzer abgebrochen"}})
    except Exception as e:
        logger.exception(f"Unerwarteter Fehler im Agenten-Task {task_id}")
        task_entry["status"] = "error"
        task_entry["error"] = str(e)
        task_entry["finished_at"] = datetime.now(timezone.utc).isoformat()
        await queue.put({"event": "error", "data": {"error": str(e)}})
    finally:
        # Signalisiere Stream-Ende
        await queue.put(None)


@router.post("/run")
async def start_agent_task(
    req: AgentRunRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """
    Startet einen spezialisierten Agenten-Task im Hintergrund.
    """
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="Aufgabenstellung (task) darf nicht leer sein.")

    try:
        agent = AgentRegistry.create_agent(
            agent_id=req.agent_id,
            user_id=user.id,
            session_id=req.session_id,
            model=req.model,
            max_steps=req.max_steps
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task_id = uuid.uuid4().hex
    queue: asyncio.Queue = asyncio.Queue()

    _ACTIVE_TASKS[task_id] = {
        "task_id": task_id,
        "agent_id": req.agent_id,
        "status": "pending",
        "task": req.task,
        "current_step": 0,
        "user_id": user.id,
        "session_id": req.session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "result": None,
        "error": None,
        "events": [],
        "queue": queue,
        "async_task": None
    }

    # Starte Background-Task
    async_task = asyncio.create_task(
        _run_agent_task_worker(task_id, agent, req.task, user.id, req.session_id)
    )
    _ACTIVE_TASKS[task_id]["async_task"] = async_task

    return {
        "success": True,
        "task_id": task_id,
        "agent_id": req.agent_id,
        "status": "running",
        "created_at": _ACTIVE_TASKS[task_id]["created_at"]
    }


@router.get("/tasks/{task_id}")
def get_task_status(
    task_id: str,
    user: User = Depends(require_active_user)
):
    """Liefert den aktuellen Status und Verlauf eines Agenten-Tasks."""
    task_entry = _ACTIVE_TASKS.get(task_id)
    if not task_entry:
        raise HTTPException(status_code=404, detail="Task nicht gefunden.")

    # Prüfe Besitzer
    if task_entry["user_id"] != user.id and getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Task.")

    return {
        "task_id": task_entry["task_id"],
        "agent_id": task_entry["agent_id"],
        "status": task_entry["status"],
        "task": task_entry["task"],
        "current_step": task_entry["current_step"],
        "created_at": task_entry["created_at"],
        "finished_at": task_entry["finished_at"],
        "result": task_entry["result"],
        "error": task_entry["error"],
        "events": task_entry["events"]
    }


@router.get("/tasks/{task_id}/stream")
async def stream_task_events(
    task_id: str,
    user: User = Depends(require_active_user)
):
    """
    Streamt Live-Events eines laufenden Agent-Tasks über Server-Sent Events (SSE).
    """
    task_entry = _ACTIVE_TASKS.get(task_id)
    if not task_entry:
        raise HTTPException(status_code=404, detail="Task nicht gefunden.")

    if task_entry["user_id"] != user.id and getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Task.")

    queue: asyncio.Queue = task_entry["queue"]

    async def event_generator():
        # Sende zuerst bestehende historische Events, falls der Client später joint
        for past_event in task_entry["events"]:
            yield f"data: {json.dumps(past_event, ensure_ascii=False)}\n\n"

        # Falls Task schon beendet ist, sofort schließen
        if task_entry["status"] in ("done", "error", "cancelled"):
            return

        # Neue Events aus der Queue streamen
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                if event is None:
                    # Ende des Streams
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                # Keep-alive Ping
                yield ": keep-alive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/tasks/{task_id}/cancel")
def cancel_task(
    task_id: str,
    user: User = Depends(require_active_user)
):
    """Bricht einen laufenden Agent-Task ab."""
    task_entry = _ACTIVE_TASKS.get(task_id)
    if not task_entry:
        raise HTTPException(status_code=404, detail="Task nicht gefunden.")

    if task_entry["user_id"] != user.id and getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Task.")

    async_task: Optional[asyncio.Task] = task_entry.get("async_task")
    if async_task and not async_task.done():
        async_task.cancel()
        task_entry["status"] = "cancelled"
        return {"success": True, "message": "Task abgebrochen."}

    return {"success": False, "message": "Task läuft nicht mehr."}
