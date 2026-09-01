"""
🌌 LIARA 4D Memory - Redis Session Service
Short-term context and session management

Manages conversation context windows and temporary state in Redis.
"""

import os
import redis
import json
import time
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

# Fail closed (issue #7 item 6): no default fallback, same reasoning as
# LIARA_SECRET_KEY in core/security.py - a deployment that omits
# REDIS_PASSWORD, or still has the known development placeholder, would
# otherwise silently run production Redis with a password that's public in
# this repository's git history.
_KNOWN_PLACEHOLDER = "liara_redis_2025"


def _load_redis_password() -> str:
    password = os.getenv("REDIS_PASSWORD")
    if not password:
        raise RuntimeError(
            "REDIS_PASSWORD must be configured (no default fallback) - "
            "generate one with e.g. `openssl rand -hex 32` and set it in "
            ".env, matching Redis's own requirepass"
        )
    if password == _KNOWN_PLACEHOLDER:
        raise RuntimeError(
            "REDIS_PASSWORD is still set to the known development "
            "placeholder - generate a real secret with e.g. "
            "`openssl rand -hex 32` and update Redis's own requirepass to match"
        )
    return password


# add_to_context() lost-update fix (issue #7 item 2): the old Python-side
# GET -> mutate -> SETEX was a classic read-modify-write on one JSON blob -
# two concurrent calls for the same session could both read the same
# starting object, both append their own context item, and whichever
# SETEX ran last would silently overwrite the other's entry and undercount
# message_count/action_count. A Lua script runs atomically on the Redis
# server itself (Redis never interleaves another command mid-script), so
# every add_to_context() call - however many arrive concurrently - is
# guaranteed to see and build on the immediately-preceding one.
_ADD_TO_CONTEXT_LUA = """
local session_key = KEYS[1]
local sessions_set_key = KEYS[2]
local session_id = ARGV[1]
local ttl_seconds = tonumber(ARGV[2])
local context_item_json = ARGV[3]
local content_type = ARGV[4]
local last_activity = ARGV[5]
local max_context = tonumber(ARGV[6])
local default_session_json = ARGV[7]

local raw = redis.call('GET', session_key)
local session
if raw then
    session = cjson.decode(raw)
else
    session = cjson.decode(default_session_json)
end

table.insert(session.context, cjson.decode(context_item_json))
local n = #session.context
if n > max_context then
    local trimmed = {}
    for i = n - max_context + 1, n do
        table.insert(trimmed, session.context[i])
    end
    session.context = trimmed
end

if content_type == 'message' then
    session.message_count = session.message_count + 1
else
    session.action_count = session.action_count + 1
end
session.last_activity = last_activity

local encoded = cjson.encode(session)
redis.call('SETEX', session_key, ttl_seconds, encoded)
redis.call('SADD', sessions_set_key, session_id)
return encoded
"""


class RedisSessionService:
    """Service for managing session context in Redis"""

    def __init__(self, host: str = "localhost", port: int = 6379,
                 password: Optional[str] = None, db: int = 0):
        """
        Initialize Redis connection

        Args:
            host: Redis host
            port: Redis port
            password: Redis password - loaded from REDIS_PASSWORD if not given
            db: Redis database number
        """
        self.host = host
        self.port = port
        self.db = db
        self._client = None
        self._add_to_context_script = None
        self._password = password if password is not None else _load_redis_password()
        logger.info(f"Initializing RedisSessionService: {host}:{port}")
    
    @property
    def client(self) -> redis.Redis:
        """Lazy load Redis client"""
        if self._client is None:
            try:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self._password,
                    db=self.db,
                    decode_responses=True
                )
                # Test connection
                self._client.ping()
                logger.info("Redis client connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._client
    
    def create_session(self, user_id: int, session_id: str) -> Dict:
        """
        Create new session
        
        Args:
            user_id: User ID
            session_id: Unique session identifier
            
        Returns:
            Session data
        """
        session_key = f"session:{user_id}:{session_id}"
        session_data = {
            'user_id': user_id,
            'session_id': session_id,
            'started_at': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat(),
            'message_count': 0,
            'action_count': 0,
            'context': []
        }
        
        # Store in Redis with 24h expiration
        self.client.setex(
            session_key,
            timedelta(hours=24),
            json.dumps(session_data)
        )
        
        # Add to user's active sessions set
        self.client.sadd(f"user:{user_id}:sessions", session_id)
        
        logger.info(f"Created session: {session_id} for user {user_id}")
        return session_data
    
    def get_session(self, user_id: int, session_id: str) -> Optional[Dict]:
        """
        Get session data
        
        Args:
            user_id: User ID
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        session_key = f"session:{user_id}:{session_id}"
        data = self.client.get(session_key)
        
        if data:
            return json.loads(data)
        return None
    
    def update_session_activity(self, user_id: int, session_id: str):
        """Update last activity timestamp for session"""
        session = self.get_session(user_id, session_id)
        if session:
            session['last_activity'] = datetime.utcnow().isoformat()
            session_key = f"session:{user_id}:{session_id}"
            self.client.setex(
                session_key,
                timedelta(hours=24),
                json.dumps(session)
            )
    
    def add_to_context(self, user_id: int, session_id: str,
                       content_type: str, content_id: int,
                       content_summary: str, metadata: Optional[Dict] = None):
        """
        Add item to session context window (race-safe, issue #7 item 2 -
        see _ADD_TO_CONTEXT_LUA above for why this is a Lua script rather
        than a Python-side GET/mutate/SETEX).

        Args:
            user_id: User ID
            session_id: Session ID
            content_type: Type of content
            content_id: Content ID
            content_summary: Brief summary of content
            metadata: Additional metadata
        """
        if self._add_to_context_script is None:
            self._add_to_context_script = self.client.register_script(_ADD_TO_CONTEXT_LUA)

        now_iso = datetime.now(timezone.utc).isoformat()
        context_item = {
            'content_type': content_type,
            'content_id': content_id,
            'content_summary': content_summary,
            'timestamp': now_iso,
            'metadata': metadata or {}
        }
        default_session = {
            'user_id': user_id,
            'session_id': session_id,
            'started_at': now_iso,
            'last_activity': now_iso,
            'message_count': 0,
            'action_count': 0,
            'context': []
        }

        session_key = f"session:{user_id}:{session_id}"
        sessions_set_key = f"user:{user_id}:sessions"
        self._add_to_context_script(
            keys=[session_key, sessions_set_key],
            args=[
                session_id,
                int(timedelta(hours=24).total_seconds()),
                json.dumps(context_item),
                content_type,
                now_iso,
                20,
                json.dumps(default_session),
            ]
        )

        logger.debug(f"Added to context: {content_type}:{content_id}")
    
    def get_context_window(self, user_id: int, session_id: str, 
                          last_n: Optional[int] = None) -> List[Dict]:
        """
        Get context window for session
        
        Args:
            user_id: User ID
            session_id: Session ID
            last_n: Get only last N items (None = all)
            
        Returns:
            List of context items
        """
        session = self.get_session(user_id, session_id)
        if not session:
            return []
        
        context = session.get('context', [])
        if last_n:
            return context[-last_n:]
        return context
    
    def end_session(self, user_id: int, session_id: str):
        """
        End session and mark as completed
        
        Args:
            user_id: User ID
            session_id: Session ID
        """
        session = self.get_session(user_id, session_id)
        if session:
            session['ended_at'] = datetime.utcnow().isoformat()
            
            # Archive session (move to longer-term storage with 7 day expiration)
            archive_key = f"session:archive:{user_id}:{session_id}"
            self.client.setex(
                archive_key,
                timedelta(days=7),
                json.dumps(session)
            )
            
            # Remove from active sessions
            session_key = f"session:{user_id}:{session_id}"
            self.client.delete(session_key)
            self.client.srem(f"user:{user_id}:sessions", session_id)
            
            logger.info(f"Ended and archived session: {session_id}")
    
    def get_active_sessions(self, user_id: int) -> List[str]:
        """
        Get list of active session IDs for user
        
        Args:
            user_id: User ID
            
        Returns:
            List of session IDs
        """
        sessions = self.client.smembers(f"user:{user_id}:sessions")
        return list(sessions) if sessions else []
    
    def cache_embedding(self, text: str, embedding: List[float], ttl: int = 3600):
        """
        Cache embedding for text (avoid recomputation)
        
        Args:
            text: Input text
            embedding: Embedding vector
            ttl: Time to live in seconds (default 1 hour)
        """
        # Use hash of text as key
        import hashlib
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        cache_key = f"embedding:cache:{text_hash}"
        
        self.client.setex(
            cache_key,
            timedelta(seconds=ttl),
            json.dumps(embedding)
        )
    
    def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get cached embedding for text
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector or None if not cached
        """
        import hashlib
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        cache_key = f"embedding:cache:{text_hash}"
        
        data = self.client.get(cache_key)
        if data:
            return json.loads(data)
        return None
    
    def store_user_state(self, user_id: int, state_key: str, state_value: Any, ttl: int = 3600):
        """
        Store temporary user state
        
        Args:
            user_id: User ID
            state_key: State identifier
            state_value: State value (will be JSON serialized)
            ttl: Time to live in seconds
        """
        key = f"user:{user_id}:state:{state_key}"
        self.client.setex(
            key,
            timedelta(seconds=ttl),
            json.dumps(state_value)
        )
    
    def get_user_state(self, user_id: int, state_key: str) -> Optional[Any]:
        """
        Get temporary user state
        
        Args:
            user_id: User ID
            state_key: State identifier
            
        Returns:
            State value or None
        """
        key = f"user:{user_id}:state:{state_key}"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def cache_json(self, key: str, value: Any, ttl: int = 600):
        """
        Generic "cache this JSON-serializable value under this exact key"
        helper - unlike cache_embedding/store_user_state above, this
        doesn't impose its own key namespace or scope (e.g. per-user), so
        callers own their own key convention. Used by search_broker.py to
        cache SearXNG result sets (shared across users for the same query),
        which doesn't fit user_id-scoped keys like store_user_state's.
        """
        self.client.setex(key, timedelta(seconds=ttl), json.dumps(value))

    def get_cached_json(self, key: str) -> Optional[Any]:
        """Read back a value stored via cache_json, or None if absent/expired."""
        data = self.client.get(key)
        return json.loads(data) if data else None

    def increment_counter(self, counter_key: str, amount: int = 1) -> int:
        """
        Increment counter (useful for rate limiting, stats, etc.)
        
        Args:
            counter_key: Counter identifier
            amount: Amount to increment
            
        Returns:
            New counter value
        """
        return self.client.incrby(counter_key, amount)
    
    def get_counter(self, counter_key: str) -> int:
        """Get counter value"""
        value = self.client.get(counter_key)
        return int(value) if value else 0

    def check_sliding_window_rate_limit(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        """
        Sliding-window rate limiter backed by a Redis sorted set - shared
        across every gunicorn worker process, unlike an in-process
        dict+threading.Lock (each worker would keep its own counter, so a
        user's effective limit silently multiplies by the worker count).

        Not perfectly atomic (there's a small check-then-act gap between the
        count read and the write below, so two near-simultaneous requests
        from different workers could in theory both slip through right at
        the limit) - acceptable here since this is light abuse-prevention
        for a single-household assistant, not a security boundary. A Lua
        script would close that gap if it's ever needed.

        Returns True if this request is allowed (and records it), False if
        the caller is currently over the limit.
        """
        now = time.time()
        cutoff = now - window_seconds

        pipe = self.client.pipeline()
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zcard(key)
        _, current_count = pipe.execute()

        if current_count >= max_requests:
            return False

        member = f"{now}:{uuid.uuid4().hex}"
        pipe = self.client.pipeline()
        pipe.zadd(key, {member: now})
        # Safety-net TTL so an abandoned key doesn't linger past its window.
        pipe.expire(key, window_seconds * 2)
        pipe.execute()
        return True

    def get_sliding_window_status(self, key: str, max_requests: int, window_seconds: int = 60) -> Dict:
        """Read-only status for check_sliding_window_rate_limit's key, without recording a request."""
        now = time.time()
        cutoff = now - window_seconds
        self.client.zremrangebyscore(key, 0, cutoff)
        current_count = self.client.zcard(key)
        return {
            'requests_last_minute': current_count,
            'max_requests': max_requests,
            'remaining': max(0, max_requests - current_count),
            'reset_in_seconds': window_seconds if current_count else 0
        }

    def close(self):
        """Close Redis connection"""
        if self._client:
            self._client.close()
            logger.info("Redis connection closed")


# Singleton instance
_redis_service: Optional[RedisSessionService] = None


def get_redis_service() -> RedisSessionService:
    """Get singleton instance of RedisSessionService"""
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisSessionService()
    return _redis_service


def close_redis_service():
    """Close Redis connection"""
    global _redis_service
    if _redis_service:
        _redis_service.close()
        _redis_service = None
