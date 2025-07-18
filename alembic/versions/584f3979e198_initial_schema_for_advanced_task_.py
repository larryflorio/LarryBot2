"""Initial schema for advanced task management

Revision ID: 584f3979e198
Revises: 
Create Date: 2025-06-27 13:03:22.493882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '584f3979e198'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('calendar_tokens',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('provider', sa.String(), nullable=False),
    sa.Column('access_token', sa.String(), nullable=False),
    sa.Column('refresh_token', sa.String(), nullable=True),
    sa.Column('expiry', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('clients',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('habits',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('streak', sa.Integer(), nullable=False),
    sa.Column('last_completed', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('tasks',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('done', sa.Boolean(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=True),
    sa.Column('priority', sa.String(length=20), nullable=False),
    sa.Column('due_date', sa.DateTime(), nullable=True),
    sa.Column('category', sa.String(length=100), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('estimated_hours', sa.DECIMAL(precision=5, scale=2), nullable=True),
    sa.Column('actual_hours', sa.DECIMAL(precision=5, scale=2), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('tags', sa.Text(), nullable=True),
    sa.Column('description_rich', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['parent_id'], ['tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('action_history',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('action_type', sa.String(), nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=True),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('undone', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('reminders',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('remind_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('task_comments',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('comment', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('task_dependencies',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('dependency_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['dependency_id'], ['tasks.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('task_time_entries',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=False),
    sa.Column('ended_at', sa.DateTime(), nullable=True),
    sa.Column('duration_minutes', sa.Integer(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('task_time_entries')
    op.drop_table('task_dependencies')
    op.drop_table('task_comments')
    op.drop_table('reminders')
    op.drop_table('action_history')
    op.drop_table('tasks')
    op.drop_table('habits')
    op.drop_table('clients')
    op.drop_table('calendar_tokens')
    # ### end Alembic commands ###
