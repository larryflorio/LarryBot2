from sqlalchemy import Column, Integer, String, DateTime, func
from larrybot.models import Base
from typing import Optional

class CalendarToken(Base):
    """
    SQLAlchemy model for storing OAuth tokens for calendar integrations.
    """
    __tablename__ = 'calendar_tokens'

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String, nullable=False)  # e.g., 'google'
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False) 