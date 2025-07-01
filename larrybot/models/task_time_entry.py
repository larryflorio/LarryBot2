from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from larrybot.models import Base

class TaskTimeEntry(Base):
    """
    SQLAlchemy model for task time entries.
    """
    __tablename__ = 'task_time_entries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)  # Null if still running
    duration_minutes = Column(Integer, nullable=True)  # Calculated when ended
    description = Column(Text, nullable=True)  # Optional description of work done
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="time_entries") 