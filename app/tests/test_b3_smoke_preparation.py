"""Validate the live-check harness without contacting a cluster."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from scripts.check_b3_cluster import MARKER, check, main


def test_default_is_plan_only(capsys):
    with patch("sys.argv", ["check_b3_cluster.py"]), \
         patch("socket.socket") as network:
        assert main() == 0
    network.assert_not_called()
    assert "PLAN ONLY" in capsys.readouterr().out


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", ["b3_echo", "unexpected_tool"])
async def test_smoke_validates_tool_roundtrip_without_dispatch(tool_name):
    provider = Mock()
    provider._query_capabilities_sync.return_value = SimpleNamespace(
        descriptor=SimpleNamespace(supported_models=["task:fast", "task:tool", "task:json"]))
    provider.chat_message_sync.side_effect = [
        {"content": MARKER, "tool_calls": []},
        {"content": "", "tool_calls": [{"id": "test-call", "function": {
            "name": tool_name, "arguments": {"marker": MARKER}}}]},
        {"content": MARKER, "tool_calls": []},
    ]

    stream_requests = []

    async def stream(*args, **kwargs):
        stream_requests.append(args)
        yield "thinking", "not content"
        yield "content", MARKER

    provider.chat_stream = stream
    provider.chat_sync.return_value = '{"decisions":["Use LiNeP"],"open_tasks":["Check B3"]}'
    if tool_name != "b3_echo":
        with pytest.raises(AssertionError, match="Unexpected tool name"):
            await check(provider)
        assert provider.chat_message_sync.call_count == 2
        provider.chat_sync.assert_not_called()
    else:
        await check(provider)
        messages = provider.chat_message_sync.call_args.args[1]
        assert messages[-1] == {"role": "tool", "content": MARKER, "tool_call_id": "test-call"}
        assert [call.args[0] for call in provider.chat_message_sync.call_args_list] == [
            "task:fast", "task:tool", "task:tool"]
        assert all(call.args[2] >= 512 for call in provider.chat_message_sync.call_args_list)
        assert stream_requests[0][0] == "task:fast"
        assert stream_requests[0][2] >= 512
        assert provider.chat_sync.call_args.args[2] >= 2048
