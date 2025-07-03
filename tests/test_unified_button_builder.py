"""
Tests for the Unified Button Builder system.

This module tests the new unified button builder that consolidates
repetitive keyboard building patterns across the LarryBot2 codebase.
"""

import pytest
from unittest.mock import Mock, patch
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from larrybot.utils.enhanced_ux_helpers import (
    UnifiedButtonBuilder,
    ContextAwareButtonBuilder,
    ProgressiveDisclosureBuilder,
    ButtonType,
    ActionType
)


class TestUnifiedButtonBuilder:
    """Test the UnifiedButtonBuilder class."""
    
    def test_create_button_basic(self):
        """Test basic button creation."""
        button = UnifiedButtonBuilder.create_button(
            text="Test Button",
            callback_data="test_callback"
        )
        
        assert isinstance(button, InlineKeyboardButton)
        assert button.text == "🔵 Test Button"
        assert button.callback_data == "test_callback"
    
    def test_create_button_with_custom_emoji(self):
        """Test button creation with custom emoji."""
        button = UnifiedButtonBuilder.create_button(
            text="Custom Button",
            callback_data="custom_callback",
            custom_emoji="🚀"
        )
        
        assert button.text == "🚀 Custom Button"
    
    def test_create_button_with_existing_emoji(self):
        """Test button creation when text already has emoji."""
        button = UnifiedButtonBuilder.create_button(
            text="✅ Already Done",
            callback_data="done_callback"
        )
        
        assert button.text == "✅ Already Done"  # Should not add duplicate emoji
    
    def test_create_action_button(self):
        """Test action button creation."""
        button = UnifiedButtonBuilder.create_action_button(
            action_type=ActionType.VIEW,
            entity_id=123,
            entity_type="task"
        )
        
        assert button.text == "👁️ View"
        assert button.callback_data == "task_view:123"
    
    def test_create_action_button_with_custom_text(self):
        """Test action button creation with custom text."""
        button = UnifiedButtonBuilder.create_action_button(
            action_type=ActionType.EDIT,
            entity_id=456,
            entity_type="client",
            custom_text="Modify"
        )
        
        assert button.text == "✏️ Modify"
        assert button.callback_data == "client_edit:456"
    
    def test_build_entity_keyboard_basic(self):
        """Test basic entity keyboard building."""
        keyboard = UnifiedButtonBuilder.build_entity_keyboard(
            entity_id=789,
            entity_type="task",
            available_actions=[ActionType.VIEW, ActionType.EDIT, ActionType.DELETE]
        )
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 3
        
        # Check button texts
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "👁️ View" in button_texts
        assert "✏️ Edit" in button_texts
        assert "🗑️ Delete" in button_texts
    
    def test_build_entity_keyboard_with_status_filtering(self):
        """Test entity keyboard with status-based button filtering."""
        keyboard = UnifiedButtonBuilder.build_entity_keyboard(
            entity_id=123,
            entity_type="task",
            available_actions=[ActionType.VIEW, ActionType.COMPLETE, ActionType.EDIT],
            entity_status="Done"
        )
        
        # Should not show complete or edit buttons for done tasks
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "👁️ View" in button_texts
        assert "✅ Done" not in button_texts
        assert "✏️ Edit" not in button_texts
    
    def test_build_entity_keyboard_with_custom_actions(self):
        """Test entity keyboard with custom actions."""
        custom_actions = [
            {
                "text": "Custom Action",
                "callback_data": "custom_action:123",
                "type": ButtonType.WARNING,
                "emoji": "⚠️"
            }
        ]
        
        keyboard = UnifiedButtonBuilder.build_entity_keyboard(
            entity_id=123,
            entity_type="task",
            available_actions=[ActionType.VIEW],
            custom_actions=custom_actions
        )
        
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "👁️ View" in button_texts
        assert "⚠️ Custom Action" in button_texts
    
    def test_build_list_keyboard(self):
        """Test list keyboard building."""
        items = [
            {"id": 1, "name": "Task 1"},
            {"id": 2, "name": "Task 2"},
            {"id": 3, "name": "Task 3"}
        ]
        
        keyboard = UnifiedButtonBuilder.build_list_keyboard(
            items=items,
            item_type="task",
            max_items=2
        )
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Should have 2 item buttons + 1 navigation row
        assert len(keyboard.inline_keyboard) == 3
        
        # Check navigation buttons
        nav_buttons = keyboard.inline_keyboard[2]
        nav_texts = [btn.text for btn in nav_buttons]
        assert "🔄 Refresh" in nav_texts
        assert "🏠 Main Menu" in nav_texts
    
    def test_build_list_keyboard_without_navigation(self):
        """Test list keyboard without navigation buttons."""
        items = [{"id": 1, "name": "Task 1"}]
        
        keyboard = UnifiedButtonBuilder.build_list_keyboard(
            items=items,
            item_type="task",
            show_navigation=False
        )
        
        # Should only have item buttons, no navigation
        assert len(keyboard.inline_keyboard) == 1
    
    def test_build_task_keyboard_basic(self):
        """Test basic task keyboard building."""
        keyboard = UnifiedButtonBuilder.build_task_keyboard(
            task_id=123,
            status="Todo"
        )
        
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "👁️ View" in button_texts
        assert "✅ Done" in button_texts
        assert "✏️ Edit" in button_texts
        assert "🗑️ Delete" in button_texts
    
    def test_build_task_keyboard_completed_task(self):
        """Test task keyboard for completed tasks."""
        keyboard = UnifiedButtonBuilder.build_task_keyboard(
            task_id=123,
            status="Done"
        )
        
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "👁️ View" in button_texts
        assert "✅ Done" not in button_texts  # Should not show for completed tasks
        assert "✏️ Edit" not in button_texts  # Should not show for completed tasks
        assert "🗑️ Delete" in button_texts
    
    def test_build_task_keyboard_with_time_tracking(self):
        """Test task keyboard with time tracking buttons."""
        keyboard = UnifiedButtonBuilder.build_task_keyboard(
            task_id=123,
            status="Todo",
            show_time_tracking=True,
            is_time_tracking=True
        )
        
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "⏹️ Stop Timer" in button_texts
        
        # Test when not tracking
        keyboard2 = UnifiedButtonBuilder.build_task_keyboard(
            task_id=123,
            status="Todo",
            show_time_tracking=True,
            is_time_tracking=False
        )
        
        button_texts2 = [btn.text for btn in keyboard2.inline_keyboard[0]]
        assert "▶️ Start Timer" in button_texts2
    
    def test_build_analytics_keyboard(self):
        """Test analytics keyboard building."""
        keyboard = UnifiedButtonBuilder.build_analytics_keyboard()
        
        button_texts = []
        for row in keyboard.inline_keyboard:
            button_texts.extend([btn.text for btn in row])
        
        assert "📊 Basic" in button_texts
        assert "📊 Detailed" in button_texts
        assert "📊 Advanced" in button_texts
        assert "⚙️ Custom Days" in button_texts
        assert "🏠 Main Menu" in button_texts
    
    def test_build_filter_keyboard(self):
        """Test filter keyboard building."""
        keyboard = UnifiedButtonBuilder.build_filter_keyboard()
        
        button_texts = []
        for row in keyboard.inline_keyboard:
            button_texts.extend([btn.text for btn in row])
        
        assert "🔍 Status" in button_texts
        assert "🔍 Priority" in button_texts
        assert "🔍 Category" in button_texts
        assert "🔍 Tags" in button_texts
        assert "⚙️ Advanced" in button_texts
        assert "🗑️ Clear Filters" in button_texts
        assert "🏠 Main Menu" in button_texts
    
    def test_build_confirmation_keyboard(self):
        """Test confirmation keyboard building."""
        keyboard = UnifiedButtonBuilder.build_confirmation_keyboard(
            action="delete",
            entity_id=123,
            entity_type="task",
            entity_name="Test Task"
        )
        
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2
        
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "⚠️ Confirm Delete" in button_texts
        assert "❌ Cancel" in button_texts
        
        # Check callback data
        callback_data = [btn.callback_data for btn in keyboard.inline_keyboard[0]]
        assert "task_delete_confirm:123" in callback_data
        assert "task_delete_cancel:123" in callback_data


class TestContextAwareButtonBuilder:
    """Test the ContextAwareButtonBuilder class."""
    
    def test_build_smart_task_keyboard_basic(self):
        """Test basic smart task keyboard building."""
        task_data = {
            "status": "Todo",
            "priority": "Medium",
            "due_date": None
        }
        
        keyboard = ContextAwareButtonBuilder.build_smart_task_keyboard(
            task_id=123,
            task_data=task_data
        )
        
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "👁️ View" in button_texts
        assert "✅ Done" in button_texts
        assert "✏️ Edit" in button_texts
        assert "🗑️ Delete" in button_texts
    
    def test_build_smart_task_keyboard_with_time_tracking(self):
        """Test smart task keyboard with time tracking context."""
        task_data = {
            "status": "In Progress",
            "priority": "Medium",
            "time_tracking_active": True
        }
        
        keyboard = ContextAwareButtonBuilder.build_smart_task_keyboard(
            task_id=123,
            task_data=task_data
        )
        
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "⏹️ Stop Timer" in button_texts
        
        # Test when not tracking
        task_data["time_tracking_active"] = False
        keyboard2 = ContextAwareButtonBuilder.build_smart_task_keyboard(
            task_id=123,
            task_data=task_data
        )
        
        button_texts2 = [btn.text for btn in keyboard2.inline_keyboard[0]]
        assert "▶️ Start Timer" in button_texts2
    
    def test_build_smart_task_keyboard_high_priority(self):
        """Test smart task keyboard for high priority tasks."""
        task_data = {
            "status": "Todo",
            "priority": "High",
            "due_date": "2025-01-15"
        }
        
        keyboard = ContextAwareButtonBuilder.build_smart_task_keyboard(
            task_id=123,
            task_data=task_data
        )
        
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "📊 Time Summary" in button_texts
        assert "📅 Extend Due Date" in button_texts
    
    def test_build_smart_task_keyboard_completed_task(self):
        """Test smart task keyboard for completed tasks."""
        task_data = {
            "status": "Done",
            "priority": "Medium",
            "due_date": None
        }
        
        keyboard = ContextAwareButtonBuilder.build_smart_task_keyboard(
            task_id=123,
            task_data=task_data
        )
        
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "👁️ View" in button_texts
        assert "✅ Done" not in button_texts  # Should not show for completed tasks
        assert "✏️ Edit" not in button_texts  # Should not show for completed tasks
        assert "🗑️ Delete" in button_texts


class TestProgressiveDisclosureBuilder:
    """Test the ProgressiveDisclosureBuilder class."""
    
    def test_build_progressive_task_keyboard_level_1(self):
        """Test progressive task keyboard at level 1."""
        task_data = {"status": "Todo"}
        
        keyboard = ProgressiveDisclosureBuilder.build_progressive_task_keyboard(
            task_id=123,
            task_data=task_data,
            disclosure_level=1
        )
        
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "👁️ View" in button_texts
        assert "✅ Done" in button_texts
        assert "🗑️ Delete" in button_texts
        assert "➕ More Options" in button_texts
        assert "✏️ Edit" not in button_texts  # Should not show at level 1
    
    def test_build_progressive_task_keyboard_level_2(self):
        """Test progressive task keyboard at level 2."""
        task_data = {"status": "Todo"}
        
        keyboard = ProgressiveDisclosureBuilder.build_progressive_task_keyboard(
            task_id=123,
            task_data=task_data,
            disclosure_level=2
        )
        
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "👁️ View" in button_texts
        assert "✅ Done" in button_texts
        assert "🗑️ Delete" in button_texts
        assert "✏️ Edit" in button_texts  # Should show at level 2
        assert "⏱️ Time Tracking" in button_texts  # Should show at level 2
        assert "➕ More Options" in button_texts
    
    def test_build_progressive_task_keyboard_level_3(self):
        """Test progressive task keyboard at level 3."""
        task_data = {"status": "Todo"}
        
        keyboard = ProgressiveDisclosureBuilder.build_progressive_task_keyboard(
            task_id=123,
            task_data=task_data,
            disclosure_level=3
        )
        
        button_texts = [btn.text for btn in keyboard.inline_keyboard[0]]
        assert "👁️ View" in button_texts
        assert "✅ Done" in button_texts
        assert "🗑️ Delete" in button_texts
        assert "✏️ Edit" in button_texts
        assert "⏱️ Time Tracking" in button_texts
        assert "📊 Analytics" in button_texts  # Should show at level 3
        assert "🔗 Dependencies" in button_texts  # Should show at level 3
        assert "➕ More Options" not in button_texts  # Should not show at max level


class TestButtonTypeEnum:
    """Test the ButtonType enum."""
    
    def test_button_type_values(self):
        """Test that all button types have expected values."""
        assert ButtonType.PRIMARY.value == "primary"
        assert ButtonType.SECONDARY.value == "secondary"
        assert ButtonType.SUCCESS.value == "success"
        assert ButtonType.DANGER.value == "danger"
        assert ButtonType.WARNING.value == "warning"
        assert ButtonType.INFO.value == "info"
    
    def test_button_styles_exist(self):
        """Test that all button types have corresponding styles."""
        for button_type in ButtonType:
            assert button_type in UnifiedButtonBuilder.BUTTON_STYLES


class TestActionTypeEnum:
    """Test the ActionType enum."""
    
    def test_action_type_values(self):
        """Test that all action types have expected values."""
        assert ActionType.VIEW.value == "view"
        assert ActionType.EDIT.value == "edit"
        assert ActionType.DELETE.value == "delete"
        assert ActionType.COMPLETE.value == "complete"
        assert ActionType.START.value == "start"
        assert ActionType.STOP.value == "stop"
        assert ActionType.REFRESH.value == "refresh"
        assert ActionType.NAVIGATE.value == "navigate"
        assert ActionType.CONFIRM.value == "confirm"
        assert ActionType.CANCEL.value == "cancel"
    
    def test_action_templates_exist(self):
        """Test that all action types have corresponding templates."""
        for action_type in ActionType:
            assert action_type in UnifiedButtonBuilder.ACTION_TEMPLATES


class TestUnifiedButtonBuilderIntegration:
    """Integration tests for the unified button builder."""
    
    def test_backward_compatibility_with_existing_patterns(self):
        """Test that the unified builder produces similar results to existing patterns."""
        # Test task keyboard
        keyboard = UnifiedButtonBuilder.build_task_keyboard(
            task_id=123,
            status="Todo",
            show_edit=True
        )
        
        # Should have the same basic structure as existing task keyboards
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) >= 3  # View, Done, Edit, Delete
        
        # Check that callback data follows expected pattern
        callback_data = [btn.callback_data for btn in keyboard.inline_keyboard[0]]
        assert any("task_view:123" in data for data in callback_data)
        assert any("task_complete:123" in data for data in callback_data)
        assert any("task_edit:123" in data for data in callback_data)
        assert any("task_delete:123" in data for data in callback_data)
    
    def test_consistent_styling_across_builders(self):
        """Test that all builders produce consistent styling."""
        # Test that all builders use the same button creation method
        task_keyboard = UnifiedButtonBuilder.build_task_keyboard(task_id=1, status="Todo")
        smart_keyboard = ContextAwareButtonBuilder.build_smart_task_keyboard(
            task_id=1, 
            task_data={"status": "Todo"}
        )
        progressive_keyboard = ProgressiveDisclosureBuilder.build_progressive_task_keyboard(
            task_id=1,
            task_data={"status": "Todo"},
            disclosure_level=1
        )
        
        # All should produce valid keyboards
        assert isinstance(task_keyboard, InlineKeyboardMarkup)
        assert isinstance(smart_keyboard, InlineKeyboardMarkup)
        assert isinstance(progressive_keyboard, InlineKeyboardMarkup)
        
        # All should have consistent button styling
        for keyboard in [task_keyboard, smart_keyboard, progressive_keyboard]:
            for row in keyboard.inline_keyboard:
                for button in row:
                    assert isinstance(button, InlineKeyboardButton)
                    assert button.text is not None
                    assert button.callback_data is not None 