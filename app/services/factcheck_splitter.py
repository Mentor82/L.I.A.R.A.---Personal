"""
Extracts <factcheck>...</factcheck> blocks from a streamed model response,
same buffering approach as task_splitter.py's TaskBlockExtractor (see that
module for the full reasoning behind the two-state machine and "safe tail"
technique - this is a near-verbatim copy with a different tag/item grammar).

Purpose: a web-search-grounded answer can cite real, genuinely-found sources
while still stating specific details (exact counts, named incidents, precise
attributions) that go beyond what those sources actually say - the story is
real, some of the numbers aren't. This block lets the model rate its own
load-bearing claims against what the shown sources support, giving the
frontend a per-claim confidence signal instead of just an undifferentiated
source list at the end. It supplements normal in-prose citation, it doesn't
replace it.

Confidence is deliberately source-centric, not self-diagnostic: the model
rates what the shown sources support, not where its own knowledge came from
(introspecting the latter isn't something a model can reliably do).
"""
import re
from dataclasses import dataclass, field

_ITEM_PATTERN = re.compile(
    r'^-\s*\[(bestätigt|teilweise|unbestätigt)(?:\|([^\]]+))?\]\s*(.+)$',
    re.MULTILINE
)


def parse_factcheck_items(raw_block_text: str) -> list[dict]:
    """Parses '- [confidence|source] claim' lines from a completed
    <factcheck> block into structured items for the SSE payload - so the
    frontend never has to re-parse this markup itself."""
    items = []
    for i, match in enumerate(_ITEM_PATTERN.finditer(raw_block_text)):
        source = match.group(2)
        items.append({
            'id': f'claim-{i}',
            'label': match.group(3).strip(),
            'confidence': match.group(1),
            'source': source.strip() if source else None
        })
    return items


@dataclass
class FactCheckBlockExtractor:
    OPEN_TAG: str = field(default="<factcheck>", init=False)
    CLOSE_TAG: str = field(default="</factcheck>", init=False)
    # Guard rail against a model re-emitting the block repeatedly, not a
    # target count - a factcheck block is conceptually a single closing
    # summary, unlike <tasks> which is expected to reappear as steps get
    # checked off.
    max_emissions: int = 5

    _state: str = "content"  # "content" <-> "in_block"
    _pending: str = ""
    _block_buffer: str = ""
    _emitted_count: int = 0

    def feed(self, delta: str) -> tuple[str, list[str]]:
        """Returns (content_part, completed_blocks) for this delta.

        content_part is delta with any <factcheck>...</factcheck> text
        removed - it never appears in the visible/persisted answer.
        completed_blocks holds the raw inner text of each block that closed
        during this delta (almost always 0 or 1). Once max_emissions
        completed blocks have been returned in total, later blocks are
        still stripped from content but silently dropped instead of
        returned.
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
        incomplete (never-closed) <factcheck> block is discarded outright,
        not rendered - a half-parsed fact-check in the UI is worse than
        none."""
        if self._state == "content":
            out, self._pending = self._pending, ""
            return out
        self._block_buffer = ""
        self._pending = ""
        return ""
