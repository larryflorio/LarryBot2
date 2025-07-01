from sqlalchemy import Column, Integer, String, Date, DateTime, func
from larrybot.models import Base
import datetime

class Habit(Base):
    """
    SQLAlchemy model for a habit.
    """
    __tablename__ = 'habits'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    streak = Column(Integer, default=0, nullable=False)
    last_completed = Column(Date, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False) 