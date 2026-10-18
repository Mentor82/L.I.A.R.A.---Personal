"""Agent Hub cluster transport and complete tool-loop regressions."""
from copy import deepcopy
from unittest.mock import AsyncMock, Mock, patch

import pytest

from services.agents.base_agent import BaseAgent
from services.agents.agent_registry import AgentRegistry
from services.linep_provider import LinepUnavailableError


def make_agent(max_steps=3):
    agent = BaseAgent("ResearchAgent", "test", "system", model="task:tool", max_steps=max_steps)
    agent.register_tool("add", "Add", {"type": "object", "properties": {
        "a": {"type": "integer"}, "b": {"type": "integer"}}}, lambda a, b: a + b)
    return agent


CALL = {"id": "call-1", "function": {"name": "add", "arguments": {"a": 2, "b": 3}}}


@pytest.fixture
def cluster():
    provider = Mock()
    with patch("services.agents.base_agent.cluster_configured", return_value=True), \
         patch("services.agents.base_agent.get_linep_provider", return_value=provider), \
         patch("services.agents.base_agent.model_supports_tools", new_callable=AsyncMock) as capabilities, \
         patch("httpx.AsyncClient") as local_http:
        yield provider
        capabilities.assert_not_awaited()
        local_http.assert_not_called()


@pytest.mark.asyncio
async def test_cluster_tool_result_then_final_answer(cluster):
    requests = []

    def reply(**kwargs):
        requests.append(deepcopy(kwargs))
        if len(requests) == 1:
            return {"role": "assistant", "content": "", "thinking": "internal", "tool_calls": [CALL]}
        return {"role": "assistant", "content": "Ergebnis: 5", "tool_calls": []}

    cluster.chat_message_sync.side_effect = reply
    agent = make_agent()
    events = []

    async def collect(event):
        events.append((event["event"], event["data"]))

    result = await agent.run("Addiere", callback=collect)
    assert result["success"] is True
    assert result["answer"] == "Ergebnis: 5"
    assert result["steps"] == 2
    assert requests[0]["model"] == "task:tool"
    assert requests[0]["temperature"] == 0.2
    assert requests[0]["tools"][0]["function"]["name"] == "add"
    assert requests[1]["messages"][-2:] == [
        {"role": "assistant", "content": "", "tool_calls": [CALL]},
        {"role": "tool", "content": "5", "tool_call_id": "call-1"},
    ]
    assert [kind for kind, _ in events].count("done") == 1
    assert "tool_call" in [kind for kind, _ in events]
    assert "tool_result" in [kind for kind, _ in events]
    assert "internal" not in str(events)


@pytest.mark.asyncio
async def test_step_limit_wrapup_uses_cluster_without_tools(cluster):
    requests = []

    def reply(**kwargs):
        requests.append(deepcopy(kwargs))
        return ({"content": "", "tool_calls": [CALL]} if len(requests) == 1
                else {"content": "Addition erledigt, weitere Aufgabe offen.", "tool_calls": []})

    cluster.chat_message_sync.side_effect = reply
    result = await make_agent(max_steps=1).run("Addiere")
    assert result["paused"] is True
    assert result["continuation_summary"] == "Addition erledigt, weitere Aufgabe offen."
    assert len(requests) == 2
    assert requests[-1]["tools"] is None
    assert requests[-1]["messages"][-2]["role"] == "tool"


@pytest.mark.asyncio
async def test_cluster_failure_does_not_fall_back(cluster):
    cluster.chat_message_sync.side_effect = LinepUnavailableError("cluster unavailable")
    result = await make_agent().run("Addiere")
    assert result["success"] is False
    assert "cluster unavailable" in result["error"]
    assert cluster.chat_message_sync.call_count == 1


@pytest.mark.asyncio
async def test_multiple_tool_calls_keep_order_and_ids(cluster):
    second = {"id": "call-2", "function": {"name": "add", "arguments": {"a": 4, "b": 5}}}
    requests = []

    def reply(**kwargs):
        requests.append(deepcopy(kwargs))
        return ({"content": "", "tool_calls": [CALL, second]} if len(requests) == 1
                else {"content": "5 und 9", "tool_calls": []})

    cluster.chat_message_sync.side_effect = reply
    result = await make_agent().run("Addiere zweimal")
    assert result["answer"] == "5 und 9"
    assert requests[1]["messages"][-2:] == [
        {"role": "tool", "content": "5", "tool_call_id": "call-1"},
        {"role": "tool", "content": "9", "tool_call_id": "call-2"},
    ]


def test_registry_uses_task_default_but_preserves_explicit_model():
    with patch("services.cluster_info.cluster_configured", return_value=True):
        assert AgentRegistry.create_agent("research").model == "task:tool"
        assert AgentRegistry.create_agent("research", model="chosen-model").model == "chosen-model"
    with patch("services.cluster_info.cluster_configured", return_value=False):
        assert AgentRegistry.create_agent("research").model == AgentRegistry._PROFILES["research"]["default_model"]


@pytest.mark.asyncio
async def test_explicit_model_is_still_routed_via_cluster(cluster):
    cluster.chat_message_sync.return_value = {"content": "OK", "tool_calls": []}
    agent = make_agent()
    agent.model = "chosen-model"
    await agent.call_llm([{"role": "user", "content": "Hallo"}])
    assert cluster.chat_message_sync.call_args.kwargs["model"] == "chosen-model"


@pytest.mark.asyncio
async def test_cancellation_between_tool_calls_stops_execution(cluster):
    cluster.chat_message_sync.return_value = {"content": "", "tool_calls": [CALL, CALL]}
    agent = make_agent()
    agent.execute_tool = AsyncMock(return_value=5)
    # Before model, before first tool, before second tool.
    cancelled = AsyncMock(side_effect=[False, False, True])
    result = await agent.run("Addiere", is_cancelled=cancelled)
    assert result["cancelled"] is True
    assert agent.execute_tool.await_count == 1
    assert cluster.chat_message_sync.call_count == 1


@pytest.mark.asyncio
async def test_local_mode_retains_http_message_contract():
    response = Mock()
    response.json.return_value = {"message": {"role": "assistant", "content": "Lokal"}}
    client = AsyncMock()
    client.post.return_value = response
    context = AsyncMock()
    context.__aenter__.return_value = client
    with patch("services.agents.base_agent.cluster_configured", return_value=False), \
         patch("services.agents.base_agent.get_linep_provider") as provider, \
         patch("httpx.AsyncClient", return_value=context):
        result = await make_agent().call_llm([{"role": "user", "content": "Hallo"}])
    assert result["content"] == "Lokal"
    provider.assert_not_called()
    assert client.post.call_args.kwargs["json"]["messages"] == [{"role": "user", "content": "Hallo"}]
