"""Public API Endpoints - No authentication required."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from api.routers.system_config_router import get_or_create_config

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/guest-mode")
async def get_guest_mode_status(db: Session = Depends(get_db)):
    """
    Get guest mode status - PUBLIC endpoint.
    Returns only whether guest mode is enabled.
    No authentication required.
    """
    config = get_or_create_config(db)
    return {"guest_mode_enabled": config.guest_mode_enabled}
