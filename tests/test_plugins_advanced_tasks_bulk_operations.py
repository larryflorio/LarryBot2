"""
Tests for the Advanced Tasks Bulk Operations module.

This module tests the bulk operations functionality including:
- Bulk task updates
- Bulk task deletion
- Bulk task completion
"""

import pytest
from unittest.mock import Mock, AsyncMock
from larrybot.plugins.advanced_tasks.bulk_operations import (
    _bulk_status_handler_internal,
    _bulk_priority_handler_internal,
    _bulk_assign_handler_internal,
    _bulk_delete_handler_internal,
    _bulk_operations_handler_internal,
    register
)


class TestAdvancedTasksBulkOperations:
    """Test cases for the Advanced Tasks Bulk Operations module."""

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
        service.bulk_update_status = AsyncMock()
        service.bulk_update_priority = AsyncMock()
        service.bulk_assign_tasks = AsyncMock()
        service.bulk_delete_tasks = AsyncMock()
        service.bulk_operations = AsyncMock()
        return service

    def test_register_bulk_operations_commands(self, mock_event_bus, mock_command_registry):
        """Test bulk operations module registration with command registry."""
        # Act
        register(mock_event_bus, mock_command_registry)

        # Assert
        assert mock_command_registry.register.call_count == 5  # 5 bulk operations commands
        registered_commands = [call[0][0] for call in mock_command_registry.register.call_args_list]
        assert "/bulk_status" in registered_commands
        assert "/bulk_priority" in registered_commands
        assert "/bulk_assign" in registered_commands
        assert "/bulk_delete" in registered_commands
        assert "/bulk_operations" in registered_commands

    @pytest.mark.asyncio
    async def test_bulk_status_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful bulk status update."""
        # Arrange
        mock_context.args = ["1,2,3", "In Progress"]
        mock_task_service.bulk_update_status.return_value = {
            'success': True,
            'updated_count': 3,
            'message': 'Successfully updated status for 3 tasks'
        }
        
        # Act
        await _bulk_status_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.bulk_update_status.assert_called_once_with((True, [1, 2, 3], ""), "In Progress")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Successfully updated status for 3 tasks" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_bulk_priority_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful bulk priority update."""
        # Arrange
        mock_context.args = ["1,2,3", "High"]
        mock_task_service.bulk_update_priority.return_value = {
            'success': True,
            'updated_count': 3,
            'message': 'Successfully updated priority for 3 tasks'
        }
        
        # Act
        await _bulk_priority_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.bulk_update_priority.assert_called_once_with((True, [1, 2, 3], ""), "High")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Successfully updated priority for 3 tasks" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_bulk_status_handler_invalid_task_ids(self, mock_update, mock_context, mock_task_service):
        """Test bulk status update with invalid task IDs."""
        # Arrange
        mock_context.args = ["invalid,2,3", "In Progress"]
        mock_task_service.bulk_update_status.return_value = {
            'success': False,
            'message': 'Invalid task ID format'
        }
        
        # Act
        await _bulk_status_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Invalid task ID format" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_bulk_status_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test bulk status update when service returns error."""
        # Arrange
        mock_context.args = ["1,2,3", "Invalid Status"]
        mock_task_service.bulk_update_status.return_value = {
            'success': False,
            'message': 'Some tasks not found'
        }
        
        # Act
        await _bulk_status_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Some tasks not found" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_bulk_delete_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful bulk task deletion."""
        # Arrange
        mock_context.args = ["1,2,3", "confirm"]
        mock_task_service.bulk_delete_tasks.return_value = {
            'success': True,
            'deleted_count': 3,
            'message': 'Successfully deleted 3 tasks'
        }
        
        # Act
        await _bulk_delete_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.bulk_delete_tasks.assert_called_once_with((True, [1, 2, 3], ""))
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Successfully deleted 3 tasks" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_bulk_delete_handler_invalid_task_ids(self, mock_update, mock_context, mock_task_service):
        """Test bulk delete with invalid task IDs."""
        # Arrange
        mock_context.args = ["invalid,2,3"]
        
        # Act
        await _bulk_delete_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Invalid task ID" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_bulk_delete_handler_missing_task_ids(self, mock_update, mock_context, mock_task_service):
        """Test bulk delete with missing task IDs."""
        # Arrange
        mock_context.args = []
        
        # Act & Assert
        with pytest.raises(IndexError):
            await _bulk_delete_handler_internal(mock_update, mock_context, mock_task_service)

    @pytest.mark.asyncio
    async def test_bulk_delete_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test bulk delete when service returns error."""
        # Arrange
        mock_context.args = ["1,2,3", "confirm"]
        mock_task_service.bulk_delete_tasks.return_value = {
            'success': False,
            'message': 'Some tasks cannot be deleted'
        }
        
        # Act
        await _bulk_delete_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Some tasks cannot be deleted" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_bulk_assign_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful bulk task assignment."""
        # Arrange
        mock_context.args = ["1,2,3", "john_doe"]
        mock_task_service.bulk_assign_tasks.return_value = {
            'success': True,
            'updated_count': 3,
            'message': 'Successfully assigned 3 tasks to john_doe'
        }
        
        # Act
        await _bulk_assign_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.bulk_assign_tasks.assert_called_once_with((True, [1, 2, 3], ""), "john_doe")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Successfully assigned 3 tasks to john\\_doe" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_bulk_delete_handler_confirmation_required(self, mock_update, mock_context, mock_task_service):
        """Test bulk delete without confirmation."""
        # Arrange
        mock_context.args = ["1,2,3"]
        
        # Act
        await _bulk_delete_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Bulk Delete Confirmation Required" in response_text
        assert "Add 'confirm' to proceed with deletion" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_bulk_operations_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test bulk operations menu."""
        # Arrange
        mock_context.args = []
        
        # Act
        await _bulk_operations_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Bulk Operations Menu" in response_text
        assert parse_mode == 'MarkdownV2' 