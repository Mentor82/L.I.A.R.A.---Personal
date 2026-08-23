"""
Shared system-prompt building blocks for chat.py and chat_streaming.py.

Both routers build a Liara system prompt from the same per-user
ingredients (personality preset, custom instructions, current date/time)
but previously did so with separate, independently-maintained inline
code - a change to how personality or instructions get worded had to be
made twice, and it was easy for one path to silently drift from the
other (which is exactly what happened before this module existed).

This does NOT unify the two routers' entire prompts - chat.py and
chat_streaming.py have genuinely different capabilities (chat.py
supports MCP tool-calling via a separate tool_registry/tool_executor
mechanism that chat_streaming.py doesn't have at all), so each still
layers its own additional instructions on top of what's built here.
"""

from datetime import datetime
from typing import Optional

from liara_engine.personality import get_personality_prompt

WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS_DE = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
             "Juli", "August", "September", "Oktober", "November", "Dezember"]


def build_temporal_context() -> str:
    """Current date/time, formatted in German, for system-prompt injection."""
    now = datetime.now()
    weekday = WEEKDAYS_DE[now.weekday()]
    return f"{weekday}, {now.day}. {MONTHS_DE[now.month]} {now.year}, {now.hour:02d}:{now.minute:02d} Uhr"


def build_personality_and_instructions_block(
    username: Optional[str],
    personality: Optional[str],
    custom_instructions: Optional[str]
) -> str:
    """
    The per-user personalization block shared by both chat paths: the
    personality preset's prompt modifier, plus the user's own standing
    custom instructions (if any).
    """
    block = f"Persönlichkeit: {get_personality_prompt(personality)}"
    if custom_instructions:
        block += f"\n\nIndividuelle Anweisungen von {username}:\n{custom_instructions}"
    return block
