"""
🌌 LIARA 4D Memory - API Router
Endpoints for semantic search, relations, and context management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from core.database import get_db
from core.dependencies import get_current_user
from services.embedding_service import get_embedding_service, analyze_content
from services.neo4j_service import get_neo4j_service
from services.redis_service import get_redis_service

router = APIRouter(prefix="/memory", tags=["4D Memory"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class SemanticSearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    content_types: Optional[List[str]] = Field(None, description="Filter by content types")
    limit: int = Field(10, ge=1, le=50, description="Maximum results")
    min_similarity: float = Field(0.5, ge=0, le=1, description="Minimum similarity score")


class SemanticSearchResult(BaseModel):
    content_type: str
    content_id: int
    similarity: float
    content_summary: str
    topics: List[str]
    intent: str
    emotion: str
    importance: int
    timestamp: datetime


class RelatedContentRequest(BaseModel):
    content_type: str
    content_id: int
    max_depth: int = Field(2, ge=1, le=4)
    limit: int = Field(10, ge=1, le=50)


class RelationshipResult(BaseModel):
    type: str
    content_id: int
    distance: int
    relationship_chain: List[str]
    properties: dict


class ContextWindowResult(BaseModel):
    session_id: str
    context_items: List[dict]
    message_count: int
    action_count: int
    started_at: str
    last_activity: str


class MoodPattern(BaseModel):
    mood: str
    energy: int
    timestamp: str
    trigger_type: Optional[str]
    trigger_properties: Optional[dict]


class AnalyzeTextRequest(BaseModel):
    text: str
    context: Optional[dict] = None


class AnalyzeTextResponse(BaseModel):
    topics: List[str]
    intent: str
    emotion: str
    importance: int
    embedding_model: str


# ============================================================================
# DIMENSION 3: Semantic Search Endpoints
# ============================================================================

@router.post("/semantic_search", response_model=List[SemanticSearchResult])
async def semantic_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Search for semantically similar content using vector embeddings
    
    Uses cosine similarity to find content similar to the query.
    """
    embedding_service = get_embedding_service()
    
    # Generate query embedding
    query_embedding = embedding_service.generate_embedding(request.query)
    
    # Build SQL query for vector similarity search
    content_type_filter = ""
    if request.content_types:
        types_str = "','".join(request.content_types)
        content_type_filter = f"AND content_type IN ('{types_str}')"
    
    # PostgreSQL query using pgvector
    sql = f"""
    SELECT 
        content_type,
        content_id,
        1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity,
        content_summary,
        topics,
        intent,
        emotion,
        importance,
        created_at as timestamp
    FROM semantic_metadata
    WHERE user_id = :user_id
        {content_type_filter}
        AND embedding IS NOT NULL
        AND 1 - (embedding <=> CAST(:query_embedding AS vector)) >= :min_similarity
    ORDER BY embedding <=> CAST(:query_embedding AS vector)
    LIMIT :limit
    """
    
    from sqlalchemy import text
    result = db.execute(
        text(sql),
        {
            'user_id': current_user.id,
            'query_embedding': str(query_embedding),
            'min_similarity': request.min_similarity,
            'limit': request.limit
        }
    )
    
    results = []
    for row in result:
        results.append(SemanticSearchResult(
            content_type=row.content_type,
            content_id=row.content_id,
            similarity=round(row.similarity, 4),
            content_summary=row.content_summary or "",
            topics=row.topics or [],
            intent=row.intent or "unknown",
            emotion=row.emotion or "neutral",
            importance=row.importance or 5,
            timestamp=row.timestamp
        ))
    
    return results


@router.post("/analyze", response_model=AnalyzeTextResponse)
async def analyze_text(
    request: AnalyzeTextRequest,
    current_user = Depends(get_current_user)
):
    """
    Analyze text and extract semantic metadata (topics, intent, emotion, importance)
    
    Does not store the analysis - just returns it.
    """
    analysis = analyze_content(request.text, request.context)
    
    return AnalyzeTextResponse(
        topics=analysis['topics'],
        intent=analysis['intent'],
        emotion=analysis['emotion'],
        importance=analysis['importance'],
        embedding_model=analysis['embedding_model']
    )


# ============================================================================
# DIMENSION 4: Relational/Graph Endpoints
# ============================================================================

@router.post("/related", response_model=List[RelationshipResult])
async def find_related_content(
    request: RelatedContentRequest,
    current_user = Depends(get_current_user)
):
    """
    Find related content using graph relationships (Neo4j)
    
    Traverses the knowledge graph to find connected content.
    """
    neo4j_service = get_neo4j_service()
    
    try:
        related = neo4j_service.find_related_content(
            content_type=request.content_type.capitalize(),
            content_id=request.content_id,
            user_id=current_user.id,
            max_depth=request.max_depth,
            limit=request.limit
        )
        
        results = []
        for item in related:
            # Extract content_id from properties
            content_id = item['properties'].get(f"{item['type'].lower()}_id", 0)
            
            results.append(RelationshipResult(
                type=item['type'],
                content_id=content_id,
                distance=item['distance'],
                relationship_chain=item['relationship_chain'],
                properties=item['properties']
            ))
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph query failed: {str(e)}")


@router.get("/mood_patterns", response_model=List[MoodPattern])
async def get_mood_patterns(
    days: int = Query(7, ge=1, le=30),
    current_user = Depends(get_current_user)
):
    """
    Analyze mood patterns and what triggers them (Neo4j)
    
    Returns mood history with detected triggers.
    """
    neo4j_service = get_neo4j_service()
    
    try:
        patterns = neo4j_service.find_mood_patterns(
            user_id=current_user.id,
            days=days
        )
        
        return [MoodPattern(**p) for p in patterns]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mood analysis failed: {str(e)}")


# ============================================================================
# DIMENSION 2: Temporal/Context Endpoints
# ============================================================================

@router.get("/context/{session_id}", response_model=ContextWindowResult)
async def get_context_window(
    session_id: str,
    last_n: Optional[int] = Query(None, ge=1, le=50),
    current_user = Depends(get_current_user)
):
    """
    Get conversation context window for a session (Redis)
    
    Returns recent context items from the session.
    """
    redis_service = get_redis_service()
    
    session = redis_service.get_session(current_user.id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    context = redis_service.get_context_window(current_user.id, session_id, last_n)
    
    return ContextWindowResult(
        session_id=session_id,
        context_items=context,
        message_count=session.get('message_count', 0),
        action_count=session.get('action_count', 0),
        started_at=session.get('started_at', ''),
        last_activity=session.get('last_activity', '')
    )


@router.get("/sessions", response_model=List[str])
async def get_active_sessions(
    current_user = Depends(get_current_user)
):
    """
    Get list of active session IDs for current user (Redis)
    """
    redis_service = get_redis_service()
    return redis_service.get_active_sessions(current_user.id)


# ============================================================================
# Status & Health Endpoints
# ============================================================================

@router.get("/status")
async def memory_status(current_user = Depends(get_current_user)):
    """
    Get status of all 4D Memory components
    """
    from sqlalchemy import text
    
    status = {
        "dimension_1_content": "PostgreSQL - OK",
        "dimension_2_temporal": None,
        "dimension_3_semantic": None,
        "dimension_4_relational": None,
        "services": {
            "embedding": None,
            "neo4j": None,
            "redis": None
        }
    }
    
    # Check PostgreSQL tables
    try:
        db = next(get_db())
        
        # Temporal
        result = db.execute(text("SELECT COUNT(*) FROM temporal_index WHERE user_id = :uid"), 
                           {"uid": current_user.id})
        temporal_count = result.scalar()
        status["dimension_2_temporal"] = f"PostgreSQL - {temporal_count} entries"
        
        # Semantic
        result = db.execute(text("SELECT COUNT(*) FROM semantic_metadata WHERE user_id = :uid"), 
                           {"uid": current_user.id})
        semantic_count = result.scalar()
        status["dimension_3_semantic"] = f"PostgreSQL+pgvector - {semantic_count} embeddings"
        
        # Relations
        result = db.execute(text("SELECT COUNT(*) FROM content_relations WHERE user_id = :uid"), 
                           {"uid": current_user.id})
        relations_count = result.scalar()
        status["dimension_4_relational"] = f"PostgreSQL - {relations_count} relations"
        
    except Exception as e:
        status["dimension_2_temporal"] = f"Error: {str(e)}"
        status["dimension_3_semantic"] = f"Error: {str(e)}"
        status["dimension_4_relational"] = f"Error: {str(e)}"
    
    # Check embedding service
    try:
        embedding_service = get_embedding_service()
        test_emb = embedding_service.generate_embedding("test")
        status["services"]["embedding"] = f"OK - {embedding_service.model_name} ({len(test_emb)} dim)"
    except Exception as e:
        status["services"]["embedding"] = f"Error: {str(e)}"
    
    # Check Neo4j
    try:
        neo4j_service = get_neo4j_service()
        with neo4j_service.driver.session() as session:
            result = session.run("RETURN 1 as test")
            if result.single():
                status["services"]["neo4j"] = "OK - Connected"
    except Exception as e:
        status["services"]["neo4j"] = f"Error: {str(e)}"
    
    # Check Redis
    try:
        redis_service = get_redis_service()
        redis_service.client.ping()
        sessions = redis_service.get_active_sessions(current_user.id)
        status["services"]["redis"] = f"OK - {len(sessions)} active sessions"
    except Exception as e:
        status["services"]["redis"] = f"Error: {str(e)}"
    
    return status
