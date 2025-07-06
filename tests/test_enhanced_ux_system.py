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
    EnhancedUXSystem,
    SmartSuggestionsHelper,
    IntelligentDefaultsHelper,
    ProgressiveDisclosureBuilder
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
        assert "**Current** > Current" in enhanced_message
    
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
        assert "💡 **Validation Error**" in help_message
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


class TestSmartSuggestionsHelper:
    """Test the SmartSuggestionsHelper class."""
    
    def test_suggest_next_actions_task_view_context(self):
        """Test suggesting next actions for task view context."""
        suggestions = SmartSuggestionsHelper.suggest_next_actions(
            'task_view', 
            {'user_id': 123}, 
            []
        )
        
        assert len(suggestions) > 0
        assert any(s['action'] == 'edit_task' for s in suggestions)
        assert any(s['action'] == 'complete_task' for s in suggestions)
    
    def test_suggest_next_actions_task_list_context(self):
        """Test suggesting next actions for task list context."""
        suggestions = SmartSuggestionsHelper.suggest_next_actions(
            'task_list', 
            {'user_id': 123}, 
            []
        )
        
        assert len(suggestions) > 0
        assert any(s['action'] == 'add_task' for s in suggestions)
        assert any(s['action'] == 'filter_tasks' for s in suggestions)
    
    def test_suggest_task_improvements_priority(self):
        """Test suggesting task improvements for priority."""
        task_data = {
            'priority': 'Medium',
            'status': 'Todo',
            'description': 'Test task'
        }
        
        suggestions = SmartSuggestionsHelper.suggest_task_improvements(task_data)
        
        assert len(suggestions) > 0
        priority_suggestion = next((s for s in suggestions if s['type'] == 'priority'), None)
        assert priority_suggestion is not None
        assert 'higher priority' in priority_suggestion['message']
    
    def test_suggest_task_improvements_due_date(self):
        """Test suggesting task improvements for due date."""
        task_data = {
            'priority': 'High',
            'status': 'Todo',
            'description': 'Test task'
        }
        
        suggestions = SmartSuggestionsHelper.suggest_task_improvements(task_data)
        
        due_date_suggestion = next((s for s in suggestions if s['type'] == 'due_date'), None)
        assert due_date_suggestion is not None
        assert 'due date' in due_date_suggestion['message']
    
    def test_suggest_productivity_improvements(self):
        """Test suggesting productivity improvements."""
        user_data = {'user_id': 123}
        task_history = [
            {'status': 'Done', 'priority': 'High'},
            {'status': 'Todo', 'priority': 'High'},
            {'status': 'Todo', 'priority': 'Medium'}
        ]
        
        suggestions = SmartSuggestionsHelper.suggest_productivity_improvements(user_data, task_history)
        
        assert 'time_management' in suggestions
        assert 'task_organization' in suggestions
        assert len(suggestions['time_management']) > 0


class TestIntelligentDefaultsHelper:
    """Test the IntelligentDefaultsHelper class."""
    
    def test_suggest_task_defaults_urgent(self):
        """Test suggesting task defaults for urgent tasks."""
        defaults = IntelligentDefaultsHelper.suggest_task_defaults(
            "This is an urgent task that needs immediate attention"
        )
        
        assert defaults['priority'] == 'Urgent'
    
    def test_suggest_task_defaults_work_category(self):
        """Test suggesting task defaults for work category."""
        defaults = IntelligentDefaultsHelper.suggest_task_defaults(
            "Complete the quarterly report for the office"
        )
        
        assert defaults['category'] == 'Work'
    
    def test_suggest_task_defaults_due_date(self):
        """Test suggesting task defaults with due date."""
        defaults = IntelligentDefaultsHelper.suggest_task_defaults(
            "Finish this task tomorrow"
        )
        
        assert defaults['due_date'] is not None
        # Should be tomorrow's date
        from datetime import datetime, timedelta
        expected_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        assert defaults['due_date'] == expected_date
    
    def test_suggest_task_defaults_tags(self):
        """Test suggesting task defaults with tags."""
        defaults = IntelligentDefaultsHelper.suggest_task_defaults(
            "Review the code changes for the urgent bug fix"
        )
        
        assert 'urgent' in defaults['tags']
        assert 'review' in defaults['tags']
    
    def test_suggest_habit_defaults_daily(self):
        """Test suggesting habit defaults for daily habits."""
        defaults = IntelligentDefaultsHelper.suggest_habit_defaults(
            "Exercise every day in the morning"
        )
        
        assert defaults['frequency'] == 'daily'
        assert defaults['time_of_day'] == 'morning'
        assert defaults['category'] == 'Health'
    
    def test_suggest_reminder_defaults_high_priority(self):
        """Test suggesting reminder defaults for high priority tasks."""
        task_data = {
            'priority': 'High',
            'due_date': '2024-01-15',
            'description': 'Important task'
        }
        
        defaults = IntelligentDefaultsHelper.suggest_reminder_defaults(task_data)
        
        assert defaults['timing'] == '2_hours_before'
        assert 'Important task' in defaults['message']
    
    def test_suggest_filter_defaults_overdue_context(self):
        """Test suggesting filter defaults for overdue context."""
        user_context = {'current_context': 'overdue_tasks'}
        
        defaults = IntelligentDefaultsHelper.suggest_filter_defaults(user_context)
        
        assert defaults['status'] == 'overdue'
        assert defaults['sort_by'] == 'due_date'
        assert defaults['sort_order'] == 'asc'


class TestEnhancedProgressiveDisclosureBuilder:
    """Test the enhanced ProgressiveDisclosureBuilder class."""
    
    def test_build_smart_disclosure_keyboard_task(self):
        """Test building smart disclosure keyboard for tasks."""
        task_data = {
            'id': 123,
            'description': 'Test task',
            'status': 'Todo',
            'priority': 'Medium'
        }
        
        keyboard = ProgressiveDisclosureBuilder.build_smart_disclosure_keyboard(
            'task', 123, task_data
        )
        
        assert keyboard is not None
        assert isinstance(keyboard, InlineKeyboardMarkup)
    
    def test_build_smart_disclosure_keyboard_client(self):
        """Test building smart disclosure keyboard for clients."""
        client_data = {
            'id': 456,
            'name': 'Test Client',
            'email': 'test@example.com'
        }
        
        keyboard = ProgressiveDisclosureBuilder.build_smart_disclosure_keyboard(
            'client', 456, client_data
        )
        
        assert keyboard is not None
        assert isinstance(keyboard, InlineKeyboardMarkup)
    
    def test_calculate_entity_complexity_simple(self):
        """Test calculating complexity for simple entity."""
        simple_data = {
            'description': 'Simple task'
        }
        
        complexity = ProgressiveDisclosureBuilder._calculate_entity_complexity(simple_data)
        
        assert complexity < 0.3
        assert complexity >= 0.0
    
    def test_calculate_entity_complexity_complex(self):
        """Test calculating complexity for complex entity."""
        complex_data = {
            'description': 'Very complex task with many details and requirements',
            'subtasks': ['subtask1', 'subtask2'],
            'attachments': ['file1.pdf'],
            'comments': ['comment1'],
            'dependencies': ['dep1'],
            'time_entries': ['entry1'],
            'reminders': ['reminder1']
        }
        
        complexity = ProgressiveDisclosureBuilder._calculate_entity_complexity(complex_data)
        
        assert complexity > 0.7
        assert complexity <= 1.0


class TestEnhancedErrorRecoveryHelper:
    """Test the enhanced ErrorRecoveryHelper class."""
    
    def test_build_error_recovery_keyboard_validation(self):
        """Test building error recovery keyboard for validation errors."""
        context = {'action': 'add_task', 'user_level': 'beginner'}
        
        keyboard = ErrorRecoveryHelper.build_error_recovery_keyboard(
            'validation_error', context
        )
        
        assert keyboard is not None
        button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert any('Try Again' in text for text in button_texts)
        assert any('Show Examples' in text for text in button_texts)
        assert any('Quick Add' in text for text in button_texts)
    
    def test_build_error_recovery_keyboard_database(self):
        """Test building error recovery keyboard for database errors."""
        keyboard = ErrorRecoveryHelper.build_error_recovery_keyboard(
            'database_error', {}
        )
        
        assert keyboard is not None
        button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert any('Retry' in text for text in button_texts)
        assert any('Check Storage' in text for text in button_texts)
        assert any('Emergency Mode' in text for text in button_texts)
    
    def test_provide_contextual_help_validation(self):
        """Test providing contextual help for validation errors."""
        error_context = {
            'type': 'validation_error',
            'message': 'Invalid task description',
            'user_level': 'beginner',
            'action': 'add_task'
        }
        
        help_message = ErrorRecoveryHelper.provide_contextual_help(error_context)
        
        assert 'Validation Error' in help_message
        assert 'Example' in help_message
        assert 'Tip' in help_message
    
    def test_provide_contextual_help_not_found(self):
        """Test providing contextual help for not found errors."""
        error_context = {
            'type': 'not_found_error',
            'entity_type': 'task',
            'search_term': 'nonexistent'
        }
        
        help_message = ErrorRecoveryHelper.provide_contextual_help(error_context)
        
        assert 'Task Not Found' in help_message
        assert 'nonexistent' in help_message
        assert 'Try these alternatives' in help_message
    
    def test_provide_contextual_help_network(self):
        """Test providing contextual help for network errors."""
        error_context = {
            'type': 'network_error',
            'message': 'Connection failed'
        }
        
        help_message = ErrorRecoveryHelper.provide_contextual_help(error_context)
        
        assert 'Network Connection Issue' in help_message
        assert 'Troubleshooting steps' in help_message
        assert 'Check your internet connection' in help_message


class TestEnhancedUXIntegration:
    """Integration tests for the enhanced UX system."""
    
    def test_smart_suggestions_with_defaults_integration(self):
        """Test integration between smart suggestions and intelligent defaults."""
        # Create a task with smart defaults
        task_input = "Urgent work meeting tomorrow to discuss quarterly report"
        defaults = IntelligentDefaultsHelper.suggest_task_defaults(task_input)
        
        # Get suggestions for task view context
        task_data = {
            'id': 123,
            'description': task_input,
            'priority': defaults['priority'],
            'category': defaults['category'],
            'due_date': defaults['due_date']
        }
        
        suggestions = SmartSuggestionsHelper.suggest_task_improvements(task_data)
        
        # Should have suggestions based on the defaults
        assert len(suggestions) > 0
        assert defaults['priority'] == 'Urgent'
        assert defaults['category'] == 'Work'
        assert defaults['due_date'] is not None
    
    def test_progressive_disclosure_with_smart_suggestions(self):
        """Test integration between progressive disclosure and smart suggestions."""
        task_data = {
            'id': 123,
            'description': 'Complex task with many details and requirements that need to be broken down into smaller manageable pieces for better organization and tracking',
            'status': 'Todo',
            'priority': 'Medium',
            'attachments': ['file1.pdf']
        }
        
        # Build smart disclosure keyboard
        keyboard = ProgressiveDisclosureBuilder.build_smart_disclosure_keyboard(
            'task', 123, task_data
        )
        
        # Get task improvements
        improvements = SmartSuggestionsHelper.suggest_task_improvements(task_data)
        
        # Both should work together
        assert keyboard is not None
        assert len(improvements) > 0
        
        # Complex task should have subtask suggestions
        subtask_suggestion = next((s for s in improvements if s['type'] == 'subtasks'), None)
        assert subtask_suggestion is not None
    
    def test_error_recovery_with_smart_suggestions(self):
        """Test integration between error recovery and smart suggestions."""
        error_context = {
            'type': 'validation_error',
            'message': 'Invalid task format',
            'action': 'add_task',
            'user_level': 'beginner'
        }
        
        # Get contextual help
        help_message = ErrorRecoveryHelper.provide_contextual_help(error_context)
        
        # Get recovery keyboard
        keyboard = ErrorRecoveryHelper.build_error_recovery_keyboard(
            'validation_error', error_context
        )
        
        # Both should provide helpful information
        assert 'Example' in help_message
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0 