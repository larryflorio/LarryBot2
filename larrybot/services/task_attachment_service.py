from typing import List, Optional, Dict, Any, Tuple
from larrybot.services.base_service import BaseService
from larrybot.storage.task_attachment_repository import TaskAttachmentRepository
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task_attachment import TaskAttachment
import os
import mimetypes


class TaskAttachmentService(BaseService):
    """Service layer for task attachment business logic."""

    def __init__(self, task_attachment_repository: TaskAttachmentRepository,
        task_repository: TaskRepository):
        super().__init__()
        self.task_attachment_repository = task_attachment_repository
        self.task_repository = task_repository
        self.max_file_size = 10 * 1024 * 1024

    async def execute(self, operation: str, *args, **kwargs) ->Any:
        """Execute attachment operations."""
        if operation == 'attach_file':
            return await self.attach_file(*args, **kwargs)
        elif operation == 'get_attachments':
            return await self.get_task_attachments(*args, **kwargs)
        elif operation == 'remove_attachment':
            return await self.remove_attachment(*args, **kwargs)
        elif operation == 'update_description':
            return await self.update_attachment_description(*args, **kwargs)
        elif operation == 'get_attachment_stats':
            return await self.get_attachment_stats(*args, **kwargs)
        else:
            return self._handle_error(ValueError(
                f'Unknown operation: {operation}'))

    async def attach_file(self, task_id: int, file_data: bytes,
        original_filename: str, description: Optional[str]=None, is_public:
        bool=False) ->Dict[str, Any]:
        """Attach a file to a task with validation."""
        try:
            task = self.task_repository.get_task_by_id(task_id)
            if not task:
                return self._handle_error(ValueError(
                    f'Task {task_id} not found'))
            if len(file_data) > self.max_file_size:
                return self._handle_error(ValueError(
                    f'File too large. Maximum size: {self.max_file_size // (1024 * 1024)}MB'
                    ))
            if not original_filename or len(original_filename) > 255:
                return self._handle_error(ValueError('Invalid filename'))
            attachment = self.task_attachment_repository.add_attachment(task_id
                =task_id, file_data=file_data, original_filename=
                original_filename, description=description, is_public=is_public
                )
            if attachment:
                return self._create_success_response({'id': attachment.id,
                    'filename': attachment.original_filename, 'size':
                    attachment.file_size, 'mime_type': attachment.mime_type,
                    'task_id': attachment.task_id},
                    f"File '{original_filename}' attached successfully")
            else:
                return self._handle_error(ValueError('Failed to attach file'))
        except Exception as e:
            return self._handle_error(e, 'Error attaching file')

    async def get_task_attachments(self, task_id: int) ->Dict[str, Any]:
        """Get all attachments for a task."""
        try:
            task = self.task_repository.get_task_by_id(task_id)
            if not task:
                return self._handle_error(ValueError(
                    f'Task {task_id} not found'))
            attachments = (self.task_attachment_repository.
                get_attachments_by_task(task_id))
            stats = self.task_attachment_repository.get_attachment_stats(
                task_id)
            attachment_data = []
            for att in attachments:
                attachment_data.append({'id': att.id, 'filename': att.
                    original_filename, 'size': att.file_size, 'mime_type':
                    att.mime_type, 'description': att.description,
                    'created_at': att.created_at.isoformat(), 'is_public':
                    att.is_public})
            return self._create_success_response({'attachments':
                attachment_data, 'stats': stats, 'task_id': task_id},
                f'Found {len(attachments)} attachments')
        except Exception as e:
            return self._handle_error(e, 'Error retrieving attachments')

    async def remove_attachment(self, attachment_id: int) ->Dict[str, Any]:
        """Remove an attachment."""
        try:
            attachment = self.task_attachment_repository.remove_attachment(
                attachment_id)
            if attachment:
                return self._create_success_response({'id': attachment.id,
                    'filename': attachment.original_filename, 'task_id':
                    attachment.task_id},
                    f"Attachment '{attachment.original_filename}' removed successfully"
                    )
            else:
                return self._handle_error(ValueError(
                    f'Attachment {attachment_id} not found'))
        except Exception as e:
            return self._handle_error(e, 'Error removing attachment')

    async def update_attachment_description(self, attachment_id: int,
        description: str) ->Dict[str, Any]:
        """Update attachment description."""
        try:
            if not description or len(description) > 1000:
                return self._handle_error(ValueError(
                    'Description must be between 1 and 1000 characters'))
            attachment = (self.task_attachment_repository.
                update_attachment_description(attachment_id, description))
            if attachment:
                return self._create_success_response({'id': attachment.id,
                    'filename': attachment.original_filename, 'description':
                    description, 'task_id': attachment.task_id},
                    f"Description updated for '{attachment.original_filename}'"
                    )
            else:
                return self._handle_error(ValueError(
                    f'Attachment {attachment_id} not found'))
        except Exception as e:
            return self._handle_error(e, 'Error updating description')

    async def get_attachment_stats(self, task_id: int) ->Dict[str, Any]:
        """Get attachment statistics for a task."""
        try:
            task = self.task_repository.get_task_by_id(task_id)
            if not task:
                return self._handle_error(ValueError(
                    f'Task {task_id} not found'))
            stats = self.task_attachment_repository.get_attachment_stats(
                task_id)
            return self._create_success_response(stats,
                'Statistics retrieved successfully')
        except Exception as e:
            return self._handle_error(e, 'Error retrieving statistics')

    async def get_attachment_by_id(self, attachment_id: int) ->Dict[str, Any]:
        """Get a specific attachment by ID."""
        try:
            attachment = self.task_attachment_repository.get_attachment_by_id(
                attachment_id)
            if attachment:
                return self._create_success_response({'id': attachment.id,
                    'filename': attachment.original_filename, 'size':
                    attachment.file_size, 'mime_type': attachment.mime_type,
                    'description': attachment.description, 'created_at':
                    attachment.created_at.isoformat(), 'task_id':
                    attachment.task_id}, 'Attachment retrieved successfully')
            else:
                return self._handle_error(ValueError(
                    f'Attachment {attachment_id} not found'))
        except Exception as e:
            return self._handle_error(e, 'Error retrieving attachment')
