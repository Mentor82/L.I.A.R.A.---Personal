"""SSE regressions through the real guest and authenticated generators."""
from copy import deepcopy
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tests import test_chat_stream_e2e as stream_fixtures
from api.routers import chat_streaming as router
from services.chat_stream.generator_stage import stream_ollama_response
from services.linep_provider import LinepUnavailableError


def decode(lines):
    return [json.loads(line[6:]) for line in lines if line.startswith("data: ")]


@pytest.fixture
def stream_environment():
    fixture = stream_fixtures.TestChatStreamE2E()
    fixture.setUp()
    try:
        with patch("services.chat_stream.generator_stage.cluster_configured", return_value=True), \
             patch("services.chat_stream.generator_stage.model_supports_tools", new_callable=AsyncMock) as caps, \
             patch("api.routers.chat_streaming.get_model_num_predict", new_callable=AsyncMock) as tokens, \
             patch("api.routers.chat_streaming.httpx.AsyncClient") as local:
            yield fixture
            caps.assert_not_awaited()
            tokens.assert_not_awaited()
            local.assert_not_called()
    finally:
        fixture.tearDown()


@pytest.mark.asyncio
async def test_authenticated_structured_tool_roundtrip_sse(stream_environment):
    requests = []
    call = {"id": "lookup-1", "function": {"name": "web_search", "arguments": {"query": "test"}}}

    async def stream(model, messages, max_tokens, temperature, tools=None):
        requests.append(deepcopy((model, messages, temperature, tools)))
        if len(requests) == 1:
            yield "thinking", "Prüfen"
            yield "tool_call", json.dumps(call)
        else:
            yield "content", "Antwort: geprüft."

    provider = MagicMock()
    provider.chat_stream = stream
    executor = MagicMock()
    executor.execute = AsyncMock(return_value={"success": True, "result": {"text": "gefunden"}})
    with patch("services.chat_stream.generator_stage.get_linep_provider", return_value=provider), \
         patch("services.chat_stream.generator_stage.get_tool_executor", return_value=executor):
        events = decode([line async for line in stream_ollama_response(
            "Frage", model=None, temperature=0.3, user_id=1,
            session_lock=stream_environment.mock_lock)])
    assert len(requests) == 2
    assert requests[0][0] == "task:tool"
    assert requests[0][1][0]["role"] == "system"
    assert requests[0][2] == 0.3
    assert requests[0][3]
    assert requests[1][1][-2]["tool_calls"] == [call]
    assert requests[1][1][-1]["role"] == "tool"
    assert requests[1][1][-1]["tool_call_id"] == "lookup-1"
    assert "gefunden" in requests[1][1][-1]["content"]
    assert sum(e["type"] == "done" for e in events) == 1
    assert any(e["type"] == "agent_steps" for e in events)
    assert any(e["type"] == "thinking" for e in events)
    content = "".join(e.get("text", "") for e in events if e["type"] == "content")
    assert content == "Antwort: geprüft."
    assert "tool_call" not in content


@pytest.mark.asyncio
async def test_authenticated_cluster_failure_is_error_without_done(stream_environment):
    async def stream(*args, **kwargs):
        yield "content", "Teilantwort"
        raise LinepUnavailableError("private diagnostic")

    provider = MagicMock()
    provider.chat_stream = stream
    with patch("services.chat_stream.generator_stage.get_linep_provider", return_value=provider):
        events = decode([line async for line in stream_ollama_response(
            "Frage", model="task:fast", session_lock=stream_environment.mock_lock)])
    assert any(e["type"] == "error" for e in events)
    assert not any(e["type"] == "done" for e in events)
    assert "private diagnostic" not in str(events)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, "transport", "tool"])
async def test_guest_cluster_sse(failure):
    requests = []

    async def stream(*args, **kwargs):
        requests.append(deepcopy((args, kwargs)))
        yield "thinking", "Überlegen"
        if failure == "transport":
            raise LinepUnavailableError("private diagnostic")
        if failure == "tool":
            yield "tool_call", json.dumps({"function": {"name": "forbidden", "arguments": {}}})
        else:
            yield "content", "Hallo!"

    provider = MagicMock()
    provider.chat_stream = stream
    embedding = MagicMock()
    embedding.detect_intent.return_value = "conversation"
    with patch.object(router, "cluster_configured", return_value=True), \
         patch.object(router, "get_linep_provider", return_value=provider), \
         patch.object(router, "get_embedding_service", return_value=embedding), \
         patch.object(router.requests, "post") as local:
        events = decode([line async for line in router.stream_guest_response("Hallo")])
    local.assert_not_called()
    args, kwargs = requests[0]
    assert args[0] == "task:fast"
    assert [m["role"] for m in args[1]] == ["system", "user"]
    assert args[1][-1]["content"] == "Hallo"
    assert args[2:] == (300, 0.7)
    assert kwargs["tools"] is None
    assert sum(e["type"] == "done" for e in events) == (0 if failure else 1)
    assert sum(e["type"] == "error" for e in events) == (1 if failure else 0)
    assert "private diagnostic" not in str(events)


@pytest.mark.asyncio
async def test_guest_local_mode_still_streams():
    response = MagicMock()
    response.iter_lines.return_value = [json.dumps({"response": "Lokal"}), json.dumps({"done": True})]
    embedding = MagicMock()
    embedding.detect_intent.return_value = "conversation"
    with patch.object(router, "cluster_configured", return_value=False), \
         patch.object(router, "get_embedding_service", return_value=embedding), \
         patch.object(router.requests, "post", return_value=response) as local:
        events = decode([line async for line in router.stream_guest_response("Hallo")])
    assert local.call_args.kwargs["json"]["model"] == "llama3.2:1b"
    assert sum(e["type"] == "done" for e in events) == 1
    assert "".join(e.get("text", "") for e in events if e["type"] == "content") == "Lokal"


@pytest.mark.asyncio
async def test_authenticated_disconnect_closes_stream_and_releases_lock(stream_environment):
    closed = []

    async def stream(*args, **kwargs):
        try:
            yield "thinking", "start"
            yield "content", "never consumed"
        finally:
            closed.append(True)

    provider = MagicMock()
    provider.chat_stream = stream
    with patch("services.chat_stream.generator_stage.get_linep_provider", return_value=provider):
        generator = stream_ollama_response("Frage", session_lock=stream_environment.mock_lock)
        async for line in generator:
            if '"thinking"' in line:
                break
        await generator.aclose()
        # Nested generators may be finalized by the event loop on its next turn.
        import asyncio
        for _ in range(3):
            await asyncio.sleep(0)
    assert closed
    stream_environment.mock_lock.release.assert_called_once()


@pytest.mark.parametrize("model,expected", [(None, "task:fast"), ("chosen-model", "chosen-model")])
def test_nonstream_chat_routes_structured_roles_and_explicit_models(model, expected):
    from liara_engine.nlp.ollama_client import OllamaClient
    provider = MagicMock()
    provider.chat_sync.return_value = "Antwort"
    with patch.object(OllamaClient, "_cluster_enabled", return_value=True), \
         patch("services.linep_provider.get_linep_provider", return_value=provider), \
         patch("requests.post") as local:
        assert OllamaClient().chat("Frage", model=model, system_prompt="System") == "Antwort"
    local.assert_not_called()
    args = provider.chat_sync.call_args.args
    assert args[0] == expected
    assert args[1] == [{"role": "system", "content": "System"}, {"role": "user", "content": "Frage"}]


def test_nonstream_cluster_failure_has_no_http_fallback():
    from liara_engine.nlp.ollama_client import OllamaClient
    provider = MagicMock()
    provider.chat_sync.side_effect = LinepUnavailableError("unavailable")
    with patch.object(OllamaClient, "_cluster_enabled", return_value=True), \
         patch("services.linep_provider.get_linep_provider", return_value=provider), \
         patch("requests.post") as local:
        with pytest.raises(LinepUnavailableError):
            OllamaClient().chat("Frage")
    local.assert_not_called()
