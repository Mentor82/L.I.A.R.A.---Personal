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
    now = _now_iso()
    mapping = {
        "task_id": task_id,
        "agent_id": agent_id,
        "status": "pending",
        "task": task_text,
        "current_step": "0",
        "user_id": str(user_id),
        "session_id": str(session_id) if session_id is not None else "",
        "created_at": now,
        "finished_at": "",
        "result": "",
        "error": "",
        "cancel_requested": "0",
    }
    client = get_redis_service().client
    key = _task_key(task_id)
    client.hset(key, mapping=mapping)
    client.expire(key, TASK_TTL_SECONDS)
    return {
        "task_id": task_id,
        "agent_id": agent_id,
        "status": "pending",
        "task": task_text,
        "current_step": 0,
        "user_id": user_id,
        "session_id": session_id,
        "created_at": now,
        "finished_at": None,
        "result": None,
        "error": None,
        "cancel_requested": False,
    }


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    client = get_redis_service().client
    raw = client.hgetall(_task_key(task_id))
    if not raw:
        return None

    data = {
        (k.decode("utf-8") if isinstance(k, bytes) else k): (v.decode("utf-8") if isinstance(v, bytes) else v)
        for k, v in raw.items()
    }
    if not data or "task_id" not in data:
        return None

    session_id_str = data.get("session_id", "")
    session_id = int(session_id_str) if session_id_str else None

    result_raw = data.get("result", "")
    result_val = None
    if result_raw:
        try:
            result_val = json.loads(result_raw)
        except Exception:
            result_val = result_raw

    return {
        "task_id": data.get("task_id", task_id),
        "agent_id": data.get("agent_id", ""),
        "status": data.get("status", "pending"),
        "task": data.get("task", ""),
        "current_step": int(data.get("current_step", 0)),
        "user_id": int(data.get("user_id", 0)),
        "session_id": session_id,
        "created_at": data.get("created_at"),
        "finished_at": data.get("finished_at") or None,
        "result": result_val,
        "error": data.get("error") or None,
        "cancel_requested": data.get("cancel_requested") in ("1", "true", "True", True),
    }


def update_task(task_id: str, **fields: Any) -> None:
    """Atomic field-level updates via Redis Hashes (HSET).
    
    Eliminates read-modify-write races across concurrent workers.
    Updates to fields like current_step by a running worker cannot
    overwrite or clear a concurrent cancel_requested=True written
    by a cancellation request on another worker.
    """
    if not fields:
        return
    client = get_redis_service().client
    key = _task_key(task_id)
    if not client.exists(key):
        return

    mapping = {}
    for k, v in fields.items():
        if v is None:
            mapping[k] = ""
        elif isinstance(v, bool):
            mapping[k] = "1" if v else "0"
        elif isinstance(v, (int, float, str)):
            mapping[k] = str(v)
        else:
            mapping[k] = json.dumps(v, ensure_ascii=False)

    client.hset(key, mapping=mapping)
    client.expire(key, TASK_TTL_SECONDS)


def request_cancel(task_id: str) -> bool:
    """Atomically sets cancel_requested=1 in the task Hash."""
    client = get_redis_service().client
    key = _task_key(task_id)
    if not client.exists(key):
        return False
    client.hset(key, mapping={"cancel_requested": "1"})
    client.expire(key, TASK_TTL_SECONDS)
    return True


def is_cancel_requested(task_id: str) -> bool:
    """Atomically reads the cancel_requested field."""
    client = get_redis_service().client
    val = client.hget(_task_key(task_id), "cancel_requested")
    if val is None:
        return False
    if isinstance(val, bytes):
        val = val.decode("utf-8")
    return val in ("1", "true", "True")


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
