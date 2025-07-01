import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task import Task

class TestTimeTracking:
    """Test time tracking functionality."""

    def test_time_tracking(self, test_session, db_task_factory):
        repo = TaskRepository(test_session)
        
        # Create task using factory without estimated hours
        task = db_task_factory(description="Time tracking test task", estimated_hours=None)
        task_id = task.id  # Store ID immediately

        fake_start = datetime(2024, 1, 1, 12, 0, 0)
        fake_end = fake_start + timedelta(hours=1)

        # Patch datetime.utcnow to simulate start time
        with patch("larrybot.storage.task_repository.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = fake_start
            mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)
            success = repo.start_time_tracking(task_id)
            assert success

        # Refresh task from database
        task = repo.get_task_by_id(task_id)
        assert task.started_at is not None

        # Patch datetime.utcnow to simulate stop time
        with patch("larrybot.storage.task_repository.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = fake_end
            mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)
            duration = repo.stop_time_tracking(task_id)
            assert duration is not None
            assert duration > 0

        # Refresh task from database
        task = repo.get_task_by_id(task_id)
        assert task.started_at is None
        assert task.actual_hours > 0

        # Test adding time entry
        start_time = fake_end - timedelta(hours=2)
        end_time = fake_end - timedelta(hours=1)
        success = repo.add_time_entry(task_id, start_time, end_time, "Manual entry")
        assert success

        # Test time summary
        summary = repo.get_task_time_summary(task_id)
        assert summary['estimated_hours'] == 0
        assert summary['actual_hours'] > 0
        assert summary['time_entries_count'] == 1 