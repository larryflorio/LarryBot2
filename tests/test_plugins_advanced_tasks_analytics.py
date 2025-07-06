"""
Tests for the Advanced Tasks Analytics module.

This module tests the analytics functionality including:
- Task statistics
- Performance metrics
- Productivity insights
"""

import pytest
from unittest.mock import Mock, AsyncMock
from larrybot.plugins.advanced_tasks.analytics import (
    _analytics_handler_internal,
    _analytics_detailed_handler_internal,
    _suggest_priority_handler_internal,
    _productivity_report_handler_internal,
    register
)


class TestAdvancedTasksAnalytics:
    """Test cases for the Advanced Tasks Analytics module."""

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
        service.get_task_analytics = AsyncMock()
        service.suggest_priority = AsyncMock()
        service.get_productivity_report = AsyncMock()
        return service

    @pytest.fixture
    def sample_analytics_data(self):
        return {
            'total_tasks': 25,
            'completed_tasks': 18,
            'pending_tasks': 7,
            'completion_rate': 72.0,
            'avg_completion_time_hours': 4.5,
            'priority_distribution': {
                'High': 8,
                'Medium': 12,
                'Low': 5
            }
        }



    def test_register_analytics_commands(self, mock_event_bus, mock_command_registry):
        """Test analytics module registration with command registry."""
        # Act
        register(mock_event_bus, mock_command_registry)

        # Assert
        assert mock_command_registry.register.call_count == 4  # 4 analytics commands
        registered_commands = [call[0][0] for call in mock_command_registry.register.call_args_list]
        assert "/analytics" in registered_commands
        assert "/analytics_detailed" in registered_commands
        assert "/suggest" in registered_commands
        assert "/productivity_report" in registered_commands

    @pytest.mark.asyncio
    async def test_analytics_handler_success(self, mock_update, mock_context, mock_task_service, sample_analytics_data):
        """Test successful analytics generation."""
        # Arrange
        mock_context.args = ["week"]
        mock_task_service.get_task_analytics.return_value = {
            'success': True,
            'data': sample_analytics_data
        }
        
        # Act
        await _analytics_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.get_task_analytics.assert_called_once_with("week", 30)
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "📊 Analytics \\(Week\\)" in response_text
        assert "total\\_tasks: 25" in response_text
        assert "completed\\_tasks: 18" in response_text
        assert "completion\\_rate: 72\\.0" in response_text
        assert "avg\\_completion\\_time\\_hours: 4\\.5" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_analytics_handler_default_period(self, mock_update, mock_context, mock_task_service, sample_analytics_data):
        """Test analytics with default period."""
        # Arrange
        mock_context.args = []
        mock_task_service.get_task_analytics.return_value = {
            'success': True,
            'data': sample_analytics_data
        }
        
        # Act
        await _analytics_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.get_task_analytics.assert_called_once_with("basic", 30)
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "📊 Analytics \\(Basic\\)" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_analytics_handler_invalid_period(self, mock_update, mock_context, mock_task_service):
        """Test analytics with invalid period."""
        # Arrange
        mock_context.args = ["invalid"]
        mock_task_service.get_task_analytics.return_value = {
            'success': False,
            'message': 'Invalid period specified'
        }
        
        # Act
        await _analytics_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Invalid period specified" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_analytics_detailed_handler_success(self, mock_update, mock_context, mock_task_service, sample_analytics_data):
        """Test successful detailed analytics."""
        # Arrange
        mock_context.args = ["60"]
        mock_task_service.get_task_analytics.return_value = {
            'success': True,
            'data': sample_analytics_data
        }
        
        # Act
        await _analytics_detailed_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.get_task_analytics.assert_called_once_with("detailed", 60)
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "📊 Detailed Analytics \\(60 days\\)" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_suggest_priority_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful priority suggestion."""
        # Arrange
        mock_context.args = ["Complete the quarterly report"]
        mock_task_service.suggest_priority.return_value = {
            'success': True,
            'data': {
                'priority': 'High',
                'confidence': 85,
                'reasoning': 'Contains time-sensitive business data'
            }
        }
        
        # Act
        await _suggest_priority_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.suggest_priority.assert_called_once_with("Complete the quarterly report")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "🎯 Priority Suggestion" in response_text
        assert "Suggested Priority: High" in response_text
        assert "Confidence: 85%" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_productivity_report_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful productivity report."""
        # Arrange
        mock_context.args = ["2025-07-01", "2025-07-31"]
        mock_task_service.get_productivity_report.return_value = {
            'success': True,
            'data': {
                'total_tasks': 25,
                'completed_tasks': 18,
                'completion_rate': 72.0,
                'avg_completion_time': 4.5
            }
        }
        
        # Act
        await _productivity_report_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.get_productivity_report.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "📈 Productivity Report" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_analytics_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test analytics when service returns error."""
        # Arrange
        mock_context.args = ["week"]
        mock_task_service.get_task_analytics.return_value = {
            'success': False,
            'message': 'Database connection error'
        }
        
        # Act
        await _analytics_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Database connection error" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_suggest_priority_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test priority suggestion when service returns error."""
        # Arrange
        mock_context.args = ["Complete the quarterly report"]
        mock_task_service.suggest_priority.return_value = {
            'success': False,
            'message': 'Unable to generate suggestion'
        }
        
        # Act
        await _suggest_priority_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Unable to generate suggestion" in response_text
        assert parse_mode == 'MarkdownV2' 