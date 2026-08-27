"""merge heads

Revision ID: f1a2b3c4d5e6
Revises: 54807c0debe8, e24ab6a63a0a
Create Date: 2026-08-27 09:00:00.000000

Reunites the two branches that existed after 9ff1059e5ba1/e24ab6a63a0a
(issue #12) were deliberately chained off 11bb445a9470 instead of
54807c0debe8 (issue #11's DROP COLUMN, postponed at the time for a quiet
traffic window). Both are now applied in production, so this is a pure
merge point - no schema change of its own.
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = ('54807c0debe8', 'e24ab6a63a0a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
