"""
Chat Streaming Pipeline Package (Issue #23)
===========================================
Modular stage-based architecture for LLM streaming, session locking,
prompt assembly, tool execution, and turn persistence.
"""

from services.chat_stream.lock_guard import (
    SessionLockError,
    SessionLockTimeoutError,
    SessionLockUnavailableError,
    SessionLockLostError,
    _acquire_session_lock,
    _renew_session_lock,
    _session_lock_watchdog,
    _release_session_lock,
    _race_with_lock_lost,
    _with_lock_lost_guard,
    _with_sse_keepalive,
    SESSION_GENERATION_LOCK_TTL,
    SESSION_GENERATION_LOCK_RENEW_INTERVAL,
    SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT,
    SSE_KEEPALIVE_INTERVAL,
)

__all__ = [
    "SessionLockError",
    "SessionLockTimeoutError",
    "SessionLockUnavailableError",
    "SessionLockLostError",
    "_acquire_session_lock",
    "_renew_session_lock",
    "_session_lock_watchdog",
    "_release_session_lock",
    "_race_with_lock_lost",
    "_with_lock_lost_guard",
    "_with_sse_keepalive",
    "SESSION_GENERATION_LOCK_TTL",
    "SESSION_GENERATION_LOCK_RENEW_INTERVAL",
    "SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT",
    "SSE_KEEPALIVE_INTERVAL",
]
