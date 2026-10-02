"""
Cluster view for status/health endpoints and the model list (Personal#29 B4):
models and tasks as advertised by the LiNeP trunk CAPABILITIES, instead of
only asking the local Ollama (/api/tags).

Not a replacement for services/ollama_capabilities.py: CAPABILITIES carry
model ids, profiles and server flags, but no per-model capabilities
(tools/thinking) or context length, so those still come from /api/show.

Blocking (opens a lease + SL1 session): call from sync endpoints or via
asyncio.to_thread. Results are cached briefly, failures even shorter, so a
dashboard poll does not hammer the trunk.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_OK_TTL = 60.0
_FAIL_TTL = 15.0
_lock = threading.Lock()
_cache: tuple[float, float, Optional[dict]] = (0.0, 0.0, None)  # (checked_at, ttl, info)


def cluster_configured() -> bool:
    try:
        from core.config import settings

        return bool(settings.linep_enabled and settings.linep_trunk_host)
    except Exception:
        return False


def get_cluster_info() -> Optional[dict[str, Any]]:
    """None when no cluster trunk is configured, else
    {"available", "trunk", "models", "tasks", "reasoning_deltas", "error"?}."""
    global _cache
    if not cluster_configured():
        return None
    with _lock:
        checked_at, ttl, info = _cache
        if info is not None and time.monotonic() - checked_at < ttl:
            return info
        from core.config import settings
        from services.linep_provider import get_linep_provider

        trunk = f"{settings.linep_trunk_host}:{settings.linep_trunk_port}"
        try:
            caps = get_linep_provider()._query_capabilities_sync()
            if caps is None:
                raise RuntimeError("trunk returned no capabilities")
            supported = list(caps.descriptor.supported_models)
            info = {
                "available": True,
                "trunk": trunk,
                "models": [m for m in supported if not m.startswith("task:")],
                "tasks": [m for m in supported if m.startswith("task:")],
                "reasoning_deltas": bool(caps.descriptor.supports_reasoning_deltas),
            }
            ttl = _OK_TTL
        except Exception as e:
            logger.warning("Cluster capabilities unavailable: %s", e)
            info = {"available": False, "trunk": trunk, "models": [], "tasks": [], "error": str(e)[:120]}
            ttl = _FAIL_TTL
        _cache = (time.monotonic(), ttl, info)
        return info
