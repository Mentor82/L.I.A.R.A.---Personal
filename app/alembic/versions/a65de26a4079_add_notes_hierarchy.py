"""add_notes_hierarchy

Revision ID: a65de26a4079
Revises: cf915787ea45
Create Date: 2025-12-05 14:32:04.360284

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a65de26a4079'
down_revision: Union[str, Sequence[str], None] = 'cf915787ea45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add parent_id for hierarchical structure
    op.add_column('notes', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.create_index('ix_notes_parent_id', 'notes', ['parent_id'])
    op.create_foreign_key('fk_notes_parent_id', 'notes', 'notes', ['parent_id'], ['id'])
    
    # Add is_expanded for UI state
    op.add_column('notes', sa.Column('is_expanded', sa.Boolean(), server_default='true', nullable=False))
    
    # Add order_index for sorting within same level
    op.add_column('notes', sa.Column('order_index', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_notes_parent_id', 'notes', type_='foreignkey')
    op.drop_index('ix_notes_parent_id', 'notes')
    op.drop_column('notes', 'parent_id')
    op.drop_column('notes', 'is_expanded')
    op.drop_column('notes', 'order_index')
