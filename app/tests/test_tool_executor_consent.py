import sys
from unittest.mock import MagicMock, patch

# Ensure redis module is mocked if not installed in local test environment
if "redis" not in sys.modules:
    try:
        import redis
    except ImportError:
        sys.modules["redis"] = MagicMock()

import pytest
from services.tool_executor import ToolExecutor, get_tool_executor
from services.tool_registry import ToolDefinition, ToolCategory


def test_tool_executor_singleton():
    executor1 = get_tool_executor()
    executor2 = get_tool_executor()
    assert executor1 is executor2


def test_check_web_search_consent_default_allowed():
    executor = ToolExecutor()
    with patch("services.tool_executor.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        # When no row exists, execute().first() returns None
        mock_session.execute.return_value.first.return_value = None

        assert executor._check_web_search_consent(user_id=999) is True
        mock_session.close.assert_called_once()


def test_check_web_search_consent_explicit_opt_out():
    executor = ToolExecutor()
    with patch("services.tool_executor.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        # When row exists with allow_web_search = False
        mock_session.execute.return_value.first.return_value = (False,)

        assert executor._check_web_search_consent(user_id=1) is False
        mock_session.close.assert_called_once()


def test_check_web_search_consent_explicit_opt_in():
    executor = ToolExecutor()
    with patch("services.tool_executor.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        # When row exists with allow_web_search = True
        mock_session.execute.return_value.first.return_value = (True,)

        assert executor._check_web_search_consent(user_id=1) is True
        mock_session.close.assert_called_once()


def test_check_workspace_agent_consent_default_false():
    executor = ToolExecutor()
    with patch("services.tool_executor.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        # Opt-in: default is False when no row exists
        mock_session.execute.return_value.first.return_value = None

        assert executor._check_workspace_agent_consent(user_id=999) is False
        mock_session.close.assert_called_once()
