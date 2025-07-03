"""add_timezone_aware_timestamps

Revision ID: a7d2eaa88f6e
Revises: 76e3fc77952e
Create Date: 2025-07-03 08:07:07.378723

"""
from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d2eaa88f6e'
down_revision: Union[str, Sequence[str], None] = '76e3fc77952e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to support timezone-aware timestamps."""
    
    # Create timezone configuration table
    op.create_table(
        'timezone_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timezone_name', sa.String(100), nullable=False),
        sa.Column('is_auto_detected', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add timezone configuration record
    op.execute("""
        INSERT INTO timezone_config (timezone_name, is_auto_detected, created_at, updated_at)
        VALUES ('UTC', true, :now, :now)
    """, {'now': datetime.now(timezone.utc)})
    
    # Update existing datetime columns to be timezone-aware
    # Note: SQLite doesn't have native timezone support, so we'll store as UTC
    # and handle timezone conversion in the application layer
    
    # Update tasks table timestamps
    op.execute("""
        UPDATE tasks 
        SET created_at = datetime(created_at, 'utc'),
            updated_at = datetime(updated_at, 'utc'),
            started_at = CASE 
                WHEN started_at IS NOT NULL THEN datetime(started_at, 'utc')
                ELSE NULL 
            END,
            completed_at = CASE 
                WHEN completed_at IS NOT NULL THEN datetime(completed_at, 'utc')
                ELSE NULL 
            END,
            due_date = CASE 
                WHEN due_date IS NOT NULL THEN datetime(due_date, 'utc')
                ELSE NULL 
            END
    """)
    
    # Update reminders table timestamps
    op.execute("""
        UPDATE reminders 
        SET created_at = datetime(created_at, 'utc'),
            updated_at = datetime(updated_at, 'utc'),
            remind_at = datetime(remind_at, 'utc')
    """)
    
    # Update time entries table timestamps
    op.execute("""
        UPDATE task_time_entries 
        SET created_at = datetime(created_at, 'utc'),
            started_at = datetime(started_at, 'utc'),
            ended_at = datetime(ended_at, 'utc')
    """)
    
    # Update other tables with timestamps
    op.execute("""
        UPDATE clients 
        SET created_at = datetime(created_at, 'utc'),
            updated_at = datetime(updated_at, 'utc')
    """)
    
    op.execute("""
        UPDATE habits 
        SET created_at = datetime(created_at, 'utc'),
            updated_at = datetime(updated_at, 'utc'),
            last_completed = CASE 
                WHEN last_completed IS NOT NULL THEN datetime(last_completed, 'utc')
                ELSE NULL 
            END
    """)
    
    op.execute("""
        UPDATE task_attachments 
        SET created_at = datetime(created_at, 'utc'),
            updated_at = datetime(updated_at, 'utc')
    """)
    
    op.execute("""
        UPDATE task_comments 
        SET created_at = datetime(created_at, 'utc'),
            updated_at = datetime(updated_at, 'utc')
    """)


def downgrade() -> None:
    """Downgrade schema."""
    
    # Remove timezone configuration table
    op.drop_table('timezone_config')
    
    # Note: We don't revert the datetime columns to naive timestamps
    # as this would lose timezone information. The application will
    # handle both timezone-aware and naive timestamps gracefully.
