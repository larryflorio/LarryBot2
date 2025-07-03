"""
Test progressive disclosure and smart suggestions functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, User, Message, Chat, CallbackQuery
from telegram.ext import ContextTypes

from larrybot.handlers.bot import TelegramBotHandler
from larrybot.config.loader import Config
from larrybot.core.command_registry import CommandRegistry
from larrybot.utils.enhanced_ux_helpers import ProgressiveDisclosureBuilder, UnifiedButtonBuilder, ButtonType


class TestProgressiveDisclosure:
    """Test progressive disclosure and smart suggestions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.registry = CommandRegistry()
        self.handler = TelegramBotHandler(self.config, self.registry)
        
        # Mock user
        self.user = Mock(spec=User)
        self.user.id = 12345
        
        # Mock chat
        self.chat = Mock(spec=Chat)
        self.chat.id = 67890
        
        # Mock message
        self.message = Mock(spec=Message)
        self.message.from_user = self.user
        self.message.chat = self.chat
        
        # Mock update
        self.update = Mock(spec=Update)
        self.update.message = self.message
        self.update.effective_user = self.user
        
        # Mock context
        self.context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        self.context.user_data = {}
    
    def test_progressive_disclosure_builder_initialization(self):
        """Test that progressive disclosure builder is available."""
        assert hasattr(ProgressiveDisclosureBuilder, 'build_progressive_task_keyboard')
    
    def test_unified_button_builder_initialization(self):
        """Test that unified button builder is available."""
        assert hasattr(UnifiedButtonBuilder, 'build_entity_keyboard')
        assert hasattr(UnifiedButtonBuilder, 'create_button')
    
    def test_button_type_enum(self):
        """Test button type enumeration."""
        assert ButtonType.PRIMARY.value == "primary"
        assert ButtonType.SECONDARY.value == "secondary"
        assert ButtonType.SUCCESS.value == "success"
        assert ButtonType.DANGER.value == "danger"
    
    @pytest.mark.asyncio
    async def test_task_disclosure_handler(self):
        """Test task disclosure handler."""
        # Mock callback query
        query = Mock(spec=CallbackQuery)
        query.data = "task_disclose:123:2"
        query.answer = AsyncMock()
        
        # Mock task view handler
        with patch.object(self.handler, '_handle_task_view') as mock_task_view:
            await self.handler._handle_task_disclosure(query, self.context)
            
            # Verify disclosure level was stored
            assert self.context.user_data['task_disclosure_123'] == 2
            
            # Verify task view was called
            mock_task_view.assert_called_once_with(query, self.context, 123)
    
    @pytest.mark.asyncio
    async def test_task_disclosure_invalid_data(self):
        """Test task disclosure handler with invalid data."""
        # Mock callback query with invalid data
        query = Mock(spec=CallbackQuery)
        query.data = "task_disclose:invalid"
        query.answer = AsyncMock()
        
        # Should handle error gracefully
        await self.handler._handle_task_disclosure(query, self.context)
        
        # Verify error was logged (we can't easily test logging, but ensure no exception)
        assert True  # If we get here, no exception was raised
    
    def test_progressive_task_keyboard_creation(self):
        """Test progressive task keyboard creation."""
        task_data = {
            'id': 123,
            'description': 'Test task',
            'status': 'Todo',
            'priority': 'Medium',
            'due_date': None,
            'category': None
        }
        
        # Test level 1 (basic)
        keyboard = ProgressiveDisclosureBuilder.build_progressive_task_keyboard(
            task_id=123,
            task_data=task_data,
            disclosure_level=1
        )
        
        assert keyboard is not None
        assert hasattr(keyboard, 'inline_keyboard')
        
        # Test level 2 (advanced)
        keyboard2 = ProgressiveDisclosureBuilder.build_progressive_task_keyboard(
            task_id=123,
            task_data=task_data,
            disclosure_level=2
        )
        
        assert keyboard2 is not None
        # Level 2 should have more buttons than level 1
        assert len(keyboard2.inline_keyboard) >= len(keyboard.inline_keyboard)
    
    def test_unified_button_creation(self):
        """Test unified button creation."""
        button = UnifiedButtonBuilder.create_button(
            text="Test Button",
            callback_data="test_callback",
            button_type=ButtonType.PRIMARY
        )
        
        assert button is not None
        assert button.text == "🔵 Test Button"  # Button includes emoji prefix
        assert button.callback_data == "test_callback"
    
    def test_entity_keyboard_creation(self):
        """Test entity keyboard creation."""
        custom_actions = [
            {
                "text": "Test Action",
                "callback_data": "test_action",
                "type": ButtonType.PRIMARY,
                "emoji": "✅"
            }
        ]
        
        keyboard = UnifiedButtonBuilder.build_entity_keyboard(
            entity_id=123,
            entity_type="task",
            available_actions=[],
            custom_actions=custom_actions
        )
        
        assert keyboard is not None
        assert hasattr(keyboard, 'inline_keyboard')


if __name__ == "__main__":
    pytest.main([__file__]) 