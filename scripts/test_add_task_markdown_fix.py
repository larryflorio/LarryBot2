#!/usr/bin/env python3
"""
Test to verify that the add task button message is properly escaped for MarkdownV2.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from larrybot.handlers.bot import TelegramBotHandler
from larrybot.config.loader import Config
from larrybot.core.command_registry import CommandRegistry
from larrybot.utils.ux_helpers import MessageFormatter


class TestAddTaskMarkdownFix:
    """Test that add task button message is properly escaped."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = MagicMock(spec=Config)
        config.TELEGRAM_BOT_TOKEN = "test_token"
        config.ALLOWED_TELEGRAM_USER_ID = 12345
        return config
    
    @pytest.fixture
    def mock_command_registry(self):
        """Create a mock command registry."""
        registry = MagicMock(spec=CommandRegistry)
        registry._commands = []  # Mock the _commands attribute
        return registry
    
    @pytest.fixture
    def bot_handler(self, mock_config, mock_command_registry):
        """Create a bot handler instance."""
        return TelegramBotHandler(mock_config, mock_command_registry)
    
    @pytest.fixture
    def mock_query(self):
        """Create a mock callback query."""
        query = AsyncMock()
        query.data = "add_task"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        return query
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        context = MagicMock()
        context.user_data = {}
        return context
    
    def test_add_task_message_escaping(self, bot_handler, mock_query, mock_context):
        """Test that the add task message is properly escaped for MarkdownV2."""
        # Call the method
        import asyncio
        asyncio.run(bot_handler._handle_add_task(mock_query, mock_context))
        
        # Verify that edit_message_text was called
        mock_query.edit_message_text.assert_called_once()
        
        # Get the message that was sent
        call_args = mock_query.edit_message_text.call_args
        message = call_args[0][0]  # First positional argument
        parse_mode = call_args[1].get('parse_mode')  # Keyword argument
        
        # Verify parse_mode is MarkdownV2
        assert parse_mode == 'MarkdownV2'
        
        # Verify that special characters are properly escaped
        # The message should contain escaped dots, dashes, etc.
        # Check for escaped special characters in the actual message
        assert '\\*\\*' in message  # Bold markers should be escaped
        assert '\\`' in message  # Code markers should be escaped
        assert '\\!' in message  # Exclamation marks should be escaped
        
        # Verify that the message contains the expected content (escaped)
        assert '📝 \\*\\*Add New Task\\*\\*' in message
        assert '\\*\\*How to add a task:\\*\\*' in message
        assert '\\*\\*Examples:\\*\\*' in message
        assert '\\*\\*Tip:\\*\\*' in message
        
        # Verify that the message doesn't contain unescaped special characters
        assert '**' not in message  # Should be escaped as \*\*
        assert '..' not in message  # Should be escaped as \.\.
        
        print("✅ Add task message is properly escaped for MarkdownV2")


if __name__ == "__main__":
    # Run the test
    test_instance = TestAddTaskMarkdownFix()
    test_instance.test_add_task_message_escaping(
        test_instance.bot_handler(None, None),
        test_instance.mock_query(),
        test_instance.mock_context()
    ) 