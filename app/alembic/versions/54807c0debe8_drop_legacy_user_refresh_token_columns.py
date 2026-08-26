"""Drop legacy users.refresh_token/refresh_token_expires (issue #11 items 4/5 follow-up)

Revision ID: 54807c0debe8
Revises: 11bb445a9470
Create Date: 2026-08-26 22:45:00.000000

DEFERRED - do not run this against the live production instance without a
maintenance window or a confirmed quiet traffic period first.

DROP COLUMN needs an ACCESS EXCLUSIVE lock on `users`, which is queried on
essentially every authenticated request. On the live instance this lock
lost to continuous read traffic even after 5 retries at a 3s lock_timeout
each (see 11bb445a9470's docstring) - it needs either a brief real gap in
traffic, or the app briefly stopped, to have a realistic chance of
acquiring the lock at all. Both columns have been unused dead schema since
11bb445a9470 shipped (replaced by the auth_sessions table), so there is no
functional urgency here, only schema cleanup.

Suggested procedure when actually running this:
    PGOPTIONS='-c lock_timeout=3000' alembic upgrade head
retrying a few times during a genuinely quiet window (or with the backend
briefly stopped) rather than blocking indefinitely.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54807c0debe8'
down_revision: Union[str, Sequence[str], None] = '11bb445a9470'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - drop the legacy single-slot refresh columns."""
    op.drop_column('users', 'refresh_token')
    op.drop_column('users', 'refresh_token_expires')


def downgrade() -> None:
    """Downgrade schema - restore the legacy columns."""
    op.add_column('users', sa.Column('refresh_token_expires', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('refresh_token', sa.String(length=500), nullable=True))
