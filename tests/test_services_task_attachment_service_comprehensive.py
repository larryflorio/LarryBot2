import pytest
from unittest.mock import Mock, patch
from larrybot.services.task_attachment_service import TaskAttachmentService
from larrybot.storage.task_attachment_repository import TaskAttachmentRepository
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task_attachment import TaskAttachment
from larrybot.models.task import Task


class TestTaskAttachmentServiceComprehensive:
    """Comprehensive tests for TaskAttachmentService covering all error paths and edge cases."""

    @pytest.fixture
    def mock_task_attachment_repository(self):
        """Create a mock task attachment repository."""
        return Mock(spec=TaskAttachmentRepository)

    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository."""
        return Mock(spec=TaskRepository)

    @pytest.fixture
    def attachment_service(self, mock_task_attachment_repository, mock_task_repository):
        """Create attachment service with mock repositories."""
        return TaskAttachmentService(mock_task_attachment_repository, mock_task_repository)

    @pytest.fixture
    def sample_task(self):
        """Create a sample task object."""
        task = Mock(spec=Task)
        task.id = 1
        task.description = "Test task"
        return task

    @pytest.fixture
    def sample_attachment(self):
        """Create a sample attachment object."""
        attachment = Mock(spec=TaskAttachment)
        attachment.id = 1
        attachment.task_id = 1
        attachment.original_filename = "test.pdf"
        attachment.file_size = 1024
        attachment.mime_type = "application/pdf"
        attachment.description = "Test attachment"
        attachment.is_public = False
        attachment.created_at = Mock()
        attachment.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        return attachment

    @pytest.fixture
    def valid_file_data(self):
        """Create valid file data for testing."""
        return b"PDF content here" * 100  # Small valid file

    # Execute Method Tests

    @pytest.mark.asyncio
    async def test_execute_unknown_operation(self, attachment_service):
        """Test execute with unknown operation."""
        result = await attachment_service.execute("unknown_operation")
        
        assert result['success'] is False
        assert "Unknown operation" in result['error']

    @pytest.mark.asyncio
    async def test_execute_attach_file_operation(self, attachment_service, mock_task_repository, sample_task, sample_attachment, valid_file_data):
        """Test execute with attach_file operation."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        attachment_service.task_attachment_repository.add_attachment.return_value = sample_attachment
        
        result = await attachment_service.execute("attach_file", 1, valid_file_data, "test.pdf")
        
        assert result['success'] is True
        assert "attached successfully" in result['message']

    @pytest.mark.asyncio
    async def test_execute_get_attachments_operation(self, attachment_service, mock_task_repository, sample_task):
        """Test execute with get_attachments operation."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        attachment_service.task_attachment_repository.get_attachments_by_task.return_value = []
        attachment_service.task_attachment_repository.get_attachment_stats.return_value = {}
        
        result = await attachment_service.execute("get_attachments", 1)
        
        assert result['success'] is True

    # Attach File Error Cases

    @pytest.mark.asyncio
    async def test_attach_file_task_not_found(self, attachment_service, mock_task_repository, valid_file_data):
        """Test attach file when task doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await attachment_service.attach_file(999, valid_file_data, "test.pdf")
        
        assert result['success'] is False
        assert "Task 999 not found" in result['error']

    @pytest.mark.asyncio
    async def test_attach_file_too_large(self, attachment_service, mock_task_repository, sample_task):
        """Test attach file when file is too large."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        large_file = b"x" * (11 * 1024 * 1024)  # 11MB file (exceeds 10MB limit)
        
        result = await attachment_service.attach_file(1, large_file, "large.pdf")
        
        assert result['success'] is False
        assert "File too large" in result['error']
        assert "10MB" in result['error']

    @pytest.mark.asyncio
    async def test_attach_file_invalid_filename_empty(self, attachment_service, mock_task_repository, sample_task, valid_file_data):
        """Test attach file with empty filename."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        
        result = await attachment_service.attach_file(1, valid_file_data, "")
        
        assert result['success'] is False
        assert "Invalid filename" in result['error']

    @pytest.mark.asyncio
    async def test_attach_file_invalid_filename_too_long(self, attachment_service, mock_task_repository, sample_task, valid_file_data):
        """Test attach file with filename too long."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        long_filename = "x" * 256 + ".pdf"  # 260 characters (exceeds 255 limit)
        
        result = await attachment_service.attach_file(1, valid_file_data, long_filename)
        
        assert result['success'] is False
        assert "Invalid filename" in result['error']

    @pytest.mark.asyncio
    async def test_attach_file_invalid_file_type(self, attachment_service, mock_task_repository, sample_task, valid_file_data):
        """Test attach file with disallowed file type."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        
        result = await attachment_service.attach_file(1, valid_file_data, "test.exe")
        
        assert result['success'] is False
        assert "File type not allowed" in result['error']
        assert ".exe" in result['error']

    @pytest.mark.asyncio
    async def test_attach_file_repository_failure(self, attachment_service, mock_task_repository, sample_task, valid_file_data):
        """Test attach file when repository fails to add attachment."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        attachment_service.task_attachment_repository.add_attachment.return_value = None
        
        result = await attachment_service.attach_file(1, valid_file_data, "test.pdf")
        
        assert result['success'] is False
        assert "Failed to attach file" in result['error']

    @pytest.mark.asyncio
    async def test_attach_file_repository_exception(self, attachment_service, mock_task_repository, sample_task, valid_file_data):
        """Test attach file when repository raises exception."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        attachment_service.task_attachment_repository.add_attachment.side_effect = Exception("Database error")
        
        result = await attachment_service.attach_file(1, valid_file_data, "test.pdf")
        
        assert result['success'] is False
        assert "Error attaching file" in result['context']

    # Get Attachments Error Cases

    @pytest.mark.asyncio
    async def test_get_attachments_task_not_found(self, attachment_service, mock_task_repository):
        """Test get attachments when task doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await attachment_service.get_task_attachments(999)
        
        assert result['success'] is False
        assert "Task 999 not found" in result['error']

    @pytest.mark.asyncio
    async def test_get_attachments_repository_exception(self, attachment_service, mock_task_repository, sample_task):
        """Test get attachments when repository raises exception."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        attachment_service.task_attachment_repository.get_attachments_by_task.side_effect = Exception("Database error")
        
        result = await attachment_service.get_task_attachments(1)
        
        assert result['success'] is False
        assert "Error retrieving attachments" in result['context']

    # Remove Attachment Error Cases

    @pytest.mark.asyncio
    async def test_remove_attachment_not_found(self, attachment_service):
        """Test remove attachment when attachment doesn't exist."""
        attachment_service.task_attachment_repository.remove_attachment.return_value = None
        
        result = await attachment_service.remove_attachment(999)
        
        assert result['success'] is False
        assert "Attachment 999 not found" in result['error']

    @pytest.mark.asyncio
    async def test_remove_attachment_repository_exception(self, attachment_service):
        """Test remove attachment when repository raises exception."""
        attachment_service.task_attachment_repository.remove_attachment.side_effect = Exception("Database error")
        
        result = await attachment_service.remove_attachment(1)
        
        assert result['success'] is False
        assert "Error removing attachment" in result['context']

    # Update Description Error Cases

    @pytest.mark.asyncio
    async def test_update_description_empty(self, attachment_service):
        """Test update description with empty description."""
        result = await attachment_service.update_attachment_description(1, "")
        
        assert result['success'] is False
        assert "Description must be between 1 and 1000 characters" in result['error']

    @pytest.mark.asyncio
    async def test_update_description_too_long(self, attachment_service):
        """Test update description with description too long."""
        long_description = "x" * 1001  # 1001 characters (exceeds 1000 limit)
        
        result = await attachment_service.update_attachment_description(1, long_description)
        
        assert result['success'] is False
        assert "Description must be between 1 and 1000 characters" in result['error']

    @pytest.mark.asyncio
    async def test_update_description_attachment_not_found(self, attachment_service):
        """Test update description when attachment doesn't exist."""
        attachment_service.task_attachment_repository.update_attachment_description.return_value = None
        
        result = await attachment_service.update_attachment_description(999, "Valid description")
        
        assert result['success'] is False
        assert "Attachment 999 not found" in result['error']

    @pytest.mark.asyncio
    async def test_update_description_repository_exception(self, attachment_service):
        """Test update description when repository raises exception."""
        attachment_service.task_attachment_repository.update_attachment_description.side_effect = Exception("Database error")
        
        result = await attachment_service.update_attachment_description(1, "Valid description")
        
        assert result['success'] is False
        assert "Error updating description" in result['context']

    # Get Stats Error Cases

    @pytest.mark.asyncio
    async def test_get_stats_task_not_found(self, attachment_service, mock_task_repository):
        """Test get stats when task doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await attachment_service.get_attachment_stats(999)
        
        assert result['success'] is False
        assert "Task 999 not found" in result['error']

    @pytest.mark.asyncio
    async def test_get_stats_repository_exception(self, attachment_service, mock_task_repository, sample_task):
        """Test get stats when repository raises exception."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        attachment_service.task_attachment_repository.get_attachment_stats.side_effect = Exception("Database error")
        
        result = await attachment_service.get_attachment_stats(1)
        
        assert result['success'] is False
        assert "Error retrieving statistics" in result['context']

    # Get Attachment By ID Error Cases

    @pytest.mark.asyncio
    async def test_get_attachment_by_id_not_found(self, attachment_service):
        """Test get attachment by ID when attachment doesn't exist."""
        attachment_service.task_attachment_repository.get_attachment_by_id.return_value = None
        
        result = await attachment_service.get_attachment_by_id(999)
        
        assert result['success'] is False
        assert "Attachment 999 not found" in result['error']

    @pytest.mark.asyncio
    async def test_get_attachment_by_id_repository_exception(self, attachment_service):
        """Test get attachment by ID when repository raises exception."""
        attachment_service.task_attachment_repository.get_attachment_by_id.side_effect = Exception("Database error")
        
        result = await attachment_service.get_attachment_by_id(1)
        
        assert result['success'] is False
        # Error message will be from the exception handling

    # Success Path Tests

    @pytest.mark.asyncio
    async def test_attach_file_success_all_parameters(self, attachment_service, mock_task_repository, sample_task, sample_attachment, valid_file_data):
        """Test successful file attachment with all parameters."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        attachment_service.task_attachment_repository.add_attachment.return_value = sample_attachment
        
        result = await attachment_service.attach_file(
            task_id=1,
            file_data=valid_file_data,
            original_filename="test.pdf",
            description="Test description",
            is_public=True
        )
        
        assert result['success'] is True
        assert result['data']['filename'] == "test.pdf"
        assert "attached successfully" in result['message']

    @pytest.mark.asyncio
    async def test_get_attachments_success_with_data(self, attachment_service, mock_task_repository, sample_task, sample_attachment):
        """Test successful get attachments with data."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        attachment_service.task_attachment_repository.get_attachments_by_task.return_value = [sample_attachment]
        attachment_service.task_attachment_repository.get_attachment_stats.return_value = {"total": 1}
        
        result = await attachment_service.get_task_attachments(1)
        
        assert result['success'] is True
        assert len(result['data']['attachments']) == 1
        assert result['data']['attachments'][0]['filename'] == "test.pdf"
        assert "Found 1 attachments" in result['message']

    @pytest.mark.asyncio
    async def test_remove_attachment_success(self, attachment_service, sample_attachment):
        """Test successful attachment removal."""
        attachment_service.task_attachment_repository.remove_attachment.return_value = sample_attachment
        
        result = await attachment_service.remove_attachment(1)
        
        assert result['success'] is True
        assert result['data']['filename'] == "test.pdf"
        assert "removed successfully" in result['message']

    @pytest.mark.asyncio
    async def test_update_description_success(self, attachment_service, sample_attachment):
        """Test successful description update."""
        attachment_service.task_attachment_repository.update_attachment_description.return_value = sample_attachment
        
        result = await attachment_service.update_attachment_description(1, "Updated description")
        
        assert result['success'] is True
        assert result['data']['description'] == "Updated description"
        assert "Description updated" in result['message']

    @pytest.mark.asyncio
    async def test_get_stats_success(self, attachment_service, mock_task_repository, sample_task):
        """Test successful stats retrieval."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        stats = {"total_attachments": 5, "total_size": 1024}
        attachment_service.task_attachment_repository.get_attachment_stats.return_value = stats
        
        result = await attachment_service.get_attachment_stats(1)
        
        assert result['success'] is True
        assert result['data'] == stats
        assert "Statistics retrieved successfully" in result['message']

    @pytest.mark.asyncio
    async def test_get_attachment_by_id_success(self, attachment_service, sample_attachment):
        """Test successful get attachment by ID."""
        attachment_service.task_attachment_repository.get_attachment_by_id.return_value = sample_attachment
        
        result = await attachment_service.get_attachment_by_id(1)
        
        assert result['success'] is True
        assert result['data']['filename'] == "test.pdf"
        assert "Attachment retrieved successfully" in result['message']

    # Configuration Tests

    def test_service_configuration(self, attachment_service):
        """Test service configuration values."""
        assert attachment_service.max_file_size == 10 * 1024 * 1024  # 10MB
        assert '.pdf' in attachment_service.allowed_extensions
        assert '.doc' in attachment_service.allowed_extensions
        assert '.exe' not in attachment_service.allowed_extensions

    # File Type Validation Edge Cases

    @pytest.mark.asyncio
    async def test_attach_file_case_insensitive_extensions(self, attachment_service, mock_task_repository, sample_task, sample_attachment, valid_file_data):
        """Test that file extensions are case insensitive."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        attachment_service.task_attachment_repository.add_attachment.return_value = sample_attachment
        
        # Test uppercase extension
        result = await attachment_service.attach_file(1, valid_file_data, "test.PDF")
        assert result['success'] is True
        
        # Test mixed case extension
        result = await attachment_service.attach_file(1, valid_file_data, "test.Pdf")
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_attach_file_no_extension(self, attachment_service, mock_task_repository, sample_task, valid_file_data):
        """Test attach file with no extension."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        
        result = await attachment_service.attach_file(1, valid_file_data, "filename_no_extension")
        
        assert result['success'] is False
        assert "File type not allowed" in result['error']

    # Boundary Testing

    @pytest.mark.asyncio
    async def test_attach_file_max_size_exactly(self, attachment_service, mock_task_repository, sample_task, sample_attachment):
        """Test attach file with exactly max file size."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        attachment_service.task_attachment_repository.add_attachment.return_value = sample_attachment
        
        max_size_file = b"x" * (10 * 1024 * 1024)  # Exactly 10MB
        
        result = await attachment_service.attach_file(1, max_size_file, "max_size.pdf")
        
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_update_description_max_length_exactly(self, attachment_service, sample_attachment):
        """Test update description with exactly max length."""
        attachment_service.task_attachment_repository.update_attachment_description.return_value = sample_attachment
        
        max_length_description = "x" * 1000  # Exactly 1000 characters
        
        result = await attachment_service.update_attachment_description(1, max_length_description)
        
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_filename_max_length_exactly(self, attachment_service, mock_task_repository, sample_task, sample_attachment, valid_file_data):
        """Test filename with exactly max length."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        attachment_service.task_attachment_repository.add_attachment.return_value = sample_attachment
        
        max_length_filename = "x" * 251 + ".pdf"  # Exactly 255 characters
        
        result = await attachment_service.attach_file(1, valid_file_data, max_length_filename)
        
        assert result['success'] is True 