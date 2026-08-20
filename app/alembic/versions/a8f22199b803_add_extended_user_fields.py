"""Add extended user fields (phone, dob, 2fa, privacy)

Revision ID: a8f22199b803
Revises: 7f58a46f0184
Create Date: 2025-12-03 12:43:06.970665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8f22199b803'
down_revision: Union[str, Sequence[str], None] = '7f58a46f0184'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add extended user fields."""
    
    # Add new columns to users table
    op.add_column('users', sa.Column('phone', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('date_of_birth', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('profile_picture', sa.String(length=500), nullable=True))
    
    # Email verification
    op.add_column('users', sa.Column('email_verification_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('email_verification_expires', sa.DateTime(), nullable=True))
    
    # Password reset
    op.add_column('users', sa.Column('password_reset_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(), nullable=True))
    
    # 2FA
    op.add_column('users', sa.Column('totp_secret', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), nullable=True, server_default='false'))
    
    # Privacy & DSGVO
    op.add_column('users', sa.Column('privacy_accepted', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('users', sa.Column('privacy_accepted_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('newsletter_opt_in', sa.Boolean(), nullable=True, server_default='false'))
    
    # Make full_name NOT NULL (with default for existing rows)
    op.execute("UPDATE users SET full_name = username WHERE full_name IS NULL OR full_name = ''")
    op.alter_column('users', 'full_name', nullable=False)


def downgrade() -> None:
    """Downgrade schema - Remove extended user fields."""
    
    # Remove columns
    op.drop_column('users', 'newsletter_opt_in')
    op.drop_column('users', 'privacy_accepted_at')
    op.drop_column('users', 'privacy_accepted')
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret')
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'email_verification_expires')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'profile_picture')
    op.drop_column('users', 'date_of_birth')
    op.drop_column('users', 'phone')
    
    # Make full_name nullable again
    op.alter_column('users', 'full_name', nullable=True)
