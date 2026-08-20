"""
Dashboard Activity Widget
Shows recent user and system activities
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from core.dependencies import require_active_user
from api.models.base_models import User
from services.log_reader import get_log_reader_service


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class ActivityItem(BaseModel):
    """Dashboard activity item"""
    id: str
    timestamp: str
    type: str  # login, chat, api_call, error, system
    user: Optional[str] = None
    action: str
    details: Optional[str] = None
    icon: str = "📌"


@router.get("/activities", response_model=List[ActivityItem])
async def get_recent_activities(
    limit: int = Query(10, ge=1, le=50, description="Number of activities to return"),
    current_user: User = Depends(require_active_user)
):
    """
    Get recent activities for dashboard widget
    
    Shows a timeline of recent user and system events
    """
    log_service = get_log_reader_service()
    
    try:
        activities = log_service.get_recent_activity(limit=limit)
        
        # Convert to dashboard format with icons
        dashboard_activities = []
        for idx, activity in enumerate(activities):
            icon = _get_activity_icon(activity['type'])
            
            dashboard_activities.append({
                'id': f"activity_{idx}_{activity['timestamp']}",
                'timestamp': activity['timestamp'],
                'type': activity['type'],
                'user': activity.get('user'),
                'action': activity.get('action', 'System activity'),
                'details': activity.get('details', '')[:100],  # Truncate long details
                'icon': icon
            })
        
        return dashboard_activities
    except Exception as e:
        # Return empty list on error to not break dashboard
        return []


def _get_activity_icon(activity_type: str) -> str:
    """Get icon for activity type"""
    icon_map = {
        'login': '🔐',
        'chat': '💬',
        'api_call': '🔌',
        'error': '❌',
        'system': '⚙️',
        'user': '👤',
        'admin': '⚡'
    }
    return icon_map.get(activity_type, '📌')
