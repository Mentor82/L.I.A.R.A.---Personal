import sys
import asyncio
import unittest
from unittest.mock import MagicMock, patch

for mod in ("sentence_transformers", "neo4j"):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from api.routers.chat_streaming import _with_sse_keepalive, _acquire_session_lock, _release_session_lock

class TestChatStreamingLock(unittest.IsolatedAsyncioTestCase):

    async def test_with_sse_keepalive_emits_pulse(self):
        """Verify that _with_sse_keepalive emits ': keep-alive\n\n' during pauses."""
        async def slow_source():
            yield "data: {\"type\": \"metadata\"}\n\n"
            await asyncio.sleep(0.08)
            yield "data: {\"type\": \"content\", \"text\": \"Hello\"}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"

        wrapped = _with_sse_keepalive(slow_source(), interval=0.03)
        chunks = []
        async for chunk in wrapped:
            chunks.append(chunk)

        # Should contain at least one keep-alive pulse between metadata and content
        self.assertIn(": keep-alive\n\n", chunks)
        self.assertIn("data: {\"type\": \"metadata\"}\n\n", chunks)
        self.assertIn("data: {\"type\": \"content\", \"text\": \"Hello\"}\n\n", chunks)
        self.assertIn("data: {\"type\": \"done\"}\n\n", chunks)

    async def test_release_session_lock_safe(self):
        """Verify _release_session_lock releases lock and handles exceptions gracefully."""
        mock_lock = MagicMock()
        _release_session_lock(mock_lock)
        mock_lock.release.assert_called_once()

        # None lock should be a no-op
        _release_session_lock(None)

        # Failing release should not raise
        failing_lock = MagicMock()
        failing_lock.release.side_effect = Exception("Lock error")
        _release_session_lock(failing_lock)
