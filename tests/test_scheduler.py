import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from larrybot.scheduler import scheduler, check_due_reminders, start_scheduler
from larrybot.core.event_bus import EventBus
from larrybot.storage.reminder_repository import ReminderRepository

@pytest.fixture(autouse=True)
def reset_scheduler():
    # Ensure scheduler is shut down before and after each test
    if scheduler.running:
        scheduler.shutdown(wait=False)
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)

class TestScheduler:
    """Test cases for the scheduler module."""

    def test_scheduler_initialization(self):
        """Test that scheduler is properly initialized."""
        assert scheduler is not None
        assert hasattr(scheduler, 'add_job')
        assert hasattr(scheduler, 'start')
        assert hasattr(scheduler, 'shutdown')

    def test_start_scheduler(self, event_bus):
        """Test starting the scheduler."""
        # Start the scheduler
        start_scheduler(event_bus)
        
        # Check that the job was added
        job = scheduler.get_job('reminder_checker')
        assert job is not None
        assert job.func == check_due_reminders
        
        # Clean up
        scheduler.shutdown()

    def test_check_due_reminders_no_reminders(self, test_session, event_bus):
        """Test checking due reminders when none exist."""
        # Start scheduler
        start_scheduler(event_bus)
        
        # Track emitted events
        emitted_events = []
        def event_tracker(data):
            emitted_events.append(("reminder_due", data))
        
        event_bus.subscribe("reminder_due", event_tracker)
        
        # Check due reminders
        check_due_reminders()
        
        # No events should be emitted
        assert len(emitted_events) == 0
        
        # Clean up
        scheduler.shutdown()

    def test_check_due_reminders_with_due_reminder(self, test_session, event_bus, db_task_factory, db_reminder_factory):
        """Test checking due reminders when one exists."""
        # Start scheduler
        start_scheduler(event_bus)
        
        # Create a task and past reminder
        task = db_task_factory()
        task_id = task.id
        past_time = datetime.now() - timedelta(hours=1)
        reminder = db_reminder_factory(task_id=task_id, remind_at=past_time)
        reminder_id = reminder.id
        
        # Track emitted events
        emitted_events = []
        def event_tracker(data):
            emitted_events.append(("reminder_due", data))
        
        event_bus.subscribe("reminder_due", event_tracker)
        
        # Patch get_session to use test_session
        with patch("larrybot.scheduler.get_session", return_value=iter([test_session])):
            # Check due reminders
            check_due_reminders()
        
        # Event should be emitted
        assert len(emitted_events) == 1
        assert emitted_events[0][0] == "reminder_due"
        assert emitted_events[0][1].reminder_id == reminder_id
        
        # Reminder should be deleted
        repo = ReminderRepository(test_session)
        retrieved_reminder = repo.get_reminder_by_id(reminder_id)
        assert retrieved_reminder is None
        
        # Clean up
        scheduler.shutdown()

    def test_check_due_reminders_with_future_reminder(self, test_session, event_bus, db_task_factory, db_reminder_factory):
        """Test checking due reminders when only future reminders exist."""
        # Start scheduler
        start_scheduler(event_bus)
        
        # Create a task and future reminder
        task = db_task_factory()
        task_id = task.id
        future_time = datetime.now() + timedelta(hours=1)
        reminder = db_reminder_factory(task_id=task_id, remind_at=future_time)
        reminder_id = reminder.id
        
        # Track emitted events
        emitted_events = []
        def event_tracker(data):
            emitted_events.append(("reminder_due", data))
        
        event_bus.subscribe("reminder_due", event_tracker)
        
        # Check due reminders
        check_due_reminders()
        
        # No events should be emitted
        assert len(emitted_events) == 0
        
        # Reminder should still exist
        repo = ReminderRepository(test_session)
        retrieved_reminder = repo.get_reminder_by_id(reminder_id)
        assert retrieved_reminder is not None
        
        # Clean up
        scheduler.shutdown()

    def test_check_due_reminders_with_task_description(self, test_session, event_bus, db_task_factory, db_reminder_factory):
        """Test checking due reminders with task description."""
        # Start scheduler
        start_scheduler(event_bus)
        
        # Create a task first
        task = db_task_factory(description="Test task description")
        task_id = task.id  # Store ID before scheduler runs
        
        # Create a past reminder for that task
        past_time = datetime.now() - timedelta(hours=1)
        reminder = db_reminder_factory(task_id=task_id, remind_at=past_time)
        
        # Track emitted events
        emitted_events = []
        def event_tracker(data):
            emitted_events.append(("reminder_due", data))
        
        event_bus.subscribe("reminder_due", event_tracker)
        
        # Patch get_session to use test_session
        with patch("larrybot.scheduler.get_session", return_value=iter([test_session])):
            # Check due reminders
            check_due_reminders()
        
        # Event should be emitted with task description
        assert len(emitted_events) == 1
        event_data = emitted_events[0][1]
        assert event_data.task_description == "Test task description"
        assert event_data.task_id == task_id  # Use stored ID
        
        # Clean up
        scheduler.shutdown()

    def test_check_due_reminders_with_nonexistent_task(self, test_session, event_bus):
        """Test checking due reminders for a task that doesn't exist."""
        # Start scheduler
        start_scheduler(event_bus)
        
        # Create a reminder for a non-existent task
        repo = ReminderRepository(test_session)
        past_time = datetime.now() - timedelta(hours=1)
        reminder = repo.add_reminder(999, past_time)  # Non-existent task ID
        
        # Track emitted events
        emitted_events = []
        def event_tracker(data):
            emitted_events.append(("reminder_due", data))
        
        event_bus.subscribe("reminder_due", event_tracker)
        
        # Patch get_session to use test_session
        with patch("larrybot.scheduler.get_session", return_value=iter([test_session])):
            # Check due reminders
            check_due_reminders()
        
        # Event should be emitted with fallback description
        assert len(emitted_events) == 1
        event_data = emitted_events[0][1]
        assert event_data.task_description == "Task 999"
        assert event_data.task_id == 999
        
        # Clean up
        scheduler.shutdown()

    def test_check_due_reminders_multiple_reminders(self, test_session, event_bus, db_task_factory, db_reminder_factory):
        """Test checking due reminders with multiple reminders."""
        # Start scheduler
        start_scheduler(event_bus)
        
        # Create multiple tasks and reminders
        task1 = db_task_factory()
        task2 = db_task_factory()
        task3 = db_task_factory()
        
        past_time = datetime.now() - timedelta(hours=1)
        future_time = datetime.now() + timedelta(hours=1)
        
        past_reminder1 = db_reminder_factory(task_id=task1.id, remind_at=past_time)
        past_reminder2 = db_reminder_factory(task_id=task2.id, remind_at=past_time)
        future_reminder = db_reminder_factory(task_id=task3.id, remind_at=future_time)
        
        # Store IDs immediately after creation
        past_reminder1_id = past_reminder1.id
        past_reminder2_id = past_reminder2.id
        future_reminder_id = future_reminder.id
        
        # Track emitted events
        emitted_events = []
        def event_tracker(data):
            emitted_events.append(("reminder_due", data))
        
        event_bus.subscribe("reminder_due", event_tracker)
        
        # Patch get_session to use test_session
        with patch("larrybot.scheduler.get_session", return_value=iter([test_session])):
            # Check due reminders
            check_due_reminders()
        
        # Two events should be emitted (for past reminders)
        assert len(emitted_events) == 2
        
        # Future reminder should still exist
        repo = ReminderRepository(test_session)
        retrieved_future_reminder = repo.get_reminder_by_id(future_reminder_id)
        assert retrieved_future_reminder is not None
        
        # Past reminders should be deleted
        retrieved_past_reminder1 = repo.get_reminder_by_id(past_reminder1_id)
        retrieved_past_reminder2 = repo.get_reminder_by_id(past_reminder2_id)
        assert retrieved_past_reminder1 is None
        assert retrieved_past_reminder2 is None
        
        # Clean up
        scheduler.shutdown()

    def test_scheduler_without_event_bus(self, test_session, db_task_factory):
        """Test scheduler behavior when no event bus is provided."""
        # Start scheduler without event bus
        start_scheduler(None)
        
        # Create a task first
        task = db_task_factory()
        task_id = task.id
        
        # Create a past reminder for that task
        repo = ReminderRepository(test_session)
        past_time = datetime.now() - timedelta(hours=1)
        reminder = repo.add_reminder(task_id, past_time)
        reminder_id = reminder.id  # Store ID before scheduler runs
        
        # Patch get_session to use test_session
        with patch("larrybot.scheduler.get_session", return_value=iter([test_session])):
            # Check due reminders (should not crash)
            check_due_reminders()
        
        # Reminder should be deleted even without event bus
        retrieved_reminder = repo.get_reminder_by_id(reminder_id)
        assert retrieved_reminder is None
        
        # Clean up
        scheduler.shutdown()

    def test_scheduler_shutdown(self):
        """Test that scheduler shuts down gracefully."""
        # Start scheduler
        start_scheduler(None)
        
        # Shutdown the scheduler
        scheduler.shutdown()
        
        # Verify the scheduler is shut down
        assert scheduler.running is False 