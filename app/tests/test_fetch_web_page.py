"""
Tests for Direct Web Page Fetch Tool (Issue #28)
================================================
Verifies fetch_web_page in ToolRegistry, ToolExecutor, and ResearchAgent.
"""

import unittest
from unittest.mock import patch, MagicMock

from services.tool_registry import get_tool_registry, ToolCategory
from services.tool_executor import ToolExecutor
from services.tool_parser import ToolCall
from services.agents.research_agent import ResearchAgent


class TestFetchWebPage(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.registry = get_tool_registry()
        self.executor = ToolExecutor()

    def test_fetch_web_page_registered(self):
        """Verify fetch_web_page is registered in ToolRegistry."""
        tool = self.registry.get_tool("fetch_web_page")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.category, ToolCategory.INFORMATION)
        self.assertEqual(tool.privacy_level, "low")
        self.assertIn("url", [p.name for p in tool.parameters])

    def test_get_tools_for_ollama_includes_fetch_web_page(self):
        """Verify Ollama native schema exports fetch_web_page."""
        tools = self.registry.get_tools_for_ollama()
        names = [t["function"]["name"] for t in tools]
        self.assertIn("fetch_web_page", names)

    @patch("services.web_safety.proxy_sandbox.ProxySandbox.fetch_safe")
    async def test_execute_fetch_web_page_success(self, mock_fetch):
        """Test successful page fetch execution."""
        mock_fetch.return_value = {
            "title": "Python 3.14 Release Notes",
            "description": "What's new in Python 3.14",
            "text_content": "Python 3.14 includes major performance enhancements, JIT compiler improvements and tail-call optimizations."
        }

        call = ToolCall(
            tool_name="fetch_web_page",
            parameters={"url": "https://docs.python.org/3/whatsnew/3.14.html"},
            raw_text='<tool_call>{"tool": "fetch_web_page"}</tool_call>'
        )

        res = await self.executor.execute(call, user_id=1)
        self.assertTrue(res.get("success"))
        result_data = res.get("result", {})
        self.assertEqual(result_data.get("title"), "Python 3.14 Release Notes")
        self.assertIn("Python 3.14 includes", result_data.get("text"))

    @patch("services.web_safety.proxy_sandbox.ProxySandbox.fetch_safe")
    async def test_execute_fetch_web_page_error(self, mock_fetch):
        """Test handling of unreachable or blocked URLs."""
        mock_fetch.return_value = {
            "error": "SSRF Blocked: Target resolves to private IP"
        }

        call = ToolCall(
            tool_name="fetch_web_page",
            parameters={"url": "http://127.0.0.1:8000/internal"},
            raw_text='<tool_call>{"tool": "fetch_web_page"}</tool_call>'
        )

        res = await self.executor.execute(call, user_id=1)
        self.assertFalse(res.get("success"))
        self.assertIn("SSRF Blocked", res.get("error", ""))

    def test_research_agent_includes_fetch_web_page(self):
        """Verify ResearchAgent has fetch_web_page registered."""
        agent = ResearchAgent()
        self.assertIn("fetch_web_page", agent.tools)

    @patch("requests.Session.get")
    def test_proxy_sandbox_json_parsing(self, mock_get):
        """Verify ProxySandbox handles application/json responses."""
        from services.web_safety.proxy_sandbox import ProxySandbox
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://example.com/api/health"
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.is_redirect = False
        mock_resp.iter_content.return_value = [b'{"status": "healthy", "uptime": "48h"}']
        mock_get.return_value = mock_resp

        sandbox = ProxySandbox()
        with patch.object(sandbox, "_check_target_is_public"):
            result = sandbox.fetch_safe("https://example.com/api/health")

        self.assertIsNone(result.get("error"))
        self.assertIn("healthy", result.get("text_content", ""))
        self.assertIn("JSON", result.get("title", ""))


if __name__ == "__main__":
    unittest.main()
