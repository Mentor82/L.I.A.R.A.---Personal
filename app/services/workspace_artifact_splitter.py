"""
Extracts <workspace_artifact>...</workspace_artifact> blocks from a streamed
chat response - the plain-chat equivalent of what the Agent Hub already does
automatically for its own "Endergebnis" (see base_agent.py): a long-form
plan/document the model produces gets saved as a real file in the session's
Workspace instead of filling up the chat scrollback, with just a short
reference card left in its place (see build_workspace_artifact_instructions()
in prompt_builder.py for the model-facing convention).

Same buffering state machine as ToolCallBlockExtractor/TaskBlockExtractor
(see toolcall_splitter.py/task_splitter.py) - a "safe tail" hold-back so a
tag split across streaming chunks is never falsely leaked as visible
content. Deliberately plain "Titel: ..." text inside the tag instead of
JSON: this exact codebase already hit models producing invalid/incomplete
JSON for prompt-based conventions (see tool_registry.py's enum-visibility
fix) - and unlike tool-calling, a malformed block here has no retry loop to
fall back on, so the convention asks for as little structure as possible.
"""
from dataclasses import dataclass, field


@dataclass
class WorkspaceArtifactBlockExtractor:
    OPEN_TAG: str = field(default="<workspace_artifact>", init=False)
    CLOSE_TAG: str = field(default="</workspace_artifact>", init=False)
    max_emissions: int = 3

    _state: str = "content"  # "content" <-> "in_block"
    _pending: str = ""
    _block_buffer: str = ""
    _emitted_count: int = 0

    def feed(self, delta: str) -> tuple[str, list[str]]:
        """Returns (content_part, completed_blocks) for this delta - see
        TaskBlockExtractor.feed() for the full contract, identical here."""
        self._pending += delta
        content_out = []
        completed = []

        while True:
            if self._state == "content":
                idx = self._pending.find(self.OPEN_TAG)
                if idx == -1:
                    safe_len = max(0, len(self._pending) - (len(self.OPEN_TAG) - 1))
                    content_out.append(self._pending[:safe_len])
                    self._pending = self._pending[safe_len:]
                    break
                content_out.append(self._pending[:idx])
                self._pending = self._pending[idx + len(self.OPEN_TAG):]
                self._state = "in_block"
                self._block_buffer = ""
            else:  # "in_block"
                self._block_buffer += self._pending
                self._pending = ""
                idx = self._block_buffer.find(self.CLOSE_TAG)
                if idx == -1:
                    break
                block_text = self._block_buffer[:idx]
                self._pending = self._block_buffer[idx + len(self.CLOSE_TAG):]
                self._block_buffer = ""
                self._state = "content"
                if self._emitted_count < self.max_emissions:
                    completed.append(block_text)
                    self._emitted_count += 1

        return "".join(content_out), completed

    def flush(self) -> str:
        """Call once streaming ends. An incomplete (never-closed) artifact
        block is discarded, not rendered - same contract as its siblings."""
        if self._state == "content":
            out, self._pending = self._pending, ""
            return out
        self._block_buffer = ""
        self._pending = ""
        return ""


def parse_workspace_artifact(raw_block: str) -> tuple[str, str]:
    """
    Splits a completed block's raw text into (title, content). Expected
    shape (see build_workspace_artifact_instructions()):

        Titel: <kurzer Titel>
        Inhalt:
        <markdown-Inhalt>

    Tolerant of a model skipping the "Titel:"/"Inhalt:" labels entirely -
    falls back to a generic title and treats the whole block as content
    rather than rejecting it outright (there's no retry path here, unlike
    tool-calling's parse_error branch).
    """
    lines = raw_block.strip("\n").split("\n")
    title = "Ergebnis"
    content_start = 0

    if lines and lines[0].strip().lower().startswith("titel:"):
        candidate = lines[0].split(":", 1)[1].strip()
        if candidate:
            title = candidate
        content_start = 1

    while content_start < len(lines) and lines[content_start].strip().lower() in ("inhalt:", ""):
        content_start += 1

    content = "\n".join(lines[content_start:]).strip()
    return title, content or raw_block.strip()
