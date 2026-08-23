-- User Preferences Schema
-- Backs the frontend Preferences page (frontend/src/components/UserPreferences.jsx),
-- which previously called GET/PUT /api/user/preferences with no matching backend
-- endpoint or table at all - settings never actually persisted.
--
-- Also adds the fields for the Claude-style personalization features:
-- custom instructions, a selectable personality preset, and opt-in/opt-out
-- toggles for chat memory creation (Neo4j concept graph + semantic_metadata/
-- temporal_index rows written by app/services/memory_integration.py).

CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Existing (previously unbacked) preferences page fields
    ai_model VARCHAR(100) NOT NULL DEFAULT 'llama3.2:3b',
    language VARCHAR(10) NOT NULL DEFAULT 'de',
    theme VARCHAR(20) NOT NULL DEFAULT 'dark',
    notifications BOOLEAN NOT NULL DEFAULT TRUE,
    sound_effects BOOLEAN NOT NULL DEFAULT FALSE,

    -- Custom instructions: standing per-user instructions spliced into
    -- every chat system prompt (chat.py and chat_streaming.py)
    custom_instructions TEXT,

    -- Personality preset (see app/liara_engine/personality.py), layered on
    -- top of the automatic/reactive MoodSystem, not a replacement for it
    personality VARCHAR(30) NOT NULL DEFAULT 'warmherzig',

    -- Memory creation opt-in/opt-out. memory_enabled gates all chat memory
    -- creation; tool_memory_enabled additionally gates memory creation
    -- specifically for messages where MCP tools or web search were used
    memory_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    tool_memory_enabled BOOLEAN NOT NULL DEFAULT TRUE,

    -- Workspace v1 feature toggle (shared file/code editing + execution tab)
    workspace_enabled BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id);

COMMENT ON TABLE user_preferences IS 'Per-user app preferences: model/theme/language, custom chat instructions, personality preset, memory creation opt-in/out.';
