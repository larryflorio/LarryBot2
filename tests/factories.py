"""
Test Data Factories for LarryBot2

This module provides factory classes for creating test data with consistent defaults
and easy customization. Factories reduce maintenance burden and improve test consistency.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from larrybot.models import Task, Client, Habit, Reminder, TaskComment, TaskDependency


class BaseFactory:
    """Base factory class with common functionality."""
    
    def __init__(self, model_class):
        self.model_class = model_class
        self._counter = 0
    
    def _get_unique_id(self) -> int:
        """Generate unique ID for factory instances."""
        self._counter += 1
        return self._counter
    
    def build(self, **kwargs) -> Any:
        """Build model instance with defaults and overrides."""
        defaults = self.get_defaults()
        defaults.update(kwargs)
        return self.model_class(**defaults)
    
    def get_defaults(self) -> Dict[str, Any]:
        """Get default values for the model."""
        raise NotImplementedError


class TaskFactory(BaseFactory):
    """Factory for creating Task instances with consistent defaults."""
    
    def __init__(self):
        super().__init__(Task)
    
    def get_defaults(self) -> Dict[str, Any]:
        return {
            'description': f'Test Task {self._get_unique_id()}',
            'done': False,
            'priority': 'Medium',
            'status': 'Todo',
            'category': 'General',
            'due_date': datetime.now() + timedelta(days=1),
            'estimated_hours': 2.0,
            'actual_hours': None,
            'started_at': None,
            'parent_id': None,
            'tags': '["test", "automated"]',
            'client_id': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
    
    def create_todo(self, **kwargs) -> Task:
        """Create a todo task."""
        return self.build(status='Todo', done=False, **kwargs)
    
    def create_in_progress(self, **kwargs) -> Task:
        """Create an in-progress task."""
        return self.build(status='In Progress', done=False, started_at=datetime.now(), **kwargs)
    
    def create_done(self, **kwargs) -> Task:
        """Create a completed task."""
        return self.build(status='Done', done=True, **kwargs)
    
    def create_high_priority(self, **kwargs) -> Task:
        """Create a high priority task."""
        return self.build(priority='High', **kwargs)
    
    def create_overdue(self, **kwargs) -> Task:
        """Create an overdue task."""
        return self.build(due_date=datetime.now() - timedelta(days=1), **kwargs)
    
    def create_with_client(self, client_id: int, **kwargs) -> Task:
        """Create a task assigned to a client."""
        return self.build(client_id=client_id, **kwargs)
    
    def create_subtask(self, parent_id: int, **kwargs) -> Task:
        """Create a subtask."""
        return self.build(parent_id=parent_id, **kwargs)


class ClientFactory(BaseFactory):
    """Factory for creating Client instances."""
    
    def __init__(self):
        super().__init__(Client)
    
    def get_defaults(self) -> Dict[str, Any]:
        return {
            'name': f'Test Client {self._get_unique_id()}',
            'created_at': datetime.now()
        }
    
    def create_with_tasks(self, task_count: int = 3, **kwargs) -> Client:
        """Create a client with associated tasks."""
        client = self.build(**kwargs)
        task_factory = TaskFactory()
        for _ in range(task_count):
            task_factory.create_with_client(client.id)
        return client


class HabitFactory(BaseFactory):
    """Factory for creating Habit instances."""
    
    def __init__(self):
        super().__init__(Habit)
    
    def get_defaults(self) -> Dict[str, Any]:
        return {
            'name': f'Test Habit {self._get_unique_id()}',
            'streak': 0,
            'last_completed': None,
            'created_at': datetime.now()
        }
    
    def create_with_streak(self, streak: int, **kwargs) -> Habit:
        """Create a habit with a specific streak."""
        return self.build(streak=streak, **kwargs)
    
    def create_completed_today(self, **kwargs) -> Habit:
        """Create a habit completed today."""
        return self.build(last_completed=datetime.now().date(), **kwargs)


class ReminderFactory(BaseFactory):
    """Factory for creating Reminder instances."""
    
    def __init__(self):
        super().__init__(Reminder)
    
    def get_defaults(self) -> Dict[str, Any]:
        return {
            'task_id': 1,
            'remind_at': datetime.now() + timedelta(hours=1),
            'created_at': datetime.now()
        }
    
    def create_overdue(self, **kwargs) -> Reminder:
        """Create an overdue reminder."""
        return self.build(remind_at=datetime.now() - timedelta(hours=1), **kwargs)
    
    def create_sent(self, **kwargs) -> Reminder:
        """Create a reminder that should have been sent (past due)."""
        return self.build(remind_at=datetime.now() - timedelta(hours=1), **kwargs)


class TaskCommentFactory(BaseFactory):
    """Factory for creating TaskComment instances."""
    
    def __init__(self):
        super().__init__(TaskComment)
    
    def get_defaults(self) -> Dict[str, Any]:
        return {
            'task_id': 1,
            'comment': f'Test Comment {self._get_unique_id()}',
            'created_at': datetime.now()
        }


class TaskDependencyFactory(BaseFactory):
    """Factory for creating TaskDependency instances."""
    
    def __init__(self):
        super().__init__(TaskDependency)
    
    def get_defaults(self) -> Dict[str, Any]:
        return {
            'task_id': 1,
            'dependency_id': 2,
            'created_at': datetime.now()
        } 