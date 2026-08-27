"""add user_preferences table

Revision ID: e24ab6a63a0a
Revises: 9ff1059e5ba1
Create Date: 2026-08-27 08:05:00.000000

Reconciliation migration (issue #12 item 1) - same reasoning as
9ff1059e5ba1: user_preferences existed only as a standalone SQL file
(app/migrations/user_preferences_schema.sql), applied by hand to
production, with no Alembic revision ever creating it.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e24ab6a63a0a'
down_revision: Union[str, Sequence[str], None] = '9ff1059e5ba1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            ai_model VARCHAR(100) NOT NULL DEFAULT 'llama3.2:3b',
            language VARCHAR(10) NOT NULL DEFAULT 'de',
            theme VARCHAR(20) NOT NULL DEFAULT 'dark',
            notifications BOOLEAN NOT NULL DEFAULT TRUE,
            sound_effects BOOLEAN NOT NULL DEFAULT FALSE,
            custom_instructions TEXT,
            personality VARCHAR(30) NOT NULL DEFAULT 'warmherzig',
            memory_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            tool_memory_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            workspace_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            workspace_agent_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            workspace_font_size INTEGER NOT NULL DEFAULT 14,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id)
        )
    """)

    # Retrofits the column onto an already-existing production table - the
    # CREATE TABLE above is a no-op there (IF NOT EXISTS), so a field added
    # after the table's first deploy still needs its own idempotent
    # ADD COLUMN, matching the original SQL file's own approach.
    op.execute("ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS workspace_font_size INTEGER NOT NULL DEFAULT 14")

    op.execute("CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id)")

    op.execute(
        "COMMENT ON TABLE user_preferences IS "
        "'Per-user app preferences: model/theme/language, custom chat instructions, "
        "personality preset, memory creation opt-in/out.'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS user_preferences")
