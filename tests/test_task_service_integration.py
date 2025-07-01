import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task import Task
import json

class TestTaskServiceIntegration:
    """Test task service integration with repository."""

    @pytest.mark.asyncio
    async def test_task_service_integration(self, test_session, db_task_factory):
        """Test task service integration with advanced features."""
        repo = TaskRepository(test_session)
        
        # Create a mock service that wraps the repository
        class MockTaskService:
            def __init__(self, repository):
                self.repo = repository
            
            async def create_task_with_metadata(self, **kwargs):
                return self.repo.add_task_with_metadata(**kwargs)
            
            async def update_task_priority(self, task_id, priority):
                return self.repo.update_priority(task_id, priority)
            
            async def get_tasks_by_priority(self, priority):
                return self.repo.get_tasks_by_priority(priority)
            
            async def start_time_tracking(self, task_id):
                return self.repo.start_time_tracking(task_id)
            
            async def stop_time_tracking(self, task_id):
                return self.repo.stop_time_tracking(task_id)
            
            async def complete_task(self, task_id):
                return self.repo.update_status(task_id, "Done")
        
        service = MockTaskService(repo)
        
        # Test creating task through service (pass tags as list)
        task_data = {
            "description": "Service test task",
            "priority": "High",
            "category": "Testing",
            "due_date": datetime.utcnow() + timedelta(days=3),
            "estimated_hours": 1.5,
            "tags": ["service", "test"]
        }
        
        task = await service.create_task_with_metadata(**task_data)
        assert task.description == "Service test task"
        assert task.priority == "High"
        assert task.category == "Testing"
        assert task.estimated_hours == 1.5
        assert task.tags == '["service", "test"]'
        task_id = task.id
        
        # Test updating task through service
        updated_task = await service.update_task_priority(task_id, "Critical")
        assert updated_task.priority == "Critical"
        
        # Test getting tasks through service
        high_priority_tasks = await service.get_tasks_by_priority("Critical")
        assert len(high_priority_tasks) == 1
        assert high_priority_tasks[0].id == task_id
        
        # Test time tracking through service
        success = await service.start_time_tracking(task_id)
        assert success
        
        # Simulate some time passing
        import asyncio
        await asyncio.sleep(0.1)
        
        duration = await service.stop_time_tracking(task_id)
        assert duration > 0
        
        # Test task completion through service
        completed_task = await service.complete_task(task_id)
        assert completed_task.status == "Done"
        assert completed_task.done 