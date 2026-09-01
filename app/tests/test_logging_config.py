"""
Unit tests for centralized structured logging configuration (Issue #24).
"""
import logging
import os
from unittest.mock import patch

from core.logging_config import (
    DEFAULT_LOG_FORMAT,
    format_context,
    get_configured_log_level,
    safe_preview,
    setup_logging,
)


def test_format_context():
    # Empty context returns empty string
    assert format_context() == ""

    # Single field
    ctx = format_context(user_id=42)
    assert ctx == "[user=42] "

    # Multiple fields
    ctx = format_context(user_id=1, session_id=10, model="llama3.2", tool_name="web_search")
    assert "[user=1" in ctx
    assert "session=10" in ctx
    assert "model=llama3.2" in ctx
    assert "tool=web_search]" in ctx


def test_safe_preview():
    assert safe_preview("") == ""
    assert safe_preview(None) == ""

    # Strips multiple newlines and spaces
    multiline = "Hello\nworld\n   test   here"
    preview = safe_preview(multiline, max_len=50)
    assert preview == "Hello world test here"

    # Truncates cleanly with ellipsis
    long_text = "a" * 100
    preview = safe_preview(long_text, max_len=10)
    assert preview == "aaaaaaaaaa..."
    assert len(preview) == 13


def test_get_configured_log_level():
    with patch.dict(os.environ, {"LIARA_LOG_LEVEL": "DEBUG"}):
        assert get_configured_log_level() == logging.DEBUG

    with patch.dict(os.environ, {"LIARA_LOG_LEVEL": "warning"}):
        assert get_configured_log_level() == logging.WARNING

    with patch.dict(os.environ, {"LIARA_LOG_LEVEL": "ERROR"}):
        assert get_configured_log_level() == logging.ERROR

    with patch.dict(os.environ, {"LIARA_LOG_LEVEL": "UNKNOWN_LEVEL"}):
        assert get_configured_log_level() == logging.INFO


def test_setup_logging(capsys):
    app_logger = setup_logging(log_level="DEBUG", force=True)
    assert app_logger is not None

    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) >= 1

    # Check noisy loggers are throttled
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("urllib3").level == logging.WARNING
