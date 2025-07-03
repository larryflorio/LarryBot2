"""
Integration test for enhanced narrative processor in bot handler.
"""

import pytest
pytestmark = pytest.mark.asyncio
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes

from larrybot.handlers.bot import TelegramBotHandler
from larrybot.config.loader import Config
from larrybot.core.command_registry import CommandRegistry
from larrybot.nlp.enhanced_narrative_processor import IntentType, ProcessedInput


class TestNarrativeIntegration:
    """Test narrative input integration in bot handler."""
    
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
        self.message.text = "Add a task to review the quarterly report"
        self.message.from_user = self.user
        self.message.chat = self.chat
        
        # Mock update
        self.update = Mock(spec=Update)
        self.update.message = self.message
        self.update.effective_user = self.user
        
        # Mock context
        self.context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        self.context.user_data = {}
    
    @patch('larrybot.handlers.bot.MessageFormatter.format_error_message')
    async def test_narrative_task_creation(self, mock_format_error):
        """Test narrative input for task creation."""
        # Mock the narrative processor response
        mock_processed_input = ProcessedInput(
            intent=IntentType.CREATE_TASK,
            entities={'task_name': 'review the quarterly report'},
            confidence=0.9,
            suggested_command="/add",
            suggested_parameters={'description': 'review the quarterly report'},
            context=Mock(),
            response_message="✅ I'll create a task for 'review the quarterly report'.\n\n💡 **Suggested command:**\n`review the quarterly report`"
        )
        
        with patch.object(self.handler.enhanced_narrative_processor, 'process_input', return_value=mock_processed_input):
            with patch.object(self.handler, '_execute_suggested_command') as mock_execute:
                await self.handler._handle_text_message(self.update, self.context)
                
                # Verify narrative processor was called
                self.handler.enhanced_narrative_processor.process_input.assert_called_once_with(
                    "Add a task to review the quarterly report", 12345
                )
                
                # Verify suggested command execution was called
                mock_execute.assert_called_once()
                
                # Verify context was updated with NLP data
                assert self.context.user_data['nlp_intent'] == 'create_task'
                assert 'task_name' in self.context.user_data['nlp_entities']
    
    @patch('larrybot.handlers.bot.MessageFormatter.format_error_message')
    async def test_narrative_low_confidence(self, mock_format_error):
        """Test narrative input with low confidence."""
        # Mock low confidence response
        mock_processed_input = ProcessedInput(
            intent=IntentType.UNKNOWN,
            entities={},
            confidence=0.1,
            suggested_command=None,
            suggested_parameters={},
            context=Mock(),
            response_message=""
        )
        
        with patch.object(self.handler.enhanced_narrative_processor, 'process_input', return_value=mock_processed_input):
            with patch.object(self.handler, '_handle_low_confidence_input') as mock_low_conf:
                await self.handler._handle_text_message(self.update, self.context)
                
                # Verify low confidence handler was called
                mock_low_conf.assert_called_once()
    
    @patch('larrybot.handlers.bot.MessageFormatter.format_error_message')
    async def test_task_edit_mode_preserved(self, mock_format_error):
        """Test that task editing mode is preserved."""
        # Set up task editing mode
        self.context.user_data['editing_task_id'] = 123
        
        with patch.object(self.handler, '_handle_task_edit_mode') as mock_edit:
            await self.handler._handle_text_message(self.update, self.context)
            
            # Verify task edit mode handler was called
            mock_edit.assert_called_once_with(self.update, self.context, "Add a task to review the quarterly report")
    
    def test_enhanced_narrative_processor_initialized(self):
        """Test that enhanced narrative processor is properly initialized."""
        assert hasattr(self.handler, 'enhanced_narrative_processor')
        assert self.handler.enhanced_narrative_processor is not None


if __name__ == "__main__":
    pytest.main([__file__]) 