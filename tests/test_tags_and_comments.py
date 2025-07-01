import pytest
import json
from larrybot.storage.task_repository import TaskRepository

class TestTagsAndComments:
    def test_tags(self, test_session, db_task_factory):
        repo = TaskRepository(test_session)
        
        # Create task using factory without default tags
        task = db_task_factory(description="Tagged task", tags='[]')
        task_id = task.id  # Store ID immediately
        
        # Test adding tags
        updated_task = repo.add_tags(task_id, ["urgent", "work", "project"])
        tags = set(json.loads(updated_task.tags))
        assert tags == {"urgent", "work", "project"}

        # Test adding more tags
        updated_task = repo.add_tags(task_id, ["urgent", "new-tag"])
        tags = set(json.loads(updated_task.tags))
        assert tags == {"urgent", "work", "project", "new-tag"}

        # Test removing tags
        updated_task = repo.remove_tags(task_id, ["urgent", "work"])
        tags = set(json.loads(updated_task.tags))
        assert tags == {"project", "new-tag"}

        # Test getting tasks by tag
        tagged_tasks = repo.get_tasks_by_tag("project")
        assert len(tagged_tasks) == 1
        assert tagged_tasks[0].id == task_id

    def test_comments(self, test_session, db_task_factory):
        repo = TaskRepository(test_session)
        
        # Create task using factory
        task = db_task_factory(description="Task with comments")
        task_id = task.id  # Store ID immediately
        
        # Test adding comments
        comment = repo.add_comment(task_id, "This is a test comment")
        assert comment.task_id == task_id
        assert comment.comment == "This is a test comment"
        assert comment.created_at is not None
        
        comment2 = repo.add_comment(task_id, "Another comment")
        assert comment2.task_id == task_id
        assert comment2.comment == "Another comment"
        
        # Test getting comments
        comments = repo.get_comments(task_id)
        assert len(comments) == 2
        assert any(c.comment == "This is a test comment" for c in comments)
        assert any(c.comment == "Another comment" for c in comments)
        assert comments[0].created_at <= comments[1].created_at 