"""Exercise application entry points affected by Personal's task-only key."""
from unittest.mock import AsyncMock, Mock, patch

import pytest

from tests import test_chat_stream_e2e as stream_fixtures  # existing optional-service test doubles
from services.agents import research_agent, code_agent
from services.agents.agent_registry import AgentRegistry
from services.chat_stream.generator_stage import _run_background_context_compaction
from services.context.structured_compactor import StructuredSessionState


@pytest.mark.asyncio
@pytest.mark.parametrize("cluster", [True, False])
@pytest.mark.parametrize("kind", ["research", "code"])
async def test_delegation_selects_task_and_preserves_result(cluster, kind):
    module = research_agent if kind == "research" else code_agent
    cls = "ResearchAgent" if kind == "research" else "CodeAgent"
    agent = Mock(system_prompt="system", run=AsyncMock(return_value={"success": True, "answer": "done"}))
    with patch.object(module, "cluster_configured", return_value=cluster), \
         patch.object(module, cls, return_value=agent) as constructor, \
         patch("services.session_workspace.list_proposals", return_value=[]):
        if kind == "research":
            result = await module.run_delegated_research("question")
        else:
            result = await module.run_delegated_code_task("question", user_id=1, session_id=2)
    assert constructor.call_args.kwargs["model"] == ("task:tool" if cluster else "gpt-oss:120b-cloud")
    assert result == {"answer": "done"}
    agent.run.assert_awaited_once()


def test_agent_list_advertises_effective_cluster_default():
    with patch("services.cluster_info.cluster_configured", return_value=True):
        assert all(a["default_model"] == "task:tool" for a in AgentRegistry.list_agents())


@pytest.mark.asyncio
async def test_background_compaction_does_not_forward_chat_model():
    state = StructuredSessionState()
    turns = [{"role": "user", "content": "remember"}]
    with patch("services.chat_stream.generator_stage.load_structured_session_state", return_value=state), \
         patch("services.chat_stream.generator_stage.persist_structured_session_state") as persist, \
         patch("services.context.structured_compactor.StructuredCompactor.compact_via_llm", new_callable=AsyncMock, return_value=state) as compact:
        await _run_background_context_compaction(1, turns, state, model="task:tool")
    compact.assert_awaited_once_with(turns, state)
    persist.assert_called_once_with(1, state)


@pytest.mark.parametrize("info", [None, {"available": False}, {
    "available": True, "tasks": ["task:tool", "task:private"], "models": ["gpt-oss:120b-cloud"]}])
def test_model_list_is_task_only_even_when_cluster_unavailable(info):
    from api.routers.chat import get_models

    with patch("services.cluster_info.cluster_configured", return_value=True), \
         patch("services.cluster_info.get_cluster_info", return_value=info), \
         patch("api.routers.chat.parse_ollama_list") as local:
        result = get_models(current_user=Mock())
    local.assert_not_called()
    assert result["models"]
    assert all(m["name"].startswith("task:") for m in result["models"])
