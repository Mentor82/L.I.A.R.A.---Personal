"""add session_id to notes

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-02 14:00:00.000000

Notes already had search, tags, and created_at/updated_at - the one thing
missing was any link back to the chat conversation that created a note (the
AI's create_note tool has always been reachable from any chat, but never
recorded which one). Adds a nullable FK to chat_sessions.id so a note can
optionally point back to its origin chat - ON DELETE SET NULL rather than
cascading, since deleting the chat that spawned a note shouldn't delete the
note itself, just orphan the reference. Manually-created notes (no chat
context) simply keep it NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('notes', sa.Column('session_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_notes_session_id_chat_sessions',
        'notes', 'chat_sessions',
        ['session_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_notes_session_id_chat_sessions', 'notes', type_='foreignkey')
    op.drop_column('notes', 'session_id')
