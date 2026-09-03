"""
Workspace Live Preview - "Browser im Browser" for the sandboxed Workspace
terminal (workspace_terminal.py). Lets a dev server started inside the
sandbox (npm run dev, vite, python3 -m http.server, ...) be embedded as an
iframe in the frontend, even though that server's socket lives inside the
sandbox's own isolated network namespace and is otherwise unreachable.

Layering (see scripts/preview_daemon.py's own docstring for the full
reasoning on *why* it's split this way):
  1. scripts/preview_daemon.py (root, sudoers-whitelisted) - the ONLY
     privileged piece. Relays raw TCP bytes between a normal localhost
     socket in the host namespace and 127.0.0.1:<inside_port> inside the
     target sandbox process's namespace. Nothing HTTP-aware in there at all.
  2. This router (unprivileged, runs as the backend's own OS user) - finds
     the session's sandbox PID, starts/stops that daemon via sudo, and
     reverse-proxies ordinary HTTP requests to the daemon's local port. All
     the auth/session-ownership/path logic lives here, in normal, reviewable
     application code - the privileged script never sees a URL.

Required sudoers rule (added manually via `sudo visudo` - NOT something
this codebase or update.sh ever writes to /etc/sudoers.d itself, same as
the existing liara-runner rule):

    mirko ALL=(root) NOPASSWD: /opt/liara/venv314/bin/python3 /opt/liara/app/scripts/preview_daemon.py *

(Replace `mirko` with whatever OS user actually runs the gunicorn workers,
and the venv path with the real interpreter path, on the target host.)
Sudoers can only pin the *script path*, not validate the arguments that
follow `*` - that validation happens inside preview_daemon.py itself
(_resolve_runner_pid, port range checks), the same division of
responsibility run_sandboxed.sh already uses.

Finding which sandbox process to bridge into: workspace_terminal.py stores
the PID of the `sudo -n -u liara-runner -- ...` monitor process it forks
for each connected shell in Redis (key workspace_shell_pid:<session_id>),
cleared when that WebSocket disconnects. This router just reads that back -
it does NOT try to independently rediscover "which liara-runner process
belongs to this session" via psutil, because it can't: a bare `bash --norc
-i` has no session-identifying string in its own cmdline, and reading its
cwd cross-uid raises psutil.AccessDenied for this unprivileged process (this
was tried and failed live - see git history). preview_daemon.py, running as
root, has no such permission barrier and does the actual sudo-monitor ->
real-liara-runner-descendant resolution itself.

Per-session state (which local port a running daemon is listening on) is
kept in Redis, not an in-process dict - gunicorn runs multiple worker
processes, and the proxy request for a given session can land on a
different worker than the one that started its daemon.
"""
import asyncio
import logging
import os
import secrets
import subprocess
import time
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import require_active_user
from core.security import verify_access_token
from api.models.base_models import User
from services.redis_service import get_redis_service

router = APIRouter(prefix="/workspace", tags=["Workspace Preview"])
logger = logging.getLogger(__name__)

DAEMON_SCRIPT = str(Path(__file__).resolve().parent.parent.parent / "scripts" / "preview_daemon.py")
PYTHON_BIN = os.sys.executable
PIDFILE_DIR = Path("/opt/liara/preview_daemons")  # created here (mirko-owned, like the rest of /opt/liara); root writes pidfiles into it fine regardless of ownership

REDIS_KEY_PREFIX = "workspace_preview:"
REDIS_TTL_SECONDS = 25 * 60  # slightly longer than preview_daemon.py's own 20min idle exit
DAEMON_STARTUP_TIMEOUT = 5.0

# An <iframe src="..."> load, and every subresource request the embedded
# page then makes on its own (JS, CSS, its own XHR/fetch calls, HMR
# websocket) can't carry a custom Authorization header - only whatever the
# browser attaches automatically. core/dependencies.py's get_current_user_ws
# already rules out a query-string token for exactly this class of route
# ("far more likely to leak into reverse-proxy/access logs, browser
# diagnostics, or monitoring than a protocol value") - and a query token
# would only cover the *first* request anyway, since the dev server's own
# HTML/JS has no reason to propagate it onto every asset URL it emits. A
# short-lived, narrowly-scoped cookie (opaque token, not the user's real
# JWT) solves both: browsers attach cookies to every same-path request
# automatically, and even if it leaked, it grants nothing but this one
# session's preview iframe for a few minutes.
PREVIEW_COOKIE_NAME = "liara_ws_preview"
PREVIEW_TOKEN_REDIS_PREFIX = "workspace_preview_token:"

# Hop-by-hop headers per RFC 7230 6.1 - never forwarded either direction,
# same list any reverse proxy needs to strip.
HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "content-length", "host",
}


def _session_owned(db, session_id: int, user_id: int) -> bool:
    row = db.execute(
        text("SELECT id FROM chat_sessions WHERE id = :session_id AND user_id = :user_id"),
        {"session_id": session_id, "user_id": user_id},
    ).first()
    return row is not None


def _authorize_preview_request(request: Request, session_id: int, db: Session) -> None:
    """Raises HTTPException(401/403) unless this request is allowed to load
    session_id's preview content - via a real Authorization Bearer header
    (e.g. a direct API call/test) or the short-lived preview cookie
    start_preview() sets (the normal iframe path - see PREVIEW_COOKIE_NAME's
    module-level comment for why a cookie and not a query token)."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        payload = verify_access_token(auth_header[7:].strip())
        user_id = payload.get("user_id") if payload else None
        if user_id is not None and _session_owned(db, session_id, user_id):
            return
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diese Session")

    token = request.cookies.get(PREVIEW_COOKIE_NAME)
    if token:
        entry = get_redis_service().get_cached_json(f"{PREVIEW_TOKEN_REDIS_PREFIX}{token}")
        if entry and entry.get("session_id") == session_id:
            return

    raise HTTPException(status_code=401, detail="Keine gültige Preview-Authentifizierung - /preview/start erneut aufrufen.")


def _find_session_shell_sudo_pid(session_id: int) -> Optional[int]:
    """Reads back the sudo-monitor PID workspace_terminal.py stored for this
    session's currently-connected shell (see module docstring above) - None
    if no shell is connected right now."""
    entry = get_redis_service().get_cached_json(f"workspace_shell_pid:{session_id}")
    return entry.get("sudo_pid") if entry else None


def _pick_free_local_port() -> int:
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


async def _wait_until_connectable(port: int, timeout: float) -> bool:
    import socket
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", port), timeout=0.5
            )
            writer.close()
            return True
        except (ConnectionRefusedError, OSError, asyncio.TimeoutError):
            await asyncio.sleep(0.2)
    return False


async def _start_daemon(session_id: int, inside_port: int) -> int:
    """Always starts a fresh preview_daemon.py and returns its local port -
    called both for a first-ever preview and to replace a stale/dead one
    (see proxy_preview's retry-on-ConnectError below). No liveness probing
    of the *old* daemon here on purpose: signalling a root-owned process
    from this unprivileged worker isn't possible (PermissionError either
    way, alive or dead), so "is it still there" is answered empirically by
    whoever actually tries to connect to it, not guessed at up front."""
    sudo_pid = _find_session_shell_sudo_pid(session_id)
    if sudo_pid is None:
        raise HTTPException(
            status_code=409,
            detail="Keine laufende Workspace-Shell für diese Session gefunden - Terminal-Tab öffnen und den Dev-Server starten, bevor die Preview geladen wird."
        )

    local_port = _pick_free_local_port()
    # mkdir here (unprivileged mirko), not inside preview_daemon.py: this
    # process needs the directory to exist too, to open logfile below,
    # before the root-run daemon ever starts - and since /opt/liara is
    # already mirko-owned (same as every other path under it this backend
    # writes to), no sudo/chmod dance is needed for the directory itself,
    # only for the daemon binary's own privileged actions later.
    PIDFILE_DIR.mkdir(parents=True, exist_ok=True)
    pidfile = str(PIDFILE_DIR / f"{session_id}.pid")
    logfile = str(PIDFILE_DIR / f"{session_id}.log")

    # stdout/stderr go to a logfile, not a PIPE this process would need to
    # keep draining for the daemon's entire (up to 20min idle-timeout)
    # lifetime - the daemon outlives this request by design. Truncated
    # ("wb", not "ab") on every fresh start: this same session_id path gets
    # reused across restarts (idle-timeout, the ConnectError retry below),
    # and an ever-appended logfile across a long session's lifetime is
    # exactly the unbounded-growth trap terminal_exec_router.py's _tail()
    # comment already flags for command output - old runs' logs aren't
    # useful once a new daemon replaces them anyway.
    with open(logfile, "wb") as log_f:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "-n", PYTHON_BIN, DAEMON_SCRIPT, "start",
            str(sudo_pid), str(inside_port), str(local_port), pidfile,
            stdout=log_f, stderr=log_f,
        )

    if not await _wait_until_connectable(local_port, DAEMON_STARTUP_TIMEOUT):
        # Either the sudoers rule is missing/wrong, or the target process
        # died, or nothing's listening on inside_port yet inside the
        # sandbox - all indistinguishable from here, so surface the logfile
        # tail instead of guessing. Seeks from the end instead of
        # read_text()-ing the whole file (same reasoning as
        # terminal_exec_router.py's own _tail() - a file this code doesn't
        # itself bound the size of shouldn't ever be loaded in full just to
        # keep its last 500 bytes).
        tail = ""
        try:
            with open(logfile, "rb") as f:
                f.seek(0, os.SEEK_END)
                f.seek(max(0, f.tell() - 500))
                tail = f.read().decode("utf-8", errors="replace")
        except OSError:
            pass
        logger.error(f"preview_daemon.py did not become connectable for session {session_id}: {tail}")
        raise HTTPException(
            status_code=502,
            detail=f"Preview-Daemon nicht erreichbar geworden (Timeout). {tail}"
        )

    redis = get_redis_service()
    redis.cache_json(f"{REDIS_KEY_PREFIX}{session_id}", {
        "local_port": local_port,
        "inside_port": inside_port,
        "pidfile": pidfile,
        "sudo_pid": sudo_pid,
        "started_at": time.time(),
    }, ttl=REDIS_TTL_SECONDS)
    return local_port


async def _get_or_start_daemon(session_id: int, inside_port: int) -> int:
    """Returns the local (host-namespace) port already relaying to
    <inside_port> for this session, trusting a cached Redis entry as-is
    (see _start_daemon's docstring for why no liveness check happens here)
    and starting a fresh preview_daemon.py only if there's no cache entry
    at all or it points at a different inside_port than requested."""
    redis = get_redis_service()
    cached = redis.get_cached_json(f"{REDIS_KEY_PREFIX}{session_id}")
    if cached and cached.get("inside_port") == inside_port:
        return cached["local_port"]
    return await _start_daemon(session_id, inside_port)


@router.post("/sessions/{session_id}/preview/start")
async def start_preview(
    session_id: int,
    response: Response,
    inside_port: int = 5173,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    if not _session_owned(db, session_id, current_user.id):
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diese Session")
    local_port = await _get_or_start_daemon(session_id, inside_port)

    # New opaque token every start (not reused across sessions/calls) -
    # scoped in Redis to this exact session_id, so it authorizes nothing
    # else. Cookie path is the proxy route's own prefix only, not "/", so it
    # never gets attached to unrelated API calls.
    token = secrets.token_urlsafe(24)
    get_redis_service().cache_json(
        f"{PREVIEW_TOKEN_REDIS_PREFIX}{token}", {"session_id": session_id}, ttl=REDIS_TTL_SECONDS
    )
    response.set_cookie(
        key=PREVIEW_COOKIE_NAME,
        value=token,
        max_age=REDIS_TTL_SECONDS,
        path=f"/api/workspace/preview/{session_id}/",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return {"ok": True, "preview_url": f"/api/workspace/preview/{session_id}/", "inside_port": inside_port, "local_port": local_port}


@router.post("/sessions/{session_id}/preview/stop")
async def stop_preview(
    session_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    if not _session_owned(db, session_id, current_user.id):
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diese Session")
    redis = get_redis_service()
    key = f"{REDIS_KEY_PREFIX}{session_id}"
    cached = redis.get_cached_json(key)
    if cached:
        subprocess.run(
            ["sudo", "-n", PYTHON_BIN, DAEMON_SCRIPT, "stop", cached["pidfile"]],
            capture_output=True, timeout=5,
        )
        redis.client.delete(key)
    return {"ok": True}


@router.api_route("/preview/{session_id}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def proxy_preview(
    session_id: int,
    path: str,
    request: Request,
    db: Session = Depends(get_db),
):
    # Deliberately not Depends(require_active_user) here - see
    # _authorize_preview_request's own docstring. This route is the one
    # actually loaded *inside* the iframe, including every subresource
    # request the embedded page makes on its own, none of which can carry a
    # custom Authorization header.
    _authorize_preview_request(request, session_id, db)

    redis = get_redis_service()
    cache_key = f"{REDIS_KEY_PREFIX}{session_id}"
    cached = redis.get_cached_json(cache_key)
    if not cached:
        raise HTTPException(status_code=409, detail="Keine aktive Preview für diese Session - erst /preview/start aufrufen.")

    forward_headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}
    body = await request.body()

    # One retry-with-restart: the cached daemon may have idle-timed-out
    # (preview_daemon.py's own 20min cutoff) since it was started, in which
    # case its port is simply refused now - restart it once transparently
    # instead of making the user manually hit "Start Preview" again for
    # something that looks, from their side, like it should just still work.
    for attempt in (1, 2):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                upstream = await client.request(
                    request.method, f"http://127.0.0.1:{cached['local_port']}/{path}",
                    params=request.query_params, headers=forward_headers, content=body,
                )
            break
        except httpx.ConnectError:
            if attempt == 2:
                raise HTTPException(status_code=502, detail="Preview-Server antwortet nicht (läuft der Dev-Server im Workspace-Terminal noch?)")
            redis.client.delete(cache_key)
            new_port = await _start_daemon(session_id, cached["inside_port"])
            cached = {**cached, "local_port": new_port}

    response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}
    return StreamingResponse(
        iter([upstream.content]),
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
