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

from services.agents.agent_registry import AgentRegistry
from services.agents.base_agent import BaseAgent
from services.agents.code_agent import CodeAgent


class TestAgentsSubsystem(unittest.TestCase):

    def test_agent_registry(self):
        agents = AgentRegistry.list_agents()
        self.assertGreaterEqual(len(agents), 2)
        
        agent_ids = [a["id"] for a in agents]
        self.assertIn("code", agent_ids)
        self.assertIn("research", agent_ids)

        # CodeAgent instanziieren
        code_agent = AgentRegistry.create_agent("code", user_id=1, session_id=2)
        self.assertIsInstance(code_agent, CodeAgent)
        self.assertIn("view_file", code_agent.tools)
        self.assertIn("replace_chunk", code_agent.tools)

    def test_react_response_parsing(self):
        agent = BaseAgent(
            name="TestAgent",
            role_description="Tester",
            system_prompt="Du bist ein Test-Agent"
        )

        # 1. Tool Call Parsing
        sample_tool_output = """
Gedanke: Ich muss die Datei main.py ansehen, um die Zeilen zu prüfen.
<tool_call>
{
  "name": "view_file",
  "arguments": {
    "filename": "main.py",
    "start_line": 1,
    "end_line": 20
  }
}
</tool_call>
"""
        parsed = agent._parse_llm_response(sample_tool_output)
        self.assertEqual(parsed["type"], "tool_call")
        self.assertIn("Ich muss die Datei main.py ansehen", parsed["thought"])
        self.assertEqual(parsed["tool_name"], "view_file")
        self.assertEqual(parsed["arguments"]["filename"], "main.py")

        # 2. Final Answer Parsing
        sample_final_output = """
Gedanke: Der Bug wurde behoben und die Tests sind erfolgreich durchgelaufen.
<final_answer>
Die Funktion `calculate_total` wurde in `utils.py` korrigiert.
</final_answer>
"""
        parsed_final = agent._parse_llm_response(sample_final_output)
        self.assertEqual(parsed_final["type"], "final_answer")
        self.assertIn("Der Bug wurde behoben", parsed_final["thought"])
        self.assertIn("Funktion `calculate_total`", parsed_final["answer"])

    def test_tool_execution(self):
        agent = BaseAgent(name="TestAgent", role_description="Tester", system_prompt="")
        
        def mock_add(a: int, b: int):
            return a + b
        
        agent.register_tool(
            name="add",
            description="Addiert zwei Zahlen",
            parameters={"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}},
            handler=mock_add
        )

        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(agent.execute_tool("add", {"a": 15, "b": 27}))
        loop.close()
        self.assertEqual(res, 42)


if __name__ == "__main__":
    unittest.main()
