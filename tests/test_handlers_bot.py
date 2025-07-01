import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from larrybot.handlers.bot import TelegramBotHandler
from larrybot.core.event_bus import EventBus
from larrybot.core.command_registry import CommandRegistry, CommandMetadata
from larrybot.config.loader import Config
import asyncio


@pytest.mark.asyncio
class TestTelegramBotHandler:
    """Test cases for TelegramBotHandler."""

    async def test_bot_handler_initialization(self, command_registry):
        """Test that TelegramBotHandler initializes correctly."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        assert handler.config.TELEGRAM_BOT_TOKEN == "test_token"

    async def test_is_authorized_with_valid_user(self, command_registry):
        """Test authorization with valid user."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        assert handler._is_authorized(mock_update)

    async def test_is_authorized_with_invalid_user(self, command_registry):
        """Test authorization with invalid user."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 999999999
        assert not handler._is_authorized(mock_update)

    async def test_is_authorized_without_user(self, command_registry):
        """Test authorization without user."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        mock_update = MagicMock()
        mock_update.effective_user = None
        assert not handler._is_authorized(mock_update)

    async def test_start_command_authorized(self, command_registry):
        """Test /start command with authorized user."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        mock_config.get_single_user_info.return_value = {
            "authorized_user_id": 123456789,
            "bot_token_configured": True,
            "rate_limit_per_minute": 60
        }
        handler = TelegramBotHandler(mock_config, command_registry)
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        await handler._start(mock_update, mock_context)
        # Check that the new welcome message was sent
        args, kwargs = mock_update.message.reply_text.call_args
        assert "Welcome to LarryBot2" in args[0]
        assert "Authorized User" in args[0]
        assert "Rate Limit" in args[0]

    async def test_start_command_unauthorized(self, command_registry):
        """Test /start command with unauthorized user."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 999999999
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        await handler._start(mock_update, mock_context)
        # Check that the new unauthorized message was sent
        args, kwargs = mock_update.message.reply_text.call_args
        assert "Unauthorized Access" in args[0]
        assert "single-user bot" in args[0]

    async def test_help_command_authorized(self, command_registry):
        """Test /help command with authorized user."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        # Register commands with correct CommandMetadata and help-compatible categories
        command_registry.register("/add", lambda u, c: "add", metadata=CommandMetadata(name="/add", description="Add task", usage="/add <desc>", category="tasks"))
        command_registry.register("/addclient", lambda u, c: "addclient", metadata=CommandMetadata(name="/addclient", description="Add client", usage="/addclient <name>", category="client"))
        command_registry.register("/habit_add", lambda u, c: "habit_add", metadata=CommandMetadata(name="/habit_add", description="Add habit", usage="/habit_add <name>", category="habit"))
        command_registry.register("/health", lambda u, c: "health", metadata=CommandMetadata(name="/health", description="Health check", usage="/health", category="system"))
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        await handler._help(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        help_text = mock_update.message.reply_text.call_args[0][0]
        # Check for static help text sections
        assert "Available Commands" in help_text
        assert "Advanced Task Features" in help_text
        assert "Client Management" in help_text
        assert "Habit Tracking" in help_text
        assert "System" in help_text
        assert "Total Commands" in help_text

    async def test_dispatch_command_authorized(self, command_registry):
        """Test command dispatch with authorized user."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        command_registry.register("/test", AsyncMock(return_value=None))
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.message.text = "/test"
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        await handler._dispatch_command(mock_update, mock_context)
        # Should not send unauthorized message
        unauthorized_calls = [call for call in mock_update.message.reply_text.call_args_list if "Unauthorized" in call[0][0]]
        assert not unauthorized_calls

    async def test_dispatch_command_unauthorized(self, command_registry):
        """Test command dispatch with unauthorized user."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 999999999
        mock_update.message.text = "/test"
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        await handler._dispatch_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_awaited_once_with("🚫 Unauthorized access.")

    async def test_dispatch_command_without_message(self, command_registry):
        """Test command dispatch without message."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.message = None
        mock_context = MagicMock()
        # Should not raise
        await handler._dispatch_command(mock_update, mock_context)

    async def test_dispatch_command_without_text(self, command_registry):
        """Test command dispatch without text."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.message.text = None
        mock_context = MagicMock()
        # Should not raise
        await handler._dispatch_command(mock_update, mock_context) 