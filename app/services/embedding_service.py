"""
🌌 LIARA 4D Memory - Embedding Service
Dimension 3: Semantic Layer

Generates vector embeddings for semantic similarity search, either in-process
with sentence-transformers or over the LiNeP cluster trunk (EMBED profile).
"""

import numpy as np
from typing import List, Dict, Optional, Union
import itertools
import logging
import math
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

BACKEND_SENTENCE_TRANSFORMERS = "sentence_transformers"
BACKEND_LINEP = "linep"

_linep_request_ids = itertools.count(1)


class EmbeddingError(RuntimeError):
    """No usable embedding could be produced (empty text, model failure, bad vector).

    Raised instead of returning a zero vector: a zero vector has no direction,
    so cosine search ranks it arbitrarily, and once stored in the index it can
    never be told apart from a real embedding (Personal#29 B10 prerequisite).
    """


class EmbeddingService:
    """Service for generating and managing semantic embeddings"""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        dimension: int = 384,
        version: int = 1,
        backend: str = BACKEND_SENTENCE_TRANSFORMERS,
        linep_model: str = "task:embed-bge",
        linep_timeout: float = 10.0,
    ):
        """
        Initialize embedding service with specified model

        Args:
            model_name: model that produces the vectors (stored as embedding_model).
                sentence_transformers: HuggingFace name, loaded in this process.
                linep: the model the trunk must report (e.g. "bge-m3"); vectors
                from any other model are rejected, since they live in another space.
            dimension: expected vector length (all-MiniLM-L6-v2: 384, bge-m3: 1024)
            version: stored as embedding_version
            backend: "sentence_transformers" or "linep"
            linep_model: model id or task sent to the trunk (linep backend only)
            linep_timeout: socket timeout per trunk request in seconds
        """
        if backend not in (BACKEND_SENTENCE_TRANSFORMERS, BACKEND_LINEP):
            raise ValueError(f"unknown embedding backend: {backend}")
        self.model_name = model_name
        self.dimension = dimension
        self.version = version
        self.backend = backend
        self.linep_model = linep_model
        self.linep_timeout = linep_timeout
        self._model = None
        logger.info(f"Initializing EmbeddingService with model: {model_name} "
                    f"({dimension} dims, backend {backend})")

    @property
    def model(self):
        """Lazy load the model on first use (sentence_transformers backend only)"""
        if self.backend != BACKEND_SENTENCE_TRANSFORMERS:
            raise EmbeddingError(f"no in-process model with backend {self.backend}")
        if self._model is None:
            # Imported here so the linep backend never pulls in torch.
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        return self._model

    def _connect_linep(self):
        """Lease-bound, SL1-signed trunk connection; the caller closes it."""
        from core.config import settings
        from services.linep_trunk import TrunkClient, TrunkRoute

        if not (settings.linep_trunk_host and settings.linep_sl1_key_file):
            raise EmbeddingError("linep embedding backend needs LINEP_TRUNK_HOST and LINEP_SL1_KEY_FILE")
        route = TrunkRoute(
            settings.linep_trunk_host,
            settings.linep_trunk_port,
            settings.linep_trunk_control_port,
            settings.linep_sl1_key_file,
        )
        client = TrunkClient(route, timeout=self.linep_timeout)
        try:
            client.connect()
            client.bind()
        except BaseException:
            client.close()
            raise
        return client

    def _embed_linep(self, client, text: str) -> List[float]:
        """One EMBED request on a bound trunk connection."""
        from linep.v0_2.constants import EventType, RuntimeProfile
        from linep.v0_2.envelopes import RequestEnvelope, StreamIdentity

        request = RequestEnvelope(
            stream=StreamIdentity(
                request_id=next(_linep_request_ids),
                execution_id=next(_linep_request_ids),
                output_id=0,
            ),
            profile=RuntimeProfile.EMBED,
            model_id=self.linep_model,
            payload=text,
        )
        result = None
        for event in client.execute_stream(request):
            if event.event_type == EventType.EMBEDDING_RESULT:
                result = event.embedding
            elif event.event_type == EventType.COMPLETED:
                break
            elif event.event_type in (EventType.FAILED, EventType.CANCELLED, EventType.ERROR):
                message = event.error.message if event.error and event.error.message else event.event_type.name
                raise EmbeddingError(f"LiNeP embedding failed: {message}")
        if result is None:
            raise EmbeddingError("LiNeP stream ended without an embedding")
        # A task may resolve to another model: its vectors are in another space.
        if result.space.model_id != self.model_name:
            raise EmbeddingError(
                f"LiNeP served {result.space.model_id!r}, expected {self.model_name!r}")
        return list(result.vector)

    def _encode_linep(self, texts: List[str]) -> List[List[float]]:
        """All texts over one trunk connection (requests run one after another)."""
        try:
            client = self._connect_linep()
            try:
                return [self._embed_linep(client, t) for t in texts]
            finally:
                client.close()
        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(f"LiNeP transport failed: {e}") from e

    def _encode(self, texts: List[str]) -> List[List[float]]:
        if self.backend == BACKEND_LINEP:
            return self._encode_linep(texts)
        return self.model.encode(texts, convert_to_numpy=True, show_progress_bar=len(texts) > 10).tolist()

    def _validate(self, vector: List[float]) -> List[float]:
        """Dimension, finiteness and non-zero norm, or EmbeddingError."""
        if len(vector) != self.dimension:
            raise EmbeddingError(f"embedding has {len(vector)} dims, expected {self.dimension}")
        if not all(math.isfinite(x) for x in vector):
            raise EmbeddingError("embedding contains NaN/Infinity")
        if not any(vector):
            raise EmbeddingError("embedding is the zero vector")
        return vector

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            EmbeddingError: empty text, model failure, or an unusable vector
        """
        if not text or not text.strip():
            raise EmbeddingError("empty text")

        try:
            return self._validate(self._encode([text])[0])
        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise EmbeddingError(f"embedding failed: {e}") from e
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing)
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: model failure or any unusable vector in the batch
        """
        if not texts:
            return []
        if any(not t or not t.strip() for t in texts):
            raise EmbeddingError("empty text in batch")

        try:
            return [self._validate(v) for v in self._encode(texts)]
        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise EmbeddingError(f"batch embedding failed: {e}") from e
    
    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (-1 to 1); 0.0 if either vector is zero

        Raises:
            ValueError: different lengths (vectors from different models, e.g.
                384-dim MiniLM next to 1024-dim bge-m3) or non-numeric input.
                Returning 0.0 here used to drop such vectors from every search
                without a trace; callers filter by dimension first.
        """
        vec1 = np.asarray(embedding1, dtype=float)
        vec2 = np.asarray(embedding2, dtype=float)
        if vec1.shape != vec2.shape:
            raise ValueError(f"embedding dimensions differ: {vec1.shape} vs {vec2.shape}")

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """
        Simple keyword extraction (can be enhanced with NLP libraries)
        
        Args:
            text: Input text
            top_n: Number of top keywords to extract
            
        Returns:
            List of keywords
        """
        # Simple implementation - can be enhanced with TF-IDF, RAKE, etc.
        words = text.lower().split()
        # Filter short words and common stop words
        stop_words = {'der', 'die', 'das', 'und', 'oder', 'aber', 'ich', 'du', 'er', 'sie', 'es',
                      'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of'}
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        
        # Count frequency
        from collections import Counter
        word_freq = Counter(keywords)
        
        return [word for word, _ in word_freq.most_common(top_n)]
    
    def detect_intent(self, text: str) -> str:
        """
        Detect intent from text (simple rule-based, can be enhanced with ML)
        
        Args:
            text: Input text
            
        Returns:
            Intent category
        """
        text_lower = text.lower()
        
        # Web Search Intents (NEW)
        # Weather - check for weather keywords OR location + "wie ist"
        if (any(word in text_lower for word in ['wetter', 'weather', 'temperatur', 'temperature', 'grad', 'celsius', 'regen', 'schnee', 'sonne']) or
            ('wie ist' in text_lower and any(city in text_lower for city in ['berlin', 'münchen', 'hamburg', 'köln', 'frankfurt', 'stuttgart', 'düsseldorf', 'dortmund', 'essen', 'leipzig', 'bremen', 'dresden', 'hannover']))):
            return 'SEARCH_WEATHER'
        
        if any(word in text_lower for word in ['news', 'nachrichten', 'aktuell', 'schlagzeilen']):
            return 'SEARCH_NEWS'
        
        if any(word in text_lower for word in ['wikipedia', 'was ist', 'what is', 'erkläre', 'explain', 'definition']):
            return 'SEARCH_WIKI'
        
        if any(word in text_lower for word in ['google', 'such im internet', 'search online', 'find online']):
            return 'SEARCH_WEB'
        
        # Task-related
        if any(word in text_lower for word in ['erstell', 'create', 'neue', 'new', 'hinzufüg', 'add']):
            if 'task' in text_lower or 'aufgabe' in text_lower:
                return 'CREATE_TASK'
            elif 'note' in text_lower or 'notiz' in text_lower:
                return 'CREATE_NOTE'
            elif 'termin' in text_lower or 'event' in text_lower:
                return 'CREATE_EVENT'
            return 'CREATE'
        
        # Search/Retrieve
        if any(word in text_lower for word in ['zeig', 'show', 'such', 'search', 'find', 'wo ist']):
            return 'SEARCH'
        
        # Delete
        if any(word in text_lower for word in ['lösch', 'delete', 'entfern', 'remove']):
            return 'DELETE'
        
        # Update
        if any(word in text_lower for word in ['änder', 'update', 'modify', 'edit', 'bearbeit']):
            return 'UPDATE'
        
        # Reflection/Analysis
        if any(word in text_lower for word in ['wie war', 'how was', 'analyse', 'überblick', 'overview']):
            return 'REFLECT'
        
        # Chat/Conversation
        return 'CHAT'

    
    def detect_emotion(self, text: str) -> str:
        """
        Simple emotion detection (can be enhanced with sentiment analysis models)
        
        Args:
            text: Input text
            
        Returns:
            Detected emotion
        """
        text_lower = text.lower()
        
        # Positive emotions
        if any(word in text_lower for word in ['super', 'great', 'toll', 'fantastisch', 'happy', 'freue']):
            return 'happy'
        
        # Negative emotions
        if any(word in text_lower for word in ['stress', 'müde', 'tired', 'traurig', 'sad', 'schlecht']):
            return 'stressed'
        
        # Focused/productive
        if any(word in text_lower for word in ['fokus', 'focus', 'konzentrier', 'arbeit', 'work']):
            return 'focused'
        
        # Neutral
        return 'neutral'
    
    def calculate_importance(self, text: str, context: Optional[Dict] = None) -> int:
        """
        Calculate importance score (1-10) based on text and context
        
        Args:
            text: Input text
            context: Additional context (user history, current mood, etc.)
            
        Returns:
            Importance score (1-10)
        """
        score = 5  # Default medium importance
        text_lower = text.lower()
        
        # High importance indicators
        if any(word in text_lower for word in ['wichtig', 'urgent', 'dringend', 'deadline', 'asap', '!!!', 'kritisch']):
            score += 3
        
        # Meeting/event indicators
        if any(word in text_lower for word in ['meeting', 'termin', 'konferenz', 'präsentation']):
            score += 2
        
        # Long-term planning
        if any(word in text_lower for word in ['projekt', 'project', 'ziel', 'goal', 'plan']):
            score += 1
        
        # Low importance indicators
        if any(word in text_lower for word in ['vielleicht', 'maybe', 'eventuell', 'später', 'sometime']):
            score -= 2
        
        # Clamp to 1-10 range
        return max(1, min(10, score))


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get singleton instance of EmbeddingService"""
    global _embedding_service
    if _embedding_service is None:
        from core.config import settings

        _embedding_service = EmbeddingService(
            model_name=settings.embedding_model,
            dimension=settings.embedding_dimension,
            version=settings.embedding_version,
            backend=settings.embedding_backend,
            linep_model=settings.embedding_linep_model,
            linep_timeout=settings.embedding_linep_timeout_seconds,
        )
    return _embedding_service


# Convenience functions
def generate_embedding(text: str) -> List[float]:
    """Generate embedding for text"""
    return get_embedding_service().generate_embedding(text)


def analyze_content(text: str, context: Optional[Dict] = None) -> Dict:
    """
    Analyze text content and extract all semantic metadata
    
    Returns:
        Dict with embedding, topics, intent, emotion, importance
    """
    service = get_embedding_service()

    # No embedding is better than a bogus one: callers store NULL (the rest of
    # the metadata is rule-based and still valid) instead of a zero vector.
    try:
        embedding = service.generate_embedding(text)
    except EmbeddingError as e:
        logger.warning("No embedding for content (%s) - storing metadata without one", e)
        embedding = None

    return {
        'embedding': embedding,
        'topics': service.extract_keywords(text, top_n=5),
        'intent': service.detect_intent(text),
        'emotion': service.detect_emotion(text),
        'importance': service.calculate_importance(text, context),
        'content_summary': text[:500] if len(text) > 500 else text,
        'embedding_model': service.model_name,
        'embedding_version': service.version,
        'analyzed_at': datetime.now(timezone.utc).isoformat()
    }
