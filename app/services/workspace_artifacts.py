"""
Saves long-form "plan"/"final answer" content as a real file in a chat
session's Workspace instead of leaving it inline in Chat/Agent-Hub. Both
already key their file storage off the exact same (user_id, session_id) any
other Workspace write uses (see session_workspace.py) - no new storage
concept needed, just a shared filename convention plus a thin wrapper
around aci.create_file (already handles the write and manifest recording).
"""
import re
from datetime import datetime, timezone
from typing import Optional

from services import aci

_UNSAFE_CHARS = re.compile(r"[^a-zA-Z0-9äöüÄÖÜß _-]")


def _slugify(title: str, max_len: int = 40) -> str:
    cleaned = _UNSAFE_CHARS.sub("", title).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:max_len] or "Ergebnis"


def save_artifact(user_id: int, session_id: int, title: str, content: str, prefix: str = "Ergebnis") -> Optional[str]:
    """
    Writes `content` as a Markdown file into the session's Workspace,
    returning the filename on success or None on failure - best-effort,
    callers already hold the content itself as a fallback to still show
    inline if this fails.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    filename = f"{prefix}_{timestamp}_{_slugify(title)}.md"
    result = aci.create_file(
        content=content, user_id=user_id, session_id=session_id,
        filename=filename, overwrite=True
    )
    return filename if result.get("success") else None
