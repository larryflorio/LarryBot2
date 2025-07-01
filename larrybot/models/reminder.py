from sqlalchemy import Column, Integer, DateTime, ForeignKey, func
from larrybot.models import Base

class Reminder(Base):
    """
    SQLAlchemy model for a task reminder.
    """
    __tablename__ = 'reminders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    remind_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False) 