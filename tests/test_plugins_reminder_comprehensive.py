"""
Comprehensive reminder plugin testing with edge cases and error scenarios.

This test suite targets the coverage gap in larrybot/plugins/reminder.py
to achieve 80%+ coverage through comprehensive testing of all reminder functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from larrybot.plugins.reminder import (
    register,
    add_reminder_handler,
    quick_reminder_handler,
    list_reminders_handler,
    delete_reminder_handler,
    reminder_stats_handler,
    ReminderEventHandler
)
from larrybot.storage.reminder_repository import ReminderRepository
from larrybot.storage.task_repository import TaskRepository
from larrybot.core.events import ReminderDueEvent


class TestReminderPluginComprehensive:
    """Comprehensive reminder plugin testing with edge cases."""

    def test_register_commands_comprehensive(self, command_registry, event_bus):
        """Test that reminder plugin registers all commands correctly."""
        register(event_bus, command_registry)
        registered_commands = list(command_registry._commands.keys())
        assert "/addreminder" in registered_commands
        assert "/reminders" in registered_commands
        assert "/delreminder" in registered_commands
        assert "/reminder_quick" in registered_commands
        assert "/reminder_stats" in registered_commands

    # Add Reminder Handler Tests
    @pytest.mark.asyncio
    async def test_add_reminder_handler_no_args(self, test_session, mock_update, mock_context):
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = []
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await add_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Invalid arguments" in call_args[0][0]
            assert call_args[1].get('parse_mode') == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_add_reminder_handler_invalid_date(self, test_session, mock_update, mock_context):
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["1", "bad-date"]
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await add_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Invalid date/time format" in call_args[0][0]
            assert call_args[1].get('parse_mode') == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_add_reminder_handler_past_time(self, test_session, mock_update, mock_context, db_task_factory):
        mock_update.message.reply_text = AsyncMock()
        task = db_task_factory(description="Test task")
        mock_context.args = [str(task.id), "2000-01-01", "00:00"]
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await add_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Reminder time is in the past" in call_args[0][0]
            assert call_args[1].get('parse_mode') == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_add_reminder_handler_task_not_found(self, test_session, mock_update, mock_context):
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["999", "2099-01-01", "10:00"]
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await add_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Task ID 999 not found" in call_args[0][0]
            assert call_args[1].get('parse_mode') == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_add_reminder_handler_success(self, test_session, mock_update, mock_context, db_task_factory):
        mock_update.message.reply_text = AsyncMock()
        task = db_task_factory(description="Test task")
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M").split()
        mock_context.args = [str(task.id)] + future_date
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await add_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Reminder set successfully" in call_args[0][0]
            assert call_args[1].get('parse_mode') == 'MarkdownV2'

    # Quick Reminder Handler Tests
    @pytest.mark.asyncio
    async def test_quick_reminder_handler_invalid_args(self, test_session, mock_update, mock_context):
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = []
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await quick_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Invalid arguments" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_quick_reminder_handler_invalid_time(self, test_session, mock_update, mock_context, db_task_factory):
        mock_update.message.reply_text = AsyncMock()
        task = db_task_factory(description="Test task")
        mock_context.args = [str(task.id), "bad"]
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await quick_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Invalid time format" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_quick_reminder_handler_task_not_found(self, test_session, mock_update, mock_context):
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["999", "30m"]
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await quick_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Task ID 999 not found" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_quick_reminder_handler_success(self, test_session, mock_update, mock_context, db_task_factory):
        mock_update.message.reply_text = AsyncMock()
        task = db_task_factory(description="Quick task")
        mock_context.args = [str(task.id), "30m"]
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await quick_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Quick reminder set" in call_args[0][0]

    # List Reminders Handler Tests
    @pytest.mark.asyncio
    async def test_list_reminders_handler_no_reminders(self, test_session, mock_update, mock_context):
        mock_update.message.reply_text = AsyncMock()
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await list_reminders_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "No reminders found" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_list_reminders_handler_with_reminders(self, test_session, mock_update, mock_context, db_task_factory, db_reminder_factory):
        mock_update.message.reply_text = AsyncMock()
        task = db_task_factory(description="List task")
        reminder = db_reminder_factory(task_id=task.id, remind_at=datetime.now() + timedelta(hours=2))
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await list_reminders_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "All Reminders" in call_args[0][0]
            assert "List task" in call_args[0][0]
            assert call_args[1].get('reply_markup') is not None

    # Delete Reminder Handler Tests
    @pytest.mark.asyncio
    async def test_delete_reminder_handler_no_args(self, test_session, mock_update, mock_context):
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = []
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await delete_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Invalid reminder ID" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_delete_reminder_handler_invalid_id(self, test_session, mock_update, mock_context):
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["bad"]
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await delete_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Invalid reminder ID" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_delete_reminder_handler_reminder_not_found(self, test_session, mock_update, mock_context):
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["999"]
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await delete_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Reminder ID 999 not found" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_delete_reminder_handler_success(self, test_session, mock_update, mock_context, db_task_factory, db_reminder_factory):
        mock_update.message.reply_text = AsyncMock()
        task = db_task_factory(description="Delete task")
        reminder = db_reminder_factory(task_id=task.id, remind_at=datetime.now() + timedelta(hours=2))
        mock_context.args = [str(reminder.id)]
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await delete_reminder_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "Confirm Reminder Deletion" in call_args[0][0]
            assert "Delete task" in call_args[0][0]
            assert call_args[1].get('reply_markup') is not None

    # Reminder Stats Handler Tests
    @pytest.mark.asyncio
    async def test_reminder_stats_handler_no_reminders(self, test_session, mock_update, mock_context):
        mock_update.message.reply_text = AsyncMock()
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await reminder_stats_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            assert "No reminders to analyze" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_reminder_stats_handler_with_reminders(self, test_session, mock_update, mock_context, db_task_factory, db_reminder_factory):
        mock_update.message.reply_text = AsyncMock()
        task = db_task_factory(description="Stats task")
        # Create reminders: overdue, due soon, due today, future
        db_reminder_factory(task_id=task.id, remind_at=datetime.now() - timedelta(hours=1))  # Overdue
        db_reminder_factory(task_id=task.id, remind_at=datetime.now() + timedelta(minutes=30))  # Due soon
        db_reminder_factory(task_id=task.id, remind_at=datetime.now() + timedelta(hours=5))  # Due today
        db_reminder_factory(task_id=task.id, remind_at=datetime.now() + timedelta(days=2))  # Future
        with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
            await reminder_stats_handler(mock_update, mock_context)
            call_args = mock_update.message.reply_text.call_args
            text = call_args[0][0]
            assert "Reminder Statistics" in text
            assert "Overdue: 1" in text
            assert "Due Soon (≤1h): 1" in text
            assert "Due Today: 1" in text
            assert "Future: 1" in text
            assert "Next Reminder" in text
            assert "Insights" in text 