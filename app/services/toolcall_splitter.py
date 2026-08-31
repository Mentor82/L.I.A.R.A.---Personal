"""
Extracts <tool_call>...</tool_call> blocks from a streamed model response -
the LiNeP transport's equivalent of Ollama's native `message.tool_calls`
field. LiNeP's RequestEnvelope has no structured tool-calling channel (only
a plain `payload` string), so the LiNeP branch in chat_streaming.py falls
back to the same prompt-based tool-calling convention chat.py's sync path
already teaches the model via ToolRegistry.get_tool_descriptions_for_llm()
- this extractor is the streaming-safe counterpart of that.

Same buffering state machine as TaskBlockExtractor/FactCheckBlockExtractor
(see task_splitter.py) - a "safe tail" hold-back so a tag split across
streaming chunks is never falsely leaked as visible content. Deliberately
has no parse_x_items()-style function of its own: unlike tasks/factcheck,
a ready-made parser for this exact tag/JSON convention already exists
(tool_parser.get_tool_parser().extract_tool_call()) - callers should feed
completed blocks through that instead of duplicating its parsing/fuzzy-JSON
recovery logic here.
"""
from dataclasses import dataclass, field


@dataclass
class ToolCallBlockExtractor:
    OPEN_TAG: str = field(default="<tool_call>", init=False)
    CLOSE_TAG: str = field(default="</tool_call>", init=False)
    max_emissions: int = 5

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
        """Call once streaming ends. An incomplete (never-closed) tool_call
        block is discarded, not rendered - same contract as its siblings."""
        if self._state == "content":
            out, self._pending = self._pending, ""
            return out
        self._block_buffer = ""
        self._pending = ""
        return ""
