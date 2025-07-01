import pytest
from datetime import datetime, timedelta
from larrybot.storage.task_repository import TaskRepository
from larrybot.services.task_service import TaskService
from larrybot.models.task import Task
from larrybot.models.task_comment import TaskComment
from larrybot.models.task_dependency import TaskDependency
from larrybot.models.task_time_entry import TaskTimeEntry
from larrybot.models.client import Client
import json

class TestAdvancedTaskFeatures:
    """Test advanced task management features."""

    def test_add_task_with_metadata(self, test_session, db_task_factory):
        """Test creating a task with advanced metadata."""
        repo = TaskRepository(test_session)
        
        # Create task with metadata using factory
        task = db_task_factory(
            description="Test task with metadata",
            priority="High",
            due_date=datetime.utcnow() + timedelta(days=7),
            category="Testing",
            estimated_hours=2.5,
            tags='["test", "metadata"]',
            parent_id=None
        )
        
        # Store ID immediately to avoid session detachment
        task_id = task.id
        
        assert task.description == "Test task with metadata"
        assert task.priority == "High"
        assert task.category == "Testing"
        assert task.estimated_hours == 2.5
        assert task.tags == '["test", "metadata"]'
        assert task.status == "Todo"
        assert not task.done 