import pytest
from datetime import datetime, timedelta
from larrybot.storage.task_repository import TaskRepository
from larrybot.storage.client_repository import ClientRepository
from larrybot.models.task import Task
from larrybot.models.client import Client

class TestClientIntegration:
    """Test client integration with task management."""

    def test_client_integration(self, test_session, db_client_factory, db_task_factory):
        """Test client integration with tasks."""
        task_repo = TaskRepository(test_session)
        client_repo = ClientRepository(test_session)
        
        # Create client using factory
        client = db_client_factory(name="Test Client")
        client.email = "test@example.com"
        client.phone = "123-456-7890"
        test_session.commit()
        client_id = client.id
        
        # Create task using factory, associate with client
        task = db_task_factory(
            description="Client project task",
            priority="High",
            category="Client Work",
            estimated_hours=5.0,
            tags='["client", "project"]',
            client_id=client_id
        )
        task_id = task.id
        
        assert task.client_id == client_id
        assert task.category == "Client Work"
        assert task.estimated_hours == 5.0
        
        # Test getting tasks by client (using client name)
        client_tasks = task_repo.get_tasks_by_client(client.name)
        assert len(client_tasks) == 1
        assert client_tasks[0].id == task_id
        assert client_tasks[0].description == "Client project task"
        
        # Test getting client tasks by status using filters
        todo_client_tasks = task_repo.get_tasks_with_filters(client_id=client_id, status="Todo")
        assert len(todo_client_tasks) == 1
        
        # Test updating task with client info
        updated_task = task_repo.update_priority(task_id, "Critical")
        task.estimated_hours = 8.0
        test_session.commit()
        assert updated_task.priority == "Critical"
        assert task.estimated_hours == 8.0
        assert updated_task.client_id == client_id  # Should remain unchanged 