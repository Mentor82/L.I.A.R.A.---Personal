"""
Per-chat-session workspace: where code-execution output lives, and the
read interface both the user (via the file-list/download endpoints) and the
LLM (via a small manifest injected into chat context) use to see it.

A directory on disk is not, by itself, "visible to the LLM" - this module is
what actually makes generated files something the model can be told about and
read the (text) content of, not just a user-facing download list.
"""
import difflib
import json
import mimetypes
import os
import shutil
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

# LIARA's proposed-but-not-yet-applied workspace changes (Agent-Vorbereitung
# v1) - deliberately a separate sidecar from MANIFEST_FILENAME, not folded
# into it: a proposal isn't a file yet (it may never become one, if rejected),
# so it shouldn't share a schema/lifecycle with real, already-on-disk files.
# Also excluded from every directory listing/diff.
PROPOSALS_FILENAME = ".liara_proposals.json"

# Project-wide text search limits - a single chat session's workspace is
# small (MAX_SESSION_TOTAL is 500 MiB across every file), but scanning
# unbounded file sizes/counts on every keystroke-triggered search would
# still be wasteful. Files over the size cap still exist and can still
# match by path, they're just skipped for line-by-line content search.
MAX_SEARCH_FILE_SIZE = 5 * 1024 * 1024  # 5 MiB
MAX_SEARCH_RESULTS_PER_FILE = 50
MAX_SEARCH_FILES = 100


def _session_dir(user_id: int, session_id: int) -> Path:
    return SESSION_FILES_DIR / str(user_id) / str(session_id)


def _workspace_dir(user_id: int, session_id: int) -> Path:
    return _session_dir(user_id, session_id) / "workspace"


def _is_text_mime(mime_type: str) -> bool:
    return mime_type.startswith(TEXT_MIME_PREFIXES) or mime_type in TEXT_MIME_EXACT


def resolve_workspace_file(user_id: int, session_id: int, filename: str) -> Optional[Path]:
    """
    Resolves `filename` (a `/`-separated relative path, possibly nested in
    subfolders) inside the session's workspace - no traversal, no symlinks.
    Returns None if the path doesn't exist or fails either check.

    `resolve(strict=True)` follows every symlink along the whole chain, so
    checking containment against the workspace root AFTER that resolve
    catches symlink-escape at any depth, not just an immediate parent.
    """
    workspace = _workspace_dir(user_id, session_id)
    if not workspace.exists():
        return None
    candidate = (workspace / filename)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        return None
    workspace_root = workspace.resolve()
    if resolved != workspace_root and workspace_root not in resolved.parents:
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
    knows who/what produced it. `source` is one of: user, upload,
    code_runner, liara, agent, web_research, generated.
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
    """
    Removes `filename`'s own entry plus, if `filename` was a folder, every
    entry nested under it (`filename/...`) - otherwise deleting a folder
    would leave stale manifest entries behind for files that no longer
    exist at that path.
    """
    manifest = _load_manifest(user_id, session_id)
    prefix = f"{filename}/"
    changed = False
    for key in list(manifest.keys()):
        if key == filename or key.startswith(prefix):
            del manifest[key]
            changed = True
    if changed:
        _save_manifest(user_id, session_id, manifest)


def _rename_file_in_manifest(user_id: int, session_id: int, old_name: str, new_name: str) -> None:
    """
    Renames `old_name`'s own entry plus, if `old_name` was a folder, every
    entry nested under it - a folder rename moves the whole subtree on disk
    in one `Path.rename`, so the manifest keys need the same prefix rewrite
    to keep pointing at files that still exist, just under a new path.
    """
    manifest = _load_manifest(user_id, session_id)
    prefix = f"{old_name}/"
    changed = False
    for key in list(manifest.keys()):
        if key == old_name:
            manifest[new_name] = manifest.pop(key)
            changed = True
        elif key.startswith(prefix):
            manifest[new_name + key[len(old_name):]] = manifest.pop(key)
            changed = True
    if changed:
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
    """
    Validates a `/`-separated relative workspace path (may address a file
    nested in subfolders, e.g. `utils/helper.py`) - rejects an empty string,
    backslashes, a leading `/` (absolute path), and any `.`/`..`/empty
    segment (so no `..` traversal and no accidental `//`). A single segment
    with no `/` at all validates exactly as before subfolders existed.
    Returns None if invalid, otherwise the path unchanged.
    """
    if not filename or "\\" in filename or filename.startswith("/"):
        return None
    segments = filename.split("/")
    if any(seg in ("", ".", "..") for seg in segments):
        return None
    return filename


def _ensure_writable_by_runner(path: Path, up_to: Path) -> None:
    """
    Chmods `path` and every directory between it and `up_to` (inclusive) to
    0o777. The sandboxed code-runner (code_sandbox.py) executes as a
    different, unprivileged OS user (`liara-runner`) that needs write access
    to any folder it might write into - not just the workspace root, which
    already gets this treatment before every run. A folder created here (by
    the backend's own user, via the UI) needs the same treatment up front,
    otherwise a script writing into a user-created subfolder would fail with
    a permission error the backend can't fix after the fact (chmod requires
    being the file's owner). Best-effort - never blocks the actual create.
    """
    current = path
    while True:
        try:
            os.chmod(current, 0o777)
        except OSError:
            pass
        if current == up_to or current.parent == current:
            break
        current = current.parent


def _workspace_total_size(workspace: Path) -> int:
    total = 0
    if workspace.exists():
        for entry in workspace.rglob("*"):
            if entry.is_file() and not entry.is_symlink() and entry.name not in (MANIFEST_FILENAME, PROPOSALS_FILENAME):
                total += entry.stat().st_size
    return total


def _create_file_bytes(user_id: int, session_id: int, filename: str, data: bytes) -> dict:
    """
    Shared validate+write path for both create_workspace_file (editor "new
    file", text) and upload_workspace_file (raw bytes from a local upload) -
    same size/traversal/existing-file checks either way, only the source
    tag recorded afterwards differs.
    """
    safe_name = _validate_filename(filename)
    if safe_name is None:
        return {"ok": False, "error": "Ungültiger Dateiname"}
    workspace = _workspace_dir(user_id, session_id)
    target = workspace / safe_name
    # Path may address a file in a not-yet-existing subfolder (e.g.
    # "utils/helper.py") - create intermediate folders on demand, same as
    # any real filesystem-backed project explorer would.
    target.parent.mkdir(parents=True, exist_ok=True)
    _ensure_writable_by_runner(target.parent, workspace)
    if target.exists():
        return {"ok": False, "error": "Datei existiert bereits"}
    if len(data) > MAX_SESSION_FILE:
        return {"ok": False, "error": f"Datei zu groß (Limit {MAX_SESSION_FILE // (1024 * 1024)} MiB)"}
    if _workspace_total_size(workspace) + len(data) > MAX_SESSION_TOTAL:
        return {"ok": False, "error": "Workspace-Speicherlimit erreicht"}
    target.write_bytes(data)
    return {"ok": True, "safe_name": safe_name}


def create_workspace_file(user_id: int, session_id: int, filename: str, content: str) -> dict:
    result = _create_file_bytes(user_id, session_id, filename, content.encode("utf-8"))
    if not result.get("ok"):
        return result
    record_file_event(user_id, session_id, result["safe_name"], source="user")
    return {"ok": True}


def upload_workspace_file(user_id: int, session_id: int, filename: str, data: bytes) -> dict:
    """Writes a raw-bytes upload from the user's own computer - same checks
    as create_workspace_file, just tagged with a distinct source so the
    Explorer can show "Hochgeladen" instead of "Selbst erstellt"."""
    result = _create_file_bytes(user_id, session_id, filename, data)
    if not result.get("ok"):
        return result
    record_file_event(user_id, session_id, result["safe_name"], source="upload")
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
    """
    Renames a file or folder to a new leaf name within the SAME parent
    folder - not a move to a different parent (that's a separate,
    not-yet-built feature; see the plan's "Nicht Ziel dieser Iteration").
    `new_name` must therefore be a single path segment, no `/`.
    """
    if not new_name or "/" in new_name or "\\" in new_name or new_name in (".", ".."):
        return {"ok": False, "error": "Ungültiger Name"}
    resolved = resolve_workspace_file(user_id, session_id, filename)
    if resolved is None:
        return {"ok": False, "error": "Datei nicht gefunden"}
    parent_path = filename.rsplit("/", 1)[0] if "/" in filename else ""
    new_relpath = f"{parent_path}/{new_name}" if parent_path else new_name
    workspace = _workspace_dir(user_id, session_id)
    target = workspace / new_relpath
    if target.exists():
        return {"ok": False, "error": "Ziel existiert bereits"}
    resolved.rename(target)
    _rename_file_in_manifest(user_id, session_id, filename, new_relpath)
    return {"ok": True}


def delete_workspace_file(user_id: int, session_id: int, filename: str) -> dict:
    """Deletes a file, or recursively an entire folder and its contents."""
    resolved = resolve_workspace_file(user_id, session_id, filename)
    if resolved is None:
        return {"ok": False, "error": "Datei nicht gefunden"}
    try:
        if resolved.is_dir():
            shutil.rmtree(resolved)
        else:
            resolved.unlink()
    except OSError as e:
        return {"ok": False, "error": str(e)}
    _remove_file_from_manifest(user_id, session_id, filename)
    return {"ok": True}


def create_workspace_folder(user_id: int, session_id: int, path: str) -> dict:
    """Creates an empty subfolder (e.g. before any file exists inside it)."""
    safe_path = _validate_filename(path)
    if safe_path is None:
        return {"ok": False, "error": "Ungültiger Ordnername"}
    workspace = _workspace_dir(user_id, session_id)
    target = workspace / safe_path
    if target.exists():
        return {"ok": False, "error": "Ordner/Datei existiert bereits"}
    target.mkdir(parents=True)
    _ensure_writable_by_runner(target, workspace)
    return {"ok": True}


def search_workspace(user_id: int, session_id: int, query: str, case_sensitive: bool = False) -> dict:
    """
    Project-wide text search across every file in this session's workspace -
    matches on the file's relative path (substring) and/or its text content
    (plain line-by-line substring search, no regex - covers the common "find
    where X is used" case without the complexity/ReDoS surface of letting
    users supply arbitrary patterns). Uses the exact same `path` identity as
    the Explorer tree/editor tabs/tool-calling, so a result is directly
    openable with no translation step.
    """
    if not query:
        return {"results": [], "truncated": False}
    workspace = _workspace_dir(user_id, session_id)
    if not workspace.exists():
        return {"results": [], "truncated": False}

    needle = query if case_sensitive else query.lower()
    results = []
    truncated = False

    for entry in sorted(workspace.rglob("*")):
        if entry.is_symlink() or not entry.is_file() or entry.name in (MANIFEST_FILENAME, PROPOSALS_FILENAME):
            continue

        relpath = entry.relative_to(workspace).as_posix()
        haystack_path = relpath if case_sensitive else relpath.lower()
        path_match = needle in haystack_path

        content_matches = []
        stat = entry.stat()
        mime_type, _ = mimetypes.guess_type(entry.name)
        mime_type = mime_type or "application/octet-stream"
        if _is_text_mime(mime_type) and stat.st_size <= MAX_SEARCH_FILE_SIZE:
            try:
                text = entry.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = None
            if text is not None:
                for line_number, line in enumerate(text.splitlines(), start=1):
                    haystack_line = line if case_sensitive else line.lower()
                    if needle in haystack_line:
                        content_matches.append({"line": line_number, "text": line.strip()[:300]})
                        if len(content_matches) >= MAX_SEARCH_RESULTS_PER_FILE:
                            break

        if path_match or content_matches:
            if len(results) >= MAX_SEARCH_FILES:
                truncated = True
                break
            results.append({
                "path": relpath,
                "name": entry.name,
                "path_match": path_match,
                "content_matches": content_matches,
            })

    return {"results": results, "truncated": truncated}


def list_session_files(user_id: int, session_id: int) -> List[dict]:
    """
    User- and LLM-facing entry listing: both files AND folders, flat (not
    nested JSON) - each entry carries `path` (full `/`-separated relative
    path, the same identifier used everywhere else: editor tabs, tool-calling,
    context-selection), `name` (last segment, for display), `parent` (parent
    path, "" for workspace root) and `type` ("file"/"folder"). The frontend
    builds its own tree/explorer view from this flat list rather than the
    backend nesting JSON - keeps this one shape reusable for future
    filter/search views too, not just a tree.
    """
    workspace = _workspace_dir(user_id, session_id)
    if not workspace.exists():
        return []
    manifest = _load_manifest(user_id, session_id)
    entries = []
    for entry in sorted(workspace.rglob("*")):
        if entry.is_symlink() or entry.name in (MANIFEST_FILENAME, PROPOSALS_FILENAME):
            continue
        relpath = entry.relative_to(workspace).as_posix()
        parent = relpath.rsplit("/", 1)[0] if "/" in relpath else ""
        if entry.is_dir():
            entries.append({
                "id": None,
                "type": "folder",
                "path": relpath,
                "name": entry.name,
                "parent": parent,
            })
            continue
        if not entry.is_file():
            continue
        stat = entry.stat()
        mime_type, _ = mimetypes.guess_type(entry.name)
        modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        meta = manifest.get(relpath, {})
        entries.append({
            "id": meta.get("id"),
            "type": "file",
            "path": relpath,
            "name": entry.name,
            "parent": parent,
            "size": stat.st_size,
            "mime_type": mime_type or "application/octet-stream",
            "modified_at": modified_at,
            "created_at": meta.get("created_at") or modified_at,
            "source": meta.get("source", "unknown"),
            "execution_id": meta.get("execution_id"),
            "selected_for_context": bool(meta.get("selected_for_context", False)),
        })
    return entries


def build_workspace_manifest(user_id: int, session_id: int) -> Optional[str]:
    """
    Short, LLM-context-ready summary of what's in this session's workspace -
    injected into the system/context prompt so the model knows these files
    exist without anyone having to ask "what did you just create?" first.
    Only files (folders aren't directly addressable by any tool).
    """
    files = [e for e in list_session_files(user_id, session_id) if e["type"] == "file"]
    if not files:
        return None
    lines = [f"- {f['path']} ({f['size']} Bytes, {f['mime_type']})" for f in files]
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


def _proposals_path(user_id: int, session_id: int) -> Path:
    return _workspace_dir(user_id, session_id) / PROPOSALS_FILENAME


def _load_proposals(user_id: int, session_id: int) -> List[dict]:
    path = _proposals_path(user_id, session_id)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _save_proposals(user_id: int, session_id: int, proposals: List[dict]) -> None:
    path = _proposals_path(user_id, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proposals), encoding="utf-8")


def create_proposal(
    user_id: int,
    session_id: int,
    filename: str,
    action: str,
    new_content: Optional[str],
    description: str,
) -> dict:
    """
    LIARA proposes a create/update/delete on a workspace file - never touches
    the real file, only appends a pending entry to the proposals sidecar. The
    diff is computed now (against whatever is on disk at proposal time) so
    the user reviews exactly what was proposed even if the file changes again
    before they get to it.
    """
    if action not in ("create", "update", "delete"):
        return {"ok": False, "error": f"Ungültige Aktion: {action}"}
    safe_name = _validate_filename(filename)
    if safe_name is None:
        return {"ok": False, "error": "Ungültiger Dateiname"}

    existing = read_session_file(user_id, session_id, safe_name)
    exists_on_disk = existing.get("found", False)

    if action == "create" and exists_on_disk:
        return {"ok": False, "error": "Datei existiert bereits"}
    if action in ("update", "delete") and not exists_on_disk:
        return {"ok": False, "error": "Datei nicht gefunden"}
    if action in ("create", "update"):
        if new_content is None:
            return {"ok": False, "error": "content ist erforderlich für create/update"}
        if len(new_content.encode("utf-8")) > MAX_SESSION_FILE:
            return {"ok": False, "error": f"Vorschlag zu groß (Limit {MAX_SESSION_FILE // (1024 * 1024)} MiB)"}

    old_text = existing.get("content") or "" if exists_on_disk else ""
    new_text = new_content if action != "delete" else ""
    diff = "\n".join(difflib.unified_diff(
        old_text.splitlines(),
        new_text.splitlines(),
        fromfile=f"a/{safe_name}" if exists_on_disk else "/dev/null",
        tofile="/dev/null" if action == "delete" else f"b/{safe_name}",
        lineterm="",
    ))

    proposal = {
        "id": uuid.uuid4().hex,
        "filename": safe_name,
        "action": action,
        "new_content": new_content if action != "delete" else None,
        "diff": diff,
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "resolved_at": None,
    }
    proposals = _load_proposals(user_id, session_id)
    proposals.append(proposal)
    _save_proposals(user_id, session_id, proposals)
    return {"ok": True, "proposal_id": proposal["id"], "diff": diff}


def list_proposals(user_id: int, session_id: int, status: Optional[str] = None) -> List[dict]:
    proposals = _load_proposals(user_id, session_id)
    if status is None:
        return proposals
    return [p for p in proposals if p.get("status") == status]


def resolve_proposal(user_id: int, session_id: int, proposal_id: str, approve: bool) -> dict:
    """
    Applies (approve=True) or discards (approve=False) a pending proposal.
    Approval dispatches to the same create/write/delete_workspace_file
    functions every other workspace write already goes through - no separate
    mutation path, so proposals get the exact same size/traversal checks.
    """
    proposals = _load_proposals(user_id, session_id)
    proposal = next((p for p in proposals if p.get("id") == proposal_id), None)
    if proposal is None:
        return {"ok": False, "error": "Vorschlag nicht gefunden"}
    if proposal.get("status") != "pending":
        return {"ok": False, "error": f"Vorschlag ist bereits {proposal.get('status')}"}

    if approve:
        action = proposal["action"]
        filename = proposal["filename"]
        if action == "create":
            result = create_workspace_file(user_id, session_id, filename, proposal["new_content"])
        elif action == "update":
            result = write_workspace_file(user_id, session_id, filename, proposal["new_content"])
        else:  # delete
            result = delete_workspace_file(user_id, session_id, filename)

        if not result.get("ok"):
            return result

        if action in ("create", "update"):
            record_file_event(user_id, session_id, filename, source="liara")

        proposal["status"] = "approved"
    else:
        proposal["status"] = "rejected"

    proposal["resolved_at"] = datetime.now(timezone.utc).isoformat()
    _save_proposals(user_id, session_id, proposals)
    return {"ok": True}


def delete_session_workspace(user_id: int, session_id: int) -> bool:
    """Best-effort recursive delete, used when a chat session is deleted."""
    session_dir = _session_dir(user_id, session_id)
    if not session_dir.exists():
        return True
    try:
        shutil.rmtree(session_dir)
        return True
    except OSError:
        return False
