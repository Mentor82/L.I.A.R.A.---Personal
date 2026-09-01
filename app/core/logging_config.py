"""
Centralized structured logging configuration for Liara backend and agent runtime.
Provides consistent timestamp, level, logger name, and PID formatting for journalctl/stdout,
environment-configurable log levels, noise suppression for third-party libraries,
and structured context helpers without leaking secrets or credentials.
"""
import logging
import os
import sys
from typing import Any, Dict, Optional

# Default log format for stdout / journalctl
DEFAULT_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] [PID:%(process)d] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Third-party loggers to suppress/tune to WARNING
NOISY_LOGGERS = [
    "httpx",
    "httpcore",
    "urllib3",
    "neo4j",
    "watchfiles",
    "uvicorn.access",
    "asyncio",
    "multipart",
]

_logging_initialized = False


def get_configured_log_level() -> int:
    """
    Resolves the log level from environment variables (LIARA_LOG_LEVEL or LOG_LEVEL).
    Defaults to INFO.
    """
    raw_level = os.getenv("LIARA_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "INFO"
    level_name = raw_level.strip().upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_name, logging.INFO)


def setup_logging(log_level: Optional[str] = None, force: bool = False) -> logging.Logger:
    """
    Initializes root and application logging handlers and formatters.
    Can be called once during startup in main.py.
    """
    global _logging_initialized
    if _logging_initialized and not force:
        return logging.getLogger("liara")

    level = (
        getattr(logging, log_level.upper(), logging.INFO)
        if log_level
        else get_configured_log_level()
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing stream handlers to avoid duplicates on reload
    for handler in list(root_logger.handlers):
        if isinstance(handler, logging.StreamHandler):
            root_logger.removeHandler(handler)

    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Tune noisy third-party loggers
    for logger_name in NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    _logging_initialized = True

    app_logger = logging.getLogger("liara")
    app_logger.info(
        "Logging initialized (level=%s, pid=%d)",
        logging.getLevelName(level),
        os.getpid(),
    )
    return app_logger


def format_context(
    *,
    user_id: Optional[Any] = None,
    session_id: Optional[Any] = None,
    run_id: Optional[str] = None,
    model: Optional[str] = None,
    transport: Optional[str] = None,
    tool_name: Optional[str] = None,
    **extra: Any,
) -> str:
    """
    Builds a consistent key=value context string for log messages.
    Example: '[user=1 session=42 model=llama3.2 tool=web_search]'
    """
    items = []
    if user_id is not None:
        items.append(f"user={user_id}")
    if session_id is not None:
        items.append(f"session={session_id}")
    if run_id is not None:
        items.append(f"run_id={run_id}")
    if model is not None:
        items.append(f"model={model}")
    if transport is not None:
        items.append(f"transport={transport}")
    if tool_name is not None:
        items.append(f"tool={tool_name}")

    for k, v in extra.items():
        if v is not None:
            items.append(f"{k}={v}")

    if not items:
        return ""
    return f"[{' '.join(items)}] "


def safe_preview(text: Optional[str], max_len: int = 80) -> str:
    """
    Safely previews arbitrary text by stripping newlines and truncating length.
    Prevents log injection and excessive log volume.
    """
    if not text:
        return ""
    cleaned = " ".join(text.split())
    if len(cleaned) > max_len:
        return cleaned[:max_len] + "..."
    return cleaned
