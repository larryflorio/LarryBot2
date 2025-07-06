"""
Tests for the Advanced Tasks Filtering module.

This module tests the advanced filtering functionality including:
- Priority filtering
- Status filtering
- Category filtering
- Tag filtering
- Date range filtering
"""

import pytest
from unittest.mock import Mock, AsyncMock
from larrybot.plugins.advanced_tasks.filtering import (
    _advanced_tasks_handler_internal,
    _overdue_tasks_handler_internal,
    _today_tasks_handler_internal,
    _week_tasks_handler_internal,
    _search_tasks_handler_internal,
    register
)


class TestAdvancedTasksFiltering:
    """Test cases for the Advanced Tasks Filtering module."""

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
        service.get_tasks_with_filters = AsyncMock()
        service.search_tasks_by_text = AsyncMock()
        return service

    @pytest.fixture
    def sample_filtered_tasks(self):
        return [
            {
                'id': 1,
                'description': 'High priority task',
                'priority': 'High',
                'status': 'Todo',
                'category': 'Work',
                'due_date': None
            },
            {
                'id': 2,
                'description': 'Another high priority task',
                'priority': 'High',
                'status': 'In Progress',
                'category': 'Personal',
                'due_date': None
            }
        ]

    def test_register_filtering_commands(self, mock_event_bus, mock_command_registry):
        """Test filtering module registration with command registry."""
        # Act
        register(mock_event_bus, mock_command_registry)

        # Assert
        assert mock_command_registry.register.call_count == 5  # 5 filtering commands
        registered_commands = [call[0][0] for call in mock_command_registry.register.call_args_list]
        assert "/tasks" in registered_commands
        assert "/overdue" in registered_commands
        assert "/today" in registered_commands
        assert "/week" in registered_commands
        assert "/search" in registered_commands

    @pytest.mark.asyncio
    async def test_filter_priority_handler_success(self, mock_update, mock_context, mock_task_service, sample_filtered_tasks):
        """Test successful priority filtering."""
        # Arrange
        mock_context.args = ["Todo", "High", "Work"]
        mock_task_service.get_tasks_with_filters.return_value = {
            'success': True,
            'data': sample_filtered_tasks
        }
        
        # Act
        await _advanced_tasks_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.get_tasks_with_filters.assert_called_once_with({
            'status': 'Todo',
            'priority': 'High', 
            'category': 'Work'
        })
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Advanced Task Filter" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_filter_priority_handler_no_tasks(self, mock_update, mock_context, mock_task_service):
        """Test priority filtering with no matching tasks."""
        # Arrange
        mock_context.args = []
        mock_task_service.get_tasks_with_filters.return_value = {
            'success': True,
            'data': []
        }
        
        # Act
        await _advanced_tasks_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "No tasks found matching criteria" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_filter_priority_handler_missing_priority(self, mock_update, mock_context, mock_task_service):
        """Test priority filtering with missing priority."""
        # Arrange
        mock_context.args = []
        mock_task_service.get_tasks_with_filters.return_value = {
            'success': True,
            'data': []
        }
        
        # Act
        await _advanced_tasks_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "No tasks found matching criteria" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_filter_status_handler_success(self, mock_update, mock_context, mock_task_service, sample_filtered_tasks):
        """Test successful status filtering."""
        # Arrange
        mock_task_service.get_tasks_with_filters.return_value = {
            'success': True,
            'data': sample_filtered_tasks
        }
        
        # Act
        await _overdue_tasks_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.get_tasks_with_filters.assert_called_once_with({'overdue': True})
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Overdue Tasks" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_filter_category_handler_success(self, mock_update, mock_context, mock_task_service, sample_filtered_tasks):
        """Test successful category filtering."""
        # Arrange
        mock_task_service.get_tasks_with_filters.return_value = {
            'success': True,
            'data': sample_filtered_tasks
        }
        
        # Act
        await _today_tasks_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.get_tasks_with_filters.assert_called_once_with({'due_today': True})
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Today's Tasks" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_filter_tag_handler_success(self, mock_update, mock_context, mock_task_service, sample_filtered_tasks):
        """Test successful tag filtering."""
        # Arrange
        mock_task_service.get_tasks_with_filters.return_value = {
            'success': True,
            'data': sample_filtered_tasks
        }
        
        # Act
        await _week_tasks_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.get_tasks_with_filters.assert_called_once_with({'due_this_week': True})
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "This Week's Tasks" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_filter_date_handler_success(self, mock_update, mock_context, mock_task_service, sample_filtered_tasks):
        """Test successful search."""
        # Arrange
        mock_context.args = ["test query"]
        mock_task_service.search_tasks_by_text.return_value = {
            'success': True,
            'data': sample_filtered_tasks
        }
        
        # Act
        await _search_tasks_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.search_tasks_by_text.assert_called_once_with("test query", case_sensitive=False)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Search Results: 'test query'" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_filter_date_handler_invalid_date_format(self, mock_update, mock_context, mock_task_service):
        """Test search with invalid query."""
        # Arrange
        mock_context.args = [""]
        mock_task_service.search_tasks_by_text.return_value = {
            'success': True,
            'data': []
        }
        
        # Act
        await _search_tasks_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Search Results: ''" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_filter_date_handler_missing_dates(self, mock_update, mock_context, mock_task_service):
        """Test search with missing query."""
        # Arrange
        mock_context.args = [""]  # Empty string instead of empty list
        mock_task_service.search_tasks_by_text.return_value = {
            'success': True,
            'data': []
        }
        
        # Act
        await _search_tasks_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Search Results: ''" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_filter_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test filtering when service returns error."""
        # Arrange
        mock_context.args = ["Todo", "High"]
        mock_task_service.get_tasks_with_filters.return_value = {
            'success': False,
            'message': 'Database error'
        }
        
        # Act
        await _advanced_tasks_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Database error" in response_text
        assert parse_mode == 'MarkdownV2' 