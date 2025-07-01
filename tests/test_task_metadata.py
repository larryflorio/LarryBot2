import pytest
from datetime import datetime, timedelta
from larrybot.storage.task_repository import TaskRepository
import json

class TestTaskMetadata:
    def test_add_task_with_metadata(self, test_session, db_task_factory):
        repo = TaskRepository(test_session)
        task = db_task_factory(
            description="Test task with metadata",
            priority="High",
            due_date=datetime.utcnow() + timedelta(days=7),
            category="Testing",
            estimated_hours=2.5,
            tags=json.dumps(["test", "metadata"]),
            parent_id=None
        )
        assert task.description == "Test task with metadata"
        assert task.priority == "High"
        assert task.category == "Testing"
        assert task.estimated_hours == 2.5
        assert task.tags == '["test", "metadata"]'
        assert task.status == "Todo"
        assert not task.done

    def test_priority_management(self, test_session, db_task_factory):
        repo = TaskRepository(test_session)
        task1 = db_task_factory(description="Low priority task", priority="Low")
        task2 = db_task_factory(description="High priority task", priority="High")
        task3 = db_task_factory(description="Critical task", priority="Critical")
        high_tasks = repo.get_tasks_by_priority("High")
        assert len(high_tasks) == 1
        assert high_tasks[0].description == "High priority task"
        updated_task = repo.update_priority(task1.id, "Medium")
        assert updated_task.priority == "Medium"

    def test_due_date_management(self, test_session, db_task_factory):
        repo = TaskRepository(test_session)
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)
        task1 = db_task_factory(description="Task due today", due_date=datetime.combine(today, datetime.min.time()))
        task2 = db_task_factory(description="Task due tomorrow", due_date=datetime.combine(tomorrow, datetime.min.time()))
        task3 = db_task_factory(description="Overdue task", due_date=datetime.combine(yesterday, datetime.min.time()))
        overdue_tasks = repo.get_overdue_tasks()
        assert len(overdue_tasks) >= 1
        assert any(task.description == "Overdue task" for task in overdue_tasks)
        today_tasks = repo.get_tasks_due_today()
        assert len(today_tasks) >= 1
        assert any(task.description == "Task due today" for task in today_tasks)
        new_due_date = datetime.utcnow() + timedelta(days=14)
        updated_task = repo.update_due_date(task1.id, new_due_date)
        assert updated_task.due_date == new_due_date

    def test_category_management(self, test_session, db_task_factory):
        repo = TaskRepository(test_session)
        task1 = db_task_factory(description="Work task", category="Work")
        task2 = db_task_factory(description="Personal task", category="Personal")
        task3 = db_task_factory(description="Another work task", category="Work")
        work_tasks = repo.get_tasks_by_category("Work")
        assert len(work_tasks) == 2
        personal_tasks = repo.get_tasks_by_category("Personal")
        assert len(personal_tasks) == 1
        categories = repo.get_all_categories()
        assert "Work" in categories
        assert "Personal" in categories
        updated_task = repo.update_category(task1.id, "Urgent")
        assert updated_task.category == "Urgent"

    def test_status_management(self, test_session, db_task_factory):
        repo = TaskRepository(test_session)
        task = db_task_factory(description="Test task")
        assert task.status == "Todo"
        assert not task.done
        updated_task = repo.update_status(task.id, "In Progress")
        assert updated_task.status == "In Progress"
        assert not updated_task.done
        updated_task = repo.update_status(task.id, "Done")
        assert updated_task.status == "Done"
        assert updated_task.done
        done_tasks = repo.get_tasks_by_status("Done")
        assert len(done_tasks) >= 1 