"""
🌌 LIARA 4D Memory - Integration Helper
Convenience functions to integrate 4D Memory into existing APIs

UPDATED: 2025-12-04
- Added auto-concept extraction from messages
- Added semantic context retrieval
- Added embedding-based similarity search
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import re
from collections import Counter

from services.embedding_service import get_embedding_service, analyze_content
from services.neo4j_service import get_neo4j_service
from services.redis_service import get_redis_service

logger = logging.getLogger(__name__)


# ============================================================================
# CONCEPT EXTRACTION
# ============================================================================

def extract_concepts(text: str, min_length: int = 4) -> List[str]:
    """
    Extrahiert Konzepte aus Text (Substantive, wichtige Terme)
    
    Args:
        text: Input-Text
        min_length: Minimale Wortlänge
        
    Returns:
        Liste von Konzepten
    """
    # Stopwords (DE + EN)
    stopwords = {
        # Deutsch
        'aber', 'als', 'auch', 'bei', 'bin', 'bis', 'das', 'dass', 'dem', 'den',
        'der', 'des', 'die', 'dies', 'diese', 'diesem', 'diesen', 'dieser', 'dieses',
        'doch', 'ein', 'eine', 'einem', 'einen', 'einer', 'eines', 'für', 'hab', 'habe',
        'haben', 'hat', 'hier', 'ich', 'ihr', 'ihre', 'ihrem', 'ihren', 'ihrer', 'ihres',
        'im', 'in', 'ist', 'kann', 'mein', 'meine', 'meinem', 'meinen', 'meiner', 'meines',
        'mit', 'nicht', 'oder', 'sein', 'seine', 'seinem', 'seinen', 'seiner', 'seines',
        'sich', 'sie', 'sind', 'über', 'und', 'vom', 'von', 'vor', 'war', 'was', 'werden',
        'wie', 'wird', 'wurde', 'wurden', 'zum', 'zur',
        # Englisch
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'been', 'but', 'by', 'for', 'from',
        'had', 'has', 'have', 'he', 'her', 'here', 'his', 'how', 'i', 'if', 'in', 'is',
        'it', 'its', 'me', 'my', 'of', 'on', 'or', 'our', 'she', 'that', 'the', 'their',
        'them', 'there', 'these', 'they', 'this', 'to', 'was', 'we', 'what', 'when',
        'where', 'which', 'who', 'will', 'with', 'you', 'your'
    }
    
    # Text normalisieren
    text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
    words = text_clean.split()
    
    # Filtern: Länge + Stopwords
    concepts = [
        word for word in words 
        if len(word) >= min_length and word not in stopwords
    ]
    
    # Deduplizieren aber Häufigkeit behalten (für Wichtigkeit)
    concept_freq = Counter(concepts)
    
    # Sortiere nach Häufigkeit, nehme unique
    unique_concepts = list(dict.fromkeys(
        [word for word, _ in concept_freq.most_common()]
    ))
    
    logger.debug(f"Extracted {len(unique_concepts)} concepts from text")
    return unique_concepts


def store_in_4d_memory(
    db: Session,
    user_id: int,
    content_type: str,
    content_id: int,
    content_text: str,
    session_id: Optional[str] = None,
    mood: Optional[str] = None,
    energy_level: Optional[int] = None,
    additional_context: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Store content in all 4 dimensions of memory
    
    Args:
        db: Database session
        user_id: User ID
        content_type: Type of content (message, task, note, event)
        content_id: ID of the content
        content_text: Text content to analyze
        session_id: Optional session ID for context tracking
        mood: Optional mood at time of creation
        energy_level: Optional energy level (1-10)
        additional_context: Optional additional context for analysis
        
    Returns:
        Dict with created entries
    """
    result = {
        'temporal': None,
        'semantic': None,
        'neo4j': None,
        'redis': None
    }
    
    try:
        # DIMENSION 3: Semantic Analysis & Embedding
        analysis = analyze_content(content_text, additional_context)
        
        # Store in semantic_metadata
        semantic_sql = text("""
        INSERT INTO semantic_metadata 
            (user_id, content_type, content_id, embedding, topics, intent, 
             emotion, importance, content_summary, embedding_model, embedding_version)
        VALUES 
            (:user_id, :content_type, :content_id, CAST(:embedding AS vector), :topics, :intent,
             :emotion, :importance, :content_summary, :model, :version)
        ON CONFLICT (user_id, content_type, content_id) 
        DO UPDATE SET
            embedding = EXCLUDED.embedding,
            topics = EXCLUDED.topics,
            intent = EXCLUDED.intent,
            emotion = EXCLUDED.emotion,
            importance = EXCLUDED.importance,
            content_summary = EXCLUDED.content_summary,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """)
        
        semantic_result = db.execute(semantic_sql, {
            'user_id': user_id,
            'content_type': content_type,
            'content_id': content_id,
            'embedding': str(analysis['embedding']),
            'topics': analysis['topics'],
            'intent': analysis['intent'],
            'emotion': analysis['emotion'],
            'importance': analysis['importance'],
            'content_summary': analysis['content_summary'],
            'model': analysis['embedding_model'],
            'version': analysis['embedding_version']
        })
        db.commit()
        result['semantic'] = semantic_result.scalar()
        
        # DIMENSION 2: Temporal Tracking
        sequence_sql = text("SELECT get_next_temporal_sequence() as seq")
        sequence_num = db.execute(sequence_sql).scalar()
        
        temporal_sql = text("""
        INSERT INTO temporal_index
            (user_id, content_type, content_id, sequence_number, session_id, 
             mood_at_time, energy_level)
        VALUES
            (:user_id, :content_type, :content_id, :sequence_number, :session_id,
             :mood, :energy)
        ON CONFLICT (user_id, content_type, content_id)
        DO UPDATE SET
            sequence_number = EXCLUDED.sequence_number,
            session_id = EXCLUDED.session_id,
            mood_at_time = EXCLUDED.mood_at_time,
            energy_level = EXCLUDED.energy_level
        RETURNING id
        """)
        
        temporal_result = db.execute(temporal_sql, {
            'user_id': user_id,
            'content_type': content_type,
            'content_id': content_id,
            'sequence_number': sequence_num,
            'session_id': session_id,
            'mood': mood,
            'energy': energy_level
        })
        db.commit()
        result['temporal'] = temporal_result.scalar()
        
        # DIMENSION 4: Neo4j Graph
        try:
            neo4j = get_neo4j_service()
            
            # Create content node
            neo4j.create_content_node(
                content_type=content_type.capitalize(),
                content_id=content_id,
                user_id=user_id,
                properties={
                    'content_summary': analysis['content_summary'],
                    'intent': analysis['intent'],
                    'emotion': analysis['emotion'],
                    'importance': analysis['importance'],
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            result['neo4j'] = 'created'
            
            # If mood is provided, create mood node and link
            if mood and energy_level:
                timestamp = datetime.utcnow().isoformat()
                neo4j.create_mood_node(
                    user_id=user_id,
                    timestamp=timestamp,
                    mood=mood,
                    energy_level=energy_level
                )
                neo4j.link_content_to_mood(
                    content_type=content_type.capitalize(),
                    content_id=content_id,
                    mood_timestamp=timestamp,
                    user_id=user_id,
                    caused_by=False  # Mood influenced content creation
                )
                
        except Exception as e:
            logger.warning(f"Neo4j storage failed: {e}")
            result['neo4j'] = f'error: {str(e)}'
        
        # Redis: Add to session context if session_id provided
        if session_id:
            try:
                redis = get_redis_service()
                redis.add_to_context(
                    user_id=user_id,
                    session_id=session_id,
                    content_type=content_type,
                    content_id=content_id,
                    content_summary=analysis['content_summary'],
                    metadata={
                        'intent': analysis['intent'],
                        'emotion': analysis['emotion'],
                        'topics': analysis['topics']
                    }
                )
                result['redis'] = 'added_to_context'
            except Exception as e:
                logger.warning(f"Redis context update failed: {e}")
                result['redis'] = f'error: {str(e)}'
        
        logger.info(f"Stored {content_type}:{content_id} in 4D Memory")
        return result
        
    except Exception as e:
        logger.error(f"4D Memory storage failed: {e}")
        db.rollback()
        raise


def search_semantic_memory(
    db: Session,
    user_id: int,
    query: str,
    content_types: Optional[list] = None,
    limit: int = 10,
    min_similarity: float = 0.5
) -> list:
    """
    Search semantic memory for similar content
    
    Args:
        db: Database session
        user_id: User ID
        query: Search query
        content_types: Optional filter by content types
        limit: Max results
        min_similarity: Minimum similarity threshold
        
    Returns:
        List of similar content with metadata
    """
    embedding_service = get_embedding_service()
    query_embedding = embedding_service.generate_embedding(query)
    
    content_filter = ""
    if content_types:
        types_str = "','".join(content_types)
        content_filter = f"AND content_type IN ('{types_str}')"
    
    sql = text(f"""
    SELECT 
        content_type,
        content_id,
        1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity,
        content_summary,
        topics,
        intent,
        emotion,
        importance,
        created_at
    FROM semantic_metadata
    WHERE user_id = :user_id
        {content_filter}
        AND embedding IS NOT NULL
        AND 1 - (embedding <=> CAST(:query_embedding AS vector)) >= :min_similarity
    ORDER BY embedding <=> CAST(:query_embedding AS vector)
    LIMIT :limit
    """)
    
    result = db.execute(sql, {
        'user_id': user_id,
        'query_embedding': str(query_embedding),
        'min_similarity': min_similarity,
        'limit': limit
    })
    
    return [dict(row._mapping) for row in result]


def get_temporal_context(
    db: Session,
    user_id: int,
    limit: int = 20,
    content_types: Optional[list] = None
) -> list:
    """
    Get recent temporal context for user
    
    Args:
        db: Database session
        user_id: User ID
        limit: Number of recent items
        content_types: Optional filter by types
        
    Returns:
        List of recent content with temporal metadata
    """
    content_filter = ""
    if content_types:
        types_str = "','".join(content_types)
        content_filter = f"AND t.content_type IN ('{types_str}')"
    
    sql = text(f"""
    SELECT 
        t.content_type,
        t.content_id,
        t.timestamp,
        t.sequence_number,
        t.mood_at_time,
        t.energy_level,
        s.intent,
        s.emotion,
        s.content_summary,
        s.topics
    FROM temporal_index t
    LEFT JOIN semantic_metadata s ON (
        t.user_id = s.user_id 
        AND t.content_type = s.content_type 
        AND t.content_id = s.content_id
    )
    WHERE t.user_id = :user_id
        {content_filter}
    ORDER BY t.sequence_number DESC
    LIMIT :limit
    """)
    
    result = db.execute(sql, {'user_id': user_id, 'limit': limit})
    return [dict(row._mapping) for row in result]


def create_relationship(
    db: Session,
    user_id: int,
    source_type: str,
    source_id: int,
    target_type: str,
    target_id: int,
    relation_type: str,
    strength: float = 0.5,
    discovery_method: str = 'user_explicit'
):
    """
    Create relationship between two content items
    
    Stores in both PostgreSQL and Neo4j
    """
    # PostgreSQL
    sql = text("""
    INSERT INTO content_relations
        (user_id, source_type, source_id, target_type, target_id, 
         relation_type, strength, discovery_method)
    VALUES
        (:user_id, :source_type, :source_id, :target_type, :target_id,
         :relation_type, :strength, :discovery_method)
    ON CONFLICT (user_id, source_type, source_id, target_type, target_id, relation_type)
    DO UPDATE SET
        strength = EXCLUDED.strength,
        discovery_method = EXCLUDED.discovery_method
    RETURNING id
    """)
    
    result = db.execute(sql, {
        'user_id': user_id,
        'source_type': source_type,
        'source_id': source_id,
        'target_type': target_type,
        'target_id': target_id,
        'relation_type': relation_type,
        'strength': strength,
        'discovery_method': discovery_method
    })
    db.commit()
    relation_id = result.scalar()
    
    # Neo4j
    try:
        neo4j = get_neo4j_service()
        neo4j.create_relationship(
            source_type=source_type.capitalize(),
            source_id=source_id,
            target_type=target_type.capitalize(),
            target_id=target_id,
            relation_type=relation_type,
            user_id=user_id,
            properties={'strength': strength, 'discovery_method': discovery_method}
        )
        
        # Mark as synced
        sync_sql = text("""
        UPDATE content_relations 
        SET synced_to_neo4j = true 
        WHERE id = :id
        """)
        db.execute(sync_sql, {'id': relation_id})
        db.commit()
        
    except Exception as e:
        logger.warning(f"Neo4j relationship creation failed: {e}")
    
    return relation_id


# ============================================================================
# AUTO-CONCEPT STORAGE (NEW)
# ============================================================================

def store_message_with_concepts(
    user_id: int,
    message_id: int,
    content: str,
    role: str,
    timestamp: Optional[datetime] = None
) -> Dict:
    """
    Speichert Message in Neo4j mit auto-extrahierten Concepts
    
    Args:
        user_id: User ID
        message_id: Message ID (from PostgreSQL)
        content: Message-Content
        role: 'user' | 'assistant'
        timestamp: Message Timestamp
        
    Returns:
        Dict mit Statistiken
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    neo4j = get_neo4j_service()
    embedding_service = get_embedding_service()
    
    # 1. Message Node erstellen
    with neo4j.driver.session() as session:
        # User sicherstellen
        session.run("""
            MERGE (u:User {user_id: $user_id})
            ON CREATE SET u.created_at = datetime()
            SET u.last_active = datetime()
        """, user_id=user_id)
        
        # Message Node
        session.run("""
            MATCH (u:User {user_id: $user_id})
            CREATE (m:Message {
                user_id: $user_id,
                message_id: $message_id,
                content: $content,
                role: $role,
                timestamp: datetime($timestamp),
                created_at: datetime()
            })
            MERGE (u)-[:SENT]->(m)
        """, 
            user_id=user_id,
            message_id=message_id,
            content=content[:500],
            role=role,
            timestamp=timestamp.isoformat()
        )
    
    # 2. Concepts extrahieren
    concepts = extract_concepts(content)
    
    # 3. Embeddings generieren (batch)
    concept_embeddings = {}
    if concepts:
        embeddings = embedding_service.generate_embeddings_batch(concepts)
        concept_embeddings = dict(zip(concepts, embeddings))
    
    # 4. Concept Nodes erstellen + Verbinden
    stored_concepts = 0
    for concept, embedding in concept_embeddings.items():
        try:
            with neo4j.driver.session() as session:
                session.run("""
                    MATCH (m:Message {user_id: $user_id, message_id: $message_id})
                    MERGE (c:Concept {text: $concept, user_id: $user_id})
                    ON CREATE SET 
                        c.embedding = $embedding,
                        c.created_at = datetime(),
                        c.mention_count = 1
                    ON MATCH SET 
                        c.mention_count = c.mention_count + 1,
                        c.last_mentioned = datetime()
                    MERGE (m)-[r:CONTAINS]->(c)
                    ON CREATE SET r.created_at = datetime()
                """,
                    user_id=user_id,
                    message_id=message_id,
                    concept=concept,
                    embedding=embedding
                )
                stored_concepts += 1
        except Exception as e:
            logger.warning(f"Failed to store concept '{concept}': {e}")
    
    stats = {
        'message_id': message_id,
        'concepts_extracted': len(concepts),
        'concepts_stored': stored_concepts
    }
    
    logger.info(f"Stored message {message_id} with {stored_concepts} concepts")
    return stats


def get_relevant_context(
    user_id: int,
    query_text: str,
    limit: int = 5,
    min_similarity: float = 0.6
) -> List[Dict]:
    """
    Findet semantisch ähnliche Concepts für Context-Injection
    
    Args:
        user_id: User ID
        query_text: Query-Text (neue Message)
        limit: Max Anzahl Ergebnisse
        min_similarity: Min Cosine-Similarity
        
    Returns:
        Liste von relevanten Concepts mit Messages
    """
    neo4j = get_neo4j_service()
    embedding_service = get_embedding_service()
    
    # 1. Query Embedding generieren
    query_embedding = embedding_service.generate_embedding(query_text)
    
    # 2. Alle Concepts des Users abrufen
    with neo4j.driver.session() as session:
        result = session.run("""
            MATCH (c:Concept {user_id: $user_id})
            WHERE c.embedding IS NOT NULL
            RETURN c.text as concept, c.embedding as embedding, 
                   c.mention_count as mentions, c.created_at as created_at
            LIMIT 1000
        """, user_id=user_id)
        
        concepts = []
        for record in result:
            if record['embedding']:
                concepts.append({
                    'concept': record['concept'],
                    'embedding': record['embedding'],
                    'mentions': record['mentions'],
                    'created_at': record['created_at']
                })
    
    # 3. Similarity berechnen
    concept_similarities = []
    for concept_data in concepts:
        similarity = embedding_service.cosine_similarity(
            query_embedding,
            concept_data['embedding']
        )
        
        if similarity >= min_similarity:
            concept_similarities.append({
                'concept': concept_data['concept'],
                'similarity': similarity,
                'mentions': concept_data['mentions'],
                'created_at': concept_data['created_at']
            })
    
    # 4. Sortiere nach Similarity (mit mention_count als Tiebreaker)
    concept_similarities.sort(
        key=lambda x: (x['similarity'], x['mentions']),
        reverse=True
    )
    
    top_concepts = concept_similarities[:limit]
    
    # 5. Hole zugehörige Messages für Context
    context_items = []
    for concept_item in top_concepts:
        with neo4j.driver.session() as session:
            result = session.run("""
                MATCH (c:Concept {text: $concept, user_id: $user_id})<-[:CONTAINS]-(m:Message)
                RETURN m.message_id as message_id, m.content as content, 
                       m.role as role, m.timestamp as timestamp
                ORDER BY m.timestamp DESC
                LIMIT 3
            """, concept=concept_item['concept'], user_id=user_id)
            
            messages = []
            for record in result:
                messages.append({
                    'message_id': record['message_id'],
                    'content': record['content'],
                    'role': record['role'],
                    'timestamp': str(record['timestamp'])
                })
            
            context_items.append({
                'concept': concept_item['concept'],
                'similarity': concept_item['similarity'],
                'mentions': concept_item['mentions'],
                'related_messages': messages
            })
    
    logger.info(f"Found {len(context_items)} relevant concepts for context injection")
    return context_items


def get_user_memory_stats(user_id: int) -> Dict:
    """Holt Memory-Statistiken für User aus Neo4j"""
    neo4j = get_neo4j_service()
    
    with neo4j.driver.session() as session:
        result = session.run("""
            MATCH (u:User {user_id: $user_id})
            OPTIONAL MATCH (u)-[:SENT]->(m:Message)
            OPTIONAL MATCH (u)-[:CREATED]->(t:Task)
            OPTIONAL MATCH (u)-[:CREATED]->(n:Note)
            OPTIONAL MATCH (u)-[:CREATED]->(e:Event)
            OPTIONAL MATCH (c:Concept {user_id: $user_id})
            RETURN 
                count(DISTINCT m) as message_count,
                count(DISTINCT t) as task_count,
                count(DISTINCT n) as note_count,
                count(DISTINCT e) as event_count,
                count(DISTINCT c) as concept_count
        """, user_id=user_id)
        
        record = result.single()
        if record:
            return {
                'user_id': user_id,
                'messages': record['message_count'],
                'tasks': record['task_count'],
                'notes': record['note_count'],
                'events': record['event_count'],
                'concepts': record['concept_count']
            }
        return {}
