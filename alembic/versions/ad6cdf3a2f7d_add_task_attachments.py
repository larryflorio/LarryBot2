"""add_task_attachments

Revision ID: ad6cdf3a2f7d
Revises: e43a3179f642
Create Date: 2025-06-28 18:32:00.337061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad6cdf3a2f7d'
down_revision: Union[str, Sequence[str], None] = 'e43a3179f642'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create task_attachments table."""
    op.create_table('task_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_url', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('ix_task_attachments_task_id', 'task_attachments', ['task_id'])
    op.create_index('ix_task_attachments_filename', 'task_attachments', ['filename'])


def downgrade() -> None:
    """Drop task_attachments table."""
    op.drop_index('ix_task_attachments_filename', 'task_attachments')
    op.drop_index('ix_task_attachments_task_id', 'task_attachments')
    op.drop_table('task_attachments')
