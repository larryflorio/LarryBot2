from sqlalchemy import Column, Integer, DateTime, ForeignKey, func
from larrybot.models import Base

class Reminder(Base):
    """
    SQLAlchemy model for a task reminder.
    All datetime fields are stored as UTC and must be timezone-aware in the application layer.
    """
    __tablename__ = 'reminders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    remind_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False) 