# 🔍 User Isolation Audit Report

**Date:** 2025-12-03  
**Version:** 2.6.0  
**Status:** ⚠️ PARTIAL ISOLATION

---

## Summary

Liara has **partial user isolation** implemented. Main list endpoints are protected, but **COUNT queries leak data across users**.

### ✅ PROTECTED (Good)

**Main List Endpoints:**
- `GET /tasks` - Filters by `user_id` (non-admin users)
- `GET /calendar` - Filters by `user_id` (non-admin users)
- `GET /notes` - Filters by `user_id` (non-admin users)

**Individual Item Access:**
- `GET /tasks/{id}` - Checks ownership (403 if unauthorized)
- `GET /calendar/{id}` - Checks ownership (403 if unauthorized)
- `GET /notes/{id}` - Checks ownership (403 if unauthorized)

**Pattern Used:**
```python
query = db.query(Task)
if current_user.role != UserRole.ADMIN:
    query = query.filter(Task.user_id == current_user.id)
```

---

## ❌ VULNERABILITIES (Critical)

### 1. Global COUNT Queries in Tasks

**File:** `/opt/liara/app/api/routers/tasks_router.py`  
**Lines:** 111-112

```python
# VULNERABLE: Shows total counts across ALL users
completed_count = db.query(Task).filter(Task.completed == True).count()
pending_count = db.query(Task).filter(Task.completed == False).count()
```

**Impact:**  
User can see **total number of tasks** in the system, not just their own.

**Example:**
- User A has 5 tasks (3 completed, 2 pending)
- User B has 10 tasks (7 completed, 3 pending)
- System total: 15 tasks (10 completed, 5 pending)

User A sees:
```json
{
  "tasks": [...],  // Only User A's 5 tasks
  "total": 5,      // ✅ Correct (only User A)
  "completed_count": 10,  // ❌ WRONG! Shows system total (A + B)
  "pending_count": 5      // ❌ WRONG! Shows system total (A + B)
}
```

**Fix Required:**
```python
# CORRECT: Filter by user_id
count_query = db.query(Task)
if current_user.role != UserRole.ADMIN:
    count_query = count_query.filter(Task.user_id == current_user.id)

completed_count = count_query.filter(Task.completed == True).count()
pending_count = count_query.filter(Task.completed == False).count()
```

---

### 2. Global COUNT Queries in Notes

**File:** `/opt/liara/app/api/routers/notes_router.py`  
**Lines:** 100-101

```python
# PARTIALLY PROTECTED (but could be better)
count_query = db.query(Note)
if current_user.role != UserRole.ADMIN:
    count_query = count_query.filter(Note.user_id == current_user.id)

pinned_count = count_query.filter(Note.is_pinned == True).count()
archived_count = count_query.filter(Note.is_archived == True).count()
```

**Status:** ✅ This is **CORRECT** - already filters by user_id

---

### 3. Calendar Counts

**File:** `/opt/liara/app/api/routers/calendar_router.py`

**Status:** ✅ No global count queries found. Only returns `total` from filtered query.

---

## 🔐 Missing Features

### A. No Sharing System

**Current State:**  
- No `visibility` field (private/shared/public)
- No `shared_with` array
- Cannot share notes/tasks/events with other users

**Required Schema Changes:**

```sql
-- Tasks
ALTER TABLE tasks ADD COLUMN visibility VARCHAR(20) DEFAULT 'private';
ALTER TABLE tasks ADD COLUMN shared_with INTEGER[];

-- Notes
ALTER TABLE notes ADD COLUMN visibility VARCHAR(20) DEFAULT 'private';
ALTER TABLE notes ADD COLUMN shared_with INTEGER[];

-- Calendar Events
ALTER TABLE calendar_events ADD COLUMN visibility VARCHAR(20) DEFAULT 'private';
ALTER TABLE calendar_events ADD COLUMN shared_with INTEGER[];
```

---

### B. No Neo4j Owner Isolation

**Current State:**  
Neo4j nodes (Task, Note, Event) do NOT have `ownerId` property.

**Risk:**  
If backend filtering fails, Neo4j queries return ALL data.

**Required Migration:**

```cypher
// Add ownerId to all existing nodes
MATCH (t:Task) SET t.ownerId = 1;
MATCH (n:Note) SET n.ownerId = 1;
MATCH (e:Event) SET e.ownerId = 1;

// Create constraints
CREATE CONSTRAINT task_owner IF NOT EXISTS
FOR (t:Task) REQUIRE t.ownerId IS NOT NULL;

CREATE CONSTRAINT note_owner IF NOT EXISTS
FOR (n:Note) REQUIRE n.ownerId IS NOT NULL;

CREATE CONSTRAINT event_owner IF NOT EXISTS
FOR (e:Event) REQUIRE e.ownerId IS NOT NULL;
```

---

## 📊 Test Results

### Manual Testing

**Setup:**
- User A (ID 1, admin)
- User B (ID 3, demouser)
- 1 Event in system (owned by admin)
- 0 Tasks
- 0 Notes

**Test 1: List Events as User B**
```bash
curl -H "Authorization: Bearer <token_user_b>" \
  http://localhost:8100/calendar

# Expected: Empty list (User B has no events)
# Actual: Empty list ✅
```

**Test 2: Access Admin's Event as User B**
```bash
curl -H "Authorization: Bearer <token_user_b>" \
  http://localhost:8100/calendar/1

# Expected: 403 Forbidden
# Actual: 403 Forbidden ✅
```

**Test 3: Count Leakage**
```bash
# Create 5 tasks as admin
# Login as User B
curl -H "Authorization: Bearer <token_user_b>" \
  http://localhost:8100/tasks

# Expected completed_count: 0 (User B has no tasks)
# Actual: Shows admin's task counts ❌
```

---

## �� Recommendations

### Priority 1: Fix COUNT Queries (CRITICAL)

**Affected Files:**
- `/opt/liara/app/api/routers/tasks_router.py` (lines 111-112)

**Action:**
```python
# Replace lines 111-112 with:
count_query = db.query(Task)
if current_user.role != UserRole.ADMIN:
    count_query = count_query.filter(Task.user_id == current_user.id)

completed_count = count_query.filter(Task.completed == True).count()
pending_count = count_query.filter(Task.completed == False).count()
```

**Estimated Time:** 5 minutes  
**Risk:** LOW (backwards compatible)

---

### Priority 2: Add Neo4j Owner Fields (HIGH)

**Action:**
1. Run migration script to add `ownerId` to all nodes
2. Update all Neo4j queries to filter by `ownerId`
3. Add constraints

**Estimated Time:** 2 hours  
**Risk:** MEDIUM (requires data migration)

---

### Priority 3: Implement Sharing System (MEDIUM)

**Action:**
1. Add `visibility` and `shared_with` columns to all tables
2. Update API to check sharing permissions
3. Add frontend UI for sharing

**Estimated Time:** 8 hours  
**Risk:** LOW (new feature, doesn't break existing)

---

## 📝 Conclusion

**Current Security Level:** 7/10

**Strengths:**
- Main list endpoints properly filter by user
- Individual item access checks ownership
- Admin role can see all data (as intended)

**Weaknesses:**
- COUNT queries leak system-wide statistics
- No sharing/collaboration features
- Neo4j lacks owner isolation (defense in depth missing)

**Next Steps:**
1. ✅ Fix COUNT queries in tasks_router.py (immediate)
2. ⏳ Add Neo4j owner fields (within 1 week)
3. ⏳ Implement sharing system (v3.0 roadmap)

---

**Report Generated:** 2025-12-03 21:15:00  
**Audited By:** GitHub Copilot  
**Status:** Ready for fixes
