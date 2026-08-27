"""add web_safety_lists table

Revision ID: 9ff1059e5ba1
Revises: 54807c0debe8
Create Date: 2026-08-27 08:00:00.000000

Reconciliation migration (issue #12 item 1): web_safety_lists existed only
as a standalone SQL file (app/migrations/004_web_safety_lists.sql), applied
by hand to production, with no Alembic revision ever creating it - a fresh
`alembic upgrade head` on an empty database would never have this table.

Reuses that file's own SQL nearly verbatim (already written with
IF NOT EXISTS / CREATE OR REPLACE / ON CONFLICT DO NOTHING throughout), so
this is safe to run both against a fresh database and against the existing
production database where the table already exists from the manual SQL run.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9ff1059e5ba1'
down_revision: Union[str, Sequence[str], None] = '54807c0debe8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS web_safety_lists (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            domain VARCHAR(255) NOT NULL,
            list_type VARCHAR(20) NOT NULL CHECK (list_type IN ('whitelist', 'graylist', 'blacklist')),
            reason TEXT,
            is_pattern BOOLEAN DEFAULT FALSE,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_user_domain_list UNIQUE (user_id, domain, list_type)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_web_safety_lists_user_type ON web_safety_lists(user_id, list_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_web_safety_lists_domain ON web_safety_lists(domain)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_web_safety_lists_global ON web_safety_lists(list_type) WHERE user_id IS NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_web_safety_lists_created_by ON web_safety_lists(created_by)")

    op.execute("""
        CREATE OR REPLACE FUNCTION update_web_safety_lists_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("DROP TRIGGER IF EXISTS web_safety_lists_update_timestamp ON web_safety_lists")
    op.execute("""
        CREATE TRIGGER web_safety_lists_update_timestamp
        BEFORE UPDATE ON web_safety_lists
        FOR EACH ROW
        EXECUTE FUNCTION update_web_safety_lists_timestamp()
    """)

    op.execute("""
        INSERT INTO web_safety_lists (user_id, domain, list_type, reason, created_by) VALUES
        (NULL, 'facebook.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
        (NULL, 'instagram.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
        (NULL, 'twitter.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
        (NULL, 'x.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
        (NULL, 'tiktok.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
        (NULL, 'linkedin.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
        (NULL, 'snapchat.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
        (NULL, 'discord.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
        (NULL, 'pinterest.com', 'blacklist', 'Social Media - Dynamic Content', NULL),
        (NULL, 'amazon.com', 'blacklist', 'Shopping - Tracking & Dynamic Prices', NULL),
        (NULL, 'amazon.de', 'blacklist', 'Shopping - Tracking & Dynamic Prices', NULL),
        (NULL, 'ebay.com', 'blacklist', 'Shopping - Tracking & Dynamic Prices', NULL),
        (NULL, 'ebay.de', 'blacklist', 'Shopping - Tracking & Dynamic Prices', NULL),
        (NULL, 'aliexpress.com', 'blacklist', 'Shopping - Tracking & Dynamic Prices', NULL),
        (NULL, 'bit.ly', 'blacklist', 'URL Shortener - Phishing Risk', NULL),
        (NULL, 'tinyurl.com', 'blacklist', 'URL Shortener - Phishing Risk', NULL),
        (NULL, 'goo.gl', 'blacklist', 'URL Shortener - Phishing Risk', NULL),
        (NULL, 'mega.nz', 'blacklist', 'File Hosting - Privacy Risk', NULL),
        (NULL, 'dropbox.com', 'blacklist', 'Cloud Storage - Privacy Risk', NULL),
        (NULL, 'drive.google.com', 'blacklist', 'Cloud Storage - Privacy Risk', NULL)
        ON CONFLICT (user_id, domain, list_type) DO NOTHING
    """)

    op.execute("COMMENT ON TABLE web_safety_lists IS 'User-specific and global domain lists for web safety filtering'")
    op.execute("COMMENT ON COLUMN web_safety_lists.user_id IS 'NULL = global rule (admin), otherwise user-specific'")
    op.execute("COMMENT ON COLUMN web_safety_lists.is_pattern IS 'TRUE if domain contains wildcards like *.example.com'")
    op.execute("COMMENT ON COLUMN web_safety_lists.reason IS 'Human-readable explanation why this domain was added'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP FUNCTION IF EXISTS update_web_safety_lists_timestamp() CASCADE")
    op.execute("DROP TABLE IF EXISTS web_safety_lists")
