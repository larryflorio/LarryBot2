import pytest
from unittest.mock import Mock, patch
from larrybot.services.task_attachment_service import TaskAttachmentService
from larrybot.storage.task_attachment_repository import TaskAttachmentRepository
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task import Task
from larrybot.models.task_attachment import TaskAttachment


@pytest.fixture
def service_and_task(test_session):
    """Create service and task for testing."""
    repo = TaskAttachmentRepository(test_session)
    repo.storage_path = "/tmp/test_attachments"
    task_repo = TaskRepository(test_session)
    service = TaskAttachmentService(repo, task_repo)
    
    # Create a test task
    task = Task(description="Test task")
    test_session.add(task)
    test_session.commit()
    
    return service, task


@pytest.mark.asyncio
async def test_attach_file_success(service_and_task):
    """Test successful file attachment."""
    service, task = service_and_task
    file_data = b"hello world"
    result = await service.attach_file(task.id, file_data, "file.txt")
    
    assert result["success"] is True
    assert result["data"]["filename"] == "file.txt"
    assert result["data"]["size"] == 11
    assert result["data"]["task_id"] == task.id
    assert "attached successfully" in result["message"]


@pytest.mark.asyncio
async def test_attach_file_invalid_task(service_and_task):
    """Test file attachment with invalid task ID."""
    service, _ = service_and_task
    file_data = b"abc"
    result = await service.attach_file(9999, file_data, "file.txt")
    
    assert result["success"] is False
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_attach_file_too_large(service_and_task):
    """Test file attachment with oversized file."""
    service, task = service_and_task
    file_data = b"a" * (11 * 1024 * 1024)  # 11MB
    result = await service.attach_file(task.id, file_data, "file.txt")
    
    assert result["success"] is False
    assert "too large" in result["error"]


@pytest.mark.asyncio
async def test_attach_file_invalid_type(service_and_task):
    """Test file attachment with invalid file type."""
    service, task = service_and_task
    file_data = b"abc"
    result = await service.attach_file(task.id, file_data, "file.exe")
    
    assert result["success"] is False
    assert "not allowed" in result["error"]


@pytest.mark.asyncio
async def test_update_description(service_and_task):
    """Test updating attachment description."""
    service, task = service_and_task
    file_data = b"abc"
    attach_result = await service.attach_file(task.id, file_data, "file.txt")
    
    assert attach_result["success"] is True
    attachment_id = attach_result["data"]["id"]
    
    # Update description
    result = await service.update_attachment_description(attachment_id, "Updated description")
    assert result["success"] is True
    assert result["data"]["description"] == "Updated description"


@pytest.mark.asyncio
async def test_get_task_attachments(service_and_task):
    """Test retrieving task attachments."""
    service, task = service_and_task
    file_data = b"test content"
    
    # Attach a file
    attach_result = await service.attach_file(task.id, file_data, "test.txt")
    assert attach_result["success"] is True
    
    # Get attachments
    result = await service.get_task_attachments(task.id)
    assert result["success"] is True
    assert len(result["data"]["attachments"]) == 1
    assert result["data"]["attachments"][0]["filename"] == "test.txt"


@pytest.mark.asyncio
async def test_remove_attachment(service_and_task):
    """Test removing an attachment."""
    service, task = service_and_task
    file_data = b"test content"
    
    # Attach a file
    attach_result = await service.attach_file(task.id, file_data, "test.txt")
    assert attach_result["success"] is True
    attachment_id = attach_result["data"]["id"]
    
    # Remove attachment
    result = await service.remove_attachment(attachment_id)
    assert result["success"] is True
    assert "removed successfully" in result["message"]


@pytest.mark.asyncio
async def test_get_attachment_stats(service_and_task):
    """Test getting attachment statistics."""
    service, task = service_and_task
    file_data = b"test content"
    
    # Attach a file
    attach_result = await service.attach_file(task.id, file_data, "test.txt")
    assert attach_result["success"] is True
    
    # Get stats
    result = await service.get_attachment_stats(task.id)
    assert result["success"] is True
    assert "count" in result["data"]
    assert result["data"]["count"] == 1 