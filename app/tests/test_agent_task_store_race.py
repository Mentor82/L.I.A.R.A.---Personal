import os
import sys
import json
import unittest
from unittest.mock import MagicMock

if "redis" not in sys.modules:
    try:
        import redis
    except ImportError:
        sys.modules["redis"] = MagicMock()


class InMemoryHashRedis:
    def __init__(self):
        self.hashes = {}
        self.streams = {}
        self.ttls = {}

    def exists(self, key):
        return key in self.hashes or key in self.streams

    def hset(self, key, mapping=None, key_field=None, value=None):
        if key not in self.hashes:
            self.hashes[key] = {}
        if mapping:
            for k, v in mapping.items():
                self.hashes[key][str(k)] = str(v)
        elif key_field is not None and value is not None:
            self.hashes[key][str(key_field)] = str(value)
        return len(self.hashes[key])

    def hget(self, key, field):
        if key not in self.hashes:
            return None
        return self.hashes[key].get(str(field))

    def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def expire(self, key, seconds):
        self.ttls[key] = seconds
        return True

    def xadd(self, key, fields):
        if key not in self.streams:
            self.streams[key] = []
        entry_id = f"{len(self.streams[key]) + 1}-0"
        self.streams[key].append((entry_id, fields))
        return entry_id

    def xrange(self, key, min="-", max="+"):
        return list(self.streams.get(key, []))

    def xread(self, streams, block=None, count=None):
        out = []
        for key, last_id in streams.items():
            entries = self.streams.get(key, [])
            out.append((key, entries))
        return out


class MockRedisService:
    def __init__(self):
        self.client = InMemoryHashRedis()


import services.agent_task_store as store

_mock_svc = MockRedisService()
store.get_redis_service = lambda: _mock_svc


class TestAgentTaskStoreRace(unittest.TestCase):

    def setUp(self):
        _mock_svc.client.hashes.clear()
        _mock_svc.client.streams.clear()
        _mock_svc.client.ttls.clear()

    def test_create_and_get_task(self):
        task = store.create_task(
            task_id="task_123",
            agent_id="code",
            task_text="Run test",
            user_id=42,
            session_id=10
        )
        self.assertEqual(task["task_id"], "task_123")
        self.assertEqual(task["status"], "pending")
        self.assertFalse(task["cancel_requested"])

        retrieved = store.get_task("task_123")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["task_id"], "task_123")
        self.assertEqual(retrieved["agent_id"], "code")
        self.assertEqual(retrieved["user_id"], 42)
        self.assertEqual(retrieved["session_id"], 10)
        self.assertEqual(retrieved["current_step"], 0)
        self.assertFalse(retrieved["cancel_requested"])

    def test_atomic_update_and_cancel_race(self):
        # Initialer Task
        store.create_task("task_race", "research", "Search web", user_id=1, session_id=None)

        # Worker A startet und aktualisiert Schritt 1
        store.update_task("task_race", status="running", current_step=1)
        self.assertEqual(store.get_task("task_race")["current_step"], 1)
        self.assertEqual(store.get_task("task_race")["status"], "running")
        self.assertFalse(store.is_cancel_requested("task_race"))

        # Worker B sendet Abbruchanforderung
        cancelled = store.request_cancel("task_race")
        self.assertTrue(cancelled)
        self.assertTrue(store.is_cancel_requested("task_race"))

        # Worker A aktualisiert Schritt 2 (darf cancel_requested=True niemals überschreiben!)
        store.update_task("task_race", current_step=2)

        final_state = store.get_task("task_race")
        self.assertEqual(final_state["current_step"], 2)
        self.assertTrue(final_state["cancel_requested"], "cancel_requested must NOT be overwritten by step updates!")
        self.assertTrue(store.is_cancel_requested("task_race"))

    def test_event_stream_append_and_read(self):
        store.append_event("task_stream", {"event": "step", "data": {"step": 1}})
        store.append_event("task_stream", {"event": "done", "data": {"answer": "OK"}})

        events = store.read_events_from_start("task_stream")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0][1]["event"], "step")
        self.assertEqual(events[1][1]["event"], "done")


if __name__ == "__main__":
    unittest.main()
