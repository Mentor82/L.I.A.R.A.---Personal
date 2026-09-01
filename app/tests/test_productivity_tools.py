"""
Comprehensive Tests for Productivity Tools & Agents (Notes, Calendar, Tasks, Memory)
===================================================================================
Verifies ToolRegistry, ToolExecutor, ProductivityAgent, and Database Persistence.
"""

import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

os.environ["LIARA_SECRET_KEY"] = "test_secret_key_for_unit_tests_1234567890abcdef"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from api.models.base_models import User, UserRole, Note, Task, CalendarEvent
from services.tool_registry import get_tool_registry, ToolCategory
from services.tool_executor import ToolExecutor
from services.tool_parser import ToolCall
from services.agents.agent_registry import AgentRegistry
from services.agents.productivity_agent import ProductivityAgent
import services.productivity_tools as pt

# Isolated in-memory SQLite database for unit tests
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


class TestProductivityToolsAndAgent(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=test_engine)

    def setUp(self):
        self.session_patcher = patch.object(pt, "SessionLocal", TestingSessionLocal)
        self.session_patcher.start()

        self.db = TestingSessionLocal()
        # Ensure test user exists
        self.user = self.db.query(User).filter(User.username == "test_productivity_user").first()
        if not self.user:
            self.user = User(
                username="test_productivity_user",
                email="prod_test@liara.local",
                hashed_password="testhash",
                full_name="Test User",
                role=UserRole.USER,
                is_active=True
            )
            self.db.add(self.user)
            self.db.commit()
            self.db.refresh(self.user)
        self.user_id = self.user.id
        self.executor = ToolExecutor()
        self.registry = get_tool_registry()

    def tearDown(self):
        # Clean up created test items
        self.db.query(Note).filter(Note.user_id == self.user_id).delete()
        self.db.query(Task).filter(Task.user_id == self.user_id).delete()
        self.db.query(CalendarEvent).filter(CalendarEvent.user_id == self.user_id).delete()
        self.db.commit()
        self.db.close()
        self.session_patcher.stop()

    def test_tool_registry_contains_productivity_tools(self):
        """Verify that all productivity tools are registered in ToolRegistry."""
        expected_tools = [
            "create_note", "list_notes",
            "create_task", "list_tasks", "update_task_status",
            "create_calendar_event", "list_calendar_events",
            "search_memory"
        ]
        for tool_name in expected_tools:
            tool_def = self.registry.get_tool(tool_name)
            self.assertIsNotNone(tool_def, f"Tool '{tool_name}' missing from registry")
            self.assertIn(tool_def.category, [ToolCategory.PRODUCTIVITY, ToolCategory.MEMORY])
            self.assertEqual(tool_def.privacy_level, "low")

    def test_get_tools_for_ollama_includes_productivity(self):
        """Verify Ollama native schema export includes productivity tools."""
        tools = self.registry.get_tools_for_ollama()
        names = [t["function"]["name"] for t in tools]
        self.assertIn("create_note", names)
        self.assertIn("create_task", names)
        self.assertIn("create_calendar_event", names)
        self.assertIn("search_memory", names)

    @patch("services.productivity_tools.store_in_4d_memory")
    async def test_execute_create_and_list_note(self, mock_store_memory):
        """Test note creation and listing via ToolExecutor."""
        call = ToolCall(
            tool_name="create_note",
            parameters={
                "title": "Projektplanung Liara",
                "content": "Architektur-Refactoring und neue Tools einführen.",
                "category": "Entwicklung",
                "tags": ["liara", "wichtig"]
            },
            raw_text='<tool_call>{"tool": "create_note"}</tool_call>'
        )
        res = await self.executor.execute(call, user_id=self.user_id)
        self.assertTrue(res.get("success"), f"Execution failed: {res}")
        note_id = res["result"]["note_id"]
        self.assertIsNotNone(note_id)

        # Verify DB
        db_note = self.db.query(Note).filter(Note.id == note_id).first()
        self.assertIsNotNone(db_note)
        self.assertEqual(db_note.title, "Projektplanung Liara")
        self.assertEqual(db_note.category, "Entwicklung")

        # Test listing notes
        list_call = ToolCall(
            tool_name="list_notes",
            parameters={"category": "Entwicklung"},
            raw_text='<tool_call>{"tool": "list_notes"}</tool_call>'
        )
        list_res = await self.executor.execute(list_call, user_id=self.user_id)
        self.assertTrue(list_res.get("success"))
        self.assertEqual(list_res["result"]["count"], 1)
        self.assertEqual(list_res["result"]["notes"][0]["title"], "Projektplanung Liara")

    @patch("services.productivity_tools.store_in_4d_memory")
    async def test_execute_create_list_and_update_task(self, mock_store_memory):
        """Test task creation, listing, and completion status update."""
        create_call = ToolCall(
            tool_name="create_task",
            parameters={
                "title": "Dokumentation für Issue #1 aktualisieren",
                "description": "Walkthrough und Systemd-Socket Details niederschreiben",
                "priority": "high",
                "due_date": "2026-09-05 17:00",
                "tags": ["docs", "urgent"]
            },
            raw_text='<tool_call>{"tool": "create_task"}</tool_call>'
        )
        res = await self.executor.execute(create_call, user_id=self.user_id)
        self.assertTrue(res.get("success"), f"Task creation failed: {res}")
        task_id = res["result"]["task_id"]

        # List open tasks
        list_call = ToolCall(
            tool_name="list_tasks",
            parameters={"completed": False, "priority": "high"},
            raw_text='<tool_call>{"tool": "list_tasks"}</tool_call>'
        )
        list_res = await self.executor.execute(list_call, user_id=self.user_id)
        self.assertTrue(list_res.get("success"))
        self.assertEqual(list_res["result"]["count"], 1)

        # Update task status to completed
        update_call = ToolCall(
            tool_name="update_task_status",
            parameters={"task_id": task_id, "completed": True},
            raw_text='<tool_call>{"tool": "update_task_status"}</tool_call>'
        )
        upd_res = await self.executor.execute(update_call, user_id=self.user_id)
        self.assertTrue(upd_res.get("success"))

        # Verify DB
        db_task = self.db.query(Task).filter(Task.id == task_id).first()
        self.assertTrue(db_task.completed)

    @patch("services.productivity_tools.store_in_4d_memory")
    async def test_execute_create_and_list_calendar_event(self, mock_store_memory):
        """Test calendar event creation and date range querying."""
        start_time = "2026-09-10 14:00"
        end_time = "2026-09-10 15:30"
        create_call = ToolCall(
            tool_name="create_calendar_event",
            parameters={
                "title": "Team Sprint Review",
                "start_time": start_time,
                "end_time": end_time,
                "description": "Q3 Meilensteine und Release 1.0",
                "location": "Konferenzraum Alpha",
                "event_type": "meeting"
            },
            raw_text='<tool_call>{"tool": "create_calendar_event"}</tool_call>'
        )
        res = await self.executor.execute(create_call, user_id=self.user_id)
        self.assertTrue(res.get("success"), f"Event creation failed: {res}")
        event_id = res["result"]["event_id"]

        # List events
        list_call = ToolCall(
            tool_name="list_calendar_events",
            parameters={
                "start_date": "2026-09-01",
                "end_date": "2026-09-30"
            },
            raw_text='<tool_call>{"tool": "list_calendar_events"}</tool_call>'
        )
        list_res = await self.executor.execute(list_call, user_id=self.user_id)
        self.assertTrue(list_res.get("success"))
        self.assertEqual(list_res["result"]["count"], 1)
        self.assertEqual(list_res["result"]["events"][0]["location"], "Konferenzraum Alpha")

    @patch("services.productivity_tools.get_relevant_context")
    async def test_execute_search_memory(self, mock_get_context):
        """Test memory search tool execution."""
        mock_get_context.return_value = [
            {"concept": "Socket Activation", "similarity": 0.94, "related_messages": [{"role": "user", "content": "Zero downtime deploy"}]}
        ]
        call = ToolCall(
            tool_name="search_memory",
            parameters={"query": "Wie funktioniert die Zero-Downtime Socket Activation?"},
            raw_text='<tool_call>{"tool": "search_memory"}</tool_call>'
        )
        res = await self.executor.execute(call, user_id=self.user_id)
        self.assertTrue(res.get("success"))
        self.assertEqual(res["result"]["count"], 1)
        self.assertEqual(res["result"]["memories"][0]["concept"], "Socket Activation")

    def test_agent_registry_productivity_profile(self):
        """Test that ProductivityAgent is registered and instantiable."""
        profile = AgentRegistry.get_profile("productivity")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["name"], "Productivity Agent")
        self.assertEqual(profile["category"], "productivity")

        agent = AgentRegistry.create_agent("productivity", user_id=self.user_id)
        self.assertIsInstance(agent, ProductivityAgent)
        self.assertEqual(agent.name, "ProductivityAgent")
        self.assertIn("create_note", agent.tools)
        self.assertIn("create_task", agent.tools)
        self.assertIn("create_calendar_event", agent.tools)


if __name__ == "__main__":
    unittest.main()
