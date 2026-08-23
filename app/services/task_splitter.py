"""
Extracts <tasks>...</tasks> blocks from a streamed model response, wherever
they appear - not just at the start (unlike ThinkingSplitter, which only
ever checks for a single leading <think> block). A model may emit this tag
once up front to declare its plan for a multi-step answer, then again later
in the same response to re-state it with items checked off as it addresses
them.

Scope note: what comes out of a completed block is a MODEL-AUTHORED plan
display, not a verified execution record - a checked item only means the
model claims to have covered that step in its own text so far, not that any
tool or orchestrator confirmed it actually happened. That distinction
changes once a real multi-step Agent loop exists: "done" would then come
from the system/tool result, not the model's own text, using this same
{id, label, done} shape. See the "Aufgaben" plan for the fuller reasoning.
"""
import re
from dataclasses import dataclass, field

_ITEM_PATTERN = re.compile(r'^-\s*\[([ xX])\]\s*(.+)$', re.MULTILINE)


def parse_task_items(raw_block_text: str) -> list[dict]:
    """Parses '- [ ] label' / '- [x] label' lines from a completed <tasks>
    block into structured items for the SSE payload - so the frontend never
    has to re-parse checklist markdown itself."""
    items = []
    for i, match in enumerate(_ITEM_PATTERN.finditer(raw_block_text)):
        items.append({
            'id': f'step-{i}',
            'label': match.group(2).strip(),
            'done': match.group(1).lower() == 'x'
        })
    return items


@dataclass
class TaskBlockExtractor:
    OPEN_TAG: str = field(default="<tasks>", init=False)
    CLOSE_TAG: str = field(default="</tasks>", init=False)
    max_emissions: int = 5

    _state: str = "content"  # "content" <-> "in_block"
    _pending: str = ""
    _block_buffer: str = ""
    _emitted_count: int = 0

    def feed(self, delta: str) -> tuple[str, list[str]]:
        """Returns (content_part, completed_blocks) for this delta.

        content_part is delta with any <tasks>...</tasks> text removed -
        it never appears in the visible answer. completed_blocks holds the
        raw inner text of each block that closed during this delta (almost
        always 0 or 1, but a delta could in principle close one and
        open+close another). Once max_emissions completed blocks have been
        returned in total, later blocks are still stripped from content but
        silently dropped instead of returned - a guard against a model
        re-emitting the block on every paragraph.
        """
        self._pending += delta
        content_out = []
        completed = []

        while True:
            if self._state == "content":
                idx = self._pending.find(self.OPEN_TAG)
                if idx == -1:
                    # No open tag in what we have - flush everything except
                    # a safe tail that could still be its start, same
                    # partial-match technique ThinkingSplitter uses.
                    safe_len = max(0, len(self._pending) - (len(self.OPEN_TAG) - 1))
                    content_out.append(self._pending[:safe_len])
                    self._pending = self._pending[safe_len:]
                    break
                content_out.append(self._pending[:idx])
                self._pending = self._pending[idx + len(self.OPEN_TAG):]
                self._state = "in_block"
                self._block_buffer = ""
                # loop again: remaining pending may already hold the close tag
            else:  # "in_block"
                self._block_buffer += self._pending
                self._pending = ""
                idx = self._block_buffer.find(self.CLOSE_TAG)
                if idx == -1:
                    break  # block text is never content; nothing to emit yet
                block_text = self._block_buffer[:idx]
                self._pending = self._block_buffer[idx + len(self.CLOSE_TAG):]
                self._block_buffer = ""
                self._state = "content"
                if self._emitted_count < self.max_emissions:
                    completed.append(block_text)
                    self._emitted_count += 1
                # loop again to process the remainder as content

        return "".join(content_out), completed

    def flush(self) -> str:
        """Call once streaming ends. Returns any buffered plain content; an
        incomplete (never-closed) <tasks> block is discarded outright, not
        rendered - a half-parsed checklist in the UI is worse than none."""
        if self._state == "content":
            out, self._pending = self._pending, ""
            return out
        self._block_buffer = ""
        self._pending = ""
        return ""
