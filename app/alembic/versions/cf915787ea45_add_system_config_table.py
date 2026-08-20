"""add_system_config_table

Revision ID: cf915787ea45
Revises: 646650e0d366
Create Date: 2025-12-05 06:35:47.389859

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf915787ea45'
down_revision: Union[str, Sequence[str], None] = '646650e0d366'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'system_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('default_model', sa.String(length=100), nullable=False, server_default='llama3.2:3b'),
        sa.Column('max_tokens', sa.Integer(), nullable=False, server_default='2000'),
        sa.Column('temperature', sa.Integer(), nullable=False, server_default='70'),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('guest_message_limit', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('guest_message_length', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('user_message_limit', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('rate_limit_window', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('web_search_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('location_services_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('guest_mode_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('registration_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('data_retention_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('search_history_retention_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('location_retention_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('auto_delete_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('ollama_host', sa.String(length=255), nullable=False, server_default='http://localhost:11434'),
        sa.Column('ollama_timeout', sa.Integer(), nullable=False, server_default='120'),
        sa.Column('ollama_pull_on_start', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_config_id'), 'system_config', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_system_config_id'), table_name='system_config')
    op.drop_table('system_config')
