import pytest
from datetime import datetime, timedelta
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task import Task

class TestErrorHandling:
    """Test error handling in task operations."""

    def test_error_handling(self, test_session, db_task_factory):
        """Test error handling for invalid operations."""
        repo = TaskRepository(test_session)
        
        # Test updating non-existent task
        result = repo.update_priority(999, "High")
        assert result is None
        
        result = repo.update_status(999, "Done")
        assert result is None
        
        result = repo.update_due_date(999, datetime.utcnow())
        assert result is None
        
        # Test time tracking on non-existent task
        success = repo.start_time_tracking(999)
        assert not success
        
        duration = repo.stop_time_tracking(999)
        assert duration is None
        
        # Test adding self-dependency (should fail)
        task = db_task_factory(description="Test task")
        task_id = task.id
        success = repo.add_task_dependency(task_id, task_id)
        assert not success
        
        # Test adding duplicate dependency (should fail)
        task2 = db_task_factory(description="Test task 2")
        task2_id = task2.id
        success = repo.add_task_dependency(task_id, task2_id)
        assert success  # First dependency should succeed
        
        success = repo.add_task_dependency(task_id, task2_id)  # Duplicate
        assert not success
        
        # Test getting dependencies for non-existent task
        deps = repo.get_task_dependencies(999)
        assert len(deps) == 0
        
        # Test adding comment to non-existent task
        comment = repo.add_comment(999, "Test comment")
        assert comment is None
        
        # Test getting comments for non-existent task
        comments = repo.get_comments(999)
        assert len(comments) == 0
        
        # Test adding tags to non-existent task
        result = repo.add_tags(999, ["test"])
        assert result is None
        
        # Test removing tags from non-existent task
        result = repo.remove_tags(999, ["test"])
        assert result is None
        
        # Test getting tasks by non-existent tag
        tasks = repo.get_tasks_by_tag("non-existent-tag")
        assert len(tasks) == 0
        
        # Test getting tasks by non-existent category
        tasks = repo.get_tasks_by_category("NonExistentCategory")
        assert len(tasks) == 0
        
        # Test getting tasks by non-existent priority
        tasks = repo.get_tasks_by_priority("NonExistentPriority")
        assert len(tasks) == 0
        
        # Test getting tasks by non-existent status
        tasks = repo.get_tasks_by_status("NonExistentStatus")
        assert len(tasks) == 0 