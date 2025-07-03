"""
Test progressive disclosure system for enhanced UX.
"""

import pytest
pytestmark = pytest.mark.asyncio
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, User, Message, Chat, CallbackQuery
from telegram.ext import ContextTypes
import asyncio

from larrybot.handlers.bot import TelegramBotHandler
from larrybot.config.loader import Config
from larrybot.core.command_registry import CommandRegistry


class TestProgressiveDisclosure:
    """Test progressive disclosure functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Set up event loop for TelegramBotHandler initialization
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        self.config = Config()
        self.registry = CommandRegistry()
        
        # Mock the Application builder to avoid event loop issues
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = Mock()
            mock_builder.return_value.token.return_value.request.return_value.build.return_value = mock_app
            self.handler = TelegramBotHandler(self.config, self.registry)
        
        # Mock user
        self.user = Mock(spec=User)
        self.user.id = 12345
        
        # Mock chat
        self.chat = Mock(spec=Chat)
        self.chat.id = 67890
        
        # Mock message
        self.message = Mock(spec=Message)
        self.message.text = "Test message"
        self.message.from_user = self.user
        self.message.chat = self.chat
        
        # Mock update
        self.update = Mock(spec=Update)
        self.update.message = self.message
        self.update.effective_user = self.user
        
        # Mock callback query
        self.callback_query = Mock(spec=CallbackQuery)
        self.callback_query.data = "task_disclosure_123"
        self.callback_query.from_user = self.user
        self.callback_query.answer = AsyncMock()
        self.callback_query.edit_message_text = AsyncMock()
        
        # Mock context
        self.context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        self.context.user_data = {}
    
    def test_progressive_disclosure_builder_initialization(self):
        """Test progressive disclosure builder initialization."""
        assert hasattr(self.handler, 'enhanced_message_processor')
        assert self.handler.enhanced_message_processor is not None
    
    def test_unified_button_builder_initialization(self):
        """Test unified button builder initialization."""
        # Test that the button builder components are available
        from larrybot.utils.ux_helpers import KeyboardBuilder
        assert KeyboardBuilder is not None
    
    def test_button_type_enum(self):
        """Test button type enum values."""
        from larrybot.utils.ux_helpers import ButtonType
        assert ButtonType.TASK_ACTION in ButtonType
        assert ButtonType.NAVIGATION in ButtonType
        assert ButtonType.CONFIRMATION in ButtonType
    
    @patch('larrybot.handlers.bot.MessageFormatter.format_error_message')
    async def test_task_disclosure_handler(self, mock_format_error):
        """Test task disclosure handler."""
        # Mock task data
        mock_task = Mock()
        mock_task.id = 123
        mock_task.description = "Test task"
        mock_task.status = "Todo"
        mock_task.priority = "Medium"
        
        with patch('larrybot.storage.task_repository.TaskRepository') as mock_repo:
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.get_task_by_id.return_value = mock_task
            
            await self.handler._handle_task_disclosure(self.callback_query, self.context)
            
            # Verify callback was answered
            self.callback_query.answer.assert_called_once()
            
            # Verify message was edited with task details
            self.callback_query.edit_message_text.assert_called_once()
    
    @patch('larrybot.handlers.bot.MessageFormatter.format_error_message')
    async def test_task_disclosure_invalid_data(self, mock_format_error):
        """Test task disclosure with invalid data."""
        # Test with invalid callback data
        self.callback_query.data = "invalid_data"
        
        await self.handler._handle_task_disclosure(self.callback_query, self.context)
        
        # Verify error message was sent
        self.callback_query.edit_message_text.assert_called_once()
    
    def test_progressive_task_keyboard_creation(self):
        """Test progressive task keyboard creation."""
        from larrybot.utils.ux_helpers import KeyboardBuilder
        
        # Test creating a progressive task keyboard
        keyboard = KeyboardBuilder.build_progressive_task_keyboard(123)
        assert keyboard is not None
        assert hasattr(keyboard, 'inline_keyboard')
    
    def test_unified_button_creation(self):
        """Test unified button creation."""
        from larrybot.utils.ux_helpers import KeyboardBuilder, ButtonType
        
        # Test creating different types of buttons
        task_button = KeyboardBuilder.create_button("Test", "test_callback", ButtonType.TASK_ACTION)
        nav_button = KeyboardBuilder.create_button("Back", "nav_back", ButtonType.NAVIGATION)
        
        assert task_button is not None
        assert nav_button is not None
        assert task_button.text == "Test"
        assert nav_button.text == "Back"
    
    def test_entity_keyboard_creation(self):
        """Test entity keyboard creation."""
        from larrybot.utils.ux_helpers import KeyboardBuilder
        
        # Test creating entity-specific keyboard
        entities = ["task", "reminder", "habit"]
        keyboard = KeyboardBuilder.build_entity_keyboard(entities, "entity_action")
        
        assert keyboard is not None
        assert hasattr(keyboard, 'inline_keyboard')


if __name__ == "__main__":
    pytest.main([__file__]) 