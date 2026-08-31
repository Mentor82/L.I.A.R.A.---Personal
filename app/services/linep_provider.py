"""
Experimental LiNeP V0.2 transport for chat generation - an alternate path to
Ollama alongside the existing raw-httpx call in chat_streaming.py, via the
linep-server already running locally on this same machine (forwards to the
same Ollama daemon at 127.0.0.1:11434).

Ported from www.mw-dresden.de's LinepChatProvider
(modules/ai/infrastructure/linep_chat_provider.py), reduced to a static
host/port - no NodeService/UDP-scheduler client here, since only one worker
(this host itself) is in play. See the LiNeP-switch plan for the full
design rationale.

Uses RuntimeProfile.GENERATE, not CHAT: GENERATE forwards `payload` to
Ollama verbatim (no chat-template reformatting), which matters here because
the caller has already flattened the full system prompt + conversation +
tool instructions into one string - CHAT's own reformatting would fight
with that instead of helping.

generate_stream() yields (kind, payload) tuples - "content"/"thinking"/
"tool_call" - instead of plain content strings: the deployed linep-server
(Mentor82/LiNeP-Ollama, commit b1d4236+) natively emits EventType.
REASONING_DELTA for reasoning-model thinking tokens and EventType.TOOL_CALL
(payload is Ollama's own api.ToolCall JSON: {"id":.., "function":
{"name":..,"arguments":..}}) for tool calls, on BOTH GENERATE and CHAT
profiles - so the model's own text stream never has to be scraped for
<think>/<tool_call> tags the way it did before this server-side fix
(task/factcheck/toolcall-tag extraction in chat_streaming.py is kept as a
defensive fallback for a server that predates this, not the primary path).
"""
from __future__ import annotations

import asyncio
import itertools
import logging
import socket
from functools import lru_cache
from typing import AsyncIterator, Optional

from core.config import settings

logger = logging.getLogger(__name__)

_request_ids = itertools.count(1)


class LinepUnavailableError(Exception):
    """Raised when the LiNeP transport fails or the runtime reports a failure mid-stream."""


def _import_linep():
    """The `linep` package is not a normal requirements.txt dependency (not
    on public PyPI, only needed at all when LINEP_ENABLED=true - see
    requirements.txt) - importing it at module level would break chat
    entirely on any deploy that hasn't built/installed that wheel, even
    with the feature flag off. Deferred here so chat_streaming.py can always
    import this module; only actually using the LiNeP path requires the
    package to be present.
    """
    try:
        from linep.v0_2.client import LiNePClient
        from linep.v0_2.constants import EventType, RuntimeProfile
        from linep.v0_2.envelopes import RequestEnvelope, StreamIdentity
    except ImportError as error:
        raise LinepUnavailableError(
            "linep package not installed - see requirements.txt for the LINEP_ENABLED setup note"
        ) from error
    return LiNePClient, EventType, RuntimeProfile, RequestEnvelope, StreamIdentity


class LinepChatProvider:
    def __init__(self, host: str, port: int, timeout: float = 180.0) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        # None = not yet queried this process; False = queried and failed
        # (package missing, connection refused, or an old server that
        # doesn't answer CAPABILITIES at all). Capabilities don't change at
        # runtime for a given server, so one successful query is cached for
        # the process lifetime - same pattern as ollama_capabilities.py.
        self._capabilities_cache = None

    async def health(self) -> bool:
        """Best-effort TCP reachability check, not a protocol handshake -
        confirms something accepts a connection on the data-plane port, not
        that it actually answers LiNeP requests. Enough to avoid routing a
        request into a transport that's clearly down. Also fails fast (no
        TCP probe) if the `linep` package itself isn't installed, so a
        missing dependency shows up as an unhealthy transport (falls back to
        Ollama-HTTP) rather than an error mid-stream on the first real call.
        """
        try:
            _import_linep()
        except LinepUnavailableError:
            return False
        return await asyncio.to_thread(self._probe_reachable)

    def _probe_reachable(self) -> bool:
        try:
            with socket.create_connection((self._host, self._port), timeout=3.0):
                return True
        except OSError:
            return False

    async def supports_reasoning_deltas(self) -> bool:
        """Whether the CONNECTED server (not the Ollama model) natively
        splits reasoning into EventType.REASONING_DELTA - queried directly
        rather than assumed, so a future rollback to an older linep-server
        (which doesn't even answer a capabilities query, confirmed live)
        safely falls back to false instead of silently leaking reasoning
        text as visible content again."""
        caps = await self._get_capabilities()
        return bool(caps and caps.descriptor.supports_reasoning_deltas)

    async def _get_capabilities(self):
        if self._capabilities_cache is not None:
            return self._capabilities_cache or None
        try:
            caps = await asyncio.to_thread(self._query_capabilities_sync)
        except Exception:
            caps = None
        self._capabilities_cache = caps if caps is not None else False
        return caps

    def _query_capabilities_sync(self):
        LiNePClient, *_rest = _import_linep()
        client = LiNePClient(host=self._host, port=self._port, timeout=5.0)
        with client:
            return client.query_capabilities()

    async def generate_stream(
        self, prompt: str, model: str, num_predict: int = 2000
    ) -> AsyncIterator[tuple[str, str]]:
        """Streams (kind, payload) tuples from a LiNeP-routed GENERATE call,
        kind being "content", "thinking", or "tool_call" (see module
        docstring for the native REASONING_DELTA/TOOL_CALL event mapping).

        Sync LiNePClient socket calls run on a worker thread; results cross
        back to this coroutine via an asyncio.Queue fed through
        call_soon_threadsafe, same bridge pattern as the mw-dresden original.
        """
        LiNePClient, EventType, RuntimeProfile, RequestEnvelope, StreamIdentity = _import_linep()

        request = RequestEnvelope(
            stream=StreamIdentity(
                request_id=next(_request_ids), execution_id=next(_request_ids), output_id=0
            ),
            profile=RuntimeProfile.GENERATE,
            model_id=model,
            payload=prompt,
            max_tokens=num_predict,
        )

        host, port, timeout = self._host, self._port, self._timeout
        loop = asyncio.get_running_loop()
        queue: "asyncio.Queue[tuple[Optional[tuple[str, str]], Optional[Exception]]]" = asyncio.Queue()

        def _worker():
            try:
                client = LiNePClient(host=host, port=port, timeout=timeout)
                with client:
                    for event in client.execute_stream(request):
                        if event.event_type == EventType.CONTENT_DELTA and event.payload:
                            loop.call_soon_threadsafe(queue.put_nowait, (("content", event.payload), None))
                        elif event.event_type == EventType.REASONING_DELTA and event.payload:
                            loop.call_soon_threadsafe(queue.put_nowait, (("thinking", event.payload), None))
                        elif event.event_type == EventType.TOOL_CALL and event.payload:
                            loop.call_soon_threadsafe(queue.put_nowait, (("tool_call", event.payload), None))
                        elif event.event_type == EventType.FAILED:
                            message = (
                                event.error.message
                                if event.error and event.error.message
                                else "LiNeP runtime reported a failure"
                            )
                            loop.call_soon_threadsafe(
                                queue.put_nowait, (None, LinepUnavailableError(message))
                            )
                            return
                loop.call_soon_threadsafe(queue.put_nowait, (None, None))
            except Exception as error:
                err = (
                    error
                    if isinstance(error, LinepUnavailableError)
                    else LinepUnavailableError(f"LiNeP transport failed: {error}")
                )
                loop.call_soon_threadsafe(queue.put_nowait, (None, err))

        asyncio.create_task(asyncio.to_thread(_worker))

        while True:
            item, err = await queue.get()
            if err is not None:
                raise err
            if item is None:
                break
            yield item


def linep_enabled() -> bool:
    """Via core.config.settings, not plain os.environ.get(): main.py's own
    load_dotenv() call uses a path relative to CWD ("../.env") that doesn't
    actually resolve to this app's real .env under its systemd
    WorkingDirectory, so .env values never reach real process environment
    variables here - confirmed live, this is why an os.environ-based
    version of this function silently always returned False. Settings'
    own env_file loading (pydantic-settings, resolved relative to CWD
    at instantiation) reads the real file correctly regardless."""
    return settings.linep_enabled


@lru_cache
def get_linep_provider() -> LinepChatProvider:
    return LinepChatProvider(
        host=settings.linep_host,
        port=settings.linep_port,
        timeout=settings.linep_timeout_seconds,
    )
