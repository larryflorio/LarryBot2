"""remove_user_id_fields_for_single_user

Revision ID: e43a3179f642
Revises: 584f3979e198
Create Date: 2025-06-27 16:31:15.232695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e43a3179f642'
down_revision: Union[str, Sequence[str], None] = '584f3979e198'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for single-user optimization."""
    # Remove user_id from task_comments (single-user system)
    op.drop_column('task_comments', 'user_id')
    
    # Note: Metrics tables (command_metrics, user_activity_metrics) will be created
    # without user_id fields when they are first used, as they don't exist yet
    # in the current schema. The models have been updated to not include user_id.


def downgrade() -> None:
    """Downgrade schema (restore multi-user fields)."""
    # Restore user_id to task_comments
    op.add_column('task_comments', sa.Column('user_id', sa.INTEGER(), nullable=False))
    
    # Note: Metrics tables would need user_id fields restored if they exist
