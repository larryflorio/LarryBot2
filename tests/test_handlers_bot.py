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
        mock_update.effective_user.first_name = "John"
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        await handler._start(mock_update, mock_context)
        # Check that the new welcome message was sent with buttons
        args, kwargs = mock_update.message.reply_text.call_args
        assert "Welcome back, John!" in args[0]
        assert "Ready to boost your productivity" in args[0]
        assert "reply_markup" in kwargs
        assert kwargs["reply_markup"] is not None

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

    # Enhanced tests for better coverage

    async def test_callback_query_unauthorized(self, command_registry):
        """Test callback query with unauthorized user."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 999999999
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        
        await handler._handle_callback_query(mock_update, MagicMock())
        
        # Should answer callback and send unauthorized message
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once()

    async def test_callback_query_timeout(self, command_registry):
        """Test callback query timeout handling."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_update.callback_query.data = "test_action"
        
        await handler._handle_callback_query(mock_update, MagicMock())
        
        # Should handle timeout gracefully
        mock_update.callback_query.answer.assert_called_once()

    async def test_callback_query_operations_timeout(self, command_registry):
        """Test callback operations timeout."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.callback_query.data = "task_done:123"
        
        # Mock the callback operations to timeout
        with patch.object(handler, '_handle_callback_operations', side_effect=asyncio.TimeoutError()):
            await handler._handle_callback_query(mock_update, MagicMock())
        
        # Should send timeout message
        mock_update.callback_query.edit_message_text.assert_called()

    async def test_callback_query_operations_exception(self, command_registry):
        """Test callback operations exception handling."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.callback_query.data = "task_done:123"
        
        # Mock the callback operations to raise exception
        with patch.object(handler, '_handle_callback_operations', side_effect=Exception("Test error")):
            await handler._handle_callback_query(mock_update, MagicMock())
        
        # Should send error message
        mock_update.callback_query.edit_message_text.assert_called()

    async def test_handle_text_message_authorized(self, command_registry):
        """Test text message handling with authorized user."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.message = MagicMock()
        mock_update.message.text = "Hello bot"
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = MagicMock()
        mock_context.user_data = {}
        
        # Mock the narrative processor
        with patch.object(handler.enhanced_narrative_processor, 'process_input') as mock_process:
            mock_process.return_value = MagicMock(
                intent=MagicMock(value='GREETING'),
                entities={},
                context=MagicMock(sentiment='positive'),
                confidence=0.8,
                response_message="Hello! How can I help you?",
                suggested_command=None
            )
            
            await handler._handle_text_message(mock_update, mock_context)
            
            # Should process the message and send response
            mock_process.assert_called_once_with("Hello bot", 123456789)
            mock_update.message.reply_text.assert_called_once()

    async def test_handle_text_message_task_edit_mode(self, command_registry):
        """Test text message handling in task edit mode."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.message = MagicMock()
        mock_update.message.text = "Updated task description"
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = MagicMock()
        mock_context.user_data = {'editing_task_id': 123}
        
        with patch.object(handler, '_handle_task_edit_mode') as mock_edit:
            await handler._handle_text_message(mock_update, mock_context)
            
            # Should call task edit handler
            mock_edit.assert_called_once_with(mock_update, mock_context, "Updated task description")

    async def test_handle_text_message_task_creation_state(self, command_registry):
        """Test text message handling in task creation state."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.message = MagicMock()
        mock_update.message.text = "Create a new task"
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = MagicMock()
        mock_context.user_data = {'task_creation_state': 'description'}
        
        with patch('larrybot.plugins.tasks.handle_narrative_task_creation') as mock_create:
            await handler._handle_text_message(mock_update, mock_context)
            
            # Should call narrative task creation
            mock_create.assert_called_once_with(mock_update, mock_context, "Create a new task")

    async def test_handle_text_message_low_confidence(self, command_registry):
        """Test text message handling with low confidence."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.message = MagicMock()
        mock_update.message.text = "Unclear message"
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = MagicMock()
        mock_context.user_data = {}
        
        # Mock the narrative processor to return low confidence
        with patch.object(handler.enhanced_narrative_processor, 'process_input') as mock_process:
            mock_process.return_value = MagicMock(
                intent=MagicMock(value='UNKNOWN'),
                entities={},
                context=MagicMock(sentiment='neutral'),
                confidence=0.3,
                response_message="I'm not sure what you mean",
                suggested_command=None
            )
            
            with patch.object(handler, '_handle_low_confidence_input') as mock_low:
                await handler._handle_text_message(mock_update, mock_context)
                
                # Should call low confidence handler
                mock_low.assert_called_once()

    async def test_global_error_handler(self, command_registry):
        """Test global error handler."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        mock_update.effective_message = MagicMock()
        mock_update.effective_message.reply_text = AsyncMock()
        
        mock_context = MagicMock()
        mock_context.error = Exception("Test error")
        
        # Mock the enhanced message processor to avoid complex dependencies
        with patch.object(handler, 'enhanced_message_processor') as mock_processor:
            mock_processor.create_error_response.return_value = ("Error message", None)
            
            await handler._global_error_handler(mock_update, mock_context)
            
            # Should send error message
            mock_update.effective_message.reply_text.assert_called_once()

    async def test_register_core_commands(self, command_registry):
        """Test core command registration."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        # Check that core commands are registered
        assert '/help' in command_registry._commands
        assert '/start' in command_registry._commands
        assert '/daily' in command_registry._commands

    async def test_register_core_handlers(self, command_registry):
        """Test core handler registration."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        # Mock the application to check handlers are added
        with patch.object(handler.application, 'add_handler') as mock_add:
            handler._register_core_handlers()
            
            # Should add multiple handlers
            assert mock_add.call_count >= 4  # start, help, callback, message handlers

    async def test_callback_operations_routing(self, command_registry):
        """Test callback operations routing to correct handlers."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        mock_query = MagicMock()
        mock_context = MagicMock()
        
        # Test different callback data routing
        test_cases = [
            ('no_action', None),
            ('nav_back', '_handle_navigation_back'),
            ('nav_main', '_handle_navigation_main'),
            ('cancel_action', '_handle_cancel_action'),
            ('task_done:123', '_handle_task_callback'),
            ('client_view:456', '_handle_client_callback'),
            ('habit_done:789', '_handle_habit_callback'),
            ('confirm_delete:123', '_handle_confirmation_callback'),
            ('menu_tasks', '_handle_menu_callback'),
            ('bulk_status:done', '_handle_bulk_operations_callback'),
            ('task_edit_cancel', '_handle_task_edit_cancel'),
            ('tasks_list', '_handle_tasks_list'),
            ('tasks_refresh', '_handle_tasks_refresh'),
            ('reminders_list', '_handle_reminders_list'),
            ('reminders_refresh', '_handle_reminders_refresh'),
            ('reminder_add', '_handle_reminder_callback'),
            ('attachment_view:123', '_handle_attachment_callback'),
            ('calendar_today', '_handle_calendar_callback'),
            ('filter_date', '_handle_filter_callback'),
            ('add_task', '_handle_add_task'),
        ]
        
        for callback_data, expected_handler in test_cases:
            mock_query.data = callback_data
            if expected_handler:
                # Patch as AsyncMock for async methods
                with patch.object(handler, expected_handler, new_callable=AsyncMock) as mock_handler:
                    await handler._handle_callback_operations(mock_query, mock_context)
                    assert mock_handler.await_count == 1
                    mock_handler.assert_awaited_once_with(mock_query, mock_context)
            else:
                # Should not call any handler for no_action
                await handler._handle_callback_operations(mock_query, mock_context)

    async def test_callback_registry_routing(self, command_registry):
        """Test callback routing through the registry system."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        mock_query = MagicMock()
        mock_context = MagicMock()
        
        # Register a test callback handler
        async def test_callback_handler(query, context):
            return 'test_callback_ok'
        
        command_registry.register_callback('test_callback', test_callback_handler)
        
        # Test that the callback is routed through the registry
        mock_query.data = 'test_callback:value'
        
        with patch.object(command_registry, 'get_callback_handler') as mock_get_handler:
            mock_get_handler.return_value = AsyncMock()
            await handler._handle_callback_operations(mock_query, mock_context)
            
            # Verify the registry was consulted
            mock_get_handler.assert_called_once_with('test_callback:value')
            
            # Verify the handler was called
            mock_get_handler.return_value.assert_awaited_once_with(mock_query, mock_context)

    async def test_authorization_edge_cases(self, command_registry):
        """Test authorization edge cases."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        # Test with no config
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456789
        
        handler.config = None
        assert not handler._is_authorized(mock_update)
        
        # Test with invalid config
        handler.config = MagicMock()
        handler.config.ALLOWED_TELEGRAM_USER_ID = "invalid"
        assert not handler._is_authorized(mock_update)
        
        # Test with no effective_user attribute
        mock_update = MagicMock()
        del mock_update.effective_user
        assert not handler._is_authorized(mock_update)

    async def test_handle_add_task_narrative_flow(self, command_registry):
        """Test that add task button starts the narrative flow."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        # Create mock query
        mock_query = MagicMock()
        mock_query.from_user = MagicMock()
        mock_query.from_user.id = 123456789
        mock_query.edit_message_text = AsyncMock()
        
        # Create mock context
        mock_context = MagicMock()
        mock_context.user_data = {}
        
        # Test the narrative flow integration
        with patch('larrybot.plugins.tasks.narrative_add_task_handler') as mock_narrative:
            await handler._handle_add_task(mock_query, mock_context)
            
            # Verify narrative handler was called
            mock_narrative.assert_called_once()
            
            # Verify the mock update was created correctly
            call_args = mock_narrative.call_args
            mock_update = call_args[0][0]
            assert mock_update.effective_user == mock_query.from_user
            assert mock_update.message.reply_text == mock_query.edit_message_text

    async def test_handle_add_task_fallback(self, command_registry):
        """Test that add task button falls back to help message if narrative flow fails."""
        mock_config = MagicMock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 123456789
        handler = TelegramBotHandler(mock_config, command_registry)
        
        # Create mock query
        mock_query = MagicMock()
        mock_query.from_user = MagicMock()
        mock_query.from_user.id = 123456789
        mock_query.edit_message_text = AsyncMock()
        
        # Create mock context
        mock_context = MagicMock()
        mock_context.user_data = {}
        
        # Test the fallback behavior when narrative flow raises an exception
        with patch('larrybot.plugins.tasks.narrative_add_task_handler', side_effect=Exception("Test error")):
            await handler._handle_add_task(mock_query, mock_context)
            
            # Verify fallback message was sent
            mock_query.edit_message_text.assert_called_once()
            call_args = mock_query.edit_message_text.call_args
            message = call_args[0][0]
            assert "Add New Task" in message
            assert "/addtask" in message
            assert "Try \\`/addtask\\` for the best experience" in message 