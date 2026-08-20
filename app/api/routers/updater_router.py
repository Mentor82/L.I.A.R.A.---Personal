"""
Admin Updater Router
Read-only git status/patch-history endpoints for the Admin "Updates" page.

Deliberately read-only for now: it reports what's pending (git commits behind
origin, existing patch archives) but doesn't execute git pull, restart_backend.sh,
deploy_frontend.sh or apply_patch.sh itself. That's a follow-up once the process-
execution/auth model for actually running them from the web UI is worked out.
"""
import subprocess
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.dependencies import require_admin
from api.models.base_models import User

router = APIRouter(prefix="/admin/updater", tags=["Admin Updater"])

GIT_TIMEOUT = 15


class CommitInfo(BaseModel):
    hash: str
    author: str
    date: str
    message: str


class UpdateStatus(BaseModel):
    branch: str
    up_to_date: bool
    behind_count: int
    commits: List[CommitInfo]
    current_commit: Optional[CommitInfo]
    changed_files: List[str]
    backend_would_restart: bool
    frontend_would_deploy: bool


class PatchInfo(BaseModel):
    name: str
    has_migration: bool
    has_rollback: bool
    info: str


def _repo_root() -> Path:
    """Find the repo root regardless of the backend process's working directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path(__file__).resolve().parent,
        capture_output=True, text=True, timeout=GIT_TIMEOUT
    )
    if result.returncode != 0:
        raise RuntimeError(f"Not a git repository: {result.stderr.strip()}")
    return Path(result.stdout.strip())


def _git(args: List[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=GIT_TIMEOUT
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _parse_commit_line(line: str) -> Optional[CommitInfo]:
    parts = line.split("|", 3)
    if len(parts) != 4:
        return None
    return CommitInfo(hash=parts[0][:7], author=parts[1], date=parts[2], message=parts[3])


@router.get("/status", response_model=UpdateStatus)
async def get_update_status(current_user: User = Depends(require_admin)):
    """
    Fetch origin and report how many commits (if any) the local checkout is
    behind, plus what those commits are. Admin-only.
    """
    try:
        repo = _repo_root()
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
        _git(["fetch", "origin", branch], repo)

        behind_raw = _git(["rev-list", "--count", f"HEAD..origin/{branch}"], repo)
        behind_count = int(behind_raw) if behind_raw.isdigit() else 0

        commits = []
        if behind_count > 0:
            log_raw = _git(
                ["log", f"HEAD..origin/{branch}", "--pretty=format:%H|%an|%ad|%s", "--date=iso"],
                repo
            )
            commits = [c for c in (_parse_commit_line(l) for l in log_raw.splitlines()) if c]

        current_raw = _git(["log", "-1", "--pretty=format:%H|%an|%ad|%s", "--date=iso"], repo)
        current_commit = _parse_commit_line(current_raw)

        changed_files = []
        if behind_count > 0:
            diff_raw = _git(["diff", "--name-only", f"HEAD..origin/{branch}"], repo)
            changed_files = [f for f in diff_raw.splitlines() if f]

        # Mirrors update.sh's own detection (app/* -> restart, frontend/* -> deploy) -
        # keep both in sync if that logic ever changes.
        backend_would_restart = any(f.startswith("app/") for f in changed_files)
        frontend_would_deploy = any(f.startswith("frontend/") for f in changed_files)

        return UpdateStatus(
            branch=branch,
            up_to_date=behind_count == 0,
            behind_count=behind_count,
            commits=commits,
            current_commit=current_commit,
            changed_files=changed_files,
            backend_would_restart=backend_would_restart,
            frontend_would_deploy=frontend_would_deploy
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patches", response_model=List[PatchInfo])
async def list_patches(current_user: User = Depends(require_admin)):
    """
    List existing patch archives created by create_patch.sh (see AI_AGENT_GUIDE.md).
    Read-only - does not apply or roll back anything. Admin-only.
    """
    try:
        repo = _repo_root()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    patches_dir = repo / "patches"
    if not patches_dir.exists():
        return []

    entries = []
    for entry in sorted(patches_dir.iterdir(), reverse=True):
        if not entry.is_dir():
            continue
        info_file = entry / "PATCH_INFO.txt"
        info_text = info_file.read_text(encoding="utf-8", errors="replace") if info_file.exists() else ""
        migrations_dir = entry / "migrations"
        has_migration = migrations_dir.is_dir() and any(migrations_dir.glob("*.sql"))
        entries.append(PatchInfo(
            name=entry.name,
            has_migration=has_migration,
            has_rollback=(entry / "rollback.sh").exists(),
            info=info_text
        ))

    return entries
