"""Add auth_sessions, retire users.refresh_token (issue #11 items 4/5)

Revision ID: 11bb445a9470
Revises: d6a1fc0793ec
Create Date: 2026-08-26 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11bb445a9470'
down_revision: Union[str, Sequence[str], None] = 'd6a1fc0793ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add auth_sessions table, drop the old single-slot refresh columns."""
    op.create_table(
        'auth_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_auth_sessions_id'), 'auth_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_auth_sessions_user_id'), 'auth_sessions', ['user_id'], unique=False)

    op.drop_column('users', 'refresh_token')
    op.drop_column('users', 'refresh_token_expires')


def downgrade() -> None:
    """Downgrade schema - restore the old columns, drop auth_sessions."""
    op.add_column('users', sa.Column('refresh_token_expires', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('refresh_token', sa.String(length=500), nullable=True))

    op.drop_index(op.f('ix_auth_sessions_user_id'), table_name='auth_sessions')
    op.drop_index(op.f('ix_auth_sessions_id'), table_name='auth_sessions')
    op.drop_table('auth_sessions')
