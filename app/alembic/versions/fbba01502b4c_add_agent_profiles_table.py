"""add agent_profiles table

Revision ID: fbba01502b4c
Revises: e5f6a7b8c9d0
Create Date: 2026-09-04 12:30:00.000000

Lets an admin override AgentRegistry._PROFILES's display fields
(name/description/default_model/icon/category) for the 4 specialized
agents (code/research/productivity/vision) without a code change +
redeploy. A missing row for a given agent_id means "use the hardcoded
default in agent_registry.py" - this migration deliberately seeds no
rows, so it stays pure schema and never goes stale against whatever the
current code defaults happen to be. `id`, `tools`, and the actual Python
agent class are NOT represented here - see agent_registry.py's own
comments for why those have to stay code, not data.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fbba01502b4c'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_profiles (
            agent_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            default_model VARCHAR(100) NOT NULL,
            icon VARCHAR(10) NOT NULL,
            category VARCHAR(50) NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    op.execute(
        "COMMENT ON TABLE agent_profiles IS "
        "'Admin overrides for AgentRegistry._PROFILES display fields "
        "(name/description/default_model/icon/category). A missing row "
        "means: use the hardcoded default for that agent_id.'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS agent_profiles")
