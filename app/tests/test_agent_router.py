"""
Integration Tests für den Agent Router von L.I.A.R.A.
"""
import os
import sys
from unittest.mock import MagicMock

# Umgebungsvariablen & Mocks für isolierten Test-Runner
os.environ["LIARA_SECRET_KEY"] = "test_secret_key_for_unit_tests_1234567890abcdef"

if "jose" not in sys.modules:
    mock_jose = MagicMock()
    mock_jose.JWTError = Exception
    sys.modules["jose"] = mock_jose
    sys.modules["jose.jwt"] = mock_jose

if "passlib" not in sys.modules:
    mock_passlib = MagicMock()
    sys.modules["passlib"] = mock_passlib
    sys.modules["passlib.context"] = mock_passlib

if "redis" not in sys.modules:
    try:
        import redis
    except ImportError:
        sys.modules["redis"] = MagicMock()

class InMemoryRedis:
    def __init__(self):
        self.data = {}

    def setex(self, name, time, value):
        self.data[name] = value

    def get(self, name):
        return self.data.get(name)

    def xadd(self, name, fields):
        pass

    def xrange(self, name, min='-', max='+'):
        return []

    def expire(self, name, time):
        return True


class MockRedisService:
    def __init__(self):
        self.client = InMemoryRedis()


import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.agent_router import router as agent_router
from core.dependencies import require_active_user
from api.models.base_models import User
import services.agent_task_store

_mock_redis_svc = MockRedisService()
services.agent_task_store.get_redis_service = lambda: _mock_redis_svc


class MockUser:
    id = 1
    username = "admin"
    role = "admin"
    is_active = True


def mock_require_active_user():
    return MockUser()


class TestAgentRouter(unittest.TestCase):

    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(agent_router)
        self.app.dependency_overrides[require_active_user] = mock_require_active_user
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def test_get_agent_types(self):
        res = self.client.get("/agents/types")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        agents = data.get("agents", [])
        self.assertGreaterEqual(len(agents), 2)
        agent_ids = [a["id"] for a in agents]
        self.assertIn("code", agent_ids)
        self.assertIn("research", agent_ids)

    def test_start_agent_task_validation(self):
        # 1. Leerer Task
        res_empty = self.client.post("/agents/run", json={"agent_id": "code", "task": "   "})
        self.assertEqual(res_empty.status_code, 400)

        # 2. Unbekannter Agent-Typ
        res_unknown = self.client.post("/agents/run", json={"agent_id": "non_existing", "task": "Do something"})
        self.assertEqual(res_unknown.status_code, 400)

    def test_start_and_get_task(self):
        # Gültigen Task starten
        res = self.client.post("/agents/run", json={"agent_id": "code", "task": "Prüfe Syntax von main.py"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("task_id", data)
        task_id = data["task_id"]

        # Status abfragen
        res_status = self.client.get(f"/agents/tasks/{task_id}")
        self.assertEqual(res_status.status_code, 200)
        status_data = res_status.json()
        self.assertEqual(status_data["task_id"], task_id)
        self.assertEqual(status_data["agent_id"], "code")


if __name__ == "__main__":
    unittest.main()
