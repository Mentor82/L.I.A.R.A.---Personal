# Liara Changelog

All notable changes to this project will be documented in this file.

## [2.7.0] - 2025-12-03

### Added - Multi-Threading Production Deployment
- **Gunicorn + Uvicorn Workers for true multi-processing**
  - Replaced single-threaded Uvicorn with Gunicorn process manager
  - 17 UvicornWorker instances (formula: CPU cores * 2 + 1)
  - Performance: ~5300 requests/second (10x improvement vs single-threaded)
  - Memory usage: ~14 GB total (~820 MB per worker)

### Changed
- **System Architecture**
  - Added Gunicorn 23.0.0 as WSGI server / process manager
  - Updated systemd service: `liara-backend.service`
  - Service configuration: `Type=simple`, `WorkingDirectory=/opt/liara/app`
  - Disabled old `liara.service` to prevent port conflicts

### Scripts
- **restart_backend.sh**: Updated for Gunicorn + workers
  - Dynamic worker calculation based on CPU cores
  - Proper process cleanup (kills both uvicorn and gunicorn)
  - Daemon mode with health check
- **start_backend.sh**: Foreground mode for systemd
  - Uses `exec` for proper signal handling
  - No `--daemon` flag (systemd manages process)

### Performance
- **Benchmark Results** (8-core system):
  - Requests/second: 5348 req/s
  - Latency: 0.187 ms per request (mean, concurrent)
  - Concurrent connections: 50 tested successfully
  - Note: Some failed requests under extreme load (DB pool limits)

### Known Issues
- **Database connection pooling** needs optimization for high concurrency
  - Current failures at 50+ concurrent connections
  - Recommendation: Increase `POOL_SIZE` in database config
  - Future work: Migrate to async SQLAlchemy 2.0 + asyncpg (Phase 2)

### Next Steps (Roadmap)
- **Phase 2**: Async SQLAlchemy 2.0 + asyncpg for non-blocking DB
- **Phase 3**: Replace `requests` with `httpx.AsyncClient` for async HTTP

## [2.6.1] - 2025-12-03

### Fixed - User Isolation Critical Bug
- **Tasks count queries leaked global statistics**
  - Fixed `completed_count` and `pending_count` in `/api/routers/tasks_router.py`
  - Counts now properly filtered by `user_id` for non-admin users
  - Previously showed system-wide task counts to all users (security issue)
  - Impact: Users could infer total number of tasks in system

### Security
- **User Isolation Audit completed**
  - Created comprehensive audit report: `/docs/USER_ISOLATION_AUDIT.md`
  - ✅ Calendar API: Fully isolated
  - ✅ Notes API: Fully isolated
  - ✅ Tasks API: Fixed (was leaking count data)
  - All individual item endpoints (GET /{id}) have proper ownership checks

### Documentation
- Added `/docs/USER_ISOLATION_AUDIT.md` with detailed security analysis
- Documented recommendations for future improvements (Neo4j owner fields, sharing system)

## [2.6.0] - 2025-12-03

### Added - 4D Memory Integration for Productivity Items
- **Tasks, Events, and Notes now fully integrated with 4D Memory System**
  - All productivity items (created via chat) are stored in `semantic_metadata`
  - Embeddings (384-dim) generated for semantic search capabilities
  - Topics automatically extracted from content
  - Intent, emotion, and importance scores calculated
  - Enables AI to remember and contextually recall user's tasks, events, and notes

- **action_executor.py completely rebuilt**
  - `store_in_4d_memory()` integration for all three create methods:
    - `execute_create_event()` - Stores event with type, location, timestamps
    - `execute_create_task()` - Stores task with priority, tags, completion status
    - `execute_create_note()` - Stores note with category, tags, pinned status
  - Robust error handling with try-except blocks
  - Detailed logging for 4D Memory operations

### Technical Details
- **Files Modified:**
  - `/opt/liara/app/liara_engine/actions/action_executor.py` (364 lines, rebuilt from scratch)
  - `/opt/liara/app/api/routers/chat_streaming.py` (fixed undefined variable bug)

- **4D Memory Storage:**
  - Dimension 1: PostgreSQL `semantic_metadata` table with pgvector embeddings
  - Dimension 2: PostgreSQL `temporal_index` for sequence tracking
  - Dimension 3: Neo4j graph relationships (CREATED_FROM, RELATED_TO)
  - Dimension 4: Redis session context (20-message window)

### Testing Results
- ✅ Note creation via chat: "Merk dir: Milch kaufen"
  - Created note ID 5 in `notes` table
  - Created 4D Memory entry ID 46 in `semantic_metadata`
  - Generated 384-dim embedding
  - Extracted topics: `{milch,kaufen}`
  - Auto-categorized as `shopping`
  - Intent: `CHAT`, Emotion: `neutral`, Importance: `5`

### Impact
- Users can now search for tasks/events/notes semantically
- AI can recall productivity items in context during conversations
- Pattern analysis possible (e.g., "show shopping-related notes from last week")
- Foundation for predictive suggestions based on user's productivity patterns

## [2.5.0] - 2025-12-03

### Fixed - Notizen & Erinnerungen aus Chat
- **Intent Detection für Notizen erweitert**
  - Pattern `merk\s+(?:dir|es)` für "merk dir" / "merk es"
  - Pattern `(?:erinner|remind).*(?:mich|me)` für Erinnerungen
  - Pattern `(?:neue|create)\s+(?:erinnerung|reminder)` für "neue Erinnerung"
  - Alle Varianten werden jetzt korrekt als `create_note` erkannt

- **Titel-Extraktion verbessert**
  - Multi-Pattern System mit 5 verschiedenen Patterns:
    1. Doppelpunkt-Syntax: "merk dir: TEXT"
    2. "dass"-Pattern: "merk dir dass TEXT"
    3. "an"-Pattern: "erinnere mich an TEXT"
    4. "to"-Pattern: "remind me to TEXT"
    5. Anführungszeichen: "Notiz 'TEXT'"
  - Intelligente Bereinigung von Trigger-Wörtern
  - Fallback auf erste 50 Zeichen wenn kein Pattern matched

- **Auto-Kategorisierung hinzugefügt**
  - `meetings`: meeting, besprechung, call, protokoll
  - `ideas`: idee, idea, brainstorm
  - `shopping`: einkauf, shopping, kaufen, besorgen
  - `health`: arzt, doctor, health, gesundheit

### Technical Changes
- `/opt/liara/app/liara_engine/actions/intent_detector.py`:
  - PATTERNS['create_note']: 4 Patterns (war 1)
  - extract_note_details(): Komplett überarbeitet
  - Regex-Patterns optimiert für deutsche & englische Sprache

### Testing
- Alle Test-Cases bestanden:
  - ✅ "merk dir: Einkaufen gehen"
  - ✅ "merk dir dass ich morgen zum Arzt muss"
  - ✅ "erinnere mich an Geburtstag"
  - ✅ "remind me to call John"
  - ✅ "neue Erinnerung: Meeting um 14 Uhr"

## [2.4.0] - 2025-12-03

### Added - UI Modernisierung
- **Tasks UI Redesign**
  - Google Calendar/Outlook-inspired design system
  - Header with dark background and glassmorphism
  - Modern forms with focus effects and shadows
  - Priority-based border indicators (left, 4px)
  - Hover effects with slide animation (translateX)
  - Improved button styles with gradients
  - Mood integration with contextual suggestions
  - Responsive design for mobile/tablet/desktop
  
- **Notes UI Redesign**
  - Card-grid layout with auto-fill columns
  - Glassmorphism effects on all panels
  - Pinned notes with golden border highlighting
  - Hover animation with lift effect (translateY)
  - Gradient border indicator (left, appears on hover)
  - Improved search box with pill design
  - Tag/category badges with color coding
  - Content truncation with -webkit-line-clamp
  - Responsive grid (1 column on mobile)

### Improved
- **Unified Design System**
  - Consistent styling across Calendar/Tasks/Notes
  - Shared color palette and spacing system
  - Smooth transitions on all interactive elements
  - Box shadows with theme colors (purple/pink gradients)
  - Improved accessibility (larger click targets, better contrast)

### Technical
- **CSS Enhancements**
  - Tasks.css: 487 lines (from 353)
  - Notes.css: 626 lines (from 415)
  - Better organized with commented sections
  - Comprehensive media queries for responsive design
  - Build size: 96.97 kB CSS (gzip: 16.62 kB)

## [2.3.0] - 2025-12-03

### Added - Week & Day Views
- **Week View (7-Day Timeline)**
  - Horizontal grid with 7 days (Mon-Sun)
  - 24-hour timeline (60px per hour)
  - Events as colored blocks with precise positioning
  - Week number (KW) in navigation
  - Automatic positioning based on start/end time
  - Hover effects with scale animation
  
- **Day View (Single-Day Detail)**
  - Full 24-hour time axis
  - Events with full width and details
  - Time range, title, location, description visible
  - Larger event blocks for better readability
  - Auto-scrolling to events (planned)
  
- **Dynamic Navigation**
  - Back/Forward adapts to current view:
    - Month: ±1 month
    - Week: ±7 days
    - Day: ±1 day
  - "Today" button works in all views
  - Week number display in week view
  - Full date display in day view
  
- **Event Positioning Logic**
  - Calculation based on time (minutes since midnight)
  - Height = duration in minutes
  - Top position = start time
  - 60px = 1 hour standard
  
- **Responsive Optimizations**
  - Week view: 7 columns on desktop, scrollable on mobile
  - Day view: Full width on all devices
  - Time axis always visible (sticky)

### Changed
- `CalendarView.jsx`: Added week/day rendering logic
- `CalendarView.css`: Added 200+ lines for week/day styles
- Navigation buttons now context-aware

## [2.2.0] - 2025-12-03

### Added - Google Calendar Style UI
- **Full Calendar View** with Month/Week/Day switching
  - 42-day grid (6 weeks) for complete month view
  - Monday as first day of week (European standard)
  - Navigation: Previous/Today/Next buttons
  - Current day highlighting
  
- **Event Display in Grid**
  - Up to 3 events visible per day
  - "+X more" indicator for days with many events
  - Color-coded event types (💼 Meeting, 🏠 Private, 📌 Other)
  - Time and title visible at a glance
  
- **Selected Date Sidebar**
  - Right-slide sidebar when clicking a day
  - Full event details (time, location, description)
  - Delete function directly in sidebar
  - "Add event" button for empty days
  
- **Quick-Add Feature**
  - Double-click on day to open create form
  - Start/end time auto-set to 9-10am
  
- **Responsive Design**
  - Desktop: Sidebar 350px right
  - Tablet: Sidebar 300px
  - Mobile: Sidebar fullscreen
  
- **New Components**
  - `CalendarView.jsx` - Main calendar component
  - `CalendarView.css` - Google Calendar-inspired design

### Changed
- `App.jsx`: Import CalendarView instead of Calendar
- Calendar route now uses new CalendarView component

## [2.1.0] - 2025-12-03

### Added - Event Detection Improvements
- **Intelligent Title Extraction**
  - Filters time keywords from titles ("morgen", "heute", "übermorgen")
  - Integrates room/location into title ("Meeting Raum 310")
  - Context-based title generation from user input
  
- **Robust Location Detection**
  - Room numbers: "Raum 310", "Zimmer 12"
  - Office locations: "Firma", "Büro", "Office"
  - Prevents confusion with time keywords
  
- **Enhanced Time Parsing**
  - Supports multiple patterns: "um 14 Uhr", "14:30", "14 Uhr"
  - Correct precedence ("übermorgen" before "morgen")
  - Default duration: 1 hour
  
- **Improved Chat Confirmations**
  - Example: "Ich habe dir morgen um 10:00 Uhr einen Termin 'Meeting' in Raum 310 erstellt."
  - Relative time output (heute/morgen/übermorgen)
  - Location integration in confirmation message
  
- **Event Type Classification**
  - `meeting`: Firma, Büro, Raum, Besprechung
  - `private`: Privat, Personal, Familie
  - `other`: Default fallback
  
- **"Besprechung" Intent**
  - Now recognized as `create_event`
  
- **Test Suite**
  - Created `test_event_detection.py` with 10 test cases
  - 8/10 test cases passing

### Changed
- `action_executor.py`: Better formatted confirmation messages
- `intent_detector.py`: Complete refactor of `extract_event_details()`

## [2.0.0] - 2025-12-03

### Added - SSE Streaming & Chat Actions
- SSE Streaming endpoint now executes actions (create_event, create_task, create_note)
- Frontend displays action result badges (✅ success, ❌ error)
- Action confirmation messages in chat
- Privacy settings database persistence
- Accessibility improvements for select elements
- Removed deprecated `X-XSS-Protection` header

### Changed
- `chat_streaming.py`: Added intent detection and action execution
- `Chat.jsx`: Added action_result SSE event handling
- `Chat.css`: Added action result badge styles
- `privacy_router.py`: SQLAlchemy 2.0 text() wrappers

## [1.2.0] - 2025-12-02

### Added
- Intent Detection & Action Execution
- Notes UI with Mood Integration
- Calendar UI with Quick-Add
- Comprehensive API Documentation

### Changed
- GPU Detection with nvidia-smi
- Ollama Management (pull/delete/storage)
- Tasks UI Polish

## [1.0.0] - 2025-12-01

### Initial Release
- Tasks/Calendar/Notes CRUD APIs
- Mood System v1.2.0
- Chat Engine with SSE Streaming
- Frontend with React + Vite
- FastAPI Backend
- PostgreSQL Database
