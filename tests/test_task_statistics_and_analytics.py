import pytest
from larrybot.storage.task_repository import TaskRepository

class TestTaskStatisticsAndAnalytics:
    def test_task_statistics(self, test_session, db_task_factory):
        repo = TaskRepository(test_session)
        
        # Create tasks using factory with different priorities
        t1 = db_task_factory(description="Task 1", priority="High")
        t2 = db_task_factory(description="Task 2", priority="Medium")
        t3 = db_task_factory(description="Task 3", priority="Low")
        t4 = db_task_factory(description="Task 4", priority="High")
        
        # Store IDs immediately to avoid session detachment
        task_ids = [t1.id, t2.id, t3.id, t4.id]
        
        # Set status after creation
        repo.update_status(t1.id, "Todo")
        repo.update_status(t2.id, "In Progress")
        repo.update_status(t3.id, "Done")
        repo.update_status(t4.id, "Done")
        
        # Get statistics
        stats = repo.get_task_statistics()
        assert stats['total_tasks'] == 4
        assert stats['completed_tasks'] == 2
        assert stats['incomplete_tasks'] == 2
        assert stats['completion_rate'] == 50.0
        assert stats['priority_distribution']['High'] == 2
        assert stats['priority_distribution']['Medium'] == 1
        assert stats['priority_distribution']['Low'] == 1
        assert stats['status_distribution']['Todo'] == 1
        assert stats['status_distribution']['In Progress'] == 1
        assert stats['status_distribution']['Done'] == 2 