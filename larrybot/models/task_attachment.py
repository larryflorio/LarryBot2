from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from larrybot.models import Base

class TaskAttachment(Base):
    """SQLAlchemy model for task file attachments."""
    __tablename__ = 'task_attachments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # Local storage path
    file_url = Column(String(500), nullable=True)    # External URL (optional)
    file_size = Column(Integer, nullable=False)      # Size in bytes
    mime_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="attachments")
    
    def __repr__(self):
        return f"<TaskAttachment(id={self.id}, task_id={self.task_id}, filename='{self.filename}')>" 