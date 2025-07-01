from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from larrybot.models import Base

class TaskDependency(Base):
    """
    SQLAlchemy model for task dependencies.
    """
    __tablename__ = 'task_dependencies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    dependency_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    dependency = relationship("Task", foreign_keys=[dependency_id], back_populates="dependents") 