"""
Agent Profiles Router - Admin-only endpoints to override AgentRegistry
display fields (name/description/default_model/icon/category) without a
code change + redeploy. See agent_registry.py / agent_profile_overrides_service.py
for why id/tools/class stay code-only and are never accepted here.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import require_admin
from api.models.base_models import User
from services.agents.agent_registry import AgentRegistry
from services.agent_profile_overrides_service import (
    set_agent_profile_override,
    reset_agent_profile_override,
    get_agent_profile_overrides,
)

router = APIRouter(prefix="/admin/agent-profiles", tags=["admin"])


class AgentProfileResponse(BaseModel):
    id: str
    name: str
    description: str
    default_model: str
    icon: str
    category: str
    tools: List[str]
    is_overridden: bool


class AgentProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_model: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None


@router.get("", response_model=List[AgentProfileResponse])
async def list_agent_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """All 4 agents, code defaults merged with any admin override."""
    overrides = get_agent_profile_overrides(db)
    profiles = AgentRegistry.list_agents(db=db)
    return [
        {**profile, "is_overridden": profile["id"] in overrides}
        for profile in profiles
    ]


@router.put("/{agent_id}", response_model=AgentProfileResponse)
async def update_agent_profile(
    agent_id: str,
    update: AgentProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Partial update - unset fields keep their current value (code default
    or existing override, whichever is currently active), so the row
    written to agent_profiles is always a complete snapshot.
    """
    current = AgentRegistry.get_profile(agent_id, db=db)
    if not current:
        raise HTTPException(status_code=400, detail=f"Unbekannter Agent-Typ: '{agent_id}'")

    update_data = update.model_dump(exclude_unset=True)
    merged_fields = {
        "name": update_data.get("name", current["name"]),
        "description": update_data.get("description", current["description"]),
        "default_model": update_data.get("default_model", current["default_model"]),
        "icon": update_data.get("icon", current["icon"]),
        "category": update_data.get("category", current["category"]),
    }
    set_agent_profile_override(db, agent_id, merged_fields)

    profile = AgentRegistry.get_profile(agent_id, db=db)
    return {**profile, "is_overridden": True}


@router.post("/{agent_id}/reset", response_model=AgentProfileResponse)
async def reset_agent_profile(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Deletes the override row, reverting the agent to its code default."""
    if not AgentRegistry.get_profile(agent_id):
        raise HTTPException(status_code=400, detail=f"Unbekannter Agent-Typ: '{agent_id}'")

    reset_agent_profile_override(db, agent_id)

    profile = AgentRegistry.get_profile(agent_id, db=db)
    return {**profile, "is_overridden": False}
