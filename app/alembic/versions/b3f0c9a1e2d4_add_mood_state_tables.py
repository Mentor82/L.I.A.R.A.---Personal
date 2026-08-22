"""add_mood_state_tables

Revision ID: b3f0c9a1e2d4
Revises: a65de26a4079
Create Date: 2026-08-22 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f0c9a1e2d4'
down_revision: Union[str, Sequence[str], None] = 'a65de26a4079'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'user_mood_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('current_mood', sa.String(length=20), nullable=False, server_default='neutral'),
        sa.Column('mood_intensity', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.8'),
        sa.Column('last_interaction_type', sa.String(length=30), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_user_mood_state_user_id', 'user_mood_state', ['user_id'])

    op.create_table(
        'mood_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('mood', sa.String(length=20), nullable=False),
        sa.Column('intensity', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('interaction_type', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mood_history_user_id', 'mood_history', ['user_id'])
    op.create_index('ix_mood_history_created_at', 'mood_history', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_mood_history_created_at', table_name='mood_history')
    op.drop_index('ix_mood_history_user_id', table_name='mood_history')
    op.drop_table('mood_history')

    op.drop_index('ix_user_mood_state_user_id', table_name='user_mood_state')
    op.drop_table('user_mood_state')
