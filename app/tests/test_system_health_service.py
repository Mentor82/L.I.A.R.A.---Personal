"""
Unit tests for System Health & Metrics Service
=============================================
Tests metrics gathering, hardware temperatures, service checks, and tool registration.
"""

import unittest
from unittest.mock import patch, MagicMock

from services.system_health_service import (
    get_system_uptime,
    get_hardware_temperatures,
    get_system_metrics,
    check_services_status,
    get_full_system_health,
)
from services.tool_registry import get_tool_registry, ToolCategory
from services.tool_executor import ToolExecutor
from services.tool_parser import ToolCall


class TestSystemHealthService(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.registry = get_tool_registry()
        self.executor = ToolExecutor()

    def test_tool_registration(self):
        """Verify get_system_health is registered in ToolRegistry."""
        tool = self.registry.get_tool("get_system_health")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.category, ToolCategory.INFORMATION)
        self.assertEqual(tool.privacy_level, "low")
        self.assertFalse(tool.requires_consent)

    def test_get_system_uptime(self):
        """Test uptime formatting."""
        uptime = get_system_uptime()
        self.assertIn("uptime_seconds", uptime)
        self.assertIn("formatted", uptime)
        self.assertIsInstance(uptime["uptime_seconds"], int)

    def test_get_system_metrics(self):
        """Test system resource metrics."""
        metrics = get_system_metrics()
        self.assertIn("cpu", metrics)
        self.assertIn("memory", metrics)
        self.assertIn("disk", metrics)
        self.assertIn("uptime", metrics)
        self.assertIn("temperatures", metrics)

        self.assertGreaterEqual(metrics["cpu"]["cores"], 1)
        self.assertGreater(metrics["memory"]["total_gb"], 0)
        self.assertGreater(metrics["disk"]["total_gb"], 0)

    @patch("services.redis_service.get_redis_service")
    def test_check_services_status(self, mock_redis_getter):
        """Test database and service health checks."""
        mock_redis = MagicMock()
        mock_redis.client.ping.return_value = True
        mock_redis_getter.return_value = mock_redis

        services = check_services_status()
        self.assertIn("postgresql", services)
        self.assertIn("redis", services)
        self.assertIn("neo4j", services)
        self.assertIn("ollama", services)

    def test_get_full_system_health_scopes(self):
        """Test summary, resources, services, and temperatures scopes."""
        summary = get_full_system_health(scope="summary")
        self.assertIn("status", summary)
        self.assertIn("resources", summary)
        self.assertIn("services", summary)
        self.assertIn("temperatures", summary)

        resources = get_full_system_health(scope="resources")
        self.assertIn("resources", resources)
        self.assertNotIn("services", resources)

        services = get_full_system_health(scope="services")
        self.assertIn("services", services)
        self.assertNotIn("resources", services)

    async def test_tool_executor_get_system_health(self):
        """Test execution via ToolExecutor."""
        call = ToolCall(
            tool_name="get_system_health",
            parameters={"scope": "summary"},
            raw_text='<tool_call>{"tool": "get_system_health"}</tool_call>'
        )
        res = await self.executor.execute(call, user_id=1)
        self.assertTrue(res.get("success"))
        result_data = res.get("result", {})
        self.assertIn("status", result_data)
        self.assertIn("resources", result_data)


if __name__ == "__main__":
    unittest.main()
