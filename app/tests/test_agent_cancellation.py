import os
import sys
import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

if "redis" not in sys.modules:
    try:
        import redis
    except ImportError:
        sys.modules["redis"] = MagicMock()

from services.agents.base_agent import BaseAgent


class DummyTestAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="dummy_agent",
            role_description="Agent for cancellation testing",
            system_prompt="Du bist ein Testagent.",
            model="qwen2.5:7b",
            max_steps=5
        )


class TestAgentCancellation(unittest.IsolatedAsyncioTestCase):

    async def test_react_loop_cancellation_mid_execution(self):
        agent = DummyTestAgent()
        
        # Tool registrieren
        tool_called = False
        def dummy_action(param: str):
            nonlocal tool_called
            tool_called = True
            return {"status": "ok"}

        agent.register_tool(
            "dummy_action",
            "Führt Dummy-Aktion aus",
            {"type": "object", "properties": {"param": {"type": "string"}}},
            dummy_action
        )

        emitted_events = []
        async def callback(event):
            emitted_events.append(event)

        # Simuliere: Cancellation wird nach Schritt 1 aktiv
        cancel_state = {"cancelled": False}
        async def is_cancelled():
            return cancel_state["cancelled"]

        # Mock LLM Response: Ruft ein Tool auf
        async def mock_call_llm(messages, tools=None):
            # Nach dem ersten LLM-Call wird die Cancellation aktiv
            cancel_state["cancelled"] = True
            return {
                "content": 'Gedanke: Führe Aktion aus\n<tool_call>{"name": "dummy_action", "arguments": {"param": "x"}}</tool_call>'
            }

        agent.call_llm = mock_call_llm

        with patch("services.agents.base_agent.model_supports_tools", new=AsyncMock(return_value=False)):
            result = await agent.run(
                task="Test cancellation",
                callback=callback,
                is_cancelled=is_cancelled
            )

        self.assertTrue(result.get("cancelled"))
        self.assertFalse(result.get("success"))
        self.assertIn("abgebrochen", result.get("error", ""))
        self.assertFalse(tool_called, "Tool must NOT be executed after cancellation was requested!")

        event_names = [e["event"] for e in emitted_events]
        self.assertIn("cancelled", event_names)


if __name__ == "__main__":
    unittest.main()
