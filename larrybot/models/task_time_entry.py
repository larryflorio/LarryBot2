from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from larrybot.models import Base


class TaskTimeEntry(Base):
    """
    SQLAlchemy model for task time entries.
    All datetime fields are stored as UTC and must be timezone-aware in the application layer.
    """
    __tablename__ = 'task_time_entries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow,
        nullable=False)
    task = relationship('Task', back_populates='time_entries')

    @property
    def hours(self) -> float:
        """Get duration in hours."""
        return (self.duration_minutes or 0) / 60.0
