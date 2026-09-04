"""
Agent Profile Overrides Service

Reads/writes admin overrides for AgentRegistry._PROFILES's display fields
(name/description/default_model/icon/category), stored in the
agent_profiles table. A missing row for a given agent_id means "use the
hardcoded default" - see agent_registry.py for how these get merged in
and why id/tools/class are never overridable here.
"""

from typing import Dict, Optional, TypedDict
from sqlalchemy.orm import Session
from sqlalchemy import text

OVERRIDABLE_FIELDS = ("name", "description", "default_model", "icon", "category")


class AgentProfileOverride(TypedDict):
    name: str
    description: str
    default_model: str
    icon: str
    category: str


def get_agent_profile_overrides(db: Session) -> Dict[str, AgentProfileOverride]:
    rows = db.execute(text("""
        SELECT agent_id, name, description, default_model, icon, category
        FROM agent_profiles
    """)).fetchall()

    return {
        row.agent_id: {
            "name": row.name,
            "description": row.description,
            "default_model": row.default_model,
            "icon": row.icon,
            "category": row.category,
        }
        for row in rows
    }


def get_agent_profile_override(db: Session, agent_id: str) -> Optional[AgentProfileOverride]:
    row = db.execute(text("""
        SELECT name, description, default_model, icon, category
        FROM agent_profiles
        WHERE agent_id = :agent_id
    """), {"agent_id": agent_id}).first()

    if not row:
        return None

    return {
        "name": row.name,
        "description": row.description,
        "default_model": row.default_model,
        "icon": row.icon,
        "category": row.category,
    }


def set_agent_profile_override(db: Session, agent_id: str, fields: AgentProfileOverride) -> AgentProfileOverride:
    """
    Upsert an override row from a COMPLETE field set - the caller (the
    admin router) is responsible for merging a partial request body onto
    the agent's current full state (code default + existing override, via
    AgentRegistry.get_profile) before calling this, so every row written
    here is always a complete snapshot, never partial with silently-NULL
    columns.
    """
    existing = get_agent_profile_override(db, agent_id)

    if existing:
        set_clause = ", ".join(f"{key} = :{key}" for key in OVERRIDABLE_FIELDS)
        db.execute(
            text(f"UPDATE agent_profiles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE agent_id = :agent_id"),
            {**fields, "agent_id": agent_id}
        )
    else:
        db.execute(text("""
            INSERT INTO agent_profiles (agent_id, name, description, default_model, icon, category)
            VALUES (:agent_id, :name, :description, :default_model, :icon, :category)
        """), {"agent_id": agent_id, **fields})

    db.commit()
    return get_agent_profile_override(db, agent_id)  # type: ignore[return-value]


def reset_agent_profile_override(db: Session, agent_id: str) -> None:
    db.execute(text("DELETE FROM agent_profiles WHERE agent_id = :agent_id"), {"agent_id": agent_id})
    db.commit()
