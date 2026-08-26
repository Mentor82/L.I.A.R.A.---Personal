"""Add token_version to users (issue #11 items 2/3)

Revision ID: d6a1fc0793ec
Revises: b3f0c9a1e2d4
Create Date: 2026-08-26 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6a1fc0793ec'
down_revision: Union[str, Sequence[str], None] = 'b3f0c9a1e2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add users.token_version."""
    op.add_column(
        'users',
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    """Downgrade schema - Remove users.token_version."""
    op.drop_column('users', 'token_version')
