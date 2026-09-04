"""
Specialized Agent Router für L.I.A.R.A.
Verwaltet asynchrone Agent-Tasks und liefert Live-Events per Server-Sent Events (SSE).

Task state (status/result/current_step) and the event log live in Redis via
agent_task_store, not in an in-process dict - liara-backend runs multiple
gunicorn workers, and nginx has no sticky routing for /api/agents/*, so the
POST /run that starts a task and the later GET .../stream that follows it
can land on different workers. See agent_task_store.py's docstring for the
full reasoning (this replaced an in-memory-dict design that 404'd on every
stream request that didn't luck into the same worker as the POST).
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
from services import agent_task_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Specialized Agents"])

# Fire-and-forget asyncio.Task handles from start_agent_task, kept only so
# they aren't garbage-collected mid-execution (asyncio's own documented
# pitfall for tasks with no other reference) - NOT used for status lookup or
# cancellation anymore, since a later request for the same task_id can land
# on a different worker process than this one entirely.
_BACKGROUND_TASKS: set = set()


class AgentRunRequest(BaseModel):
    agent_id: str = "code"
    task: str
    session_id: Optional[int] = None
    model: Optional[str] = None
    max_steps: Optional[int] = 12
    # Nur True, wenn der Nutzer explizit einen zuvor an max_steps
    # ausgelaufenen Lauf fortsetzen will (siehe base_agent.py run()) - nie
    # automatisch anhand des Task-Texts geraten, sonst würde ein neuer,
    # unabhängiger Task versehentlich mit altem Kontext vermischt.
    resume: bool = False


class AgentTaskStatus(BaseModel):
    task_id: str
    agent_id: str
    status: str  # "running", "done", "error", "cancelled", "paused"
    task: str
    current_step: int = 0
    created_at: str
    finished_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    events: List[Dict[str, Any]] = []


@router.get("/types")
def get_available_agents(db: Session = Depends(get_db)):
    """Gibt alle verfügbaren Agenten-Profile und deren Fähigkeiten zurück."""
    return {
        "success": True,
        "agents": AgentRegistry.list_agents(db=db)
    }


async def _run_agent_task_worker(
    task_id: str,
    agent: BaseAgent,
    task_prompt: str,
    user_id: int,
    session_id: Optional[int],
    resume: bool = False
):
    async def event_callback(event: Dict[str, Any]):
        timestamp = datetime.now(timezone.utc).isoformat()
        event_payload = {**event, "timestamp": timestamp}
        await asyncio.to_thread(agent_task_store.append_event, task_id, event_payload)
        if "step" in event.get("data", {}):
            await asyncio.to_thread(agent_task_store.update_task, task_id, current_step=event["data"]["step"])

    async def is_cancelled() -> bool:
        return await asyncio.to_thread(agent_task_store.is_cancel_requested, task_id)

    if await is_cancelled():
        finished_at = datetime.now(timezone.utc).isoformat()
        await asyncio.to_thread(agent_task_store.update_task, task_id, status="cancelled", finished_at=finished_at, error="Task vor Start abgebrochen")
        await asyncio.to_thread(
            agent_task_store.append_event, task_id,
            {"event": "cancelled", "data": {"message": "Task durch Benutzer vor Start abgebrochen"}, "timestamp": finished_at}
        )
        return

    await asyncio.to_thread(agent_task_store.update_task, task_id, status="running")

    try:
        result = await agent.run(
            task=task_prompt,
            user_id=user_id,
            session_id=session_id,
            callback=event_callback,
            is_cancelled=is_cancelled,
            resume=resume
        )

        finished_at = datetime.now(timezone.utc).isoformat()
        if result.get("cancelled"):
            await asyncio.to_thread(
                agent_task_store.update_task, task_id,
                status="cancelled", finished_at=finished_at, error=result.get("error")
            )
        elif result.get("paused"):
            # Schritt-Budget erreicht, aber kein Fehlschlag - eine
            # Fortsetzungs-Zusammenfassung wurde bereits gespeichert
            # (base_agent.py), ein Folge-Run mit resume=True knüpft daran an.
            await asyncio.to_thread(
                agent_task_store.update_task, task_id,
                status="paused", finished_at=finished_at, error=result.get("error")
            )
        elif result.get("success"):
            await asyncio.to_thread(
                agent_task_store.update_task, task_id,
                status="done", finished_at=finished_at, result=result.get("answer")
            )
        else:
            await asyncio.to_thread(
                agent_task_store.update_task, task_id,
                status="error", finished_at=finished_at, error=result.get("error")
            )

    except asyncio.CancelledError:
        # Only reachable if something cancels our own asyncio.Task directly
        # (e.g. a worker shutting down) - the normal user-facing cancel path
        # is the cooperative is_cancelled() flag checked inside agent.run().
        finished_at = datetime.now(timezone.utc).isoformat()
        await asyncio.to_thread(agent_task_store.update_task, task_id, status="cancelled", finished_at=finished_at)
        await asyncio.to_thread(
            agent_task_store.append_event, task_id,
            {"event": "cancelled", "data": {"message": "Task durch Benutzer abgebrochen"}, "timestamp": finished_at}
        )
    except Exception as e:
        logger.exception(f"Unerwarteter Fehler im Agenten-Task {task_id}")
        finished_at = datetime.now(timezone.utc).isoformat()
        await asyncio.to_thread(agent_task_store.update_task, task_id, status="error", finished_at=finished_at, error=str(e))
        await asyncio.to_thread(
            agent_task_store.append_event, task_id,
            {"event": "error", "data": {"error": str(e)}, "timestamp": finished_at}
        )


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
    if not req.task.strip() and not req.resume:
        raise HTTPException(status_code=400, detail="Aufgabenstellung (task) darf nicht leer sein.")

    try:
        agent = AgentRegistry.create_agent(
            agent_id=req.agent_id,
            user_id=user.id,
            session_id=req.session_id,
            model=req.model,
            max_steps=req.max_steps,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task_id = uuid.uuid4().hex
    task_entry = agent_task_store.create_task(task_id, req.agent_id, req.task, user.id, req.session_id)

    # Fire-and-forget: execution stays in whichever worker handled this
    # request (same as before), only the STATE is now cross-worker-visible
    # via Redis. _BACKGROUND_TASKS just prevents GC of the running task.
    async_task = asyncio.create_task(
        _run_agent_task_worker(task_id, agent, req.task, user.id, req.session_id, resume=req.resume)
    )
    _BACKGROUND_TASKS.add(async_task)
    async_task.add_done_callback(_BACKGROUND_TASKS.discard)

    return {
        "success": True,
        "task_id": task_id,
        "agent_id": req.agent_id,
        "status": "running",
        "created_at": task_entry["created_at"]
    }


@router.get("/tasks/{task_id}")
def get_task_status(
    task_id: str,
    user: User = Depends(require_active_user)
):
    """Liefert den aktuellen Status und Verlauf eines Agenten-Tasks."""
    task_entry = agent_task_store.get_task(task_id)
    if not task_entry:
        raise HTTPException(status_code=404, detail="Task nicht gefunden.")

    # Prüfe Besitzer
    if task_entry["user_id"] != user.id and getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Task.")

    events = [event for _entry_id, event in agent_task_store.read_events_from_start(task_id)]
    return {**task_entry, "events": events}


@router.get("/tasks/{task_id}/stream")
async def stream_task_events(
    task_id: str,
    user: User = Depends(require_active_user)
):
    """
    Streamt Live-Events eines laufenden Agent-Tasks über Server-Sent Events (SSE).

    Reads from the Redis stream in agent_task_store (see its docstring) so
    this works regardless of which gunicorn worker started the task -
    replays whatever already happened via XRANGE, then tails new entries via
    blocking XREAD, re-checking the task's Redis status after each attempt to
    know when to stop (there's no in-process queue sentinel anymore).
    """
    task_entry = agent_task_store.get_task(task_id)
    if not task_entry:
        raise HTTPException(status_code=404, detail="Task nicht gefunden.")

    if task_entry["user_id"] != user.id and getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Task.")

    async def event_generator():
        last_id = "0"
        past_events = await asyncio.to_thread(agent_task_store.read_events_from_start, task_id)
        for entry_id, event in past_events:
            last_id = entry_id
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        current = await asyncio.to_thread(agent_task_store.get_task, task_id)
        if current is None or current["status"] in ("done", "error", "cancelled"):
            return

        while True:
            new_events = await asyncio.to_thread(agent_task_store.read_new_events, task_id, last_id, 30000)
            if new_events:
                for entry_id, event in new_events:
                    last_id = entry_id
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            else:
                yield ": keep-alive\n\n"

            current = await asyncio.to_thread(agent_task_store.get_task, task_id)
            if current is None or current["status"] in ("done", "error", "cancelled"):
                break

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
    """
    Fordert den Abbruch eines laufenden Agent-Tasks an (kooperativ - siehe
    BaseAgent.run()s is_cancelled-Check - da die eigentliche Task-Loop auf
    jedem beliebigen Worker laufen kann, nicht notwendigerweise diesem hier).
    """
    task_entry = agent_task_store.get_task(task_id)
    if not task_entry:
        raise HTTPException(status_code=404, detail="Task nicht gefunden.")

    if task_entry["user_id"] != user.id and getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Task.")

    if task_entry["status"] == "cancelling":
        return {"success": True, "message": "Abbruch bereits angefordert."}

    if task_entry["status"] not in ("pending", "running"):
        return {"success": False, "message": "Task läuft nicht mehr."}

    agent_task_store.request_cancel(task_id)
    agent_task_store.update_task(task_id, status="cancelling")
    now_iso = datetime.now(timezone.utc).isoformat()
    agent_task_store.append_event(
        task_id,
        {"event": "status", "data": {"status": "cancelling", "message": "Abbruch angefordert"}, "timestamp": now_iso}
    )
    return {"success": True, "message": "Abbruch angefordert."}
