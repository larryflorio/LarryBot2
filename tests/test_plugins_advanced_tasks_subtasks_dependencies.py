"""
Tests for the Advanced Tasks Subtasks and Dependencies module.

This module tests the subtask and dependency management functionality including:
- Subtask creation
- Task dependency management
"""

import pytest
from unittest.mock import Mock, AsyncMock
from larrybot.plugins.advanced_tasks.subtasks_dependencies import (
    _subtask_handler_internal,
    _dependency_handler_internal,
    register
)


class TestAdvancedTasksSubtasksDependencies:
    """Test cases for the Advanced Tasks Subtasks and Dependencies module."""

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
        service.add_subtask = AsyncMock()
        service.add_task_dependency = AsyncMock()
        return service

    @pytest.fixture
    def sample_subtask_data(self):
        return {
            'id': 2,
            'description': 'Subtask description',
            'parent_id': 1,
            'priority': 'Medium',
            'status': 'Todo'
        }

    def test_register_subtasks_dependencies_commands(self, mock_event_bus, mock_command_registry):
        """Test subtasks and dependencies module registration with command registry."""
        # Act
        register(mock_event_bus, mock_command_registry)

        # Assert
        assert mock_command_registry.register.call_count == 2  # 2 subtasks/dependencies commands
        registered_commands = [call[0][0] for call in mock_command_registry.register.call_args_list]
        assert "/subtask" in registered_commands
        assert "/depend" in registered_commands

    @pytest.mark.asyncio
    async def test_subtask_handler_success(self, mock_update, mock_context, mock_task_service, sample_subtask_data):
        """Test successful subtask creation."""
        # Arrange
        mock_context.args = ["1", "Subtask description"]
        mock_task_service.add_subtask.return_value = {
            'success': True,
            'data': sample_subtask_data,
            'message': 'Subtask created successfully'
        }
        
        # Act
        await _subtask_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.add_subtask.assert_called_once_with(1, "Subtask description")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Subtask created successfully" in response_text
        assert "Parent Task: 1" in response_text
        assert "Subtask ID: 2" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_subtask_handler_invalid_parent_id(self, mock_update, mock_context, mock_task_service):
        """Test subtask creation with invalid parent task ID."""
        # Arrange
        mock_context.args = ["invalid", "Subtask description"]
        
        # Act
        await _subtask_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_subtask_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test subtask creation when service returns error."""
        # Arrange
        mock_context.args = ["1", "Subtask description"]
        mock_task_service.add_subtask.return_value = {
            'success': False,
            'message': 'Parent task not found'
        }
        
        # Act
        await _subtask_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Parent task not found" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_dependency_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful dependency creation."""
        # Arrange
        mock_context.args = ["1", "2"]
        mock_task_service.add_task_dependency.return_value = {
            'success': True,
            'message': 'Dependency added successfully'
        }
        
        # Act
        await _dependency_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.add_task_dependency.assert_called_once_with(1, 2)
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Dependency added successfully" in response_text
        assert "Task ID: 1" in response_text
        assert "Dependency ID: 2" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_dependency_handler_invalid_task_id(self, mock_update, mock_context, mock_task_service):
        """Test dependency creation with invalid task ID."""
        # Arrange
        mock_context.args = ["invalid", "2"]
        
        # Act
        await _dependency_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_dependency_handler_invalid_dependency_id(self, mock_update, mock_context, mock_task_service):
        """Test dependency creation with invalid dependency ID."""
        # Arrange
        mock_context.args = ["1", "invalid"]
        
        # Act
        await _dependency_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_dependency_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test dependency creation when service returns error."""
        # Arrange
        mock_context.args = ["1", "2"]
        mock_task_service.add_task_dependency.return_value = {
            'success': False,
            'message': 'Circular dependency detected'
        }
        
        # Act
        await _dependency_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Circular dependency detected" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_dependency_handler_same_task_id(self, mock_update, mock_context, mock_task_service):
        """Test dependency creation with same task ID."""
        # Arrange
        mock_context.args = ["1", "1"]
        mock_task_service.add_task_dependency.return_value = {
            'success': False,
            'message': 'Task cannot depend on itself'
        }
        
        # Act
        await _dependency_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task cannot depend on itself" in response_text
        assert parse_mode == 'MarkdownV2' 