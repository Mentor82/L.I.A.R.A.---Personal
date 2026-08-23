"""
Per-chat-session workspace: where code-execution output lives, and the
read interface both the user (via the file-list/download endpoints) and the
LLM (via a small manifest injected into chat context) use to see it.

A directory on disk is not, by itself, "visible to the LLM" - this module is
what actually makes generated files something the model can be told about and
read the (text) content of, not just a user-facing download list.
"""
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

SESSION_FILES_DIR = Path(os.getenv("SESSION_FILES_DIR", "/opt/liara/app/session_files"))

# Text-like files get their content read into chat context directly (bounded
# size); anything else is reported as present/size/type only.
TEXT_MIME_PREFIXES = ("text/",)
TEXT_MIME_EXACT = {"application/json", "application/csv", "application/xml"}
MAX_INLINE_TEXT_READ = 50 * 1024  # 50 KiB


def _session_dir(user_id: int, session_id: int) -> Path:
    return SESSION_FILES_DIR / str(user_id) / str(session_id)


def _workspace_dir(user_id: int, session_id: int) -> Path:
    return _session_dir(user_id, session_id) / "workspace"


def _is_text_mime(mime_type: str) -> bool:
    return mime_type.startswith(TEXT_MIME_PREFIXES) or mime_type in TEXT_MIME_EXACT


def resolve_workspace_file(user_id: int, session_id: int, filename: str) -> Optional[Path]:
    """
    Resolves `filename` inside the session's workspace, rejecting anything
    that isn't a direct child of it - no traversal, no symlinks. Returns None
    if the file doesn't exist or fails either check.
    """
    workspace = _workspace_dir(user_id, session_id)
    if not workspace.exists():
        return None
    candidate = (workspace / filename)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        return None
    if resolved.parent != workspace.resolve():
        return None
    if candidate.is_symlink():
        return None
    return resolved


def list_session_files(user_id: int, session_id: int) -> List[dict]:
    """User- and LLM-facing file listing: name, size, mime type, mtime."""
    workspace = _workspace_dir(user_id, session_id)
    if not workspace.exists():
        return []
    files = []
    for entry in sorted(workspace.iterdir()):
        if not entry.is_file() or entry.is_symlink():
            continue
        stat = entry.stat()
        mime_type, _ = mimetypes.guess_type(entry.name)
        files.append({
            "name": entry.name,
            "size": stat.st_size,
            "mime_type": mime_type or "application/octet-stream",
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return files


def build_workspace_manifest(user_id: int, session_id: int) -> Optional[str]:
    """
    Short, LLM-context-ready summary of what's in this session's workspace -
    injected into the system/context prompt so the model knows these files
    exist without anyone having to ask "what did you just create?" first.
    """
    files = list_session_files(user_id, session_id)
    if not files:
        return None
    lines = [f"- {f['name']} ({f['size']} Bytes, {f['mime_type']})" for f in files]
    return "Dateien im Workspace dieser Chat-Session:\n" + "\n".join(lines)


def read_session_file(user_id: int, session_id: int, filename: str) -> dict:
    """
    LLM-facing file read. Text-like files under MAX_INLINE_TEXT_READ get their
    content returned; everything else (binary, or too large) is reported as
    metadata-only so the model can still reference it without derailing into
    a token-expensive binary dump.
    """
    resolved = resolve_workspace_file(user_id, session_id, filename)
    if resolved is None:
        return {"found": False}

    stat = resolved.stat()
    mime_type, _ = mimetypes.guess_type(resolved.name)
    mime_type = mime_type or "application/octet-stream"
    result = {
        "found": True,
        "name": resolved.name,
        "size": stat.st_size,
        "mime_type": mime_type,
        "content": None,
    }
    if _is_text_mime(mime_type) and stat.st_size <= MAX_INLINE_TEXT_READ:
        try:
            result["content"] = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return result


def delete_session_workspace(user_id: int, session_id: int) -> bool:
    """Best-effort recursive delete, used when a chat session is deleted."""
    import shutil
    session_dir = _session_dir(user_id, session_id)
    if not session_dir.exists():
        return True
    try:
        shutil.rmtree(session_dir)
        return True
    except OSError:
        return False
