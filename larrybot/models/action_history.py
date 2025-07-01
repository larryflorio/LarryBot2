from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func
from larrybot.models import Base

class ActionHistory(Base):
    """
    SQLAlchemy model for action history (for undo functionality).
    """
    __tablename__ = 'action_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_type = Column(String, nullable=False)  # e.g., 'task_created', 'task_completed'
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    undone = Column(Boolean, default=False, nullable=False) 