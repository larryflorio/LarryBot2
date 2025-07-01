import pytest
from larrybot.models.task import Task
from larrybot.models.task_attachment import TaskAttachment
from sqlalchemy.orm import Session
from datetime import datetime

def test_task_attachment_model_fields(test_session: Session):
    # Create a dummy task
    task = Task(description="Test task")
    test_session.add(task)
    test_session.commit()
    
    # Create a TaskAttachment
    attachment = TaskAttachment(
        task_id=task.id,
        filename="file1.pdf",
        original_filename="original.pdf",
        file_path="attachments/file1.pdf",
        file_size=1234,
        mime_type="application/pdf",
        description="Test file",
        is_public=False
    )
    test_session.add(attachment)
    test_session.commit()
    
    # Fetch and assert
    fetched = test_session.query(TaskAttachment).filter_by(id=attachment.id).first()
    assert fetched is not None
    assert fetched.task_id == task.id
    assert fetched.filename == "file1.pdf"
    assert fetched.original_filename == "original.pdf"
    assert fetched.file_size == 1234
    assert fetched.mime_type == "application/pdf"
    assert fetched.description == "Test file"
    assert fetched.is_public is False
    assert isinstance(fetched.created_at, datetime)
    assert isinstance(fetched.updated_at, datetime)
    # Relationship
    assert fetched.task.id == task.id 