-- Location Preferences Schema
-- Privacy-conscious storage with explicit consent tracking

CREATE TABLE IF NOT EXISTS user_location_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Location data (derived from IP, NOT storing IP itself)
    country VARCHAR(100),
    country_code VARCHAR(3),
    region VARCHAR(100),
    city VARCHAR(100),
    timezone VARCHAR(50),
    latitude FLOAT,
    longitude FLOAT,
    
    -- Privacy & Consent
    consent_given BOOLEAN NOT NULL DEFAULT FALSE,
    consent_timestamp TIMESTAMP,
    
    -- Metadata
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- One location per user
    UNIQUE(user_id)
);

CREATE INDEX idx_user_location_user ON user_location_preferences(user_id);
CREATE INDEX idx_user_location_consent ON user_location_preferences(user_id, consent_given);

COMMENT ON TABLE user_location_preferences IS 'Privacy-conscious user location storage with explicit consent. IP addresses are NEVER stored.';
COMMENT ON COLUMN user_location_preferences.consent_given IS 'Explicit user consent required for location storage and usage';


-- Web Search History (optional, with privacy controls)
CREATE TABLE IF NOT EXISTS user_search_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Search data
    query TEXT NOT NULL,
    search_type VARCHAR(50), -- 'web', 'wikipedia', 'weather'
    result_summary TEXT,
    
    -- Privacy controls
    stored_with_consent BOOLEAN NOT NULL DEFAULT FALSE,
    can_be_used_for_training BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Metadata
    searched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_search_history_user ON user_search_history(user_id, searched_at DESC);
CREATE INDEX idx_search_history_consent ON user_search_history(user_id, stored_with_consent);

COMMENT ON TABLE user_search_history IS 'Optional search history with granular privacy controls. Users can disable or delete.';


-- Privacy Settings Table
CREATE TABLE IF NOT EXISTS user_privacy_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Location Privacy
    allow_location_detection BOOLEAN NOT NULL DEFAULT FALSE,
    allow_location_storage BOOLEAN NOT NULL DEFAULT FALSE,
    share_location_with_llm BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Search Privacy
    allow_web_search BOOLEAN NOT NULL DEFAULT TRUE,
    store_search_history BOOLEAN NOT NULL DEFAULT FALSE,
    allow_search_for_training BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Data Retention
    auto_delete_location_after_days INTEGER DEFAULT 30,
    auto_delete_searches_after_days INTEGER DEFAULT 7,
    
    -- Metadata
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id)
);

CREATE INDEX idx_privacy_settings_user ON user_privacy_settings(user_id);

COMMENT ON TABLE user_privacy_settings IS 'Granular privacy controls for location and web search features';

-- Default privacy settings for all users (privacy-first)
INSERT INTO user_privacy_settings (user_id, allow_location_detection, allow_web_search)
SELECT id, false, true FROM users
ON CONFLICT (user_id) DO NOTHING;
