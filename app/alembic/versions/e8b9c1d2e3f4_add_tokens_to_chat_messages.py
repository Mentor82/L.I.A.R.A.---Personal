"""add tokens column to chat_messages

Revision ID: e8b9c1d2e3f4
Revises: bd77ccac727b
Create Date: 2026-09-01 18:20:00.000000

Adds a nullable `tokens` JSON/Text column to chat_messages so that token usage
statistics (in, think, out, gesamt) are persistently stored and preserved across
page refreshes and session loads.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8b9c1d2e3f4'
down_revision: Union[str, Sequence[str], None] = 'bd77ccac727b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chat_messages', sa.Column('tokens', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chat_messages', 'tokens')
