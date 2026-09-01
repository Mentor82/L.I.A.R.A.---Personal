"""
Chat Archive Service (Issue #22)
================================
Provides persistent archiving and export of chat sessions into the workspace
file tree (chat_archives/) as structured Markdown or JSON documents.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from api.models.chat_session import ChatSession
from api.models.chat_message import ChatMessage
from services.session_workspace import write_workspace_file, create_workspace_folder


def sanitize_filename(title: str, max_length: int = 50) -> str:
    """Sanitizes session title for safe filesystem paths."""
    # Replace non-alphanumeric chars with underscores
    clean = re.sub(r'[^a-zA-Z0-9äöüÄÖÜß_-]+', '_', title.strip())
    clean = re.sub(r'_+', '_', clean).strip('_')
    if not clean:
        clean = "chat_archive"
    return clean[:max_length]


def format_session_as_markdown(session: ChatSession, messages: List[ChatMessage]) -> str:
    """
    Formats a chat session and its turns into a clean, structured Markdown document.
    Includes frontmatter metadata, thinking traces, tool cards, and sources.
    """
    created_str = session.created_at.strftime("%Y-%m-%d %H:%M:%S") if session.created_at else "Unknown"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Collect distinct models used
    models_used = sorted(list({msg.model for msg in messages if msg.model}))
    models_str = ", ".join(models_used) if models_used else "default"

    lines = [
        "---",
        f"title: \"{session.title or 'Chat Session'}\"",
        f"session_id: {session.id}",
        f"user_id: {session.user_id}",
        f"created_at: \"{created_str}\"",
        f"archived_at: \"{now_str}\"",
        f"messages_count: {len(messages)}",
        f"models_used: \"{models_str}\"",
        "---",
        "",
        f"# {session.title or 'Chat Session'}",
        "",
        f"> **Archivierte Konversation** (Sitzungs-ID: `{session.id}` | Erstellt: {created_str} | Modelle: `{models_str}`)",
        "",
        "---",
        "",
    ]

    for idx, msg in enumerate(messages, 1):
        role_label = "**User**" if msg.role == "user" else "**LIARA (Assistant)**"
        if msg.role == "system":
            role_label = "**System**"
        elif msg.role == "error":
            role_label = "**Fehlermeldung**"

        timestamp_str = msg.timestamp.strftime("%H:%M:%S") if msg.timestamp else ""
        header = f"### Turn {idx} — {role_label}"
        if timestamp_str:
            header += f" `[{timestamp_str}]`"
        if msg.model:
            header += f" `({msg.model})`"

        lines.append(header)
        lines.append("")

        content = msg.content or ""

        # Format reasoning/thinking traces if embedded in <think> tags
        if "<think>" in content and "</think>" in content:
            parts = content.split("</think>")
            for p in parts[:-1]:
                if "<think>" in p:
                    think_text = p.split("<think>")[1].strip()
                    lines.append("<details>")
                    lines.append("<summary>💭 <i>Gedankengang (Reasoning Trace)</i></summary>\n")
                    lines.append(f"{think_text}\n")
                    lines.append("</details>\n")
            actual_content = parts[-1].strip()
            if actual_content:
                lines.append(actual_content)
                lines.append("")
        else:
            lines.append(content)
            lines.append("")

        # Format Tool Calls if present in action_result
        if msg.action_result and isinstance(msg.action_result, dict):
            tool_name = msg.action_result.get("tool_name") or msg.action_result.get("tool")
            if tool_name:
                lines.append(f"> 🛠️ **Ausgeführtes Tool:** `{tool_name}`")
                output = msg.action_result.get("output") or msg.action_result.get("result")
                if output:
                    lines.append("```json")
                    lines.append(json.dumps(output, indent=2, ensure_ascii=False) if isinstance(output, (dict, list)) else str(output))
                    lines.append("```\n")

        # Format Web Search Sources if present
        if msg.web_search_results and isinstance(msg.web_search_results, list) and msg.web_search_results:
            lines.append("#### 🌐 Quellennachweise:")
            for s in msg.web_search_results:
                if isinstance(s, dict):
                    title = s.get("title", "Quelle")
                    url = s.get("url", "#")
                    snippet = s.get("snippet", "")
                    lines.append(f"- [{title}]({url}) — *{snippet[:120]}...*" if snippet else f"- [{title}]({url})")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def format_session_as_json(session: ChatSession, messages: List[ChatMessage]) -> Dict[str, Any]:
    """Formats session and messages into a clean JSON export structure."""
    return {
        "metadata": {
            "session_id": session.id,
            "user_id": session.user_id,
            "title": session.title,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "messages_count": len(messages),
        },
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "model": msg.model,
                "mood": msg.mood,
                "action_result": msg.action_result,
                "web_search_results": msg.web_search_results,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
            }
            for msg in messages
        ]
    }


def archive_session_to_workspace(
    user_id: int,
    session_id: int,
    db: Session,
    target_folder: str = "chat_archives"
) -> Dict[str, Any]:
    """
    Exports the canonical chat session to a markdown archive file directly inside
    the user's workspace directory at `chat_archives/<title>_<session_id>_<timestamp>.md`.
    """
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id
    ).first()

    if not session:
        return {"ok": False, "error": f"Sitzung {session_id} nicht gefunden oder kein Zugriff"}

    # Fetch messages ordered chronologically
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.timestamp.asc(), ChatMessage.id.asc()).all()

    # Generate markdown content
    markdown_content = format_session_as_markdown(session, messages)

    # Ensure target directory in workspace exists
    if target_folder:
        create_workspace_folder(user_id, session_id, target_folder)

    # Construct filename
    clean_title = sanitize_filename(session.title or "chat")
    timestamp_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{clean_title}_{session_id}_{timestamp_suffix}.md"
    rel_path = f"{target_folder}/{filename}" if target_folder else filename

    # Write file into session workspace
    write_result = write_workspace_file(
        user_id=user_id,
        session_id=session_id,
        rel_path=rel_path,
        content=markdown_content
    )

    if not write_result.get("ok"):
        return write_result

    return {
        "ok": True,
        "filename": filename,
        "filepath": rel_path,
        "size_bytes": len(markdown_content.encode("utf-8")),
        "messages_archived": len(messages),
        "message": f"Sitzung erfolgreich als '{rel_path}' im Workspace archiviert."
    }
