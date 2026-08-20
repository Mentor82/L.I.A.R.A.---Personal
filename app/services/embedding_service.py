"""
🌌 LIARA 4D Memory - Embedding Service
Dimension 3: Semantic Layer

Generates vector embeddings using sentence-transformers for semantic similarity search.
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Optional, Union
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing semantic embeddings"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedding service with specified model
        
        Args:
            model_name: HuggingFace model name (default: all-MiniLM-L6-v2, 384 dimensions)
        """
        self.model_name = model_name
        self.dimension = 384  # all-MiniLM-L6-v2 produces 384-dim embeddings
        self.version = 1
        self._model = None
        logger.info(f"Initializing EmbeddingService with model: {model_name}")
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the model on first use"""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        return self._model
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * self.dimension
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * self.dimension
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing)
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=len(texts) > 10)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [[0.0] * self.dimension] * len(texts)
    
    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
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
        _embedding_service = EmbeddingService()
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
    
    return {
        'embedding': service.generate_embedding(text),
        'topics': service.extract_keywords(text, top_n=5),
        'intent': service.detect_intent(text),
        'emotion': service.detect_emotion(text),
        'importance': service.calculate_importance(text, context),
        'content_summary': text[:500] if len(text) > 500 else text,
        'embedding_model': service.model_name,
        'embedding_version': service.version,
        'analyzed_at': datetime.utcnow().isoformat()
    }
