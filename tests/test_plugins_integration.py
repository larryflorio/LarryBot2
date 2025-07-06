import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from larrybot.core.event_bus import EventBus
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.plugin_loader import PluginLoader
from larrybot.storage.db import get_session
from larrybot.storage.task_repository import TaskRepository
from larrybot.storage.habit_repository import HabitRepository
from larrybot.storage.reminder_repository import ReminderRepository
from unittest.mock import Mock

@pytest.fixture
def mock_context():
    context = Mock()
    context.args = []
    context.user_data = {}
    return context

class TestPluginIntegration:
    """Integration tests for plugin system."""

    def test_plugin_loader_discovery(self, plugin_loader):
        """Test that plugin loader discovers all plugins."""
        plugin_loader.discover_and_load()
        
        # Should discover all plugins
        plugin_names = [p.__name__ for p in plugin_loader.plugins]
        assert "larrybot.plugins.tasks" in plugin_names
        assert "larrybot.plugins.habit" in plugin_names
        assert "larrybot.plugins.reminder" in plugin_names
        assert "larrybot.plugins.calendar" in plugin_names
        assert "larrybot.plugins.hello" in plugin_names

    def test_plugin_registration(self, event_bus, command_registry, plugin_loader):
        """Test that plugins register their commands correctly."""
        plugin_loader.discover_and_load()
        plugin_loader.register_plugins(event_bus, command_registry)
        
        # Check that commands are registered
        registered_commands = list(command_registry._commands.keys())
        
        # Task commands
        assert "/addtask" in registered_commands
        assert "/list" in registered_commands
        assert "/done" in registered_commands
        assert "/edit" in registered_commands
        assert "/remove" in registered_commands
        
        # Habit commands
        assert "/habit_add" in registered_commands
        assert "/habit_done" in registered_commands
        assert "/habit_list" in registered_commands
        assert "/habit_delete" in registered_commands
        
        # Reminder commands
        assert "/addreminder" in registered_commands
        assert "/reminders" in registered_commands
        assert "/delreminder" in registered_commands
        
        # Calendar commands
        assert "/agenda" in registered_commands
        assert "/connect_google" in registered_commands
        assert "/disconnect" in registered_commands
        
        # Hello command
        assert "/hello" in registered_commands

    @pytest.mark.asyncio
    async def test_task_plugin_events(self, event_bus, command_registry, test_session, mock_update, mock_context):
        """Test that task plugin emits events correctly."""
        from larrybot.plugins.tasks import register
        
        # Register the task plugin
        register(event_bus, command_registry)
        
        # Track emitted events
        emitted_events = []
        def event_tracker(data):
            emitted_events.append(("task_created", data))
        
        event_bus.subscribe("task_created", event_tracker)
        event_bus.subscribe("task_completed", event_tracker)
        event_bus.subscribe("task_edited", event_tracker)
        event_bus.subscribe("task_removed", event_tracker)
        
        # Mock the database session
        mock_context.args = ["Test task"]
        
        # Test task creation
        handler = command_registry._commands["/addtask"]
        await handler(mock_update, mock_context)
        
        # Check that task_created event was emitted
        assert len(emitted_events) == 1
        assert emitted_events[0][0] == "task_created"
        assert emitted_events[0][1]["description"] == "Test task"

    @pytest.mark.asyncio
    async def test_reminder_plugin_event_subscription(self, event_bus, command_registry, test_session):
        """Test that reminder plugin subscribes to events correctly."""
        from larrybot.plugins.reminder import register_event_handler, subscribe_to_events
        
        # Mock bot application
        mock_bot_app = MagicMock()
        mock_bot_app.bot = MagicMock()
        
        # Register reminder event handler
        register_event_handler(mock_bot_app, 123456789)
        subscribe_to_events(event_bus)
        
        # Check that reminder_due event is subscribed
        assert "reminder_due" in event_bus._listeners
        assert len(event_bus._listeners["reminder_due"]) == 1

    @pytest.mark.asyncio
    async def test_hello_plugin(self, event_bus, command_registry, mock_update, mock_context):
        """Test the hello plugin."""
        from larrybot.plugins.hello import register
        
        # Register the hello plugin
        register(event_bus, command_registry)
        
        # Mock the reply_text method
        mock_update.message.reply_text = AsyncMock()
        
        # Test hello command
        handler = command_registry._commands["/hello"]
        await handler(mock_update, mock_context)
        
        # Check that the correct message was sent
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        
        assert "Hello from LarryBot plugin!" in response_text
        # Note: hello plugin doesn't use MarkdownV2, so no parse_mode check


class TestTaskPluginIntegration:
    """Integration tests specifically for task plugin."""

    @pytest.mark.asyncio
    async def test_add_task_integration(self, event_bus, command_registry, test_session, mock_update, mock_context):
        """Test adding a task through the plugin."""
        from larrybot.plugins.tasks import register
        
        # Register the task plugin
        register(event_bus, command_registry)
        
        # Mock the reply_text method
        mock_update.message.reply_text = AsyncMock()
        
        # Test adding a task
        mock_context.args = ["Integration test task"]
        handler = command_registry._commands["/addtask"]
        await handler(mock_update, mock_context)
        
        # Check that the task was created and message was sent
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Integration test task" in response_text
        assert "ID:" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_list_tasks_integration(self, event_bus, command_registry, test_session, mock_update, mock_context, db_task_factory):
        """Test listing tasks through the plugin."""
        from larrybot.plugins.tasks import register
        
        # Register the task plugin
        register(event_bus, command_registry)
        
        # Create some tasks in the database using factory
        db_task_factory(description="Test task")
        db_task_factory(description="Integration test task")
        
        # Mock the reply_text method
        mock_update.message.reply_text = AsyncMock()
        
        # Test listing tasks
        handler = command_registry._commands["/list"]
        await handler(mock_update, mock_context)
        
        # Check that the tasks were listed
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Test task" in response_text
        assert "Integration test task" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_done_task_integration(self, event_bus, command_registry, test_session, mock_update, mock_context, db_task_factory):
        """Test marking a task as done through the plugin."""
        from larrybot.plugins.tasks import register
        
        # Register the task plugin
        register(event_bus, command_registry)
        
        # Create a task in the database using factory
        task = db_task_factory(description="Task to complete")
        test_session.commit()
        
        # Patch get_session to yield test_session
        with patch("larrybot.plugins.tasks.get_session", return_value=iter([test_session])):
            # Mock the reply_text method
            mock_update.message.reply_text = AsyncMock()
            
            # Test marking task as done
            mock_context.args = [str(task.id)]
            handler = command_registry._commands["/done"]
            await handler(mock_update, mock_context)
            
            # Check that the task was marked as done
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "✅ **Success**" in response_text
            assert "Task completed" in response_text
            assert parse_mode == 'MarkdownV2'
            
            # Verify in database
            test_session.expire_all()
            updated_task = TaskRepository(test_session).get_task_by_id(task.id)
            assert updated_task.done is True


class TestHabitPluginIntegration:
    """Integration tests specifically for habit plugin."""

    @pytest.mark.asyncio
    async def test_add_habit_integration(self, event_bus, command_registry, test_session, mock_update, mock_context):
        """Test adding a habit through the plugin."""
        from larrybot.plugins.habit import register
        
        # Register the habit plugin
        register(event_bus, command_registry)
        
        # Mock the reply_text method
        mock_update.message.reply_text = AsyncMock()
        
        # Test adding a habit
        mock_context.args = ["Integration test habit"]
        handler = command_registry._commands["/habit_add"]
        await handler(mock_update, mock_context)
        
        # Check that the habit was created and message was sent
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Integration test habit" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_mark_habit_done_integration(self, event_bus, command_registry, test_session, mock_update, mock_context, db_habit_factory):
        """Test marking a habit as done through the plugin."""
        from larrybot.plugins.habit import register
        
        # Register the habit plugin
        register(event_bus, command_registry)
        
        # Create a habit in the database using factory
        habit = db_habit_factory(name="Habit to complete")
        test_session.commit()
        
        # Patch get_session to yield test_session
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            # Mock the reply_text method
            mock_update.message.reply_text = AsyncMock()
            
            # Test marking habit as done
            mock_context.args = [habit.name]
            handler = command_registry._commands["/habit_done"]
            await handler(mock_update, mock_context)
            
            # Check that the habit was marked as done
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Habit completed for today" in response_text
            assert parse_mode == 'MarkdownV2'
            
            # Verify in database
            test_session.expire_all()
            updated_habit = HabitRepository(test_session).get_habit_by_name(habit.name)
            assert updated_habit.streak == 1
            assert updated_habit.last_completed is not None 