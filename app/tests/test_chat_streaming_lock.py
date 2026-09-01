import sys
import json
import asyncio
import unittest
from unittest.mock import MagicMock, patch

for mod in ("sentence_transformers", "neo4j"):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from api.routers.chat_streaming import (
    _with_sse_keepalive,
    _acquire_session_lock,
    _release_session_lock,
    stream_ollama_response,
    SESSION_GENERATION_LOCK_TTL,
    SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT
)

class TestChatStreamingLock(unittest.IsolatedAsyncioTestCase):

    def test_lock_constants(self):
        """Verify that acquire timeout matches lock TTL so long turns can wait without 15s cutoff."""
        self.assertGreaterEqual(SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT, 600)
        self.assertEqual(SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT, SESSION_GENERATION_LOCK_TTL)

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

    async def test_concurrent_turn_history_serialized_under_lock(self):
        """
        Verify that when two concurrent turns target the same session_id:
        Turn 2 waits for Turn 1's lock, and only queries conversation_history
        AFTER Turn 1 has completed and released the lock (Issue #13 + Issue #18).
        """
        lock_acquire_events = []
        history_read_snapshots = []
        simulated_messages_db = []

        class MockRedisService:
            def __init__(self):
                self.active_owner = None

            def create_lock(self, owner_id):
                service = self
                class Lock:
                    def __init__(self, owner):
                        self.owner = owner

                    def acquire(self, blocking=True):
                        if service.active_owner is not None and service.active_owner != self.owner:
                            return False
                        service.active_owner = self.owner
                        return True

                    def release(self):
                        if service.active_owner == self.owner:
                            service.active_owner = None
                return Lock(owner_id)

        redis_service = MockRedisService()

        async def simulated_turn_worker(turn_id, user_text, reply_text):
            lock = redis_service.create_lock(turn_id)
            # 1. Acquire lock (retrying until available)
            while not lock.acquire():
                await asyncio.sleep(0.01)
            lock_acquire_events.append(f"acquired_{turn_id}")

            try:
                # 2. History snapshot happens UNDER the lock
                snapshot = list(simulated_messages_db)
                history_read_snapshots.append((turn_id, snapshot))

                # 3. User message persisted
                simulated_messages_db.append({"role": "user", "content": user_text})
                await asyncio.sleep(0.03)

                # 4. Assistant message persisted
                simulated_messages_db.append({"role": "assistant", "content": reply_text})
            finally:
                lock.release()
                lock_acquire_events.append(f"released_{turn_id}")

        # Launch Turn A and Turn B concurrently
        await asyncio.gather(
            simulated_turn_worker("A", "Hallo von A", "Antwort auf A"),
            simulated_turn_worker("B", "Hallo von B", "Antwort auf B")
        )

        # Verify strict turn ordering
        self.assertEqual(lock_acquire_events, [
            "acquired_A", "released_A",
            "acquired_B", "released_B"
        ])

        # Turn A saw empty history
        turn_a_history = [s for t, s in history_read_snapshots if t == "A"][0]
        self.assertEqual(turn_a_history, [])

        # Turn B MUST see Turn A's user message AND Turn A's assistant reply
        turn_b_history = [s for t, s in history_read_snapshots if t == "B"][0]
        self.assertEqual(len(turn_b_history), 2)
        self.assertEqual(turn_b_history[0]["content"], "Hallo von A")
        self.assertEqual(turn_b_history[1]["content"], "Antwort auf A")

    @patch("api.routers.chat_streaming.get_redis_service")
    @patch("api.routers.chat_streaming._acquire_session_lock")
    async def test_stream_ollama_response_lock_timeout_aborts(self, mock_acquire, mock_get_redis):
        """Verify that if lock acquisition returns None on an active Redis service, stream aborts cleanly with error event."""
        mock_acquire.return_value = None
        mock_redis_svc = MagicMock()
        mock_redis_svc.client = MagicMock()
        mock_get_redis.return_value = mock_redis_svc

        generator = stream_ollama_response(
            message="Test message",
            session_id=123,
            user_id=1
        )

        events = []
        async for chunk in generator:
            events.append(chunk)

        self.assertEqual(len(events), 1)
        parsed = json.loads(events[0].replace("data: ", "").strip())
        self.assertEqual(parsed.get("type"), "error")
        self.assertIn("vorherige Anfrage", parsed.get("error", ""))
