"""add_multi_account_calendar_support

Revision ID: 2d56b2550005
Revises: a7d2eaa88f6e
Create Date: 2025-07-03 11:42:05.154781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d56b2550005'
down_revision: Union[str, Sequence[str], None] = 'a7d2eaa88f6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to support multiple calendar accounts."""
    # Add new columns for multi-account support (nullable for SQLite compatibility)
    op.add_column('calendar_tokens', sa.Column('account_id', sa.String(), nullable=True))
    op.add_column('calendar_tokens', sa.Column('account_name', sa.String(), nullable=True))
    op.add_column('calendar_tokens', sa.Column('account_email', sa.String(), nullable=True))
    op.add_column('calendar_tokens', sa.Column('is_primary', sa.Boolean(), nullable=True, default=False))
    op.add_column('calendar_tokens', sa.Column('is_active', sa.Boolean(), nullable=True, default=True))
    
    # Migrate existing data
    op.execute("""
        UPDATE calendar_tokens 
        SET account_id = 'default', 
            account_name = 'Default Account',
            is_primary = true,
            is_active = true
        WHERE provider = 'google' AND account_id IS NULL
    """)
    
    # Add unique constraint for provider + account_id
    op.create_unique_constraint('uq_provider_account', 'calendar_tokens', ['provider', 'account_id'])


def downgrade() -> None:
    """Downgrade schema to single account support."""
    # Remove unique constraint
    op.drop_constraint('uq_provider_account', 'calendar_tokens', type_='unique')
    
    # Remove new columns
    op.drop_column('calendar_tokens', 'is_active')
    op.drop_column('calendar_tokens', 'is_primary')
    op.drop_column('calendar_tokens', 'account_email')
    op.drop_column('calendar_tokens', 'account_name')
    op.drop_column('calendar_tokens', 'account_id')
