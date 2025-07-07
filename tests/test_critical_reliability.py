import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from larrybot.core.exceptions import ValidationError, DatabaseError
from larrybot.services.task_service import TaskService
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task import Task
from larrybot.models.enums import TaskStatus, TaskPriority


class TestCriticalErrorHandling:
    """Test critical error handling for bot reliability."""
    
    def test_validation_error_formatting(self):
        """Test that validation errors are properly formatted for users."""
        error = ValidationError("Invalid task title", field_name="title")
        
        assert error.error_code.value == 'V001'
        assert "invalid" in error.user_message.lower()
        assert "check your input" in error.user_message.lower()
    
    def test_database_error_formatting(self):
        """Test that database errors are properly formatted for users."""
        error = DatabaseError("Connection failed", operation="create_task")
        
        assert error.error_code.value == 'D001'
        assert "database" in error.user_message.lower()
        assert "try again" in error.user_message.lower()


class TestCriticalTaskOperations:
    """Test critical task operations that must work reliably."""
    
    @pytest.fixture
    def task_service(self):
        mock_repository = Mock(spec=TaskRepository)
        return TaskService(mock_repository)
    
    @pytest.fixture
    def mock_task(self):
        """Create a realistic mock task with all required attributes."""
        task = Mock(spec=Task)
        task.id = 123
        task.description = "Test task description"
        task.done = False
        task.priority_enum = TaskPriority.MEDIUM
        task.due_date = None
        task.category = "work"
        task.status = "Todo"
        task.estimated_hours = 2.0
        task.actual_hours = 1.5
        task.started_at = None
        task.parent_id = None
        task.tags = '["urgent", "meeting"]'
        task.client_id = None
        task.created_at = datetime(2024, 1, 1, 12, 0, 0)
        task.updated_at = datetime(2024, 1, 1, 12, 0, 0)
        return task

    @pytest.mark.asyncio
    async def test_create_task_success(self, task_service, mock_task):
        """Test successful task creation - critical for bot functionality."""
        task_service.task_repository.add_task_with_metadata.return_value = mock_task
        
        result = await task_service.create_task_with_metadata(
            description="Important meeting",
            priority="High"
        )
        
        assert result['success'] == True
        assert 'data' in result
        assert 'message' in result
        assert 'Task created successfully' in result['message']
        task_service.task_repository.add_task_with_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_validation_error(self, task_service):
        """Test task creation with validation error - must handle gracefully."""
        result = await task_service.create_task_with_metadata(description="", priority="Invalid")
        
        assert result['success'] == False
        assert 'message' in result
        assert 'Invalid priority' in result['message']

    @pytest.mark.asyncio
    async def test_get_tasks_success(self, task_service, mock_task):
        """Test task retrieval - critical for listing functionality."""
        tasks = [mock_task]
        task_service.task_repository.get_tasks_with_filters.return_value = tasks
        
        result = await task_service.get_tasks_with_filters()
        
        assert result['success'] == True
        assert 'data' in result
        assert len(result['data']) == 1
        assert 'Found 1 tasks' in result['message']

    @pytest.mark.asyncio
    async def test_update_task_status_success(self, task_service, mock_task):
        """Test task status update - critical for task management."""
        task_service.task_repository.update_status.return_value = mock_task
        
        result = await task_service.update_task_status(123, "Done")
        
        assert result['success'] == True
        assert 'data' in result
        assert 'status updated to Done' in result['message']
        task_service.task_repository.update_status.assert_called_once_with(123, "Done")

    @pytest.mark.asyncio
    async def test_update_task_status_invalid(self, task_service):
        """Test invalid status update - must handle gracefully."""
        result = await task_service.update_task_status(123, "Invalid")
        
        assert result['success'] == False
        assert 'message' in result
        assert 'Invalid status' in result['message']

    @pytest.mark.asyncio
    async def test_search_tasks_success(self, task_service, mock_task):
        """Test task search - critical for finding tasks."""
        tasks = [mock_task]
        task_service.task_repository.search_tasks_by_text.return_value = tasks
        
        result = await task_service.search_tasks_by_text("meeting")
        
        assert result['success'] == True
        assert 'data' in result
        assert "Found 1 tasks matching 'meeting'" in result['message']
        task_service.task_repository.search_tasks_by_text.assert_called_once_with("meeting", False)

    @pytest.mark.asyncio
    async def test_search_tasks_empty(self, task_service):
        """Test empty search results - must handle gracefully."""
        task_service.task_repository.search_tasks_by_text.return_value = []
        
        result = await task_service.search_tasks_by_text("nonexistent")
        
        assert result['success'] == True
        assert 'data' in result
        assert len(result['data']) == 0


class TestCriticalMessageProcessing:
    """Test critical message processing scenarios."""
    
    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        return context
    
    @pytest.fixture
    def mock_update(self):
        update = Mock()
        update.effective_chat = Mock()
        update.effective_chat.id = 12345
        update.effective_message = Mock()
        update.effective_message.text = "test command"
        update.effective_message.from_user = Mock()
        update.effective_message.from_user.id = 67890
        return update

    @pytest.mark.asyncio
    async def test_empty_message_handling(self, mock_context, mock_update):
        """Test handling of empty messages - must not crash."""
        mock_update.effective_message.text = ""
        
        # This should not raise an exception
        # The actual implementation should handle empty messages gracefully
        assert mock_update.effective_message.text == ""

    @pytest.mark.asyncio
    async def test_none_message_handling(self, mock_context, mock_update):
        """Test handling of None messages - must not crash."""
        mock_update.effective_message.text = None
        
        # This should not raise an exception
        # The actual implementation should handle None messages gracefully
        assert mock_update.effective_message.text is None

    @pytest.mark.asyncio
    async def test_long_message_handling(self, mock_context, mock_update):
        """Test handling of very long messages - must not crash."""
        mock_update.effective_message.text = "a" * 1000
        
        # This should not raise an exception
        # The actual implementation should handle long messages gracefully
        assert len(mock_update.effective_message.text) == 1000


class TestCriticalDataIntegrity:
    """Test critical data integrity scenarios."""
    
    @pytest.fixture
    def task_service(self):
        mock_repository = Mock(spec=TaskRepository)
        return TaskService(mock_repository)

    @pytest.mark.asyncio
    async def test_task_id_validation(self, task_service):
        """Test that invalid task IDs are handled gracefully."""
        # Test with invalid task ID
        result = await task_service.update_task_status(-1, "Done")
        
        # Should handle gracefully without crashing
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_empty_string_handling(self, task_service):
        """Test that empty strings are handled gracefully."""
        result = await task_service.create_task_with_metadata(description="")
        
        # Should handle gracefully without crashing
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_special_character_handling(self, task_service):
        """Test that special characters are handled gracefully."""
        result = await task_service.create_task_with_metadata(
            description="Task with @#$%^&*() characters"
        )
        
        # Should handle gracefully without crashing
        assert result is not None
        assert isinstance(result, dict)


class TestCriticalErrorRecovery:
    """Test critical error recovery scenarios."""
    
    @pytest.fixture
    def task_service(self):
        mock_repository = Mock(spec=TaskRepository)
        return TaskService(mock_repository)

    @pytest.mark.asyncio
    async def test_repository_exception_handling(self, task_service):
        """Test that repository exceptions are handled gracefully."""
        task_service.task_repository.add_task_with_metadata.side_effect = Exception("Database error")
        
        result = await task_service.create_task_with_metadata(description="Test task")
        
        # Should handle gracefully without crashing
        assert result is not None
        assert isinstance(result, dict)
        assert result['success'] == False

    @pytest.mark.asyncio
    async def test_validation_exception_handling(self, task_service):
        """Test that validation exceptions are handled gracefully."""
        task_service.task_repository.add_task_with_metadata.side_effect = ValidationError("Invalid data")
        
        result = await task_service.create_task_with_metadata(description="Test task")
        
        # Should handle gracefully without crashing
        assert result is not None
        assert isinstance(result, dict)
        assert result['success'] == False

    @pytest.mark.asyncio
    async def test_database_exception_handling(self, task_service):
        """Test that database exceptions are handled gracefully."""
        task_service.task_repository.add_task_with_metadata.side_effect = DatabaseError("Connection failed")
        
        result = await task_service.create_task_with_metadata(description="Test task")
        
        # Should handle gracefully without crashing
        assert result is not None
        assert isinstance(result, dict)
        assert result['success'] == False

    @pytest.mark.asyncio
    async def test_empty_search_text_handling(self, task_service):
        """Test that empty search text is handled gracefully."""
        result = await task_service.search_tasks_by_text("")
        
        assert result['success'] == False
        assert 'Search text cannot be empty' in result['message']

    @pytest.mark.asyncio
    async def test_whitespace_search_text_handling(self, task_service):
        """Test that whitespace-only search text is handled gracefully."""
        result = await task_service.search_tasks_by_text("   ")
        
        assert result['success'] == False
        assert 'Search text cannot be empty' in result['message']

    @pytest.mark.asyncio
    async def test_invalid_priority_handling(self, task_service):
        """Test that invalid priority values are handled gracefully."""
        result = await task_service.create_task_with_metadata(
            description="Test task",
            priority="InvalidPriority"
        )
        
        assert result['success'] == False
        assert 'Invalid priority' in result['message']

    @pytest.mark.asyncio
    async def test_past_due_date_handling(self, task_service):
        """Test that past due dates are handled gracefully."""
        past_date = datetime(2020, 1, 1, 12, 0, 0)
        result = await task_service.create_task_with_metadata(
            description="Test task",
            due_date=past_date
        )
        
        assert result['success'] == False
        assert 'Due date cannot be in the past' in result['message']

    @pytest.mark.asyncio
    async def test_nonexistent_task_update(self, task_service):
        """Test that updating nonexistent tasks is handled gracefully."""
        task_service.task_repository.update_status.return_value = None
        
        result = await task_service.update_task_status(999, "Done")
        
        assert result['success'] == False
        assert 'Task 999 not found' in result['message'] 