from sqlalchemy import Column, Integer, String, Date, DateTime, func
from larrybot.models import Base
import datetime


class Habit(Base):
    """
    SQLAlchemy model for a habit.
    All datetime fields are stored as UTC and must be timezone-aware in the application layer.
    """
    __tablename__ = 'habits'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    streak = Column(Integer, default=0, nullable=False)
    last_completed = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(),
        nullable=False)
