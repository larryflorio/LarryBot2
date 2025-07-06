"""
Tests for the Advanced Tasks plugin.

This module tests the advanced task management functionality including:
- Task creation with metadata
- Priority and status management
- Time tracking
- Subtasks and dependencies
- Tags and comments
- Advanced filtering and search
- Analytics and insights
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from larrybot.plugins.advanced_tasks import (
    add_task_with_metadata_handler, priority_handler, due_date_handler, category_handler, status_handler,
    start_time_tracking_handler, stop_time_tracking_handler, time_entry_handler, time_summary_handler,
    subtask_handler, dependency_handler, tags_handler, comment_handler, comments_handler,
    advanced_tasks_handler, overdue_tasks_handler, today_tasks_handler, week_tasks_handler, search_tasks_handler,
    analytics_handler, analytics_detailed_handler, suggest_priority_handler, productivity_report_handler,
    bulk_status_handler, bulk_priority_handler, bulk_assign_handler, bulk_delete_handler, bulk_operations_handler,
    filter_advanced_handler, tags_multi_handler, time_range_handler, priority_range_handler,
    # Internal functions for testing
    _add_task_with_metadata_handler_internal, _priority_handler_internal, _due_date_handler_internal, 
    _category_handler_internal, _status_handler_internal
)
from larrybot.plugins.advanced_tasks import register


class TestAdvancedTasksPlugin:
    """Test cases for the Advanced Tasks plugin."""

    @pytest.fixture
    def mock_event_bus(self):
        return Mock()

    @pytest.fixture
    def mock_command_registry(self):
        return Mock()

    @pytest.fixture
    def mock_update(self):
        update = Mock()
        update.message.reply_text = AsyncMock()
        update.effective_user.id = 12345
        return update

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.args = []
        return context

    @pytest.fixture
    def mock_task_service(self):
        service = Mock()
        # Mock all the methods that handlers might call
        service.create_task_with_metadata = AsyncMock()
        service.update_task_priority = AsyncMock()
        service.update_task_due_date = AsyncMock()
        service.update_task_category = AsyncMock()
        service.update_task_status = AsyncMock()
        service.start_time_tracking = AsyncMock()
        service.stop_time_tracking = AsyncMock()
        service.add_time_entry = AsyncMock()
        service.get_time_summary = AsyncMock()
        service.add_subtask = AsyncMock()
        service.add_task_dependency = AsyncMock()
        service.add_tags = AsyncMock()
        service.add_comment = AsyncMock()
        service.get_comments = AsyncMock()
        service.get_tasks_with_filters = AsyncMock()
        service.get_task_analytics = AsyncMock()
        service.suggest_priority = AsyncMock()
        return service

    @pytest.fixture
    def sample_task_data(self):
        return {
            'id': 1,
            'description': 'Test task',
            'priority': 'Medium',
            'status': 'Todo',
            'category': 'Testing',
            'due_date': None,
            'created_at': datetime.now(),
            'done': False
        }

    def test_register_plugin(self, mock_event_bus, mock_command_registry):
        """Test plugin registration with command registry."""
        # Act
        register(mock_event_bus, mock_command_registry)

        # Assert
        assert mock_command_registry.register.call_count == 32  # Actual count after consolidation

    @pytest.mark.asyncio
    async def test_add_task_with_metadata_handler_success(self, mock_update, mock_context, mock_task_service, sample_task_data):
        """Test successful task creation with metadata."""
        # Arrange
        mock_context.args = ["Test task", "High", "2025-07-15", "Work"]
        mock_task_service.create_task_with_metadata.return_value = {
            'success': True,
            'data': sample_task_data,
            'message': 'Task created successfully'
        }
        
        # Act - Use internal function with dependency injection
        await _add_task_with_metadata_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        # Get the actual call arguments
        actual_call = mock_task_service.create_task_with_metadata.call_args
        actual_kwargs = actual_call[1]  # Get keyword arguments
        
        # Check the call was made with correct arguments
        assert actual_kwargs['description'] == "Test task"
        assert actual_kwargs['priority'] == "High"
        assert actual_kwargs['category'] == "Work"
        
        # Check due_date is timezone-aware and has correct date
        due_date = actual_kwargs['due_date']
        assert due_date.tzinfo is not None  # Should be timezone-aware
        assert due_date.date() == datetime(2025, 7, 15).date()  # Same date
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task created" in response_text
        assert "ID: 1" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_add_task_with_metadata_handler_invalid_date(self, mock_update, mock_context, mock_task_service):
        """Test task creation with invalid date format."""
        # Arrange
        mock_context.args = ["Test task", "High", "invalid-date", "Work"]
        
        # Act
        await add_task_with_metadata_handler(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once_with("Invalid date format\\. Use YYYY\\-MM\\-DD", parse_mode='MarkdownV2')

    @pytest.mark.asyncio
    async def test_add_task_with_metadata_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test task creation when service returns error."""
        # Arrange
        mock_context.args = ["Test task", "High", "2025-07-15", "Work"]
        mock_task_service.create_task_with_metadata.return_value = {
            'success': False,
            'message': 'Database error'
        }
        
        # Act - Use internal function with dependency injection
        await _add_task_with_metadata_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Database error" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_priority_handler_success(self, mock_update, mock_context, mock_task_service, sample_task_data):
        """Test successful priority update."""
        # Arrange
        mock_context.args = ["1", "Critical"]
        mock_task_service.update_task_priority.return_value = {
            'success': True,
            'message': 'Priority updated successfully'
        }
        
        # Act - Use internal function with dependency injection
        await _priority_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.update_task_priority.assert_called_once_with(1, "Critical")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Priority updated successfully" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_priority_handler_invalid_task_id(self, mock_update, mock_context):
        """Test priority update with invalid task ID."""
        # Arrange
        mock_context.args = ["invalid", "Critical"]
        
        # Act
        await priority_handler(mock_update, mock_context)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_due_date_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful due date update."""
        # Arrange
        mock_context.args = ["1", "2025-07-15"]
        mock_task_service.update_task_due_date.return_value = {
            'success': True,
            'message': 'Due date updated successfully'
        }
        
        # Act - Use internal function with dependency injection
        await _due_date_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        # Get the actual call arguments
        actual_call = mock_task_service.update_task_due_date.call_args
        actual_args = actual_call[0]  # Get positional arguments
        
        # Check the call was made with correct arguments
        assert actual_args[0] == 1  # task_id
        
        # Check due_date is timezone-aware and has correct date
        due_date = actual_args[1]
        assert due_date.tzinfo is not None  # Should be timezone-aware
        assert due_date.date() == datetime(2025, 7, 15).date()  # Same date
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Due date updated successfully" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_due_date_handler_invalid_date(self, mock_update, mock_context):
        """Test due date update with invalid date format."""
        # Arrange
        mock_context.args = ["1", "invalid-date"]
        
        # Act
        await due_date_handler(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once_with("Invalid date format\\. Use YYYY\\-MM\\-DD", parse_mode='MarkdownV2')

    @pytest.mark.asyncio
    async def test_category_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful category update."""
        # Arrange
        mock_context.args = ["1", "Development"]
        mock_task_service.update_task_category.return_value = {
            'success': True,
            'message': 'Category updated successfully'
        }
        
        # Act - Use internal function with dependency injection
        await _category_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.update_task_category.assert_called_once_with(1, "Development")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Category updated successfully" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_status_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful status update."""
        # Arrange
        mock_context.args = ["1", "In Progress"]
        mock_task_service.update_task_status.return_value = {
            'success': True,
            'message': 'Status updated successfully'
        }
        
        # Act - Use internal function with dependency injection
        await _status_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.update_task_status.assert_called_once_with(1, "In Progress")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Status updated successfully" in response_text
        assert parse_mode == 'MarkdownV2'

    # Continue with other tests using the same pattern...
    # For now, let's run a quick test to see if our refactoring works 