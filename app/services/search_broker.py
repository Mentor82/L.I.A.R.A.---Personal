"""
🔎 SearchBroker - general web search via self-hosted SearXNG

Issue #4 phase 1: a provider-neutral abstraction so the rest of Liara never
has to know it's talking to SearXNG specifically. web_search_service.py's
DuckDuckGo Instant Answer / Wikipedia paths stay exactly as they are (quick
facts/definitions) - this is the "real search discovery" layer for
research-style queries that need multiple actual sources, not a single
instant-answer snippet.

SearXNG runs in Docker, bound to 127.0.0.1 only (see docker-compose.yml) -
never reachable from the LAN/internet, only from this process.
"""
import hashlib
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse

import httpx

from services.redis_service import get_redis_service

logger = logging.getLogger(__name__)

SEARXNG_URL = "http://127.0.0.1:8080/search"
CACHE_TTL_SECONDS = 600  # short-lived: cheap dedup for repeat queries, not a freshness/policy layer


class SearchBroker:
    """Normalizes SearXNG results into a provider-independent shape."""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=8.0)

    async def search(self, query: str, language: str = "de", limit: int = 10) -> List[Dict]:
        """
        Returns a list of normalized results, or an empty list if SearXNG
        is unreachable/errors/returns nothing - callers should treat "no
        results" and "search engine down" the same way (answer honestly
        that nothing was found), not crash the whole tool call over it.
        """
        cache_key = f"search:web:{hashlib.sha256(query.encode()).hexdigest()}:{language}"
        try:
            cached = get_redis_service().get_cached_json(cache_key)
            if cached is not None:
                return cached
        except Exception as e:
            logger.warning(f"Search cache read failed (continuing without it): {e}")

        try:
            response = await self._client.get(
                SEARXNG_URL,
                params={"q": query, "format": "json", "language": language}
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.warning(f"SearXNG search failed for '{query}': {e}")
            return []

        results = []
        for rank, item in enumerate(data.get("results", [])[:limit], start=1):
            url = item.get("url", "")
            results.append({
                "title": item.get("title", ""),
                "url": url,
                "domain": urlparse(url).netloc,
                "snippet": item.get("content", ""),
                "published_at": item.get("publishedDate"),
                "rank": rank,
                "engine": item.get("engine", "")
            })

        try:
            get_redis_service().cache_json(cache_key, results, ttl=CACHE_TTL_SECONDS)
        except Exception as e:
            logger.warning(f"Search cache write failed (non-fatal): {e}")

        return results


_search_broker_instance: Optional[SearchBroker] = None


def get_search_broker() -> SearchBroker:
    """Factory für SearchBroker (Singleton)"""
    global _search_broker_instance
    if _search_broker_instance is None:
        _search_broker_instance = SearchBroker()
    return _search_broker_instance
