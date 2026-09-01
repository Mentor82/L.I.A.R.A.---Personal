import os
import sys
import unittest
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

from api.models.base_models import User, UserRole
from core.dependencies import get_current_user_ws, get_admin_user_ws
from api.routers.workspace_terminal import _session_owned


class MockWebSocket:
    def __init__(self, token=None):
        self.headers = {}
        if token:
            self.headers["sec-websocket-protocol"] = token


class TestTerminalAuth(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.normal_user = User(
            id=1,
            username="normal_user",
            role=UserRole.USER,
            is_active=True,
            token_version=1
        )
        self.admin_user = User(
            id=2,
            username="admin_user",
            role=UserRole.ADMIN,
            is_active=True,
            token_version=1
        )
        self.inactive_user = User(
            id=3,
            username="inactive_user",
            role=UserRole.USER,
            is_active=False,
            token_version=1
        )

    @patch("core.dependencies.verify_access_token")
    @patch("core.dependencies.token_version_matches")
    async def test_get_current_user_ws_normal_user_success(self, mock_tv, mock_vat):
        mock_vat.return_value = {"user_id": 1, "token_version": 1}
        mock_tv.return_value = True

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = self.normal_user

        ws = MockWebSocket(token="valid_normal_token")
        user = await get_current_user_ws(ws, mock_db)
        self.assertEqual(user.id, 1)
        self.assertEqual(user.role, UserRole.USER)

    @patch("core.dependencies.verify_access_token")
    @patch("core.dependencies.token_version_matches")
    async def test_get_admin_user_ws_normal_user_rejected(self, mock_tv, mock_vat):
        mock_vat.return_value = {"user_id": 1, "token_version": 1}
        mock_tv.return_value = True

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = self.normal_user

        ws = MockWebSocket(token="valid_normal_token")
        with self.assertRaises(Exception) as ctx:
            await get_admin_user_ws(ws, mock_db)
        self.assertIn("Admin privileges required", str(ctx.exception))

    @patch("core.dependencies.verify_access_token")
    @patch("core.dependencies.token_version_matches")
    async def test_get_admin_user_ws_admin_user_success(self, mock_tv, mock_vat):
        mock_vat.return_value = {"user_id": 2, "token_version": 1}
        mock_tv.return_value = True

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = self.admin_user

        ws = MockWebSocket(token="valid_admin_token")
        user = await get_admin_user_ws(ws, mock_db)
        self.assertEqual(user.id, 2)
        self.assertEqual(user.role, UserRole.ADMIN)

    @patch("core.dependencies.verify_access_token")
    async def test_get_current_user_ws_no_token_rejected(self, mock_vat):
        mock_db = MagicMock()
        ws = MockWebSocket(token=None)
        with self.assertRaises(Exception) as ctx:
            await get_current_user_ws(ws, mock_db)
        self.assertIn("No authentication token provided", str(ctx.exception))

    def test_session_ownership(self):
        mock_db = MagicMock()
        # Session 100 gehört User 1
        mock_db.execute().first.return_value = (100,)
        self.assertTrue(_session_owned(mock_db, 100, 1))

        # Session 200 gehört nicht User 1
        mock_db.execute().first.return_value = None
        self.assertFalse(_session_owned(mock_db, 200, 1))


if __name__ == "__main__":
    unittest.main()
