"""
Sandboxed code execution for the chat "Run" button (Python/Julia), plus the
per-session workspace file list/download endpoints.

Deliberately NOT wired into the intent-detector/action-executor pattern used
for tasks/calendar/notes - code execution is higher-stakes than those, so it
stays an explicit user action (the Run button calling this endpoint with the
exact code already shown in the bubble), never something inferred from free
chat text.
"""
import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, List, Optional, Tuple

from core.dependencies import require_active_user
from core.database import get_db
from api.models.base_models import User
from services import code_sandbox
from services.session_workspace import (
    SESSION_FILES_DIR, list_session_files, resolve_workspace_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/code-exec", tags=["Code Execution"])


class RunRequest(BaseModel):
    session_id: int
    language: str
    code: str


class RunFile(BaseModel):
    name: str
    mime_type: str
    size: int
    status: str
    inline: bool = False
    inline_base64: Optional[str] = None


class RunResponse(BaseModel):
    run_id: str
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    timed_out: bool = False
    error: Optional[str] = None
    files: List[RunFile] = []


def _verify_session_ownership(db: Session, session_id: int, user_id: int) -> None:
    owned = db.execute(text("""
        SELECT id FROM chat_sessions WHERE id = :session_id AND user_id = :user_id
    """), {"session_id": session_id, "user_id": user_id}).first()
    if not owned:
        raise HTTPException(status_code=404, detail="Session not found")


# One asyncio.Lock per (user_id, session_id), created lazily - serializes
# concurrent runs *within the same session* (two overlapping runs would
# otherwise snapshot/diff the same workspace/ directory and can misattribute
# each other's output, see issue #8) while leaving different sessions fully
# parallel. Grows for the process's lifetime (one tiny entry per session
# ever run) - acceptable since the backend restarts on every deploy anyway.
_session_run_locks: Dict[Tuple[int, int], asyncio.Lock] = {}


def _get_session_run_lock(user_id: int, session_id: int) -> asyncio.Lock:
    key = (user_id, session_id)
    lock = _session_run_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _session_run_locks[key] = lock
    return lock


@router.get("/runtimes")
@router.get("/versions")
async def list_available_runtimes(
    current_user: User = Depends(require_active_user),
):
    """Listet verfügbare Sandbox-Laufzeitumgebungen (Python 3.11-3.14, Julia)."""
    return {
        "default": "python3.14",
        "runtimes": code_sandbox.AVAILABLE_RUNTIMES,
    }


@router.post("/run", response_model=RunResponse)
async def run_code(
    req: RunRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    _verify_session_ownership(db, req.session_id, current_user.id)

    session_dir = SESSION_FILES_DIR / str(current_user.id) / str(req.session_id)
    # code_sandbox.run_code() is fully synchronous (blocking subprocess.wait,
    # up to TIMEOUT_SECONDS) - asyncio.to_thread() keeps that off the ASGI
    # event loop so a long-running sandbox execution doesn't stall unrelated
    # requests/SSE traffic on this worker. The per-session lock (acquired
    # around the threaded call, not inside it) serializes same-session runs
    # without blocking other sessions' runs from proceeding concurrently.
    lock = _get_session_run_lock(current_user.id, req.session_id)
    async with lock:
        result = await asyncio.to_thread(
            code_sandbox.run_code, req.language, req.code, session_dir,
            user_id=current_user.id, session_id=req.session_id,
        )

    return RunResponse(
        run_id=result.run_id,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        timed_out=result.timed_out,
        error=result.error,
        files=[
            RunFile(
                name=f.name, mime_type=f.mime_type, size=f.size,
                status=f.status, inline=f.inline, inline_base64=f.inline_base64,
            )
            for f in result.files
        ],
    )


@router.get("/sessions/{session_id}/files")
async def get_session_files(
    session_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    _verify_session_ownership(db, session_id, current_user.id)
    return {"files": list_session_files(current_user.id, session_id)}


@router.get("/sessions/{session_id}/files/{filename:path}")
async def download_session_file(
    session_id: int,
    filename: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    _verify_session_ownership(db, session_id, current_user.id)
    resolved = resolve_workspace_file(current_user.id, session_id, filename)
    if resolved is None:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(resolved), filename=resolved.name)
