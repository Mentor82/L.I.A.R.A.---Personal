"""
Lock Guard & Lease Management (Issue #13, #18, #20, #23)
=========================================================
Handles Redis per-session generation locking, lease renewal heartbeat watchdog,
zero-lag lease loss racing, and SSE keep-alive pulse generator.
"""

import sys
import asyncio
import logging
from typing import Optional

from services.redis_service import get_redis_service

logger = logging.getLogger(__name__)

SESSION_GENERATION_LOCK_TTL = 60  # seconds
SESSION_GENERATION_LOCK_RENEW_INTERVAL = 15.0  # seconds
SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT = 1200  # seconds
SSE_KEEPALIVE_INTERVAL = 10.0  # seconds


class SessionLockError(Exception):
    """Base exception for chat session lock failures."""
    pass


class SessionLockTimeoutError(SessionLockError):
    """Raised when lock acquisition times out due to session lock contention."""
    pass


class SessionLockUnavailableError(SessionLockError):
    """Raised when Redis or the lock coordination infrastructure is unavailable."""
    pass


class SessionLockLostError(SessionLockError):
    """Raised when the session generation lock lease is lost mid-turn."""
    pass


def _resolve_redis_service():
    mod = sys.modules.get("api.routers.chat_streaming")
    if mod and hasattr(mod, "get_redis_service"):
        return mod.get_redis_service()
    return get_redis_service()


def _acquire_session_lock(session_id: int):
    """
    Redis lock serializing active /chat/stream generation per session (issue #13, #18, #25).
    """
    try:
        redis_svc = _resolve_redis_service()
        if not redis_svc or not redis_svc.client:
            raise SessionLockUnavailableError("Redis service is unavailable")
        lock = redis_svc.client.lock(
            f"chat_stream_lock:{session_id}",
            timeout=SESSION_GENERATION_LOCK_TTL,
            blocking_timeout=SESSION_GENERATION_LOCK_ACQUIRE_TIMEOUT,
            thread_local=False,
        )
        if not lock.acquire(blocking=True):
            raise SessionLockTimeoutError(f"Session lock acquisition timed out for session {session_id}")
        return lock
    except (SessionLockTimeoutError, SessionLockUnavailableError):
        raise
    except Exception as e:
        logger.warning(f"Session generation lock error for session {session_id}: {e}")
        raise SessionLockUnavailableError(f"Redis lock error: {e}") from e


def _renew_session_lock(lock) -> bool:
    """
    Renews/extends the lease on an active Redis session lock.
    """
    if lock is None:
        return False
    try:
        if hasattr(lock, "reacquire"):
            return bool(lock.reacquire())
        elif hasattr(lock, "extend"):
            return bool(lock.extend(SESSION_GENERATION_LOCK_TTL, replace_ttl=True))
        return False
    except Exception as e:
        logger.warning(f"Failed to renew session generation lock: {e}")
        return False


def _resolve_renew_interval(interval: Optional[float]) -> float:
    if interval is not None:
        return interval
    mod = sys.modules.get("api.routers.chat_streaming")
    if mod and hasattr(mod, "SESSION_GENERATION_LOCK_RENEW_INTERVAL"):
        return getattr(mod, "SESSION_GENERATION_LOCK_RENEW_INTERVAL")
    return SESSION_GENERATION_LOCK_RENEW_INTERVAL


async def _session_lock_watchdog(lock, lock_lost_event: Optional[asyncio.Event] = None, interval: Optional[float] = None):
    """
    Background heartbeat task that periodically renews the session lock lease.
    """
    sleep_interval = _resolve_renew_interval(interval)
    try:
        while True:
            await asyncio.sleep(sleep_interval)
            mod = sys.modules.get("api.routers.chat_streaming")
            renew_fn = getattr(mod, "_renew_session_lock", _renew_session_lock) if mod else _renew_session_lock
            renewed = await asyncio.to_thread(renew_fn, lock)
            if not renewed:
                logger.warning("Session lock lease renewal failed - lock ownership lost! Signalling turn abort.")
                if lock_lost_event is not None:
                    lock_lost_event.set()
                break
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(f"Session lock watchdog error: {e}")
        if lock_lost_event is not None:
            lock_lost_event.set()


def _release_session_lock(lock) -> None:
    if lock is None:
        return
    try:
        lock.release()
    except Exception as e:
        logger.debug(f"Session generation lock release skipped: {e}")


async def _race_with_lock_lost(coro_or_future, lock_lost_event: Optional[asyncio.Event]):
    """
    Awaits an async operation while watching lock_lost_event.
    """
    if lock_lost_event is None:
        return await coro_or_future

    if lock_lost_event.is_set():
        raise SessionLockLostError("Sitzungskoordination wurde unterbrochen (Lease-Verlust).")

    op_task = asyncio.ensure_future(coro_or_future)
    lost_task = asyncio.ensure_future(lock_lost_event.wait())

    done, pending = await asyncio.wait(
        {op_task, lost_task},
        return_when=asyncio.FIRST_COMPLETED
    )

    for p in pending:
        p.cancel()
        try:
            await p
        except (asyncio.CancelledError, Exception):
            pass

    if lost_task in done:
        raise SessionLockLostError("Sitzungskoordination wurde während der Operation unterbrochen (Lease-Verlust).")

    return await op_task


async def _with_lock_lost_guard(async_iterable, lock_lost_event: Optional[asyncio.Event]):
    """
    Wraps an async generator/iterator so that every next-chunk wait is raced against lock_lost_event.
    """
    if lock_lost_event is None:
        async for item in async_iterable:
            yield item
        return

    iterator = async_iterable.__aiter__()
    while True:
        if lock_lost_event.is_set():
            raise SessionLockLostError("Sitzungskoordination wurde während des Streamings unterbrochen (Lease-Verlust).")

        next_task = asyncio.ensure_future(iterator.__anext__())
        lost_task = asyncio.ensure_future(lock_lost_event.wait())

        done, pending = await asyncio.wait(
            {next_task, lost_task},
            return_when=asyncio.FIRST_COMPLETED
        )

        for p in pending:
            p.cancel()
            try:
                await p
            except (asyncio.CancelledError, Exception):
                pass

        if lost_task in done:
            raise SessionLockLostError("Sitzungskoordination wurde während des Streamings unterbrochen (Lease-Verlust).")

        try:
            item = await next_task
        except StopAsyncIteration:
            break

        yield item


async def _with_sse_keepalive(source, interval: float = SSE_KEEPALIVE_INTERVAL):
    """
    Interleaves ': keep-alive\\n\\n' SSE comment lines into `source` whenever nothing real is yielded.
    """
    it = source.__aiter__()
    pending = None
    try:
        while True:
            if pending is None:
                pending = asyncio.ensure_future(it.__anext__())
            done, _ = await asyncio.wait({pending}, timeout=interval)
            if pending in done:
                task, pending = pending, None
                try:
                    yield task.result()
                except StopAsyncIteration:
                    break
            else:
                yield ": keep-alive\n\n"
    finally:
        if pending is not None:
            pending.cancel()
            try:
                await pending
            except (asyncio.CancelledError, StopAsyncIteration, Exception):
                pass
        aclose = getattr(source, "aclose", None)
        if aclose is not None:
            try:
                await aclose()
            except Exception:
                pass
