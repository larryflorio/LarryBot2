import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from larrybot.services.task_service import TaskService
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task import Task
from larrybot.models.task_comment import TaskComment
from larrybot.models.task_dependency import TaskDependency
from larrybot.models.task_time_entry import TaskTimeEntry
from larrybot.models.client import Client
from larrybot.utils.datetime_utils import get_utc_now


class TestTaskService:
    """Test task service business logic and validation."""

    @pytest.fixture
    def mock_task_repository(self):
        """Mock task repository for testing."""
        repo = Mock(spec=TaskRepository)
        repo.add_task_with_metadata = Mock()
        repo.get_tasks_with_filters = Mock()
        repo.update_priority = Mock()
        repo.update_due_date = Mock()
        repo.update_category = Mock()
        repo.update_status = Mock()
        repo.get_task_by_id = Mock()
        repo.start_time_tracking = Mock()
        repo.stop_time_tracking = Mock()
        repo.add_subtask = Mock()
        repo.get_subtasks = Mock()
        repo.add_task_dependency = Mock()
        repo.get_task_dependencies = Mock()
        repo.add_tags = Mock()
        repo.get_tasks_by_tag = Mock()
        repo.add_comment = Mock()
        repo.get_comments = Mock()
        return repo

    @pytest.fixture
    def task_service(self, mock_task_repository):
        """Task service instance with mocked repository."""
        return TaskService(mock_task_repository)

    @pytest.fixture
    def sample_task(self, task_factory):
        """Sample task object for testing (real Task instance)."""
        return task_factory.build(
            id=1,
            description="Test task",
            priority="High",
            due_date=get_utc_now() + timedelta(days=7),
            category="Testing",
            status="Todo",
            done=False,
            started_at=None,
            created_at=get_utc_now(),
            updated_at=get_utc_now(),
            tags='["test", "sample"]',
            estimated_hours=2.5,
            actual_hours=None,
            parent_id=None
        )

    @pytest.fixture
    def sample_comment(self):
        """Sample comment object for testing."""
        comment = Mock(spec=TaskComment)
        comment.id = 1
        comment.task_id = 1
        comment.comment = "Test comment"
        comment.created_at = get_utc_now()
        return comment

    @pytest.mark.asyncio
    async def test_create_task_with_metadata_success(self, task_service, mock_task_repository, sample_task):
        """Test successful task creation with metadata."""
        # Arrange
        mock_task_repository.add_task_with_metadata.return_value = sample_task
        
        # Act
        result = await task_service.create_task_with_metadata(
            description="Test task",
            priority="High",
            due_date=get_utc_now() + timedelta(days=7),
            category="Testing",
            estimated_hours=2.5,
            tags=["test", "sample"],
            parent_id=None
        )
        
        # Assert
        assert result['success'] is True
        assert result['data']['description'] == "Test task"
        assert result['data']['priority'] == "High"
        assert result['data']['category'] == "Testing"
        mock_task_repository.add_task_with_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_metadata_invalid_priority(self, task_service):
        """Test task creation with invalid priority."""
        # Act
        result = await task_service.create_task_with_metadata(
            description="Test task",
            priority="Invalid"
        )
        
        # Assert
        assert result['success'] is False
        assert "Invalid priority" in result['message']

    @pytest.mark.asyncio
    async def test_create_task_with_metadata_past_due_date(self, task_service):
        """Test task creation with past due date."""
        # Act
        result = await task_service.create_task_with_metadata(
            description="Test task",
            due_date=get_utc_now() - timedelta(days=1)
        )
        
        # Assert
        assert result['success'] is False
        assert "Due date cannot be in the past" in result['message']

    @pytest.mark.asyncio
    async def test_create_task_with_metadata_invalid_parent(self, task_service, mock_task_repository):
        """Test task creation with invalid parent task."""
        # Arrange
        mock_task_repository.get_task_by_id.return_value = None
        
        # Act
        result = await task_service.create_task_with_metadata(
            description="Test task",
            parent_id=999
        )
        
        # Assert
        assert result['success'] is False
        assert "Parent task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_get_tasks_with_filters_success(self, task_service, mock_task_repository, sample_task):
        """Test successful task filtering."""
        # Arrange
        mock_task_repository.get_tasks_with_filters.return_value = [sample_task]
        
        # Act
        result = await task_service.get_tasks_with_filters(
            status="Todo",
            priority="High",
            category="Testing"
        )
        
        # Assert
        assert result['success'] is True
        assert len(result['data']) == 1
        assert result['data'][0]['description'] == "Test task"
        mock_task_repository.get_tasks_with_filters.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tasks_with_filters_repository_error(self, task_service, mock_task_repository):
        """Test task filtering when repository raises error."""
        # Arrange
        mock_task_repository.get_tasks_with_filters.side_effect = Exception("Database error")
        
        # Act
        result = await task_service.get_tasks_with_filters()
        
        # Assert
        assert result['success'] is False
        assert "Error retrieving tasks" in result['message']

    @pytest.mark.asyncio
    async def test_update_task_priority_success(self, task_service, mock_task_repository, sample_task):
        """Test successful priority update."""
        # Arrange
        mock_task_repository.update_priority.return_value = sample_task
        
        # Act
        result = await task_service.update_task_priority(1, "Critical")
        
        # Assert
        assert result['success'] is True
        assert result['data']['priority'] == "High"  # From sample task
        mock_task_repository.update_priority.assert_called_once_with(1, "Critical")

    @pytest.mark.asyncio
    async def test_update_task_priority_invalid_priority(self, task_service):
        """Test priority update with invalid priority."""
        # Act
        result = await task_service.update_task_priority(1, "Invalid")
        
        # Assert
        assert result['success'] is False
        assert "Invalid priority" in result['message']

    @pytest.mark.asyncio
    async def test_update_task_priority_task_not_found(self, task_service, mock_task_repository):
        """Test priority update for non-existent task."""
        # Arrange
        mock_task_repository.update_priority.return_value = None
        
        # Act
        result = await task_service.update_task_priority(999, "High")
        
        # Assert
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_update_task_due_date_success(self, task_service, mock_task_repository, sample_task):
        """Test successful due date update."""
        # Arrange
        mock_task_repository.update_due_date.return_value = sample_task
        future_date = get_utc_now() + timedelta(days=7)
        
        # Act
        result = await task_service.update_task_due_date(1, future_date)
        
        # Assert
        assert result['success'] is True
        mock_task_repository.update_due_date.assert_called_once_with(1, future_date)

    @pytest.mark.asyncio
    async def test_update_task_due_date_past_date(self, task_service):
        """Test due date update with past date."""
        # Act
        result = await task_service.update_task_due_date(1, get_utc_now() - timedelta(days=1))
        
        # Assert
        assert result['success'] is False
        assert "Due date cannot be in the past" in result['message']

    @pytest.mark.asyncio
    async def test_update_task_category_success(self, task_service, mock_task_repository, sample_task):
        """Test successful category update."""
        # Arrange
        mock_task_repository.update_category.return_value = sample_task
        
        # Act
        result = await task_service.update_task_category(1, "Development")
        
        # Assert
        assert result['success'] is True
        mock_task_repository.update_category.assert_called_once_with(1, "Development")

    @pytest.mark.asyncio
    async def test_update_task_category_task_not_found(self, task_service, mock_task_repository):
        """Test category update for non-existent task."""
        # Arrange
        mock_task_repository.update_category.return_value = None
        
        # Act
        result = await task_service.update_task_category(999, "Development")
        
        # Assert
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_update_task_status_success(self, task_service, mock_task_repository, sample_task):
        """Test successful status update."""
        # Arrange
        mock_task_repository.update_status.return_value = sample_task
        
        # Act
        result = await task_service.update_task_status(1, "In Progress")
        
        # Assert
        assert result['success'] is True
        mock_task_repository.update_status.assert_called_once_with(1, "In Progress")

    @pytest.mark.asyncio
    async def test_update_task_status_invalid_status(self, task_service):
        """Test status update with invalid status."""
        # Act
        result = await task_service.update_task_status(1, "Invalid")
        
        # Assert
        assert result['success'] is False
        assert "Invalid status" in result['message']

    @pytest.mark.asyncio
    async def test_start_time_tracking_success(self, task_service, mock_task_repository, sample_task):
        """Test successful time tracking start."""
        # Arrange
        mock_task_repository.get_task_by_id.return_value = sample_task
        mock_task_repository.start_time_tracking.return_value = True
        
        # Act
        result = await task_service.start_time_tracking(1)
        
        # Assert
        assert result['success'] is True
        assert "Time tracking started" in result['message']
        mock_task_repository.start_time_tracking.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_start_time_tracking_task_not_found(self, task_service, mock_task_repository):
        """Test time tracking start for non-existent task."""
        # Arrange
        mock_task_repository.get_task_by_id.return_value = None
        
        # Act
        result = await task_service.start_time_tracking(999)
        
        # Assert
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_start_time_tracking_already_started(self, task_service, mock_task_repository, sample_task):
        """Test time tracking start when already started."""
        # Arrange
        sample_task.started_at = get_utc_now()
        mock_task_repository.get_task_by_id.return_value = sample_task
        
        # Act
        result = await task_service.start_time_tracking(1)
        
        # Assert
        assert result['success'] is False
        assert "Time tracking already started" in result['message']

    @pytest.mark.asyncio
    async def test_stop_time_tracking_success(self, task_service, mock_task_repository, sample_task):
        """Test successful time tracking stop."""
        # Arrange
        sample_task.started_at = get_utc_now() - timedelta(hours=2)
        mock_task_repository.get_task_by_id.return_value = sample_task
        mock_task_repository.stop_time_tracking.return_value = 120  # 2 hours in minutes
        
        # Act
        result = await task_service.stop_time_tracking(1)
        
        # Assert
        assert result['success'] is True
        assert result['data']['task_id'] == 1
        mock_task_repository.stop_time_tracking.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_stop_time_tracking_not_started(self, task_service, mock_task_repository, sample_task):
        """Test time tracking stop when not started."""
        # Arrange
        sample_task.started_at = None
        mock_task_repository.get_task_by_id.return_value = sample_task
        
        # Act
        result = await task_service.stop_time_tracking(1)
        
        # Assert
        assert result['success'] is False
        assert "Time tracking not started" in result['message']

    @pytest.mark.asyncio
    async def test_add_subtask_success(self, task_service, mock_task_repository, sample_task):
        """Test successful subtask creation."""
        # Arrange
        mock_task_repository.get_task_by_id.return_value = sample_task
        mock_task_repository.add_subtask.return_value = sample_task
        
        # Act
        result = await task_service.add_subtask(1, "Subtask description")
        
        # Assert
        assert result['success'] is True
        mock_task_repository.add_subtask.assert_called_once_with(1, "Subtask description")

    @pytest.mark.asyncio
    async def test_add_subtask_parent_not_found(self, task_service, mock_task_repository):
        """Test subtask creation with non-existent parent."""
        # Arrange
        mock_task_repository.get_task_by_id.return_value = None
        
        # Act
        result = await task_service.add_subtask(999, "Subtask description")
        
        # Assert
        assert result['success'] is False
        assert "Parent task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_get_subtasks_success(self, task_service, mock_task_repository, sample_task):
        """Test successful subtasks retrieval."""
        # Arrange
        mock_task_repository.get_subtasks.return_value = [sample_task]
        
        # Act
        result = await task_service.get_subtasks(1)
        
        # Assert
        assert result['success'] is True
        assert len(result['data']) == 1
        mock_task_repository.get_subtasks.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_add_task_dependency_success(self, task_service, mock_task_repository, sample_task):
        """Test successful dependency creation."""
        # Arrange
        mock_task_repository.get_task_by_id.side_effect = [sample_task, sample_task]
        mock_task_repository.add_task_dependency.return_value = True
        
        # Act
        result = await task_service.add_task_dependency(1, 2)
        
        # Assert
        assert result['success'] is True
        mock_task_repository.add_task_dependency.assert_called_once_with(1, 2)

    @pytest.mark.asyncio
    async def test_add_task_dependency_task_not_found(self, task_service, mock_task_repository):
        """Test dependency creation with non-existent task."""
        # Arrange
        mock_task_repository.get_task_by_id.return_value = None
        
        # Act
        result = await task_service.add_task_dependency(999, 2)
        
        # Assert
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_add_task_dependency_dependency_not_found(self, task_service, mock_task_repository, sample_task):
        """Test dependency creation with non-existent dependency."""
        # Arrange
        mock_task_repository.get_task_by_id.side_effect = [sample_task, None]
        
        # Act
        result = await task_service.add_task_dependency(1, 999)
        
        # Assert
        assert result['success'] is False
        assert "Dependency task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_get_task_dependencies_success(self, task_service, mock_task_repository, sample_task):
        """Test successful dependencies retrieval."""
        # Arrange
        mock_task_repository.get_task_dependencies.return_value = [sample_task]
        
        # Act
        result = await task_service.get_task_dependencies(1)
        
        # Assert
        assert result['success'] is True
        assert len(result['data']) == 1
        mock_task_repository.get_task_dependencies.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_add_tags_success(self, task_service, mock_task_repository, sample_task):
        """Test successful tag addition."""
        # Arrange
        mock_task_repository.get_task_by_id.return_value = sample_task
        mock_task_repository.add_tags.return_value = sample_task
        
        # Act
        result = await task_service.add_tags(1, ["urgent", "important"])
        
        # Assert
        assert result['success'] is True
        mock_task_repository.add_tags.assert_called_once_with(1, ["urgent", "important"])

    @pytest.mark.asyncio
    async def test_add_tags_task_not_found(self, task_service, mock_task_repository):
        """Test tag addition for non-existent task."""
        # Arrange
        mock_task_repository.get_task_by_id.return_value = None
        
        # Act
        result = await task_service.add_tags(999, ["urgent"])
        
        # Assert
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_get_tasks_by_tag_success(self, task_service, mock_task_repository, sample_task):
        """Test successful tasks retrieval by tag."""
        # Arrange
        mock_task_repository.get_tasks_by_tag.return_value = [sample_task]
        
        # Act
        result = await task_service.get_tasks_by_tag("urgent")
        
        # Assert
        assert result['success'] is True
        assert len(result['data']) == 1
        mock_task_repository.get_tasks_by_tag.assert_called_once_with("urgent")

    @pytest.mark.asyncio
    async def test_add_comment_success(self, task_service, mock_task_repository, sample_task, sample_comment):
        """Test successful comment addition."""
        # Arrange
        mock_task_repository.get_task_by_id.return_value = sample_task
        mock_task_repository.add_comment.return_value = sample_comment
        
        # Act
        result = await task_service.add_comment(1, "Test comment")
        
        # Assert
        assert result['success'] is True
        mock_task_repository.add_comment.assert_called_once_with(1, "Test comment")

    @pytest.mark.asyncio
    async def test_add_comment_task_not_found(self, task_service, mock_task_repository):
        """Test comment addition for non-existent task."""
        # Arrange
        mock_task_repository.get_task_by_id.return_value = None
        
        # Act
        result = await task_service.add_comment(999, "Test comment")
        
        # Assert
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_get_comments_success(self, task_service, mock_task_repository, sample_comment):
        """Test successful comments retrieval."""
        # Arrange
        mock_task_repository.get_comments.return_value = [sample_comment]
        
        # Act
        result = await task_service.get_comments(1)
        
        # Assert
        assert result['success'] is True
        assert len(result['data']) == 1
        mock_task_repository.get_comments.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_task_analytics_success(self, task_service, mock_task_repository):
        """Test successful analytics generation."""
        # Arrange
        mock_task_repository.get_task_statistics.return_value = {
            'total_tasks': 10,
            'completed_tasks': 5,
            'overdue_tasks': 2
        }
        mock_task_repository.get_overdue_tasks.return_value = []
        mock_task_repository.get_tasks_due_today.return_value = []
        mock_task_repository.get_all_categories.return_value = ['Work', 'Personal']
        
        # Act
        result = await task_service.get_task_analytics()
        
        # Assert
        assert result['success'] is True
        assert 'total_tasks' in result['data']
        assert 'completed_tasks' in result['data']
        assert 'overdue_tasks' in result['data']

    @pytest.mark.asyncio
    async def test_suggest_priority_success(self, task_service):
        """Test successful priority suggestion."""
        # Act
        result = await task_service.suggest_priority("Complete project documentation")
        
        # Assert
        assert result['success'] is True
        assert 'suggested_priority' in result['data']
        assert result['data']['suggested_priority'] in ['Low', 'Medium', 'High', 'Critical']

    def test_task_to_dict_conversion(self, task_service, sample_task):
        """Test task object to dictionary conversion."""
        # Act
        task_dict = task_service._task_to_dict(sample_task)
        
        # Assert
        assert task_dict['id'] == 1
        assert task_dict['description'] == "Test task"
        assert task_dict['priority'] == "High"
        assert task_dict['category'] == "Testing"
        assert task_dict['status'] == "Todo"
        assert task_dict['done'] is False
        assert 'created_at' in task_dict
        assert 'updated_at' in task_dict

    def test_comment_to_dict_conversion(self, task_service, sample_comment):
        """Test comment object to dictionary conversion."""
        # Act
        comment_dict = task_service._comment_to_dict(sample_comment)
        
        # Assert
        assert comment_dict['id'] == 1
        assert comment_dict['task_id'] == 1
        assert comment_dict['comment'] == "Test comment"
        assert 'created_at' in comment_dict

    @pytest.mark.asyncio
    async def test_service_error_handling(self, task_service, mock_task_repository):
        """Test error handling in service methods."""
        # Arrange
        mock_task_repository.add_task_with_metadata.side_effect = Exception("Database connection failed")
        
        # Act
        result = await task_service.create_task_with_metadata(description="Test task")
        
        # Assert
        assert result['success'] is False
        assert "Error creating task" in result['message']
        assert "Database connection failed" in result['message']

    @pytest.mark.asyncio
    async def test_validation_edge_cases(self, task_service, mock_task_repository, sample_task):
        """Test validation edge cases."""
        # Arrange
        mock_task_repository.add_task_with_metadata.return_value = sample_task
        
        # Test empty description
        result = await task_service.create_task_with_metadata(description="")
        assert result['success'] is True  # Empty description should be allowed
        
        # Test very long description
        long_description = "A" * 1000
        result = await task_service.create_task_with_metadata(description=long_description)
        assert result['success'] is True  # Long description should be allowed
        
        # Test special characters in description
        special_description = "Task with special chars: !@#$%^&*()"
        result = await task_service.create_task_with_metadata(description=special_description)
        assert result['success'] is True  # Special characters should be allowed

    @pytest.mark.asyncio
    async def test_date_validation_edge_cases(self, task_service, mock_task_repository, sample_task):
        """Test date validation edge cases."""
        # Arrange
        mock_task_repository.add_task_with_metadata.return_value = sample_task
        
        # Test current date (should be valid)
        # Add a buffer to avoid race condition with get_utc_now()
        current_date = get_utc_now() + timedelta(seconds=5)
        mock_task_repository.add_task_with_metadata.return_value = sample_task
        result = await task_service.create_task_with_metadata(
            description="Test task",
            due_date=current_date
        )
        assert result['success'] is True
        
        # Test far future date (should be valid)
        far_future = get_utc_now() + timedelta(days=365)
        mock_task_repository.add_task_with_metadata.return_value = sample_task
        result = await task_service.create_task_with_metadata(
            description="Test task",
            due_date=far_future
        )
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_priority_validation_all_values(self, task_service, mock_task_repository, sample_task):
        """Test all valid priority values."""
        # Arrange
        mock_task_repository.add_task_with_metadata.return_value = sample_task
        
        valid_priorities = ['Low', 'Medium', 'High', 'Critical']
        
        for priority in valid_priorities:
            # Act
            result = await task_service.create_task_with_metadata(
                description="Test task",
                priority=priority
            )
            
            # Assert
            assert result['success'] is True, f"Priority {priority} should be valid"

    @pytest.mark.asyncio
    async def test_status_validation_all_values(self, task_service, mock_task_repository, sample_task):
        """Test all valid status values."""
        # Arrange
        mock_task_repository.update_status.return_value = sample_task
        
        valid_statuses = ['Todo', 'In Progress', 'Review', 'Done']
        
        for status in valid_statuses:
            # Act
            result = await task_service.update_task_status(1, status)
            
            # Assert
            assert result['success'] is True, f"Status {status} should be valid"


class TestTaskServiceComprehensive:
    """Comprehensive tests for TaskService covering all business logic paths."""

    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository."""
        return Mock(spec=TaskRepository)

    @pytest.fixture
    def task_service(self, mock_task_repository):
        """Create task service with mock repository."""
        return TaskService(mock_task_repository)

    @pytest.fixture
    def sample_task(self):
        """Create a sample task object."""
        task = Mock(spec=Task)
        task.id = 1
        task.description = "Test task"
        task.done = False
        task.priority = "Medium"
        task.due_date = None
        task.category = None
        task.status = "Todo"
        task.estimated_hours = None
        task.actual_hours = None
        task.started_at = None
        task.parent_id = None
        task.tags = "[]"
        task.client_id = None
        task.created_at = get_utc_now()
        task.updated_at = get_utc_now()
        return task

    # Error Handling and Validation Tests

    @pytest.mark.asyncio
    async def test_create_task_invalid_priority(self, task_service, mock_task_repository):
        """Test create task with invalid priority."""
        result = await task_service.create_task_with_metadata(
            description="Test task",
            priority="Invalid"
        )
        
        assert result['success'] is False
        assert "Invalid priority" in result['message']
        mock_task_repository.add_task_with_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_task_due_date_in_past(self, task_service, mock_task_repository):
        """Test create task with due date in the past."""
        past_date = get_utc_now() - timedelta(days=1)
        result = await task_service.create_task_with_metadata(
            description="Test task",
            due_date=past_date
        )
        
        assert result['success'] is False
        assert "Due date cannot be in the past" in result['message']
        mock_task_repository.add_task_with_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_task_parent_not_found(self, task_service, mock_task_repository):
        """Test create task with non-existent parent."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await task_service.create_task_with_metadata(
            description="Test task",
            parent_id=999
        )
        
        assert result['success'] is False
        assert "Parent task 999 not found" in result['message']
        mock_task_repository.add_task_with_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_task_repository_exception(self, task_service, mock_task_repository):
        """Test create task when repository raises exception."""
        mock_task_repository.add_task_with_metadata.side_effect = Exception("Database error")
        
        result = await task_service.create_task_with_metadata(
            description="Test task"
        )
        
        assert result['success'] is False
        assert "Error creating task" in result['message']

    @pytest.mark.asyncio
    async def test_update_priority_invalid_priority(self, task_service, mock_task_repository):
        """Test update priority with invalid priority value."""
        result = await task_service.update_task_priority(1, "Invalid")
        
        assert result['success'] is False
        assert "Invalid priority" in result['message']
        mock_task_repository.update_priority.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_priority_task_not_found(self, task_service, mock_task_repository):
        """Test update priority when task doesn't exist."""
        mock_task_repository.update_priority.return_value = None
        
        result = await task_service.update_task_priority(999, "High")
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_update_due_date_past_date(self, task_service, mock_task_repository):
        """Test update due date with past date."""
        past_date = get_utc_now() - timedelta(days=1)
        result = await task_service.update_task_due_date(1, past_date)
        
        assert result['success'] is False
        assert "Due date cannot be in the past" in result['message']
        mock_task_repository.update_due_date.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_due_date_task_not_found(self, task_service, mock_task_repository):
        """Test update due date when task doesn't exist."""
        future_date = get_utc_now() + timedelta(days=1)
        mock_task_repository.update_due_date.return_value = None
        
        result = await task_service.update_task_due_date(999, future_date)
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_update_category_task_not_found(self, task_service, mock_task_repository):
        """Test update category when task doesn't exist."""
        mock_task_repository.update_category.return_value = None
        
        result = await task_service.update_task_category(999, "Work")
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_update_status_invalid_status(self, task_service, mock_task_repository):
        """Test update status with invalid status value."""
        result = await task_service.update_task_status(1, "Invalid Status")
        
        assert result['success'] is False
        assert "Invalid status" in result['message']
        mock_task_repository.update_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_status_task_not_found(self, task_service, mock_task_repository):
        """Test update status when task doesn't exist."""
        mock_task_repository.update_status.return_value = None
        
        result = await task_service.update_task_status(999, "Done")
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    # Time Tracking Error Cases

    @pytest.mark.asyncio
    async def test_start_time_tracking_task_not_found(self, task_service, mock_task_repository):
        """Test start time tracking when task doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await task_service.start_time_tracking(999)
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_start_time_tracking_already_started(self, task_service, mock_task_repository, sample_task):
        """Test start time tracking when already started."""
        sample_task.started_at = get_utc_now()
        mock_task_repository.get_task_by_id.return_value = sample_task
        
        result = await task_service.start_time_tracking(1)
        
        assert result['success'] is False
        assert "Time tracking already started" in result['message']

    @pytest.mark.asyncio
    async def test_start_time_tracking_repository_failure(self, task_service, mock_task_repository, sample_task):
        """Test start time tracking when repository operation fails."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        mock_task_repository.start_time_tracking.return_value = False
        
        result = await task_service.start_time_tracking(1)
        
        assert result['success'] is False
        assert "Failed to start time tracking" in result['message']

    @pytest.mark.asyncio
    async def test_stop_time_tracking_task_not_found(self, task_service, mock_task_repository):
        """Test stop time tracking when task doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await task_service.stop_time_tracking(999)
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_stop_time_tracking_not_started(self, task_service, mock_task_repository, sample_task):
        """Test stop time tracking when not started."""
        sample_task.started_at = None
        mock_task_repository.get_task_by_id.return_value = sample_task
        
        result = await task_service.stop_time_tracking(1)
        
        assert result['success'] is False
        assert "Time tracking not started" in result['message']

    @pytest.mark.asyncio
    async def test_stop_time_tracking_repository_failure(self, task_service, mock_task_repository, sample_task):
        """Test stop time tracking when repository operation fails."""
        sample_task.started_at = get_utc_now()
        mock_task_repository.get_task_by_id.return_value = sample_task
        mock_task_repository.stop_time_tracking.return_value = None
        
        result = await task_service.stop_time_tracking(1)
        
        assert result['success'] is False
        assert "Failed to stop time tracking" in result['message']

    # Subtask Error Cases

    @pytest.mark.asyncio
    async def test_add_subtask_parent_not_found(self, task_service, mock_task_repository):
        """Test add subtask when parent doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await task_service.add_subtask(999, "Subtask description")
        
        assert result['success'] is False
        assert "Parent task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_add_subtask_creation_failure(self, task_service, mock_task_repository, sample_task):
        """Test add subtask when creation fails."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        mock_task_repository.add_subtask.return_value = None
        
        result = await task_service.add_subtask(1, "Subtask description")
        
        assert result['success'] is False
        assert "Failed to create subtask" in result['message']

    @pytest.mark.asyncio
    async def test_get_subtasks_parent_not_found(self, task_service, mock_task_repository):
        """Test get subtasks when parent doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await task_service.get_subtasks(999)
        
        assert result['success'] is False
        assert "Parent task 999 not found" in result['message']

    # Dependency Error Cases

    @pytest.mark.asyncio
    async def test_add_dependency_task_not_found(self, task_service, mock_task_repository):
        """Test add dependency when task doesn't exist."""
        mock_task_repository.get_task_by_id.side_effect = [None, Mock()]
        
        result = await task_service.add_task_dependency(999, 1)
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_add_dependency_dependency_not_found(self, task_service, mock_task_repository):
        """Test add dependency when dependency task doesn't exist."""
        mock_task_repository.get_task_by_id.side_effect = [Mock(), None]
        
        result = await task_service.add_task_dependency(1, 999)
        
        assert result['success'] is False
        assert "Dependency task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_add_dependency_self_reference(self, task_service, mock_task_repository):
        """Test add dependency when task depends on itself."""
        mock_task_repository.get_task_by_id.return_value = Mock()
        
        result = await task_service.add_task_dependency(1, 1)
        
        assert result['success'] is False
        assert "Task cannot depend on itself" in result['message']

    @pytest.mark.asyncio
    async def test_add_dependency_creation_failure(self, task_service, mock_task_repository):
        """Test add dependency when creation fails."""
        mock_task_repository.get_task_by_id.return_value = Mock()
        mock_task_repository.add_task_dependency.return_value = False
        
        result = await task_service.add_task_dependency(1, 2)
        
        assert result['success'] is False
        assert "Dependency already exists or failed to create" in result['message']

    @pytest.mark.asyncio
    async def test_get_dependencies_task_not_found(self, task_service, mock_task_repository):
        """Test get dependencies when task doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await task_service.get_task_dependencies(999)
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    # Tag Error Cases

    @pytest.mark.asyncio
    async def test_add_tags_task_not_found(self, task_service, mock_task_repository):
        """Test add tags when task doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await task_service.add_tags(999, ["tag1", "tag2"])
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_add_tags_empty_tags(self, task_service, mock_task_repository, sample_task):
        """Test add tags with empty tag list."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        
        result = await task_service.add_tags(1, [])
        
        assert result['success'] is False
        assert "No tags provided" in result['message']

    @pytest.mark.asyncio
    async def test_add_tags_repository_failure(self, task_service, mock_task_repository, sample_task):
        """Test add tags when repository operation fails."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        mock_task_repository.add_tags.return_value = None
        
        result = await task_service.add_tags(1, ["tag1"])
        
        assert result['success'] is False
        assert "Failed to add tags" in result['message']

    # Comment Error Cases

    @pytest.mark.asyncio
    async def test_add_comment_task_not_found(self, task_service, mock_task_repository):
        """Test add comment when task doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await task_service.add_comment(999, "Test comment")
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_add_comment_empty_comment(self, task_service, mock_task_repository, sample_task):
        """Test add comment with empty comment."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        
        result = await task_service.add_comment(1, "")
        
        assert result['success'] is False
        assert "Comment cannot be empty" in result['message']

    @pytest.mark.asyncio
    async def test_get_comments_task_not_found(self, task_service, mock_task_repository):
        """Test get comments when task doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await task_service.get_comments(999)
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    # Bulk Operations Error Cases

    @pytest.mark.asyncio
    async def test_bulk_update_status_invalid_status(self, task_service, mock_task_repository):
        """Test bulk update status with invalid status."""
        result = await task_service.bulk_update_status([1, 2, 3], "Invalid Status")
        
        assert result['success'] is False
        assert "Invalid status" in result['message']

    @pytest.mark.asyncio
    async def test_bulk_update_priority_invalid_priority(self, task_service, mock_task_repository):
        """Test bulk update priority with invalid priority."""
        result = await task_service.bulk_update_priority([1, 2, 3], "Invalid Priority")
        
        assert result['success'] is False
        assert "Invalid priority" in result['message']

    @pytest.mark.asyncio
    async def test_bulk_update_status_empty_list(self, task_service, mock_task_repository):
        """Test bulk update status with empty task list."""
        result = await task_service.bulk_update_status([], "Done")
        
        assert result['success'] is False
        assert "No task IDs provided" in result['message']

    # Manual Time Entry Error Cases

    @pytest.mark.asyncio
    async def test_manual_time_entry_task_not_found(self, task_service, mock_task_repository):
        """Test manual time entry when task doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await task_service.add_manual_time_entry(999, 60, "Test work")
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    @pytest.mark.asyncio
    async def test_manual_time_entry_invalid_duration(self, task_service, mock_task_repository, sample_task):
        """Test manual time entry with invalid duration."""
        mock_task_repository.get_task_by_id.return_value = sample_task
        
        result = await task_service.add_manual_time_entry(1, -60, "Test work")
        
        assert result['success'] is False
        assert "Duration must be positive" in result['message']

    @pytest.mark.asyncio
    async def test_get_time_summary_task_not_found(self, task_service, mock_task_repository):
        """Test get time summary when task doesn't exist."""
        mock_task_repository.get_task_by_id.return_value = None
        
        result = await task_service.get_task_time_summary(999)
        
        assert result['success'] is False
        assert "Task 999 not found" in result['message']

    # Advanced Filtering Error Cases

    @pytest.mark.asyncio
    async def test_search_tasks_empty_text(self, task_service, mock_task_repository):
        """Test search tasks with empty search text."""
        result = await task_service.search_tasks_by_text("")
        
        assert result['success'] is False
        assert "Search text cannot be empty" in result['message']

    @pytest.mark.asyncio
    async def test_get_tasks_by_multiple_tags_empty_tags(self, task_service, mock_task_repository):
        """Test get tasks by multiple tags with empty tag list."""
        result = await task_service.get_tasks_by_multiple_tags([])
        
        assert result['success'] is False
        assert "No tags provided" in result['message']

    @pytest.mark.asyncio
    async def test_get_tasks_by_time_range_invalid_range(self, task_service, mock_task_repository):
        """Test get tasks by time range with invalid date range."""
        start_date = get_utc_now()
        end_date = start_date - timedelta(days=1)
        
        result = await task_service.get_tasks_by_time_range(start_date, end_date)
        
        assert result['success'] is False
        assert "Start date must be before end date" in result['message']

    @pytest.mark.asyncio
    async def test_get_tasks_by_priority_range_invalid_priority(self, task_service, mock_task_repository):
        """Test get tasks by priority range with invalid priority."""
        result = await task_service.get_tasks_by_priority_range("Invalid", "High")
        
        assert result['success'] is False
        assert "Invalid priority" in result['message']

    @pytest.mark.asyncio
    async def test_productivity_report_invalid_date_range(self, task_service, mock_task_repository):
        """Test productivity report with invalid date range."""
        start_date = get_utc_now()
        end_date = start_date - timedelta(days=1)
        
        result = await task_service.get_productivity_report(start_date, end_date)
        
        assert result['success'] is False
        assert "Start date must be before end date" in result['message']

    # Success Path Tests for Complete Coverage

    @pytest.mark.asyncio
    async def test_create_task_success_with_all_metadata(self, task_service, mock_task_repository, sample_task):
        """Test successful task creation with all metadata."""
        future_date = get_utc_now() + timedelta(days=1)
        mock_task_repository.get_task_by_id.return_value = Mock()  # Parent exists
        mock_task_repository.add_task_with_metadata.return_value = sample_task
        
        result = await task_service.create_task_with_metadata(
            description="Test task",
            priority="High",
            due_date=future_date,
            category="Work",
            estimated_hours=2.5,
            tags=["urgent", "frontend"],
            parent_id=1
        )
        
        assert result['success'] is True
        assert result['data']['id'] == 1
        assert "Task created successfully" in result['message']

    @pytest.mark.asyncio
    async def test_execute_default_implementation(self, task_service, mock_task_repository, sample_task):
        """Test the default execute implementation."""
        mock_task_repository.add_task_with_metadata.return_value = sample_task
        
        result = await task_service.execute("Test task")
        
        assert result['success'] is True
        mock_task_repository.add_task_with_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_update_methods_success_paths(self, task_service, mock_task_repository, sample_task):
        """Test success paths for all update methods."""
        mock_task_repository.update_priority.return_value = sample_task
        mock_task_repository.update_due_date.return_value = sample_task
        mock_task_repository.update_category.return_value = sample_task
        mock_task_repository.update_status.return_value = sample_task
        
        # Test priority update
        future_date = get_utc_now() + timedelta(days=1)
        
        result = await task_service.update_task_priority(1, "High")
        assert result['success'] is True
        
        result = await task_service.update_task_due_date(1, future_date)
        assert result['success'] is True
        
        result = await task_service.update_task_category(1, "Work")
        assert result['success'] is True
        
        result = await task_service.update_task_status(1, "Done")
        assert result['success'] is True

    # Exception Handling in Repository Operations

    @pytest.mark.asyncio
    async def test_exception_handling_in_all_methods(self, task_service, mock_task_repository):
        """Test exception handling in all service methods."""
        mock_task_repository.get_task_by_id.side_effect = Exception("Database connection error")
        
        # Test that all methods handle exceptions gracefully
        methods_to_test = [
            (task_service.update_task_priority, (1, "High")),
            (task_service.update_task_due_date, (1, get_utc_now() + timedelta(days=1))),
            (task_service.update_task_category, (1, "Work")),
            (task_service.update_task_status, (1, "Done")),
            (task_service.start_time_tracking, (1,)),
            (task_service.stop_time_tracking, (1,)),
            (task_service.add_subtask, (1, "Subtask")),
            (task_service.get_subtasks, (1,)),
            (task_service.add_task_dependency, (1, 2)),
            (task_service.get_task_dependencies, (1,)),
            (task_service.add_tags, (1, ["tag1"])),
            (task_service.get_tasks_by_tag, ("tag1",)),
            (task_service.add_comment, (1, "Comment")),
            (task_service.get_comments, (1,)),
            (task_service.add_manual_time_entry, (1, 60, "Work")),
            (task_service.get_task_time_summary, (1,)),
        ]
        
        for method, args in methods_to_test:
            result = await method(*args)
            assert result['success'] is False
            assert "error" in result['message'].lower() or "Error" in result['message'] 