"""
Comprehensive UX helpers testing with edge cases and error scenarios.

This test suite targets the 44% coverage gap in larrybot/utils/ux_helpers.py
to achieve 80%+ coverage through comprehensive testing of all UX components.
"""

import pytest
from unittest.mock import Mock, patch
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from larrybot.utils.ux_helpers import (
    KeyboardBuilder, MessageFormatter, NavigationHelper, 
    ChartBuilder, AnalyticsFormatter
)


class TestKeyboardBuilderComprehensive:
    """Comprehensive keyboard builder testing with edge cases."""

    def test_build_task_keyboard_completed_task(self):
        """Test task keyboard for completed task."""
        keyboard = KeyboardBuilder.build_task_keyboard(123, "Done", show_edit=True)
        
        # Should not show Done button for completed tasks
        buttons = keyboard.inline_keyboard[0]
        button_texts = [btn.text for btn in buttons]
        assert "✅ Done" not in button_texts
        assert "🗑️ Delete" in button_texts

    def test_build_task_keyboard_incomplete_task(self):
        """Test task keyboard for incomplete task."""
        keyboard = KeyboardBuilder.build_task_keyboard(123, "Todo", show_edit=True)
        
        # Should show Done and Edit buttons for incomplete tasks
        buttons = keyboard.inline_keyboard[0]
        button_texts = [btn.text for btn in buttons]
        assert "✅ Done" in button_texts
        assert "✏️ Edit" in button_texts
        assert "🗑️ Delete" in button_texts

    def test_build_task_keyboard_hide_edit(self):
        """Test task keyboard with edit hidden."""
        keyboard = KeyboardBuilder.build_task_keyboard(123, "Todo", show_edit=False)
        
        # Should not show Edit button when show_edit=False
        buttons = keyboard.inline_keyboard[0]
        button_texts = [btn.text for btn in buttons]
        assert "✅ Done" in button_texts
        assert "✏️ Edit" not in button_texts
        assert "🗑️ Delete" in button_texts

    def test_build_client_keyboard(self):
        """Test client keyboard building."""
        keyboard = KeyboardBuilder.build_client_keyboard(123, "Test Client")
        
        buttons = keyboard.inline_keyboard[0]
        button_texts = [btn.text for btn in buttons]
        assert "📋 View Tasks" in button_texts
        assert "📊 Analytics" in button_texts
        assert "🗑️ Delete" in button_texts

    def test_build_habit_keyboard_not_completed(self):
        """Test habit keyboard for habit not completed today."""
        keyboard = KeyboardBuilder.build_habit_keyboard(123, "Test Habit", completed_today=False)
        
        buttons = keyboard.inline_keyboard[0]
        button_texts = [btn.text for btn in buttons]
        assert "✅ Complete" in button_texts
        assert "📊 Progress" in button_texts
        assert "🗑️ Delete" in button_texts

    def test_build_habit_keyboard_completed_today(self):
        """Test habit keyboard for habit completed today."""
        keyboard = KeyboardBuilder.build_habit_keyboard(123, "Test Habit", completed_today=True)
        
        buttons = keyboard.inline_keyboard[0]
        button_texts = [btn.text for btn in buttons]
        assert "✅ Complete" not in button_texts  # Should not show complete if already done
        assert "📊 Progress" in button_texts
        assert "🗑️ Delete" in button_texts

    def test_build_navigation_keyboard_all_options(self):
        """Test navigation keyboard with all options."""
        keyboard = KeyboardBuilder.build_navigation_keyboard(
            show_back=True, 
            show_main_menu=True,
            custom_buttons=[
                {"text": "Custom 1", "callback_data": "custom_1"},
                {"text": "Custom 2", "callback_data": "custom_2"}
            ]
        )
        # Should have custom buttons (each as a row) and navigation buttons
        assert len(keyboard.inline_keyboard) == 3
        custom_row_1 = keyboard.inline_keyboard[0]
        custom_row_2 = keyboard.inline_keyboard[1]
        nav_buttons = keyboard.inline_keyboard[2]
        assert custom_row_1[0].text == "Custom 1"
        assert custom_row_2[0].text == "Custom 2"
        assert nav_buttons[0].text == "⬅️ Back"
        assert nav_buttons[1].text == "🏠 Main Menu"

    def test_build_navigation_keyboard_no_options(self):
        """Test navigation keyboard with no options."""
        keyboard = KeyboardBuilder.build_navigation_keyboard(
            show_back=False, 
            show_main_menu=False
        )
        
        # Should have no navigation buttons
        assert len(keyboard.inline_keyboard) == 0

    def test_build_navigation_keyboard_only_custom(self):
        """Test navigation keyboard with only custom buttons."""
        keyboard = KeyboardBuilder.build_navigation_keyboard(
            show_back=False, 
            show_main_menu=False,
            custom_buttons=[
                {"text": "Custom 1", "callback_data": "custom_1"}
            ]
        )
        # Should have only custom button as a row
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 1
        assert keyboard.inline_keyboard[0][0].text == "Custom 1"

    def test_build_pagination_keyboard_first_page(self):
        """Test pagination keyboard for first page."""
        keyboard = KeyboardBuilder.build_pagination_keyboard(1, 5, "test_callback")
        
        # Should not have previous button on first page
        buttons = keyboard.inline_keyboard[0]
        assert len(buttons) == 2
        assert buttons[0].text == "1/5"
        assert buttons[1].text == "➡️"

    def test_build_pagination_keyboard_last_page(self):
        """Test pagination keyboard for last page."""
        keyboard = KeyboardBuilder.build_pagination_keyboard(5, 5, "test_callback")
        
        # Should not have next button on last page
        buttons = keyboard.inline_keyboard[0]
        assert len(buttons) == 2
        assert buttons[0].text == "⬅️"
        assert buttons[1].text == "5/5"

    def test_build_pagination_keyboard_middle_page(self):
        """Test pagination keyboard for middle page."""
        keyboard = KeyboardBuilder.build_pagination_keyboard(3, 5, "test_callback")
        
        # Should have both previous and next buttons
        buttons = keyboard.inline_keyboard[0]
        assert len(buttons) == 3
        assert buttons[0].text == "⬅️"
        assert buttons[1].text == "3/5"
        assert buttons[2].text == "➡️"

    def test_build_pagination_keyboard_single_page(self):
        """Test pagination keyboard for single page."""
        keyboard = KeyboardBuilder.build_pagination_keyboard(1, 1, "test_callback")
        
        # Should only show current page
        buttons = keyboard.inline_keyboard[0]
        assert len(buttons) == 1
        assert buttons[0].text == "1/1"

    def test_build_confirmation_keyboard(self):
        """Test confirmation keyboard building (destructive action)."""
        keyboard = KeyboardBuilder.build_confirmation_keyboard("delete", 123, "Test Item")
        # Should have confirm, cancel, and back buttons
        assert len(keyboard.inline_keyboard) == 2
        confirm_row = keyboard.inline_keyboard[0]
        back_row = keyboard.inline_keyboard[1]
        assert confirm_row[0].text == "✅ Confirm"
        assert confirm_row[1].text == "❌ Cancel"
        assert back_row[0].text == "⬅️ Back"

    def test_build_client_list_keyboard(self):
        """Test client list keyboard building."""
        keyboard = KeyboardBuilder.build_client_list_keyboard()
        
        # Should have navigation buttons
        assert len(keyboard.inline_keyboard) > 0

    def test_build_client_detail_keyboard(self):
        """Test client detail keyboard building."""
        keyboard = KeyboardBuilder.build_client_detail_keyboard(123, "Test Client")
        # Should have delete button in the second row
        all_button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "🗑️ Delete" in all_button_texts
        assert "📋 View Tasks" in all_button_texts
        assert "📊 Analytics" in all_button_texts

    def test_build_habit_list_keyboard(self):
        """Test habit list keyboard building."""
        keyboard = KeyboardBuilder.build_habit_list_keyboard()
        
        # Should have navigation buttons
        assert len(keyboard.inline_keyboard) > 0

    def test_build_habit_detail_keyboard(self):
        """Test habit detail keyboard building."""
        keyboard = KeyboardBuilder.build_habit_detail_keyboard(123, "Test Habit")
        all_button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "✅ Mark Done" in all_button_texts
        assert "📊 Progress" in all_button_texts
        assert "🗑️ Delete" in all_button_texts

    def test_build_reminder_list_keyboard(self):
        """Test reminder list keyboard building."""
        keyboard = KeyboardBuilder.build_reminder_list_keyboard()
        
        # Should have navigation buttons
        assert len(keyboard.inline_keyboard) > 0

    def test_build_reminder_action_keyboard(self):
        """Test reminder action keyboard building."""
        keyboard = KeyboardBuilder.build_reminder_action_keyboard(123, 456)
        all_button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "✅ Mark Done" in all_button_texts
        assert "⏰ Snooze 1h" in all_button_texts
        assert "🗑️ Delete Reminder" in all_button_texts

    def test_build_reminder_keyboard_active(self):
        """Test reminder keyboard for active reminder."""
        keyboard = KeyboardBuilder.build_reminder_keyboard(123, is_active=True)
        all_button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "✅ Complete" in all_button_texts
        assert "⏰ Snooze" in all_button_texts

    def test_build_reminder_keyboard_inactive(self):
        """Test reminder keyboard for inactive reminder."""
        keyboard = KeyboardBuilder.build_reminder_keyboard(123, is_active=False)
        
        buttons = keyboard.inline_keyboard[0]
        button_texts = [btn.text for btn in buttons]
        assert "🗑️ Delete" in button_texts

    def test_build_analytics_keyboard(self):
        """Test analytics keyboard building."""
        keyboard = KeyboardBuilder.build_analytics_keyboard()
        all_button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "📈 Detailed" in all_button_texts
        assert "📊 Productivity" in all_button_texts
        assert "⏰ Time Tracking" in all_button_texts
        assert "🎯 Performance" in all_button_texts
        assert "📅 Trends" in all_button_texts
        assert "📋 Reports" in all_button_texts
        assert "🔙 Back to Main" in all_button_texts

    def test_build_filter_keyboard(self):
        """Test filter keyboard building."""
        keyboard = KeyboardBuilder.build_filter_keyboard()
        all_button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "📅 Date Range" in all_button_texts
        assert "🎯 Priority" in all_button_texts
        assert "📋 Status" in all_button_texts
        assert "🏷️ Tags" in all_button_texts
        assert "📂 Category" in all_button_texts
        assert "⏰ Time Tracking" in all_button_texts
        assert "🔍 Advanced Search" in all_button_texts
        assert "💾 Save Filter" in all_button_texts
        assert "🔙 Back to Tasks" in all_button_texts

    def test_build_attachment_keyboard(self):
        """Test attachment keyboard building."""
        keyboard = KeyboardBuilder.build_attachment_keyboard(1, 2)
        all_button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "📝 Edit Description" in all_button_texts
        assert "📊 View Details" in all_button_texts
        assert "🗑️ Remove" in all_button_texts
        assert "📋 Task Details" in all_button_texts
        assert "🔙 Back to Attachments" in all_button_texts

    def test_build_attachments_list_keyboard(self):
        """Test attachments list keyboard building."""
        keyboard = KeyboardBuilder.build_attachments_list_keyboard(2, 5)
        all_button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "📊 Statistics" in all_button_texts
        assert "📝 Add Description" in all_button_texts
        assert "🗑️ Bulk Remove" in all_button_texts
        assert "📋 Export List" in all_button_texts
        assert "📎 Add New File" in all_button_texts
        assert "🔙 Back to Task" in all_button_texts

    def test_build_calendar_keyboard(self):
        """Test calendar keyboard building."""
        keyboard = KeyboardBuilder.build_calendar_keyboard()
        all_button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "📅 Today" in all_button_texts
        assert "📅 Week" in all_button_texts
        assert "📅 Month" in all_button_texts
        assert "📅 Upcoming" in all_button_texts
        assert "🔄 Sync" in all_button_texts
        assert "⚙️ Settings" in all_button_texts
        assert "🔙 Back to Main" in all_button_texts

    def test_build_bulk_operations_keyboard(self):
        """Test bulk operations keyboard building."""
        keyboard = KeyboardBuilder.build_bulk_operations_keyboard()
        all_button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "📋 Status" in all_button_texts
        assert "🎯 Priority" in all_button_texts
        assert "👥 Assign" in all_button_texts
        assert "🗑️ Delete" in all_button_texts
        assert "📊 Preview" in all_button_texts
        assert "💾 Save Selection" in all_button_texts
        assert "🔙 Back to Tasks" in all_button_texts


class TestMessageFormatterComprehensive:
    """Comprehensive message formatter testing."""

    def test_escape_markdown_basic(self):
        text = "Hello *world* and _italic_ text"
        escaped = MessageFormatter.escape_markdown(text)
        # Should escape * and _ with backslash
        assert "\\*" in escaped
        assert "\\_" in escaped

    def test_escape_markdown_special_characters(self):
        text = "Special chars: [test](url) ~`>#+-=|{}.!"
        escaped = MessageFormatter.escape_markdown(text)
        for char in ['[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
            assert f"\\{char}" in escaped

    def test_escape_markdown_empty_string(self):
        text = ""
        escaped = MessageFormatter.escape_markdown(text)
        assert escaped == ""

    def test_escape_markdown_none_value(self):
        text = None
        escaped = MessageFormatter.escape_markdown(text)
        assert escaped is None

    def test_format_task_list_empty(self):
        """Test task list formatting with empty list."""
        tasks = []
        formatted = MessageFormatter.format_task_list(tasks, "Empty Tasks")
        
        assert "Empty Tasks" in formatted
        assert "No tasks found" in formatted

    def test_format_task_list_single_task(self):
        """Test task list formatting with single task."""
        tasks = [
            {"id": 1, "description": "Test task", "status": "Todo", "priority": "High"}
        ]
        formatted = MessageFormatter.format_task_list(tasks, "Test Tasks")
        
        assert "Test Tasks" in formatted
        assert "Test task" in formatted
        assert "High" in formatted

    def test_format_task_list_multiple_tasks(self):
        """Test task list formatting with multiple tasks."""
        tasks = [
            {"id": 1, "description": "Task 1", "status": "Todo", "priority": "High"},
            {"id": 2, "description": "Task 2", "status": "Done", "priority": "Medium"}
        ]
        formatted = MessageFormatter.format_task_list(tasks, "Multiple Tasks")
        
        assert "Multiple Tasks" in formatted
        assert "Task 1" in formatted
        assert "Task 2" in formatted
        assert "High" in formatted
        assert "Medium" in formatted

    def test_format_task_list_with_client(self):
        tasks = [{"id": 1, "description": "Test task", "status": "Todo", "priority": "High"}]
        formatted = MessageFormatter.format_task_list(tasks, title="Tasks with Client")
        assert "Test task" in formatted
        assert "Tasks with Client" in formatted

    def test_format_task_list_with_due_date(self):
        """Test task list formatting with due date."""
        from datetime import datetime, timedelta
        
        due_date = datetime.now() + timedelta(days=1)
        tasks = [
            {
                "id": 1, 
                "description": "Test task", 
                "status": "Todo", 
                "priority": "High",
                "due_date": due_date
            }
        ]
        formatted = MessageFormatter.format_task_list(tasks, "Tasks with Due Date")
        
        assert "due" in formatted.lower()

    def test_format_client_list_empty(self):
        """Test client list formatting with empty list."""
        clients = []
        formatted = MessageFormatter.format_client_list(clients)
        
        assert "No clients found" in formatted

    def test_format_client_list_single_client(self):
        clients = [{"id": 1, "name": "Test Client", "task_count": 5}]
        formatted = MessageFormatter.format_client_list(clients)
        assert "Test Client" in formatted
        assert "📋 Tasks: 5" in formatted

    def test_format_client_list_multiple_clients(self):
        clients = [
            {"id": 1, "name": "Client 1", "task_count": 3},
            {"id": 2, "name": "Client 2", "task_count": 7}
        ]
        formatted = MessageFormatter.format_client_list(clients)
        assert "Client 1" in formatted
        assert "📋 Tasks: 3" in formatted
        assert "Client 2" in formatted
        assert "📋 Tasks: 7" in formatted

    def test_format_habit_list_empty(self):
        """Test habit list formatting with empty list."""
        habits = []
        formatted = MessageFormatter.format_habit_list(habits)
        
        assert "No habits found" in formatted

    def test_format_habit_list_single_habit(self):
        habits = [
            {"id": 1, "name": "Test Habit", "streak": 5, "completed_today": False}
        ]
        formatted = MessageFormatter.format_habit_list(habits)
        assert "Test Habit" in formatted
        assert "🔥 Streak: 5 days" in formatted

    def test_format_habit_list_completed_today(self):
        habits = [
            {"id": 1, "name": "Test Habit", "streak": 5, "completed_today": True}
        ]
        formatted = MessageFormatter.format_habit_list(habits)
        assert "Test Habit" in formatted
        assert "🔥 Streak: 5 days" in formatted

    def test_format_error_message(self):
        formatted = MessageFormatter.format_error_message("Test Error", "Try again")
        assert "❌ **Error**" in formatted
        assert "Test Error" in formatted
        assert "💡 **Suggestion:**" in formatted
        assert "Try again" in formatted

    def test_format_error_message_no_suggestion(self):
        """Test error message formatting without suggestion."""
        formatted = MessageFormatter.format_error_message("Test Error")
        
        assert "❌ **Error**" in formatted
        assert "Test Error" in formatted
        assert "💡 **Suggestion**" not in formatted

    def test_format_success_message(self):
        """Test success message formatting."""
        formatted = MessageFormatter.format_success_message("Task completed", {"id": 123})
        
        assert "✅ **Success**" in formatted
        assert "Task completed" in formatted
        assert "123" in formatted

    def test_format_success_message_no_details(self):
        """Test success message formatting without details."""
        formatted = MessageFormatter.format_success_message("Task completed")
        
        assert "✅ **Success**" in formatted
        assert "Task completed" in formatted

    def test_format_analytics_basic(self):
        analytics = {
            "total_tasks": 10,
            "completed_tasks": 7,
            "incomplete_tasks": 0,
            "overdue_tasks": 0,
            "completion_rate": 70.0
        }
        formatted = MessageFormatter.format_analytics(analytics)
        assert "70.0%" in formatted
        assert "Total Tasks: 10" in formatted
        assert "Completed: 7" in formatted

    def test_format_analytics_complex(self):
        analytics = {
            "total_tasks": 20,
            "completed_tasks": 15,
            "incomplete_tasks": 0,
            "overdue_tasks": 0,
            "completion_rate": 75.0,
            "priority_distribution": {
                "High": 5,
                "Medium": 10,
                "Low": 5
            }
        }
        formatted = MessageFormatter.format_analytics(analytics)
        assert "75.0%" in formatted
        assert "Total Tasks: 20" in formatted
        assert "Completed: 15" in formatted
        assert "High: 5" in formatted
        assert "Medium: 10" in formatted

    def test_format_warning_message(self):
        formatted = MessageFormatter.format_warning_message("Test Warning", {"detail": "Warning detail"})
        assert "⚠️ **Test Warning**" in formatted
        assert "Warning detail" in formatted

    def test_format_info_message(self):
        formatted = MessageFormatter.format_info_message("Test Info", {"detail": "Info detail"})
        assert "ℹ️ **Test Info**" in formatted
        assert "Info detail" in formatted


class TestNavigationHelperComprehensive:
    """Comprehensive navigation helper testing."""

    def test_get_main_menu_keyboard(self):
        """Test main menu keyboard building."""
        keyboard = NavigationHelper.get_main_menu_keyboard()
        all_button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "📋 Tasks" in all_button_texts
        assert "👥 Clients" in all_button_texts
        assert "🔄 Habits" in all_button_texts
        assert "⏰ Reminders" in all_button_texts
        assert "📊 Analytics" in all_button_texts
        assert "📎 Files" in all_button_texts
        assert "📅 Calendar" in all_button_texts
        assert "⚙️ Settings" in all_button_texts

    def test_get_task_menu_keyboard(self):
        """Test task menu keyboard building."""
        keyboard = NavigationHelper.get_task_menu_keyboard()
        all_button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "📋 View Tasks" in all_button_texts
        assert "➕ Add Task" in all_button_texts
        assert "🔍 Search" in all_button_texts
        assert "📊 Analytics" in all_button_texts
        assert "⚠️ Overdue" in all_button_texts
        assert "📅 Today" in all_button_texts
        assert "⬅️ Back" in all_button_texts


class TestChartBuilderComprehensive:
    """Comprehensive chart builder testing."""

    def test_build_bar_chart_basic(self):
        """Test basic bar chart building."""
        data = {"A": 5, "B": 3, "C": 7}
        chart = ChartBuilder.build_bar_chart(data, "Test Chart")
        
        assert "Test Chart" in chart
        assert "A" in chart
        assert "B" in chart
        assert "C" in chart

    def test_build_bar_chart_empty_data(self):
        """Test bar chart building with empty data."""
        data = {}
        chart = ChartBuilder.build_bar_chart(data, "Empty Chart")
        
        assert "Empty Chart" in chart
        assert "No data available" in chart

    def test_build_bar_chart_large_values(self):
        """Test bar chart building with large values."""
        data = {"A": 100, "B": 50, "C": 75}
        chart = ChartBuilder.build_bar_chart(data, "Large Values Chart")
        
        assert "Large Values Chart" in chart
        assert "A" in chart
        assert "B" in chart
        assert "C" in chart

    def test_build_pie_chart_basic(self):
        """Test basic pie chart building."""
        data = {"A": 30, "B": 40, "C": 30}
        chart = ChartBuilder.build_pie_chart(data, "Test Pie Chart")
        
        assert "Test Pie Chart" in chart
        assert "A" in chart
        assert "B" in chart
        assert "C" in chart

    def test_build_pie_chart_empty_data(self):
        """Test pie chart building with empty data."""
        data = {}
        chart = ChartBuilder.build_pie_chart(data, "Empty Pie Chart")
        
        assert "Empty Pie Chart" in chart
        assert "No data available" in chart

    def test_build_progress_bar_basic(self):
        """Test basic progress bar building."""
        chart = ChartBuilder.build_progress_bar(7, 10, label="Test Progress")
        
        assert "Test Progress" in chart
        assert "7/10" in chart

    def test_build_progress_bar_complete(self):
        """Test progress bar for complete progress."""
        chart = ChartBuilder.build_progress_bar(10, 10, 20, "Complete Progress")
        assert "100.0%" in chart
        assert "Complete Progress" in chart
        assert "10/10" in chart  # The parentheses are escaped in MarkdownV2 output

    def test_build_progress_bar_zero_progress(self):
        """Test progress bar building for zero progress."""
        chart = ChartBuilder.build_progress_bar(0, 10, label="Zero Progress")
        
        assert "Zero Progress" in chart
        assert "0/10" in chart
        assert "0%" in chart

    def test_build_timeline_chart_basic(self):
        """Test timeline chart with basic data."""
        from datetime import date
        data = [
            (date(2023, 1, 1), 5, "Task 1"),
            (date(2023, 1, 2), 3, "Task 2"),
            (date(2023, 1, 3), 7, "Task 3")
        ]
        chart = ChartBuilder.build_timeline_chart(data, "Test Timeline")
        assert "Test Timeline" in chart
        assert "Task 1" in chart
        assert "Task 2" in chart
        assert "Task 3" in chart

    def test_build_heatmap_basic(self):
        """Test heatmap with basic data."""
        data = {
            "Monday": 5,
            "Tuesday": 3,
            "Wednesday": 7,
            "Thursday": 2,
            "Friday": 8
        }
        chart = ChartBuilder.build_heatmap(data, "Test Heatmap")
        assert "Test Heatmap" in chart
        assert "Monday" in chart
        assert "Friday" in chart


class TestAnalyticsFormatterComprehensive:
    """Comprehensive analytics formatter testing."""

    def test_format_task_analytics_basic(self):
        """Test basic task analytics formatting."""
        analytics = {
            "total_tasks": 20,
            "completed_tasks": 15,
            "incomplete_tasks": 0,
            "overdue_tasks": 0,
            "completion_rate": 75.0
        }
        formatted = AnalyticsFormatter.format_task_analytics(analytics)
        assert "📊 **Task Analytics Dashboard**" in formatted
        assert "Total Tasks: 20" in formatted
        assert "Completed: 15" in formatted
        assert "75.0%" in formatted

    def test_format_task_analytics_complex(self):
        """Test complex task analytics formatting."""
        analytics = {
            "total_tasks": 50,
            "completed_tasks": 35,
            "incomplete_tasks": 0,
            "overdue_tasks": 0,
            "completion_rate": 70.0,
            "priority_distribution": {
                "High": 10,
                "Medium": 25,
                "Low": 15
            },
            "status_distribution": {
                "Done": 35,
                "Todo": 15,
                "In Progress": 5
            }
        }
        formatted = AnalyticsFormatter.format_task_analytics(analytics)
        assert "📊 **Task Analytics Dashboard**" in formatted
        assert "Total Tasks: 50" in formatted
        assert "Completed: 35" in formatted
        assert "70.0%" in formatted

    def test_format_productivity_report_basic(self):
        """Test basic productivity report formatting."""
        data = {
            "period": "This Week",
            "tasks_completed": 15,
            "total_tasks": 20,
            "completion_rate": 75.0
        }
        formatted = AnalyticsFormatter.format_productivity_report(data)
        assert "📈 **Productivity Report**" in formatted

    def test_format_productivity_report_complex(self):
        """Test complex productivity report formatting."""
        data = {
            "period": "This Month",
            "tasks_completed": 45,
            "total_tasks": 60,
            "completion_rate": 75.0,
            "daily_average": 1.5,
            "best_day": "Monday",
            "worst_day": "Friday"
        }
        formatted = AnalyticsFormatter.format_productivity_report(data)
        assert "📈 **Productivity Report**" in formatted


class TestUXHelpersEdgeCases:
    """Edge cases and error scenarios for UX helpers."""

    def test_keyboard_builder_edge_cases(self):
        """Test keyboard builder with edge cases."""
        # Test with very long text
        long_text = "A" * 100
        keyboard = KeyboardBuilder.build_task_keyboard(123, long_text, show_edit=True)
        assert keyboard is not None

        # Test with special characters
        special_text = "Task with 🎉 emoji and special chars: !@#$%^&*()"
        keyboard = KeyboardBuilder.build_task_keyboard(123, special_text, show_edit=True)
        assert keyboard is not None

    def test_message_formatter_edge_cases(self):
        """Test message formatter with edge cases."""
        # Test with very long descriptions
        long_description = "A" * 1000
        tasks = [{"id": 1, "description": long_description, "status": "Todo"}]
        formatted = MessageFormatter.format_task_list(tasks, "Long Description")
        assert "Long Description" in formatted

        # Test with None values
        tasks = [{"id": 1, "description": None, "status": "Todo"}]
        formatted = MessageFormatter.format_task_list(tasks, "None Description")
        assert "None Description" in formatted

    def test_chart_builder_edge_cases(self):
        """Test chart builder with edge cases."""
        # Test with very large numbers
        data = {"A": 1000000, "B": 500000}
        chart = ChartBuilder.build_bar_chart(data, "Large Numbers")
        assert "Large Numbers" in chart

        # Test with zero values
        data = {"A": 0, "B": 0}
        chart = ChartBuilder.build_bar_chart(data, "Zero Values")
        assert "Zero Values" in chart

    def test_analytics_formatter_edge_cases(self):
        """Test analytics formatter with edge cases."""
        # Test with empty data
        empty_analytics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "incomplete_tasks": 0,
            "overdue_tasks": 0,
            "completion_rate": 0.0
        }
        formatted = AnalyticsFormatter.format_task_analytics(empty_analytics)
        assert "📊 **Task Analytics Dashboard**" in formatted
        assert "Total Tasks: 0" in formatted
        assert "0.0%" in formatted 