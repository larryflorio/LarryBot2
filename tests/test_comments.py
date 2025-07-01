import pytest
from datetime import datetime
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task import Task
from larrybot.models.task_comment import TaskComment

class TestTaskComments:
    """Test task comment functionality."""

    def test_comments(self, test_session, db_task_factory, db_task_comment_factory):
        """Test comment management features."""
        repo = TaskRepository(test_session)
        
        # Create task using factory
        task = db_task_factory(description="Task with comments")
        
        # Store task ID immediately to avoid session detachment
        task_id = task.id
        
        # Test adding comment
        comment = repo.add_comment(task_id, "This is a test comment")
        assert comment.task_id == task_id
        assert comment.comment == "This is a test comment"
        assert comment.created_at is not None
        
        # Test adding another comment
        comment2 = repo.add_comment(task_id, "Another comment")
        assert comment2.task_id == task_id
        assert comment2.comment == "Another comment"
        
        # Test getting comments
        comments = repo.get_comments(task_id)
        assert len(comments) == 2
        assert any(c.comment == "This is a test comment" for c in comments)
        assert any(c.comment == "Another comment" for c in comments)
        
        # Test comment ordering (oldest first)
        assert comments[0].created_at <= comments[1].created_at 