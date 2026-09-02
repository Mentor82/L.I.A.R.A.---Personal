"""add structured_state column to chat_sessions

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-09-02 12:00:00.000000

The 4-layer context architecture (context_budget_manager.py) was designed
for "inkrementell verdichtete" session state (StructuredSessionState:
decisions/constraints/open tasks/technical state), but process_turn_context()
was never actually called with a session_state - it always started from a
fresh, empty state and threw the result away after each turn. Adds a
nullable `structured_state` JSON/Text column, same pattern as the
`tasks`/`tokens`/`thinking` columns on chat_messages, so compaction can
actually persist and build up across turns instead of recomputing from
scratch every time.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chat_sessions', sa.Column('structured_state', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chat_sessions', 'structured_state')
