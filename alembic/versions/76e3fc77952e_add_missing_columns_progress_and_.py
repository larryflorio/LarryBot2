"""add missing columns progress and completed_at

Revision ID: 76e3fc77952e
Revises: ad6cdf3a2f7d
Create Date: 2025-07-01 18:15:08.345426

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76e3fc77952e'
down_revision: Union[str, Sequence[str], None] = 'ad6cdf3a2f7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add missing columns only - avoid SQLite ALTER COLUMN limitations
    op.add_column('tasks', sa.Column('progress', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tasks', sa.Column('completed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema.""" 
    # Remove added columns
    op.drop_column('tasks', 'completed_at')
    op.drop_column('tasks', 'progress')
