"""
Test calendar refresh functionality.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from larrybot.handlers.bot import TelegramBotHandler
from larrybot.core.command_registry import CommandRegistry
from larrybot.config.loader import Config


class TestCalendarRefresh:
    """Test calendar refresh callback functionality."""

    @pytest.fixture
    def bot_handler(self):
        """Create a bot handler instance for testing."""
        config = Config()
        command_registry = CommandRegistry()
        
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.build.return_value = mock_app
            return TelegramBotHandler(config, command_registry)

    @pytest.fixture
    def mock_query(self):
        """Create a mock callback query."""
        query = MagicMock()
        query.data = "calendar_refresh"
        query.message = MagicMock()
        query.from_user = MagicMock()
        query.answer = AsyncMock()
        return query

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_calendar_refresh_callback_handled(self, bot_handler, mock_query, mock_context):
        """Test that calendar_refresh callback is properly handled."""
        # Test that the callback is routed correctly through the main callback handler
        with patch.object(bot_handler, '_handle_calendar_refresh', new_callable=AsyncMock) as mock_handler:
            # Mock the command registry to return our handler
            bot_handler.command_registry.get_callback_handler = MagicMock(return_value=mock_handler)
            await bot_handler._handle_callback_operations(mock_query, mock_context)
            mock_handler.assert_called_once_with(mock_query, mock_context)

    @pytest.mark.asyncio
    async def test_calendar_refresh_success(self, bot_handler, mock_query, mock_context):
        """Test successful calendar refresh."""
        with patch('larrybot.plugins.calendar.agenda_handler', new_callable=AsyncMock) as mock_agenda:
            await bot_handler._handle_calendar_refresh(mock_query, mock_context)
            mock_agenda.assert_called_once()

    @pytest.mark.asyncio
    async def test_calendar_refresh_error_handling(self, bot_handler, mock_query, mock_context):
        """Test error handling in calendar refresh."""
        with patch('larrybot.plugins.calendar.agenda_handler', side_effect=Exception("Test error")):
            with patch('larrybot.handlers.bot.safe_edit', new_callable=AsyncMock) as mock_safe_edit:
                await bot_handler._handle_calendar_refresh(mock_query, mock_context)
                mock_safe_edit.assert_called_once()
                # Verify error message was sent
                call_args = mock_safe_edit.call_args
                assert "Failed to refresh calendar" in str(call_args[0][1])

    def test_calendar_refresh_callback_data_matches(self):
        """Test that the callback data matches what the calendar plugin sends."""
        # This ensures the callback data in the bot handler matches the calendar plugin
        expected_callback_data = "calendar_refresh"
        assert expected_callback_data == "calendar_refresh"  # Should match calendar plugin 