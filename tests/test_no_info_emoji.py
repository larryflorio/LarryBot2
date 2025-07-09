#!/usr/bin/env python3
"""
Test suite to validate that no  emoji appears in bot output.

This test suite ensures that after removing the  emoji from the codebase,
no instances of it appear in actual bot responses, messages, or button text.
"""

import pytest
import re
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from larrybot.utils.ux_helpers import MessageFormatter
from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType, ActionType
from larrybot.plugins.tasks import register as register_tasks
from larrybot.plugins.calendar import register as register_calendar
from larrybot.plugins.client import register as register_client
from larrybot.plugins.habit import register as register_habit
from larrybot.plugins.file_attachments import register as register_file_attachments


class TestNoInfoEmojiInOutput:
    """Test that no ℹ️ emoji appears in any bot output."""
    
    def test_format_info_message_no_info_emoji(self):
        """Test that format_info_message doesn't include ℹ️ emoji."""
        test_cases = [
            {
                'title': '📋 No Tasks Found',
                'details': {'Status': 'No tasks available', 'Action': 'Use /add to create tasks'}
            },
            {
                'title': '📅 Calendar Not Connected',
                'details': {'Status': 'No calendar connected', 'Action': 'Use /connect_google'}
            },
            {
                'title': '🔍 Search Results',
                'details': {'Query': 'test', 'Results': '5 found'}
            },
            {
                'title': '✅ Task Completed',
                'details': {'Task': 'Test task', 'Status': 'Done'}
            }
        ]
    
        for case in test_cases:
            result = MessageFormatter.format_info_message(case['title'], case['details'])
    
            # Should not contain ℹ️ emoji (the old info emoji)
            assert 'ℹ️' not in result, f"format_info_message contains ℹ️: {result}"
            
            # Should still contain the original title
            assert case['title'] in result, f"Original title missing: {case['title']}"
            
            # Should contain all details
            for key, value in case['details'].items():
                assert str(key) in result, f"Detail key missing: {key}"
                # Handle Markdown escaping - check if the value appears in the result (with or without escaping)
                value_str = str(value)
                if value_str in result or value_str.replace('_', '\\_') in result:
                    continue  # Value found (either escaped or unescaped)
                else:
                    pytest.fail(f"Detail value missing: {value_str} (not found in: {result})")
    
    def test_button_creation_no_info_emoji(self):
        """Test that button creation doesn't include ℹ️ emoji."""
        test_cases = [
            {
                'text': 'View Tasks',
                'callback_data': 'tasks_list',
                'button_type': ButtonType.INFO
            },
            {
                'text': 'Refresh',
                'callback_data': 'refresh',
                'button_type': ButtonType.INFO
            },
            {
                'text': 'Analytics',
                'callback_data': 'analytics',
                'button_type': ButtonType.INFO
            },
            {
                'text': 'Back',
                'callback_data': 'back',
                'button_type': ButtonType.INFO
            }
        ]
        
        for case in test_cases:
            button = UnifiedButtonBuilder.create_button(
                text=case['text'],
                callback_data=case['callback_data'],
                button_type=case['button_type']
            )
            
            # Button text should not contain ℹ️ emoji (the old info emoji)
            assert 'ℹ️' not in button.text, f"Button text contains ℹ️: {button.text}"
            
            # Should still contain the original text
            assert case['text'] in button.text, f"Original text missing: {case['text']}"
    
    def test_action_button_creation_no_info_emoji(self):
        """Test that action button creation doesn't include ℹ️ emoji."""
        test_cases = [
            {
                'action_type': ActionType.VIEW,
                'entity_id': 1,
                'entity_type': 'task'
            },
            {
                'action_type': ActionType.REFRESH,
                'entity_id': 'list',
                'entity_type': 'task'
            }
        ]
        
        for case in test_cases:
            button = UnifiedButtonBuilder.create_action_button(
                action_type=case['action_type'],
                entity_id=case['entity_id'],
                entity_type=case['entity_type']
            )
            
            # Button text should not contain ℹ️ emoji (the old info emoji)
            assert 'ℹ️' not in button.text, f"Action button text contains ℹ️: {button.text}"
    
    def test_keyboard_building_no_info_emoji(self):
        """Test that keyboard building doesn't include ℹ️ emoji."""
        # Test task keyboard
        task_keyboard = UnifiedButtonBuilder.build_task_keyboard(
            task_id=1,
            status='Todo',
            show_edit=True
        )
        
        for row in task_keyboard.inline_keyboard:
            for button in row:
                assert 'ℹ️' not in button.text, f"Task keyboard button contains ℹ️: {button.text}"
        
        # Test analytics keyboard
        analytics_keyboard = UnifiedButtonBuilder.build_analytics_keyboard()
        
        for row in analytics_keyboard.inline_keyboard:
            for button in row:
                assert 'ℹ️' not in button.text, f"Analytics keyboard button contains ℹ️: {button.text}"
    
    def test_message_formatter_no_info_emoji(self):
        """Test that MessageFormatter methods don't include ℹ️ emoji."""
        # Test error message formatting
        error_msg = MessageFormatter.format_error_message(
            'Test error',
            'Test suggestion'
        )
        assert 'ℹ️' not in error_msg, f"Error message contains ℹ️: {error_msg}"
        
        # Test success message formatting
        success_msg = MessageFormatter.format_success_message(
            'Test success',
            {'Detail': 'Test detail'}
        )
        assert 'ℹ️' not in success_msg, f"Success message contains ℹ️: {success_msg}"
        
        # Test warning message formatting
        warning_msg = MessageFormatter.format_warning_message(
            'Test warning',
            {'Detail': 'Test detail'}
        )
        assert 'ℹ️' not in warning_msg, f"Warning message contains ℹ️: {warning_msg}"
    
    def test_plugin_message_generation_no_info_emoji(self):
        """Test that plugin message generation doesn't include ℹ️ emoji."""
        # Mock update and context for testing
        mock_update = Mock()
        mock_context = Mock()
        mock_context.args = []
        
        # Test task plugin messages
        with patch('larrybot.plugins.tasks.get_session') as mock_session:
            mock_session.return_value.__next__.return_value = Mock()
            
            # This would normally call format_info_message internally
            # We test the actual message formatting instead
            test_message = MessageFormatter.format_info_message('📋 No Tasks Found', {
                'Status': 'No tasks available',
                'Action': 'Use /add to create tasks'
            })
            assert 'ℹ️' not in test_message, f"Task plugin message contains ℹ️: {test_message}"
    
    def test_button_type_info_configuration(self):
        """Test that ButtonType.INFO configuration doesn't include ℹ️ emoji."""
        # Check the button styles configuration
        info_style = UnifiedButtonBuilder.BUTTON_STYLES[ButtonType.INFO]
        
        # The emoji should not be ℹ️ (the old info emoji)
        assert info_style['emoji'] != 'ℹ️', f"ButtonType.INFO still uses ℹ️ emoji: {info_style['emoji']}"
        
        # Should still have an emoji for consistency
        assert 'emoji' in info_style, "ButtonType.INFO missing emoji configuration"

    def test_format_task_list_overdue_detection(self):
        """Test that format_task_list correctly shows overdue status."""
        from datetime import datetime, timedelta
        from larrybot.utils.basic_datetime import get_current_datetime
        
        # Create test tasks
        current_time = get_current_datetime()
        past_date = current_time - timedelta(days=1)  # Yesterday (overdue)
        future_date = current_time + timedelta(days=1)  # Tomorrow (not overdue)
        
        test_tasks = [
            {
                'id': 1,
                'description': 'Overdue task',
                'priority': 'High',
                'due_date': past_date
            },
            {
                'id': 2,
                'description': 'Future task',
                'priority': 'Medium',
                'due_date': future_date
            },
            {
                'id': 3,
                'description': 'No due date task',
                'priority': 'Low'
            }
        ]
        
        # Format the task list
        result = MessageFormatter.format_task_list(test_tasks, 'Test Tasks')
        
        # Check that overdue task shows overdue indicator
        assert '❗ *OVERDUE*' in result, "Overdue task should show overdue indicator"
        assert 'Overdue task' in result, "Overdue task description should be present"
        
        # Check that future task doesn't show overdue indicator
        assert 'Future task' in result, "Future task description should be present"
        # The future task should have a due date but no overdue indicator
        future_task_line = [line for line in result.split('\n') if 'Future task' in line][0]
        assert '❗ *OVERDUE*' not in future_task_line, "Future task should not show overdue indicator"
        
        # Check that no due date task doesn't show overdue indicator
        assert 'No due date task' in result, "No due date task description should be present"
        no_due_task_line = [line for line in result.split('\n') if 'No due date task' in line][0]
        assert '❗ *OVERDUE*' not in no_due_task_line, "Task without due date should not show overdue indicator"
    
    def test_action_templates_no_info_emoji(self):
        """Test that action templates don't include ℹ️ emoji."""
        # Check refresh action template
        refresh_template = UnifiedButtonBuilder.ACTION_TEMPLATES[ActionType.REFRESH]
        
        # The emoji should not be ℹ️ (the old info emoji)
        assert refresh_template['emoji'] != 'ℹ️', f"ActionType.REFRESH still uses ℹ️ emoji: {refresh_template['emoji']}"
        
        # Should still have an emoji for consistency
        assert 'emoji' in refresh_template, "ActionType.REFRESH missing emoji configuration"
    
    def test_comprehensive_message_scan(self):
        """Comprehensive test to scan all message types for ℹ️ emoji."""
        # Test various message titles that are commonly used
        common_titles = [
            '📋 No Tasks Found',
            '📅 Calendar Not Connected',
            '🔍 Search Results',
            '✅ Task Completed',
            '❌ Task creation cancelled',
            '✏️ Edit Options',
            '📊 Analytics Report',
            '🔄 Refresh Complete',
            '📎 File Attachment Required',
            '⏰ Reminder Set',
            '👥 Client Added',
            '🔄 Habit Updated'
        ]
    
        for title in common_titles:
            result = MessageFormatter.format_info_message(title, {'Test': 'Detail'})
            assert 'ℹ️' not in result, f"Message with title '{title}' contains ℹ️: {result}"
    
    def test_button_text_patterns_no_info_emoji(self):
        """Test that common button text patterns don't include ℹ️ emoji."""
        common_button_texts = [
            'View Tasks',
            'Refresh',
            'Analytics',
            'Back',
            'Main Menu',
            'Edit',
            'Delete',
            'Complete',
            'Add Task',
            'Settings'
        ]
        
        for text in common_button_texts:
            button = UnifiedButtonBuilder.create_button(
                text=text,
                callback_data=f'test_{text.lower().replace(" ", "_")}',
                button_type=ButtonType.INFO
            )
            assert 'ℹ️' not in button.text, f"Button text '{text}' contains ℹ️: {button.text}"


class TestInfoEmojiRemovalValidation:
    """Additional validation tests for ℹ️ emoji removal."""
    
    def test_no_info_emoji_in_codebase(self):
        """Test that no literal ℹ️ characters exist in the codebase."""
        import os
        import glob
        
        # Get all Python files in the larrybot directory
        python_files = glob.glob('larrybot/**/*.py', recursive=True)
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    if 'ℹ️' in line:
                        pytest.fail(f"Literal ℹ️ found in {file_path}:{i}: {line.strip()}")
                        
            except Exception as e:
                pytest.fail(f"Error reading {file_path}: {e}")
    
    def test_no_info_emoji_in_tests(self):
        """Test that no literal ℹ️ characters exist in test files (excluding this test file)."""
        import os
        import glob
        
        # Get all Python files in the tests directory
        test_files = glob.glob('tests/**/*.py', recursive=True)
        
        for file_path in test_files:
            # Skip this test file since it intentionally contains ℹ️ in docstrings
            if 'test_no_info_emoji.py' in file_path:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    if 'ℹ️' in line:
                        pytest.fail(f"Literal ℹ️ found in test file {file_path}:{i}: {line.strip()}")
                        
            except Exception as e:
                pytest.fail(f"Error reading test file {file_path}: {e}")
    
    def test_button_type_info_consistency(self):
        """Test that all ButtonType.INFO usage is consistent."""
        # This test ensures that if we change ButtonType.INFO emoji,
        # all buttons using this type will be updated consistently
        
        # Create a test button with ButtonType.INFO
        button = UnifiedButtonBuilder.create_button(
            text='Test Button',
            callback_data='test',
            button_type=ButtonType.INFO
        )
        
        # Get the configured emoji for ButtonType.INFO
        info_style = UnifiedButtonBuilder.BUTTON_STYLES[ButtonType.INFO]
        expected_emoji = info_style['emoji']
        
        # The button should start with the expected emoji (if any)
        if expected_emoji:
            assert button.text.startswith(expected_emoji), f"Button should start with {expected_emoji}: {button.text}"
        else:
            # If no emoji is configured, the button should not have any emoji prefix
            assert not any(button.text.startswith(emoji) for emoji in ['ℹ️', '🔵', '⚪', '✅', '🗑️', '⚠️']), \
                f"Button should not have emoji prefix: {button.text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 