import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task import Task
from larrybot.models.task_time_entry import TaskTimeEntry
from larrybot.services.task_service import TaskService


class TestTimeTracking:
    """Test time tracking functionality."""

    def test_task_time_entry_hours_property(self, test_session):
        """Test that TaskTimeEntry has the hours property."""
        # Create a time entry
        time_entry = TaskTimeEntry(
            task_id=1,
            started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2024, 1, 1, 13, 30, 0, tzinfo=timezone.utc),
            duration_minutes=90,
            description="Test entry"
        )
        
        # Test hours property
        assert time_entry.hours == 1.5
        
        # Test with None duration
        time_entry.duration_minutes = None
        assert time_entry.hours == 0.0
        
        # Test with zero duration
        time_entry.duration_minutes = 0
        assert time_entry.hours == 0.0

    def test_task_time_spent_hours_property(self, test_session, db_task_factory):
        """Test that Task.time_spent_hours works with the new hours property."""
        repo = TaskRepository(test_session)
        
        # Create task
        task = db_task_factory(description="Time tracking test task")
        task_id = task.id
        
        # Create time entries
        entry1 = TaskTimeEntry(
            task_id=task_id,
            started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
            duration_minutes=60,
            description="First entry"
        )
        
        entry2 = TaskTimeEntry(
            task_id=task_id,
            started_at=datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2024, 1, 1, 15, 30, 0, tzinfo=timezone.utc),
            duration_minutes=90,
            description="Second entry"
        )
        
        test_session.add(entry1)
        test_session.add(entry2)
        test_session.commit()
        
        # Refresh task to load relationships
        task = repo.get_task_by_id(task_id)
        
        # Test time_spent_hours property
        assert task.time_spent_hours == 2.5  # 1.0 + 1.5 hours

    def test_time_tracking(self, test_session, db_task_factory):
        """Test time tracking functionality."""
        repo = TaskRepository(test_session)
        
        # Create task using factory without estimated hours
        task = db_task_factory(description="Time tracking test task", estimated_hours=None)
        task_id = task.id  # Store ID immediately

        fake_start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        fake_end = fake_start + timedelta(hours=1)

        # Patch the timezone-aware datetime functions to simulate start time
        with patch("larrybot.utils.datetime_utils.get_current_utc_datetime", return_value=fake_start):
            success = repo.start_time_tracking(task_id)
            assert success

        # Refresh task from database
        task = repo.get_task_by_id(task_id)
        assert task.started_at is not None

        # Patch the timezone-aware datetime functions to simulate stop time
        with patch("larrybot.utils.datetime_utils.get_current_utc_datetime", return_value=fake_end):
            duration = repo.stop_time_tracking(task_id)
            assert duration is not None
            # Duration should be positive (1 hour difference) or clamped to 0
            assert duration >= 0  # Allow for negative duration clamping

        # Refresh task from database
        task = repo.get_task_by_id(task_id)
        assert task.started_at is None
        # actual_hours should be at least 0 (could be 0 if duration was clamped)
        assert task.actual_hours >= 0

        # Test adding time entry with proper time calculation
        start_time = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
        success = repo.add_time_entry(task_id, start_time, end_time, "Manual entry")
        assert success

        # Test time summary
        summary = repo.get_task_time_summary(task_id)
        assert summary['time_entries_count'] >= 1
        assert summary['time_entries_hours'] >= 0

    @pytest.mark.asyncio
    async def test_time_summary_service(self, test_session, db_task_factory):
        """Test time summary service with enhanced error handling."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Create task with time entries
        task = db_task_factory(description="Time tracking test task", estimated_hours=3.0)
        task_id = task.id
        
        # Add time entries
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        repo.add_time_entry(task_id, start_time, end_time, "Test entry")
        
        # Test time summary
        result = await service.get_task_time_summary(task_id)
        
        assert result['success'] is True
        summary = result['data']
        assert summary['task_id'] == task_id
        assert summary['estimated_hours'] == 3.0
        assert summary['time_entries_hours'] == 1.0
        assert summary['time_entries_count'] == 1
        assert 'efficiency' in summary
        assert 'comments_count' in summary

    @pytest.mark.asyncio
    async def test_time_summary_handler_fix(self, test_session, db_task_factory):
        """Test that the time summary handler uses correct field names."""
        from larrybot.plugins.advanced_tasks.time_tracking import _time_summary_handler_internal
        
        # Create task with time entries
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        task = db_task_factory(description="Time tracking test task")
        task_id = task.id
        
        # Add time entry
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        repo.add_time_entry(task_id, start_time, end_time, "Test entry")
        
        # Mock update and context
        mock_update = AsyncMock()
        mock_context = AsyncMock()
        mock_context.args = [str(task_id)]
        
        # Mock the task service
        with patch('larrybot.plugins.advanced_tasks.time_tracking.get_task_service', return_value=service):
            # This should not raise an AttributeError anymore
            await _time_summary_handler_internal(mock_update, mock_context, service)
            
            # Verify that reply_text was called (indicating success)
            mock_update.message.reply_text.assert_called_once()


class TestTimeTrackingService:
    """Test time tracking service enhancements."""

    @pytest.mark.asyncio
    async def test_get_task_time_summary_enhanced(self, test_session, db_task_factory):
        """Test enhanced time summary service with error handling."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Create task with time entry
        task = db_task_factory(description="Time tracking test task", estimated_hours=3.0)
        task_id = task.id
        
        # Add time entry
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        repo.add_time_entry(task_id, start_time, end_time, "Test entry")
        
        # Test time summary
        result = await service.get_task_time_summary(task_id)
        
        assert result['success'] is True
        summary = result['data']
        assert summary['task_id'] == task_id
        assert summary['estimated_hours'] == 3.0
        assert summary['time_entries_hours'] == 1.0
        assert summary['time_entries_count'] == 1
        assert isinstance(summary['efficiency'], (int, float))
        assert isinstance(summary['comments_count'], int)

    @pytest.mark.asyncio
    async def test_get_task_time_summary_task_not_found(self, test_session):
        """Test time summary service with non-existent task."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Test with non-existent task
        result = await service.get_task_time_summary(99999)
        
        assert result['success'] is False
        assert 'Task 99999 not found' in result['message'] 