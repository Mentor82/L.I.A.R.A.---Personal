"""
Per-chat-session workspace: where code-execution output lives, and the
read interface both the user (via the file-list/download endpoints) and the
LLM (via a small manifest injected into chat context) use to see it.

A directory on disk is not, by itself, "visible to the LLM" - this module is
what actually makes generated files something the model can be told about and
read the (text) content of, not just a user-facing download list.
"""
import json
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

SESSION_FILES_DIR = Path(os.getenv("SESSION_FILES_DIR", "/opt/liara/app/session_files"))

# Text-like files get their content read into chat context directly (bounded
# size); anything else is reported as present/size/type only.
TEXT_MIME_PREFIXES = ("text/",)
TEXT_MIME_EXACT = {"application/json", "application/csv", "application/xml"}
MAX_INLINE_TEXT_READ = 50 * 1024  # 50 KiB

# Workspace v1 write limits (previously defined but never enforced in
# code_sandbox.py - live here now since that's where workspace writes
# actually happen).
MAX_SESSION_FILE = 100 * 1024 * 1024  # 100 MiB
MAX_SESSION_TOTAL = 500 * 1024 * 1024  # 500 MiB per session workspace

# Sidecar metadata the filesystem itself can't tell us (id/source/created_at/
# execution_id/context-selection) - the filesystem stays the source of truth
# for content/size/mtime/mime-type, this is a thin overlay only. Excluded
# from every directory listing/diff so it never shows up as a "file".
MANIFEST_FILENAME = ".liara_manifest.json"


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


def _manifest_path(user_id: int, session_id: int) -> Path:
    return _workspace_dir(user_id, session_id) / MANIFEST_FILENAME


def _load_manifest(user_id: int, session_id: int) -> dict:
    path = _manifest_path(user_id, session_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_manifest(user_id: int, session_id: int, manifest: dict) -> None:
    path = _manifest_path(user_id, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def record_file_event(user_id: int, session_id: int, filename: str, source: str, execution_id: Optional[str] = None) -> None:
    """
    Called whenever a file is created/overwritten by any workspace-writing
    path (user create/save, or code_sandbox's run-diff) so the manifest
    knows who/what produced it. `source` is one of: user, code_runner,
    liara, agent, web_research, generated.
    """
    manifest = _load_manifest(user_id, session_id)
    entry = manifest.get(filename, {})
    entry["id"] = entry.get("id") or uuid.uuid4().hex
    entry["source"] = source
    entry["created_at"] = entry.get("created_at") or datetime.now(timezone.utc).isoformat()
    if execution_id is not None:
        entry["execution_id"] = execution_id
    manifest[filename] = entry
    _save_manifest(user_id, session_id, manifest)


def _remove_file_from_manifest(user_id: int, session_id: int, filename: str) -> None:
    manifest = _load_manifest(user_id, session_id)
    if filename in manifest:
        del manifest[filename]
        _save_manifest(user_id, session_id, manifest)


def _rename_file_in_manifest(user_id: int, session_id: int, old_name: str, new_name: str) -> None:
    manifest = _load_manifest(user_id, session_id)
    if old_name in manifest:
        manifest[new_name] = manifest.pop(old_name)
        _save_manifest(user_id, session_id, manifest)


def set_context_selection(user_id: int, session_id: int, filenames: List[str]) -> None:
    """Replaces the full "included in chat context" set for this workspace."""
    manifest = _load_manifest(user_id, session_id)
    selected = set(filenames)
    for name in list(manifest.keys()):
        manifest[name]["selected_for_context"] = name in selected
    for name in selected:
        if name not in manifest:
            manifest[name] = {
                "id": uuid.uuid4().hex,
                "source": "unknown",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "selected_for_context": True,
            }
    _save_manifest(user_id, session_id, manifest)


def get_context_selected_files(user_id: int, session_id: int) -> List[str]:
    manifest = _load_manifest(user_id, session_id)
    return [name for name, entry in manifest.items() if entry.get("selected_for_context")]


def _validate_filename(filename: str) -> Optional[str]:
    """Rejects empty/`.`/`..`/path-separator names. Returns None if invalid."""
    if not filename or filename in (".", "..") or "/" in filename or "\\" in filename:
        return None
    return filename


def _workspace_total_size(workspace: Path) -> int:
    total = 0
    if workspace.exists():
        for entry in workspace.iterdir():
            if entry.is_file() and not entry.is_symlink() and entry.name != MANIFEST_FILENAME:
                total += entry.stat().st_size
    return total


def create_workspace_file(user_id: int, session_id: int, filename: str, content: str) -> dict:
    safe_name = _validate_filename(filename)
    if safe_name is None:
        return {"ok": False, "error": "Ungültiger Dateiname"}
    workspace = _workspace_dir(user_id, session_id)
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / safe_name
    if target.exists():
        return {"ok": False, "error": "Datei existiert bereits"}
    data = content.encode("utf-8")
    if len(data) > MAX_SESSION_FILE:
        return {"ok": False, "error": f"Datei zu groß (Limit {MAX_SESSION_FILE // (1024 * 1024)} MiB)"}
    if _workspace_total_size(workspace) + len(data) > MAX_SESSION_TOTAL:
        return {"ok": False, "error": "Workspace-Speicherlimit erreicht"}
    target.write_bytes(data)
    record_file_event(user_id, session_id, safe_name, source="user")
    return {"ok": True}


def write_workspace_file(user_id: int, session_id: int, filename: str, content: str) -> dict:
    resolved = resolve_workspace_file(user_id, session_id, filename)
    if resolved is None:
        return {"ok": False, "error": "Datei nicht gefunden"}
    data = content.encode("utf-8")
    if len(data) > MAX_SESSION_FILE:
        return {"ok": False, "error": f"Datei zu groß (Limit {MAX_SESSION_FILE // (1024 * 1024)} MiB)"}
    workspace = _workspace_dir(user_id, session_id)
    current_size = resolved.stat().st_size
    if _workspace_total_size(workspace) - current_size + len(data) > MAX_SESSION_TOTAL:
        return {"ok": False, "error": "Workspace-Speicherlimit erreicht"}
    resolved.write_bytes(data)
    record_file_event(user_id, session_id, filename, source="user")
    return {"ok": True}


def rename_workspace_file(user_id: int, session_id: int, filename: str, new_name: str) -> dict:
    safe_new = _validate_filename(new_name)
    if safe_new is None:
        return {"ok": False, "error": "Ungültiger Dateiname"}
    resolved = resolve_workspace_file(user_id, session_id, filename)
    if resolved is None:
        return {"ok": False, "error": "Datei nicht gefunden"}
    workspace = _workspace_dir(user_id, session_id)
    target = workspace / safe_new
    if target.exists():
        return {"ok": False, "error": "Zieldatei existiert bereits"}
    resolved.rename(target)
    _rename_file_in_manifest(user_id, session_id, filename, safe_new)
    return {"ok": True}


def delete_workspace_file(user_id: int, session_id: int, filename: str) -> dict:
    resolved = resolve_workspace_file(user_id, session_id, filename)
    if resolved is None:
        return {"ok": False, "error": "Datei nicht gefunden"}
    try:
        resolved.unlink()
    except OSError as e:
        return {"ok": False, "error": str(e)}
    _remove_file_from_manifest(user_id, session_id, filename)
    return {"ok": True}


def list_session_files(user_id: int, session_id: int) -> List[dict]:
    """User- and LLM-facing file listing: name, size, mime type, mtime, plus
    the manifest overlay (id/source/created_at/execution_id/context-selection)."""
    workspace = _workspace_dir(user_id, session_id)
    if not workspace.exists():
        return []
    manifest = _load_manifest(user_id, session_id)
    files = []
    for entry in sorted(workspace.iterdir()):
        if not entry.is_file() or entry.is_symlink() or entry.name == MANIFEST_FILENAME:
            continue
        stat = entry.stat()
        mime_type, _ = mimetypes.guess_type(entry.name)
        modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        meta = manifest.get(entry.name, {})
        files.append({
            "id": meta.get("id"),
            "name": entry.name,
            "size": stat.st_size,
            "mime_type": mime_type or "application/octet-stream",
            "modified_at": modified_at,
            "created_at": meta.get("created_at") or modified_at,
            "source": meta.get("source", "unknown"),
            "execution_id": meta.get("execution_id"),
            "selected_for_context": bool(meta.get("selected_for_context", False)),
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
