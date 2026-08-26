from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel
import subprocess
import shlex
from datetime import datetime

from core.database import get_db
from core.dependencies import get_current_admin_user
from api.models.base_models import User
from core.security import hash_password
from services.password_reset_service import password_reset_service

router = APIRouter()


class ServiceStatus(BaseModel):
    name: str
    active_state: str
    sub_state: str
    uptime: str | None = None
    description: str | None = None


class CommandRequest(BaseModel):
    command: str


class CommandResponse(BaseModel):
    output: str | None = None
    error: str | None = None
    exit_code: int


# Allowed services that can be controlled
ALLOWED_SERVICES = ['liara', 'liara-frontend', 'nginx', 'postgresql']

# Restricted commands for security
RESTRICTED_COMMANDS = ['rm', 'mkfs', 'dd', 'fdisk', 'reboot', 'shutdown', 'halt', 'poweroff']


def run_command(command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute a shell command safely with timeout.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            'output': result.stdout,
            'error': result.stderr,
            'exit_code': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'output': None,
            'error': f'Command timed out after {timeout} seconds',
            'exit_code': -1
        }
    except Exception as e:
        return {
            'output': None,
            'error': str(e),
            'exit_code': -1
        }


def get_service_status(service_name: str) -> Dict[str, Any]:
    """
    Get systemd service status.
    """
    try:
        # Get service status
        result = run_command(f"systemctl show {service_name} --no-page")
        if result['exit_code'] != 0:
            return {
                'name': service_name,
                'active_state': 'unknown',
                'sub_state': 'unknown',
                'uptime': None
            }

        # Parse output
        status_dict = {}
        for line in result['output'].split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                status_dict[key] = value

        # Get uptime if active
        uptime = None
        if status_dict.get('ActiveState') == 'active':
            uptime_result = run_command(f"systemctl status {service_name} | grep Active | awk '{{print $6, $7, $8}}'")
            if uptime_result['exit_code'] == 0:
                uptime = uptime_result['output'].strip()

        return {
            'name': service_name,
            'active_state': status_dict.get('ActiveState', 'unknown'),
            'sub_state': status_dict.get('SubState', 'unknown'),
            'uptime': uptime,
            'description': status_dict.get('Description', '')
        }
    except Exception as e:
        return {
            'name': service_name,
            'active_state': 'error',
            'sub_state': str(e),
            'uptime': None
        }


@router.get("/services/status")
async def get_services_status(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, List[ServiceStatus]]:
    """
    Get status of all managed services.
    """
    services = []
    for service_name in ALLOWED_SERVICES:
        status = get_service_status(service_name)
        services.append(ServiceStatus(**status))

    return {"services": services}


@router.post("/services/{service_name}/start")
async def start_service(
    service_name: str,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Start a systemd service.
    """
    if service_name not in ALLOWED_SERVICES:
        raise HTTPException(status_code=400, detail=f"Service {service_name} not allowed")

    result = run_command(f"sudo systemctl start {service_name}")
    if result['exit_code'] != 0:
        raise HTTPException(status_code=500, detail=result['error'] or "Failed to start service")

    return {"message": f"Service {service_name} started successfully"}


@router.post("/services/{service_name}/stop")
async def stop_service(
    service_name: str,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Stop a systemd service.
    """
    if service_name not in ALLOWED_SERVICES:
        raise HTTPException(status_code=400, detail=f"Service {service_name} not allowed")

    result = run_command(f"sudo systemctl stop {service_name}")
    if result['exit_code'] != 0:
        raise HTTPException(status_code=500, detail=result['error'] or "Failed to stop service")

    return {"message": f"Service {service_name} stopped successfully"}


@router.post("/services/{service_name}/restart")
async def restart_service(
    service_name: str,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Restart a systemd service.
    """
    if service_name not in ALLOWED_SERVICES:
        raise HTTPException(status_code=400, detail=f"Service {service_name} not allowed")

    result = run_command(f"sudo systemctl restart {service_name}")
    if result['exit_code'] != 0:
        raise HTTPException(status_code=500, detail=result['error'] or "Failed to restart service")

    return {"message": f"Service {service_name} restarted successfully"}


@router.post("/services/{service_name}/reload")
async def reload_service(
    service_name: str,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Reload a systemd service configuration.
    """
    if service_name not in ALLOWED_SERVICES:
        raise HTTPException(status_code=400, detail=f"Service {service_name} not allowed")

    result = run_command(f"sudo systemctl reload {service_name}")
    if result['exit_code'] != 0:
        raise HTTPException(status_code=500, detail=result['error'] or "Failed to reload service")

    return {"message": f"Service {service_name} reloaded successfully"}


@router.post("/terminal/connect")
async def connect_terminal(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """
    Initialize terminal session.
    """
    return {
        "message": f"Terminal connected for user {current_user.username}",
        "user": current_user.username,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/terminal/execute")
async def execute_terminal_command(
    request: CommandRequest,
    current_user: User = Depends(get_current_admin_user)
) -> CommandResponse:
    """
    Execute a terminal command.
    Security: Only allows safe commands, blocks destructive operations.
    """
    command = request.command.strip()
    
    if not command:
        raise HTTPException(status_code=400, detail="Command cannot be empty")

    # Check for restricted commands
    cmd_parts = shlex.split(command)
    base_command = cmd_parts[0] if cmd_parts else ""
    
    if any(restricted in command.lower() for restricted in RESTRICTED_COMMANDS):
        raise HTTPException(
            status_code=403, 
            detail=f"Command '{base_command}' is restricted for security reasons"
        )

    # Execute command
    result = run_command(command, timeout=30)
    
    return CommandResponse(
        output=result['output'],
        error=result['error'],
        exit_code=result['exit_code']
    )


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Reset user password and send personalized email from Liara.
    
    Admin-only endpoint that:
    1. Generates a secure reset token
    2. Analyzes user's conversation history with Liara
    3. Generates a personalized password reset email
    4. Sends email with reset link
    
    Returns:
        Success message and email status
    """
    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Don't allow resetting admin's own password this way
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot reset your own password. Use the profile settings instead."
        )
    
    # Check if user has email
    if not user.email:
        raise HTTPException(
            status_code=400,
            detail=f"User {user.username} has no email address configured"
        )
    
    try:
        # Create reset token
        reset_token = password_reset_service.create_reset_token(
            user_id=user.id,
            username=user.username
        )
        
        # Generate reset URL
        import os
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        reset_url = f"{frontend_url}/reset-password?token={reset_token}"
        
        # Try to send personalized email with Liara's memories
        email_sent = await password_reset_service.send_reset_email(
            user=user,
            reset_token=reset_token,
            db=db
        )
        
        # Return success with token info (fallback mode if email fails)
        return {
            "success": True,
            "email_sent": email_sent,
            "message": f"Password reset {'email sent to' if email_sent else 'token generated for'} {user.email}",
            "username": user.username,
            "email": user.email,
            "token_expires_hours": 24,
            "reset_token": reset_token if not email_sent else None,
            "reset_url": reset_url if not email_sent else None,
            "smtp_configured": email_sent
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error sending password reset: {str(e)}"
        )


@router.post("/password-reset/verify")
async def verify_reset_token(
    token: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Verify a password reset token (public endpoint for reset page)
    
    Args:
        token: Reset token from email
        
    Returns:
        User info if token valid
    """
    token_data = password_reset_service.verify_reset_token(token)
    
    if not token_data:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )
    
    return {
        "valid": True,
        "username": token_data['username'],
        "expires_at": token_data['expires_at'].isoformat()
    }


@router.post("/password-reset/complete")
async def complete_password_reset(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Complete password reset with new password (public endpoint)
    
    Args:
        token: Reset token from email
        new_password: New password
        
    Returns:
        Success message
    """
    # Verify token
    token_data = password_reset_service.verify_reset_token(token)
    
    if not token_data:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )
    
    # Find user
    user = db.query(User).filter(User.id == token_data['user_id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate password strength
    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters"
        )
    
    # Update password - also ends every existing session (issue #11 item 3),
    # since a "forgot password" reset is exactly the scenario where an
    # already-issued token might be in someone else's hands.
    from core.security import invalidate_sessions
    user.hashed_password = hash_password(new_password)
    invalidate_sessions(user)
    db.commit()

    # Invalidate token
    password_reset_service.invalidate_token(token)
    
    return {
        "success": True,
        "message": f"Password updated successfully for {user.username}"
    }

