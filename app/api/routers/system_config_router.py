"""System Configuration Router - Admin-only endpoints for global settings."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import require_admin
from api.models.base_models import SystemConfig, User

router = APIRouter(prefix="/admin/config", tags=["admin"])


# Pydantic Models
class SystemConfigResponse(BaseModel):
    """System Config Response"""
    # AI & Model
    default_model: str
    max_tokens: int
    temperature: int  # 0-100
    system_prompt: Optional[str]
    
    # Rate Limits
    guest_message_limit: int
    guest_message_length: int
    user_message_limit: int
    rate_limit_window: int
    
    # Features
    web_search_enabled: bool
    location_services_enabled: bool
    guest_mode_enabled: bool
    registration_enabled: bool
    
    # Privacy
    data_retention_days: int
    search_history_retention_days: int
    location_retention_days: int
    auto_delete_enabled: bool
    
    # Ollama
    ollama_host: str
    ollama_timeout: int
    ollama_pull_on_start: bool
    
    class Config:
        from_attributes = True


class SystemConfigUpdate(BaseModel):
    """System Config Update Request"""
    # AI & Model
    default_model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[int] = None
    system_prompt: Optional[str] = None
    
    # Rate Limits
    guest_message_limit: Optional[int] = None
    guest_message_length: Optional[int] = None
    user_message_limit: Optional[int] = None
    rate_limit_window: Optional[int] = None
    
    # Features
    web_search_enabled: Optional[bool] = None
    location_services_enabled: Optional[bool] = None
    guest_mode_enabled: Optional[bool] = None
    registration_enabled: Optional[bool] = None
    
    # Privacy
    data_retention_days: Optional[int] = None
    search_history_retention_days: Optional[int] = None
    location_retention_days: Optional[int] = None
    auto_delete_enabled: Optional[bool] = None
    
    # Ollama
    ollama_host: Optional[str] = None
    ollama_timeout: Optional[int] = None
    ollama_pull_on_start: Optional[bool] = None


def get_or_create_config(db: Session) -> SystemConfig:
    """Get existing config or create default (Singleton pattern)."""
    config = db.query(SystemConfig).first()
    if not config:
        config = SystemConfig(
            default_model="llama3.2:3b",
            max_tokens=2000,
            temperature=70,
            system_prompt=None,
            guest_message_limit=20,
            guest_message_length=500,
            user_message_limit=100,
            rate_limit_window=60,
            web_search_enabled=True,
            location_services_enabled=True,
            guest_mode_enabled=True,
            registration_enabled=True,
            data_retention_days=30,
            search_history_retention_days=7,
            location_retention_days=30,
            auto_delete_enabled=True,
            ollama_host="http://localhost:11434",
            ollama_timeout=120,
            ollama_pull_on_start=False
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("/public/guest-mode", tags=["public"])
async def get_guest_mode_status(db: Session = Depends(get_db)):
    """
    Get guest mode status - PUBLIC endpoint.
    Returns only whether guest mode is enabled.
    """
    config = get_or_create_config(db)
    return {"guest_mode_enabled": config.guest_mode_enabled}


@router.get("", response_model=SystemConfigResponse)
async def get_system_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get current system configuration.
    Admin-only endpoint.
    """
    config = get_or_create_config(db)
    return config


@router.put("", response_model=SystemConfigResponse)
async def update_system_config(
    update: SystemConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update system configuration.
    Admin-only endpoint.
    """
    config = get_or_create_config(db)
    
    # Update nur gesetzte Felder
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    
    return config
