"""add thinking column to chat_messages

Revision ID: bd77ccac727b
Revises: f1a2b3c4d5e6
Create Date: 2026-08-31 23:30:00.000000

chat_messages/chat_sessions predate this project's Alembic setup entirely -
no earlier revision created or otherwise touches either table, so this is
the first Alembic-tracked change to chat_messages. Adds a nullable
`thinking` column: chat_streaming.py streamed reasoning-model "thinking"
content live via SSE but never persisted it (only the final answer went
into chat_messages.content), so a page reload silently lost the reasoning
trace the user had already seen live. Nullable and additive only - existing
rows/readers unaffected.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd77ccac727b'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chat_messages', sa.Column('thinking', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chat_messages', 'thinking')
