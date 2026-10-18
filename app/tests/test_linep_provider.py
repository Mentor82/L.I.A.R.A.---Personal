"""Cluster CHAT contract tests, with real envelopes and a fake transport."""
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("linep", reason="optional LiNeP SDK required for envelope contract tests")
from linep.v0_2.constants import EventType, RuntimeProfile

from services.linep_provider import LinepChatProvider, LinepUnavailableError


CALL = {"id": "call-1", "function": {"name": "weather", "arguments": {"city": "Dresden"}}}
MESSAGES = [
    {"role": "system", "content": "Antworte präzise."},
    {"role": "user", "content": "Wetter?"},
    {"role": "assistant", "content": "", "tool_calls": [CALL]},
    {"role": "tool", "tool_call_id": "call-1", "content": "Sonnig"},
]
TOOLS = [{"type": "function", "function": {"name": "weather", "parameters": {
    "type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}]


def event(kind, payload="", error=None):
    return SimpleNamespace(event_type=kind, payload=payload, error=error)


class Transport:
    def __init__(self, events):
        self.events = events
        self.requests = []
        self.closed = False

    def execute_stream(self, request):
        self.requests.append(request)
        yield from self.events

    def close(self):
        self.closed = True


def provider_with(events):
    return LinepChatProvider("unused", 9000), Transport(events)


def test_structured_message_and_wire_contract():
    second = {"function": {"name": "clock", "arguments": {}}}
    provider, transport = provider_with([
        event(EventType.ACCEPTED), event(EventType.REASONING_DELTA, "Überlegen"),
        event(EventType.CONTENT_DELTA, "Hallo "), event(EventType.TOOL_CALL, json.dumps(CALL)),
        event(EventType.CONTENT_DELTA, "Mirko"), event(EventType.TOOL_CALL, json.dumps(second)),
        event(EventType.COMPLETED), event(EventType.CONTENT_DELTA, "late"),
    ])
    with patch.object(provider, "_connect_sync", return_value=transport):
        result = provider.chat_message_sync("task:tool", MESSAGES, 123, 0.0, TOOLS)
    assert result == {"role": "assistant", "content": "Hallo Mirko", "thinking": "Überlegen",
                      "tool_calls": [CALL, second]}
    request, = transport.requests
    assert request.profile == RuntimeProfile.CHAT
    assert request.model_id == "task:tool"
    assert request.max_tokens == 123
    assert request.temperature == 0.0
    assert json.loads(request.payload) == {"messages": MESSAGES, "tools": TOOLS}
    assert transport.closed


def test_tool_only_reply_is_valid():
    provider, transport = provider_with([
        event(EventType.TOOL_CALL, json.dumps(CALL)), event(EventType.COMPLETED)])
    with patch.object(provider, "_connect_sync", return_value=transport):
        assert provider.chat_message_sync("task:tool", MESSAGES)["tool_calls"] == [CALL]
    assert transport.closed


def test_empty_completion_is_not_an_answer():
    provider, transport = provider_with([event(EventType.COMPLETED)])
    with patch.object(provider, "_connect_sync", return_value=transport):
        with pytest.raises(LinepUnavailableError, match="empty response"):
            provider.chat_message_sync("task:tool", MESSAGES)
    assert transport.closed


def test_legacy_text_interface_preserves_contract():
    provider, transport = provider_with([
        event(EventType.CONTENT_DELTA, " Hallo "), event(EventType.COMPLETED)])
    with patch.object(provider, "_connect_sync", return_value=transport):
        assert provider.chat_sync("task:fast", MESSAGES) == "Hallo"
    assert "tools" not in json.loads(transport.requests[0].payload)


@pytest.mark.parametrize("terminal", [EventType.FAILED, EventType.CANCELLED, EventType.ERROR, None])
def test_partial_response_is_not_success(terminal):
    events = [event(EventType.CONTENT_DELTA, "partial")]
    if terminal is not None:
        events.append(event(terminal, error=SimpleNamespace(message="stopped")))
    provider, transport = provider_with(events)
    with patch.object(provider, "_connect_sync", return_value=transport):
        with pytest.raises(LinepUnavailableError):
            provider.chat_message_sync("task:tool", MESSAGES)
    assert transport.closed


@pytest.mark.parametrize("payload", ["{", "[]", "{}", '{"function":{"name":"x","arguments":"{}"}}'])
def test_malformed_tool_calls_fail_closed(payload):
    provider, transport = provider_with([
        event(EventType.TOOL_CALL, payload), event(EventType.COMPLETED)])
    with patch.object(provider, "_connect_sync", return_value=transport):
        with pytest.raises(LinepUnavailableError):
            provider.chat_message_sync("task:tool", MESSAGES)
    assert transport.closed


@pytest.mark.asyncio
async def test_structured_stream_keeps_event_boundaries():
    provider, transport = provider_with([
        event(EventType.REASONING_DELTA, "thinking"), event(EventType.CONTENT_DELTA, "text"),
        event(EventType.TOOL_CALL, json.dumps(CALL)), event(EventType.COMPLETED)])
    with patch.object(provider, "_connect_sync", return_value=transport):
        result = [item async for item in provider.chat_stream("task:tool", MESSAGES, 88, 0.2, TOOLS)]
    assert result == [("thinking", "thinking"), ("content", "text"), ("tool_call", json.dumps(CALL))]
    assert json.loads(transport.requests[0].payload) == {"messages": MESSAGES, "tools": TOOLS}
    assert transport.requests[0].temperature == 0.2
    assert transport.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal", [EventType.FAILED, EventType.CANCELLED, EventType.ERROR, None])
async def test_stream_reports_failure_or_missing_completion(terminal):
    provider, transport = provider_with([] if terminal is None else [event(terminal)])
    with patch.object(provider, "_connect_sync", return_value=transport):
        with pytest.raises(LinepUnavailableError):
            _ = [item async for item in provider.chat_stream("task:tool", MESSAGES)]
    assert transport.closed


@pytest.mark.asyncio
async def test_stream_rejects_invalid_tool_payload():
    provider, transport = provider_with([event(EventType.TOOL_CALL, "")])
    with patch.object(provider, "_connect_sync", return_value=transport):
        with pytest.raises(LinepUnavailableError, match="tool-call"):
            _ = [item async for item in provider.chat_stream("task:tool", MESSAGES)]
    assert transport.closed
