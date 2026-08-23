"""
Workspace v1 API: file create/save/rename/delete and chat-context selection
on top of the existing per-session workspace (session_workspace.py) and code
execution (code_sandbox.py, code_exec_router.py) - additive only, the
existing /code-exec endpoints Chat.jsx's inline Run button depends on are
untouched.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from core.dependencies import require_active_user
from core.database import get_db
from api.models.base_models import User
from api.routers.code_exec_router import _verify_session_ownership
from services.session_workspace import (
    list_session_files,
    create_workspace_file,
    write_workspace_file,
    rename_workspace_file,
    delete_workspace_file,
    set_context_selection,
    get_context_selected_files,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace", tags=["Workspace"])


class CreateFileRequest(BaseModel):
    filename: str
    content: str = ""


class WriteFileRequest(BaseModel):
    content: str


class RenameFileRequest(BaseModel):
    new_name: str


class ContextSelectionRequest(BaseModel):
    filenames: List[str]


def _ok_or_400(result: dict) -> dict:
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Vorgang fehlgeschlagen"))
    return result


@router.get("/sessions/{session_id}/files")
async def get_workspace_files(
    session_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    _verify_session_ownership(db, session_id, current_user.id)
    return {"files": list_session_files(current_user.id, session_id)}


@router.post("/sessions/{session_id}/files")
async def create_file(
    session_id: int,
    req: CreateFileRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    _verify_session_ownership(db, session_id, current_user.id)
    result = _ok_or_400(create_workspace_file(current_user.id, session_id, req.filename, req.content))
    return result


@router.put("/sessions/{session_id}/files/{filename}")
async def save_file(
    session_id: int,
    filename: str,
    req: WriteFileRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    _verify_session_ownership(db, session_id, current_user.id)
    result = _ok_or_400(write_workspace_file(current_user.id, session_id, filename, req.content))
    return result


@router.post("/sessions/{session_id}/files/{filename}/rename")
async def rename_file(
    session_id: int,
    filename: str,
    req: RenameFileRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    _verify_session_ownership(db, session_id, current_user.id)
    result = _ok_or_400(rename_workspace_file(current_user.id, session_id, filename, req.new_name))
    return result


@router.delete("/sessions/{session_id}/files/{filename}")
async def delete_file(
    session_id: int,
    filename: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    _verify_session_ownership(db, session_id, current_user.id)
    result = _ok_or_400(delete_workspace_file(current_user.id, session_id, filename))
    return result


@router.put("/sessions/{session_id}/context")
async def update_context_selection(
    session_id: int,
    req: ContextSelectionRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    _verify_session_ownership(db, session_id, current_user.id)
    set_context_selection(current_user.id, session_id, req.filenames)
    return {"filenames": get_context_selected_files(current_user.id, session_id)}
