"""
🖥️ WebSocket PTY Terminal
Real interactive terminal with full TTY support (su, vim, etc.)
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from api.models.base_models import User
from core.dependencies import get_current_user_ws
from core.database import SessionLocal
import pty
import os
import select
import subprocess
import struct
import fcntl
import termios
import asyncio
import logging

router = APIRouter(prefix="/admin/terminal", tags=["Admin Terminal"])

logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_pty(
    websocket: WebSocket,
):
    """
    WebSocket PTY Terminal

    Supports two connection modes:
    1. Local: Direct shell on Liara server (?type=local)
    2. SSH: Connect to remote server via SSH (?type=ssh&ssh_host=...&ssh_user=...&ssh_port=...)

    Requires admin authentication via the Sec-WebSocket-Protocol header
    (see core.dependencies.get_current_user_ws).
    """
    # Authenticate BEFORE accept() (issue #10) - websocket.headers/query_params
    # are already populated from the ASGI scope at this point, no need to
    # accept first just to read them. A rejected handshake here never
    # creates any PTY/SSH state, and closing before accept() makes uvicorn
    # deny the WS upgrade at the protocol level instead of accepting then
    # immediately closing. There's no accepted connection yet to send a JSON
    # error over - the frontend already shows a generic disconnect message
    # on any WS close (TerminalTabs.jsx), which avoids leaking str(e) to an
    # unauthenticated client as a side effect.
    #
    # A short-lived SessionLocal() is opened just for this one-time lookup,
    # not FastAPI's Depends(get_db) (same reasoning as issue #13 item 6's
    # ToolExecutor fix): that generator only closes when the whole handler
    # returns, so a request-scoped session would sit open - and idle in
    # transaction - for the PTY connection's entire life, which for an admin
    # terminal tab can be hours. That idle-in-transaction connection was
    # observed live blocking an `ALTER TABLE ... ADD COLUMN` migration (needs
    # an ACCESS EXCLUSIVE lock) until the terminal tab was closed.
    auth_db = SessionLocal()
    try:
        user = await get_current_user_ws(websocket, auth_db)
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008)  # Policy Violation
        return
    finally:
        auth_db.close()

    # Echo the offered subprotocol back (issue #10 follow-up, found live):
    # per the WebSocket spec, if the client's handshake offered a
    # Sec-WebSocket-Protocol and the server's response omits a matching
    # one, standards-compliant browsers (confirmed: Chrome) abort the
    # connection immediately - even though the upgrade itself succeeded and
    # auth passed. curl doesn't enforce this, which is why a direct curl
    # test looked fine while the real browser failed instantly. The value
    # itself (the JWT) is never actually used as a negotiated protocol, just
    # echoed back to satisfy this handshake requirement.
    offered_protocol = websocket.headers.get("sec-websocket-protocol", "").split(",")[0].strip() or None
    await websocket.accept(subprotocol=offered_protocol)

    try:
        # Get connection parameters from query string
        connection_type = websocket.query_params.get('type', 'local')
        
        logger.info(f"Terminal PTY session started for user {user.username} (id={user.id}, type={connection_type})")
        
        # Determine which command to execute
        if connection_type == 'ssh':
            ssh_host = websocket.query_params.get('ssh_host', '')
            ssh_user = websocket.query_params.get('ssh_user', 'root')
            ssh_port = websocket.query_params.get('ssh_port', '22')
            
            if not ssh_host:
                await websocket.send_json({
                    "type": "error",
                    "data": "SSH host required for SSH connection"
                })
                await websocket.close(code=1008)
                return
            
            # Build SSH command. StrictHostKeyChecking=accept-new (issue #10,
            # OpenSSH >=7.6): a host seen for the first time is trusted and
            # its key recorded in the default ~/.ssh/known_hosts (no
            # UserKnownHostsFile override - reuses whatever this OS user has
            # already verified manually too) - but if a KNOWN host's key
            # later changes (the actual MITM signal this is meant to catch),
            # the connection fails closed instead of silently proceeding.
            shell_cmd = [
                'ssh',
                '-o', 'StrictHostKeyChecking=accept-new',
                '-p', ssh_port,
                f'{ssh_user}@{ssh_host}'
            ]
            logger.info(f"SSH connection: {ssh_user}@{ssh_host}:{ssh_port}")
        else:
            # Local bash shell
            shell_cmd = ['bash']
            logger.info("Local shell connection")
        
        # Create PTY
        pid, fd = pty.fork()
        
        if pid == 0:
            # Child process - execute shell or SSH
            # Set TERM environment for proper terminal emulation (MC, vim, htop, etc.)
            os.environ['TERM'] = 'xterm-256color'
            os.environ['COLORTERM'] = 'truecolor'
            os.execvp(shell_cmd[0], shell_cmd)
        else:
            # Parent process - handle I/O
            try:
                # Set PTY to non-blocking
                fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
                
                # Log connection (don't send to terminal to avoid clutter)
                logger.info(f"PTY created with PID: {pid}")
                
                # Bidirectional I/O loop
                while True:
                    # Check for data from PTY (non-blocking)
                    ready, _, _ = select.select([fd], [], [], 0.01)
                    
                    if fd in ready:
                        try:
                            output = os.read(fd, 1024)
                            if output:
                                await websocket.send_json({
                                    "type": "data",
                                    "data": output.decode('utf-8', errors='replace')
                                })
                        except OSError:
                            break
                    
                    # Check for data from WebSocket
                    try:
                        message = await asyncio.wait_for(
                            websocket.receive_json(),
                            timeout=0.01
                        )
                        
                        msg_type = message.get('type')
                        
                        if msg_type == 'data':
                            # User input
                            data = message.get('data', '')
                            os.write(fd, data.encode('utf-8'))
                        
                        elif msg_type == 'resize':
                            # Terminal resize
                            rows = message.get('rows', 30)  # Increased from 24
                            cols = message.get('cols', 120)  # Increased from 80
                            logger.info(f"📐 Terminal resize: {cols} cols × {rows} rows")
                            winsize = struct.pack('HHHH', rows, cols, 0, 0)
                            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
                        
                    except asyncio.TimeoutError:
                        # No message from client, continue
                        pass
                    except WebSocketDisconnect:
                        break
                
            finally:
                # Clean up
                try:
                    os.close(fd)
                    os.kill(pid, 9)
                    os.waitpid(pid, 0)
                except:
                    pass
    
    except Exception as e:
        logger.error(f"PTY error: {e}")
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
