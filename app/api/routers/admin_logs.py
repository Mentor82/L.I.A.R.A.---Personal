"""
Admin Logs Router
Endpoints for reading and filtering system logs
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from core.dependencies import require_admin
from api.models.base_models import User
from services.log_reader import (
    get_log_reader_service,
    ServiceType,
    LogLevel
)


router = APIRouter(prefix="/admin/logs", tags=["Admin Logs"])


class LogEntry(BaseModel):
    """Log entry model"""
    timestamp: str
    level: str
    message: str
    service: str


class ActivityEntry(BaseModel):
    """Activity entry model"""
    timestamp: str
    service: str
    level: str
    type: str
    user: Optional[str]
    action: Optional[str]
    details: str


@router.get("", response_model=List[LogEntry])
async def get_logs(
    service: ServiceType = Query(..., description="Service to read logs from"),
    level: Optional[LogLevel] = Query(None, description="Filter by log level"),
    since: Optional[datetime] = Query(None, description="Start time for logs"),
    until: Optional[datetime] = Query(None, description="End time for logs"),
    search: Optional[str] = Query(None, description="Search term"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entries"),
    current_user: User = Depends(require_admin)
):
    """
    Get system logs with optional filters
    
    Requires admin role
    """
    log_service = get_log_reader_service()
    
    try:
        logs = log_service.get_logs(
            service=service,
            level=level,
            since=since,
            until=until,
            search=search,
            limit=limit
        )
        
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")


@router.get("/activity", response_model=List[ActivityEntry])
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=100, description="Number of activities"),
    current_user: User = Depends(require_admin)
):
    """
    Get recent system activity across all services
    
    Requires admin role
    """
    log_service = get_log_reader_service()
    
    try:
        activities = log_service.get_recent_activity(limit=limit)
        return activities
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get activities: {str(e)}")


@router.get("/services", response_model=List[str])
async def get_available_services(
    current_user: User = Depends(require_admin)
):
    """
    Get list of available services to query logs from
    
    Requires admin role
    """
    return [service.value for service in ServiceType]


@router.get("/levels", response_model=List[str])
async def get_log_levels(
    current_user: User = Depends(require_admin)
):
    """
    Get list of available log levels
    
    Requires admin role
    """
    return [level.value for level in LogLevel]
