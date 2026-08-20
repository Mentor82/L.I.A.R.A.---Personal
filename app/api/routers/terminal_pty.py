"""
🖥️ WebSocket PTY Terminal
Real interactive terminal with full TTY support (su, vim, etc.)
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from api.models.base_models import User
from core.dependencies import get_current_user_ws
from core.database import get_db
from sqlalchemy.orm import Session
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
    db: Session = Depends(get_db)
):
    """
    WebSocket PTY Terminal
    
    Supports two connection modes:
    1. Local: Direct shell on Liara server (?type=local)
    2. SSH: Connect to remote server via SSH (?type=ssh&ssh_host=...&ssh_user=...&ssh_port=...)
    
    Requires admin authentication via query param: ?token=...
    """
    await websocket.accept()
    
    try:
        # Authenticate user (admin only)
        try:
            user = await get_current_user_ws(websocket, db)
        except Exception as e:
            logger.error(f"WebSocket auth failed: {e}")
            await websocket.send_json({
                "type": "error", 
                "data": f"Authentication failed: {str(e)}"
            })
            await websocket.close(code=1008)  # Policy Violation
            return
        
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
            
            # Build SSH command
            shell_cmd = [
                'ssh',
                '-o', 'StrictHostKeyChecking=no',  # Auto-accept host keys
                '-o', 'UserKnownHostsFile=/dev/null',  # Don't save host keys
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
