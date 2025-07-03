"""
Tests for Test Data Factories

This module tests the factory classes to ensure they create valid test data
with consistent defaults and proper customization capabilities.
"""

import pytest
from datetime import datetime, timedelta
from tests.factories import (
    TaskFactory, ClientFactory, HabitFactory, ReminderFactory,
    TaskCommentFactory, TaskDependencyFactory
)
from tests.utils import TestUtils, PerformanceTest
from larrybot.utils.basic_datetime import get_current_datetime


class TestTaskFactory:
    """Test TaskFactory functionality."""
    
    def test_task_factory_creates_valid_task(self, task_factory):
        """Test that task factory creates valid task instances."""
        task = task_factory.build()
        
        assert task is not None
        assert task.description is not None
        assert task.done is False
        assert task.priority_enum.name.title() == 'Medium'
        assert str(task.status) == 'Todo'
        assert task.category == 'General'
        assert task.estimated_hours == 2.0
        assert task.client_id is None
    
    def test_task_factory_with_custom_values(self, task_factory):
        """Test that task factory accepts custom values."""
        task = task_factory.build(
            description="Custom task",
            priority="High",
            category="Custom"
        )
        
        assert task.description == "Custom task"
        assert task.priority_enum.name.title() == 'High'  # Handle enum conversion
        assert task.category == "Custom"
    
    def test_task_factory_create_todo(self, task_factory):
        """Test creating todo task."""
        task = task_factory.create_todo()
        assert str(task.status) == 'Todo'  # Handle enum conversion
        assert task.done is False
    
    def test_task_factory_create_done(self, task_factory):
        """Test creating completed task."""
        task = task_factory.create_done()
        assert str(task.status) == 'Done'  # Handle enum conversion  
        assert task.done is True
    
    def test_task_factory_create_high_priority(self, task_factory):
        """Test creating high priority task."""
        task = task_factory.create_high_priority()
        assert task.priority_enum.name.title() == 'High'  # Handle enum conversion
    
    def test_task_factory_create_overdue(self, task_factory):
        """Test create_overdue method."""
        overdue_task = task_factory.create_overdue(description="Overdue Task")
        
        assert overdue_task.due_date < get_current_datetime()
        assert overdue_task.description == "Overdue Task"
    
    def test_task_factory_create_with_client(self, task_factory):
        """Test create_with_client method."""
        task_with_client = task_factory.create_with_client(
            client_id=123, 
            description="Client Task"
        )
        
        assert task_with_client.client_id == 123
        assert task_with_client.description == "Client Task"
    
    def test_task_factory_create_subtask(self, task_factory):
        """Test create_subtask method."""
        subtask = task_factory.create_subtask(
            parent_id=456, 
            description="Subtask"
        )
        
        assert subtask.parent_id == 456
        assert subtask.description == "Subtask"


class TestClientFactory:
    """Test ClientFactory functionality."""
    
    def test_client_factory_creates_valid_client(self, client_factory):
        """Test that client factory creates valid client instances."""
        client = client_factory.build()
        
        assert client is not None
        assert client.name is not None
        assert client.created_at is not None
    
    def test_client_factory_with_custom_name(self, client_factory):
        """Test client factory with custom name."""
        custom_client = client_factory.build(name="Acme Corporation")
        
        assert custom_client.name == "Acme Corporation"
    
    def test_client_factory_unique_names(self, client_factory):
        """Test that factory creates unique names."""
        client1 = client_factory.build()
        client2 = client_factory.build()
        
        assert client1.name != client2.name


class TestHabitFactory:
    """Test HabitFactory functionality."""
    
    def test_habit_factory_creates_valid_habit(self, habit_factory):
        """Test that habit factory creates valid habit instances."""
        habit = habit_factory.build()
        
        assert habit is not None
        assert habit.name is not None
        assert habit.streak == 0
        assert habit.last_completed is None
    
    def test_habit_factory_create_with_streak(self, habit_factory):
        """Test create_with_streak method."""
        habit_with_streak = habit_factory.create_with_streak(
            streak=5, 
            name="Exercise Habit"
        )
        
        assert habit_with_streak.streak == 5
        assert habit_with_streak.name == "Exercise Habit"
    
    def test_habit_factory_create_completed_today(self, habit_factory):
        """Test create_completed_today method."""
        completed_habit = habit_factory.create_completed_today(name="Daily Habit")
        
        assert completed_habit.last_completed == datetime.now().date()
        assert completed_habit.name == "Daily Habit"


class TestReminderFactory:
    """Test ReminderFactory functionality."""
    
    def test_reminder_factory_creates_valid_reminder(self, reminder_factory):
        """Test that reminder factory creates valid reminder instances."""
        reminder = reminder_factory.build()
        
        assert reminder is not None
        assert reminder.task_id == 1
        assert reminder.remind_at > get_current_datetime()
        assert reminder.created_at is not None
    
    def test_reminder_factory_create_overdue(self, reminder_factory):
        """Test create_overdue method."""
        overdue_reminder = reminder_factory.create_overdue(
            task_id=123
        )
        
        assert overdue_reminder.remind_at < get_current_datetime()
        assert overdue_reminder.task_id == 123
    
    def test_reminder_factory_create_sent(self, reminder_factory):
        """Test create_sent method."""
        sent_reminder = reminder_factory.create_sent(
            task_id=456
        )
        
        assert sent_reminder.remind_at < get_current_datetime()
        assert sent_reminder.task_id == 456


class TestFactoryIntegration:
    """Test factory integration and relationships."""
    
    def test_factories_fixture_provides_all_factories(self, factories):
        """Test that factories fixture provides all factory types."""
        assert 'task' in factories
        assert 'client' in factories
        assert 'habit' in factories
        assert 'reminder' in factories
        assert 'task_comment' in factories
        assert 'task_dependency' in factories
        
        # Test that they are the correct types
        assert isinstance(factories['task'], TaskFactory)
        assert isinstance(factories['client'], ClientFactory)
        assert isinstance(factories['habit'], HabitFactory)
    
    def test_create_test_data_set(self, factories):
        """Test creating a complete test data set."""
        data_set = TestUtils.create_test_data_set(factories)
        
        assert 'client' in data_set
        assert 'task' in data_set
        assert 'habit' in data_set
        
        # Verify relationships
        assert data_set['task'].client_id == data_set['client'].id


class TestDatabaseFactories:
    """Test database-integrated factories."""
    
    def test_db_task_factory_creates_persisted_task(self, db_task_factory):
        """Test that db_task_factory creates and persists tasks."""
        task = db_task_factory(description="Persisted Task")
        
        assert task.id is not None
        assert task.description == "Persisted Task"
    
    def test_db_client_factory_creates_persisted_client(self, db_client_factory):
        """Test that db_client_factory creates and persists clients."""
        client = db_client_factory(name="Persisted Client")
        
        assert client.id is not None
        assert client.name == "Persisted Client"
    
    def test_db_habit_factory_creates_persisted_habit(self, db_habit_factory):
        """Test that db_habit_factory creates and persists habits."""
        habit = db_habit_factory(name="Persisted Habit")
        
        assert habit.id is not None
        assert habit.name == "Persisted Habit"


class TestFactoryPerformance:
    """Test factory performance characteristics."""
    
    @pytest.mark.performance
    def test_task_factory_performance(self, task_factory):
        """Test task factory creation performance."""
        def create_tasks():
            return [task_factory.build() for _ in range(100)]
        
        metrics = PerformanceTest.benchmark_operation(create_tasks)
        PerformanceTest.assert_performance_threshold(
            metrics['duration'], 0.1, "Task factory creation"
        )
    
    @pytest.mark.performance
    def test_db_task_factory_performance(self, db_task_factory):
        """Test database task factory creation performance."""
        def create_db_tasks():
            return [db_task_factory() for _ in range(10)]
        
        metrics = PerformanceTest.benchmark_operation(create_db_tasks)
        PerformanceTest.assert_performance_threshold(
            metrics['duration'], 1.0, "Database task factory creation"
        )


class TestFactoryEdgeCases:
    """Test factory edge cases and error handling."""
    
    def test_factory_with_none_values(self, task_factory):
        """Test factory handles None values properly."""
        task = task_factory.build(
            description=None,
            priority=None,
            client_id=None
        )
        
        assert task.description is None
        assert task.priority is None
        assert task.client_id is None
    
    def test_factory_with_empty_strings(self, task_factory):
        """Test factory handles empty strings properly."""
        task = task_factory.build(
            description="",
            category=""
        )
        
        assert task.description == ""
        assert task.category == ""
    
    def test_factory_unique_id_generation(self, task_factory):
        """Test that factory generates unique IDs."""
        task1 = task_factory.build()
        task2 = task_factory.build()
        task3 = task_factory.build()
        
        # Extract IDs from descriptions (they contain unique numbers)
        id1 = int(task1.description.split()[-1])
        id2 = int(task2.description.split()[-1])
        id3 = int(task3.description.split()[-1])
        
        assert id1 != id2
        assert id2 != id3
        assert id1 != id3 