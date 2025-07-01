import os
import pytest
from larrybot.models.task import Task
from larrybot.storage.task_attachment_repository import TaskAttachmentRepository
from larrybot.storage.task_repository import TaskRepository
from larrybot.services.task_attachment_service import TaskAttachmentService
from sqlalchemy.orm import Session

@pytest.mark.asyncio
async def test_file_attachment_workflow(test_session: Session, tmp_path):
    """Test complete file attachment workflow."""
    # Setup repositories and service
    repo = TaskAttachmentRepository(test_session)
    repo.storage_path = str(tmp_path)
    task_repo = TaskRepository(test_session)
    service = TaskAttachmentService(repo, task_repo)
    
    # Create a task
    task = Task(description="Integration test task")
    test_session.add(task)
    test_session.commit()
    
    # Attach a file
    file_data = b"integration test file"
    attach_result = await service.attach_file(task.id, file_data, "integration.txt")
    
    assert attach_result["success"] is True
    assert attach_result["data"]["filename"] == "integration.txt"
    assert attach_result["data"]["size"] == 21  # "integration test file" is 21 bytes
    attachment_id = attach_result["data"]["id"]
    
    # Get attachments for the task
    list_result = await service.get_task_attachments(task.id)
    assert list_result["success"] is True
    assert len(list_result["data"]["attachments"]) == 1
    assert list_result["data"]["attachments"][0]["id"] == attachment_id
    
    # Update description
    update_result = await service.update_attachment_description(attachment_id, "Updated description")
    assert update_result["success"] is True
    assert update_result["data"]["description"] == "Updated description"
    
    # Get attachment by ID
    get_result = await service.get_attachment_by_id(attachment_id)
    assert get_result["success"] is True
    assert get_result["data"]["filename"] == "integration.txt"
    assert get_result["data"]["description"] == "Updated description"
    
    # Get stats
    stats_result = await service.get_attachment_stats(task.id)
    assert stats_result["success"] is True
    assert stats_result["data"]["count"] == 1
    assert stats_result["data"]["total_size"] == 21
    
    # Remove attachment
    remove_result = await service.remove_attachment(attachment_id)
    assert remove_result["success"] is True
    assert "removed successfully" in remove_result["message"]
    
    # Verify attachment is gone
    final_list_result = await service.get_task_attachments(task.id)
    assert final_list_result["success"] is True
    assert len(final_list_result["data"]["attachments"]) == 0

@pytest.mark.asyncio
async def test_multiple_attachments_per_task(test_session: Session, tmp_path):
    """Test attaching multiple files to a single task."""
    # Setup
    repo = TaskAttachmentRepository(test_session)
    repo.storage_path = str(tmp_path)
    task_repo = TaskRepository(test_session)
    service = TaskAttachmentService(repo, task_repo)
    
    # Create a task
    task = Task(description="Multiple attachments test")
    test_session.add(task)
    test_session.commit()
    
    # Attach multiple files
    files = [
        (b"file1 content", "file1.txt"),
        (b"file2 content", "file2.txt"),
        (b"file3 content", "file3.txt")
    ]
    
    attachment_ids = []
    for file_data, filename in files:
        result = await service.attach_file(task.id, file_data, filename)
        assert result["success"] is True
        attachment_ids.append(result["data"]["id"])
    
    # Verify all attachments exist
    list_result = await service.get_task_attachments(task.id)
    assert list_result["success"] is True
    assert len(list_result["data"]["attachments"]) == 3
    
    # Verify stats
    stats_result = await service.get_attachment_stats(task.id)
    assert stats_result["success"] is True
    assert stats_result["data"]["count"] == 3
    assert stats_result["data"]["total_size"] == 39  # 13 + 13 + 13

@pytest.mark.asyncio
async def test_attachment_validation_errors(test_session: Session, tmp_path):
    """Test various validation error scenarios."""
    # Setup
    repo = TaskAttachmentRepository(test_session)
    repo.storage_path = str(tmp_path)
    task_repo = TaskRepository(test_session)
    service = TaskAttachmentService(repo, task_repo)
    
    # Create a task
    task = Task(description="Validation test task")
    test_session.add(task)
    test_session.commit()
    
    # Test invalid task ID
    result = await service.attach_file(99999, b"test", "test.txt")
    assert result["success"] is False
    assert "not found" in result["error"]
    
    # Test oversized file
    large_file = b"x" * (11 * 1024 * 1024)  # 11MB
    result = await service.attach_file(task.id, large_file, "large.txt")
    assert result["success"] is False
    assert "too large" in result["error"]
    
    # Test invalid file type
    result = await service.attach_file(task.id, b"test", "test.exe")
    assert result["success"] is False
    assert "not allowed" in result["error"]
    
    # Test invalid filename (empty string)
    result = await service.attach_file(task.id, b"test", "")
    assert result["success"] is False
    assert "Invalid filename" in result["error"]
    
    # Test description too long
    valid_result = await service.attach_file(task.id, b"test", "valid.txt")
    assert valid_result["success"] is True
    attachment_id = valid_result["data"]["id"]
    
    long_description = "x" * 1001  # Over 1000 character limit
    result = await service.update_attachment_description(attachment_id, long_description)
    assert result["success"] is False
    assert "between 1 and 1000 characters" in result["error"] 