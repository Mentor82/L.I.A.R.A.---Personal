"""
Generator Helpers - LiNeP & Artifact Parsing Helpers
====================================================
Extracted helper functions for generator stage.
"""

import sys
import json
import asyncio
from typing import List, Dict, Optional

from services.prompt_builder import _format_tool_result_for_llm, _get_tool_aware_system_prompt
from services.tool_parser import get_tool_parser
from services.workspace_artifact_splitter import parse_workspace_artifact
from services.workspace_artifacts import save_artifact


def _resolve_symbol(name: str, fallback):
    mod = sys.modules.get("api.routers.chat_streaming")
    if mod and hasattr(mod, name):
        return getattr(mod, name)
    return fallback


def _flatten_messages_for_linep(messages: List[Dict], include_tools: bool) -> str:
    """Turns the OpenAI-style messages list into a single prompt string for LiNeP."""
    parts = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content") or ""
        if role == "system":
            if include_tools:
                content = f"{content}\n\n{_get_tool_aware_system_prompt()}"
            parts.append(content)
        elif role == "tool":
            try:
                tool_result = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                tool_result = {"result": content}
            parts.append(f"Tool-Ergebnis:\n{_format_tool_result_for_llm(tool_result)}")
        elif role == "assistant":
            if content:
                parts.append(f"Assistant: {content}")
        else:
            parts.append(f"User: {content}")
    parts.append("Assistant:")
    return "\n\n".join(parts)


def _append_linep_tool_call(turn_tool_calls: List[Dict], raw_block: str) -> None:
    """Parses a completed <tool_call> block from LiNeP."""
    parsed = get_tool_parser().extract_tool_call(f"<tool_call>{raw_block}</tool_call>")
    if parsed:
        turn_tool_calls.append({"function": {"name": parsed.tool_name, "arguments": parsed.parameters}})


async def _handle_workspace_artifact_blocks(raw_blocks: List[str], user_id: Optional[int], session_id: Optional[int]):
    """Saves each completed <workspace_artifact> block and yields its SSE line."""
    for raw_block in raw_blocks:
        title, content = parse_workspace_artifact(raw_block)
        filename = None
        if user_id is not None and session_id is not None:
            filename = await asyncio.to_thread(save_artifact, user_id, session_id, title, content, "Plan")
        payload = {"type": "workspace_artifact", "title": title, "filename": filename}
        if filename is None:
            payload["content"] = content
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def calculate_usage_stats(
    prompt_tokens: int,
    eval_tokens: int,
    thinking_text: str,
    response_text: str,
    messages: Optional[List[Dict]] = None
) -> Dict[str, int]:
    """Calculates structured token statistics for input, thinking, output, and total."""
    if prompt_tokens <= 0 and messages:
        prompt_chars = sum(len(str(m.get("content", ""))) for m in messages if isinstance(m, dict))
        prompt_tokens = max(1, round(prompt_chars / 3.8))

    think_len = len(thinking_text) if thinking_text else 0
    resp_len = len(response_text) if response_text else 0
    total_gen_chars = think_len + resp_len

    if eval_tokens <= 0 and total_gen_chars > 0:
        eval_tokens = max(1, round(total_gen_chars / 3.8))

    if think_len > 0 and total_gen_chars > 0 and eval_tokens > 0:
        tokens_think = round(eval_tokens * (think_len / total_gen_chars))
        tokens_out = max(0, eval_tokens - tokens_think)
    else:
        tokens_think = 0
        tokens_out = max(0, eval_tokens)

    tokens_in = max(0, prompt_tokens)
    tokens_total = tokens_in + tokens_think + tokens_out

    return {
        "in": tokens_in,
        "think": tokens_think,
        "out": tokens_out,
        "total": tokens_total
    }
