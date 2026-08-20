"""
🌌 LIARA 4D Memory - Redis Session Service
Short-term context and session management

Manages conversation context windows and temporary state in Redis.
"""

import redis
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RedisSessionService:
    """Service for managing session context in Redis"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, 
                 password: str = "liara_redis_2025", db: int = 0):
        """
        Initialize Redis connection
        
        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            db: Redis database number
        """
        self.host = host
        self.port = port
        self.db = db
        self._client = None
        self._password = password
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
        Add item to session context window
        
        Args:
            user_id: User ID
            session_id: Session ID
            content_type: Type of content
            content_id: Content ID
            content_summary: Brief summary of content
            metadata: Additional metadata
        """
        session = self.get_session(user_id, session_id)
        if not session:
            session = self.create_session(user_id, session_id)
        
        context_item = {
            'content_type': content_type,
            'content_id': content_id,
            'content_summary': content_summary,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        session['context'].append(context_item)
        
        # Keep only last 20 items in context window
        if len(session['context']) > 20:
            session['context'] = session['context'][-20:]
        
        # Update message/action count
        if content_type == 'message':
            session['message_count'] += 1
        else:
            session['action_count'] += 1
        
        session['last_activity'] = datetime.utcnow().isoformat()
        
        session_key = f"session:{user_id}:{session_id}"
        self.client.setex(
            session_key,
            timedelta(hours=24),
            json.dumps(session)
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
