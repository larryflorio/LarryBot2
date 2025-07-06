"""
Comprehensive callback query flow testing.

This test suite focuses on testing actual callback query operations
with realistic data and side effects, ensuring that button presses
result in the correct bot behavior.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from telegram import Update, User, Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from larrybot.handlers.bot import TelegramBotHandler
from larrybot.config.loader import Config
from larrybot.core.command_registry import CommandRegistry
from larrybot.storage.db import get_session
from larrybot.storage.task_repository import TaskRepository
from larrybot.storage.client_repository import ClientRepository
from larrybot.storage.habit_repository import HabitRepository
from larrybot.models.task import Task
from larrybot.models.client import Client
from larrybot.models.habit import Habit
from larrybot.core.dependency_injection import ServiceLocator


class TestCallbackQueryFlows:
    """Test callback query flows with realistic data and side effects."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        config = Mock(spec=Config)
        config.TELEGRAM_BOT_TOKEN = "test_token_12345"
        config.ALLOWED_TELEGRAM_USER_ID = 123456789
        config.get_single_user_info.return_value = {
            'authorized_user_id': 123456789,
            'bot_token_configured': True,
            'rate_limit_per_minute': 30
        }
        return config

    @pytest.fixture
    def mock_command_registry(self):
        """Create a mock command registry for testing."""
        registry = Mock(spec=CommandRegistry)
        registry._commands = {
            "/start": Mock(),
            "/help": Mock(),
            "/add": Mock(),
            "/list": Mock(),
            "/done": Mock(),
            "/habit_add": Mock(),
            "/health": Mock()
        }
        return registry

    @pytest.fixture
    def bot_handler(self, mock_config, mock_command_registry):
        """Create a bot handler instance for testing."""
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = Mock()
            mock_builder.return_value.token.return_value.build.return_value = mock_app
            handler = TelegramBotHandler(mock_config, mock_command_registry)
            handler.application = mock_app
            return handler

    @pytest.fixture
    def mock_context(self):
        """Create a mock Telegram context object."""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = []
        context.bot_data = {}
        context.user_data = {}
        return context

    @pytest.fixture
    def mock_callback_query(self):
        """Create a mock callback query for testing."""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.data = "test_callback_data"
        return query

    @pytest.fixture
    def mock_update_with_callback(self, mock_callback_query):
        """Create a mock update with callback query."""
        update = Mock(spec=Update)
        update.callback_query = mock_callback_query
        update.effective_user = Mock()
        update.effective_user.id = 123456789  # Authorized user
        return update

    @pytest.fixture(autouse=True)
    def setup_service_locator(self):
        """Setup ServiceLocator mock for all tests."""
        with patch('larrybot.handlers.bot.ServiceLocator') as mock_service_locator:
            mock_service_locator.has.return_value = False  # No event bus in tests
            yield mock_service_locator

    @pytest.fixture
    def session_context_manager(self, test_session):
        class SessionContextManager:
            def __enter__(self):
                return test_session
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        return SessionContextManager()

    # Task Operation Callback Tests

    @pytest.mark.asyncio
    async def test_task_done_callback_flow(self, bot_handler, mock_update_with_callback, mock_context, test_session, session_context_manager):
        """Test task done callback flow with realistic data."""
        # Arrange
        mock_update_with_callback.callback_query.data = "task_done:123"
        
        # Create a test task
        with test_session as session:
            repo = TaskRepository(session)
            task = Task(description="Test task for completion", priority="Medium", status="Todo", done=False)
            session.add(task)
            session.commit()
            task_id = task.id
            
            # Debug print to confirm task state before callback
            print(f"[TEST DEBUG] Created task: id={task.id}, status={task.status}, done={task.done}")
            
            # Update callback data to use the actual task ID
            mock_update_with_callback.callback_query.data = f"task_done:{task_id}"
            
            # Patch get_session to use the test session
            with patch('larrybot.storage.db.get_optimized_session', return_value=session_context_manager):
                # Act
                await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
                
                # Assert
                # Should acknowledge the callback query
                mock_update_with_callback.callback_query.answer.assert_called_once()
                
                # Should edit the message with completion confirmation
                mock_update_with_callback.callback_query.edit_message_text.assert_called()
                call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
                assert call_args is not None
                message_text = call_args[0][0]
                assert (
                    "✅ Task Completed" in message_text
                    or "Task marked as done" in message_text
                    or "✅ Already Complete" in message_text
                    or "Already marked as done" in message_text
                )
                
                # Verify task is actually marked as done
                # Fetch the task again to get the updated state
                updated_task = repo.get_task_by_id(task_id)
                assert updated_task.status == "Done"

    @pytest.mark.asyncio
    async def test_task_edit_callback_flow(self, bot_handler, mock_update_with_callback, mock_context, test_session, session_context_manager):
        """Test task edit callback flow."""
        # Arrange
        with test_session as session:
            repo = TaskRepository(session)
            task = Task(description="Original task description", priority="Low", status="Todo")
            session.add(task)
            session.commit()
            task_id = task.id
            
            mock_update_with_callback.callback_query.data = f"task_edit:{task_id}"
            
            # Patch get_session to use the test session
            with patch('larrybot.storage.db.get_optimized_session', return_value=session_context_manager):
                # Act
                await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
                
                # Assert
                mock_update_with_callback.callback_query.answer.assert_called_once()
                mock_update_with_callback.callback_query.edit_message_text.assert_called()
                
                # Should store task_id in context for edit mode
                assert mock_context.user_data['editing_task_id'] == task_id
                
                # Should show edit instructions
                call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
                message_text = call_args[0][0]
                assert "Edit" in message_text or "editing" in message_text
                
                # Fetch the updated task for further assertions if needed
                updated_task = repo.get_task_by_id(task_id)
                assert updated_task is not None

    @pytest.mark.asyncio
    async def test_task_delete_callback_flow(self, bot_handler, mock_update_with_callback, mock_context, test_session, session_context_manager):
        """Test task delete callback flow."""
        # Arrange
        with test_session as session:
            repo = TaskRepository(session)
            task = Task(description="Task to be deleted", priority="Medium", status="Todo")
            session.add(task)
            session.commit()
            task_id = task.id
            
            mock_update_with_callback.callback_query.data = f"task_delete:{task_id}"
            
            # Patch get_session to use the test session
            with patch('larrybot.storage.db.get_optimized_session', return_value=session_context_manager):
                # Act
                await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
                
                # Assert
                mock_update_with_callback.callback_query.answer.assert_called_once()
                mock_update_with_callback.callback_query.edit_message_text.assert_called()
                
                # Should show confirmation dialog
                call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
                message_text = call_args[0][0]
                assert "Confirm" in message_text or "delete" in message_text.lower()
                
                # Fetch the task to ensure it still exists (not deleted yet, just confirmation shown)
                updated_task = repo.get_task_by_id(task_id)
                assert updated_task is not None

    @pytest.mark.asyncio
    async def test_task_view_callback_flow(self, bot_handler, mock_update_with_callback, mock_context, test_session, session_context_manager):
        """Test task view callback flow."""
        # Arrange
        with test_session as session:
            repo = TaskRepository(session)
            task = Task(
                description="Task for viewing",
                priority="High",
                status="In Progress",
                category="Development"
            )
            session.add(task)
            session.commit()
            task_id = task.id
            
            mock_update_with_callback.callback_query.data = f"task_view:{task_id}"
            
            # Patch get_session to use the test session
            with patch('larrybot.storage.db.get_optimized_session', return_value=session_context_manager):
                # Act
                await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
                
                # Assert
                mock_update_with_callback.callback_query.answer.assert_called_once()
                mock_update_with_callback.callback_query.edit_message_text.assert_called()
                
                # Should show task details
                call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
                message_text = call_args[0][0]
                assert "Task for viewing" in message_text
                assert "High" in message_text
                assert "In Progress" in message_text
                
                # Fetch the updated task for further assertions if needed
                updated_task = repo.get_task_by_id(task_id)
                assert updated_task is not None

    # Client Operation Callback Tests

    @pytest.mark.asyncio
    async def test_client_view_callback_flow(self, bot_handler, mock_update_with_callback, mock_context, test_session, session_context_manager):
        """Test client view callback flow."""
        # Arrange
        with test_session as session:
            repo = ClientRepository(session)
            client = Client(name="Test Client")
            session.add(client)
            session.commit()
            client_id = client.id
            
            mock_update_with_callback.callback_query.data = f"client_view:{client_id}"
            
            # Patch get_session to use the test session
            with patch('larrybot.storage.db.get_optimized_session', return_value=session_context_manager):
                # Act
                await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
                
                # Assert
                mock_update_with_callback.callback_query.answer.assert_called_once()
                mock_update_with_callback.callback_query.edit_message_text.assert_called()
                
                # Should show client details
                call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
                message_text = call_args[0][0]
                assert "Test Client" in message_text
                
                # Fetch the updated client for further assertions if needed
                updated_client = repo.get_client_by_id(client_id)
                assert updated_client is not None

    @pytest.mark.asyncio
    async def test_client_tasks_callback_flow(self, bot_handler, mock_update_with_callback, mock_context, test_session, session_context_manager):
        """Test client tasks callback flow."""
        # Arrange
        with test_session as session:
            client_repo = ClientRepository(session)
            task_repo = TaskRepository(session)
            
            client = Client(name="Test Client")
            session.add(client)
            session.commit()
            client_id = client.id
            
            # Create tasks for this client using correct relationship
            task1 = Task(description="Client task 1", client_id=client_id)
            task2 = Task(description="Client task 2", client_id=client_id)
            session.add_all([task1, task2])
            session.commit()
            
            mock_update_with_callback.callback_query.data = f"client_tasks:{client_id}"
            
            # Patch get_session to use the test session
            with patch('larrybot.storage.db.get_optimized_session', return_value=session_context_manager):
                # Act
                await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
                
                # Assert
                mock_update_with_callback.callback_query.answer.assert_called_once()
                mock_update_with_callback.callback_query.edit_message_text.assert_called()
                
                # Should show tasks for the client
                call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
                message_text = call_args[0][0]
                assert "Tasks for Test Client" in message_text
                assert "Client task 1" in message_text
                assert "Client task 2" in message_text
                
                # Fetch the updated tasks for further assertions if needed
                session.expire_all()
                updated_tasks = task_repo.get_tasks_with_filters(client_id=client_id)
                assert len(updated_tasks) == 2

    # Habit Operation Callback Tests

    @pytest.mark.asyncio
    async def test_habit_done_callback_flow(self, bot_handler, mock_update_with_callback, mock_context, test_session, session_context_manager):
        """Test habit done callback flow."""
        # Arrange
        with test_session as session:
            repo = HabitRepository(session)
            habit = Habit(
                name="Test Habit",
                streak=5
            )
            session.add(habit)
            session.commit()
            habit_id = habit.id
            
            mock_update_with_callback.callback_query.data = f"habit_done:{habit_id}"
            
            # Patch get_session to use the test session
            with patch('larrybot.storage.db.get_optimized_session', return_value=session_context_manager):
                # Act
                await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
                
                # Assert
                mock_update_with_callback.callback_query.answer.assert_called_once()
                mock_update_with_callback.callback_query.edit_message_text.assert_called()
                
                # Should show completion confirmation
                call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
                message_text = call_args[0][0]
                assert "Habit completed" in message_text or "streak" in message_text.lower()
                
                # Fetch the updated habit for further assertions if needed
                updated_habit = repo.get_habit_by_id(habit_id)
                assert updated_habit is not None

    # Navigation Callback Tests

    @pytest.mark.asyncio
    async def test_navigation_main_callback_flow(self, bot_handler, mock_update_with_callback, mock_context):
        """Test navigation to main menu callback flow."""
        # Arrange
        mock_update_with_callback.callback_query.data = "nav_main"
        
        # Act
        await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
        
        # Assert
        mock_update_with_callback.callback_query.answer.assert_called_once()
        mock_update_with_callback.callback_query.edit_message_text.assert_called()
        
        # Should show main menu
        call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
        message_text = call_args[0][0]
        assert "Main Menu" in message_text
        
        # Should include keyboard with menu options
        reply_markup = call_args[1]['reply_markup']
        assert isinstance(reply_markup, InlineKeyboardMarkup)

    @pytest.mark.asyncio
    async def test_menu_tasks_callback_flow(self, bot_handler, mock_update_with_callback, mock_context):
        """Test menu tasks callback flow."""
        # Arrange
        mock_update_with_callback.callback_query.data = "menu_tasks"
        
        # Act
        await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
        
        # Assert
        mock_update_with_callback.callback_query.answer.assert_called_once()
        mock_update_with_callback.callback_query.edit_message_text.assert_called()
        
        # Should show task management menu
        call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
        message_text = call_args[0][0]
        assert "Task Management" in message_text

    # Bulk Operations Callback Tests

    @pytest.mark.asyncio
    async def test_bulk_status_menu_callback_flow(self, bot_handler, mock_update_with_callback, mock_context):
        """Test bulk status menu callback flow."""
        # Arrange
        mock_update_with_callback.callback_query.data = "bulk_status_menu"
        
        # Act
        await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
        
        # Assert
        mock_update_with_callback.callback_query.answer.assert_called_once()
        mock_update_with_callback.callback_query.edit_message_text.assert_called()
        
        # Should show bulk status update menu
        call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
        message_text = call_args[0][0]
        assert "Bulk Status Update" in message_text
        
        # Should include status options
        reply_markup = call_args[1]['reply_markup']
        assert isinstance(reply_markup, InlineKeyboardMarkup)

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_unknown_callback_data(self, bot_handler, mock_update_with_callback, mock_context):
        """Test handling of unknown callback data."""
        # Arrange
        mock_update_with_callback.callback_query.data = "unknown_action:123"
        
        # Act
        await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
        
        # Assert
        mock_update_with_callback.callback_query.answer.assert_called_once()
        mock_update_with_callback.callback_query.edit_message_text.assert_called()
        
        # Should show error message
        call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
        message_text = call_args[0][0]
        assert "Unknown action" in message_text or "not implemented" in message_text.lower()

    @pytest.mark.asyncio
    async def test_unauthorized_callback_query(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query from unauthorized user."""
        # Arrange
        mock_update_with_callback.effective_user.id = 999999999  # Unauthorized user
        mock_update_with_callback.callback_query.data = "task_done:123"
        
        # Act
        await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
        
        # Assert
        mock_update_with_callback.callback_query.answer.assert_called_once()
        mock_update_with_callback.callback_query.edit_message_text.assert_called()
        
        # Should show unauthorized message
        call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
        message_text = call_args[0][0]
        assert "Unauthorized access" in message_text

    # Edge Case Tests

    @pytest.mark.asyncio
    async def test_callback_query_timeout_handling(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query timeout handling."""
        # Arrange
        mock_update_with_callback.callback_query.data = "task_done:123"
        
        # Mock a timeout in the callback operations
        with patch.object(bot_handler, '_handle_callback_operations', side_effect=asyncio.TimeoutError()):
            # Act
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            
            # Assert
            mock_update_with_callback.callback_query.answer.assert_called_once()
            mock_update_with_callback.callback_query.edit_message_text.assert_called()
            
            # Should show timeout message
            call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
            message_text = call_args[0][0]
            assert "timed out" in message_text.lower() or "timeout" in message_text.lower()

    @pytest.mark.asyncio
    async def test_callback_query_exception_handling(self, bot_handler, mock_update_with_callback, mock_context):
        """Test callback query exception handling."""
        # Arrange
        mock_update_with_callback.callback_query.data = "task_done:123"
        
        # Mock an exception in the callback operations
        with patch.object(bot_handler, '_handle_callback_operations', side_effect=Exception("Test error")):
            # Act
            await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
            
            # Assert
            mock_update_with_callback.callback_query.answer.assert_called_once()
            mock_update_with_callback.callback_query.edit_message_text.assert_called()
            
            # Should show error message
            call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
            message_text = call_args[0][0]
            assert "error occurred" in message_text.lower() or "try again" in message_text.lower()

    # Integration Tests

    @pytest.mark.asyncio
    async def test_task_complete_workflow(self, bot_handler, mock_update_with_callback, mock_context, test_session, session_context_manager):
        """Test complete task workflow: view -> complete -> confirmation."""
        # Arrange
        with test_session as session:
            repo = TaskRepository(session)
            task = Task(description="Workflow test task", priority="Medium", status="Todo")
            session.add(task)
            session.commit()
            task_id = task.id
            
            # Patch get_session to use the test session
            with patch('larrybot.storage.db.get_optimized_session', return_value=session_context_manager):
                # Step 1: View task
                mock_update_with_callback.callback_query.data = f"task_view:{task_id}"
                await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
                
                # Step 2: Complete task
                mock_update_with_callback.callback_query.data = f"task_done:{task_id}"
                await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
                
                # Assert
                # Verify task is completed
                session.expire_all()
                repo = TaskRepository(session)
                updated_task = repo.get_task_by_id(task_id)
                assert updated_task.status == "Done"

    @pytest.mark.asyncio
    async def test_client_workflow(self, bot_handler, mock_update_with_callback, mock_context, test_session, session_context_manager):
        """Test client workflow: view client -> view tasks -> back to client."""
        # Arrange
        with test_session as session:
            client_repo = ClientRepository(session)
            task_repo = TaskRepository(session)
            
            client = Client(name="Workflow Client")
            session.add(client)
            session.commit()
            client_id = client.id
            
            # Create a task for this client
            task = Task(description="Client workflow task", client_id=client_id)
            session.add(task)
            session.commit()
            
            # Patch get_session to use the test session
            with patch('larrybot.storage.db.get_optimized_session', return_value=session_context_manager):
                # Step 1: View client
                mock_update_with_callback.callback_query.data = f"client_view:{client_id}"
                await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
                
                # Step 2: View client tasks
                mock_update_with_callback.callback_query.data = f"client_tasks:{client_id}"
                await bot_handler._handle_callback_query(mock_update_with_callback, mock_context)
                
                # Assert
                # Should show tasks for the client
                call_args = mock_update_with_callback.callback_query.edit_message_text.call_args
                message_text = call_args[0][0]
                assert "Client workflow task" in message_text
                
                # Fetch the updated tasks for further assertions if needed
                session.expire_all()
                task_repo = TaskRepository(session)
                updated_tasks = task_repo.get_tasks_with_filters(client_id=client_id)
                assert len(updated_tasks) == 1 