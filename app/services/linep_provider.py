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
"""
from __future__ import annotations

import asyncio
import itertools
import logging
import os
import socket
from functools import lru_cache
from typing import AsyncIterator, Optional

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

    async def generate_stream(
        self, prompt: str, model: str, num_predict: int = 2000
    ) -> AsyncIterator[str]:
        """Streams token deltas from a LiNeP-routed GENERATE call.

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
        queue: "asyncio.Queue[tuple[Optional[str], Optional[Exception]]]" = asyncio.Queue()

        def _worker():
            try:
                client = LiNePClient(host=host, port=port, timeout=timeout)
                with client:
                    for event in client.execute_stream(request):
                        if event.event_type == EventType.CONTENT_DELTA and event.payload:
                            loop.call_soon_threadsafe(queue.put_nowait, (event.payload, None))
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
    """Read directly from the environment (same convention as the rest of
    the codebase - app/core/config.py's Settings class is not otherwise
    wired into the chat hot path, and its own undeclared-.env-key
    validation once broke the whole app the moment anything did import it -
    deliberately not depending on it here)."""
    return os.environ.get("LINEP_ENABLED", "").strip().lower() in ("1", "true", "yes")


@lru_cache
def get_linep_provider() -> LinepChatProvider:
    return LinepChatProvider(
        host=os.environ.get("LINEP_HOST", "127.0.0.1"),
        port=int(os.environ.get("LINEP_PORT", "11435")),
        timeout=float(os.environ.get("LINEP_TIMEOUT_SECONDS", "180.0")),
    )
