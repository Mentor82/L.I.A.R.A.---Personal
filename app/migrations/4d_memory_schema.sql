-- 🌌 LIARA 4D Memory Architecture - Database Schema
-- Created: 2025-12-03
-- Dimensions: Content | Temporal | Semantic | Relational

-- ============================================================================
-- DIMENSION 1: CONTENT LAYER
-- Existing tables: users, tasks, calendar_events, notes, messages
-- New: Enhanced metadata tracking
-- ============================================================================

-- ============================================================================
-- DIMENSION 2: TEMPORAL LAYER
-- Tracks sequences, context windows, and temporal relationships
-- ============================================================================

CREATE TABLE IF NOT EXISTS temporal_index (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(50) NOT NULL,  -- 'message', 'task', 'note', 'event', 'mood'
    content_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Temporal metadata
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sequence_number BIGINT NOT NULL,  -- Global sequence across all user events
    session_id VARCHAR(255),  -- Links to Redis session
    
    -- Context window
    context_window_start TIMESTAMP,
    context_window_end TIMESTAMP,
    
    -- Mood tracking at time of creation
    mood_at_time VARCHAR(50),  -- happy, sad, stressed, focused, etc.
    energy_level INTEGER CHECK (energy_level >= 1 AND energy_level <= 10),
    
    -- Indexing
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, content_type, content_id)
);

-- Indexes for temporal queries
CREATE INDEX idx_temporal_user_timestamp ON temporal_index(user_id, timestamp DESC);
CREATE INDEX idx_temporal_sequence ON temporal_index(user_id, sequence_number DESC);
CREATE INDEX idx_temporal_session ON temporal_index(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_temporal_mood ON temporal_index(user_id, mood_at_time) WHERE mood_at_time IS NOT NULL;

-- ============================================================================
-- DIMENSION 3: SEMANTIC LAYER
-- Vector embeddings for semantic similarity search
-- ============================================================================

CREATE TABLE IF NOT EXISTS semantic_metadata (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(50) NOT NULL,
    content_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Semantic embedding (384 dimensions for all-MiniLM-L6-v2)
    embedding vector(384),
    
    -- Semantic analysis
    topics TEXT[],  -- Extracted topics/keywords
    intent VARCHAR(100),  -- CREATE, UPDATE, DELETE, SEARCH, REFLECT, etc.
    emotion VARCHAR(50),  -- Detected emotion from content
    importance INTEGER CHECK (importance >= 1 AND importance <= 10),
    
    -- Content snapshot for context
    content_summary TEXT,  -- First 500 chars or summary
    
    -- Versioning
    embedding_model VARCHAR(100) DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    embedding_version INTEGER DEFAULT 1,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, content_type, content_id)
);

-- Indexes for semantic search
CREATE INDEX idx_semantic_user ON semantic_metadata(user_id);
CREATE INDEX idx_semantic_type ON semantic_metadata(content_type);
CREATE INDEX idx_semantic_intent ON semantic_metadata(intent);
CREATE INDEX idx_semantic_importance ON semantic_metadata(user_id, importance DESC);

-- HNSW index for fast vector similarity search
CREATE INDEX idx_semantic_embedding_hnsw ON semantic_metadata 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- IVFFlat index as alternative (faster build, slower query)
-- CREATE INDEX idx_semantic_embedding_ivf ON semantic_metadata 
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);

-- ============================================================================
-- DIMENSION 4: RELATIONAL LAYER (PostgreSQL component)
-- Neo4j handles complex graph relationships, but we store basic links here
-- ============================================================================

CREATE TABLE IF NOT EXISTS content_relations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Source entity
    source_type VARCHAR(50) NOT NULL,
    source_id INTEGER NOT NULL,
    
    -- Target entity
    target_type VARCHAR(50) NOT NULL,
    target_id INTEGER NOT NULL,
    
    -- Relationship metadata
    relation_type VARCHAR(100) NOT NULL,  -- CAUSED_MOOD, RELATED_TO, TRIGGERED_BY, etc.
    strength FLOAT CHECK (strength >= 0 AND strength <= 1),  -- Relationship strength
    
    -- Context
    discovered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    discovery_method VARCHAR(100),  -- 'user_explicit', 'semantic_similarity', 'temporal_proximity', 'ml_inferred'
    
    -- Syncing with Neo4j
    synced_to_neo4j BOOLEAN DEFAULT FALSE,
    neo4j_relation_id VARCHAR(255),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, source_type, source_id, target_type, target_id, relation_type)
);

-- Indexes for relationship queries
CREATE INDEX idx_relations_source ON content_relations(user_id, source_type, source_id);
CREATE INDEX idx_relations_target ON content_relations(user_id, target_type, target_id);
CREATE INDEX idx_relations_type ON content_relations(relation_type);
CREATE INDEX idx_relations_strength ON content_relations(user_id, strength DESC);
CREATE INDEX idx_relations_neo4j_sync ON content_relations(synced_to_neo4j) WHERE synced_to_neo4j = FALSE;

-- ============================================================================
-- SESSION MEMORY (Redis-backed, PostgreSQL tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS session_memory (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,
    
    -- Session metadata
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    
    -- Session context
    context_summary TEXT,
    primary_intent VARCHAR(100),
    
    -- Redis sync
    redis_key VARCHAR(255),  -- Key in Redis where full context is stored
    
    -- Session stats
    message_count INTEGER DEFAULT 0,
    action_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(session_id)
);

CREATE INDEX idx_session_user ON session_memory(user_id, started_at DESC);
CREATE INDEX idx_session_active ON session_memory(user_id, ended_at) WHERE ended_at IS NULL;
CREATE INDEX idx_session_redis ON session_memory(redis_key);

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_semantic_metadata_updated_at BEFORE UPDATE ON semantic_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_session_memory_updated_at BEFORE UPDATE ON session_memory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to generate sequence numbers
CREATE SEQUENCE IF NOT EXISTS temporal_sequence_global;

CREATE OR REPLACE FUNCTION get_next_temporal_sequence()
RETURNS BIGINT AS $$
BEGIN
    RETURN nextval('temporal_sequence_global');
END;
$$ language 'plpgsql';

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Recent memory context for a user
CREATE OR REPLACE VIEW v_recent_memory_context AS
SELECT 
    t.user_id,
    t.content_type,
    t.content_id,
    t.timestamp,
    t.sequence_number,
    t.mood_at_time,
    s.intent,
    s.emotion,
    s.importance,
    s.topics,
    s.content_summary
FROM temporal_index t
LEFT JOIN semantic_metadata s ON (
    t.user_id = s.user_id 
    AND t.content_type = s.content_type 
    AND t.content_id = s.content_id
)
ORDER BY t.sequence_number DESC;

-- View: Active sessions
CREATE OR REPLACE VIEW v_active_sessions AS
SELECT 
    sm.*,
    COUNT(ti.id) as event_count
FROM session_memory sm
LEFT JOIN temporal_index ti ON sm.session_id = ti.session_id
WHERE sm.ended_at IS NULL
GROUP BY sm.id
ORDER BY sm.last_activity DESC;

-- ============================================================================
-- INITIAL DATA & VALIDATION
-- ============================================================================

-- Grant permissions (adjust based on your database user)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO liara_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO liara_user;

-- Validation query
SELECT 
    'temporal_index' as table_name, COUNT(*) as row_count FROM temporal_index
UNION ALL
SELECT 'semantic_metadata', COUNT(*) FROM semantic_metadata
UNION ALL
SELECT 'content_relations', COUNT(*) FROM content_relations
UNION ALL
SELECT 'session_memory', COUNT(*) FROM session_memory;

-- Extension verification
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

COMMENT ON TABLE temporal_index IS '4D Memory - Dimension 2: Temporal tracking of all user content with sequence numbers and context windows';
COMMENT ON TABLE semantic_metadata IS '4D Memory - Dimension 3: Vector embeddings and semantic analysis for similarity search';
COMMENT ON TABLE content_relations IS '4D Memory - Dimension 4: Relationships between content items (syncs with Neo4j)';
COMMENT ON TABLE session_memory IS '4D Memory - Short-term context storage (syncs with Redis)';
