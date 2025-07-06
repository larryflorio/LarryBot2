"""
Tests for the Advanced Tasks Core module.

This module tests the core task management functionality including:
- Task creation with metadata
- Priority and status management
- Due date and category management
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from larrybot.plugins.advanced_tasks.core import (
    _add_task_with_metadata_handler_internal,
    _priority_handler_internal,
    _due_date_handler_internal,
    _category_handler_internal,
    _status_handler_internal,
    register
)


class TestAdvancedTasksCore:
    """Test cases for the Advanced Tasks Core module."""

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
        service.create_task_with_metadata = AsyncMock()
        service.update_task_priority = AsyncMock()
        service.update_task_due_date = AsyncMock()
        service.update_task_category = AsyncMock()
        service.update_task_status = AsyncMock()
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

    def test_register_core_commands(self, mock_event_bus, mock_command_registry):
        """Test core module registration with command registry."""
        # Act
        register(mock_event_bus, mock_command_registry)

        # Assert
        assert mock_command_registry.register.call_count == 5  # 5 core commands
        registered_commands = [call[0][0] for call in mock_command_registry.register.call_args_list]
        assert "/addtask" in registered_commands
        assert "/priority" in registered_commands
        assert "/due" in registered_commands
        assert "/category" in registered_commands
        assert "/status" in registered_commands

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
        
        # Act
        await _add_task_with_metadata_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        actual_call = mock_task_service.create_task_with_metadata.call_args
        actual_kwargs = actual_call[1]
        
        assert actual_kwargs['description'] == "Test task"
        assert actual_kwargs['priority'] == "High"
        assert actual_kwargs['category'] == "Work"
        
        due_date = actual_kwargs['due_date']
        assert due_date.tzinfo is not None
        assert due_date.date() == datetime(2025, 7, 15).date()
        
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
        await _add_task_with_metadata_handler_internal(mock_update, mock_context, mock_task_service)
        
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
        
        # Act
        await _add_task_with_metadata_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Database error" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_priority_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful priority update."""
        # Arrange
        mock_context.args = ["1", "Critical"]
        mock_task_service.update_task_priority.return_value = {
            'success': True,
            'message': 'Priority updated successfully'
        }
        
        # Act
        await _priority_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.update_task_priority.assert_called_once_with(1, "Critical")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Priority updated successfully" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_priority_handler_invalid_task_id(self, mock_update, mock_context, mock_task_service):
        """Test priority update with invalid task ID."""
        # Arrange
        mock_context.args = ["invalid", "Critical"]
        
        # Act
        await _priority_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_priority_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test priority update when service returns error."""
        # Arrange
        mock_context.args = ["1", "Critical"]
        mock_task_service.update_task_priority.return_value = {
            'success': False,
            'message': 'Task not found'
        }
        
        # Act
        await _priority_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task not found" in response_text
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
        
        # Act
        await _due_date_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        actual_call = mock_task_service.update_task_due_date.call_args
        actual_args = actual_call[0]
        
        assert actual_args[0] == 1
        due_date = actual_args[1]
        assert due_date.tzinfo is not None
        assert due_date.date() == datetime(2025, 7, 15).date()
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Due date updated successfully" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_due_date_handler_invalid_date(self, mock_update, mock_context, mock_task_service):
        """Test due date update with invalid date format."""
        # Arrange
        mock_context.args = ["1", "invalid-date"]
        
        # Act
        await _due_date_handler_internal(mock_update, mock_context, mock_task_service)
        
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
        
        # Act
        await _category_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.update_task_category.assert_called_once_with(1, "Development")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Category updated successfully" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_category_handler_invalid_task_id(self, mock_update, mock_context, mock_task_service):
        """Test category update with invalid task ID."""
        # Arrange
        mock_context.args = ["invalid", "Development"]
        
        # Act
        await _category_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
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
        
        # Act
        await _status_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.update_task_status.assert_called_once_with(1, "In Progress")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Status updated successfully" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_status_handler_invalid_task_id(self, mock_update, mock_context, mock_task_service):
        """Test status update with invalid task ID."""
        # Arrange
        mock_context.args = ["invalid", "In Progress"]
        
        # Act
        await _status_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_status_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test status update when service returns error."""
        # Arrange
        mock_context.args = ["1", "Invalid Status"]
        mock_task_service.update_task_status.return_value = {
            'success': False,
            'message': 'Invalid status value'
        }
        
        # Act
        await _status_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Invalid status value" in response_text
        assert parse_mode == 'MarkdownV2' 