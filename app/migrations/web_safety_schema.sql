-- 💾 Web Access Logging Schema
-- Audit Trail für alle Internet-Zugriffe

-- ============================================================================
-- web_access_logs: Haupttabelle für alle Web-Anfragen
-- ============================================================================

CREATE TABLE IF NOT EXISTS web_access_logs (
    id SERIAL PRIMARY KEY,
    
    -- User Info
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Request Details
    query TEXT NOT NULL,                    -- Original User Query
    rewritten_query TEXT,                   -- Entschärfte Query (nach Intent Check)
    final_url TEXT,                         -- Finale URL (nach Redirects)
    request_type VARCHAR(50),               -- 'search', 'fetch', 'weather', etc.
    
    -- Risk Assessment
    intent_risk_score INTEGER DEFAULT 0,    -- Layer 1: Intent Check (0-100)
    domain_risk_score INTEGER DEFAULT 0,    -- Layer 2: Domain Risk (0-100)
    content_risk_score INTEGER DEFAULT 0,   -- Layer 4: Content Risk (0-100)
    response_risk_score INTEGER DEFAULT 0,  -- Layer 5: Response Risk (0-100)
    final_risk_score INTEGER DEFAULT 0,     -- Combined Risk Score
    risk_level VARCHAR(20),                 -- 'safe', 'gray', 'unsafe', 'critical', 'blocked'
    
    -- Execution Status
    blocked BOOLEAN DEFAULT false,
    blocked_reason TEXT,                    -- Grund für Blockierung
    blocked_layer VARCHAR(20),              -- Welcher Layer hat blockiert
    
    -- Response Details
    status_code INTEGER,                    -- HTTP Status
    content_type VARCHAR(100),
    content_length INTEGER,                 -- Bytes
    response_time_ms INTEGER,               -- Millisekunden
    
    -- Content Analysis
    toxic_content_found BOOLEAN DEFAULT false,
    pii_removed INTEGER DEFAULT 0,          -- Anzahl entfernter PII
    affiliate_links_removed INTEGER DEFAULT 0,
    
    -- Metadata
    ip_address INET,                        -- User IP (für Abuse Detection)
    user_agent TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes für web_access_logs
CREATE INDEX idx_web_logs_user ON web_access_logs(user_id, created_at DESC);
CREATE INDEX idx_web_logs_blocked ON web_access_logs(blocked, created_at DESC);
CREATE INDEX idx_web_logs_risk ON web_access_logs(final_risk_score DESC);
CREATE INDEX idx_web_logs_url ON web_access_logs(final_url);
CREATE INDEX idx_web_logs_created ON web_access_logs(created_at DESC);

COMMENT ON TABLE web_access_logs IS 'Audit Trail für alle Web-Zugriffe (4-Layer Security)';
COMMENT ON COLUMN web_access_logs.intent_risk_score IS 'Layer 1: Query Safety Check';
COMMENT ON COLUMN web_access_logs.domain_risk_score IS 'Layer 2: Domain Reputation';
COMMENT ON COLUMN web_access_logs.content_risk_score IS 'Layer 4: Content Filter';
COMMENT ON COLUMN web_access_logs.response_risk_score IS 'Layer 5: Response Safety';


-- ============================================================================
-- web_blocked_keywords: Getrackte blockierte Keywords
-- ============================================================================

CREATE TABLE IF NOT EXISTS web_blocked_keywords (
    id SERIAL PRIMARY KEY,
    
    log_id INTEGER REFERENCES web_access_logs(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    category VARCHAR(50),                   -- 'hacking', 'violence', 'drugs', etc.
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_blocked_keywords_log ON web_blocked_keywords(log_id);
CREATE INDEX idx_blocked_keywords_keyword ON web_blocked_keywords(keyword);
CREATE INDEX idx_blocked_keywords_category ON web_blocked_keywords(category);

COMMENT ON TABLE web_blocked_keywords IS 'Tracking blockierter Keywords (Security Analytics)';


-- ============================================================================
-- web_rate_limits: Rate-Limit Violations
-- ============================================================================

CREATE TABLE IF NOT EXISTS web_rate_limit_violations (
    id SERIAL PRIMARY KEY,
    
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    violation_count INTEGER DEFAULT 1,
    requests_in_window INTEGER,
    max_allowed INTEGER,
    window_minutes INTEGER DEFAULT 1,
    
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rate_violations_user ON web_rate_limit_violations(user_id, created_at DESC);
CREATE INDEX idx_rate_violations_ip ON web_rate_limit_violations(ip_address, created_at DESC);

COMMENT ON TABLE web_rate_limit_violations IS 'Tracking Rate-Limit Überschreitungen (Abuse Detection)';


-- ============================================================================
-- web_domain_reputation: Domain Reputation Cache
-- ============================================================================

CREATE TABLE IF NOT EXISTS web_domain_reputation (
    id SERIAL PRIMARY KEY,
    
    domain VARCHAR(255) UNIQUE NOT NULL,
    
    -- Reputation
    reputation_score INTEGER DEFAULT 50,    -- 0-100 (0=blocked, 100=safe)
    category VARCHAR(50),                   -- 'whitelist', 'graylist', 'blacklist', 'unknown'
    
    -- Statistics
    access_count INTEGER DEFAULT 0,
    blocked_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP,
    
    -- SSL Info
    has_valid_ssl BOOLEAN DEFAULT false,
    ssl_checked_at TIMESTAMP,
    
    -- Manual Overrides
    manually_whitelisted BOOLEAN DEFAULT false,
    manually_blacklisted BOOLEAN DEFAULT false,
    admin_notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_domain_rep_domain ON web_domain_reputation(domain);
CREATE INDEX idx_domain_rep_category ON web_domain_reputation(category);
CREATE INDEX idx_domain_rep_score ON web_domain_reputation(reputation_score);

COMMENT ON TABLE web_domain_reputation IS 'Cache für Domain-Reputation (Performance + Analytics)';


-- ============================================================================
-- Views für Analytics
-- ============================================================================

-- Top blocked queries
CREATE OR REPLACE VIEW v_web_top_blocked AS
SELECT 
    query,
    COUNT(*) as block_count,
    blocked_reason,
    blocked_layer,
    AVG(final_risk_score) as avg_risk_score
FROM web_access_logs
WHERE blocked = true
GROUP BY query, blocked_reason, blocked_layer
ORDER BY block_count DESC
LIMIT 100;

-- User web activity summary
CREATE OR REPLACE VIEW v_web_user_activity AS
SELECT 
    u.id,
    u.username,
    COUNT(*) as total_requests,
    COUNT(*) FILTER (WHERE wal.blocked = true) as blocked_requests,
    COUNT(*) FILTER (WHERE wal.blocked = false) as successful_requests,
    AVG(wal.final_risk_score) as avg_risk_score,
    MAX(wal.created_at) as last_request_at
FROM users u
LEFT JOIN web_access_logs wal ON u.id = wal.user_id
GROUP BY u.id, u.username;

-- Daily statistics
CREATE OR REPLACE VIEW v_web_daily_stats AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_requests,
    COUNT(*) FILTER (WHERE blocked = true) as blocked_requests,
    COUNT(*) FILTER (WHERE toxic_content_found = true) as toxic_content_found,
    AVG(final_risk_score) as avg_risk_score,
    AVG(response_time_ms) as avg_response_time_ms
FROM web_access_logs
GROUP BY DATE(created_at)
ORDER BY date DESC;


-- ============================================================================
-- Trigger für updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_web_domain_reputation_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_web_domain_reputation_updated_at
BEFORE UPDATE ON web_domain_reputation
FOR EACH ROW
EXECUTE FUNCTION update_web_domain_reputation_updated_at();


-- ============================================================================
-- Grants
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO liara;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO liara;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO liara;
