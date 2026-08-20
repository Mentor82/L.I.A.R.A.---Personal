# Changelog

All notable changes to Liara will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.7.2] - 2025-12-06

### Added - Mobile-First Optimization
- **Touch-Optimized Design**: 44px+ touch targets (iOS/Android guidelines)
- **Mobile CSS Variables**: `--tap-target-min`, `--mobile-padding`, `--mobile-spacing`
- **Mobile Utilities**: `.tap-target`, `.mobile-stack`, `.mobile-grid`, `.desktop-only`
- **Responsive Breakpoints**: 480px, 768px, 1024px, 1440px
- **Sticky Chat Input**: Bottom-fixed input bar on mobile
- **Overlay Sidebar**: Mobile-friendly slide-out navigation

### Changed
- **Dashboard**: Single-column layout on <768px
- **Chat**: 85vw sidebar width on mobile, 44px+ input height
- **Tasks**: Full-width buttons, stack layout on mobile
- **Calendar**: Compact grid (60-70px day height on mobile)
- **Notes**: Touch-friendly actions (36px+ buttons)

### Fixed
- Chat message bubbles responsive sizing
- Form inputs now 16px font (prevents auto-zoom)
- Button min-height compliance across all components

---

## [2.7.0] - 2025-12-03

### Added
- **Multi-Threading Support**: Improved concurrent request handling
- **Auto Model Selection**: Intelligent model selection based on query type
- **Enhanced Admin Panel**: System health monitoring improvements

### Changed
- Optimized database queries for better performance
- Updated deployment scripts with cache clearing

### Fixed
- Memory leaks in long-running sessions
- Race conditions in 4D memory sync

---

## [2.6.1] - 2025-12-03

### Fixed
- **User Isolation Bug**: Fixed data leakage between users
- **Neo4j Relationships**: Corrected user_id in graph queries
- **Task/Event/Note Privacy**: Enforced user-specific filtering

### Security
- Added comprehensive user isolation audit
- Enhanced permission checks in all CRUD operations

---

## [2.6.0] - 2025-12-03

### Added - 4D Memory Integration
- **Semantic Memory**: 384-dim embeddings with pgvector
- **Graph Relations**: Neo4j integration for relationship tracking
- **Temporal Index**: Time-series data storage
- **Session Context**: Redis 20-message window
- **Auto-Extraction**: Topics, intent, emotion, importance

### Changed
- Refactored chat to use 4D memory for context
- Improved semantic search accuracy

---

## [2.5.0] - 2025-11-28

### Added
- **Guest Mode**: Chat without registration
- **Streaming SSE**: Real-time responses via Server-Sent Events
- **Rate Limiting**: Guest mode limits (20 messages, 500 chars)
- **Model Selection**: UI for switching between Ollama models

### Changed
- Chat interface redesign with message bubbles
- Improved streaming performance

---

## [2.4.0] - 2025-11-20

### Added
- **Terminal PTY**: Full bash terminal with xterm.js
- **Service Management**: Start/Stop/Restart system services
- **Log Reader**: Real-time log viewing with filtering
- **System Config UI**: Environment variable editor

### Security
- Added security warnings for terminal access
- Implemented command logging

---

## [2.3.0] - 2025-11-15

### Added
- **Tasks System**: Things/Todoist-style task management
- **Calendar**: Month/Week/Day views
- **Notes**: Tree-structured knowledge base
- **Intent Detection**: Automatic task/event/note creation from chat

### Changed
- Improved NLP accuracy for intent detection
- Enhanced UI for productivity features

---

## [2.2.0] - 2025-11-10

### Added
- **Web Search**: DuckDuckGo, Wikipedia, Weather, News
- **Location Services**: IP-based geolocation (opt-in)
- **Privacy Controls**: Auto-delete, retention settings
- **Web Safety**: Content filtering, risk scoring

### Security
- Added GDPR-compliant legal pages
- Implemented cookie consent

---

## [2.1.0] - 2025-11-05

### Added
- **User Management**: CRUD operations for admin
- **Role System**: Admin/User/Guest roles
- **Activity Tracking**: Dashboard with recent activities
- **Mood Dashboard**: 7-dimensional emotion tracking

### Changed
- Admin panel UI improvements
- Better permission handling

---

## [2.0.0] - 2025-11-01

### Added - Major Redesign
- **Halo/UNSC Theme**: Complete design overhaul
- **Glassmorphism**: Transparency, blur effects, glows
- **Dark/Light Mode**: System preference detection
- **Responsive Design**: Mobile-first approach
- **Design System**: 40+ CSS variables

### Changed
- Complete frontend rewrite with modern React patterns
- Improved accessibility (WCAG 2.1 AA)

---

## [1.5.0] - 2025-10-20

### Added
- **Admin Dashboard**: System health monitoring
- **User Statistics**: Usage analytics
- **Quick Actions**: System management shortcuts

---

## [1.4.0] - 2025-10-15

### Added
- **Ollama Integration**: Multi-model AI support
- **Chat History**: Persistent conversation storage
- **Context Window**: 20-message sliding window

---

## [1.3.0] - 2025-10-10

### Added
- **PostgreSQL**: Main database migration from SQLite
- **Redis**: Caching layer
- **Neo4j**: Graph database for relationships

### Changed
- Improved database performance
- Better data modeling

---

## [1.2.0] - 2025-10-05

### Added
- **Authentication**: JWT-based auth system
- **User Profiles**: Profile editing, avatars
- **Settings Page**: User preferences

---

## [1.1.0] - 2025-10-01

### Added
- **Chat UI**: Basic chat interface
- **Message Streaming**: Real-time response display

---

## [1.0.0] - 2025-09-25

### Added - Initial Release
- **FastAPI Backend**: Basic API structure
- **React Frontend**: Initial UI
- **SQLite Database**: Basic data storage
- **Basic AI Chat**: Simple chat functionality

---

## Legend

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security patches

---

**Note**: For migration guides between major versions, see the [Migration Guide](./docs/MIGRATION.md).
