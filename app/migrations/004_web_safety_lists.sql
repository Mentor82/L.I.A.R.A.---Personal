-- Migration: Web Safety Custom Lists
-- Date: 2025-12-05
-- Description: User-specific and global whitelist/graylist/blacklist management

-- ============================================================================
-- Web Safety Custom Lists Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS web_safety_lists (
    id SERIAL PRIMARY KEY,
    
    -- Ownership: NULL = global (admin), otherwise user-specific
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Domain/Pattern
    domain VARCHAR(255) NOT NULL,
    
    -- List Type
    list_type VARCHAR(20) NOT NULL CHECK (list_type IN ('whitelist', 'graylist', 'blacklist')),
    
    -- Metadata
    reason TEXT,  -- Why was this domain added?
    is_pattern BOOLEAN DEFAULT FALSE,  -- TRUE if domain contains wildcards (*.example.com)
    
    -- Audit Trail
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Prevent duplicates: Same domain can't be in same list twice for same user
    CONSTRAINT unique_user_domain_list UNIQUE (user_id, domain, list_type)
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Fast lookup by user + list type (most common query)
CREATE INDEX idx_web_safety_lists_user_type ON web_safety_lists(user_id, list_type);

-- Fast domain lookup (exact match)
CREATE INDEX idx_web_safety_lists_domain ON web_safety_lists(domain);

-- Global rules (user_id IS NULL)
CREATE INDEX idx_web_safety_lists_global ON web_safety_lists(list_type) WHERE user_id IS NULL;

-- Audit queries
CREATE INDEX idx_web_safety_lists_created_by ON web_safety_lists(created_by);

-- ============================================================================
-- Trigger for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_web_safety_lists_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER web_safety_lists_update_timestamp
BEFORE UPDATE ON web_safety_lists
FOR EACH ROW
EXECUTE FUNCTION update_web_safety_lists_timestamp();

-- ============================================================================
-- Seed Data: Import Hardcoded Blacklist (Social Media, Shopping)
-- ============================================================================

INSERT INTO web_safety_lists (user_id, domain, list_type, reason, created_by) VALUES
-- Social Media (Global Blacklist)
(NULL, 'facebook.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
(NULL, 'instagram.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
(NULL, 'twitter.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
(NULL, 'x.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
(NULL, 'tiktok.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
(NULL, 'linkedin.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
(NULL, 'snapchat.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
(NULL, 'discord.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
(NULL, 'pinterest.com', 'blacklist', 'Social Media - Dynamic Content', NULL),

-- Shopping (Global Blacklist)
(NULL, 'amazon.com', 'blacklist', 'Shopping - Tracking & Dynamic Prices', NULL),
(NULL, 'amazon.de', 'blacklist', 'Shopping - Tracking & Dynamic Prices', NULL),
(NULL, 'ebay.com', 'blacklist', 'Shopping - Tracking & Dynamic Prices', NULL),
(NULL, 'ebay.de', 'blacklist', 'Shopping - Tracking & Dynamic Prices', NULL),
(NULL, 'aliexpress.com', 'blacklist', 'Shopping - Tracking & Dynamic Prices', NULL),

-- URL Shorteners (Phishing Risk)
(NULL, 'bit.ly', 'blacklist', 'URL Shortener - Phishing Risk', NULL),
(NULL, 'tinyurl.com', 'blacklist', 'URL Shortener - Phishing Risk', NULL),
(NULL, 'goo.gl', 'blacklist', 'URL Shortener - Phishing Risk', NULL),

-- File Hosting (Privacy Risk)
(NULL, 'mega.nz', 'blacklist', 'File Hosting - Privacy Risk', NULL),
(NULL, 'dropbox.com', 'blacklist', 'Cloud Storage - Privacy Risk', NULL),
(NULL, 'drive.google.com', 'blacklist', 'Cloud Storage - Privacy Risk', NULL)

ON CONFLICT (user_id, domain, list_type) DO NOTHING;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE web_safety_lists IS 'User-specific and global domain lists for web safety filtering';
COMMENT ON COLUMN web_safety_lists.user_id IS 'NULL = global rule (admin), otherwise user-specific';
COMMENT ON COLUMN web_safety_lists.is_pattern IS 'TRUE if domain contains wildcards like *.example.com';
COMMENT ON COLUMN web_safety_lists.reason IS 'Human-readable explanation why this domain was added';
