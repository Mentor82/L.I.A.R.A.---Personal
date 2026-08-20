# 🧠 4D Memory System

**Version:** 2.6.0  
**Erstellt:** 2025-12-03  
**Status:** ✅ Produktiv

---

## 📋 Übersicht

Das 4D Memory System ist Liara's multi-dimensionales Gedächtnissystem, das Kontext, Bedeutung und zeitliche Zusammenhänge über mehrere Speicherschichten verwaltet.

**4 Dimensionen:**
1. **Semantic Memory** - PostgreSQL + pgvector (Bedeutung & Embeddings)
2. **Temporal Index** - PostgreSQL (Zeitliche Sequenzen)
3. **Graph Relations** - Neo4j (Beziehungen & Muster)
4. **Session Context** - Redis (Kurzzeit-Kontext)

---

## 🌌 Dimension 1: Semantic Memory (PostgreSQL + pgvector)

### Architektur

**Tabelle:** `semantic_metadata`

```sql
CREATE TABLE semantic_metadata (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(50) NOT NULL,  -- 'message', 'task', 'event', 'note'
    content_id INTEGER NOT NULL,        -- ID des Originalobjekts
    user_id INTEGER NOT NULL REFERENCES users(id),
    
    -- Semantic Fields
    embedding vector(384),              -- 384-dim Vektor (pgvector)
    topics TEXT[],                      -- Extrahierte Keywords
    intent VARCHAR(100),                -- CHAT, CREATE, SEARCH, etc.
    emotion VARCHAR(50),                -- neutral, joy, sadness, etc.
    importance INTEGER CHECK (importance BETWEEN 1 AND 10),
    content_summary TEXT,               -- Zusammenfassung des Inhalts
    
    -- Metadata
    embedding_model VARCHAR(100) DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    embedding_version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, content_type, content_id)
);

-- HNSW Index für schnelle Vektor-Suche
CREATE INDEX idx_semantic_embedding_hnsw ON semantic_metadata 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);
```

### Content Types

| Type | Source | Additional Context |
|------|--------|-------------------|
| `message` | Chat messages | model, temperature, mood, energy_level |
| `task` | Tasks table | priority, tags, completed |
| `event` | Calendar events | event_type, location, start_time, end_time |
| `note` | Notes table | category, tags, is_pinned |

### Embedding Model

**Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions:** 384
- **Max Sequence Length:** 256 tokens
- **Speed:** ~2000 sentences/sec on CPU
- **Use Case:** Semantic similarity, clustering, retrieval

### Topic Extraction

Automatische Keyword-Extraktion mittels:
1. **TF-IDF** (Term Frequency - Inverse Document Frequency)
2. **Stop-Word Removal** (de/en)
3. **Top-5 Selection** (nach Relevanz sortiert)

**Beispiel:**
```
Content: "Merk dir: Milch und Brot kaufen"
→ Topics: {milch, brot, kaufen}
```

### Semantic Search

**Cosine Similarity Query:**

```sql
SELECT 
    id,
    content_type,
    content_id,
    content_summary,
    1 - (embedding <=> query_embedding) as similarity
FROM semantic_metadata
WHERE user_id = $1
    AND content_type = ANY($2)  -- Optional: Filter by type
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

**Python API:**

```python
from services.memory_integration import search_semantic_memory

results = search_semantic_memory(
    db=db,
    user_id=1,
    query="shopping items",
    content_types=['note', 'task'],
    limit=10,
    min_similarity=0.5
)

for result in results:
    print(f"{result.content_type} #{result.content_id}: {result.summary} (similarity: {result.similarity:.2f})")
```

---

## ⏱️ Dimension 2: Temporal Index

### Architektur

**Tabelle:** `temporal_index`

```sql
CREATE TABLE temporal_index (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    content_type VARCHAR(50) NOT NULL,
    content_id INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,  -- Fortlaufende Nummer
    session_id VARCHAR(100),           -- Optional: Session-Gruppierung
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, sequence_number)
);

CREATE INDEX idx_temporal_user_seq ON temporal_index(user_id, sequence_number DESC);
CREATE INDEX idx_temporal_session ON temporal_index(session_id);
```

### Use Cases

**1. Chronologische Historie:**
```sql
SELECT * FROM temporal_index
WHERE user_id = 1
ORDER BY sequence_number DESC
LIMIT 20;
```

**2. Session-Reconstruction:**
```sql
SELECT * FROM temporal_index
WHERE session_id = 'chat_1_20251203_203000'
ORDER BY sequence_number ASC;
```

**3. Time-Range Queries:**
```sql
SELECT * FROM temporal_index
WHERE user_id = 1
    AND created_at >= NOW() - INTERVAL '7 days'
ORDER BY sequence_number DESC;
```

---

## 🕸️ Dimension 3: Graph Relations (Neo4j)

### Node Types

| Node | Properties | Purpose |
|------|-----------|---------|
| `User` | id, username, email | User entity |
| `Message` | content, timestamp, mood | Chat messages |
| `Task` | title, priority, completed | Tasks |
| `Event` | title, start_time, location | Calendar events |
| `Note` | title, category, content | Notes |
| `Topic` | name, frequency | Extracted keywords |

### Relationship Types

| Relationship | From → To | Meaning |
|--------------|-----------|---------|
| `CREATED_FROM` | Task/Event/Note → Message | Item was created from chat |
| `MENTIONED_IN` | Topic → Message | Topic was mentioned |
| `RELATED_TO` | Task ↔ Event | Semantic connection |
| `BELONGS_TO` | Task/Event/Note → User | Ownership |
| `TRIGGERED_BY` | Message → Message | Conversation flow |

### Graph Queries (Cypher)

**Find related tasks:**
```cypher
MATCH (u:User {id: 1})-[:BELONGS_TO]-(t:Task)-[:RELATED_TO]-(related:Task)
RETURN t, related
ORDER BY related.created_at DESC
LIMIT 10;
```

**Productivity patterns:**
```cypher
MATCH (u:User {id: 1})-[:BELONGS_TO]-(item)
WHERE item:Task OR item:Event OR item:Note
WITH u, labels(item)[0] as type, COUNT(item) as count
RETURN type, count
ORDER BY count DESC;
```

**Topic co-occurrence:**
```cypher
MATCH (t1:Topic)-[:MENTIONED_IN]->(m:Message)<-[:MENTIONED_IN]-(t2:Topic)
WHERE t1 <> t2
RETURN t1.name, t2.name, COUNT(m) as co_occurrence
ORDER BY co_occurrence DESC
LIMIT 20;
```

---

## 🔴 Dimension 4: Session Context (Redis)

### Architecture

**Key Pattern:** `user:{user_id}:context`

**Data Structure:**
```json
{
  "user_id": 1,
  "session_id": "chat_1_20251203_203000",
  "messages": [
    {
      "id": 145,
      "content": "Merk dir: Milch kaufen",
      "timestamp": "2025-12-03T20:34:24",
      "role": "user",
      "embedding": [0.123, -0.456, ...],  // 384-dim
      "intent": "create_note"
    },
    {
      "id": 146,
      "content": "✅ Notiz \"Milch kaufen\" wurde gespeichert!",
      "timestamp": "2025-12-03T20:34:25",
      "role": "assistant"
    }
    // ... up to 20 messages
  ],
  "current_mood": "neutral",
  "energy_level": 0.7,
  "last_activity": "2025-12-03T20:34:25"
}
```

### TTL (Time-to-Live)

- **Default:** 1 hour (3600 seconds)
- **Sliding Window:** Aktualisiert bei jedem Request
- **Auto-Cleanup:** Redis entfernt abgelaufene Keys automatisch

### Python API

```python
from services.redis_service import RedisService

redis = RedisService()

# Store context
redis.set_user_context(
    user_id=1,
    messages=recent_messages,
    mood="neutral",
    energy=0.7,
    ttl=3600
)

# Retrieve context
context = redis.get_user_context(user_id=1)

# Update (add message)
redis.append_message(user_id=1, message={
    "id": 147,
    "content": "Was habe ich heute zu tun?",
    "role": "user"
})
```

---

## 🔄 Integration Flow

### 1. User Action (Create Note via Chat)

```
User: "Merk dir: Milch kaufen"
  ↓
IntentDetector.detect() → "create_note"
  ↓
ActionExecutor.execute_create_note()
  ↓
PostgreSQL: INSERT INTO notes (title, content, category, user_id)
  ↓
db.refresh(note)  # Get note.id = 5
```

### 2. 4D Memory Storage

```python
store_in_4d_memory(
    db=db,
    user_id=1,
    content_type='note',
    content_id=5,
    content_text="Milch kaufen. Merk dir: Milch kaufen",
    additional_context={'category': 'shopping', 'tags': []}
)
```

**What happens internally:**

#### **Dimension 1: Semantic Memory**
```python
# Generate embedding
embedding = embedding_service.generate_embedding("Milch kaufen. Merk dir: Milch kaufen")
# → 384-dim vector

# Extract topics
topics = extract_topics("Milch kaufen. Merk dir: Milch kaufen")
# → ['milch', 'kaufen']

# Detect intent & emotion
intent = "CHAT"
emotion = "neutral"
importance = 5

# Store in PostgreSQL
INSERT INTO semantic_metadata (
    user_id, content_type, content_id,
    embedding, topics, intent, emotion, importance, content_summary
) VALUES (1, 'note', 5, embedding, topics, intent, emotion, 5, "Milch kaufen. ...");
```

#### **Dimension 2: Temporal Index**
```python
sequence_number = get_next_sequence(user_id=1)  # e.g., 123

INSERT INTO temporal_index (
    user_id, content_type, content_id, sequence_number, session_id
) VALUES (1, 'note', 5, 123, 'chat_1_20251203_203000');
```

#### **Dimension 3: Graph Relations (Neo4j)**
```cypher
// Create Note node
CREATE (n:Note {
    id: 5,
    title: "Milch kaufen",
    category: "shopping",
    created_at: datetime()
})

// Link to User
MATCH (u:User {id: 1})
CREATE (n)-[:BELONGS_TO]->(u)

// Create Topic nodes
CREATE (t1:Topic {name: "milch"})
CREATE (t2:Topic {name: "kaufen"})
CREATE (n)-[:HAS_TOPIC]->(t1)
CREATE (n)-[:HAS_TOPIC]->(t2)

// Link to creating message (if available)
MATCH (m:Message {id: 145})
CREATE (n)-[:CREATED_FROM]->(m)
```

#### **Dimension 4: Session Context (Redis)**
```python
redis.append_message(user_id=1, message={
    "id": 145,
    "content": "Merk dir: Milch kaufen",
    "role": "user",
    "embedding": embedding,
    "intent": "create_note",
    "action_result": {
        "note_id": 5,
        "title": "Milch kaufen",
        "category": "shopping"
    }
})
```

### 3. Result

**All 4 Dimensions updated:**
- ✅ Semantic: Searchable by meaning ("shopping items")
- ✅ Temporal: Retrievable in sequence ("what did I add today?")
- ✅ Graph: Connected to topics, user, and creating message
- ✅ Session: Available in current conversation context

---

## 🔍 Semantic Search Examples

### Find Shopping Items

```python
results = search_semantic_memory(
    db=db,
    user_id=1,
    query="things to buy at grocery store",
    content_types=['note', 'task'],
    limit=5
)

# Results:
# note #5: "Milch kaufen. Merk dir: Milch kaufen" (similarity: 0.87)
# note #3: "Einkaufsliste: Brot, Butter, Eier" (similarity: 0.79)
```

### Find Recent Tasks

```sql
SELECT 
    sm.content_summary,
    ti.sequence_number,
    ti.created_at
FROM semantic_metadata sm
JOIN temporal_index ti ON (
    ti.user_id = sm.user_id 
    AND ti.content_type = sm.content_type 
    AND ti.content_id = sm.content_id
)
WHERE sm.user_id = 1
    AND sm.content_type = 'task'
    AND ti.created_at >= NOW() - INTERVAL '7 days'
ORDER BY ti.sequence_number DESC
LIMIT 10;
```

### Contextual Recall in Chat

**User:** "Was sollte ich einkaufen?"

**AI retrieves from 4D Memory:**
1. Semantic search: "einkaufen" → finds note #5 "Milch kaufen"
2. Redis context: Checks recent conversation
3. Neo4j: Finds related shopping topics
4. Temporal: Orders by recency

**AI Response:**
> "Du hast dir notiert: **Milch kaufen** (heute, 20:34 Uhr). Soll ich dir noch weitere Einkaufsnotizen anzeigen?"

---

## 📊 Statistics & Monitoring

### Count by Content Type

```sql
SELECT 
    content_type,
    COUNT(*) as total,
    COUNT(DISTINCT user_id) as unique_users
FROM semantic_metadata
GROUP BY content_type
ORDER BY total DESC;
```

### Average Importance by Category

```sql
SELECT 
    n.category,
    AVG(sm.importance) as avg_importance,
    COUNT(*) as count
FROM semantic_metadata sm
JOIN notes n ON (sm.content_type = 'note' AND sm.content_id = n.id)
WHERE sm.user_id = 1
GROUP BY n.category
ORDER BY avg_importance DESC;
```

### Storage Size

```sql
SELECT 
    pg_size_pretty(pg_total_relation_size('semantic_metadata')) as table_size,
    COUNT(*) as row_count,
    pg_size_pretty(pg_total_relation_size('semantic_metadata') / COUNT(*)) as avg_row_size
FROM semantic_metadata;
```

---

## 🚀 Performance Optimization

### HNSW Index Tuning

```sql
-- Adjust index parameters for better performance
CREATE INDEX idx_semantic_embedding_hnsw ON semantic_metadata 
USING hnsw (embedding vector_cosine_ops) 
WITH (
    m = 16,                -- Connections per layer (higher = better recall, slower build)
    ef_construction = 64   -- Build-time search depth (higher = better index quality)
);

-- Runtime search quality
SET hnsw.ef_search = 40;  -- Search depth (higher = better recall, slower search)
```

### Vacuuming

```sql
-- Regular maintenance
VACUUM ANALYZE semantic_metadata;
VACUUM ANALYZE temporal_index;

-- Full vacuum (blocks table)
VACUUM FULL semantic_metadata;
```

### Redis Memory Management

```bash
# Set maxmemory policy
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Monitor memory usage
redis-cli INFO memory
```

---

## 🔧 Troubleshooting

### Check if embeddings are generated

```sql
SELECT 
    content_type,
    COUNT(*) as total,
    COUNT(embedding) as with_embedding,
    COUNT(*) - COUNT(embedding) as missing_embedding
FROM semantic_metadata
GROUP BY content_type;
```

### Find items without topics

```sql
SELECT id, content_type, content_id, content_summary
FROM semantic_metadata
WHERE topics IS NULL OR array_length(topics, 1) = 0
LIMIT 10;
```

### Redis connection test

```python
from services.redis_service import RedisService

redis = RedisService()
if redis.ping():
    print("✅ Redis connected")
else:
    print("❌ Redis connection failed")
```

### Neo4j connection test

```python
from services.neo4j_service import Neo4jService

neo4j = Neo4jService()
if neo4j.verify_connectivity():
    print("✅ Neo4j connected")
else:
    print("❌ Neo4j connection failed")
```

---

## 📚 API Reference

### `store_in_4d_memory()`

```python
from services.memory_integration import store_in_4d_memory

store_in_4d_memory(
    db: Session,                    # SQLAlchemy session
    user_id: int,                   # User ID
    content_type: str,              # 'message', 'task', 'event', 'note'
    content_id: int,                # ID of the item
    content_text: str,              # Text to embed
    session_id: Optional[str] = None,
    mood: Optional[str] = None,
    energy_level: Optional[float] = None,
    additional_context: Optional[Dict] = None
) -> int:  # Returns semantic_metadata.id
```

### `search_semantic_memory()`

```python
from services.memory_integration import search_semantic_memory

results = search_semantic_memory(
    db: Session,
    user_id: int,
    query: str,                     # Search query
    content_types: Optional[List[str]] = None,
    limit: int = 10,
    min_similarity: float = 0.5
) -> List[SemanticResult]
```

---

## 🎯 Future Enhancements

- [ ] **Automatic importance adjustment** based on user interactions
- [ ] **Memory consolidation** (merge similar memories)
- [ ] **Forgetting curve** implementation (decay old, unimportant items)
- [ ] **Cross-user pattern analysis** (with privacy controls)
- [ ] **Vector compression** for storage efficiency
- [ ] **Multi-modal embeddings** (images, audio)
- [ ] **Real-time graph updates** via change data capture
- [ ] **Federated search** across all dimensions in single query

---

**Version History:**
- **2.6.0** (2025-12-03): Initial 4D Memory System with full integration
