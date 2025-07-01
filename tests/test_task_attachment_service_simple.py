import pytest
from unittest.mock import Mock
from larrybot.services.task_attachment_service import TaskAttachmentService
from larrybot.storage.task_attachment_repository import TaskAttachmentRepository
from larrybot.storage.task_repository import TaskRepository


class TestTaskAttachmentServiceSimple:
    """Simple tests to cover uncovered paths in TaskAttachmentService."""

    @pytest.fixture
    def attachment_service(self):
        mock_attachment_repo = Mock(spec=TaskAttachmentRepository)
        mock_task_repo = Mock(spec=TaskRepository)
        return TaskAttachmentService(mock_attachment_repo, mock_task_repo)

    @pytest.fixture
    def valid_file_data(self):
        return b"Test file content"

    @pytest.mark.asyncio
    async def test_execute_unknown_operation(self, attachment_service):
        """Test unknown operation in execute method."""
        result = await attachment_service.execute("unknown")
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_attach_file_task_not_found(self, attachment_service, valid_file_data):
        """Test attach file when task doesn't exist."""
        attachment_service.task_repository.get_task_by_id.return_value = None
        result = await attachment_service.attach_file(1, valid_file_data, "test.pdf")
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_attach_file_too_large(self, attachment_service, valid_file_data):
        """Test attach file with large file."""
        attachment_service.task_repository.get_task_by_id.return_value = Mock()
        large_file = b"x" * (11 * 1024 * 1024)  # 11MB
        result = await attachment_service.attach_file(1, large_file, "large.pdf")
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_attach_file_empty_filename(self, attachment_service, valid_file_data):
        """Test attach file with empty filename."""
        attachment_service.task_repository.get_task_by_id.return_value = Mock()
        result = await attachment_service.attach_file(1, valid_file_data, "")
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_attach_file_long_filename(self, attachment_service, valid_file_data):
        """Test attach file with very long filename."""
        attachment_service.task_repository.get_task_by_id.return_value = Mock()
        long_name = "x" * 256 + ".pdf"
        result = await attachment_service.attach_file(1, valid_file_data, long_name)
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_attach_file_invalid_extension(self, attachment_service, valid_file_data):
        """Test attach file with invalid extension."""
        attachment_service.task_repository.get_task_by_id.return_value = Mock()
        result = await attachment_service.attach_file(1, valid_file_data, "test.exe")
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_attach_file_repository_failure(self, attachment_service, valid_file_data):
        """Test attach file when repository fails."""
        attachment_service.task_repository.get_task_by_id.return_value = Mock()
        attachment_service.task_attachment_repository.add_attachment.return_value = None
        result = await attachment_service.attach_file(1, valid_file_data, "test.pdf")
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_get_attachments_task_not_found(self, attachment_service):
        """Test get attachments when task not found."""
        attachment_service.task_repository.get_task_by_id.return_value = None
        result = await attachment_service.get_task_attachments(1)
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_remove_attachment_not_found(self, attachment_service):
        """Test remove attachment when not found."""
        attachment_service.task_attachment_repository.remove_attachment.return_value = None
        result = await attachment_service.remove_attachment(1)
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_update_description_empty(self, attachment_service):
        """Test update description with empty description."""
        result = await attachment_service.update_attachment_description(1, "")
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_update_description_too_long(self, attachment_service):
        """Test update description with description too long."""
        long_desc = "x" * 1001
        result = await attachment_service.update_attachment_description(1, long_desc)
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_update_description_not_found(self, attachment_service):
        """Test update description when attachment not found."""
        attachment_service.task_attachment_repository.update_attachment_description.return_value = None
        result = await attachment_service.update_attachment_description(1, "valid")
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_get_stats_task_not_found(self, attachment_service):
        """Test get stats when task not found."""
        attachment_service.task_repository.get_task_by_id.return_value = None
        result = await attachment_service.get_attachment_stats(1)
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_get_attachment_by_id_not_found(self, attachment_service):
        """Test get attachment by id when not found."""
        attachment_service.task_attachment_repository.get_attachment_by_id.return_value = None
        result = await attachment_service.get_attachment_by_id(1)
        assert result['success'] is False

    # Success cases to ensure we cover positive paths too
    @pytest.mark.asyncio
    async def test_attach_file_success(self, attachment_service, valid_file_data):
        """Test successful file attachment."""
        attachment_service.task_repository.get_task_by_id.return_value = Mock()
        mock_attachment = Mock()
        mock_attachment.id = 1
        mock_attachment.original_filename = "test.pdf"
        mock_attachment.file_size = 1024
        mock_attachment.mime_type = "application/pdf"
        mock_attachment.task_id = 1
        attachment_service.task_attachment_repository.add_attachment.return_value = mock_attachment
        
        result = await attachment_service.attach_file(1, valid_file_data, "test.pdf")
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_get_attachments_success(self, attachment_service):
        """Test successful get attachments."""
        attachment_service.task_repository.get_task_by_id.return_value = Mock()
        attachment_service.task_attachment_repository.get_attachments_by_task.return_value = []
        attachment_service.task_attachment_repository.get_attachment_stats.return_value = {}
        
        result = await attachment_service.get_task_attachments(1)
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_remove_attachment_success(self, attachment_service):
        """Test successful attachment removal."""
        mock_attachment = Mock()
        mock_attachment.id = 1
        mock_attachment.original_filename = "test.pdf"
        mock_attachment.task_id = 1
        attachment_service.task_attachment_repository.remove_attachment.return_value = mock_attachment
        
        result = await attachment_service.remove_attachment(1)
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_update_description_success(self, attachment_service):
        """Test successful description update."""
        mock_attachment = Mock()
        mock_attachment.id = 1
        mock_attachment.original_filename = "test.pdf"
        mock_attachment.task_id = 1
        attachment_service.task_attachment_repository.update_attachment_description.return_value = mock_attachment
        
        result = await attachment_service.update_attachment_description(1, "Updated description")
        assert result['success'] is True

    def test_service_configuration(self, attachment_service):
        """Test service has correct configuration."""
        assert attachment_service.max_file_size == 10 * 1024 * 1024
        assert '.pdf' in attachment_service.allowed_extensions
        assert '.exe' not in attachment_service.allowed_extensions

    @pytest.mark.asyncio
    async def test_file_extension_case_insensitive(self, attachment_service, valid_file_data):
        """Test file extensions are case insensitive."""
        attachment_service.task_repository.get_task_by_id.return_value = Mock()
        mock_attachment = Mock()
        mock_attachment.id = 1
        mock_attachment.original_filename = "test.PDF"
        mock_attachment.file_size = 1024
        mock_attachment.mime_type = "application/pdf"
        mock_attachment.task_id = 1
        attachment_service.task_attachment_repository.add_attachment.return_value = mock_attachment
        
        result = await attachment_service.attach_file(1, valid_file_data, "test.PDF")
        assert result['success'] is True

    @pytest.mark.asyncio  
    async def test_no_file_extension(self, attachment_service, valid_file_data):
        """Test file with no extension is rejected."""
        attachment_service.task_repository.get_task_by_id.return_value = Mock()
        result = await attachment_service.attach_file(1, valid_file_data, "filename_no_ext")
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_max_file_size_boundary(self, attachment_service):
        """Test exactly max file size."""
        attachment_service.task_repository.get_task_by_id.return_value = Mock()
        mock_attachment = Mock()
        mock_attachment.id = 1
        mock_attachment.original_filename = "max.pdf"
        mock_attachment.file_size = 10 * 1024 * 1024
        mock_attachment.mime_type = "application/pdf"
        mock_attachment.task_id = 1
        attachment_service.task_attachment_repository.add_attachment.return_value = mock_attachment
        
        max_file = b"x" * (10 * 1024 * 1024)  # Exactly 10MB
        result = await attachment_service.attach_file(1, max_file, "max.pdf")
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_max_filename_length_boundary(self, attachment_service, valid_file_data):
        """Test exactly max filename length."""
        attachment_service.task_repository.get_task_by_id.return_value = Mock()
        mock_attachment = Mock()
        mock_attachment.id = 1
        mock_attachment.file_size = 1024
        mock_attachment.mime_type = "application/pdf"
        mock_attachment.task_id = 1
        attachment_service.task_attachment_repository.add_attachment.return_value = mock_attachment
        
        max_filename = "x" * 251 + ".pdf"  # Exactly 255 chars
        mock_attachment.original_filename = max_filename
        result = await attachment_service.attach_file(1, valid_file_data, max_filename)
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_max_description_length_boundary(self, attachment_service):
        """Test exactly max description length."""
        mock_attachment = Mock()
        mock_attachment.id = 1
        mock_attachment.original_filename = "test.pdf"
        mock_attachment.task_id = 1
        attachment_service.task_attachment_repository.update_attachment_description.return_value = mock_attachment
        
        max_description = "x" * 1000  # Exactly 1000 chars
        result = await attachment_service.update_attachment_description(1, max_description)
        assert result['success'] is True 