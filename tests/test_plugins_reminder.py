import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timedelta
from larrybot.plugins.reminder import (
    register,
    register_event_handler,
    set_main_event_loop,
    subscribe_to_events,
    add_reminder_handler,
    list_reminders_handler,
    delete_reminder_handler,
    ReminderEventHandler
)
from larrybot.storage.reminder_repository import ReminderRepository
from larrybot.storage.task_repository import TaskRepository
from larrybot.core.events import ReminderDueEvent


def test_register_commands(command_registry, event_bus):
    """Test that reminder plugin registers all commands correctly."""
    register(event_bus, command_registry)
    
    registered_commands = list(command_registry._commands.keys())
    assert "/addreminder" in registered_commands
    assert "/reminders" in registered_commands
    assert "/delreminder" in registered_commands


def test_register_event_handler():
    """Test registering the reminder event handler."""
    mock_bot_app = MagicMock()
    user_id = 12345
    
    register_event_handler(mock_bot_app, user_id)
    
    # The function sets a global variable, so we can't easily test it
    # But we can test that it doesn't raise an exception
    assert True


def test_set_main_event_loop():
    """Test setting the main event loop."""
    mock_loop = MagicMock()
    
    set_main_event_loop(mock_loop)
    
    # The function sets global variables, so we can't easily test it
    # But we can test that it doesn't raise an exception
    assert True


def test_subscribe_to_events(event_bus):
    """Test subscribing to reminder events."""
    mock_bot_app = MagicMock()
    user_id = 12345
    
    register_event_handler(mock_bot_app, user_id)
    subscribe_to_events(event_bus)
    
    # Verify that the event bus was subscribed to
    assert "reminder_due" in event_bus._listeners


@pytest.mark.asyncio
async def test_reminder_event_handler_handle_reminder_due():
    """Test the ReminderEventHandler.handle_reminder_due method."""
    mock_bot_app = MagicMock()
    mock_bot_app.bot.send_message = AsyncMock()
    user_id = 12345
    
    handler = ReminderEventHandler(mock_bot_app, user_id)
    
    # Create a reminder event
    task_description = "Test task"
    remind_at = datetime(2024, 1, 1, 10, 30)
    event = ReminderDueEvent(
        reminder_id=1,
        task_id=1,
        task_description=task_description,
        remind_at=remind_at
    )
    
    await handler.handle_reminder_due(event)
    
    # Verify the message was sent with rich formatting
    call_args = mock_bot_app.bot.send_message.call_args
    response_text = call_args[1]['text']
    parse_mode = call_args[1].get('parse_mode')
    
    assert "Reminder Due!" in response_text
    assert "Test task" in response_text
    assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_reminder_event_handler_handle_reminder_due_error():
    """Test the ReminderEventHandler.handle_reminder_due method when an error occurs."""
    mock_bot_app = MagicMock()
    mock_bot_app.bot.send_message = AsyncMock(side_effect=Exception("Bot error"))
    user_id = 12345
    
    handler = ReminderEventHandler(mock_bot_app, user_id)
    
    # Create a reminder event
    task_description = "Test task"
    remind_at = datetime(2024, 1, 1, 10, 30)
    event = ReminderDueEvent(
        reminder_id=1,
        task_id=1,
        task_description=task_description,
        remind_at=remind_at
    )
    
    # Should not raise an exception
    await handler.handle_reminder_due(event)
    
    # Verify the message was attempted
    mock_bot_app.bot.send_message.assert_called_once()


def test_reminder_event_handler_set_event_loop():
    """Test setting the event loop on the ReminderEventHandler."""
    mock_bot_app = MagicMock()
    user_id = 12345
    mock_loop = MagicMock()
    
    handler = ReminderEventHandler(mock_bot_app, user_id)
    handler.set_event_loop(mock_loop)
    
    assert handler._loop == mock_loop


@pytest.mark.asyncio
async def test_add_reminder_handler_no_args(test_session, mock_update, mock_context):
    """Test add_reminder handler when no arguments are provided."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = []
    
    with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
        await add_reminder_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Invalid arguments" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_add_reminder_handler_invalid_task_id(test_session, mock_update, mock_context):
    """Test add_reminder handler when task_id is not a number."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["abc", "2024-01-01", "10:30"]
    
    with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
        await add_reminder_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Invalid arguments" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_add_reminder_handler_invalid_date_format(test_session, mock_update, mock_context):
    """Test add_reminder handler when date format is invalid."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["1", "invalid-date"]
    
    with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
        await add_reminder_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Invalid date/time format" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_add_reminder_handler_task_not_found(test_session, mock_update, mock_context):
    """Test add_reminder handler when task ID doesn't exist."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["999", "2024-01-01", "10:30"]
    
    with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
        await add_reminder_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Reminder time is in the past" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_add_reminder_handler_success(test_session, mock_update, mock_context, db_task_factory):
    """Test add_reminder handler with valid arguments."""
    mock_update.message.reply_text = AsyncMock()
    # Create a task first
    task = db_task_factory(description="Test task")
    task_id = task.id
    
    # Use a future date for the reminder
    future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    mock_context.args = [str(task_id), future_date, "10:30"]
    
    with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
        await add_reminder_handler(mock_update, mock_context)
        
        # Check that the reminder was created
        reminder_repo = ReminderRepository(test_session)
        reminders = reminder_repo.list_reminders()
        assert len(reminders) == 1
        assert reminders[0].task_id == task_id
        
        # Check the response message
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "✅ **Success**" in response_text
        assert "Reminder set" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_list_reminders_handler_no_reminders(test_session, mock_update, mock_context):
    """Test list_reminders handler when no reminders exist."""
    mock_update.message.reply_text = AsyncMock()
    
    with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
        await list_reminders_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "No reminders found" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_delete_reminder_handler_no_args(test_session, mock_update, mock_context):
    """Test delete_reminder handler when no arguments are provided."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = []
    
    with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
        await delete_reminder_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Invalid reminder ID" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_delete_reminder_handler_invalid_id(test_session, mock_update, mock_context):
    """Test delete_reminder handler when reminder_id is not a number."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["abc"]
    
    with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
        await delete_reminder_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Invalid reminder ID" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_delete_reminder_handler_reminder_not_found(test_session, mock_update, mock_context):
    """Test delete_reminder handler when reminder ID doesn't exist."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["999"]
    
    with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
        await delete_reminder_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Reminder ID 999 not found" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_delete_reminder_handler_success(test_session, mock_update, mock_context, db_task_factory, db_reminder_factory):
    """Test delete_reminder handler with valid arguments."""
    mock_update.message.reply_text = AsyncMock()
    # Create a task and reminder first
    task = db_task_factory(description="Test task")
    
    # Use a future date for the reminder
    future_date = datetime.now() + timedelta(days=1)
    reminder = db_reminder_factory(task_id=task.id, remind_at=future_date)
    reminder_id = reminder.id
    mock_context.args = [str(reminder_id)]
    
    with patch("larrybot.plugins.reminder.get_session", return_value=iter([test_session])):
        await delete_reminder_handler(mock_update, mock_context)
        
        # Check that confirmation dialog was shown (new UX behavior)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        reply_markup = call_args[1].get('reply_markup')
        parse_mode = call_args[1].get('parse_mode')
        
        assert "🗑️ **Confirm Reminder Deletion**" in response_text
        assert "Test task" in response_text
        assert str(reminder_id) in response_text
        assert reply_markup is not None  # Should have confirmation keyboard
        assert parse_mode == 'MarkdownV2'
        
        # The reminder should still exist (not deleted until confirmed)
        reminder_repo = ReminderRepository(test_session)
        reminder_still_exists = reminder_repo.get_reminder_by_id(reminder_id)
        assert reminder_still_exists is not None 