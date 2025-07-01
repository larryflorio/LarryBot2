import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
from larrybot.plugins.tasks import (
    register,
    add_task_handler,
    list_tasks_handler,
    done_task_handler,
    edit_task_handler,
    remove_task_handler
)
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task import Task


def test_register_commands(command_registry, event_bus):
    """Test that tasks plugin registers all commands correctly."""
    register(event_bus, command_registry)
    
    registered_commands = list(command_registry._commands.keys())
    assert "/add" in registered_commands
    assert "/list" in registered_commands
    assert "/done" in registered_commands
    assert "/edit" in registered_commands
    assert "/remove" in registered_commands


@pytest.mark.asyncio
async def test_add_task_handler_no_args(test_session, mock_update, mock_context):
    """Test add_task handler when no arguments are provided."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = []
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await add_task_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Missing task description" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_add_task_handler_success(test_session, mock_update, mock_context):
    """Test successful task addition with enhanced handler."""
    # Arrange - test basic task creation (single argument)
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Test task"]
    
    # Act
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await add_task_handler(mock_update, mock_context)
        
        # Assert - verify task was created in database
        repo = TaskRepository(test_session)
        tasks = repo.list_incomplete_tasks()
        assert len(tasks) == 1
        assert tasks[0].description == "Test task"
        
        # Verify response
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Task added successfully" in response_text
        assert "Test task" in response_text


@pytest.mark.asyncio
async def test_add_task_handler_emits_event(test_session, mock_update, mock_context):
    """Test that add_task handler emits task_created event."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["Test task"]
    
    # Mock the global event bus
    mock_event_bus = MagicMock()
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        with patch("larrybot.plugins.tasks._task_event_bus", mock_event_bus):
            await add_task_handler(mock_update, mock_context)
            
            # Verify event was emitted
            mock_event_bus.emit.assert_called_once_with("task_created", mock_event_bus.emit.call_args[0][1])


@pytest.mark.asyncio
async def test_list_tasks_handler_no_tasks(test_session, mock_update, mock_context):
    """Test list_tasks handler when no tasks exist."""
    mock_update.message.reply_text = AsyncMock()
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await list_tasks_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "No Tasks Found" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_list_tasks_handler_with_tasks(test_session, mock_update, mock_context, db_task_factory):
    """Test list_tasks handler when tasks exist."""
    mock_update.message.reply_text = AsyncMock()
    
    # Create some tasks using the factory
    task1 = db_task_factory(description="Task 1")
    task2 = db_task_factory(description="Task 2")
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await list_tasks_handler(mock_update, mock_context)
        
        # Check that the message contains both tasks
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Incomplete Tasks" in call_args[0][0]
        assert "Task 1" in call_args[0][0]
        assert "Task 2" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_list_tasks_handler_only_incomplete_tasks(test_session, mock_update, mock_context, db_task_factory):
    """Test list_tasks handler only shows incomplete tasks."""
    mock_update.message.reply_text = AsyncMock()
    
    # Create tasks and mark one as done using the factory
    task1 = db_task_factory(description="Task 1")
    task2 = db_task_factory(description="Task 2")
    repo = TaskRepository(test_session)
    repo.mark_task_done(task1.id)
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await list_tasks_handler(mock_update, mock_context)
        
        # Check that only incomplete task is shown
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Incomplete Tasks" in call_args[0][0]
        assert "Task 2" in call_args[0][0]
        assert "Task 1" not in call_args[0][0]  # Should not appear since it's done
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_done_task_handler_no_args(test_session, mock_update, mock_context):
    """Test done_task handler when no arguments are provided."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = []
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await done_task_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Missing or invalid task ID" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_done_task_handler_invalid_id(test_session, mock_update, mock_context):
    """Test done_task handler when task_id is not a number."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["abc"]
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await done_task_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Missing or invalid task ID" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_done_task_handler_task_not_found(test_session, mock_update, mock_context):
    """Test done_task handler when task ID doesn't exist."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["999"]
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await done_task_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Task ID 999 not found" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_done_task_handler_already_completed(test_session, mock_update, mock_context, db_task_factory):
    """Test done_task handler when task is already completed."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["1"]
    
    # Create a task and mark it as done using the factory
    task = db_task_factory(description="Test task")
    repo = TaskRepository(test_session)
    repo.mark_task_done(task.id)
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await done_task_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Task Already Complete" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_done_task_handler_success(test_session, mock_update, mock_context, db_task_factory):
    """Test done_task handler when task exists and is not completed."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["1"]
    
    # Create a task using the factory
    task = db_task_factory(description="Test task")
    repo = TaskRepository(test_session)
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await done_task_handler(mock_update, mock_context)
        
        # Check the response message
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Task completed" in call_args[0][0]
        assert "Test task" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_done_task_handler_emits_event(test_session, mock_update, mock_context, db_task_factory):
    """Test that done_task handler emits task_completed event."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["1"]
    
    # Create a task using the factory
    task = db_task_factory(description="Test task")
    
    # Mock the global event bus
    mock_event_bus = MagicMock()
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        with patch("larrybot.plugins.tasks._task_event_bus", mock_event_bus):
            await done_task_handler(mock_update, mock_context)
            
            # Verify event was emitted with dictionary format
            mock_event_bus.emit.assert_called_once()
            call_args = mock_event_bus.emit.call_args
            assert call_args[0][0] == "task_completed"  # event name
            assert isinstance(call_args[0][1], dict)  # event data should be dict
            assert call_args[0][1]["description"] == "Test task"  # check dict content


@pytest.mark.asyncio
async def test_edit_task_handler_no_args(test_session, mock_update, mock_context):
    """Test edit_task handler when no arguments are provided."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = []
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await edit_task_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Invalid arguments" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_edit_task_handler_invalid_id(test_session, mock_update, mock_context):
    """Test edit_task handler when task_id is not a number."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["abc", "new", "description"]
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await edit_task_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Invalid arguments" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_edit_task_handler_empty_description(test_session, mock_update, mock_context):
    """Test edit_task handler when new description is empty."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["1", ""]
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await edit_task_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "New description cannot be empty" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_edit_task_handler_task_not_found(test_session, mock_update, mock_context):
    """Test edit_task handler when task ID doesn't exist."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["999", "new", "description"]
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await edit_task_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Task ID 999 not found" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_edit_task_handler_success(test_session, mock_update, mock_context, db_task_factory):
    """Test edit_task handler when task exists."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["1", "Updated", "task", "description"]
    
    # Create a task using the factory
    task = db_task_factory(description="Original task")
    repo = TaskRepository(test_session)
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await edit_task_handler(mock_update, mock_context)
        
        # Check the response message
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Task updated successfully" in call_args[0][0]
        assert "Updated task description" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'
        
        # Verify task was updated
        updated_task = repo.get_task_by_id(task.id)
        assert updated_task.description == "Updated task description"


@pytest.mark.asyncio
async def test_edit_task_handler_emits_event(test_session, mock_update, mock_context, db_task_factory):
    """Test that edit_task handler emits task_edited event."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["1", "Updated", "description"]
    
    # Create a task using the factory
    task = db_task_factory(description="Original task")
    
    # Mock the global event bus
    mock_event_bus = MagicMock()
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        with patch("larrybot.plugins.tasks._task_event_bus", mock_event_bus):
            await edit_task_handler(mock_update, mock_context)
            
            # Verify event was emitted with the updated task
            mock_event_bus.emit.assert_called_once_with("task_edited", mock_event_bus.emit.call_args[0][1])


@pytest.mark.asyncio
async def test_remove_task_handler_no_args(test_session, mock_update, mock_context):
    """Test remove_task handler when no arguments are provided."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = []
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await remove_task_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Missing or invalid task ID" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_remove_task_handler_invalid_id(test_session, mock_update, mock_context):
    """Test remove_task handler when task_id is not a number."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["abc"]
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await remove_task_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Missing or invalid task ID" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_remove_task_handler_task_not_found(test_session, mock_update, mock_context):
    """Test remove_task handler when task ID doesn't exist."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["999"]
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await remove_task_handler(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Task ID 999 not found" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'


@pytest.mark.asyncio
async def test_remove_task_handler_success(test_session, mock_update, mock_context, db_task_factory):
    """Test remove_task handler when task exists."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["1"]
    
    # Create a task using the factory
    task = db_task_factory(description="Test task")
    repo = TaskRepository(test_session)
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await remove_task_handler(mock_update, mock_context)
        
        # Check the response message - now shows confirmation dialog
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Confirm Task Deletion" in call_args[0][0]
        assert "Test task" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'
        assert 'reply_markup' in call_args[1]  # Should have inline keyboard


@pytest.mark.asyncio
async def test_remove_task_handler_emits_event(test_session, mock_update, mock_context, db_task_factory):
    """Test that remove_task handler shows confirmation dialog."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["1"]
    
    # Create a task using the factory
    task = db_task_factory(description="Test task")
    
    with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
        await remove_task_handler(mock_update, mock_context)
        
        # Verify confirmation dialog is shown (no event emitted until confirmed)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Confirm Task Deletion" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2' 