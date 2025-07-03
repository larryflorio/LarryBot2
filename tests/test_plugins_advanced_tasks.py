import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from larrybot.plugins.advanced_tasks import (
    register,
    add_task_with_metadata_handler,
    priority_handler,
    due_date_handler,
    category_handler,
    status_handler,
    start_time_tracking_handler,
    stop_time_tracking_handler,
    subtask_handler,
    dependency_handler,
    tags_handler,
    comment_handler,
    comments_handler,
    advanced_tasks_handler,
    overdue_tasks_handler,
    today_tasks_handler,
    week_tasks_handler,
    search_tasks_handler,
    analytics_handler,
    suggest_priority_handler
)
from larrybot.core.event_bus import EventBus
from larrybot.core.command_registry import CommandRegistry
from larrybot.services.task_service import TaskService
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task import Task
from larrybot.models.task_comment import TaskComment
from larrybot.models.task_dependency import TaskDependency
from larrybot.models.task_time_entry import TaskTimeEntry


class TestAdvancedTasksPlugin:
    """Test advanced task management plugin functionality."""

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus for testing."""
        return Mock(spec=EventBus)

    @pytest.fixture
    def mock_command_registry(self):
        """Mock command registry for testing."""
        return Mock(spec=CommandRegistry)

    @pytest.fixture
    def mock_update(self):
        """Mock Telegram update object."""
        update = Mock(spec=Update)
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Mock Telegram context object."""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = []
        return context

    @pytest.fixture
    def mock_task_service(self):
        """Mock task service for testing."""
        service = Mock(spec=TaskService)
        service.create_task_with_metadata = AsyncMock()
        service.update_task_priority = AsyncMock()
        service.update_task_due_date = AsyncMock()
        service.update_task_category = AsyncMock()
        service.update_task_status = AsyncMock()
        service.start_time_tracking = AsyncMock()
        service.stop_time_tracking = AsyncMock()
        service.add_subtask = AsyncMock()
        service.add_task_dependency = AsyncMock()
        service.add_tags = AsyncMock()
        service.add_comment = AsyncMock()
        service.get_comments = AsyncMock()
        service.get_tasks_with_filters = AsyncMock()
        service.get_task_analytics = AsyncMock()
        service.suggest_priority = AsyncMock()
        return service

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing."""
        return {
            'id': 1,
            'description': 'Test task',
            'priority': 'High',
            'due_date': datetime.utcnow() + timedelta(days=7),
            'category': 'Testing',
            'status': 'Todo',
            'done': False,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

    def test_register_plugin(self, mock_event_bus, mock_command_registry):
        """Test plugin registration with command registry."""
        # Act
        register(mock_event_bus, mock_command_registry)
        
        # Assert
        assert mock_command_registry.register.call_count == 41  # Actual count after consolidation
        registered_commands = [call[0][0] for call in mock_command_registry.register.call_args_list]
        expected_commands = [
            "/addtask", "/priority", "/due", "/category", "/status",
            "/start", "/stop", "/subtask", "/depend", "/tags",
            "/comment", "/comments", "/tasks", "/overdue", "/today",
            "/week", "/search", "/analytics", "/suggest",
            "/bulk_status", "/bulk_priority", "/bulk_assign", "/bulk_delete",
            "/time_entry", "/time_summary",
            "/search_advanced", "/filter_advanced", "/tags_multi", "/time_range", "/priority_range",
            "/analytics_advanced", "/productivity_report", "/bulk_operations", "/analytics_detailed"
        ]
        for cmd in expected_commands:
            assert cmd in registered_commands

    @pytest.mark.asyncio
    async def test_add_task_with_metadata_handler_success(self, mock_update, mock_context, mock_task_service, sample_task_data):
        """Test successful task creation with metadata."""
        # Arrange
        mock_context.args = ["Test task", "High", "2025-07-15", "Work"]
        mock_task_service.create_task_with_metadata.return_value = {
            'success': True,
            'data': sample_task_data,
            'message': 'Task created successfully'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await add_task_with_metadata_handler(mock_update, mock_context)
            
            # Assert
            # Get the actual call arguments
            actual_call = mock_task_service.create_task_with_metadata.call_args
            actual_kwargs = actual_call[1]  # Get keyword arguments
            
            # Check the call was made with correct arguments
            assert actual_kwargs['description'] == "Test task"
            assert actual_kwargs['priority'] == "High"
            assert actual_kwargs['category'] == "Work"
            
            # Check due_date is timezone-aware and has correct date
            due_date = actual_kwargs['due_date']
            assert due_date.tzinfo is not None  # Should be timezone-aware
            assert due_date.date() == datetime(2025, 7, 15).date()  # Same date
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Task created" in response_text
            assert "ID: 1" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_add_task_with_metadata_handler_invalid_date(self, mock_update, mock_context, mock_task_service):
        """Test task creation with invalid date format."""
        # Arrange
        mock_context.args = ["Test task", "High", "invalid-date", "Work"]
        
        # Act
        await add_task_with_metadata_handler(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once_with("Invalid date format\\. Use YYYY\\-MM\\-DD", parse_mode='MarkdownV2')

    @pytest.mark.asyncio
    async def test_add_task_with_metadata_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test task creation when service returns error."""
        # Arrange
        mock_context.args = ["Test task", "High", "2025-07-15", "Work"]
        mock_task_service.create_task_with_metadata.return_value = {
            'success': False,
            'message': 'Database error'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await add_task_with_metadata_handler(mock_update, mock_context)
            
            # Assert
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Database error" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_priority_handler_success(self, mock_update, mock_context, mock_task_service, sample_task_data):
        """Test successful priority update."""
        # Arrange
        mock_context.args = ["1", "Critical"]
        mock_task_service.update_task_priority.return_value = {
            'success': True,
            'message': 'Priority updated successfully'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await priority_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.update_task_priority.assert_called_once_with(1, "Critical")
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Priority updated successfully" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_priority_handler_invalid_task_id(self, mock_update, mock_context):
        """Test priority update with invalid task ID."""
        # Arrange
        mock_context.args = ["invalid", "Critical"]
        
        # Act
        await priority_handler(mock_update, mock_context)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_due_date_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful due date update."""
        # Arrange
        mock_context.args = ["1", "2025-07-15"]
        mock_task_service.update_task_due_date.return_value = {
            'success': True,
            'message': 'Due date updated successfully'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await due_date_handler(mock_update, mock_context)
            
            # Assert
            # Get the actual call arguments
            actual_call = mock_task_service.update_task_due_date.call_args
            actual_args = actual_call[0]  # Get positional arguments
            
            # Check the call was made with correct arguments
            assert actual_args[0] == 1  # task_id
            
            # Check due_date is timezone-aware and has correct date
            due_date = actual_args[1]
            assert due_date.tzinfo is not None  # Should be timezone-aware
            assert due_date.date() == datetime(2025, 7, 15).date()  # Same date
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Due date updated successfully" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_due_date_handler_invalid_date(self, mock_update, mock_context):
        """Test due date update with invalid date format."""
        # Arrange
        mock_context.args = ["1", "invalid-date"]
        
        # Act
        await due_date_handler(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once_with("Invalid date format\\. Use YYYY\\-MM\\-DD", parse_mode='MarkdownV2')

    @pytest.mark.asyncio
    async def test_category_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful category update."""
        # Arrange
        mock_context.args = ["1", "Development"]
        mock_task_service.update_task_category.return_value = {
            'success': True,
            'message': 'Category updated successfully'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await category_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.update_task_category.assert_called_once_with(1, "Development")
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Category updated successfully" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_status_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful status update."""
        # Arrange
        mock_context.args = ["1", "In Progress"]
        mock_task_service.update_task_status.return_value = {
            'success': True,
            'message': 'Status updated successfully'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await status_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.update_task_status.assert_called_once_with(1, "In Progress")
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Status updated successfully" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_start_time_tracking_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful time tracking start."""
        # Arrange
        mock_context.args = ["1"]
        mock_task_service.start_time_tracking.return_value = {
            'success': True,
            'message': 'Time tracking started',
            'data': {'started_at': '2025-06-28 10:00:00'}
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await start_time_tracking_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.start_time_tracking.assert_called_once_with(1)
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Time tracking started" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_stop_time_tracking_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful time tracking stop."""
        # Arrange
        mock_context.args = ["1"]
        mock_task_service.stop_time_tracking.return_value = {
            'success': True,
            'message': 'Time tracking stopped',
            'data': {'duration_minutes': 150, 'total_hours': 2.5}
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await stop_time_tracking_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.stop_time_tracking.assert_called_once_with(1)
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Time tracking stopped" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_subtask_handler_success(self, mock_update, mock_context, mock_task_service, sample_task_data):
        """Test successful subtask creation."""
        # Arrange
        mock_context.args = ["1", "Subtask description"]
        # Add parent_id to sample data
        subtask_data = sample_task_data.copy()
        subtask_data['parent_id'] = 1
        mock_task_service.add_subtask.return_value = {
            'success': True,
            'data': subtask_data,
            'message': 'Subtask created successfully'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await subtask_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.add_subtask.assert_called_once_with(1, "Subtask description")
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Subtask created" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_dependency_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful dependency creation."""
        # Arrange
        mock_context.args = ["1", "2"]
        mock_task_service.add_task_dependency.return_value = {
            'success': True,
            'message': 'Dependency added successfully'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await dependency_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.add_task_dependency.assert_called_once_with(1, 2)
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Dependency added successfully" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_tags_handler_add_success(self, mock_update, mock_context, mock_task_service):
        """Test successful tag addition."""
        # Arrange
        mock_context.args = ["1", "add", "urgent,important"]
        mock_task_service.add_tags.return_value = {
            'success': True,
            'message': 'Tags added successfully'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await tags_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.add_tags.assert_called_once_with(1, ["urgent", "important"])
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Tags added successfully" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_comment_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful comment addition."""
        # Arrange
        mock_context.args = ["1", "This is a test comment"]
        mock_task_service.add_comment.return_value = {
            'success': True,
            'message': 'Comment added successfully'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await comment_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.add_comment.assert_called_once_with(1, "This is a test comment")
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Comment added successfully" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_comments_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful comments retrieval."""
        # Arrange
        mock_context.args = ["1"]
        mock_task_service.get_comments.return_value = {
            'success': True,
            'data': [
                {'id': 1, 'comment': 'Comment 1', 'created_at': '2025-06-28 10:00:00'},
                {'id': 2, 'comment': 'Comment 2', 'created_at': '2025-06-28 11:00:00'}
            ],
            'message': 'Comments retrieved successfully'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await comments_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.get_comments.assert_called_once_with(1)
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Comments for Task" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_advanced_tasks_handler_success(self, mock_update, mock_context, mock_task_service, sample_task_data):
        """Test successful advanced task filtering."""
        # Arrange
        mock_context.args = ["In Progress", "High"]
        mock_task_service.get_tasks_with_filters.return_value = {
            'success': True,
            'data': [sample_task_data],
            'message': 'Found 1 task'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await advanced_tasks_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.get_tasks_with_filters.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Tasks" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_overdue_tasks_handler_success(self, mock_update, mock_context, mock_task_service, sample_task_data):
        """Test successful overdue tasks retrieval."""
        # Arrange
        mock_task_service.get_tasks_with_filters.return_value = {
            'success': True,
            'data': [sample_task_data],
            'message': 'Found 1 overdue task'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await overdue_tasks_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.get_tasks_with_filters.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            # parse_mode = call_args[1].get('parse_mode')
            assert "Tasks due today" not in response_text  # sanity check
            assert "Tasks due this week" not in response_text  # sanity check
            assert "Tasks due" not in response_text  # sanity check
            assert "Overdue" in response_text or "overdue" in response_text

    @pytest.mark.asyncio
    async def test_today_tasks_handler_success(self, mock_update, mock_context, mock_task_service, sample_task_data):
        """Test successful today's tasks retrieval."""
        # Arrange
        mock_task_service.get_tasks_with_filters.return_value = {
            'success': True,
            'data': [sample_task_data],
            'message': 'Found 1 task due today'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await today_tasks_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.get_tasks_with_filters.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            assert "Tasks due today" in response_text

    @pytest.mark.asyncio
    async def test_week_tasks_handler_success(self, mock_update, mock_context, mock_task_service, sample_task_data):
        """Test successful week's tasks retrieval."""
        # Arrange
        mock_task_service.get_tasks_with_filters.return_value = {
            'success': True,
            'data': [sample_task_data],
            'message': 'Found 1 task due this week'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await week_tasks_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.get_tasks_with_filters.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            assert "Tasks due this week" in response_text

    @pytest.mark.asyncio
    async def test_search_tasks_handler_with_results(self):
        """Test search tasks handler with basic search - matching results found."""
        mock_update = Mock()
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = Mock()
        mock_context.args = ["groceries"]  # Query that will match one of our tasks
        
        # Mock task service to return tasks where one matches our query
        with patch('larrybot.plugins.advanced_tasks._get_task_service') as mock_get_service:
            mock_service = Mock()
            
            sample_tasks = [
                {'id': 1, 'description': 'Buy groceries', 'priority': 'Medium', 'status': 'Todo'},
                {'id': 2, 'description': 'Walk the dog', 'priority': 'Low', 'status': 'Todo'},
                {'id': 3, 'description': 'Get groceries for dinner', 'priority': 'High', 'status': 'Todo'}
            ]
            
            # For basic search, the handler calls get_tasks_with_filters then filters locally
            mock_service.get_tasks_with_filters = AsyncMock(return_value={
                'success': True, 
                'data': sample_tasks
            })
            
            mock_get_service.return_value = mock_service
            
            await search_tasks_handler(mock_update, mock_context)
            
            # Verify the service method was called correctly
            mock_service.get_tasks_with_filters.assert_called_once_with(done=False)
            
            # Verify response shows search results (should find 2 tasks containing "groceries")
            mock_update.message.reply_text.assert_called_once()
            response_text = mock_update.message.reply_text.call_args[0][0]
            assert "Basic Search Results for 'groceries'" in response_text
            assert "Buy groceries" in response_text
            assert "Get groceries for dinner" in response_text
            assert "Walk the dog" not in response_text  # This shouldn't match

    @pytest.mark.asyncio
    async def test_analytics_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful analytics retrieval."""
        # Arrange
        mock_task_service.get_task_analytics.return_value = {
            'success': True,
            'data': {
                'total_tasks': 10,
                'completed_tasks': 5,
                'completion_rate': 50.0
            },
            'message': 'Analytics retrieved successfully'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await analytics_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.get_task_analytics.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Analytics" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_suggest_priority_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful priority suggestion."""
        # Arrange
        mock_context.args = ["This is a test task description"]
        mock_task_service.suggest_priority.return_value = {
            'success': True,
            'data': {
                'description': 'This is a test task description',
                'suggested_priority': 'High'
            },
            'message': 'Priority suggested successfully'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await suggest_priority_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.suggest_priority.assert_called_once_with("This is a test task description")
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            assert "Priority Suggestion" in response_text
            assert "Description: This is a test task description" in response_text
            assert "Suggested Priority: High" in response_text

    @pytest.mark.asyncio
    async def test_error_handling_service_failure(self, mock_update, mock_context, mock_task_service):
        """Test error handling when service returns failure."""
        # Arrange
        mock_context.args = ["1", "High"]
        mock_task_service.update_task_priority.return_value = {
            'success': False,
            'message': 'Task not found'
        }
        
        with patch('larrybot.plugins.advanced_tasks._get_task_service', return_value=mock_task_service):
            # Act
            await priority_handler(mock_update, mock_context)
            
            # Assert
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Task not found" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_invalid_arguments_handling(self, mock_update, mock_context):
        """Test handling of invalid arguments."""
        # Arrange
        mock_context.args = ["1"]  # Missing second argument
        
        # Act
        await priority_handler(mock_update, mock_context)
        
        # Assert
        # The decorator should handle this and show usage message
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "requires at least 2 argument" in response_text

    def test_get_task_service_integration(self, test_session):
        """Test integration with actual task service."""
        # Arrange
        from larrybot.plugins.advanced_tasks import _get_task_service
        from larrybot.storage.task_repository import TaskRepository
        
        # Act
        service = _get_task_service()
        
        # Assert
        assert isinstance(service, TaskService)
        assert isinstance(service.task_repository, TaskRepository)

    @pytest.mark.asyncio
    async def test_search_tasks_handler_no_results(self):
        """Test search tasks handler with basic search - no matching results."""
        mock_update = Mock()
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = Mock()
        mock_context.args = ["nonexistent"]  # Query that won't match any tasks
        
        # Mock task service to return some tasks that don't match our query
        with patch('larrybot.plugins.advanced_tasks._get_task_service') as mock_get_service:
            mock_service = Mock()
            
            # Mock basic search: get_tasks_with_filters returns tasks, but none match query
            sample_tasks = [
                {'id': 1, 'description': 'Buy groceries', 'priority': 'Medium', 'status': 'Todo'},
                {'id': 2, 'description': 'Walk the dog', 'priority': 'Low', 'status': 'Todo'}
            ]
            
            # For basic search, the handler calls get_tasks_with_filters then filters locally
            mock_service.get_tasks_with_filters = AsyncMock(return_value={
                'success': True, 
                'data': sample_tasks
            })
            
            mock_get_service.return_value = mock_service
            
            await search_tasks_handler(mock_update, mock_context)
            
            # Verify the service method was called correctly for basic search
            mock_service.get_tasks_with_filters.assert_called_once_with(done=False)
            
            # Verify response shows no results found (since "nonexistent" doesn't match any task descriptions)
            mock_update.message.reply_text.assert_called_once()
            response_text = mock_update.message.reply_text.call_args[0][0]
            assert "🔍 No Results Found" in response_text
            assert "Query**: nonexistent" in response_text
            assert "Mode**: Basic" in response_text 