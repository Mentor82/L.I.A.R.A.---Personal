from fastapi import APIRouter
from dashboard.info import get_dashboard_info

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/info")
def dashboard_info():
    return get_dashboard_info()
