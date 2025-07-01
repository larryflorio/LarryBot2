import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date
from larrybot.plugins.habit import (
    register,
    habit_add_handler,
    habit_done_handler,
    habit_list_handler,
    habit_delete_handler
)
from larrybot.storage.habit_repository import HabitRepository
from larrybot.models.habit import Habit


def test_register_commands(command_registry, event_bus):
    """Test that habit plugin registers all commands correctly."""
    register(event_bus, command_registry)
    
    registered_commands = list(command_registry._commands.keys())
    assert "/habit_add" in registered_commands
    assert "/habit_done" in registered_commands
    assert "/habit_list" in registered_commands
    assert "/habit_delete" in registered_commands


@pytest.mark.asyncio
async def test_habit_add_handler_no_args(test_session, mock_update, mock_context):
    """Test habit_add handler when no arguments are provided."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = []
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_add_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Missing habit name" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_habit_add_handler_success(test_session, mock_update, mock_context):
    """Test habit_add handler with valid arguments."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Exercise"]
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_add_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Habit 'Exercise' created successfully" in response_text
        assert parse_mode == 'MarkdownV2'
        
        # Verify habit was created in database
        repo = HabitRepository(test_session)
        habit = repo.get_habit_by_name("Exercise")
        assert habit is not None
        assert habit.name == "Exercise"
        assert habit.streak == 0
        assert habit.last_completed is None


@pytest.mark.asyncio
async def test_habit_add_handler_multiple_words(test_session, mock_update, mock_context):
    """Test habit_add handler with multiple word habit name."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Drink", "water"]
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_add_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Habit 'Drink water' created successfully" in response_text
        assert parse_mode == 'MarkdownV2'
        
        # Verify habit was created with combined name
        repo = HabitRepository(test_session)
        habit = repo.get_habit_by_name("Drink water")
        assert habit is not None
        assert habit.name == "Drink water"


@pytest.mark.asyncio
async def test_habit_add_handler_already_exists(test_session, mock_update, mock_context, db_habit_factory):
    """Test habit_add handler when habit already exists."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Exercise"]
    
    # Create a habit first
    db_habit_factory(name="Exercise")
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_add_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Habit 'Exercise' already exists" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_habit_done_handler_no_args(test_session, mock_update, mock_context):
    """Test habit_done handler when no arguments are provided."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = []
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_done_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Missing habit name" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_habit_done_handler_habit_not_found(test_session, mock_update, mock_context):
    """Test habit_done handler when habit doesn't exist."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Nonexistent"]
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_done_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Habit 'Nonexistent' not found" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_habit_done_handler_success_first_time(test_session, mock_update, mock_context, db_habit_factory):
    """Test habit_done handler when marking habit done for the first time."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Exercise"]
    
    # Create a habit first
    db_habit_factory(name="Exercise")
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_done_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Habit completed for today" in response_text
        assert parse_mode == 'MarkdownV2'
        
        # Verify habit was updated
        repo = HabitRepository(test_session)
        updated_habit = repo.get_habit_by_name("Exercise")
        assert updated_habit.streak == 1
        assert updated_habit.last_completed == date.today()


@pytest.mark.asyncio
async def test_habit_done_handler_streak_increase(test_session, mock_update, mock_context, db_habit_factory):
    """Test habit_done handler when continuing a streak."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Exercise"]
    
    # Create a habit and mark it done yesterday
    habit = db_habit_factory(name="Exercise")
    habit.last_completed = date.today() - date.resolution  # Yesterday
    habit.streak = 3
    test_session.commit()
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_done_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Habit completed for today" in response_text
        assert parse_mode == 'MarkdownV2'
        
        # Verify streak increased
        repo = HabitRepository(test_session)
        updated_habit = repo.get_habit_by_name("Exercise")
        assert updated_habit.streak == 4
        assert updated_habit.last_completed == date.today()


@pytest.mark.asyncio
async def test_habit_done_handler_streak_reset(test_session, mock_update, mock_context, db_habit_factory):
    """Test habit_done handler when streak is reset due to missed days."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Exercise"]
    
    # Create a habit and mark it done 3 days ago
    habit = db_habit_factory(name="Exercise")
    habit.last_completed = date.today() - date.resolution * 3  # 3 days ago
    habit.streak = 5
    test_session.commit()
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_done_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Habit completed for today" in response_text
        assert parse_mode == 'MarkdownV2'
        
        # Verify streak reset to 1
        repo = HabitRepository(test_session)
        updated_habit = repo.get_habit_by_name("Exercise")
        assert updated_habit.streak == 1
        assert updated_habit.last_completed == date.today()


@pytest.mark.asyncio
async def test_habit_done_handler_already_done_today(test_session, mock_update, mock_context, db_habit_factory):
    """Test habit_done handler when habit is already marked done today."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Exercise"]
    
    # Create a habit and mark it done today
    habit = db_habit_factory(name="Exercise")
    habit.last_completed = date.today()
    habit.streak = 3
    test_session.commit()
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_done_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Habit completed for today" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_habit_list_handler_no_habits(test_session, mock_update, mock_context):
    """Test habit_list handler when no habits exist."""
    mock_update.message.reply_text = AsyncMock()
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_list_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "No habits found" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_habit_list_handler_with_habits(test_session, mock_update, mock_context, db_habit_factory):
    """Test habit_list handler when habits exist."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = []
    
    db_habit_factory(name="Exercise")
    db_habit_factory(name="Read")
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_list_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Exercise" in response_text
        assert "Read" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_habit_delete_handler_no_args(test_session, mock_update, mock_context):
    """Test habit_delete handler when no arguments are provided."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = []
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_delete_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Missing habit name" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_habit_delete_handler_habit_not_found(test_session, mock_update, mock_context):
    """Test habit_delete handler when habit doesn't exist."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Nonexistent"]
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_delete_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Habit 'Nonexistent' not found" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_habit_delete_handler_success(test_session, mock_update, mock_context, db_habit_factory):
    """Test habit_delete handler when habit exists."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Exercise"]
    
    db_habit_factory(name="Exercise")
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_delete_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Confirm Habit Deletion" in response_text
        assert parse_mode == 'MarkdownV2'
        
        # Verify habit still exists (confirmation dialog shown)
        repo = HabitRepository(test_session)
        habit = repo.get_habit_by_name("Exercise")
        assert habit is not None


@pytest.mark.asyncio
async def test_habit_delete_handler_multiple_words(test_session, mock_update, mock_context, db_habit_factory):
    """Test habit_delete handler with multiple word habit name."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Drink", "water"]
    
    db_habit_factory(name="Drink water")
    
    with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
        await habit_delete_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Confirm Habit Deletion" in response_text
        assert parse_mode == 'MarkdownV2'
        
        # Verify habit still exists (confirmation dialog shown)
        repo = HabitRepository(test_session)
        habit = repo.get_habit_by_name("Drink water")
        assert habit is not None 