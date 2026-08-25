"""
Workspace v1 API: file create/save/rename/delete and chat-context selection
on top of the existing per-session workspace (session_workspace.py) and code
execution (code_sandbox.py, code_exec_router.py) - additive only, the
existing /code-exec endpoints Chat.jsx's inline Run button depends on are
untouched.
"""
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Tuple

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
    create_workspace_folder,
    upload_workspace_file,
    search_workspace,
    set_context_selection,
    get_context_selected_files,
    list_proposals,
    resolve_proposal,
    MAX_SESSION_FILE,
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


class CreateFolderRequest(BaseModel):
    path: str


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


@router.get("/sessions/{session_id}/search")
async def search_workspace_endpoint(
    session_id: int,
    q: str = "",
    case_sensitive: bool = False,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    """Project-wide text search (path + content) across this session's workspace."""
    _verify_session_ownership(db, session_id, current_user.id)
    return search_workspace(current_user.id, session_id, q, case_sensitive)


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


@router.post("/sessions/{session_id}/folders")
async def create_folder(
    session_id: int,
    req: CreateFolderRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    _verify_session_ownership(db, session_id, current_user.id)
    result = _ok_or_400(create_workspace_folder(current_user.id, session_id, req.path))
    return result


_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB


async def _read_upload_bounded(upload: UploadFile, limit: int) -> Tuple[bytes, bool]:
    """
    Reads an upload in bounded chunks instead of `await upload.read()`
    (which materializes the entire file as one Python `bytes` object before
    anyone checks its size) - stops as soon as the running total exceeds
    `limit`, so an oversized file never sits fully buffered in process
    memory just to then be rejected (issue #8). Returns (data, exceeded).
    """
    chunks = []
    total = 0
    while True:
        chunk = await upload.read(_UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            return b"", True
        chunks.append(chunk)
    return b"".join(chunks), False


@router.post("/sessions/{session_id}/upload")
async def upload_files(
    session_id: int,
    files: List[UploadFile] = File(...),
    folder: str = Form(""),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    """
    Upload from the user's own computer - one or more files at once (drag &
    drop or a multi-select file picker), landing directly at the workspace
    root or inside `folder` if given. Each file gets the exact same
    validation/size-limit path as create_workspace_file - a browser-supplied
    filename is untrusted input like any other. Partial success is reported
    per file rather than failing the whole batch over one bad file.
    """
    _verify_session_ownership(db, session_id, current_user.id)
    results = []
    for upload in files:
        data, exceeded = await _read_upload_bounded(upload, MAX_SESSION_FILE)
        target_path = f"{folder}/{upload.filename}" if folder else upload.filename
        if exceeded:
            results.append({
                "filename": upload.filename,
                "ok": False,
                "error": f"Datei zu groß (Limit {MAX_SESSION_FILE // (1024 * 1024)} MiB)",
            })
            continue
        result = upload_workspace_file(current_user.id, session_id, target_path, data)
        results.append({
            "filename": upload.filename,
            "ok": result.get("ok", False),
            "error": result.get("error"),
        })
    return {"results": results}


@router.put("/sessions/{session_id}/files/{filename:path}")
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


@router.post("/sessions/{session_id}/files/{filename:path}/rename")
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


@router.delete("/sessions/{session_id}/files/{filename:path}")
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


@router.get("/sessions/{session_id}/proposals")
async def get_proposals(
    session_id: int,
    status: Optional[str] = None,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    """
    LIARA's proposed-but-not-yet-applied changes (Agent-Vorbereitung v1).
    Nothing here has touched the filesystem yet - see approve/reject below.
    """
    _verify_session_ownership(db, session_id, current_user.id)
    return {"proposals": list_proposals(current_user.id, session_id, status)}


@router.post("/sessions/{session_id}/proposals/{proposal_id}/approve")
async def approve_proposal(
    session_id: int,
    proposal_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    """
    Only this endpoint - triggered by an explicit user click - ever turns a
    proposal into a real filesystem change (create/write/delete_workspace_file,
    the same functions every other workspace write already goes through).
    """
    _verify_session_ownership(db, session_id, current_user.id)
    result = _ok_or_400(resolve_proposal(current_user.id, session_id, proposal_id, approve=True))
    return result


@router.post("/sessions/{session_id}/proposals/{proposal_id}/reject")
async def reject_proposal(
    session_id: int,
    proposal_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    _verify_session_ownership(db, session_id, current_user.id)
    result = _ok_or_400(resolve_proposal(current_user.id, session_id, proposal_id, approve=False))
    return result
