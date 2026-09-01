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
    _renew_session_lock,
    _session_lock_watchdog,
    _release_session_lock,
    stream_ollama_response,
    SESSION_GENERATION_LOCK_TTL,
    SESSION_GENERATION_LOCK_RENEW_INTERVAL,
    SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT,
    SessionLockTimeoutError,
    SessionLockUnavailableError,
    SessionLockLostError,
)

class TestChatStreamingLock(unittest.IsolatedAsyncioTestCase):

    def test_lock_constants(self):
        """Verify that lease TTL is short for fast crash-recovery, while acquire timeout allows long turns."""
        self.assertLessEqual(SESSION_GENERATION_LOCK_TTL, 120)  # Crash-recovery TTL <= 120s
        self.assertLess(SESSION_GENERATION_LOCK_RENEW_INTERVAL, SESSION_GENERATION_LOCK_TTL)
        self.assertGreaterEqual(SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT, 600)

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

    def test_renew_session_lock(self):
        """Verify _renew_session_lock reacquires or extends lock lease."""
        mock_lock = MagicMock()
        mock_lock.reacquire.return_value = True
        self.assertTrue(_renew_session_lock(mock_lock))
        mock_lock.reacquire.assert_called_once()

        # None lock returns False safely
        self.assertFalse(_renew_session_lock(None))

        # Failing reacquire returns False without raising
        failing_lock = MagicMock()
        failing_lock.reacquire.side_effect = Exception("Redis error")
        self.assertFalse(_renew_session_lock(failing_lock))

    async def test_session_lock_watchdog_renews_and_stops(self):
        """Verify watchdog task renews lease periodically and exits cleanly upon cancellation."""
        renew_count = 0
        mock_lock = MagicMock()
        def mock_reacquire():
            nonlocal renew_count
            renew_count += 1
            return True
        mock_lock.reacquire.side_effect = mock_reacquire

        lock_lost_event = asyncio.Event()
        watchdog_task = asyncio.create_task(_session_lock_watchdog(mock_lock, lock_lost_event, interval=0.02))
        await asyncio.sleep(0.065)
        watchdog_task.cancel()
        await asyncio.gather(watchdog_task, return_exceptions=True)

        self.assertGreaterEqual(renew_count, 2)
        self.assertFalse(lock_lost_event.is_set())

    async def test_session_lock_watchdog_signals_lock_lost_on_failure(self):
        """Verify watchdog signals lock_lost_event when lease renewal fails."""
        mock_lock = MagicMock()
        mock_lock.reacquire.return_value = False  # Renewal fails (e.g. key expired in Redis)

        lock_lost_event = asyncio.Event()
        watchdog_task = asyncio.create_task(_session_lock_watchdog(mock_lock, lock_lost_event, interval=0.02))
        await asyncio.sleep(0.05)

        self.assertTrue(lock_lost_event.is_set())
        watchdog_task.cancel()
        await asyncio.gather(watchdog_task, return_exceptions=True)

    async def test_lease_renewal_protects_turn_longer_than_ttl(self):
        """
        Verify that an active turn running longer than initial TTL is protected by
        watchdog lease renewal, preventing a concurrent turn from acquiring the lock mid-turn.
        """
        import time
        active_owner = None
        ttl_expiry_time = 0.0

        class TimeAwareMockLock:
            def __init__(self, owner_id):
                self.owner_id = owner_id

            def acquire(self, blocking=True):
                nonlocal active_owner, ttl_expiry_time
                now = time.monotonic()
                if active_owner is not None and now < ttl_expiry_time:
                    if active_owner != self.owner_id:
                        return False
                active_owner = self.owner_id
                ttl_expiry_time = now + 0.08  # 80ms initial TTL
                return True

            def reacquire(self):
                nonlocal active_owner, ttl_expiry_time
                now = time.monotonic()
                if active_owner == self.owner_id:
                    ttl_expiry_time = now + 0.08  # Reset TTL by 80ms
                    return True
                return False

            def release(self):
                nonlocal active_owner, ttl_expiry_time
                if active_owner == self.owner_id:
                    active_owner = None
                    ttl_expiry_time = 0.0

        lock_a = TimeAwareMockLock("worker_A")
        lock_b = TimeAwareMockLock("worker_B")

        # Worker A acquires lock (initial TTL = 80ms)
        self.assertTrue(lock_a.acquire())
        # Start watchdog renewing every 30ms
        lock_lost_a = asyncio.Event()
        watchdog_a = asyncio.create_task(_session_lock_watchdog(lock_a, lock_lost_a, interval=0.03))

        # Worker A runs for 180ms (> 2x initial TTL of 80ms)
        await asyncio.sleep(0.18)

        # Worker B tries to acquire lock while Worker A is still running
        # Because watchdog kept renewing, Worker B CANNOT acquire lock
        self.assertFalse(lock_b.acquire())

        # Worker A finishes, cancels watchdog, and releases lock
        watchdog_a.cancel()
        await asyncio.gather(watchdog_a, return_exceptions=True)
        lock_a.release()

        # Now Worker B can immediately acquire lock
        self.assertTrue(lock_b.acquire())
        lock_b.release()

    async def test_dead_worker_allows_subsequent_acquire_after_ttl(self):
        """
        Verify Crash Recovery: if a worker dies without releasing the lock (and without renewing),
        the lock expires after TTL and a subsequent request can take over.
        """
        import time
        active_owner = None
        ttl_expiry_time = 0.0

        class TimeAwareMockLock:
            def __init__(self, owner_id):
                self.owner_id = owner_id

            def acquire(self, blocking=True):
                nonlocal active_owner, ttl_expiry_time
                now = time.monotonic()
                if active_owner is not None and now < ttl_expiry_time:
                    if active_owner != self.owner_id:
                        return False
                active_owner = self.owner_id
                ttl_expiry_time = now + 0.05  # 50ms TTL
                return True

        lock_a = TimeAwareMockLock("dead_worker_A")
        lock_b = TimeAwareMockLock("worker_B")

        # Worker A acquires lock with 50ms TTL, then 'crashes' (no watchdog, no release)
        self.assertTrue(lock_a.acquire())

        # Immediately, Worker B cannot acquire
        self.assertFalse(lock_b.acquire())

        # Wait 70ms (> 50ms TTL)
        await asyncio.sleep(0.07)

        # Worker B can now acquire because Worker A's un-renewed lock expired
        self.assertTrue(lock_b.acquire())

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
    def test_acquire_session_lock_raises_unavailable_when_redis_missing(self, mock_get_redis):
        """Verify _acquire_session_lock raises SessionLockUnavailableError when Redis is unavailable."""
        mock_get_redis.return_value = None
        with self.assertRaises(SessionLockUnavailableError):
            _acquire_session_lock(123)

        mock_svc = MagicMock()
        mock_svc.client = None
        mock_get_redis.return_value = mock_svc
        with self.assertRaises(SessionLockUnavailableError):
            _acquire_session_lock(123)

    @patch("api.routers.chat_streaming.get_redis_service")
    def test_acquire_session_lock_raises_timeout_when_contended(self, mock_get_redis):
        """Verify _acquire_session_lock raises SessionLockTimeoutError when lock cannot be acquired."""
        mock_svc = MagicMock()
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = False
        mock_svc.client.lock.return_value = mock_lock
        mock_get_redis.return_value = mock_svc

        with self.assertRaises(SessionLockTimeoutError):
            _acquire_session_lock(123)

    @patch("api.routers.chat_streaming._acquire_session_lock")
    async def test_stream_ollama_response_lock_timeout_aborts(self, mock_acquire):
        """Verify stream aborts with error event when lock acquisition times out."""
        mock_acquire.side_effect = SessionLockTimeoutError("Contention timeout")

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

    @patch("api.routers.chat_streaming._acquire_session_lock")
    async def test_stream_ollama_response_redis_unavailable_aborts(self, mock_acquire):
        """Verify stream fails closed with error event when Redis is unavailable (no lockless fallback)."""
        mock_acquire.side_effect = SessionLockUnavailableError("Redis is down")

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
        self.assertIn("Sitzungskoordination momentan nicht verfügbar", parsed.get("error", ""))

    @patch("api.routers.chat_streaming._acquire_session_lock")
    @patch("api.routers.chat_streaming._renew_session_lock")
    @patch("api.routers.chat_streaming.httpx.AsyncClient")
    @patch("api.routers.chat_streaming.get_model_num_predict")
    @patch("api.routers.chat_streaming.get_config_service")
    @patch("api.routers.chat_streaming.MoodSystem")
    async def test_stream_ollama_response_lease_loss_aborts_mid_turn(self, mock_mood, mock_get_config, mock_num_predict, mock_http_client, mock_renew, mock_acquire):
        """
        Verify that when lease renewal fails during an active generation turn,
        the turn aborts fail-closed with SSE error 'Sitzungskoordination wurde während der Anfrage unterbrochen'
        and does not perform normal turn completion.
        """
        mock_mood_instance = MagicMock()
        mock_mood_instance.get_snapshot.return_value = {"mood": "neutral", "modifier": ""}
        mock_mood.return_value = mock_mood_instance
        mock_mood.detect_interaction_type.return_value = "chat"

        mock_num_predict.return_value = 1024
        mock_cfg_svc = MagicMock()
        mock_cfg_svc.get_max_tokens.return_value = 1024
        mock_get_config.return_value = mock_cfg_svc

        mock_lock = MagicMock()
        mock_acquire.return_value = mock_lock
        mock_renew.return_value = False  # Renewal immediately fails on watchdog tick

        # Mock slow streaming from Ollama
        async def mock_aiter_lines():
            yield json.dumps({"message": {"content": "First word"}})
            await asyncio.sleep(0.05)  # Watchdog fires and sets lock_lost_event
            yield json.dumps({"message": {"content": "Second word"}})
            yield json.dumps({"done": True})

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.aiter_lines = MagicMock(side_effect=mock_aiter_lines)

        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__.return_value = mock_resp
        mock_stream_ctx.__aexit__.return_value = None
        mock_client_instance.stream.return_value = mock_stream_ctx
        mock_http_client.return_value = mock_client_instance

        with patch("api.routers.chat_streaming.SESSION_GENERATION_LOCK_RENEW_INTERVAL", 0.02):
            generator = stream_ollama_response(
                message="Test message",
                session_id=123,
                user_id=None
            )

            events = []
            async for chunk in generator:
                events.append(chunk)

            parsed_errors = [
                json.loads(e.replace("data: ", "").strip()).get("error", "")
                for e in events if e.startswith("data: ") and '"error"' in e
            ]
            self.assertTrue(
                any("Sitzungskoordination wurde während der Anfrage unterbrochen" in err for err in parsed_errors),
                f"Events yielded: {events}"
            )
