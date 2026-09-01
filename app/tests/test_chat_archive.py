"""
Unit Tests for Chat Archive & Export Service (Issue #22)
"""

import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

os.environ["LIARA_SECRET_KEY"] = "test_secret_key_for_unit_tests_1234567890abcdef"

if "jose" not in sys.modules:
    mock_jose = MagicMock()
    mock_jose.JWTError = Exception
    sys.modules["jose"] = mock_jose
    sys.modules["jose.jwt"] = mock_jose

for mod in ("fcntl", "pty", "termios"):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from api.models.chat_session import ChatSession
from api.models.chat_message import ChatMessage
from services.chat_archive_service import (
    sanitize_filename,
    format_session_as_markdown,
    format_session_as_json,
    archive_session_to_workspace,
)


class TestChatArchiveService(unittest.TestCase):

    def setUp(self):
        self.session = ChatSession(
            id=42,
            user_id=1,
            title="Architektur & Code Diskussion: Refactoring #22",
            created_at=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 9, 1, 12, 30, 0, tzinfo=timezone.utc),
        )

        self.messages = [
            ChatMessage(
                id=101,
                session_id=42,
                user_id=1,
                role="user",
                content="Kannst du mir bei der Archivierung helfen?",
                timestamp=datetime(2026, 9, 1, 12, 0, 5, tzinfo=timezone.utc),
            ),
            ChatMessage(
                id=102,
                session_id=42,
                user_id=1,
                role="assistant",
                content="<think>Ich erstelle ein Konzept für den Export.</think>Klar! Hier ist der Plan.",
                model="llama3.2:3b",
                action_result={"tool_name": "workspace_search", "output": {"matches": 3}},
                web_search_results=[{"title": "Liara Docs", "url": "https://example.com/docs", "snippet": "Dokumentation"}],
                timestamp=datetime(2026, 9, 1, 12, 0, 15, tzinfo=timezone.utc),
            )
        ]

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("Normal Title"), "Normal_Title")
        self.assertEqual(sanitize_filename("Äpfel & Birnen / Früchte?"), "Äpfel_Birnen_Früchte")
        self.assertEqual(sanitize_filename("   "), "chat_archive")
        self.assertEqual(sanitize_filename("A" * 100, max_length=10), "AAAAAAAAAA")

    def test_format_session_as_markdown(self):
        md = format_session_as_markdown(self.session, self.messages)
        
        # Check Frontmatter
        self.assertIn("---", md)
        self.assertIn('title: "Architektur & Code Diskussion: Refactoring #22"', md)
        self.assertIn("session_id: 42", md)
        self.assertIn("models_used: \"llama3.2:3b\"", md)
        
        # Check Content and Structure
        self.assertIn("# Architektur & Code Diskussion: Refactoring #22", md)
        self.assertIn("### Turn 1 — **User**", md)
        self.assertIn("Kannst du mir bei der Archivierung helfen?", md)
        
        # Check Thinking folding
        self.assertIn("<details>", md)
        self.assertIn("Ich erstelle ein Konzept für den Export.", md)
        self.assertIn("Klar! Hier ist der Plan.", md)
        
        # Check Tool call
        self.assertIn("🛠️ **Ausgeführtes Tool:** `workspace_search`", md)
        
        # Check Web search sources
        self.assertIn("🌐 Quellennachweise:", md)
        self.assertIn("[Liara Docs](https://example.com/docs)", md)

    def test_format_session_as_json(self):
        data = format_session_as_json(self.session, self.messages)
        self.assertEqual(data["metadata"]["session_id"], 42)
        self.assertEqual(data["metadata"]["messages_count"], 2)
        self.assertEqual(len(data["messages"]), 2)
        self.assertEqual(data["messages"][0]["role"], "user")
        self.assertEqual(data["messages"][1]["role"], "assistant")
        self.assertEqual(data["messages"][1]["model"], "llama3.2:3b")

    @patch("services.chat_archive_service.write_workspace_file")
    @patch("services.chat_archive_service.create_workspace_folder")
    def test_archive_session_to_workspace_success(self, mock_create_folder, mock_write_file):
        mock_write_file.return_value = {"ok": True}

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        
        # Setup session query return
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = self.session
        mock_filter.order_by.return_value.all.return_value = self.messages

        result = archive_session_to_workspace(
            user_id=1,
            session_id=42,
            db=mock_db,
            target_folder="chat_archives"
        )

        self.assertTrue(result["ok"])
        self.assertIn("chat_archives/", result["filepath"])
        self.assertEqual(result["messages_archived"], 2)
        mock_create_folder.assert_called_once_with(1, 42, "chat_archives")
        mock_write_file.assert_called_once()

    def test_archive_session_not_found(self):
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        result = archive_session_to_workspace(
            user_id=1,
            session_id=999,
            db=mock_db
        )

        self.assertFalse(result["ok"])
        self.assertIn("nicht gefunden", result["error"])


if __name__ == "__main__":
    unittest.main()
