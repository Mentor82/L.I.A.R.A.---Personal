"""add tasks column to chat_messages

Revision ID: c1d2e3f4a5b6
Revises: e8b9c1d2e3f4
Create Date: 2026-09-02 00:15:00.000000

The model-authored plan/checklist (<tasks> block, see task_splitter.py) was
streamed live via SSE but never persisted - only the final prose answer
went into chat_messages.content. A page reload or navigating away and back
silently lost the checklist entirely, including which items the user had
been tracking as done. Adds a nullable `tasks` JSON/Text column, same
pattern as the `thinking`/`tokens` columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'e8b9c1d2e3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chat_messages', sa.Column('tasks', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chat_messages', 'tasks')
