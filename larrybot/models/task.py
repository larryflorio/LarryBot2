from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, DECIMAL, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from larrybot.models import Base

class Task(Base):
    """
    SQLAlchemy model for a task with enhanced features.
    """
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String, nullable=False)
    done = Column(Boolean, default=False, nullable=False)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=True)
    
    # Phase 1 Enhanced Fields
    priority = Column(String(20), default='Medium', nullable=False)
    due_date = Column(DateTime, nullable=True)
    category = Column(String(100), nullable=True)
    status = Column(String(20), default='Todo', nullable=False)
    estimated_hours = Column(DECIMAL(5, 2), nullable=True)
    actual_hours = Column(DECIMAL(5, 2), nullable=True)
    started_at = Column(DateTime, nullable=True)
    parent_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    tags = Column(Text, nullable=True)  # JSON array as text
    description_rich = Column(Text, nullable=True)  # Markdown support
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="tasks")
    
    # Self-referencing relationships for parent/child tasks
    parent = relationship("Task", remote_side=[id], back_populates="subtasks")
    subtasks = relationship("Task", back_populates="parent")
    
    # Dependencies (tasks this task depends on)
    dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task"
    )
    
    # Dependents (tasks that depend on this task)
    dependents = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.dependency_id",
        back_populates="dependency"
    )
    
    # Comments
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    
    # Time entries
    time_entries = relationship("TaskTimeEntry", back_populates="task", cascade="all, delete-orphan")
    
    # File attachments
    attachments = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan") 