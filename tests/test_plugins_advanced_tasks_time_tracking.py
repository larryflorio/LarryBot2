"""
Tests for the Advanced Tasks Time Tracking module.

This module tests the time tracking functionality including:
- Start/stop time tracking
- Manual time entry
- Time summaries
"""

import pytest
from unittest.mock import Mock, AsyncMock
from larrybot.plugins.advanced_tasks.time_tracking import (
    _start_time_tracking_handler_internal,
    _stop_time_tracking_handler_internal,
    _time_entry_handler_internal,
    _time_summary_handler_internal,
    register
)


class TestAdvancedTasksTimeTracking:
    """Test cases for the Advanced Tasks Time Tracking module."""

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
        service.start_time_tracking = AsyncMock()
        service.stop_time_tracking = AsyncMock()
        service.add_time_entry = AsyncMock()
        service.get_time_summary = AsyncMock()
        return service

    def test_register_time_tracking_commands(self, mock_event_bus, mock_command_registry):
        """Test time tracking module registration with command registry."""
        # Act
        register(mock_event_bus, mock_command_registry)

        # Assert
        assert mock_command_registry.register.call_count == 4  # 4 time tracking commands
        registered_commands = [call[0][0] for call in mock_command_registry.register.call_args_list]
        assert "/time_start" in registered_commands
        assert "/time_stop" in registered_commands
        assert "/time_entry" in registered_commands
        assert "/time_summary" in registered_commands

    @pytest.mark.asyncio
    async def test_start_time_tracking_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful start time tracking."""
        # Arrange
        mock_context.args = ["1"]
        mock_task_service.start_time_tracking.return_value = {
            'success': True,
            'message': 'Time tracking started'
        }
        
        # Act
        await _start_time_tracking_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.start_time_tracking.assert_called_once_with(1)
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Time tracking started" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_start_time_tracking_handler_invalid_task_id(self, mock_update, mock_context, mock_task_service):
        """Test start time tracking with invalid task ID."""
        # Arrange
        mock_context.args = ["invalid"]
        
        # Act
        await _start_time_tracking_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_start_time_tracking_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test start time tracking when service returns error."""
        # Arrange
        mock_context.args = ["1"]
        mock_task_service.start_time_tracking.return_value = {
            'success': False,
            'message': 'Task not found'
        }
        
        # Act
        await _start_time_tracking_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task not found" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_stop_time_tracking_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful stop time tracking."""
        # Arrange
        mock_context.args = ["1"]
        mock_task_service.stop_time_tracking.return_value = {
            'success': True,
            'message': 'Time tracking stopped',
            'duration_minutes': 90
        }
        
        # Act
        await _stop_time_tracking_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.stop_time_tracking.assert_called_once_with(1)
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Time tracking stopped" in response_text
        assert "Duration: 1h 30m" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_stop_time_tracking_handler_invalid_task_id(self, mock_update, mock_context, mock_task_service):
        """Test stop time tracking with invalid task ID."""
        # Arrange
        mock_context.args = ["invalid"]
        
        # Act
        await _stop_time_tracking_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_time_entry_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful manual time entry."""
        # Arrange
        mock_context.args = ["1", "120", "Development work"]
        mock_task_service.add_time_entry.return_value = {
            'success': True,
            'message': 'Time entry added'
        }
        
        # Act
        await _time_entry_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.add_time_entry.assert_called_once_with(1, 120, "Development work")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Time entry added" in response_text
        assert ("Duration: 2h 0m" in response_text or "Duration: 2h" in response_text)
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_time_entry_handler_invalid_duration(self, mock_update, mock_context, mock_task_service):
        """Test time entry with invalid duration."""
        # Arrange
        mock_context.args = ["1", "invalid", "Development work"]
        
        # Act
        await _time_entry_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Invalid duration" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_time_entry_handler_negative_duration(self, mock_update, mock_context, mock_task_service):
        """Test time entry with negative duration."""
        # Arrange
        mock_context.args = ["1", "-30", "Development work"]
        
        # Act
        await _time_entry_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Invalid duration" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_time_entry_handler_without_description(self, mock_update, mock_context, mock_task_service):
        """Test time entry without description."""
        # Arrange
        mock_context.args = ["1", "60"]
        mock_task_service.add_time_entry.return_value = {
            'success': True,
            'message': 'Time entry added'
        }
        
        # Act
        await _time_entry_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.add_time_entry.assert_called_once_with(1, 60, None)
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Time entry added" in response_text
        assert ("Duration: 1h 0m" in response_text or "Duration: 1h" in response_text)
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_time_summary_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful time summary."""
        # Arrange
        mock_context.args = ["1"]
        mock_task_service.get_time_summary.return_value = {
            'success': True,
            'data': {
                'total_minutes': 240,
                'entry_count': 3
            }
        }
        
        # Act
        await _time_summary_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.get_time_summary.assert_called_once_with(1)
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert ("Time Summary for Task #1" in response_text or "Time Summary for Task \\#1" in response_text)
        assert ("Total Time: 4h 0m" in response_text or "Total Time: 4h" in response_text)
        assert "Entries: 3" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_time_summary_handler_no_entries(self, mock_update, mock_context, mock_task_service):
        """Test time summary with no entries."""
        # Arrange
        mock_context.args = ["1"]
        mock_task_service.get_time_summary.return_value = {
            'success': True,
            'data': {
                'total_minutes': 0,
                'entry_count': 0
            }
        }
        
        # Act
        await _time_summary_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert ("Time Summary for Task #1" in response_text or "Time Summary for Task \\#1" in response_text)
        assert ("Total Time: 0m" in response_text)
        assert "Entries: 0" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_time_summary_handler_invalid_task_id(self, mock_update, mock_context, mock_task_service):
        """Test time summary with invalid task ID."""
        # Arrange
        mock_context.args = ["invalid"]
        
        # Act
        await _time_summary_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_time_summary_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test time summary when service returns error."""
        # Arrange
        mock_context.args = ["1"]
        mock_task_service.get_time_summary.return_value = {
            'success': False,
            'message': 'Task not found'
        }
        
        # Act
        await _time_summary_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task not found" in response_text
        assert parse_mode == 'MarkdownV2' 