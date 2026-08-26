"""Add auth_sessions table (issue #11 items 4/5)

Revision ID: 11bb445a9470
Revises: d6a1fc0793ec
Create Date: 2026-08-26 22:15:00.000000

Only adds the new table here. Dropping users.refresh_token/
refresh_token_expires is a separate follow-up revision - DROP COLUMN needs
an ACCESS EXCLUSIVE lock on `users`, which is queried on essentially every
authenticated request, so on a live instance that lock can never win
against continuous read traffic (confirmed live: 5 retries at a 3s
lock_timeout each still failed). Creating this table only needs a lock on
`users` compatible with plain reads (SELECT), so it's safe to ship without
a maintenance window. The two old columns are simply unused dead schema
in the meantime - the ORM model and all code already stopped referencing
them in this same change.
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
    """Upgrade schema - add auth_sessions table."""
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


def downgrade() -> None:
    """Downgrade schema - drop auth_sessions."""
    op.drop_index(op.f('ix_auth_sessions_user_id'), table_name='auth_sessions')
    op.drop_index(op.f('ix_auth_sessions_id'), table_name='auth_sessions')
    op.drop_table('auth_sessions')
