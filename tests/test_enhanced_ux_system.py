"""
Tests for Enhanced UX System

This module tests the enhanced UX components including message layout,
smart navigation, error recovery, and visual feedback systems.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from larrybot.utils.enhanced_ux_helpers import (
    MessageLayoutBuilder,
    SmartNavigationHelper,
    ErrorRecoveryHelper,
    VisualFeedbackSystem,
    EnhancedUXSystem
)
from larrybot.core.enhanced_message_processor import EnhancedMessageProcessor
from larrybot.config.ux_config import UXConfig
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class TestMessageLayoutBuilder:
    """Test the MessageLayoutBuilder class."""
    
    def test_build_section_header(self):
        """Test building section headers."""
        header = MessageLayoutBuilder.build_section_header("Test Section", "📋")
        assert "📋 **Test Section**" in header
        assert "─" * 30 in header
    
    def test_build_section_header_with_subtitle(self):
        """Test building section headers with subtitle."""
        header = MessageLayoutBuilder.build_section_header("Test Section", "📋", "Subtitle")
        assert "📋 **Test Section**" in header
        assert "_Subtitle_" in header
    
    def test_build_info_card_default(self):
        """Test building default info cards."""
        content = {"Name": "Test", "Value": "123"}
        card = MessageLayoutBuilder.build_info_card("Test Card", content)
        assert "ℹ️ **Test Card**" in card
        assert "Name: Test" in card
        assert "Value: 123" in card
    
    def test_build_info_card_success(self):
        """Test building success info cards."""
        content = {"Status": "Success"}
        card = MessageLayoutBuilder.build_info_card("Success Card", content, "success")
        assert "✅ **Success Card**" in card
    
    def test_build_progressive_list(self):
        """Test building progressive lists."""
        items = [{"description": f"Item {i}"} for i in range(1, 8)]
        list_text = MessageLayoutBuilder.build_progressive_list(items, max_visible=5, title="Test List")
        assert "📋 **Test List** \\(7 total\\)" in list_text
        assert "Item 1" in list_text
        assert "Item 5" in list_text
        assert "\\.\\.\\. and 2 more items" in list_text
    
    def test_build_progressive_list_empty(self):
        """Test building progressive lists with empty items."""
        list_text = MessageLayoutBuilder.build_progressive_list([], title="Empty List")
        assert "📋 **Empty List**" in list_text
        assert "No items found" in list_text
    
    def test_build_status_indicator(self):
        """Test building status indicators."""
        indicator = MessageLayoutBuilder.build_status_indicator("In Progress", "High")
        assert "🔄 **In Progress**" in indicator
        assert "🟠 High" in indicator
    
    def test_build_summary_card(self):
        """Test building summary cards."""
        metrics = {"Total": 10, "Completed": 7, "Rate": 70.0}
        card = MessageLayoutBuilder.build_summary_card("Test Summary", metrics)
        assert "📊 **Test Summary**" in card
        assert "Total: 10" in card
        assert "Completed: 7" in card
        assert "Rate: 70.0%" in card


class TestSmartNavigationHelper:
    """Test the SmartNavigationHelper class."""
    
    def test_build_contextual_keyboard(self):
        """Test building contextual keyboards."""
        available_actions = [
            {'text': 'Action 1', 'callback_data': 'action1', 'type': 'primary'},
            {'text': 'Action 2', 'callback_data': 'action2', 'type': 'secondary'},
            {'text': 'Back', 'callback_data': 'back', 'type': 'navigation'}
        ]
        
        keyboard = SmartNavigationHelper.build_contextual_keyboard(
            'test_context',
            available_actions
        )
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Check that buttons are properly grouped
        assert len(keyboard.inline_keyboard) > 0
    
    def test_add_breadcrumb_navigation(self):
        """Test adding breadcrumb navigation."""
        message = "Test message"
        navigation_path = ['Main', 'Submenu', 'Current']
        
        enhanced_message = SmartNavigationHelper.add_breadcrumb_navigation(message, navigation_path)
        assert "📍 **Navigation:**" in enhanced_message
        assert "Main > Submenu > **Current**" in enhanced_message
    
    def test_suggest_next_actions(self):
        """Test suggesting next actions."""
        suggestions = SmartNavigationHelper.suggest_next_actions('task_list', {})
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
    
    def test_build_quick_actions_keyboard_task(self):
        """Test building quick actions keyboard for tasks."""
        keyboard = SmartNavigationHelper.build_quick_actions_keyboard('task', 123)
        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Check that task-specific actions are present
        button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert any('Done' in text for text in button_texts)
        assert any('Edit' in text for text in button_texts)
    
    def test_build_quick_actions_keyboard_client(self):
        """Test building quick actions keyboard for clients."""
        keyboard = SmartNavigationHelper.build_quick_actions_keyboard('client', 456)
        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Check that client-specific actions are present
        button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert any('Tasks' in text for text in button_texts)
        assert any('Analytics' in text for text in button_texts)


class TestErrorRecoveryHelper:
    """Test the ErrorRecoveryHelper class."""
    
    def test_build_error_recovery_keyboard_validation(self):
        """Test building error recovery keyboard for validation errors."""
        keyboard = ErrorRecoveryHelper.build_error_recovery_keyboard(
            'validation_error',
            {'field': 'name'}
        )
        assert isinstance(keyboard, InlineKeyboardMarkup)
        button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert any('Try Again' in text for text in button_texts)
        assert any('Edit Input' in text for text in button_texts)
    
    def test_build_error_recovery_keyboard_not_found(self):
        """Test building error recovery keyboard for not found errors."""
        keyboard = ErrorRecoveryHelper.build_error_recovery_keyboard(
            'not_found_error',
            {'entity_type': 'task'}
        )
        assert isinstance(keyboard, InlineKeyboardMarkup)
        button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert any('Search' in text for text in button_texts)
        assert any('Create New' in text for text in button_texts)
    
    def test_suggest_alternatives(self):
        """Test suggesting alternative commands."""
        alternatives = ErrorRecoveryHelper.suggest_alternatives('add_task', {})
        assert isinstance(alternatives, list)
        assert len(alternatives) > 0
    
    def test_provide_contextual_help(self):
        """Test providing contextual help."""
        help_message = ErrorRecoveryHelper.provide_contextual_help({
            'type': 'validation_error',
            'message': 'Invalid input'
        })
        assert "💡 **Help**" in help_message
        assert "Invalid input" in help_message


class TestVisualFeedbackSystem:
    """Test the VisualFeedbackSystem class."""
    
    def test_show_loading_state(self):
        """Test showing loading state."""
        loading_message = VisualFeedbackSystem.show_loading_state("Processing tasks")
        assert "⏳ **Processing tasks**" in loading_message
        assert "🔄 Processing\\.\\.\\." in loading_message
    
    def test_show_loading_state_with_estimate(self):
        """Test showing loading state with time estimate."""
        loading_message = VisualFeedbackSystem.show_loading_state("Processing tasks", 5.0)
        assert "⏳ **Processing tasks**" in loading_message
        assert "⏱️ Estimated time: 5.0s" in loading_message
    
    def test_show_success_animation(self):
        """Test showing success animation."""
        details = {"Tasks": 5, "Status": "Completed"}
        success_message = VisualFeedbackSystem.show_success_animation("Task completion", details)
        assert "✅ **Task completion**" in success_message
        assert "🎉 Successfully completed!" in success_message
        assert "Tasks: 5" in success_message
    
    def test_show_progress_bar(self):
        """Test showing progress bar."""
        progress_message = VisualFeedbackSystem.show_progress_bar(3, 10, "Task Progress")
        assert "📊 **Task Progress**" in progress_message
        assert "Progress: 3/10" in progress_message
        assert "30.0%" in progress_message
    
    def test_show_confirmation_dialog(self):
        """Test showing confirmation dialog."""
        details = {"Task": "Test task", "Risk": "Low"}
        message, keyboard = VisualFeedbackSystem.show_confirmation_dialog(
            "delete task",
            details,
            "low"
        )
        assert "ℹ️ **Confirm delete task**" in message
        assert "Task: Test task" in message
        assert "Are you sure you want to proceed?" in message
        assert isinstance(keyboard, InlineKeyboardMarkup)


class TestEnhancedUXSystem:
    """Test the EnhancedUXSystem class."""
    
    @pytest.mark.asyncio
    async def test_enhance_message(self):
        """Test enhancing messages with UX improvements."""
        ux_system = EnhancedUXSystem()
        message = "Test message"
        context = {
            'current_context': 'main',
            'navigation_path': ['Main Menu'],
            'available_actions': [
                {'text': 'Test Action', 'callback_data': 'test_action', 'type': 'primary'}
            ]
        }
        
        enhanced_message, keyboard = ux_system.enhance_message(message, context)
        assert "📍 **Navigation:**" in enhanced_message
        assert "Test message" in enhanced_message
        assert isinstance(keyboard, InlineKeyboardMarkup)
    
    def test_create_error_response(self):
        """Test creating error responses."""
        ux_system = EnhancedUXSystem()
        context = {'current_context': 'error'}
        
        error_message, keyboard = ux_system.create_error_response(
            'validation_error',
            'Invalid input',
            context
        )
        assert "❌ **Error**" in error_message
        assert "Invalid input" in error_message
        assert isinstance(keyboard, InlineKeyboardMarkup)


class TestEnhancedMessageProcessor:
    """Test the EnhancedMessageProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create a message processor instance."""
        return EnhancedMessageProcessor()
    
    @pytest.mark.asyncio
    async def test_process_message_basic(self, processor):
        """Test basic message processing."""
        message = "Test message"
        context = {'current_context': 'main'}
        
        enhanced_message, keyboard = await processor.process_message(message, context)
        assert enhanced_message == message
        assert isinstance(keyboard, InlineKeyboardMarkup)
    
    @pytest.mark.asyncio
    async def test_process_message_with_tasks(self, processor):
        """Test message processing with task context."""
        message = "Task list"
        context = {
            'current_context': 'tasks',
            'tasks': [{'description': 'Test task 1'}, {'description': 'Test task 2'}]
        }
        
        enhanced_message, keyboard = await processor.process_message(message, context)
        assert "📋 **Tasks** \\(2 total\\)" in enhanced_message
        assert isinstance(keyboard, InlineKeyboardMarkup)
    
    @pytest.mark.asyncio
    async def test_process_message_with_clients(self, processor):
        """Test message processing with client context."""
        message = "Client list"
        context = {
            'current_context': 'clients',
            'clients': [{'name': 'Client 1'}, {'name': 'Client 2'}]
        }
        
        enhanced_message, keyboard = await processor.process_message(message, context)
        assert "📋 **Clients** \\(2 total\\)" in enhanced_message
        assert isinstance(keyboard, InlineKeyboardMarkup)
    
    @pytest.mark.asyncio
    async def test_process_message_with_analytics(self, processor):
        """Test message processing with analytics context."""
        message = "Analytics"
        context = {
            'current_context': 'analytics',
            'analytics': {'Total': 10, 'Completed': 7}
        }
        
        enhanced_message, keyboard = await processor.process_message(message, context)
        assert "📊 **Analytics Summary**" in enhanced_message
        assert isinstance(keyboard, InlineKeyboardMarkup)
    
    def test_create_error_response(self, processor):
        """Test creating error responses."""
        context = {'current_context': 'error'}
        
        error_message, keyboard = processor.create_error_response(
            'validation_error',
            'Invalid input',
            context
        )
        assert "❌ **Error**" in error_message
        assert "Invalid input" in error_message
        assert isinstance(keyboard, InlineKeyboardMarkup)
    
    def test_create_loading_message(self, processor):
        """Test creating loading messages."""
        loading_message = processor.create_loading_message("Processing")
        assert "⏳ **Processing**" in loading_message
        assert "🔄 Processing\\.\\.\\." in loading_message
    
    def test_create_success_message(self, processor):
        """Test creating success messages."""
        details = {"Tasks": 5}
        success_message = processor.create_success_message("Task completion", details)
        assert "✅ **Task completion**" in success_message
        assert "🎉 Successfully completed!" in success_message
    
    def test_create_confirmation_dialog(self, processor):
        """Test creating confirmation dialogs."""
        details = {"Task": "Test task"}
        message, keyboard = processor.create_confirmation_dialog(
            "delete task",
            details,
            "low"
        )
        assert "ℹ️ **Confirm delete task**" in message
        assert "Are you sure you want to proceed?" in message
        assert isinstance(keyboard, InlineKeyboardMarkup)


class TestUXConfig:
    """Test the UXConfig class."""
    
    def test_get_config(self):
        """Test getting configuration as dictionary."""
        config = UXConfig.get_config()
        assert isinstance(config, dict)
        assert 'progressive_disclosure' in config
        assert 'smart_navigation' in config
        assert 'enhanced_feedback' in config
    
    def test_is_feature_enabled(self):
        """Test checking if features are enabled."""
        assert UXConfig.is_feature_enabled('progressive_disclosure') == True
        assert UXConfig.is_feature_enabled('smart_navigation') == True
        assert UXConfig.is_feature_enabled('nonexistent_feature') == False


class TestEnhancedUXIntegration:
    """Integration tests for the enhanced UX system."""
    
    @pytest.mark.asyncio
    async def test_full_message_processing_workflow(self):
        """Test the complete message processing workflow."""
        processor = EnhancedMessageProcessor()
        
        # Simulate a task list context
        message = "Task list"
        context = {
            'current_context': 'tasks',
            'tasks': [
                {'description': 'Complete project documentation'},
                {'description': 'Review code changes'},
                {'description': 'Update dependencies'}
            ],
            'navigation_path': ['Main Menu', 'Tasks'],
            'available_actions': [
                {'text': '➕ Add Task', 'callback_data': 'add_task', 'type': 'primary'},
                {'text': '🔄 Refresh', 'callback_data': 'tasks_refresh', 'type': 'primary'},
                {'text': '🏠 Main Menu', 'callback_data': 'nav_main', 'type': 'navigation'}
            ]
        }
        
        # Process the message
        enhanced_message, keyboard = await processor.process_message(message, context)
        
        # Verify enhanced message
        assert "📋 **Tasks** \\(3 total\\)" in enhanced_message
        assert "Complete project documentation" in enhanced_message
        assert "Review code changes" in enhanced_message
        assert "Update dependencies" in enhanced_message
        assert "📍 **Navigation:**" in enhanced_message
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test the complete error recovery workflow."""
        processor = EnhancedMessageProcessor()
        
        # Simulate an error context
        context = {
            'current_context': 'error',
            'error_type': 'validation_error',
            'navigation_path': ['Error Recovery'],
            'available_actions': [
                {'text': '🔄 Retry', 'callback_data': 'retry_action', 'type': 'primary'},
                {'text': '🏠 Main Menu', 'callback_data': 'nav_main', 'type': 'navigation'},
                {'text': '❓ Help', 'callback_data': 'show_help', 'type': 'secondary'}
            ]
        }
        
        # Create error response
        error_message, keyboard = processor.create_error_response(
            'validation_error',
            'Invalid task description format',
            context
        )
        
        # Verify error message
        assert "❌ **Error**" in error_message
        assert "Invalid task description format" in error_message
        assert "💡 **Help**" in error_message
        assert isinstance(keyboard, InlineKeyboardMarkup)
        button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert any('Try Again' in text or 'Retry' in text for text in button_texts)
        assert any('Edit Input' in text or 'Help' in text for text in button_texts) 