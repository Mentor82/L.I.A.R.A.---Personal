# 🚀 Liara v3.0 Roadmap - Complete Upgrade Plan

**Current Version:** 2.6.0  
**Target Version:** 3.0.0  
**Created:** 2025-12-03  
**Status:** 📋 Planning Phase

---

## 📊 Overview

This document outlines all necessary changes to transform Liara from v2.6 to v3.0, focusing on **multi-user isolation**, **security hardening**, and **architectural improvements**.

**Total Items:** 18 major change categories  
**Critical Issues:** 5 (must fix immediately)  
**Important Items:** 4 (security & architecture)  
**Quality Improvements:** 6 (UX/Performance)  
**Nice-to-Have:** 4 (future features)

---

## 🔥 1️⃣ CRITICAL (Immediate Action Required)

### A. User Isolation (HIGHEST PRIORITY!)

**Problem:**  
Tasks, Calendar Events, and Notes currently show **ALL entries system-wide**, regardless of which user is logged in. This is a critical privacy and security issue.

**Required Changes:**

- [ ] **Neo4j Schema Update**
  ```cypher
  // Add ownerId to all content nodes
  MATCH (n:Note) SET n.ownerId = 1  // Migrate existing
  MATCH (t:Task) SET t.ownerId = 1
  MATCH (e:Event) SET e.ownerId = 1
  
  // Create constraint
  CREATE CONSTRAINT note_owner IF NOT EXISTS 
  FOR (n:Note) REQUIRE n.ownerId IS NOT NULL
  ```

- [ ] **Default Query Pattern**
  ```cypher
  // All queries MUST filter by ownerId
  MATCH (n:Note { ownerId: $userId })
  WHERE n.visibility IN ['private', 'shared']
  RETURN n
  ```

- [ ] **Admin vs User Access**
  - Admin role: Can see ALL data (with owner info displayed)
  - User role: Only see own data + explicitly shared items
  - API returns `403 Forbidden` if user tries to access foreign content

- [ ] **Prepare Sharing System**
  - Add `visibility` field: `private` | `shared` | `public`
  - Add `sharedWith` array: `[userId1, userId2, ...]`
  - Default: `visibility = 'private'`

- [ ] **Frontend Filtering**
  - Already filters by `session.user.id` client-side
  - Add server-side enforcement (double security)

**Files to Modify:**
- `/opt/liara/app/api/routers/tasks_router.py`
- `/opt/liara/app/api/routers/calendar_router.py`
- `/opt/liara/app/api/routers/notes_router.py`
- `/opt/liara/app/services/neo4j_service.py`

**Estimated Effort:** 8 hours  
**Risk Level:** HIGH (breaks existing data if not migrated properly)

---

### B. Auth Flow / Session Fix

**Problems:**
- Guest mode sessions get lost unexpectedly
- JWT tokens not refreshed automatically
- Login sometimes stuck in redirect loop
- Session state inconsistent between frontend/backend

**Required Changes:**

- [ ] **Refresh Token Implementation**
  ```python
  # /opt/liara/app/api/routers/auth_router.py
  @router.post("/refresh")
  async def refresh_token(refresh_token: str):
      # Validate refresh token
      # Issue new access token
      # Return new token pair
  ```

- [ ] **Redis Session Storage**
  ```python
  # Store session in Redis instead of only local cookie
  redis.setex(
      f"session:{user_id}",
      3600,  # 1 hour TTL
      json.dumps({
          "user_id": user_id,
          "username": username,
          "role": role,
          "last_activity": datetime.now().isoformat()
      })
  )
  ```

- [ ] **Stabilize /auth/me Endpoint**
  ```python
  @router.get("/me")
  async def get_current_user(
      current_user: User = Depends(require_active_user)
  ):
      # Return full user profile
      # Include permissions, settings, preferences
      # Never fail silently - return proper error codes
  ```

- [ ] **Fix Calendar/Notes Redirects**
  - Remove redirect loops in protected routes
  - Clear token validation logic
  - Proper error messages on auth failure

**Files to Modify:**
- `/opt/liara/app/api/routers/auth_router.py`
- `/opt/liara/app/core/dependencies.py`
- `/opt/liara/app/services/redis_service.py`
- `/opt/liara/frontend/src/utils/auth.js`

**Estimated Effort:** 6 hours  
**Risk Level:** MEDIUM

---

### C. Calendar - Event Leak

**Problem:**  
Calendar shows events from **all users**, not just the logged-in user.

**Required Changes:**

- [ ] **Backend Filtering**
  ```python
  # /opt/liara/app/api/routers/calendar_router.py
  @router.get("/")
  async def list_events(
      current_user: User = Depends(require_active_user),
      db: Session = Depends(get_db)
  ):
      # MUST filter by user_id
      events = db.query(CalendarEvent).filter(
          CalendarEvent.user_id == current_user.id
      ).all()
  ```

- [ ] **No Global Queries**
  ```cypher
  // WRONG (shows all events)
  MATCH (e:Event) RETURN e
  
  // CORRECT (user-scoped)
  MATCH (e:Event { ownerId: $userId }) RETURN e
  ```

- [ ] **Event Details with Owner Check**
  ```python
  @router.get("/{event_id}")
  async def get_event(
      event_id: int,
      current_user: User = Depends(require_active_user),
      db: Session = Depends(get_db)
  ):
      event = db.query(CalendarEvent).filter_by(id=event_id).first()
      if event.user_id != current_user.id and current_user.role != "admin":
          raise HTTPException(status_code=403, detail="Access denied")
      return event
  ```

- [ ] **Separate Admin View**
  ```python
  @router.get("/admin/all-events")
  async def admin_list_all_events(
      current_user: User = Depends(require_admin)
  ):
      # Admin can see all events with owner info
  ```

**Files to Modify:**
- `/opt/liara/app/api/routers/calendar_router.py`
- `/opt/liara/frontend/src/pages/Calendar.jsx`

**Estimated Effort:** 3 hours  
**Risk Level:** LOW

---

### D. Notes - Global Notes Visible

**Problem:**  
Notes are visible across all users.

**Required Changes:**

- [ ] **Add Owner Field to Schema**
  ```cypher
  MATCH (n:Note) 
  SET n.ownerId = 1,  // Default migration
      n.visibility = 'private'
  ```

- [ ] **Enforce Filtering in API**
  ```python
  @router.get("/")
  async def list_notes(
      current_user: User = Depends(require_active_user),
      db: Session = Depends(get_db)
  ):
      notes = db.query(Note).filter(
          Note.user_id == current_user.id,
          Note.is_archived == False
      ).all()
  ```

- [ ] **Prepare Sharing Field**
  ```sql
  ALTER TABLE notes ADD COLUMN visibility VARCHAR(20) DEFAULT 'private';
  ALTER TABLE notes ADD COLUMN shared_with INTEGER[];
  ```

- [ ] **UI Pre-fill with Session User**
  ```jsx
  // Frontend: Always set user_id from session
  const createNote = async (noteData) => {
      const payload = {
          ...noteData,
          user_id: session.user.id  // Auto-inject
      };
      await api.post('/notes', payload);
  };
  ```

**Files to Modify:**
- `/opt/liara/app/api/routers/notes_router.py`
- `/opt/liara/app/api/models/base_models.py` (add visibility field)
- `/opt/liara/frontend/src/pages/Notes.jsx`

**Estimated Effort:** 3 hours  
**Risk Level:** LOW

---

### E. Tasks - Global Tasks Visible

**Problem:**  
Same as Notes - tasks are visible across all users.

**Required Changes:**  
(Identical to Notes section above)

- [ ] Add `tasks.ownerId` to Neo4j
- [ ] Add `tasks.visibility` to PostgreSQL
- [ ] Enforce user_id filtering in all queries
- [ ] Separate admin view from user view

**Files to Modify:**
- `/opt/liara/app/api/routers/tasks_router.py`
- `/opt/liara/frontend/src/pages/Tasks.jsx`

**Estimated Effort:** 3 hours  
**Risk Level:** LOW

---

## 📌 2️⃣ IMPORTANT (Security & Architecture)

### F. Neo4j - Structure Hardening

**Current State:**  
No constraints, no indexes, no data integrity guarantees.

**Required Changes:**

- [ ] **Unique Constraints**
  ```cypher
  CREATE CONSTRAINT user_id_unique IF NOT EXISTS
  FOR (u:User) REQUIRE u.id IS UNIQUE;
  
  CREATE CONSTRAINT task_id_unique IF NOT EXISTS
  FOR (t:Task) REQUIRE t.id IS UNIQUE;
  
  CREATE CONSTRAINT note_id_unique IF NOT EXISTS
  FOR (n:Note) REQUIRE n.id IS UNIQUE;
  
  CREATE CONSTRAINT event_id_unique IF NOT EXISTS
  FOR (e:Event) REQUIRE e.id IS UNIQUE;
  ```

- [ ] **Performance Indexes**
  ```cypher
  CREATE INDEX user_username IF NOT EXISTS
  FOR (u:User) ON (u.username);
  
  CREATE INDEX note_owner IF NOT EXISTS
  FOR (n:Note) ON (n.ownerId);
  
  CREATE INDEX task_owner IF NOT EXISTS
  FOR (t:Task) ON (t.ownerId);
  ```

- [ ] **Relationship Cleanup**
  ```cypher
  // Standardize relationship naming
  MATCH (t:Task)-[r:TASK_CREATED_BY]->(u:User)
  CREATE (t)-[:BELONGS_TO]->(u)
  DELETE r;
  
  // Notes
  MATCH (n:Note)-[old]->(u:User)
  WHERE type(old) <> 'BELONGS_TO'
  CREATE (n)-[:BELONGS_TO]->(u)
  DELETE old;
  ```

**Estimated Effort:** 4 hours  
**Risk Level:** MEDIUM (can break existing queries)

---

### G. API Consistency Fix

**Problem:**  
Heterogeneous API response formats across different endpoints.

**Required Changes:**

- [ ] **Standardize Response Structure**
  ```python
  # All endpoints return this format
  {
      "success": true|false,
      "data": { ... },  // On success
      "error": { ... },  // On failure
      "metadata": {
          "timestamp": "2025-12-03T...",
          "request_id": "uuid...",
          "version": "3.0.0"
      }
  }
  ```

- [ ] **HTTP Status Codes**
  - `200` - Success
  - `201` - Created
  - `400` - Bad Request (validation error)
  - `401` - Unauthorized (no token / invalid token)
  - `403` - Forbidden (valid user, but no permission)
  - `404` - Not Found
  - `500` - Internal Server Error

- [ ] **Enhance /info Endpoint**
  ```python
  @app.get("/info")
  def enhanced_info():
      return {
          "success": true,
          "data": {
              "version": "3.0.0",
              "hostname": platform.node(),
              "uptime_seconds": time.time() - START_TIME,
              "health": "healthy",
              "features": {
                  "4d_memory": true,
                  "multi_user": true,
                  "sharing": true
              }
          }
      }
  ```

- [ ] **Unify /dashboard/info**
  - Consistent metric names
  - Same timestamp format everywhere
  - Clear data/metadata separation

- [ ] **Dynamic /chat/models**
  ```python
  @router.get("/models")
  async def list_models():
      # Query Ollama dynamically
      ollama_models = requests.get("http://localhost:11434/api/tags").json()
      return {
          "success": true,
          "data": {
              "models": ollama_models["models"],
              "default": "llama3.2:3b",
              "count": len(ollama_models["models"])
          }
      }
  ```

**Estimated Effort:** 6 hours  
**Risk Level:** LOW (backwards compatible possible)

---

### H. 4D Memory Integration (Clean Architecture)

**Current State:**  
Rough integration, no clear boundaries between memory dimensions.

**Required Changes:**

- [ ] **Memory Buckets**
  ```python
  class MemoryBucket(Enum):
      LONG_TERM = "long_term"      # semantic_metadata
      SHORT_TERM = "short_term"     # Redis (20 messages)
      EPISODIC = "episodic"         # temporal_index
      PERSONA = "persona"           # User preferences, personality
  ```

- [ ] **Event-Trigger per Interaction**
  ```python
  @router.post("/chat/stream")
  async def stream_chat(...):
      # Trigger memory storage
      await memory_service.store_interaction(
          user_id=current_user.id,
          interaction_type="chat",
          content=request.message,
          buckets=[MemoryBucket.SHORT_TERM, MemoryBucket.EPISODIC]
      )
  ```

- [ ] **Memory Relevance Scoring**
  ```python
  def calculate_relevance(memory, current_context):
      # Recency: newer = higher score
      recency_score = 1.0 / (1 + days_since_creation)
      
      # Semantic similarity
      similarity = cosine_similarity(
          memory.embedding,
          current_context.embedding
      )
      
      # Importance (user-defined or auto-calculated)
      importance = memory.importance / 10.0
      
      # Combined score
      return 0.3 * recency_score + 0.5 * similarity + 0.2 * importance
  ```

**Estimated Effort:** 8 hours  
**Risk Level:** MEDIUM

---

### I. Logging System Improvement

**Current State:**  
Inconsistent logging, no request tracing, verbose error traces.

**Required Changes:**

- [ ] **Repair Admin Logs Page**
  - Fix `/admin/logs` endpoint
  - Stream last 100 log entries
  - Filter by level (INFO, WARNING, ERROR)

- [ ] **Request UUID Tracking**
  ```python
  import uuid
  from fastapi import Request
  
  @app.middleware("http")
  async def add_request_id(request: Request, call_next):
      request_id = str(uuid.uuid4())
      request.state.request_id = request_id
      
      logger.info(f"[{request_id}] {request.method} {request.url.path}")
      response = await call_next(request)
      response.headers["X-Request-ID"] = request_id
      return response
  ```

- [ ] **Safe Error Traces**
  ```python
  # Production mode: hide internal details
  if settings.ENVIRONMENT == "production":
      error_detail = "Internal server error"
  else:
      error_detail = str(exception)
  ```

- [ ] **Crash Memory in Neo4j**
  ```cypher
  CREATE (crash:CrashLog {
      timestamp: datetime(),
      request_id: $request_id,
      error_type: $error_type,
      stack_trace: $stack_trace,
      user_id: $user_id,
      endpoint: $endpoint
  })
  ```

**Estimated Effort:** 5 hours  
**Risk Level:** LOW

---

## ⭐ 3️⃣ QUALITY (UX, Performance, Polish)

### J. UI/UX - Calendar Improvements

- [ ] **Event Modal**
  - Click event → show details modal
  - Edit in-place
  - Quick delete with confirmation

- [ ] **Multiple Views**
  - Day view (hourly slots)
  - Week view (7 columns)
  - Month view (grid layout)
  - Smooth transitions between views

- [ ] **Drag & Drop (Optional)**
  - Move events between time slots
  - Resize event duration
  - Visual feedback during drag

- [ ] **Category Colors**
  - meeting: blue
  - reminder: yellow
  - appointment: green
  - custom: user-defined

**Estimated Effort:** 12 hours  
**Risk Level:** LOW

---

### K. UI/UX - Notes Improvements

- [ ] **Rich Text Mode**
  - Markdown support
  - Plain text fallback
  - Preview/Edit toggle

- [ ] **Tags System**
  - Add multiple tags per note
  - Tag autocomplete
  - Filter notes by tags

- [ ] **Full-Text Search**
  - Search in title + content
  - Highlight matches
  - Sort by relevance

**Estimated Effort:** 8 hours  
**Risk Level:** LOW

---

### L. UI/UX - Tasks Improvements

- [ ] **Subtasks**
  - Nested task structure
  - Parent/child relationships
  - Progress tracking (3/5 subtasks done)

- [ ] **Priorities**
  - High/Medium/Low visual indicators
  - Sort by priority
  - Color-coded borders

- [ ] **Due Date Warnings**
  - Red badge if overdue
  - Yellow badge if due today
  - Notification icon if due within 3 days

- [ ] **Sorting & Filtering**
  - Sort: priority, due date, created date
  - Filter: completed, active, all
  - Search by title

**Estimated Effort:** 10 hours  
**Risk Level:** LOW

---

### M. Chat / LLM Integration

- [ ] **Model Selector Modal**
  - Show all available Ollama models
  - Display model size, RAM usage
  - Quick-switch button in chat

- [ ] **Response Length Mode**
  - Short: max 100 tokens (quick answers)
  - Medium: max 500 tokens (default)
  - Long: max 2000 tokens (detailed)

- [ ] **Per-User System Prompt**
  ```python
  # Store in users table
  user.system_prompt = "You are a helpful assistant focused on..."
  
  # Use in chat
  messages = [
      {"role": "system", "content": user.system_prompt},
      {"role": "user", "content": message}
  ]
  ```

**Estimated Effort:** 6 hours  
**Risk Level:** LOW

---

### N. Terminal in Admin Area

- [ ] **Command Scope Limitation**
  - Whitelist: `ls`, `cat`, `systemctl status`, `journalctl`
  - Blacklist: `rm`, `dd`, `mkfs`, etc.
  - Admin-only access

- [ ] **Command History**
  - Store last 50 commands
  - Arrow-up to recall
  - Clear history button

- [ ] **Auto-Scroll Fix**
  - Scroll to bottom on new output
  - Manual scroll: pause auto-scroll
  - Resume auto-scroll on new command

**Estimated Effort:** 4 hours  
**Risk Level:** MEDIUM (security implications)

---

## ✨ 4️⃣ NICE TO HAVE (Future Features)

### O. Profile Templates

- [ ] Mood-based color schemes
- [ ] Light/Dark theme selection
- [ ] AI-generated avatars (Stable Diffusion)
- [ ] Custom CSS overrides

**Estimated Effort:** 8 hours

---

### P. Sharing System (Complete)

- [ ] **Share Notes**
  - Select users to share with
  - View-only or edit permissions
  - Revoke sharing

- [ ] **Share Calendar Events**
  - Team events
  - Public events (URL sharing)

- [ ] **Assign Tasks**
  - Assign to other users
  - Task ownership transfer
  - Collaborative task lists

- [ ] **Visibility Levels**
  - `private`: Only owner
  - `shared`: Selected users
  - `team`: All team members
  - `public`: Everyone (read-only)

**Estimated Effort:** 16 hours

---

### Q. AI Profile Builder

Based on PERSONA.md:

- [ ] **Configure AI Core**
  - Trait sliders: warm, playful, analytical, calm
  - Personality presets
  - Custom descriptions

- [ ] **Temperature/Top-P UI**
  - Visual sliders
  - Explain what they do
  - Per-user settings

- [ ] **Personalized Responses**
  - AI adapts to user's trait configuration
  - Learning from interactions

**Estimated Effort:** 12 hours

---

### R. Multi-Agent System Preparation

- [ ] **Cortana** (Dev Agent)
  - Code generation
  - Technical documentation
  - System diagnostics

- [ ] **Nephy** (Experience Agent)
  - Creative writing
  - Storytelling
  - Entertainment

- [ ] **Liara** (Daily Agent)
  - Task management
  - Calendar planning
  - General assistance

- [ ] **Separate APIs per Agent**
  - `/cortana/chat`
  - `/nephy/chat`
  - `/liara/chat` (default)

**Estimated Effort:** 24 hours

---

## ❤️ Bonus: Future Vision (v3.0+)

**What Liara will enable later:**

1. **Multi-User Multi-Context**
   - Isolated data spaces per user
   - No cross-contamination
   - Scalable to 1000+ users

2. **Private Data Cells**
   - Each user has own Neo4j namespace
   - Encrypted data at rest
   - Zero-knowledge architecture possible

3. **LLM Memory**
   - Persistent conversation memory
   - Long-term learning
   - Personality evolution

4. **Plugin System**
   - Third-party integrations
   - Custom actions
   - Webhook support

5. **Full Offline Capability**
   - Local-first architecture
   - Sync when online
   - Progressive Web App (PWA)

6. **User Groups**
   - Family workspace
   - Work workspace
   - Guest mode
   - Role-based permissions

---

## 📋 Implementation Plan

### Phase 1: Critical Fixes (Week 1)
- A. User Isolation
- B. Auth Flow Fix
- C. Calendar Event Leak
- D. Notes Global Visibility
- E. Tasks Global Visibility

**Total Effort:** ~23 hours

### Phase 2: Architecture (Week 2)
- F. Neo4j Hardening
- G. API Consistency
- H. 4D Memory Clean Architecture
- I. Logging System

**Total Effort:** ~23 hours

### Phase 3: Quality & UX (Week 3-4)
- J. Calendar UI
- K. Notes UI
- L. Tasks UI
- M. Chat/LLM
- N. Terminal

**Total Effort:** ~40 hours

### Phase 4: Future Features (v3.1+)
- O. Profile Templates
- P. Sharing System
- Q. AI Profile Builder
- R. Multi-Agent System

**Total Effort:** ~60 hours

---

**Grand Total Estimated Effort:** ~146 hours (~4 weeks full-time)

**Version Release Plan:**
- v2.7.0: Critical fixes (Phase 1)
- v2.8.0: Architecture improvements (Phase 2)
- v2.9.0: Quality & UX (Phase 3)
- v3.0.0: Future features (Phase 4)

---

**Last Updated:** 2025-12-03  
**Document Version:** 1.0  
**Status:** Ready for implementation 🚀
