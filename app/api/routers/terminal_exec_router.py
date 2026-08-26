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
import json
import logging
import os
import re
import signal
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from core.dependencies import require_admin
from api.models.base_models import User
from services.redis_service import get_redis_service

router = APIRouter(prefix="/admin/terminal", tags=["Admin Terminal Exec"])

EXEC_TIMEOUT = 300  # seconds, hard cap per command
JOB_TTL_SECONDS = 3600  # how long a finished job's result stays fetchable
OUTPUT_CAP = 20000  # bytes kept per stdout/stderr (tail), to keep Redis entries bounded
JOB_KEY_PREFIX = "ai_exec_job:"
AUDIT_LOG_PATH = "/var/log/liara/ai_exec_audit.log"

logger = logging.getLogger(__name__)

# Separate logger so this never mixes into general app logs and is easy to
# grep/ship independently. Deliberately does NOT include stdout/stderr - those
# can contain secrets, and this log is meant to be kept far longer than the
# 1h Redis TTL on the job result itself.
audit_logger = logging.getLogger("ai_exec_audit")
if not audit_logger.handlers:
    try:
        _handler = logging.FileHandler(AUDIT_LOG_PATH)
        _handler.setFormatter(logging.Formatter("%(message)s"))
        audit_logger.addHandler(_handler)
        audit_logger.setLevel(logging.INFO)
        audit_logger.propagate = False
    except OSError as e:
        # e.g. /var/log/liara doesn't exist on this machine (local dev) -
        # audit logging is best-effort, never worth failing a job over, but
        # silently losing the whole audit trail shouldn't go completely
        # unnoticed either - surface it in the normal app log.
        logger.warning(f"AI-exec audit log disabled, could not open {AUDIT_LOG_PATH}: {e}")


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
    user_id: Optional[int] = None
    username: Optional[str] = None


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
    """Raw Redis write. Raises redis.RedisError on failure - callers decide how to handle it."""
    get_redis_service().client.setex(
        _job_key(job.job_id), timedelta(seconds=JOB_TTL_SECONDS), job.model_dump_json()
    )


def _load_job(job_id: str) -> Optional[ExecJob]:
    """Raw Redis read. Raises redis.RedisError on failure - callers decide how to handle it."""
    data = get_redis_service().client.get(_job_key(job_id))
    return ExecJob.model_validate_json(data) if data else None


def _tail(file_obj, n: int) -> str:
    """Last n bytes of a binary temp file, decoded leniently."""
    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(max(0, size - n))
    return file_obj.read().decode("utf-8", errors="replace")


_SECRET_KEY_WORD = r'(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)'

# Redacts common secret-bearing CLI forms before they reach the long-lived
# audit log (issue #10) - stdout/stderr are already excluded, but the raw
# command itself frequently carries secrets directly (curl auth headers,
# --password/--token flags, export FOO_KEY=..., credentials embedded in a
# connection-string URL). Best-effort by design: this is pattern matching on
# free-form shell text, not a shell parser - it catches the common,
# documented forms, not an exhaustive guarantee.
_SECRET_PATTERNS = [
    # key=value / key="value" - env assignments, --flag=value, URL query params
    re.compile(rf'(?i)((?:--)?(?:export\s+)?{_SECRET_KEY_WORD}[a-z0-9_]*\s*=\s*)(["\']?)(\S+?)(\2)(?=\s|$)'),
    # --flag value / -flag value - space-separated CLI args
    re.compile(rf'(?i)(--?{_SECRET_KEY_WORD}[a-z0-9_-]*\s+)(["\']?)(\S+?)(\2)(?=\s|$)'),
    # Authorization: Bearer/Basic <value> header (typically curl -H "...")
    re.compile(r'(?i)(authorization["\']?\s*:?\s*(?:bearer|basic)\s+)(\S+)'),
    # credentials embedded in a URL: scheme://user:PASSWORD@host (DB
    # connection strings, git remotes with an embedded token, etc.)
    re.compile(r'(?i)(://[^\s:/@]+:)([^\s@/]+)(@)'),
]


def _redact_secrets(command: str) -> str:
    redacted = command
    for pattern in _SECRET_PATTERNS[:2]:
        redacted = pattern.sub(lambda m: m.group(1) + m.group(2) + "***REDACTED***" + m.group(2), redacted)
    redacted = _SECRET_PATTERNS[2].sub(lambda m: m.group(1) + "***REDACTED***", redacted)
    redacted = _SECRET_PATTERNS[3].sub(lambda m: m.group(1) + "***REDACTED***" + m.group(3), redacted)
    return redacted


def _write_audit_log(job: ExecJob, cwd: str):
    """
    Append-only audit trail, kept separately from the ephemeral Redis job
    result. Intentionally excludes stdout/stderr (may contain secrets) - just
    who ran what, when, and how it ended. The command itself is redacted
    (see _redact_secrets) since this log persists far longer than the 1h
    Redis job TTL; the unredacted command stays in Redis, already protected
    by the job-owner check in get_exec_result().
    """
    try:
        audit_logger.info(json.dumps({
            "job_id": job.job_id,
            "user_id": job.user_id,
            "username": job.username,
            "command": _redact_secrets(job.command),
            "cwd": cwd,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "status": job.status,
            "exit_code": job.exit_code,
        }))
    except Exception as e:
        # Best-effort - never worth failing a job over - but not worth losing
        # silently either.
        logger.warning(f"AI-exec audit log write failed for job {job.job_id}: {e}")


def _run_job(job_id: str, command: str, cwd: str):
    try:
        job = _load_job(job_id)
    except redis.RedisError:
        # Nothing we can do here - there's no HTTP response to send from a
        # background task. submit_exec already returned the job to the
        # caller before this runs; if Redis is gone now, the poll endpoint
        # will surface the 503 on its own next call.
        return
    if not job:
        return

    # Output goes straight to temp files instead of subprocess.PIPE: PIPE +
    # capture_output/communicate() buffers the *entire* output in this
    # process's RAM before any truncation happens, so a sufficiently chatty
    # command could exhaust memory even though only OUTPUT_CAP bytes end up
    # kept. Temp files push that cost to disk instead, and _tail() only ever
    # reads the last OUTPUT_CAP bytes back into memory.
    with tempfile.TemporaryFile() as stdout_f, tempfile.TemporaryFile() as stderr_f:
        try:
            # start_new_session makes the shell the leader of its own process
            # group, so a timeout can kill the whole tree (including anything
            # it backgrounded) via os.killpg - plain process.kill() only
            # kills the shell itself and would leave orphaned children running.
            process = subprocess.Popen(
                command, shell=True, cwd=cwd,
                stdout=stdout_f, stderr=stderr_f,
                start_new_session=True
            )
            try:
                process.wait(timeout=EXEC_TIMEOUT)
                job.status = "done"
                job.exit_code = process.returncode
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                job.status = "timeout"

            job.stdout = _tail(stdout_f, OUTPUT_CAP)
            job.stderr = _tail(stderr_f, OUTPUT_CAP)
            if job.status == "timeout":
                job.stderr = (job.stderr + f"\n[Abgebrochen nach {EXEC_TIMEOUT}s Timeout, Prozessgruppe beendet]")[-OUTPUT_CAP:]
        except Exception as e:
            job.status = "error"
            job.stderr = str(e)

    job.finished_at = datetime.utcnow().isoformat()
    try:
        _save_job(job)
    except redis.RedisError:
        pass  # see comment above - nothing to do from a background task
    _write_audit_log(job, cwd)


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
        started_at=datetime.utcnow().isoformat(),
        user_id=current_user.id,
        username=current_user.username
    )
    try:
        _save_job(job)
    except redis.RedisError as e:
        raise HTTPException(status_code=503, detail=f"Exec backend unavailable (Redis): {e}")
    background_tasks.add_task(_run_job, job_id, req.command, str(cwd))
    return job


@router.get("/exec/{job_id}", response_model=ExecJob)
async def get_exec_result(job_id: str, current_user: User = Depends(require_admin)):
    """
    Poll a previously submitted job for its current status/result.

    Restricted to the admin who submitted it - job_ids are unguessable
    (uuid4) in practice, but another admin knowing/leaking one shouldn't be
    enough to read a peer's command output.
    """
    try:
        job = _load_job(job_id)
    except redis.RedisError as e:
        raise HTTPException(status_code=503, detail=f"Exec backend unavailable (Redis): {e}")
    if not job:
        raise HTTPException(status_code=404, detail="Job not found (unknown id or expired)")
    if job.user_id is not None and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This job belongs to a different admin")
    return job
