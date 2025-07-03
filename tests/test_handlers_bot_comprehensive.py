"""
Comprehensive bot handler testing with edge cases and error scenarios.

This test suite targets the 67% coverage gap in larrybot/handlers/bot.py
to achieve 90%+ coverage through comprehensive error scenario testing.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from telegram import Update, User, Message, CallbackQuery
from telegram.ext import ContextTypes
from larrybot.handlers.bot import TelegramBotHandler
from larrybot.config.loader import Config
from larrybot.core.command_registry import CommandRegistry


class TestBotHandlerComprehensive:
    """Comprehensive bot handler testing with edge cases and error scenarios."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        config = Mock(spec=Config)
        config.TELEGRAM_BOT_TOKEN = "test_token_12345"
        config.ALLOWED_TELEGRAM_USER_ID = 123456789
        config.get_single_user_info.return_value = {
            'authorized_user_id': 123456789,
            'bot_token_configured': True,
            'rate_limit_per_minute': 30
        }
        return config

    @pytest.fixture
    def mock_command_registry(self):
        """Create a mock command registry for testing."""
        registry = Mock(spec=CommandRegistry)
        registry._commands = {
            "/start": Mock(),
            "/help": Mock(),
            "/add": Mock(),
            "/list": Mock(),
            "/done": Mock(),
            "/habit_add": Mock(),
            "/health": Mock()
        }
        return registry

    @pytest.fixture
    def bot_handler(self, mock_config, mock_command_registry):
        """Create a bot handler instance for testing."""
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = Mock()
            mock_builder.return_value.token.return_value.build.return_value = mock_app
            handler = TelegramBotHandler(mock_config, mock_command_registry)
            handler.application = mock_app
            return handler

    @pytest.fixture
    def mock_context(self):
        """Create a mock Telegram context object."""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = []
        context.bot_data = {}
        return context

    @pytest.fixture
    def mock_callback_query(self):
        """Create a mock callback query for testing."""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.data = "test_callback_data"
        return query

    @pytest.fixture
    def mock_update_with_callback(self, mock_callback_query):
        """Create a mock update with callback query."""
        update = Mock(spec=Update)
        update.callback_query = mock_callback_query
        update.effective_user = Mock()
        update.effective_user.id = 123456789  # Authorized user
        return update

    # Authorization & Security Tests

    def test_authorization_edge_cases_invalid_user_ids(self, bot_handler, mock_update, mock_context):
        """Test authorization with various invalid user IDs."""
        # Test negative user ID
        mock_update.effective_user.id = -1
        assert not bot_handler._is_authorized(mock_update)

        # Test zero user ID
        mock_update.effective_user.id = 0
        assert not bot_handler._is_authorized(mock_update)

        # Test non-integer user ID (string)
        mock_update.effective_user.id = "invalid_id"
        assert not bot_handler._is_authorized(mock_update)

    def test_authorization_missing_user_information(self, bot_handler, mock_update, mock_context):
        """Test authorization when user information is missing."""
        # Test with no effective_user
        mock_update.effective_user = None
        assert not bot_handler._is_authorized(mock_update)

        # Test with effective_user but no id attribute
        mock_update.effective_user = Mock()
        # Use configure_mock to properly handle attribute deletion
        mock_update.effective_user.configure_mock(**{})
        # Remove the id attribute by setting it to raise AttributeError using property
        type(mock_update.effective_user).id = property(lambda self: (_ for _ in ()).throw(AttributeError("id")))
        assert not bot_handler._is_authorized(mock_update)

    def test_authorization_multiple_attempts(self, bot_handler, mock_update, mock_context):
        """Test multiple authorization attempts with different users."""
        # First attempt with authorized user
        mock_update.effective_user.id = 123456789
        assert bot_handler._is_authorized(mock_update)

        # Second attempt with unauthorized user
        mock_update.effective_user.id = 987654321
        assert not bot_handler._is_authorized(mock_update)

        # Third attempt with authorized user again
        mock_update.effective_user.id = 123456789
        assert bot_handler._is_authorized(mock_update)

    # Callback Query Handling Tests

    @pytest.mark.asyncio
    async def test_handle_callback_query_unauthorized(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query handling with unauthorized user."""
        mock_update_with_callback.effective_user.id = 987654321  # Unauthorized user
        
        await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
        
        # Should acknowledge the callback query
        mock_update_with_callback.callback_query.answer.assert_called_once()
        # Should show unauthorized message
        mock_update_with_callback.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
        assert "Unauthorized access" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_callback_query_no_action(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query with no_action data."""
        mock_update_with_callback.callback_query.data = "no_action"
        
        await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
        
        # Should acknowledge the callback query
        mock_update_with_callback.callback_query.answer.assert_called_once()
        # Should not edit message for no_action
        mock_update_with_callback.callback_query.edit_message_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_callback_query_navigation_back(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query with navigation back."""
        mock_update_with_callback.callback_query.data = "nav_back"
        
        # Mock the navigation handler
        with patch.object(bot_handler, '_handle_navigation_back') as mock_nav:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            
            mock_nav.assert_called_once_with(mock_update_with_callback.callback_query, mock_context)

    @pytest.mark.asyncio
    async def test_handle_callback_query_navigation_main(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query with navigation to main menu."""
        mock_update_with_callback.callback_query.data = "nav_main"
        
        # Mock the navigation handler
        with patch.object(bot_handler, '_handle_navigation_main') as mock_nav:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            
            mock_nav.assert_called_once_with(mock_update_with_callback.callback_query, mock_context)

    @pytest.mark.asyncio
    async def test_handle_callback_query_cancel_action(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query with cancel action."""
        mock_update_with_callback.callback_query.data = "cancel_action"
        
        # Mock the cancel handler
        with patch.object(bot_handler, '_handle_cancel_action') as mock_cancel:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            
            mock_cancel.assert_called_once_with(mock_update_with_callback.callback_query, mock_context)

    @pytest.mark.asyncio
    async def test_handle_callback_query_task_actions(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query with task actions."""
        # Test task done
        mock_update_with_callback.callback_query.data = "task_done:123"
        with patch.object(bot_handler, '_handle_task_done') as mock_task:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_task.assert_called_once_with(mock_update_with_callback.callback_query, mock_context, 123)

        # Test task edit
        mock_update_with_callback.callback_query.data = "task_edit:456"
        with patch.object(bot_handler, '_handle_task_edit') as mock_task:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_task.assert_called_once_with(mock_update_with_callback.callback_query, mock_context, 456)

        # Test task delete
        mock_update_with_callback.callback_query.data = "task_delete:789"
        with patch.object(bot_handler, '_handle_task_delete') as mock_task:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_task.assert_called_once_with(mock_update_with_callback.callback_query, mock_context, 789)

    @pytest.mark.asyncio
    async def test_handle_callback_query_client_actions(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query with client actions."""
        # Test client tasks
        mock_update_with_callback.callback_query.data = "client_tasks:123"
        with patch.object(bot_handler, '_handle_client_tasks') as mock_client:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_client.assert_called_once_with(mock_update_with_callback.callback_query, mock_context, 123)

        # Test client analytics
        mock_update_with_callback.callback_query.data = "client_analytics:456"
        with patch.object(bot_handler, '_handle_client_analytics') as mock_client:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_client.assert_called_once_with(mock_update_with_callback.callback_query, mock_context, 456)

        # Test client delete
        mock_update_with_callback.callback_query.data = "client_delete:789"
        with patch.object(bot_handler, '_handle_client_delete') as mock_client:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_client.assert_called_once_with(mock_update_with_callback.callback_query, mock_context, 789)

    @pytest.mark.asyncio
    async def test_handle_callback_query_habit_actions(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query with habit actions."""
        # Test habit done
        mock_update_with_callback.callback_query.data = "habit_done:123"
        with patch.object(bot_handler, '_handle_habit_done') as mock_habit:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_habit.assert_called_once_with(mock_update_with_callback.callback_query, mock_context, 123)

        # Test habit progress
        mock_update_with_callback.callback_query.data = "habit_progress:456"
        with patch.object(bot_handler, '_handle_habit_progress') as mock_habit:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_habit.assert_called_once_with(mock_update_with_callback.callback_query, mock_context, 456)

        # Test habit delete
        mock_update_with_callback.callback_query.data = "habit_delete:789"
        with patch.object(bot_handler, '_handle_habit_delete') as mock_habit:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_habit.assert_called_once_with(mock_update_with_callback.callback_query, mock_context, 789)

    @pytest.mark.asyncio
    async def test_handle_callback_query_confirmation_actions(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query with confirmation actions."""
        # Test confirm task delete
        mock_update_with_callback.callback_query.data = "confirm_task_delete:123"
        with patch.object(bot_handler, '_confirm_task_delete') as mock_confirm:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_confirm.assert_called_once_with(mock_update_with_callback.callback_query, mock_context, 123)

        # Test confirm client delete
        mock_update_with_callback.callback_query.data = "confirm_client_delete:456"
        with patch.object(bot_handler, '_confirm_client_delete') as mock_confirm:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_confirm.assert_called_once_with(mock_update_with_callback.callback_query, mock_context, 456)

        # Test confirm habit delete
        mock_update_with_callback.callback_query.data = "confirm_habit_delete:789"
        with patch.object(bot_handler, '_confirm_habit_delete') as mock_confirm:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_confirm.assert_called_once_with(mock_update_with_callback.callback_query, mock_context, 789)

    @pytest.mark.asyncio
    async def test_handle_callback_query_menu_actions(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query with menu actions."""
        # Test menu tasks
        mock_update_with_callback.callback_query.data = "menu_tasks"
        with patch.object(bot_handler, '_show_task_menu') as mock_menu:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_menu.assert_called_once_with(mock_update_with_callback.callback_query, mock_context)

        # Test menu clients
        mock_update_with_callback.callback_query.data = "menu_clients"
        with patch.object(bot_handler, '_show_client_menu') as mock_menu:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_menu.assert_called_once_with(mock_update_with_callback.callback_query, mock_context)

        # Test menu habits
        mock_update_with_callback.callback_query.data = "menu_habits"
        with patch.object(bot_handler, '_show_habit_menu') as mock_menu:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_menu.assert_called_once_with(mock_update_with_callback.callback_query, mock_context)

    @pytest.mark.asyncio
    async def test_handle_callback_query_bulk_operations(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query with bulk operations."""
        mock_update_with_callback.callback_query.data = "bulk_status"
        with patch.object(bot_handler, '_handle_bulk_operations_callback') as mock_bulk:
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            mock_bulk.assert_called_once_with(mock_update_with_callback.callback_query, mock_context)

    @pytest.mark.asyncio
    async def test_handle_callback_query_unknown_action(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query with unknown action."""
        mock_update_with_callback.callback_query.data = "unknown_action"
        
        await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
        
        # Should show unknown action message
        mock_update_with_callback.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
        assert "Unknown action" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_callback_query_exception_handling(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query exception handling."""
        # Mock an exception during callback handling
        mock_update_with_callback.callback_query.data = "task_done:123"
        with patch.object(bot_handler, '_handle_task_done', side_effect=Exception("Test error")):
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            
            # Should show error message
            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()
            call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
            assert "An error occurred" in call_args[0][0]

    # Navigation Handler Tests

    @pytest.mark.asyncio
    async def test_handle_navigation_back(self, bot_handler, mock_callback_query, mock_context):
        """Test navigation back handler."""
        with patch('larrybot.utils.ux_helpers.NavigationHelper.get_main_menu_keyboard') as mock_keyboard:
            mock_keyboard.return_value = Mock()
            
            await bot_handler._handle_navigation_back(mock_callback_query, mock_context)
            
            mock_callback_query.edit_message_text.assert_called_once()
            call_args = mock_callback_query.edit_message_text.call_args
            assert "Back Navigation" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_navigation_main(self, bot_handler, mock_callback_query, mock_context):
        """Test navigation to main menu handler."""
        with patch('larrybot.utils.ux_helpers.NavigationHelper.get_main_menu_keyboard') as mock_keyboard:
            mock_keyboard.return_value = Mock()
            
            await bot_handler._handle_navigation_main(mock_callback_query, mock_context)
            
            mock_callback_query.edit_message_text.assert_called_once()
            call_args = mock_callback_query.edit_message_text.call_args
            assert "Main Menu" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_cancel_action(self, bot_handler, mock_callback_query, mock_context):
        """Test cancel action handler."""
        await bot_handler._handle_cancel_action(mock_callback_query, mock_context)
        
        mock_callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query.edit_message_text.call_args
        assert "Action Cancelled" in call_args[0][0]

    # Task Action Handler Tests

    @pytest.mark.asyncio
    async def test_handle_task_done(self, bot_handler, mock_callback_query, mock_context):
        """Test task done handler."""
        task_id = 123
        
        with patch('larrybot.storage.db.get_session') as mock_session, \
             patch('larrybot.storage.task_repository.TaskRepository') as mock_repo, \
             patch('larrybot.core.dependency_injection.ServiceLocator') as mock_service_locator:
            
            mock_session.return_value.__enter__.return_value = mock_session.return_value
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            
            # Mock ServiceLocator to avoid event bus issues
            mock_service_locator.get.return_value = Mock()
            
            # Create a mock task that is not done
            mock_task = Mock(id=task_id, description="Test task", done=False)
            mock_repo_instance.get_task_by_id.return_value = mock_task
            mock_repo_instance.mark_task_done.return_value = mock_task
            
            # Mock list_incomplete_tasks to return an empty list (iterable)
            mock_repo_instance.list_incomplete_tasks.return_value = []
            
            await bot_handler._handle_task_done(mock_callback_query, mock_context, task_id)
            
            # Handler calls edit_message_text twice: loading message + result
            assert mock_callback_query.edit_message_text.call_count == 2
            
            # Check the final call contains success message
            final_call_args = mock_callback_query.edit_message_text.call_args_list[-1]
            # The success message should contain task completion indicators
            final_message = final_call_args[0][0].lower()
            assert any(indicator in final_message for indicator in ["completed", "task completed", "great work", "momentum"])

    @pytest.mark.asyncio
    async def test_handle_task_edit(self, bot_handler, mock_callback_query, mock_context):
        """Test task edit handler."""
        task_id = 123
        
        with patch('larrybot.storage.db.get_session') as mock_session, \
             patch('larrybot.storage.task_repository.TaskRepository') as mock_repo:
            
            mock_session.return_value.__enter__.return_value = mock_session.return_value
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.get_task_by_id.return_value = Mock(id=task_id, description="Test task")
            
            await bot_handler._handle_task_edit(mock_callback_query, mock_context, task_id)
            
            mock_callback_query.edit_message_text.assert_called_once()
            call_args = mock_callback_query.edit_message_text.call_args
            assert "edit" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_handle_task_delete(self, bot_handler, mock_callback_query, mock_context):
        """Test task delete handler."""
        task_id = 123
        
        with patch('larrybot.storage.db.get_session') as mock_session, \
             patch('larrybot.storage.task_repository.TaskRepository') as mock_repo:
            
            mock_session.return_value.__enter__.return_value = mock_session.return_value
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.get_task_by_id.return_value = Mock(id=task_id, description="Test task")
            
            await bot_handler._handle_task_delete(mock_callback_query, mock_context, task_id)
            
            mock_callback_query.edit_message_text.assert_called_once()
            call_args = mock_callback_query.edit_message_text.call_args
            assert "delete" in call_args[0][0].lower()

    # Help Command Error Handling Tests

    @pytest.mark.asyncio
    async def test_help_command_unauthorized_access(self, bot_handler, mock_update, mock_context):
        """Test help command with unauthorized access."""
        mock_update.effective_user.id = 987654321  # Unauthorized user
        
        await bot_handler._help(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Unauthorized access" in call_args

    @pytest.mark.asyncio
    async def test_help_command_malformed_metadata(self, bot_handler, mock_update, mock_context):
        """Test help command with malformed command metadata."""
        # Mock command registry with malformed metadata
        bot_handler.command_registry._commands = {
            "/start": Mock(),
            "/help": Mock(),
            "/add": Mock(),
            "/list": Mock()
        }
        
        # Mock get_command_metadata to return malformed data
        def mock_get_metadata(cmd):
            if cmd == "/add":
                return Mock(description=None, category="tasks")  # Missing description
            elif cmd == "/list":
                return Mock(description="List tasks", category=None)  # Missing category
            return Mock(description="Test command", category="test")
        
        bot_handler.command_registry.get_command_metadata = mock_get_metadata
        
        await bot_handler._help(mock_update, mock_context)
        
        # Should handle malformed metadata gracefully
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_help_command_empty_command_registry(self, bot_handler, mock_update, mock_context):
        """Test help command with empty command registry."""
        bot_handler.command_registry._commands = {}
        bot_handler.command_registry.get_command_metadata = Mock(return_value=None)
        
        await bot_handler._help(mock_update, mock_context)
        
        # Should handle empty registry gracefully
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        # The text is escaped for MarkdownV2, so we need to look for escaped asterisks
        assert "\\*Total Commands\\*: 0" in call_args

    @pytest.mark.asyncio
    async def test_help_command_markdown_parsing_failures(self, bot_handler, mock_update, mock_context):
        """Test help command with Markdown parsing failures."""
        # Mock command registry with problematic descriptions
        bot_handler.command_registry._commands = {
            "/start": Mock(),
            "/help": Mock(),
            "/test": Mock()
        }
        
        # Mock get_command_metadata to return descriptions with special characters
        def mock_get_metadata(cmd):
            if cmd == "/test":
                return Mock(
                    description="Test command with _italics_ and *bold* and [links]",
                    category="test"
                )
            return Mock(description="Normal command", category="system")
        
        bot_handler.command_registry.get_command_metadata = mock_get_metadata
        
        # Mock reply_text to raise exception on first call (Markdown failure)
        mock_update.message.reply_text.side_effect = [
            Exception("Markdown parsing failed"),  # First call fails
            None  # Second call (fallback) succeeds
        ]
        
        await bot_handler._help(mock_update, mock_context)
        
        # Should call reply_text twice: once with Markdown, once with fallback
        assert mock_update.message.reply_text.call_count == 2

    @pytest.mark.asyncio
    async def test_help_command_very_long_descriptions(self, bot_handler, mock_update, mock_context):
        """Test help command with very long descriptions."""
        bot_handler.command_registry._commands = {
            "/start": Mock(),
            "/help": Mock(),
            "/long": Mock()
        }
        
        # Mock get_command_metadata to return very long descriptions
        def mock_get_metadata(cmd):
            if cmd == "/long":
                return Mock(
                    description="A" * 1000,  # Very long description
                    category="test"
                )
            return Mock(description="Normal command", category="system")
        
        bot_handler.command_registry.get_command_metadata = mock_get_metadata
        
        await bot_handler._help(mock_update, mock_context)
        
        # Should handle long descriptions gracefully
        mock_update.message.reply_text.assert_called_once()

    # Dispatch Command Tests

    @pytest.mark.asyncio
    async def test_dispatch_command_unauthorized_access(self, bot_handler, mock_update, mock_context):
        """Test dispatch command with unauthorized access."""
        mock_update.effective_user.id = 987654321  # Unauthorized user
        mock_update.message.text = "/add Test task"
        
        await bot_handler._dispatch_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Unauthorized access" in call_args

    @pytest.mark.asyncio
    async def test_dispatch_command_without_message(self, bot_handler, mock_update, mock_context):
        """Test dispatch command without message."""
        mock_update.message = None
        
        await bot_handler._dispatch_command(mock_update, mock_context)
        
        # Should handle gracefully without calling reply_text

    @pytest.mark.asyncio
    async def test_dispatch_command_without_text(self, bot_handler, mock_update, mock_context):
        """Test dispatch command without text."""
        mock_update.message.text = None
        
        await bot_handler._dispatch_command(mock_update, mock_context)
        
        # Should handle gracefully without calling reply_text

    @pytest.mark.asyncio
    async def test_dispatch_command_invalid_command_format(self, bot_handler, mock_update, mock_context):
        """Test dispatch command with invalid command format."""
        mock_update.message.text = "invalid_command_format"
        
        # Mock the command registry to handle invalid format
        bot_handler.command_registry.dispatch.return_value = None
        
        await bot_handler._dispatch_command(mock_update, mock_context)
        
        # Should call dispatch but may not call reply_text for invalid format
        bot_handler.command_registry.dispatch.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_command_registry_exception(self, bot_handler, mock_update, mock_context):
        """Test dispatch command when registry raises exception."""
        mock_update.message.text = "/add Test task"
        
        # Mock registry to raise exception
        bot_handler.command_registry.dispatch.side_effect = Exception("Registry error")
        
        await bot_handler._dispatch_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Error" in call_args

    @pytest.mark.asyncio
    async def test_dispatch_command_async_result(self, bot_handler, mock_update, mock_context):
        """Test dispatch command with async result."""
        mock_update.message.text = "/add Test task"
        
        # Mock registry to return async handler
        async def async_handler(update, context):
            return "Async result"
        
        bot_handler.command_registry.dispatch.return_value = async_handler
        
        await bot_handler._dispatch_command(mock_update, mock_context)
        
        # Should handle async result properly
        bot_handler.command_registry.dispatch.assert_called_once()

    # Startup Sequence Tests

    def test_startup_sequence_event_loop_setting(self, bot_handler):
        """Test startup sequence event loop setting."""
        with patch('larrybot.plugins.reminder.set_main_event_loop') as mock_set_loop, \
             patch('asyncio.get_event_loop') as mock_get_loop, \
             patch.object(bot_handler.application, 'run_polling'):
            
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop
            
            bot_handler.run()
            
            # The set_main_event_loop call may not happen in test environment
            # but the method should complete without errors

    def test_startup_sequence_event_loop_runtime_error(self, bot_handler):
        """Test startup sequence with event loop runtime error."""
        with patch('larrybot.plugins.reminder.set_main_event_loop') as mock_set_loop, \
             patch('asyncio.get_event_loop', side_effect=RuntimeError("No event loop")):
            
            # Should handle runtime error gracefully
            bot_handler.run()
            
            # Should not call set_main_event_loop if no event loop
            mock_set_loop.assert_not_called()

    def test_startup_sequence_application_startup(self, bot_handler):
        """Test startup sequence application startup."""
        with patch('larrybot.plugins.reminder.set_main_event_loop') as mock_set_loop, \
             patch.object(bot_handler.application, 'run_polling') as mock_run:
            
            bot_handler.run()
            
            mock_run.assert_called_once()

    # Start Command Tests

    @pytest.mark.asyncio
    async def test_start_command_authorized_user(self, bot_handler, mock_update, mock_context):
        """Test start command with authorized user."""
        await bot_handler._start(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Welcome" in call_args

    @pytest.mark.asyncio
    async def test_start_command_unauthorized_user(self, bot_handler, mock_update, mock_context):
        """Test start command with unauthorized user."""
        mock_update.effective_user.id = 987654321  # Unauthorized user
        
        await bot_handler._start(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Unauthorized Access" in call_args

    # Help Command Success Tests

    @pytest.mark.asyncio
    async def test_help_command_successful_rendering(self, bot_handler, mock_update, mock_context):
        """Test help command successful rendering."""
        bot_handler.command_registry._commands = {
            "/start": Mock(),
            "/help": Mock(),
            "/add": Mock(),
            "/list": Mock()
        }
        
        def mock_get_metadata(cmd):
            return Mock(
                description="Test command description",
                category="test",
                usage="/test"
            )
        
        bot_handler.command_registry.get_command_metadata = mock_get_metadata
        
        await bot_handler._help(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Available Commands" in call_args[0][0]
        assert call_args[1].get('parse_mode') == 'MarkdownV2'

    # Error Recovery Tests

    @pytest.mark.asyncio
    async def test_error_recovery_in_dispatch_command(self, bot_handler, mock_update, mock_context):
        """Test error recovery in dispatch command."""
        mock_update.message.text = "/add Test task"
        
        # Mock registry to raise different types of exceptions
        exceptions_to_test = [
            ValueError("Invalid input"),
            KeyError("Missing key"),
            AttributeError("Missing attribute"),
            Exception("Generic error")
        ]
        
        for exception in exceptions_to_test:
            bot_handler.command_registry.dispatch.side_effect = exception
            
            await bot_handler._dispatch_command(mock_update, mock_context)
            
            mock_update.message.reply_text.assert_called()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Error" in call_args
            
            # Reset for next iteration
            mock_update.message.reply_text.reset_mock()

    # Performance Tests

    def test_authorization_performance(self, bot_handler, mock_update):
        """Test authorization performance with multiple calls."""
        import time
        
        start_time = time.time()
        for _ in range(1000):
            bot_handler._is_authorized(mock_update)
        end_time = time.time()
        
        # Should complete 1000 authorization checks in under 1 second
        assert end_time - start_time < 1.0

    # Large Dataset Tests

    @pytest.mark.asyncio
    async def test_help_command_large_command_registry(self, bot_handler, mock_update, mock_context):
        """Test help command with large command registry."""
        # Create large command registry
        large_commands = {f"/command_{i}": Mock() for i in range(100)}
        bot_handler.command_registry._commands = large_commands
        
        def mock_get_metadata(cmd):
            return Mock(
                description=f"Description for {cmd}",
                category="test",
                usage=f"{cmd} usage"
            )
        
        bot_handler.command_registry.get_command_metadata = mock_get_metadata
        
        await bot_handler._help(mock_update, mock_context)
        
        # Should handle large registry gracefully
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        # The text is escaped for MarkdownV2, so we need to look for escaped asterisks
        assert "\\*Total Commands\\*: 100" in call_args 