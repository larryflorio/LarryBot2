import pytest
from datetime import datetime, timedelta
from larrybot.storage.task_repository import TaskRepository
from larrybot.storage.habit_repository import HabitRepository
from larrybot.storage.reminder_repository import ReminderRepository
from larrybot.models.task import Task
from larrybot.models.habit import Habit
from larrybot.models.reminder import Reminder


class TestTaskRepository:
    """Test cases for TaskRepository."""

    def test_add_task(self, test_session):
        """Test adding a task."""
        repo = TaskRepository(test_session)
        task = repo.add_task("Test task")
        
        assert task.id is not None
        assert task.description == "Test task"
        assert task.done is False

    def test_get_task_by_id(self, test_session, db_task_factory):
        """Test getting a task by ID."""
        repo = TaskRepository(test_session)
        created_task = db_task_factory()
        retrieved_task = repo.get_task_by_id(created_task.id)
        
        assert retrieved_task is not None
        assert retrieved_task.id == created_task.id
        assert retrieved_task.description == created_task.description

    def test_get_task_by_id_not_found(self, test_session):
        """Test getting a task by non-existent ID."""
        repo = TaskRepository(test_session)
        task = repo.get_task_by_id(999)
        
        assert task is None

    def test_list_incomplete_tasks(self, test_session, db_task_factory):
        """Test listing incomplete tasks."""
        repo = TaskRepository(test_session)
        
        # Add some tasks using factories
        task1 = db_task_factory(description="Task 1")
        task2 = db_task_factory(description="Task 2")
        task3 = db_task_factory(description="Task 3")
        
        # Mark one as done
        repo.mark_task_done(task2.id)
        
        incomplete_tasks = repo.list_incomplete_tasks()
        
        assert len(incomplete_tasks) == 2
        task_ids = [t.id for t in incomplete_tasks]
        assert task1.id in task_ids
        assert task3.id in task_ids
        assert task2.id not in task_ids

    def test_mark_task_done(self, test_session, db_task_factory):
        """Test marking a task as done."""
        repo = TaskRepository(test_session)
        task = db_task_factory()
        
        updated_task = repo.mark_task_done(task.id)
        
        assert updated_task is not None
        assert updated_task.done is True
        
        # Verify in database
        retrieved_task = repo.get_task_by_id(task.id)
        assert retrieved_task.done is True

    def test_mark_task_done_already_completed(self, test_session, db_task_factory):
        """Test marking an already completed task as done."""
        repo = TaskRepository(test_session)
        task = db_task_factory()
        repo.mark_task_done(task.id)
        
        # Try to mark as done again
        result = repo.mark_task_done(task.id)
        
        assert result is None

    def test_edit_task(self, test_session, db_task_factory):
        """Test editing a task description."""
        repo = TaskRepository(test_session)
        task = db_task_factory(description="Original description")
        
        updated_task = repo.edit_task(task.id, "New description")
        
        assert updated_task is not None
        assert updated_task.description == "New description"
        
        # Verify in database
        retrieved_task = repo.get_task_by_id(task.id)
        assert retrieved_task.description == "New description"

    def test_edit_task_not_found(self, test_session):
        """Test editing a non-existent task."""
        repo = TaskRepository(test_session)
        result = repo.edit_task(999, "New description")
        
        assert result is None

    def test_remove_task(self, test_session, db_task_factory):
        """Test removing a task."""
        repo = TaskRepository(test_session)
        task = db_task_factory()
        
        removed_task = repo.remove_task(task.id)
        
        assert removed_task is not None
        assert removed_task.id == task.id
        
        # Verify it's gone from database
        retrieved_task = repo.get_task_by_id(task.id)
        assert retrieved_task is None

    def test_remove_task_not_found(self, test_session):
        """Test removing a non-existent task."""
        repo = TaskRepository(test_session)
        result = repo.remove_task(999)
        
        assert result is None


class TestHabitRepository:
    """Test cases for HabitRepository."""

    def test_add_habit(self, test_session):
        """Test adding a habit."""
        repo = HabitRepository(test_session)
        habit = repo.add_habit("Test habit")
        
        assert habit.id is not None
        assert habit.name == "Test habit"
        assert habit.streak == 0
        assert habit.last_completed is None

    def test_get_habit_by_name(self, test_session, db_habit_factory):
        """Test getting a habit by name."""
        repo = HabitRepository(test_session)
        created_habit = db_habit_factory()
        retrieved_habit = repo.get_habit_by_name(created_habit.name)
        
        assert retrieved_habit is not None
        assert retrieved_habit.id == created_habit.id
        assert retrieved_habit.name == created_habit.name

    def test_get_habit_by_name_not_found(self, test_session):
        """Test getting a habit by non-existent name."""
        repo = HabitRepository(test_session)
        habit = repo.get_habit_by_name("Nonexistent habit")
        
        assert habit is None

    def test_list_habits(self, test_session, db_habit_factory):
        """Test listing all habits."""
        repo = HabitRepository(test_session)
        
        habit1 = db_habit_factory(name="Habit 1")
        habit2 = db_habit_factory(name="Habit 2")
        
        habits = repo.list_habits()
        
        assert len(habits) == 2
        habit_names = [h.name for h in habits]
        assert "Habit 1" in habit_names
        assert "Habit 2" in habit_names

    def test_mark_habit_done_first_time(self, test_session, db_habit_factory):
        """Test marking a habit as done for the first time."""
        repo = HabitRepository(test_session)
        habit = db_habit_factory()
        
        updated_habit = repo.mark_habit_done(habit.name)
        
        assert updated_habit is not None
        assert updated_habit.streak == 1
        assert updated_habit.last_completed == datetime.now().date()

    def test_mark_habit_done_consecutive_days(self, test_session, db_habit_factory):
        """Test marking a habit as done on consecutive days."""
        repo = HabitRepository(test_session)
        habit = db_habit_factory()
        
        # Mark done yesterday
        yesterday = datetime.now().date() - timedelta(days=1)
        habit.last_completed = yesterday
        habit.streak = 1
        test_session.commit()
        
        # Mark done today
        updated_habit = repo.mark_habit_done(habit.name)
        
        assert updated_habit is not None
        assert updated_habit.streak == 2
        assert updated_habit.last_completed == datetime.now().date()

    def test_mark_habit_done_break_streak(self, test_session, db_habit_factory):
        """Test marking a habit as done after breaking the streak."""
        repo = HabitRepository(test_session)
        habit = db_habit_factory()
        
        # Mark done 3 days ago
        three_days_ago = datetime.now().date() - timedelta(days=3)
        habit.last_completed = three_days_ago
        habit.streak = 5
        test_session.commit()
        
        # Mark done today
        updated_habit = repo.mark_habit_done(habit.name)
        
        assert updated_habit is not None
        assert updated_habit.streak == 1  # Reset to 1
        assert updated_habit.last_completed == datetime.now().date()

    def test_mark_habit_done_same_day(self, test_session, db_habit_factory):
        """Test marking a habit as done on the same day."""
        repo = HabitRepository(test_session)
        habit = db_habit_factory()
        
        # Mark done today
        repo.mark_habit_done(habit.name)
        
        # Try to mark done again today
        result = repo.mark_habit_done(habit.name)
        
        assert result is not None
        assert result.streak == 1  # Should not increment

    def test_delete_habit(self, test_session, db_habit_factory):
        """Test deleting a habit."""
        repo = HabitRepository(test_session)
        habit = db_habit_factory()
        
        deleted_habit = repo.delete_habit(habit.name)
        
        assert deleted_habit is not None
        assert deleted_habit.name == habit.name
        
        # Verify it's gone
        retrieved_habit = repo.get_habit_by_name(habit.name)
        assert retrieved_habit is None

    def test_delete_habit_not_found(self, test_session):
        """Test deleting a non-existent habit."""
        repo = HabitRepository(test_session)
        result = repo.delete_habit("Nonexistent habit")
        
        assert result is None


class TestReminderRepository:
    """Test cases for ReminderRepository."""

    def test_add_reminder(self, test_session, db_task_factory):
        """Test adding a reminder."""
        repo = ReminderRepository(test_session)
        task = db_task_factory()
        remind_at = datetime.now() + timedelta(hours=1)
        
        reminder = repo.add_reminder(task.id, remind_at)
        
        assert reminder.id is not None
        assert reminder.task_id == task.id
        assert reminder.remind_at == remind_at

    def test_get_reminder_by_id(self, test_session, db_task_factory):
        """Test getting a reminder by ID."""
        repo = ReminderRepository(test_session)
        task = db_task_factory()
        remind_at = datetime.now() + timedelta(hours=1)
        created_reminder = repo.add_reminder(task.id, remind_at)
        
        retrieved_reminder = repo.get_reminder_by_id(created_reminder.id)
        
        assert retrieved_reminder is not None
        assert retrieved_reminder.id == created_reminder.id
        assert retrieved_reminder.task_id == created_reminder.task_id

    def test_list_reminders(self, test_session, db_task_factory):
        """Test listing all reminders."""
        repo = ReminderRepository(test_session)
        
        task1 = db_task_factory()
        task2 = db_task_factory()
        remind_at1 = datetime.now() + timedelta(hours=1)
        remind_at2 = datetime.now() + timedelta(hours=2)
        
        reminder1 = repo.add_reminder(task1.id, remind_at1)
        reminder2 = repo.add_reminder(task2.id, remind_at2)
        
        reminders = repo.list_reminders()
        
        assert len(reminders) == 2
        reminder_ids = [r.id for r in reminders]
        assert reminder1.id in reminder_ids
        assert reminder2.id in reminder_ids

    def test_list_due_reminders(self, test_session, db_task_factory):
        """Test listing due reminders."""
        repo = ReminderRepository(test_session)
        
        task1 = db_task_factory()
        task2 = db_task_factory()
        
        # Add a past reminder
        past_time = datetime.now() - timedelta(hours=1)
        past_reminder = repo.add_reminder(task1.id, past_time)
        
        # Add a future reminder
        future_time = datetime.now() + timedelta(hours=1)
        future_reminder = repo.add_reminder(task2.id, future_time)
        
        due_reminders = repo.list_due_reminders(datetime.now())
        
        assert len(due_reminders) == 1
        assert due_reminders[0].id == past_reminder.id

    def test_delete_reminder(self, test_session, db_task_factory):
        """Test deleting a reminder."""
        repo = ReminderRepository(test_session)
        task = db_task_factory()
        remind_at = datetime.now() + timedelta(hours=1)
        reminder = repo.add_reminder(task.id, remind_at)
        
        deleted_reminder = repo.delete_reminder(reminder.id)
        
        assert deleted_reminder is not None
        assert deleted_reminder.id == reminder.id
        
        # Verify it's gone
        retrieved_reminder = repo.get_reminder_by_id(reminder.id)
        assert retrieved_reminder is None

    def test_delete_reminder_not_found(self, test_session):
        """Test deleting a non-existent reminder."""
        repo = ReminderRepository(test_session)
        result = repo.delete_reminder(999)
        
        assert result is None 