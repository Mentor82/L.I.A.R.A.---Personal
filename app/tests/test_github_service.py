"""
Tests for GitHub Search Service & Agent Integration
===================================================
Verifies GithubService, ToolRegistry, ToolExecutor, and ResearchAgent.
"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from services.github_service import GithubService, get_github_service
from services.tool_registry import get_tool_registry, ToolCategory
from services.tool_executor import ToolExecutor
from services.tool_parser import ToolCall
from services.agents.research_agent import ResearchAgent


class TestGithubService(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.service = GithubService()
        self.registry = get_tool_registry()
        self.executor = ToolExecutor()

    def test_tool_registry_has_github_tools(self):
        """Verify github_search and github_repo_readme are registered."""
        for name in ["github_search", "github_repo_readme"]:
            tool_def = self.registry.get_tool(name)
            self.assertIsNotNone(tool_def, f"Tool '{name}' missing from ToolRegistry")
            self.assertEqual(tool_def.category, ToolCategory.INFORMATION)
            self.assertEqual(tool_def.privacy_level, "low")

    def test_get_tools_for_ollama_includes_github(self):
        """Verify Ollama native tool schema export includes github_search."""
        tools = self.registry.get_tools_for_ollama()
        names = [t["function"]["name"] for t in tools]
        self.assertIn("github_search", names)
        self.assertIn("github_repo_readme", names)

    @patch("httpx.AsyncClient.get")
    async def test_search_repositories_mocked(self, mock_get):
        """Test repository search result parsing."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "total_count": 1,
            "items": [
                {
                    "full_name": "tiangolo/fastapi",
                    "name": "fastapi",
                    "owner": {"login": "tiangolo"},
                    "description": "FastAPI framework, high performance, easy to learn",
                    "stargazers_count": 75000,
                    "forks_count": 6200,
                    "language": "Python",
                    "license": {"spdx_id": "MIT"},
                    "html_url": "https://github.com/tiangolo/fastapi",
                    "updated_at": "2026-08-30T12:00:00Z",
                    "topics": ["fastapi", "python", "asyncio"]
                }
            ]
        }
        mock_get.return_value = mock_resp

        res = await self.service.search_repositories(query="fastapi", language="python", limit=3)
        self.assertTrue(res.get("success"), f"Search failed: {res}")
        self.assertEqual(res["count"], 1)
        repo = res["repositories"][0]
        self.assertEqual(repo["full_name"], "tiangolo/fastapi")
        self.assertEqual(repo["stars"], 75000)
        self.assertEqual(repo["license"], "MIT")

    @patch("httpx.AsyncClient.get")
    async def test_get_repository_readme_mocked(self, mock_get):
        """Test README fetch and truncation."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "# FastAPI\n\nFastAPI is a modern, fast web framework for building APIs."
        mock_get.return_value = mock_resp

        res = await self.service.get_repository_readme(repo="tiangolo/fastapi")
        self.assertTrue(res.get("success"), f"README fetch failed: {res}")
        self.assertEqual(res["repository"], "tiangolo/fastapi")
        self.assertIn("FastAPI is a modern", res["readme"])

    @patch("services.github_service.GithubService.search_repositories")
    async def test_tool_executor_executes_github_search(self, mock_search):
        """Test ToolExecutor routing for github_search."""
        mock_search.return_value = {
            "success": True,
            "query": "tts language:python",
            "count": 1,
            "repositories": [{"full_name": "coqui-ai/TTS", "stars": 30000}]
        }
        call = ToolCall(
            tool_name="github_search",
            parameters={"query": "tts", "language": "python"},
            raw_text='<tool_call>{"tool": "github_search"}</tool_call>'
        )
        res = await self.executor.execute(call, user_id=1)
        self.assertTrue(res.get("success"))
        self.assertEqual(res["result"]["repositories"][0]["full_name"], "coqui-ai/TTS")

    def test_research_agent_has_github_tools(self):
        """Verify ResearchAgent registers github_search and github_repo_readme."""
        agent = ResearchAgent()
        self.assertIn("github_search", agent.tools)
        self.assertIn("github_repo_readme", agent.tools)
        self.assertIn("web_search", agent.tools)
        self.assertIn("wikipedia_search", agent.tools)


if __name__ == "__main__":
    unittest.main()
