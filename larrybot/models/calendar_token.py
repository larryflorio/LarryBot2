from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, UniqueConstraint
from larrybot.models import Base
from typing import Optional


class CalendarToken(Base):
    """
    SQLAlchemy model for storing OAuth tokens for calendar integrations.
    Supports multiple accounts per provider with enhanced account management.
    All datetime fields are stored as UTC and must be timezone-aware in the application layer.
    """
    __tablename__ = 'calendar_tokens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String, nullable=False)
    account_id = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    account_email = Column(String, nullable=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    expiry = Column(DateTime(timezone=True), nullable=True)
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(),
        nullable=False)
    __table_args__ = UniqueConstraint('provider', 'account_id', name=
        'uq_provider_account'),
