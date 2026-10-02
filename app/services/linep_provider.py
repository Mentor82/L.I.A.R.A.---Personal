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

Uses RuntimeProfile.CHAT, not GENERATE (changed from an earlier version of
this file): GENERATE forwards `payload` verbatim with no chat-template
reformatting, which was originally chosen so the caller's own flattened
system-prompt/conversation/tool-instructions string wouldn't be fought by
Ollama's template - but it also meant reasoning never got natively
classified at all (Ollama's raw /api/generate never populates a "thinking"
field, confirmed live with multiple models). Mentor82/LiNeP-Ollama commit
2af68a6 made CHAT use Ollama's own native model-family response parser
(resp.Message.Thinking/.ToolCalls/.Content) instead of a text-level tag
scanner, but that native parsing only exists on the CHAT code path - so
this switches profiles despite CHAT wrapping the whole flattened payload
into a single "user"-role api.Message before forwarding to Ollama's
/api/chat (still no structured multi-message channel over the wire; the
caller still has to flatten everything into one string either way).

generate_stream() yields (kind, payload) tuples - "content"/"thinking"/
"tool_call" - instead of plain content strings: the deployed linep-server
natively emits EventType.REASONING_DELTA for reasoning-model thinking
tokens and EventType.TOOL_CALL (payload is Ollama's own api.ToolCall JSON:
{"id":.., "function": {"name":..,"arguments":..}}) for tool calls, so the
model's own text stream never has to be scraped for <think>/<tool_call>
tags (task/factcheck/toolcall-tag extraction in chat_streaming.py is kept
as a defensive fallback for a server that predates this, not the primary
path).

Cluster trunk mode (Personal#29 B1): with LINEP_TRUNK_HOST set, every call
goes to linepd on the cluster instead of the local linep-server - lease on the
control port, SL1-signed SESSION_BIND, signed frames (see services/linep_trunk.py).
Model ids may then be concrete models or "task:<name>"; linepd picks runtime
and node. There is no fallback to the local linep-server from inside this
class: if the trunk is down, health() is false and chat_streaming falls back
to Ollama-HTTP, as before.
"""
from __future__ import annotations

import asyncio
import itertools
import logging
import socket
import time
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
    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 180.0,
        control_port: int = 0,
        key_file: str = "",
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        # control_port + key_file set = cluster trunk mode (lease + SL1)
        self._control_port = control_port
        self._key_file = key_file
        self._health_checked_at = 0.0
        self._health_ok = False
        # None = not yet queried this process; False = queried and failed
        # (package missing, connection refused, or an old server that
        # doesn't answer CAPABILITIES at all). Capabilities don't change at
        # runtime for a given server, so one successful query is cached for
        # the process lifetime - same pattern as ollama_capabilities.py.
        self._capabilities_cache = None
        self._capabilities_failed_at = 0.0

    @property
    def trunk_mode(self) -> bool:
        return bool(self._control_port and self._key_file)

    def _connect_sync(self, timeout: float):
        """Connected client, bound to a lease + SL1 session in trunk mode.
        The caller closes it. The socket timeout is `timeout` afterwards."""
        LiNePClient, *_rest = _import_linep()
        if not self.trunk_mode:
            client = LiNePClient(host=self._host, port=self._port, timeout=timeout)
            client.connect()
            return client
        from services.linep_trunk import TrunkClient, TrunkRoute

        route = TrunkRoute(self._host, self._port, self._control_port, self._key_file)
        client = TrunkClient(route, timeout=10.0)
        try:
            client.connect()
            client.bind()
            client.timeout = timeout
            client._sock.settimeout(timeout)
        except BaseException:
            client.close()
            raise
        return client

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
        if self.trunk_mode:
            # A reachable port says nothing about the lease/SL1 handshake, so
            # trunk health is a real bind + CAPABILITIES, cached briefly.
            if time.monotonic() - self._health_checked_at < 15.0:
                return self._health_ok
            try:
                caps = await asyncio.to_thread(self._query_capabilities_sync)
                ok = caps is not None
            except Exception as error:
                logger.warning("LiNeP trunk health check failed: %s", error)
                ok = False
            self._health_ok, self._health_checked_at = ok, time.monotonic()
            return ok
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
        if self._capabilities_cache:
            return self._capabilities_cache
        # A failed query is retried after 30 s instead of being cached for the
        # process lifetime: a cluster trunk can be briefly down, the old local
        # server could only be down or too old.
        if self._capabilities_cache is False and time.monotonic() - self._capabilities_failed_at < 30.0:
            return None
        try:
            caps = await asyncio.to_thread(self._query_capabilities_sync)
        except Exception:
            caps = None
        if caps is None:
            self._capabilities_cache = False
            self._capabilities_failed_at = time.monotonic()
        else:
            self._capabilities_cache = caps
        return caps

    def _query_capabilities_sync(self):
        client = self._connect_sync(5.0)
        try:
            return client.query_capabilities()
        finally:
            client.close()

    def chat_sync(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 2000,
        temperature: Optional[float] = None,
    ) -> str:
        """Blocking structured chat for the sync call sites (OllamaClient.chat).

        `model` is a concrete model or "task:<name>"; messages go over the wire
        as {"messages": [...]} (structured, role-separated, no flattening).
        Raises LinepUnavailableError on any failure: the caller decides about a
        fallback. Must not be called from inside the event loop's thread
        without to_thread - same as the requests call it replaces.
        """
        import json

        _client_cls, EventType, RuntimeProfile, RequestEnvelope, StreamIdentity = _import_linep()
        request = RequestEnvelope(
            stream=StreamIdentity(
                request_id=next(_request_ids), execution_id=next(_request_ids), output_id=0
            ),
            profile=RuntimeProfile.CHAT,
            model_id=model,
            payload=json.dumps({"messages": messages}),
            max_tokens=max_tokens,
        )
        if temperature is not None:
            request.temperature = float(temperature)
        parts: list[str] = []
        try:
            client = self._connect_sync(self._timeout)
            try:
                for event in client.execute_stream(request):
                    if event.event_type == EventType.CONTENT_DELTA and event.payload:
                        parts.append(event.payload)
                    elif event.event_type == EventType.FAILED:
                        message = (
                            event.error.message
                            if event.error and event.error.message
                            else "LiNeP runtime reported a failure"
                        )
                        raise LinepUnavailableError(message)
            finally:
                client.close()
        except LinepUnavailableError:
            raise
        except Exception as error:
            raise LinepUnavailableError(f"LiNeP transport failed: {error}") from error
        text = "".join(parts).strip()
        if not text:
            raise LinepUnavailableError("LiNeP runtime returned an empty response")
        return text

    async def generate_stream(
        self,
        prompt: str,
        model: str,
        num_predict: int = 2000,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[tuple[str, str]]:
        """Streams (kind, payload) tuples from a LiNeP-routed GENERATE call,
        kind being "content", "thinking", or "tool_call" (see module
        docstring for the native REASONING_DELTA/TOOL_CALL event mapping).

        Sync LiNePClient socket calls run on a worker thread; results cross
        back to this coroutine via an asyncio.Queue fed through
        call_soon_threadsafe, same bridge pattern as the mw-dresden original.
        """
        _client_cls, EventType, RuntimeProfile, RequestEnvelope, StreamIdentity = _import_linep()

        request = RequestEnvelope(
            stream=StreamIdentity(
                request_id=next(_request_ids), execution_id=next(_request_ids), output_id=0
            ),
            profile=RuntimeProfile.CHAT,
            model_id=model,
            payload=prompt,
            max_tokens=num_predict,
        )
        if temperature is not None:
            request.temperature = float(temperature)

        timeout = self._timeout
        loop = asyncio.get_running_loop()
        queue: "asyncio.Queue[tuple[Optional[tuple[str, str]], Optional[Exception]]]" = asyncio.Queue()

        def _worker():
            try:
                client = self._connect_sync(timeout)
                try:
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
                finally:
                    client.close()
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
    if settings.linep_trunk_host:
        return LinepChatProvider(
            host=settings.linep_trunk_host,
            port=settings.linep_trunk_port,
            timeout=settings.linep_timeout_seconds,
            control_port=settings.linep_trunk_control_port,
            key_file=settings.linep_sl1_key_file,
        )
    return LinepChatProvider(
        host=settings.linep_host,
        port=settings.linep_port,
        timeout=settings.linep_timeout_seconds,
    )
