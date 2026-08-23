"""
Splits streamed model output into (thinking, answer) as chunks arrive.

Reasoning models (deepseek-r1 and similar) emit a `<think>...</think>` block
before the actual answer. Left alone, that block streams straight into the
visible chat text with no separation - this splits it out so the caller can
emit it as a distinct SSE event (e.g. "thinking") instead of "content".

Scope: a single <think>...</think> pair at the very start of the response,
which is how every reasoning model observed in practice emits it - not a
general repeated-toggle parser. Models that never emit the tag pass straight
through after a short sniff window, at effectively no cost.
"""
from dataclasses import dataclass, field


@dataclass
class ThinkingSplitter:
    OPEN_TAG: str = field(default="<think>", init=False)
    CLOSE_TAG: str = field(default="</think>", init=False)

    _state: str = "sniffing"  # "sniffing" -> "thinking" -> "content"
    _pending: str = ""

    def feed(self, delta: str) -> tuple[str, str]:
        """Returns (thinking_part, content_part) to emit for this delta."""
        if self._state == "content":
            return "", delta

        self._pending += delta

        if self._state == "sniffing":
            stripped = self._pending.lstrip()
            if len(stripped) < len(self.OPEN_TAG):
                # Not enough data yet to know either way - unless what we
                # have already can't possibly be a prefix of "<think>".
                if stripped and not self.OPEN_TAG.startswith(stripped):
                    self._state = "content"
                    out = self._pending
                    self._pending = ""
                    return "", out
                return "", ""  # wait for more

            if stripped.startswith(self.OPEN_TAG):
                self._state = "thinking"
                self._pending = stripped[len(self.OPEN_TAG):]
            else:
                self._state = "content"
                out = self._pending
                self._pending = ""
                return "", out

        if self._state == "thinking":
            if self.CLOSE_TAG in self._pending:
                before, _, after = self._pending.partition(self.CLOSE_TAG)
                self._state = "content"
                self._pending = ""
                return before, after
            # Keep a short tail back in case CLOSE_TAG is split across a
            # chunk boundary - only flush what can't be part of it.
            safe_len = max(0, len(self._pending) - (len(self.CLOSE_TAG) - 1))
            thinking_out = self._pending[:safe_len]
            self._pending = self._pending[safe_len:]
            return thinking_out, ""

        return "", ""

    def flush(self) -> tuple[str, str]:
        """Call once streaming ends, to emit anything still buffered (e.g. a
        response that never closed its <think> tag)."""
        if self._state == "thinking":
            out, self._pending = self._pending, ""
            return out, ""
        if self._state == "sniffing" and self._pending:
            out, self._pending = self._pending, ""
            return "", out
        return "", ""
