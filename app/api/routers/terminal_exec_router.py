"""
Admin Terminal Exec Router
Async, JSON-based command execution for the "AI" terminal tab type.

This is intentionally admin-only, same trust level as the existing WebSocket
PTY terminal (terminal_pty.py) - it does NOT introduce new privilege, just a
different invocation shape: submit a shell command, get a job_id back
immediately, poll for the result. That's far more reliable for programmatic/
AI callers than driving an interactive xterm PTY through simulated keystrokes.

Job state lives in Redis (not in-process memory), because gunicorn runs
multiple worker processes - a poll request can land on a different worker
than the one that started the job.
"""
import os
import signal
import subprocess
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from core.dependencies import require_admin
from api.models.base_models import User
from services.redis_service import get_redis_service

router = APIRouter(prefix="/admin/terminal", tags=["Admin Terminal Exec"])

EXEC_TIMEOUT = 300  # seconds, hard cap per command
JOB_TTL_SECONDS = 3600  # how long a finished job's result stays fetchable
OUTPUT_CAP = 20000  # chars kept per stdout/stderr, to keep Redis entries bounded
JOB_KEY_PREFIX = "ai_exec_job:"


class ExecRequest(BaseModel):
    command: str
    cwd: Optional[str] = None  # relative to repo root; must not escape it


class ExecJob(BaseModel):
    job_id: str
    command: str
    status: str  # "running" | "done" | "error" | "timeout"
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    started_at: str
    finished_at: Optional[str] = None


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path(__file__).resolve().parent,
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        raise RuntimeError(f"Not a git repository: {result.stderr.strip()}")
    return Path(result.stdout.strip())


def _resolve_cwd(repo_root: Path, cwd: Optional[str]) -> Path:
    if not cwd:
        return repo_root
    candidate = (repo_root / cwd).resolve()
    if repo_root not in candidate.parents and candidate != repo_root:
        raise ValueError("cwd must stay inside the repo")
    return candidate


def _job_key(job_id: str) -> str:
    return f"{JOB_KEY_PREFIX}{job_id}"


def _save_job(job: ExecJob):
    get_redis_service().client.setex(
        _job_key(job.job_id), timedelta(seconds=JOB_TTL_SECONDS), job.model_dump_json()
    )


def _load_job(job_id: str) -> Optional[ExecJob]:
    data = get_redis_service().client.get(_job_key(job_id))
    return ExecJob.model_validate_json(data) if data else None


def _run_job(job_id: str, command: str, cwd: str):
    job = _load_job(job_id)
    if not job:
        return
    try:
        # start_new_session makes the shell the leader of its own process group,
        # so a timeout can kill the whole tree (including anything it backgrounded)
        # via os.killpg - plain process.kill() only kills the shell itself and
        # would leave orphaned children running.
        process = subprocess.Popen(
            command, shell=True, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True
        )
        try:
            stdout, stderr = process.communicate(timeout=EXEC_TIMEOUT)
            job.status = "done"
            job.exit_code = process.returncode
            job.stdout = stdout[-OUTPUT_CAP:]
            job.stderr = stderr[-OUTPUT_CAP:]
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
            job.status = "timeout"
            job.stdout = stdout[-OUTPUT_CAP:]
            job.stderr = (stderr + f"\n[Abgebrochen nach {EXEC_TIMEOUT}s Timeout, Prozessgruppe beendet]")[-OUTPUT_CAP:]
    except Exception as e:
        job.status = "error"
        job.stderr = str(e)
    job.finished_at = datetime.utcnow().isoformat()
    _save_job(job)


@router.post("/exec", response_model=ExecJob)
async def submit_exec(
    req: ExecRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin)
):
    """Submit a shell command for background execution. Returns immediately with a job_id to poll."""
    try:
        repo_root = _repo_root()
        cwd = _resolve_cwd(repo_root, req.cwd)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())
    job = ExecJob(
        job_id=job_id,
        command=req.command,
        status="running",
        started_at=datetime.utcnow().isoformat()
    )
    _save_job(job)
    background_tasks.add_task(_run_job, job_id, req.command, str(cwd))
    return job


@router.get("/exec/{job_id}", response_model=ExecJob)
async def get_exec_result(job_id: str, current_user: User = Depends(require_admin)):
    """Poll a previously submitted job for its current status/result."""
    job = _load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found (unknown id or expired)")
    return job
