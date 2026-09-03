"""
🌌 LIARA 4D Memory - Integration Helper
Convenience functions to integrate 4D Memory into existing APIs

UPDATED: 2025-12-04
- Added auto-concept extraction from messages
- Added semantic context retrieval
- Added embedding-based similarity search
"""

from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import logging
import re
from collections import Counter

from services.embedding_service import get_embedding_service, analyze_content
from services.neo4j_service import get_neo4j_service
from services.redis_service import get_redis_service

logger = logging.getLogger(__name__)


# Nouns that are grammatically real concepts (spaCy correctly tags them
# NOUN/PROPN) but carry almost no topic-specific signal - they show up in
# nearly every conversation regardless of subject ("im Jahr...", "diese
# Sache...", "im Moment..."), so their embeddings sit in a generically
# "temporal/generic" region of embedding space that scores misleadingly
# high cosine similarity against almost any other short phrase. Observed
# live: the concept "jahr" (from an old, unrelated space-travel message)
# came back at 0.68 similarity for a completely unrelated "guten Morgen,
# Tagesüberblick" message and got injected into the model's context as if
# it were a relevant memory. Excluded at BOTH extraction (stop creating new
# noise going forward) and retrieval (existing Concept nodes already in the
# graph stay unmatched too) rather than deleting the existing nodes - they
# might still be harmless for other, non-injection purposes (mention
# counts, graph stats).
GENERIC_LOW_SIGNAL_CONCEPTS = {
    'jahr', 'jahre', 'jahren', 'monat', 'monate', 'monaten', 'woche', 'wochen',
    'tag', 'tage', 'tagen', 'zeit', 'zeiten', 'moment', 'momente', 'mal',
    'sache', 'sachen', 'ding', 'dinge', 'teil', 'teile', 'seite', 'seiten',
    'punkt', 'punkte', 'frage', 'fragen', 'antwort', 'antworten', 'art',
    'weise', 'mensch', 'menschen', 'leben', 'welt', 'weg', 'wege',
}


# ============================================================================
# CONCEPT EXTRACTION
# ============================================================================

# Lazy-loaded singleton: spaCy's German model takes a noticeable moment to
# load (~1-2s), so it's loaded once per process, not per call. `parser`/`ner`
# are disabled since concept extraction only needs POS tags + lemmas, not
# dependency trees or named-entity spans - skipping them roughly halves
# per-message processing time.
_nlp_de = None
_nlp_de_unavailable = False


def _get_spacy_nlp():
    global _nlp_de, _nlp_de_unavailable
    if _nlp_de is not None or _nlp_de_unavailable:
        return _nlp_de
    try:
        import spacy
        _nlp_de = spacy.load("de_core_news_sm", disable=["parser", "ner"])
        logger.info("Loaded spaCy de_core_news_sm for concept extraction")
    except Exception as e:
        # Missing model/package shouldn't break chat - degrade to the naive
        # extractor below instead of raising on every single message.
        logger.warning(f"spaCy German model unavailable, falling back to naive concept extraction: {e}")
        _nlp_de_unavailable = True
    return _nlp_de


def extract_concepts(text: str, min_length: int = 4) -> List[str]:
    """
    Extrahiert Konzepte aus Text - echte Substantive/Eigennamen via
    Wortart-Erkennung (spaCy), nicht nur "Wort ist lang genug und kein
    Stoppwort". Die alte längen+Stoppwort-Heuristik hatte kein Konzept von
    Grammatik: 2.-Person-Pronomen, Begrüßungen, Adverbien und konjugierte
    Verbformen landeten genauso als "Concept" im Graph wie echte Substantive,
    weil eine Stoppwortliste jede einzelne Flexionsform separat auflisten
    müsste, um das zu verhindern.

    Args:
        text: Input-Text
        min_length: Minimale Wortlänge (nach Lemmatisierung)

    Returns:
        Liste von Konzepten (lemmatisiert, häufigste zuerst)
    """
    nlp = _get_spacy_nlp()
    if nlp is None:
        return _extract_concepts_naive(text, min_length)

    doc = nlp(text)
    concepts = [
        token.lemma_.lower() for token in doc
        if token.pos_ in ("NOUN", "PROPN")
        and token.is_alpha
        and len(token.lemma_) >= min_length
        and token.lemma_.lower() not in GENERIC_LOW_SIGNAL_CONCEPTS
    ]

    concept_freq = Counter(concepts)
    unique_concepts = list(dict.fromkeys(
        [word for word, _ in concept_freq.most_common()]
    ))

    logger.debug(f"Extracted {len(unique_concepts)} concepts from text (spaCy)")
    return unique_concepts


def _extract_concepts_naive(text: str, min_length: int = 4) -> List[str]:
    """
    Fallback used only when the spaCy German model isn't installed:
    length + a small stopword list, no actual grammar awareness. Kept
    around so a missing model degrades chat quality slightly instead of
    breaking message storage outright.
    """
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

    text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
    words = text_clean.split()

    concepts = [
        word for word in words
        if len(word) >= min_length
        and word not in stopwords
        and word not in GENERIC_LOW_SIGNAL_CONCEPTS
    ]

    concept_freq = Counter(concepts)
    unique_concepts = list(dict.fromkeys(
        [word for word, _ in concept_freq.most_common()]
    ))

    logger.debug(f"Extracted {len(unique_concepts)} concepts from text (naive fallback)")
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
        result['temporal'] = temporal_result.scalar()

        # Single commit for both PostgreSQL dimensions together (issue #7
        # item 4): previously each had its own commit, so a failure between
        # them (e.g. the temporal_index insert) left the semantic_metadata
        # row permanently committed with no matching temporal_index row -
        # the outer except's db.rollback() below is a no-op for work
        # that's already committed. Either both land together or neither
        # does.
        db.commit()

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
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
            )
            result['neo4j'] = 'created'
            
            # If mood is provided, create mood node and link
            if mood and energy_level:
                timestamp = datetime.now(timezone.utc).isoformat()
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
    
    # content_types filter as a bind parameter, not string interpolation
    # (issue #7 item 7) - expanding=True lets SQLAlchemy turn the list into
    # a safely parameterized IN (...) regardless of its contents.
    content_filter = "AND content_type IN :content_types" if content_types else ""

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
    if content_types:
        sql = sql.bindparams(bindparam('content_types', expanding=True))

    params = {
        'user_id': user_id,
        'query_embedding': str(query_embedding),
        'min_similarity': min_similarity,
        'limit': limit
    }
    if content_types:
        params['content_types'] = content_types

    result = db.execute(sql, params)

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
    # content_types filter as a bind parameter, not string interpolation
    # (issue #7 item 7) - same reasoning as search_semantic_memory() above.
    content_filter = "AND t.content_type IN :content_types" if content_types else ""

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
    if content_types:
        sql = sql.bindparams(bindparam('content_types', expanding=True))

    params = {'user_id': user_id, 'limit': limit}
    if content_types:
        params['content_types'] = content_types

    result = db.execute(sql, params)
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
    timestamp: Optional[datetime] = None,
    session_id: Optional[int] = None,
    source_type: Optional[str] = None
) -> Dict:
    """
    Speichert Message in Neo4j mit auto-extrahierten Concepts

    Args:
        user_id: User ID
        message_id: Message ID (from PostgreSQL)
        content: Message-Content
        role: 'user' | 'assistant'
        timestamp: Message Timestamp
        session_id: PostgreSQL chat_sessions.id - lets later queries (e.g.
            "find the last assistant reply in this conversation") scope by
            the actual conversation instead of across the whole user
        source_type: 'tool_result' | 'user_statement' | 'assistant_reply' -
            drives the starting epistemic_state/confidence (see
            memory_verification.py's SOURCE_TYPE_TO_EPISTEMIC_STATE /
            EPISTEMIC_STATE_CONFIDENCE - naming aligned with the sibling
            LIARA repo's ADR-007 "Epistemic Subgraph"). Defaults to deriving from `role` when not given
            explicitly - a tool_result caller must pass it, since there's no
            way to infer "this text came from a verified tool call" from
            role/content alone.

    Returns:
        Dict mit Statistiken
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    from services.memory_verification import (
        classify_source_type, initial_confidence_for, epistemic_state_for
    )

    resolved_source_type = source_type or classify_source_type(role)
    confidence = initial_confidence_for(resolved_source_type)
    epistemic_state = epistemic_state_for(resolved_source_type).value

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

        # Message Node - MERGE on the constrained key (user_id, message_id),
        # not CREATE (issue #7 item 5): a retried call for the same message
        # used to hit the message_unique constraint and throw, aborting
        # before the concept loop below even ran. ON CREATE SET means a
        # retry finds the existing node, sets nothing again, and the MERGE
        # relationship below is a no-op - the whole call now converges to
        # the same state instead of failing.
        #
        # source_type/confidence/valid_from/valid_until (bi-temporal, Zep-
        # pattern): a superseded memory is never deleted, only invalidated
        # (valid_until set) with a SUPERSEDES edge to whatever replaced it -
        # see invalidate_message()/supersede_message() below. valid_until
        # starts null (still valid); confidence starts at the source's trust
        # level and can be adjusted later (contradiction penalty, explicit
        # correction) without changing what's on record about where the
        # memory originally came from.
        session.run("""
            MATCH (u:User {user_id: $user_id})
            MERGE (m:Message {user_id: $user_id, message_id: $message_id})
            ON CREATE SET
                m.content = $content,
                m.role = $role,
                m.session_id = $session_id,
                m.timestamp = datetime($timestamp),
                m.created_at = datetime(),
                m.source_type = $source_type,
                m.epistemic_state = $epistemic_state,
                m.confidence = $confidence,
                m.valid_from = datetime($timestamp),
                m.valid_until = null,
                m.superseded_by = null
            MERGE (u)-[:SENT]->(m)
        """,
            user_id=user_id,
            message_id=message_id,
            content=content[:500],
            role=role,
            session_id=session_id,
            timestamp=timestamp.isoformat(),
            source_type=resolved_source_type,
            epistemic_state=epistemic_state,
            confidence=confidence
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
                # mention_count is incremented on the (Message)-[:CONTAINS]->
                # (Concept) relationship's ON CREATE, not the Concept node's
                # ON MATCH (issue #7 item 5): the old version bumped it
                # whenever the Concept already existed, regardless of
                # whether THIS message had already been linked to it - a
                # retry of the same message re-processing this exact
                # concept would double-count it. Tying the increment to the
                # relationship's own creation makes it idempotent per
                # (message, concept) pair - a replay finds the relationship
                # already there, MERGE is a no-op, ON CREATE SET doesn't
                # fire again.
                session.run("""
                    MATCH (m:Message {user_id: $user_id, message_id: $message_id})
                    MERGE (c:Concept {text: $concept, user_id: $user_id})
                    ON CREATE SET
                        c.embedding = $embedding,
                        c.created_at = datetime(),
                        c.mention_count = 0
                    MERGE (m)-[r:CONTAINS]->(c)
                    ON CREATE SET
                        r.created_at = datetime(),
                        c.mention_count = c.mention_count + 1,
                        c.last_mentioned = datetime()
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
    min_similarity: float = 0.78
) -> List[Dict]:
    """
    Findet semantisch ähnliche Concepts für Context-Injection

    Args:
        user_id: User ID
        query_text: Query-Text (neue Message)
        limit: Max Anzahl Ergebnisse
        min_similarity: Min Cosine-Similarity - raised from 0.6 to 0.78
            (see GENERIC_LOW_SIGNAL_CONCEPTS above for why 0.6 let noise
            through). Still advisory, not a hard guarantee against every
            spurious match, just a much tighter bar.

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
            # Second line of defense (see GENERIC_LOW_SIGNAL_CONCEPTS): the
            # extraction-time filter only stops NEW noise, existing Concept
            # nodes created before this fix are still sitting in the graph.
            if record['embedding'] and record['concept'] not in GENERIC_LOW_SIGNAL_CONCEPTS:
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
            # valid_until IS NOT NULL means a SUPERSEDES edge invalidated this
            # message (see supersede_message() below) - it stays in the graph
            # for the audit trail (bi-temporal, Zep-pattern) but must not be
            # surfaced as current context anymore. Old Message nodes from
            # before the epistemic-state migration have valid_until = NULL
            # (never set), so they pass this filter unaffected - no backfill
            # needed for this query to be safe, only to have accurate
            # confidence/epistemic_state on them (see migrate_legacy_messages()).
            result = session.run("""
                MATCH (c:Concept {text: $concept, user_id: $user_id})<-[:CONTAINS]-(m:Message)
                WHERE m.valid_until IS NULL
                RETURN m.message_id as message_id, m.content as content,
                       m.role as role, m.timestamp as timestamp,
                       coalesce(m.confidence, 0.5) as confidence,
                       coalesce(m.epistemic_state, 'INFERENCE') as epistemic_state
                ORDER BY m.timestamp DESC
                LIMIT 3
            """, concept=concept_item['concept'], user_id=user_id)

            messages = []
            for record in result:
                messages.append({
                    'message_id': record['message_id'],
                    'content': record['content'],
                    'role': record['role'],
                    'timestamp': str(record['timestamp']),
                    'confidence': record['confidence'],
                    'epistemic_state': record['epistemic_state']
                })
            
            context_items.append({
                'concept': concept_item['concept'],
                'similarity': concept_item['similarity'],
                'mentions': concept_item['mentions'],
                'related_messages': messages
            })
    
    logger.info(f"Found {len(context_items)} relevant concepts for context injection")
    return context_items


def supersede_message(
    user_id: int,
    old_message_id: int,
    new_message_id: int,
    reason: str = ""
) -> bool:
    """
    Invalidiert eine bestehende Erinnerung zugunsten einer neueren, besser
    belegten - bi-temporal (Zep-Pattern): der alte Message-Knoten bleibt
    erhalten (Audit-Trail), wird aber nicht mehr als aktueller Stand
    zurückgegeben (get_relevant_context() filtert per valid_until IS NULL).

    Für den Fall, dass die neue, bessere Erinnerung selbst als Message-Knoten
    existiert (z.B. eine neue, korrekte Assistant-Antwort im selben Thema).
    Trigger a (tool_executor.py, automatischer Tool-Widerspruch) hat dagegen
    keinen neuen Message-Knoten zur Hand - dort ist der Tool-Call selbst der
    Beleg, ohne eigenen Message-Eintrag - und ruft daher stattdessen
    invalidate_message(..., hard=True) auf (siehe dort).

    Legt eine (new)-[:SUPERSEDES]->(old) Kante an (Relation-Name aus
    memory_verification.MemoryRelation, deckungsgleich mit ADR-007's
    EvolutionRelation.SUPERSEDES im Schwester-Repo).
    """
    from services.memory_verification import EpistemicState, MemoryRelation

    neo4j = get_neo4j_service()
    with neo4j.driver.session() as session:
        result = session.run(f"""
            MATCH (old:Message {{user_id: $user_id, message_id: $old_message_id}})
            MATCH (new:Message {{user_id: $user_id, message_id: $new_message_id}})
            SET old.valid_until = datetime(),
                old.superseded_by = $new_message_id,
                old.epistemic_state = $superseded_state
            MERGE (new)-[r:{MemoryRelation.SUPERSEDES.value}]->(old)
            ON CREATE SET r.reason = $reason, r.created_at = datetime()
            RETURN old.message_id as invalidated
        """,
            user_id=user_id,
            old_message_id=old_message_id,
            new_message_id=new_message_id,
            superseded_state=EpistemicState.SUPERSEDED.value,
            reason=reason
        )
        invalidated = result.single()

    if invalidated:
        logger.info(
            f"Message {old_message_id} superseded by {new_message_id} "
            f"for user {user_id} ({reason or 'no reason given'})"
        )
        return True
    logger.warning(
        f"supersede_message: old={old_message_id} or new={new_message_id} "
        f"not found for user {user_id}"
    )
    return False


def invalidate_message(
    user_id: int,
    message_id: int,
    reason: str = "",
    contradicting_message_id: Optional[int] = None,
    hard: bool = False
) -> bool:
    """
    Markiert eine Erinnerung als widerlegt (CONTRADICTED), ohne dass es
    zwingend einen Ersatz-Message-Knoten gibt (anders als supersede_message).
    Für Trigger b (Nutzer-Widerspruch ohne nachprüfbaren Tool-Call - reine,
    weiche Konfidenz-Abwertung statt hartem Invalidieren) UND für den Fall,
    dass eine Nachprüfung stattfand, aber kein neuer Message-Knoten das
    Ergebnis trägt (z.B. eine Tool-Antwort, die nicht selbst gespeichert
    wird). Setzt confidence standardmäßig per UNVERIFIED_CONTRADICTION_PENALTY
    nur herab statt sie auf 0 zu setzen - BeliefMem-Gedanke: Unsicherheit
    halten, nicht hart auf falsch springen, solange keine echte Verifikation
    vorliegt.

    hard=True (Trigger c, bewusstes correct_memory-Kommando): der Nutzer hat
    die alte Erinnerung nicht nur heuristisch angezweifelt, sondern explizit
    und eindeutig als falsch benannt - Konfidenz wird direkt auf einen
    Rest-Wert nahe 0 gesetzt statt nur graduell abgewertet.

    Wenn eine contradicting_message_id vorliegt (z.B. Trigger c, explizite
    Korrektur mit Beleg), wird zusätzlich eine CONTRADICTS-Kante angelegt.
    """
    from services.memory_verification import (
        EpistemicState, MemoryRelation, UNVERIFIED_CONTRADICTION_PENALTY
    )

    neo4j = get_neo4j_service()
    with neo4j.driver.session() as session:
        if hard:
            result = session.run("""
                MATCH (m:Message {user_id: $user_id, message_id: $message_id})
                SET m.epistemic_state = $contradicted_state,
                    m.confidence = 0.05
                RETURN m.message_id as flagged
            """,
                user_id=user_id,
                message_id=message_id,
                contradicted_state=EpistemicState.CONTRADICTED.value
            )
        else:
            result = session.run("""
                MATCH (m:Message {user_id: $user_id, message_id: $message_id})
                SET m.epistemic_state = $contradicted_state,
                    m.confidence = CASE
                        WHEN m.confidence IS NULL THEN 0.3
                        WHEN m.confidence - $penalty < 0.0 THEN 0.0
                        ELSE m.confidence - $penalty
                    END
                RETURN m.message_id as flagged
            """,
                user_id=user_id,
                message_id=message_id,
                contradicted_state=EpistemicState.CONTRADICTED.value,
                penalty=UNVERIFIED_CONTRADICTION_PENALTY
            )
        flagged = result.single()

        if flagged and contradicting_message_id is not None:
            session.run(f"""
                MATCH (a:Message {{user_id: $user_id, message_id: $contradicting_id}})
                MATCH (b:Message {{user_id: $user_id, message_id: $message_id}})
                MERGE (a)-[r:{MemoryRelation.CONTRADICTS.value}]->(b)
                ON CREATE SET r.reason = $reason, r.created_at = datetime()
            """,
                user_id=user_id,
                contradicting_id=contradicting_message_id,
                message_id=message_id,
                reason=reason
            )

    if flagged:
        logger.info(
            f"Message {message_id} flagged CONTRADICTED for user {user_id} "
            f"({reason or 'no reason given'})"
        )
        return True
    logger.warning(f"invalidate_message: message {message_id} not found for user {user_id}")
    return False


def migrate_legacy_messages(user_id: Optional[int] = None, batch_size: int = 500) -> Dict:
    """
    Backfill für Message-Knoten von vor der Epistemic-State-Einführung
    (2026-09-03): setzt source_type/epistemic_state/confidence/valid_from
    anhand des vorhandenen role-Felds, valid_until bleibt null (weiterhin
    gültig). Ohne diesen Lauf würden alte Knoten in get_relevant_context()
    zwar noch auftauchen (valid_until IS NULL trifft auf sie automatisch zu),
    aber mit den irreführenden Fallback-Werten aus der Abfrage
    (confidence=0.5, epistemic_state='INFERENCE') statt ihrer tatsächlichen,
    aus role ableitbaren Einstufung.

    Idempotent - nur Knoten ohne epistemic_state werden angefasst, ein
    erneuter Lauf ändert nichts mehr.
    """
    from services.memory_verification import classify_source_type, initial_confidence_for, epistemic_state_for

    neo4j = get_neo4j_service()
    user_filter = "AND m.user_id = $user_id" if user_id is not None else ""

    updated = 0
    with neo4j.driver.session() as session:
        while True:
            result = session.run(f"""
                MATCH (m:Message)
                WHERE m.epistemic_state IS NULL {user_filter}
                RETURN m.user_id as user_id, m.message_id as message_id, m.role as role
                LIMIT $batch_size
            """, user_id=user_id, batch_size=batch_size)
            rows = list(result)
            if not rows:
                break

            for row in rows:
                source_type = classify_source_type(row['role'])
                session.run("""
                    MATCH (m:Message {user_id: $user_id, message_id: $message_id})
                    SET m.source_type = coalesce(m.source_type, $source_type),
                        m.epistemic_state = $epistemic_state,
                        m.confidence = coalesce(m.confidence, $confidence),
                        m.valid_from = coalesce(m.valid_from, m.timestamp, datetime())
                """,
                    user_id=row['user_id'],
                    message_id=row['message_id'],
                    source_type=source_type,
                    epistemic_state=epistemic_state_for(source_type).value,
                    confidence=initial_confidence_for(source_type)
                )
                updated += 1

            if len(rows) < batch_size:
                break

    logger.info(f"migrate_legacy_messages: backfilled {updated} Message nodes")
    return {"updated": updated}


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
