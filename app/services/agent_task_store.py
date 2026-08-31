"""
Redis-backed state for Agent Hub background tasks (agent_router.py).

liara-backend runs multiple gunicorn workers (same reasoning as
terminal_exec_router.py's job store): a task started by POST /agents/run on
worker A must still be visible when nginx round-robins the follow-up GET
/agents/tasks/{id}/stream to worker B. A plain in-process dict (the previous
design) made that follow-up request 404 unless it happened to land back on
worker A - this store keeps status/result and the full event log in Redis
instead, and cancellation as a flag any worker's request can set and the
worker actually running the task's loop polls cooperatively.

Redis Streams (not Pub/Sub) for the event log: Pub/Sub is fire-and-forget - a
subscriber that isn't listening at publish time loses the message, which
would drop steps emitted in the gap between the client's POST response and
its GET .../stream request actually attaching. A Stream persists every entry
so a late-arriving reader can always XRANGE-replay what already happened
before tailing new ones via XREAD, matching the previous in-memory design's
"replay accumulated events, then keep listening" behavior.
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.redis_service import get_redis_service

TASK_TTL_SECONDS = 3600  # 1h, matches terminal_exec_router.py's JOB_TTL_SECONDS convention
TASK_KEY_PREFIX = "agent_task:"
EVENTS_KEY_PREFIX = "agent_task_events:"


def _task_key(task_id: str) -> str:
    return f"{TASK_KEY_PREFIX}{task_id}"


def _events_key(task_id: str) -> str:
    return f"{EVENTS_KEY_PREFIX}{task_id}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_task(task_id: str, agent_id: str, task_text: str, user_id: int, session_id: Optional[int]) -> Dict[str, Any]:
    task = {
        "task_id": task_id,
        "agent_id": agent_id,
        "status": "pending",
        "task": task_text,
        "current_step": 0,
        "user_id": user_id,
        "session_id": session_id,
        "created_at": _now_iso(),
        "finished_at": None,
        "result": None,
        "error": None,
        "cancel_requested": False,
    }
    get_redis_service().client.setex(_task_key(task_id), timedelta(seconds=TASK_TTL_SECONDS), json.dumps(task))
    return task


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    data = get_redis_service().client.get(_task_key(task_id))
    return json.loads(data) if data else None


def update_task(task_id: str, **fields: Any) -> None:
    """Read-modify-write - safe here because only the single worker running
    this task's agent loop ever writes status/result/error/current_step;
    request_cancel() is the only other writer and touches a different field,
    so there's no concurrent-writer race to guard against (unlike
    redis_service.py's add_to_context, which needed a Lua script)."""
    client = get_redis_service().client
    task = get_task(task_id)
    if task is None:
        return
    task.update(fields)
    client.setex(_task_key(task_id), timedelta(seconds=TASK_TTL_SECONDS), json.dumps(task))


def request_cancel(task_id: str) -> bool:
    task = get_task(task_id)
    if task is None:
        return False
    task["cancel_requested"] = True
    get_redis_service().client.setex(_task_key(task_id), timedelta(seconds=TASK_TTL_SECONDS), json.dumps(task))
    return True


def is_cancel_requested(task_id: str) -> bool:
    task = get_task(task_id)
    return bool(task and task.get("cancel_requested"))


def append_event(task_id: str, event: Dict[str, Any]) -> None:
    client = get_redis_service().client
    key = _events_key(task_id)
    client.xadd(key, {"data": json.dumps(event, ensure_ascii=False)})
    client.expire(key, TASK_TTL_SECONDS)


def read_events_from_start(task_id: str) -> List[Tuple[str, Dict[str, Any]]]:
    """All events recorded so far, as (stream_id, event_dict) pairs, oldest first."""
    entries = get_redis_service().client.xrange(_events_key(task_id))
    return [(entry_id, json.loads(fields["data"])) for entry_id, fields in entries]


def read_new_events(task_id: str, last_id: str, block_ms: int = 30000) -> List[Tuple[str, Dict[str, Any]]]:
    """Blocks (in the calling thread - always call via asyncio.to_thread from
    async code) up to block_ms for stream entries newer than last_id."""
    result = get_redis_service().client.xread({_events_key(task_id): last_id}, block=block_ms, count=50)
    if not result:
        return []
    _key, entries = result[0]
    return [(entry_id, json.loads(fields["data"])) for entry_id, fields in entries]
