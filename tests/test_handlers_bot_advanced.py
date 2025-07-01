"""
Bot Handler Testing Suite - Real Functionality Only

This test suite tests actual TelegramBotHandler functionality:
- Basic command dispatch and error handling
- Network error recovery (using existing _global_error_handler)
- Integration with real command registry and config

Removed tests for non-existent features like webhooks, rate limiting, and advanced auth.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from telegram import Update, User, Message, Bot
from telegram.ext import ContextTypes
from telegram.error import NetworkError, TelegramError, BadRequest, Forbidden

from larrybot.handlers.bot import TelegramBotHandler
from larrybot.config.loader import Config
from larrybot.core.command_registry import CommandRegistry


class TestBotHandlerBasicFunctionality:
    """Test basic bot handler functionality that actually exists."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.TELEGRAM_BOT_TOKEN = "test_token_12345"
        config.ALLOWED_TELEGRAM_USER_ID = 123456789
        return config

    @pytest.fixture
    def mock_command_registry(self):
        """Create a mock command registry."""
        registry = Mock(spec=CommandRegistry)
        registry._commands = {"/start": Mock(), "/help": Mock(), "/test": Mock()}
        return registry

    @pytest.fixture
    def bot_handler(self, mock_config, mock_command_registry):
        """Create a bot handler for testing."""
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.request.return_value.build.return_value = mock_app
            handler = TelegramBotHandler(mock_config, mock_command_registry)
            handler.application = mock_app
            return handler

    @pytest.fixture
    def mock_update(self):
        """Create a mock update."""
        update = Mock(spec=Update)
        update.effective_user = Mock()
        update.effective_user.id = 123456789
        update.message = Mock()
        update.message.text = "/test"
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    def test_bot_handler_initialization(self, mock_config, mock_command_registry):
        """Test that bot handler initializes correctly with real config and registry."""
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.request.return_value.build.return_value = mock_app
            
            handler = TelegramBotHandler(mock_config, mock_command_registry)
            
            assert handler.config == mock_config
            assert handler.command_registry == mock_command_registry
            assert handler.application == mock_app

    def test_is_authorized_valid_user(self, bot_handler, mock_update):
        """Test authorization for valid user."""
        mock_update.effective_user.id = 123456789
        
        result = bot_handler._is_authorized(mock_update)
        
        assert result is True

    def test_is_authorized_invalid_user(self, bot_handler, mock_update):
        """Test authorization for invalid user."""
        mock_update.effective_user.id = 999999999  # Different user
        
        result = bot_handler._is_authorized(mock_update)
        
        assert result is False

    def test_is_authorized_no_user(self, bot_handler):
        """Test authorization when no user in update."""
        update = Mock()
        update.effective_user = None
        
        result = bot_handler._is_authorized(update)
        
        assert result is False

    def test_is_authorized_config_failure(self, bot_handler, mock_update):
        """Test authorization handles config failures gracefully."""
        bot_handler.config = None  # Simulate config failure
        
        result = bot_handler._is_authorized(mock_update)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_dispatch_command_authorized_user(self, bot_handler, mock_update, mock_context):
        """Test command dispatch for authorized user."""
        mock_update.message.text = "/test"
        mock_command = AsyncMock()
        bot_handler.command_registry.dispatch = Mock(return_value=mock_command)
        
        await bot_handler._dispatch_command(mock_update, mock_context)
        
        # Verify dispatch was called with correct command
        bot_handler.command_registry.dispatch.assert_called_once_with("/test", mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_dispatch_command_unauthorized_user(self, bot_handler, mock_update, mock_context):
        """Test command dispatch blocks unauthorized user."""
        mock_update.effective_user.id = 999999999  # Unauthorized user
        
        await bot_handler._dispatch_command(mock_update, mock_context)
        
        # Should send unauthorized message
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "unauthorized" in call_args.lower() or "not authorized" in call_args.lower()

    @pytest.mark.asyncio
    async def test_dispatch_command_exception_handling(self, bot_handler, mock_update, mock_context):
        """Test command dispatch handles exceptions properly."""
        mock_update.message.text = "/test"
        bot_handler.command_registry.dispatch = Mock(side_effect=Exception("Command failed"))
        
        await bot_handler._dispatch_command(mock_update, mock_context)
        
        # Should send error message
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "error" in call_args.lower()

    @pytest.mark.asyncio 
    async def test_dispatch_command_async_result(self, bot_handler, mock_update, mock_context):
        """Test command dispatch handles async command results."""
        mock_update.message.text = "/test"
        
        async def async_command():
            return "async_result"
        
        bot_handler.command_registry.dispatch = Mock(return_value=async_command())
        
        # Should not raise exception for async result
        await bot_handler._dispatch_command(mock_update, mock_context)


class TestBotHandlerErrorRecovery:
    """Test error recovery using actual _global_error_handler method."""

    @pytest.fixture
    def recovery_bot_handler(self, mock_config, mock_command_registry):
        """Create a bot handler for error recovery testing."""
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.request.return_value.build.return_value = mock_app
            handler = TelegramBotHandler(mock_config, mock_command_registry)
            handler.application = mock_app
            return handler

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.TELEGRAM_BOT_TOKEN = "test_token_12345"
        config.ALLOWED_TELEGRAM_USER_ID = 123456789
        return config

    @pytest.fixture
    def mock_command_registry(self):
        """Create a mock command registry."""
        registry = Mock(spec=CommandRegistry)
        registry._commands = {"/test": Mock()}
        return registry

    @pytest.mark.asyncio
    async def test_global_error_handler_with_update_message(self, recovery_bot_handler, mock_update, mock_context):
        """Test global error handler with update containing message."""
        mock_context.error = TelegramError("Test error")
        
        # Should not raise exception
        await recovery_bot_handler._global_error_handler(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_global_error_handler_without_message(self, recovery_bot_handler, mock_context):
        """Test global error handler without message in update."""
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 123456789
        update.message = None  # No message
        
        mock_context.error = TelegramError("Test error")
        
        # Should not raise exception
        await recovery_bot_handler._global_error_handler(update, mock_context)

    @pytest.mark.asyncio
    async def test_global_error_handler_reply_fails(self, recovery_bot_handler, mock_update, mock_context):
        """Test global error handler when reply fails."""
        mock_context.error = TelegramError("Test error")
        mock_update.message.reply_text = AsyncMock(side_effect=TelegramError("Reply failed"))
        
        # Should not raise exception even if reply fails
        await recovery_bot_handler._global_error_handler(mock_update, mock_context)

    @pytest.fixture
    def mock_update(self):
        """Create a mock update for error recovery tests."""
        update = Mock(spec=Update)
        update.effective_user = Mock()
        update.effective_user.id = 123456789
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        return update


class TestBotHandlerIntegration:
    """Test integration with real components."""

    def test_integration_with_real_command_registry(self):
        """Test bot handler works with real command registry."""
        config = Mock(spec=Config)
        config.TELEGRAM_BOT_TOKEN = "test_token_12345"
        config.ALLOWED_TELEGRAM_USER_ID = 123456789
        
        # Use real command registry
        real_registry = CommandRegistry()
        
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.request.return_value.build.return_value = mock_app
            
            handler = TelegramBotHandler(config, real_registry)
            
            # Should initialize without errors
            assert handler.command_registry == real_registry
            assert len(real_registry._commands) >= 2  # At least /start and /help

    def test_core_command_registration(self):
        """Test that core commands are properly registered."""
        config = Mock(spec=Config)
        config.TELEGRAM_BOT_TOKEN = "test_token_12345"
        config.ALLOWED_TELEGRAM_USER_ID = 123456789
        
        registry = CommandRegistry()
        
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.request.return_value.build.return_value = mock_app
            
            TelegramBotHandler(config, registry)
            
            # Should register core commands
            assert "/help" in registry._commands
            assert "/start" in registry._commands

    @pytest.mark.asyncio
    async def test_help_command_execution(self):
        """Test that help command executes correctly."""
        config = Mock(spec=Config)
        config.TELEGRAM_BOT_TOKEN = "test_token_12345"
        config.ALLOWED_TELEGRAM_USER_ID = 123456789
        
        registry = CommandRegistry()
        
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.request.return_value.build.return_value = mock_app
            
            handler = TelegramBotHandler(config, registry)
            
            # Create mock update and context
            update = Mock()
            update.effective_user = Mock()
            update.effective_user.id = 123456789
            update.message = Mock()
            update.message.reply_text = AsyncMock()
            
            context = Mock()
            
            # Execute help command
            await handler._help(update, context)
            
            # Should send help message
            update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_command_execution(self):
        """Test that start command executes correctly."""
        config = Mock(spec=Config)
        config.TELEGRAM_BOT_TOKEN = "test_token_12345"
        config.ALLOWED_TELEGRAM_USER_ID = 123456789
        config.get_single_user_info = Mock(return_value={
            'authorized_user_id': 123456789,
            'bot_token_configured': True,
            'rate_limit_per_minute': 60
        })
        
        registry = CommandRegistry()
        
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.request.return_value.build.return_value = mock_app
            
            handler = TelegramBotHandler(config, registry)
            
            # Create mock update and context
            update = Mock()
            update.effective_user = Mock()
            update.effective_user.id = 123456789
            update.message = Mock()
            update.message.reply_text = AsyncMock()
            
            context = Mock()
            
            # Execute start command
            await handler._start(update, context)
            
            # Should send welcome message
            update.message.reply_text.assert_called_once()
            call_args = update.message.reply_text.call_args[0][0]
            assert "Welcome to LarryBot2" in call_args 