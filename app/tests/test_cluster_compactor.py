"""Compaction uses the cluster or deterministic heuristics, never local HTTP."""
import asyncio
from copy import deepcopy
from unittest.mock import Mock, patch

import pytest

from core.config import settings
from services.context.structured_compactor import (
    COMPACTOR_SYSTEM_PROMPT, StructuredCompactor, StructuredSessionState,
)
from services.linep_provider import LinepUnavailableError


TURNS = [{"role": "user", "content": "Wir nutzen LiNeP. Bitte nur lokale Daten verwenden."}]


@pytest.fixture
def state():
    return StructuredSessionState(
        decisions=["Bestehende Entscheidung"], user_constraints=["Keine Änderungen"],
        open_tasks=["Offene Aufgabe"], last_compacted_turn_index=12,
    )


@pytest.fixture(autouse=True)
def no_direct_http():
    with patch("httpx.AsyncClient") as http, patch("requests.post") as post:
        yield
        http.assert_not_called()
        post.assert_not_called()


@pytest.fixture
def cluster():
    provider = Mock()
    with patch.object(settings, "linep_enabled", True), \
         patch.object(settings, "linep_trunk_host", "unused"), \
         patch("services.linep_provider.get_linep_provider", return_value=provider):
        yield provider


@pytest.mark.asyncio
async def test_cluster_merges_facts_without_mutating_existing_state(cluster, state):
    before = deepcopy(state.to_dict())
    cluster.chat_sync.return_value = '```json\n{"decisions":["Neue Entscheidung"],"open_tasks":["Testen"]}\n```'
    result = await StructuredCompactor.compact_via_llm(TURNS, state)
    assert result.decisions == ["Bestehende Entscheidung", "Neue Entscheidung"]
    assert result.open_tasks == ["Offene Aufgabe", "Testen"]
    assert result.user_constraints == state.user_constraints
    assert result.last_compacted_turn_index == 12
    assert state.to_dict() == before
    args = cluster.chat_sync.call_args.args
    assert args[0] == "task:json"
    assert args[1] == [{"role": "system", "content": COMPACTOR_SYSTEM_PROMPT},
                       {"role": "user", "content": "user: " + TURNS[0]["content"]}]
    assert args[2:] == (2000, 0.1)


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["task:tool", "task:custom-json", "gpt-oss:120b-cloud", None])
async def test_chat_model_cannot_override_json_task(cluster, state, model):
    cluster.chat_sync.return_value = '{}'
    await StructuredCompactor.compact_via_llm(TURNS, state, model=model)
    assert cluster.chat_sync.call_args.args[0] == "task:json"


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [LinepUnavailableError("offline"), TimeoutError("timeout")])
async def test_cluster_failure_only_uses_heuristics(cluster, state, error):
    before = deepcopy(state.to_dict())
    cluster.chat_sync.side_effect = error
    result = await StructuredCompactor.compact_via_llm(TURNS, state)
    assert result == StructuredCompactor.extract_heuristic_facts(TURNS, state)
    assert len(result.decisions) > len(state.decisions)
    assert state.to_dict() == before
    cluster.chat_sync.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled,host", [(False, "unused"), (True, "")])
async def test_unconfigured_cluster_only_uses_heuristics(state, enabled, host):
    with patch.object(settings, "linep_enabled", enabled), \
         patch.object(settings, "linep_trunk_host", host), \
         patch("services.linep_provider.get_linep_provider") as provider:
        result = await StructuredCompactor.compact_via_llm(TURNS, state)
    provider.assert_not_called()
    assert result == StructuredCompactor.extract_heuristic_facts(TURNS, state)


@pytest.mark.asyncio
@pytest.mark.parametrize("response", ["", "kein JSON", '{"decisions":',
    '{"decisions":"nicht als Liste"}', '{"decisions":[42]}'])
async def test_invalid_response_falls_back_without_state_damage(cluster, state, response):
    before = deepcopy(state.to_dict())
    cluster.chat_sync.return_value = response
    result = await StructuredCompactor.compact_via_llm(TURNS, state)
    assert result == StructuredCompactor.extract_heuristic_facts(TURNS, state)
    assert state.to_dict() == before


@pytest.mark.asyncio
async def test_cancellation_is_not_converted_into_heuristics(cluster, state):
    cluster.chat_sync.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await StructuredCompactor.compact_via_llm(TURNS, state)
