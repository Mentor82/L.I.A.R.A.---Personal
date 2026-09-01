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

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import text

from core.database import SessionLocal
from core.dependencies import get_current_user_ws
from services.session_workspace import (
    SESSION_FILES_DIR,
    ensure_session_venv_dir,
    ensure_session_metadata_dir,
)

router = APIRouter(prefix="/workspace", tags=["Workspace Terminal"])

logger = logging.getLogger(__name__)

RUNNER_USER = "liara-runner"
RUNNER_SHELL_SCRIPT = str(Path(__file__).resolve().parent.parent.parent / "scripts" / "run_sandboxed_shell.sh")


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
            os.close(fd)
            os.kill(pid, 9)
            os.waitpid(pid, 0)
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
