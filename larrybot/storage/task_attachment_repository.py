from sqlalchemy.orm import Session
from larrybot.models.task_attachment import TaskAttachment
from larrybot.models.task import Task
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import hashlib
import mimetypes

class TaskAttachmentRepository:
    """Repository for CRUD operations on TaskAttachment model."""
    
    def __init__(self, session: Session):
        self.session = session
        self.storage_path = "attachments"  # Configurable storage path
    
    def add_attachment(self, 
                      task_id: int, 
                      file_data: bytes, 
                      original_filename: str,
                      description: Optional[str] = None,
                      is_public: bool = False) -> Optional[TaskAttachment]:
        """Add a file attachment to a task."""
        # Verify task exists
        task = self.session.query(Task).filter_by(id=task_id).first()
        if not task:
            return None
        
        # Generate unique filename
        file_hash = hashlib.md5(file_data).hexdigest()
        file_extension = os.path.splitext(original_filename)[1]
        filename = f"{file_hash}{file_extension}"
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(original_filename)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save file to disk
        file_path = os.path.join(self.storage_path, filename)
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Create attachment record
        attachment = TaskAttachment(
            task_id=task_id,
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=len(file_data),
            mime_type=mime_type,
            description=description,
            is_public=is_public
        )
        
        self.session.add(attachment)
        self.session.commit()
        return attachment
    
    def get_attachment_by_id(self, attachment_id: int) -> Optional[TaskAttachment]:
        """Get attachment by ID."""
        return self.session.query(TaskAttachment).filter_by(id=attachment_id).first()
    
    def get_attachments_by_task(self, task_id: int) -> List[TaskAttachment]:
        """Get all attachments for a task."""
        return self.session.query(TaskAttachment).filter_by(task_id=task_id).order_by(TaskAttachment.created_at).all()
    
    def remove_attachment(self, attachment_id: int) -> Optional[TaskAttachment]:
        """Remove an attachment."""
        attachment = self.get_attachment_by_id(attachment_id)
        if attachment:
            # Delete file from disk
            if os.path.exists(attachment.file_path):
                os.remove(attachment.file_path)
            
            # Remove from database
            self.session.delete(attachment)
            self.session.commit()
            return attachment
        return None
    
    def update_attachment_description(self, attachment_id: int, description: str) -> Optional[TaskAttachment]:
        """Update attachment description."""
        attachment = self.get_attachment_by_id(attachment_id)
        if attachment:
            attachment.description = description
            self.session.commit()
            return attachment
        return None
    
    def get_attachment_stats(self, task_id: int) -> Dict[str, Any]:
        """Get attachment statistics for a task."""
        attachments = self.get_attachments_by_task(task_id)
        total_size = sum(att.file_size for att in attachments)
        file_types = {}
        
        for att in attachments:
            ext = os.path.splitext(att.original_filename)[1].lower()
            file_types[ext] = file_types.get(ext, 0) + 1
        
        return {
            'count': len(attachments),
            'total_size': total_size,
            'file_types': file_types
        }
    
    def get_all_attachments(self) -> List[TaskAttachment]:
        """Get all attachments (for admin purposes)."""
        return self.session.query(TaskAttachment).order_by(TaskAttachment.created_at.desc()).all()
    
    def get_attachments_by_mime_type(self, mime_type: str) -> List[TaskAttachment]:
        """Get attachments by MIME type."""
        return self.session.query(TaskAttachment).filter_by(mime_type=mime_type).all()
    
    def get_large_attachments(self, size_threshold: int = 1024 * 1024) -> List[TaskAttachment]:
        """Get attachments larger than the specified threshold."""
        return self.session.query(TaskAttachment).filter(TaskAttachment.file_size > size_threshold).all() 