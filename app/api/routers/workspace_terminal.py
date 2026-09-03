"""
🖥️ Workspace WebSocket PTY Terminal

Full interactive shell inside the same sandbox the one-shot "Ausführen"
button uses (services/code_sandbox.py) - runs as the unprivileged
liara-runner OS user via run_sandboxed_shell.sh, network-isolated, cwd'd
into one chat session's own Workspace directory with that session's own
Python venv on PATH. Session-ownership checked like every other Workspace
endpoint (not admin-gated like terminal_pty.py - this is a regular
per-user feature, scoped to the caller's own session).

Same bidirectional I/O loop shape as terminal_pty.py (pty.fork() + a
select()-driven read/write loop) - that file execs a raw shell directly;
this one execs `sudo -n -u liara-runner -- run_sandboxed_shell.sh
<workspace_dir>` instead, so the actual shell the user gets is the
sandboxed one, not the backend's own OS user.
"""
import asyncio
import fcntl
import logging
import os
import pty
import select
import struct
import termios
from pathlib import Path

import signal
import subprocess
import time
import psutil
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import SessionLocal, get_db
from core.dependencies import get_current_user_ws, require_active_user
from api.models.base_models import User
from services.session_workspace import (
    SESSION_FILES_DIR,
    ensure_session_venv_dir,
    ensure_session_metadata_dir,
)
from services.redis_service import get_redis_service

# Key a running shell's PID lives under while connected - read by
# workspace_preview.py to find which sandbox netns to bridge into, without
# needing to re-derive "which liara-runner process belongs to this session"
# via psutil (a bare `bash --norc -i` has no session-identifying info in its
# own cmdline, and reading its cwd cross-uid raises psutil.AccessDenied - see
# workspace_preview.py's module docstring for the fuller reasoning). No TTL:
# cleared explicitly in the finally block below, for exactly the lifetime of
# one connected WebSocket.
SHELL_PID_REDIS_PREFIX = "workspace_shell_pid:"

router = APIRouter(prefix="/workspace", tags=["Workspace Terminal"])

logger = logging.getLogger(__name__)

RUNNER_USER = "liara-runner"
RUNNER_SHELL_SCRIPT = str(Path(__file__).resolve().parent.parent.parent / "scripts" / "run_sandboxed_shell.sh")


@router.get("/sessions/{session_id}/processes")
async def list_session_processes(
    session_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    """Listet alle aktiven Sandbox-Prozesse für die gegebene Workspace-Session."""
    if not _session_owned(db, session_id, current_user.id):
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diese Session")

    session_marker = f"/session_files/{current_user.id}/{session_id}"
    now = time.time()
    processes = []

    for p in psutil.process_iter(['pid', 'name', 'username', 'cmdline', 'create_time', 'memory_info']):
        try:
            info = p.info
            if info.get('username') == RUNNER_USER:
                cmd_list = info.get('cmdline') or []
                cmd_str = " ".join(cmd_list)
                is_this_session = session_marker in cmd_str
                try:
                    cwd = p.cwd()
                    if session_marker in cwd:
                        is_this_session = True
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass

                # Also match if cmdline is a workspace python / bash runner
                if is_this_session:
                    create_t = info.get('create_time') or now
                    age_s = max(0, int(now - create_t))
                    mem_mb = round((info['memory_info'].rss if info.get('memory_info') else 0) / (1024 * 1024), 1)

                    # Extract concise display command
                    display_cmd = cmd_str
                    if "python" in info['name'] or "script.py" in cmd_str:
                        # find target script
                        parts = cmd_str.split()
                        for part in reversed(parts):
                            if part.endswith(('.py', '.jl', '.sh')):
                                display_cmd = f"{info['name']} {Path(part).name}"
                                break

                    processes.append({
                        "pid": info['pid'],
                        "name": info['name'],
                        "cmdline": display_cmd[:100],
                        "full_cmdline": cmd_str[:250],
                        "created_at": create_t,
                        "running_seconds": age_s,
                        "memory_mb": mem_mb,
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return {"processes": processes, "count": len(processes)}


def _kill_runner_process(workspace_dir: Path, pid: int) -> bool:
    try:
        proc = psutil.Process(pid)
        if proc.username() != RUNNER_USER:
            return False
    except psutil.NoSuchProcess:
        return True

    # 1. Direct kill attempt
    try:
        os.kill(pid, signal.SIGKILL)
        return True
    except (PermissionError, ProcessLookupError):
        pass

    # 2. Invoke manage_venv.sh kill via sudo
    manage_script = str(Path(__file__).resolve().parent.parent.parent / "scripts" / "manage_venv.sh")
    try:
        res = subprocess.run(
            ["sudo", "-n", "-u", RUNNER_USER, "--", manage_script, str(workspace_dir), "kill", str(pid)],
            capture_output=True,
            timeout=5,
        )
        return res.returncode == 0
    except Exception as e:
        logger.error(f"Failed to kill runner process {pid}: {e}")
        return False


@router.post("/sessions/{session_id}/processes/{pid}/kill")
async def kill_session_process(
    session_id: int,
    pid: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    """Beendet einen aktiven Sandbox-Prozess."""
    if not _session_owned(db, session_id, current_user.id):
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diese Session")

    session_dir = SESSION_FILES_DIR / str(current_user.id) / str(session_id)
    workspace_dir = session_dir / "workspace"

    success = _kill_runner_process(workspace_dir, pid)
    if not success:
        raise HTTPException(status_code=500, detail=f"Prozess {pid} konnte nicht beendet werden")
    return {"ok": True, "message": f"Prozess {pid} erfolgreich beendet"}


@router.post("/sessions/{session_id}/processes/kill-all")
async def kill_all_session_processes(
    session_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    """Beendet alle aktiven Sandbox-Prozesse dieser Session."""
    if not _session_owned(db, session_id, current_user.id):
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diese Session")

    session_dir = SESSION_FILES_DIR / str(current_user.id) / str(session_id)
    workspace_dir = session_dir / "workspace"
    session_marker = f"/session_files/{current_user.id}/{session_id}"
    killed_count = 0

    for p in psutil.process_iter(['pid', 'username', 'cmdline']):
        try:
            if p.info.get('username') == RUNNER_USER:
                cmd_str = " ".join(p.info.get('cmdline') or [])
                is_this_session = session_marker in cmd_str
                try:
                    if session_marker in p.cwd():
                        is_this_session = True
                except Exception:
                    pass

                if is_this_session:
                    if _kill_runner_process(workspace_dir, p.info['pid']):
                        killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return {"ok": True, "killed_count": killed_count}


def _session_owned(db, session_id: int, user_id: int) -> bool:
    row = db.execute(
        text("SELECT id FROM chat_sessions WHERE id = :session_id AND user_id = :user_id"),
        {"session_id": session_id, "user_id": user_id},
    ).first()
    return row is not None


@router.websocket("/sessions/{session_id}/terminal/ws")
async def workspace_terminal_ws(websocket: WebSocket, session_id: int):
    # Auth before accept() - same reasoning as terminal_pty.py: a rejected
    # handshake never creates any PTY/sandbox state, and closing pre-accept
    # makes uvicorn deny the WS upgrade at the protocol level.
    auth_db = SessionLocal()
    try:
        user = await get_current_user_ws(websocket, auth_db)
    except Exception as e:
        logger.error(f"Workspace terminal WS auth failed: {e}")
        await websocket.close(code=1008)
        return
    finally:
        auth_db.close()

    owned_db = SessionLocal()
    try:
        owned = _session_owned(owned_db, session_id, user.id)
    finally:
        owned_db.close()
    if not owned:
        await websocket.close(code=1008)
        return

    offered_protocol = websocket.headers.get("sec-websocket-protocol", "").split(",")[0].strip() or None
    await websocket.accept(subprotocol=offered_protocol)

    session_dir = SESSION_FILES_DIR / str(user.id) / str(session_id)
    workspace_dir = session_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # liara-runner needs execute/traverse permission on every ancestor
    # directory to reach workspace_dir at all, and write access to
    # workspace_dir itself - same reasoning as code_sandbox.py's run_code().
    for ancestor in (SESSION_FILES_DIR, session_dir.parent, session_dir):
        try:
            os.chmod(ancestor, 0o755)
        except OSError:
            pass
    os.chmod(workspace_dir, 0o777)
    ensure_session_venv_dir(session_dir)
    ensure_session_metadata_dir(session_dir)

    shell_cmd = ["sudo", "-n", "-u", RUNNER_USER, "--", RUNNER_SHELL_SCRIPT, str(workspace_dir)]

    try:
        pid, fd = pty.fork()
    except OSError as e:
        logger.error(f"Workspace terminal pty.fork() failed: {e}")
        await websocket.send_json({"type": "error", "data": str(e)})
        await websocket.close()
        return

    if pid == 0:
        os.execvp(shell_cmd[0], shell_cmd)
        os._exit(1)  # only reached if execvp itself failed

    # `pid` here is sudo's own monitor process (this is *our* direct child
    # from pty.fork(), still in the backend's own default namespace - sudo
    # forks again internally to actually become liara-runner). Stored as-is,
    # not resolved further: preview_daemon.py runs as root and can freely
    # walk sudo's process tree to find the real liara-runner descendant and
    # its netns, which this unprivileged handler cannot (reading another
    # uid's /proc/<pid>/cwd raises psutil.AccessDenied here, but not for
    # root).
    redis = get_redis_service()
    redis.cache_json(f"{SHELL_PID_REDIS_PREFIX}{session_id}", {"sudo_pid": pid}, ttl=24 * 60 * 60)

    try:
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        while True:
            ready, _, _ = select.select([fd], [], [], 0.01)

            if fd in ready:
                try:
                    output = os.read(fd, 1024)
                    if output:
                        await websocket.send_json({"type": "data", "data": output.decode("utf-8", errors="replace")})
                    else:
                        break  # EOF - shell exited
                except OSError:
                    break

            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=0.01)
                msg_type = message.get("type")

                if msg_type == "data":
                    os.write(fd, message.get("data", "").encode("utf-8"))
                elif msg_type == "resize":
                    rows = message.get("rows", 30)
                    cols = message.get("cols", 120)
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.error(f"Workspace terminal PTY error: {e}")
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except Exception:
            pass
    finally:
        try:
            redis.client.delete(f"{SHELL_PID_REDIS_PREFIX}{session_id}")
        except Exception:
            pass
        try:
            os.close(fd)
            os.kill(pid, 9)
            os.waitpid(pid, 0)
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
