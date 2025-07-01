import os
import tempfile
import pytest
from larrybot.models.task import Task
from larrybot.storage.task_attachment_repository import TaskAttachmentRepository
from sqlalchemy.orm import Session

def test_add_and_get_attachment(test_session: Session, tmp_path):
    # Setup
    repo = TaskAttachmentRepository(test_session)
    repo.storage_path = str(tmp_path)
    task = Task(description="Test task")
    test_session.add(task)
    test_session.commit()
    file_data = b"test file content"
    original_filename = "test.txt"
    
    # Add attachment
    attachment = repo.add_attachment(
        task_id=task.id,
        file_data=file_data,
        original_filename=original_filename,
        description="desc"
    )
    assert attachment is not None
    assert os.path.exists(attachment.file_path)
    
    # Get by ID
    fetched = repo.get_attachment_by_id(attachment.id)
    assert fetched is not None
    assert fetched.original_filename == original_filename
    
    # Get by task
    attachments = repo.get_attachments_by_task(task.id)
    assert len(attachments) == 1
    
    # Remove
    removed = repo.remove_attachment(attachment.id)
    assert removed is not None
    assert not os.path.exists(removed.file_path)
    assert repo.get_attachment_by_id(attachment.id) is None

def test_update_attachment_description(test_session: Session, tmp_path):
    repo = TaskAttachmentRepository(test_session)
    repo.storage_path = str(tmp_path)
    task = Task(description="Task")
    test_session.add(task)
    test_session.commit()
    file_data = b"abc"
    att = repo.add_attachment(task.id, file_data, "a.txt")
    updated = repo.update_attachment_description(att.id, "new desc")
    assert updated.description == "new desc" 