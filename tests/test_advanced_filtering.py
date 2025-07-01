import pytest
from larrybot.storage.task_repository import TaskRepository

class TestAdvancedFiltering:
    def test_advanced_filtering(self, test_session, db_task_factory):
        repo = TaskRepository(test_session)
        
        # Create tasks using factory with specific attributes
        task1 = db_task_factory(
            description="High priority work task", 
            priority="High", 
            category="Work"
        )
        task2 = db_task_factory(
            description="Low priority personal task", 
            priority="Low", 
            category="Personal"
        )
        task3 = db_task_factory(
            description="Medium priority work task", 
            priority="Medium", 
            category="Work"
        )
        
        # Store IDs immediately to avoid session detachment
        task_ids = [task1.id, task2.id, task3.id]
        
        # Test priority filtering
        high_tasks = repo.get_tasks_with_filters(priority="High")
        assert len(high_tasks) == 1
        assert high_tasks[0].description == "High priority work task"
        
        # Test category filtering
        work_tasks = repo.get_tasks_with_filters(category="Work")
        assert len(work_tasks) == 2
        
        # Test combined filtering
        high_work_tasks = repo.get_tasks_with_filters(priority="High", category="Work")
        assert len(high_work_tasks) == 1
        
        # Test status filtering
        todo_tasks = repo.get_tasks_with_filters(status="Todo")
        assert len(todo_tasks) == 3
        
        # Test completion filtering
        incomplete_tasks = repo.get_tasks_with_filters(done=False)
        assert len(incomplete_tasks) == 3 