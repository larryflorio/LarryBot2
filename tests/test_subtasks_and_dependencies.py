import pytest
from larrybot.storage.task_repository import TaskRepository

class TestSubtasksAndDependencies:
    def test_subtasks(self, test_session, db_task_factory):
        repo = TaskRepository(test_session)
        
        # Create parent task using factory
        parent = db_task_factory(description="Parent task")
        parent_id = parent.id  # Store ID immediately
        
        # Create subtasks
        subtask1 = repo.add_subtask(parent_id, "Subtask 1")
        subtask2 = repo.add_subtask(parent_id, "Subtask 2")
        
        assert subtask1.parent_id == parent_id
        assert subtask2.parent_id == parent_id
        
        subtasks = repo.get_subtasks(parent_id)
        assert len(subtasks) == 2
        assert any(task.description == "Subtask 1" for task in subtasks)
        assert any(task.description == "Subtask 2" for task in subtasks)

    def test_dependencies(self, test_session, db_task_factory):
        repo = TaskRepository(test_session)
        
        # Create tasks using factory
        task1 = db_task_factory(description="Task 1")
        task2 = db_task_factory(description="Task 2")
        task3 = db_task_factory(description="Task 3")
        
        # Store IDs immediately to avoid session detachment
        task1_id = task1.id
        task2_id = task2.id
        task3_id = task3.id
        
        # Test adding dependencies
        success = repo.add_task_dependency(task2_id, task1_id)
        assert success
        
        success = repo.add_task_dependency(task3_id, task2_id)
        assert success
        
        # Test getting dependencies
        deps = repo.get_task_dependencies(task2_id)
        assert len(deps) == 1
        assert deps[0].id == task1_id
        
        deps = repo.get_task_dependencies(task3_id)
        assert len(deps) == 1
        assert deps[0].id == task2_id
        
        # Test getting dependents
        dependents = repo.get_task_dependents(task1_id)
        assert len(dependents) == 1
        assert dependents[0].id == task2_id
        
        # Test removing dependency
        success = repo.remove_task_dependency(task2_id, task1_id)
        assert success
        
        deps = repo.get_task_dependencies(task2_id)
        assert len(deps) == 0 