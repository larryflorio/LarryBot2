import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from larrybot.storage.task_repository import TaskRepository
from larrybot.services.task_service import TaskService
from larrybot.models.task import Task
from larrybot.plugins.advanced_tasks import (
    bulk_status_handler, bulk_priority_handler, bulk_assign_handler, 
    bulk_delete_handler, time_entry_handler, time_summary_handler
)

class TestBulkOperations:
    """Test bulk operations functionality."""

    def test_bulk_operations_repository(self, test_session, db_task_factory):
        """Test bulk operations at repository level."""
        repo = TaskRepository(test_session)
        
        # Create tasks using factory
        task1 = db_task_factory(description="Task 1")
        task2 = db_task_factory(description="Task 2")
        task3 = db_task_factory(description="Task 3")
        
        # Store IDs immediately to avoid session detachment
        task_ids = [task1.id, task2.id, task3.id]
        
        # Test bulk status update
        updated_count = repo.bulk_update_status(task_ids, "In Progress")
        assert updated_count == 3
        
        for task_id in task_ids:
            task = repo.get_task_by_id(task_id)
            assert task.status == "In Progress"
        
        # Test bulk priority update
        updated_count = repo.bulk_update_priority(task_ids, "High")
        assert updated_count == 3
        
        for task_id in task_ids:
            task = repo.get_task_by_id(task_id)
            assert task.priority == "High"
        
        # Test bulk category update
        updated_count = repo.bulk_update_category(task_ids, "Testing")
        assert updated_count == 3
        
        for task_id in task_ids:
            task = repo.get_task_by_id(task_id)
            assert task.category == "Testing"

    def test_bulk_assign_to_client(self, test_session, db_task_factory, db_client_factory):
        """Test bulk assign to client."""
        repo = TaskRepository(test_session)
        
        # Create client and tasks
        client = db_client_factory(name="TestClient")
        client_id = client.id  # Store client ID
        task1 = db_task_factory(description="Task 1")
        task2 = db_task_factory(description="Task 2")
        
        task_ids = [task1.id, task2.id]
        
        # Test bulk assign
        updated_count = repo.bulk_assign_to_client(task_ids, "TestClient")
        assert updated_count == 2
        
        for task_id in task_ids:
            task = repo.get_task_by_id(task_id)
            assert task.client_id == client_id

    def test_bulk_delete_tasks(self, test_session, db_task_factory):
        """Test bulk delete tasks."""
        repo = TaskRepository(test_session)
        
        # Create tasks and store IDs immediately
        task_ids = []
        for i in range(3):
            task = db_task_factory(description=f"Task {i+1}")
            task_ids.append(task.id)
        
        # Verify tasks exist
        for task_id in task_ids:
            assert repo.get_task_by_id(task_id) is not None
        
        # Test bulk delete
        deleted_count = repo.bulk_delete_tasks(task_ids)
        assert deleted_count == 3
        
        # Verify tasks are deleted with fresh queries
        test_session.expire_all()  # Clear session cache
        for task_id in task_ids:
            # Use a fresh query to avoid detached instance issues
            task_count = test_session.query(Task).filter(Task.id == task_id).count()
            assert task_count == 0

    def test_manual_time_entry(self, test_session, db_task_factory):
        """Test manual time entry functionality."""
        repo = TaskRepository(test_session)
        
        # Create task
        task = db_task_factory(description="Time tracking test task")
        task_id = task.id
        
        # Test adding manual time entry
        from larrybot.utils.basic_datetime import get_utc_now
        start_time = get_utc_now() - timedelta(hours=2)
        end_time = get_utc_now() - timedelta(hours=1)
        
        success = repo.add_time_entry(task_id, start_time, end_time, "Manual entry test")
        assert success
        
        # Test time summary
        summary = repo.get_task_time_summary(task_id)
        assert summary['time_entries_count'] == 1
        assert summary['time_entries_hours'] == 1.0  # 1 hour difference

class TestBulkOperationsService:
    """Test bulk operations at service level."""

    @pytest.mark.asyncio
    async def test_bulk_update_status_service(self, test_session, db_task_factory):
        """Test bulk status update at service level."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Create tasks
        task1 = db_task_factory(description="Task 1")
        task2 = db_task_factory(description="Task 2")
        task_ids = [task1.id, task2.id]
        
        # Test bulk status update
        result = await service.bulk_update_status(task_ids, "In Progress")
        
        assert result['success'] is True
        assert result['data']['updated_count'] == 2
        assert result['data']['new_status'] == "In Progress"
        
        # Verify tasks were updated
        for task_id in task_ids:
            task = repo.get_task_by_id(task_id)
            assert task.status == "In Progress"

    @pytest.mark.asyncio
    async def test_bulk_update_priority_service(self, test_session, db_task_factory):
        """Test bulk priority update at service level."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Create tasks
        task1 = db_task_factory(description="Task 1")
        task2 = db_task_factory(description="Task 2")
        task_ids = [task1.id, task2.id]
        
        # Test bulk priority update
        result = await service.bulk_update_priority(task_ids, "High")
        
        assert result['success'] is True
        assert result['data']['updated_count'] == 2
        assert result['data']['new_priority'] == "High"
        
        # Verify tasks were updated
        for task_id in task_ids:
            task = repo.get_task_by_id(task_id)
            assert task.priority == "High"

    @pytest.mark.asyncio
    async def test_bulk_assign_to_client_service(self, test_session, db_task_factory, db_client_factory):
        """Test bulk assign to client at service level."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Create client and tasks
        client = db_client_factory(name="TestClient")
        task1 = db_task_factory(description="Task 1")
        task2 = db_task_factory(description="Task 2")
        task_ids = [task1.id, task2.id]
        
        # Test bulk assign
        result = await service.bulk_assign_to_client(task_ids, "TestClient")
        
        assert result['success'] is True
        assert result['data']['updated_count'] == 2
        assert result['data']['client_name'] == "TestClient"
        
        # Verify tasks were assigned
        test_session.expire_all()  # Clear session cache
        for task_id in task_ids:
            task = repo.get_task_by_id(task_id)
            assert task is not None
            assert task.client_id == client.id

    @pytest.mark.asyncio
    async def test_bulk_delete_tasks_service(self, test_session, db_task_factory):
        """Test bulk delete at service level."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Create tasks and store IDs immediately
        task_ids = []
        for i in range(2):
            task = db_task_factory(description=f"Task {i+1}")
            task_ids.append(task.id)
        
        # Test bulk delete
        result = await service.bulk_delete_tasks(task_ids)
        
        assert result['success'] is True
        assert result['data']['deleted_count'] == 2
        
        # Verify tasks were deleted with fresh queries
        test_session.expire_all()  # Clear session cache
        for task_id in task_ids:
            # Use a fresh query to avoid detached instance issues
            task_count = test_session.query(Task).filter(Task.id == task_id).count()
            assert task_count == 0

    @pytest.mark.asyncio
    async def test_add_manual_time_entry_service(self, test_session, db_task_factory):
        """Test manual time entry at service level."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Create task
        task = db_task_factory(description="Time tracking test task")
        task_id = task.id
        
        # Test adding manual time entry
        result = await service.add_manual_time_entry(task_id, 120, "Manual entry test")
        
        assert result['success'] is True
        assert result['data']['duration_minutes'] == 120
        assert result['data']['description'] == "Manual entry test"
        
        # Verify time entry was added
        summary = repo.get_task_time_summary(task_id)
        assert summary['time_entries_count'] == 1
        assert summary['time_entries_hours'] == 2.0  # 120 minutes = 2 hours

    @pytest.mark.asyncio
    async def test_get_task_time_summary_service(self, test_session, db_task_factory):
        """Test time summary at service level."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Create task with time entry
        task = db_task_factory(description="Time tracking test task", estimated_hours=3.0)
        task_id = task.id
        
        # Add time entry
        from larrybot.utils.basic_datetime import get_utc_now
        start_time = get_utc_now() - timedelta(hours=2)
        end_time = get_utc_now() - timedelta(hours=1)
        repo.add_time_entry(task_id, start_time, end_time, "Test entry")
        
        # Test time summary
        result = await service.get_task_time_summary(task_id)
        
        assert result['success'] is True
        summary = result['data']
        assert summary['task_id'] == task_id
        assert summary['estimated_hours'] == 3.0
        assert summary['time_entries_hours'] == 1.0
        assert summary['time_entries_count'] == 1

class TestBulkOperationsCommands:
    """Test bulk operations at command level."""

    @pytest.mark.asyncio
    async def test_bulk_status_command_success(self, mock_update, mock_context, mock_task_service):
        """Test successful bulk status command."""
        # Arrange
        mock_context.args = ["1,2,3", "In Progress"]
        mock_task_service.bulk_update_status.return_value = {
            'success': True,
            'message': 'Updated status to In Progress for 3 tasks'
        }
        
        with patch('larrybot.plugins.advanced_tasks.bulk_operations.get_task_service', return_value=mock_task_service):
            # Act
            await bulk_status_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.bulk_update_status.assert_called_once_with([1, 2, 3], "In Progress")
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "✅ **Success**" in call_args[0][0]
            assert "Updated status to In Progress for 3 tasks" in call_args[0][0]
            assert call_args[1]['parse_mode'] == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_bulk_priority_command_success(self, mock_update, mock_context, mock_task_service):
        """Test successful bulk priority command."""
        # Arrange
        mock_context.args = ["1,2,3", "High"]
        mock_task_service.bulk_update_priority.return_value = {
            'success': True,
            'message': 'Updated priority to High for 3 tasks'
        }
        
        with patch('larrybot.plugins.advanced_tasks.bulk_operations.get_task_service', return_value=mock_task_service):
            # Act
            await bulk_priority_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.bulk_update_priority.assert_called_once_with([1, 2, 3], "High")
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "✅ **Success**" in call_args[0][0]
            assert "Updated priority to High for 3 tasks" in call_args[0][0]
            assert call_args[1]['parse_mode'] == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_bulk_assign_command_success(self, mock_update, mock_context, mock_task_service):
        """Test successful bulk assign command."""
        # Arrange
        mock_context.args = ["1,2,3", "TestClient"]
        mock_task_service.bulk_assign_to_client.return_value = {
            'success': True,
            'message': 'Assigned 3 tasks to client TestClient'
        }
        
        with patch('larrybot.plugins.advanced_tasks.bulk_operations.get_task_service', return_value=mock_task_service):
            # Act
            await bulk_assign_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.bulk_assign_to_client.assert_called_once_with([1, 2, 3], "TestClient")
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "✅ **Success**" in call_args[0][0]
            assert "Assigned 3 tasks to client TestClient" in call_args[0][0]
            assert call_args[1]['parse_mode'] == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_bulk_delete_command_without_confirm(self, mock_update, mock_context):
        """Test bulk delete command without confirmation."""
        # Arrange
        mock_context.args = ["1,2,3"]
        
        # Act
        await bulk_delete_handler(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "⚠️ Bulk Delete Confirmation Required" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'
        # No reply_markup expected for warning message

    @pytest.mark.asyncio
    async def test_bulk_delete_command_with_confirm(self, mock_update, mock_context, mock_task_service):
        """Test bulk delete command with confirmation."""
        # Arrange
        mock_context.args = ["1,2,3", "confirm"]
        mock_task_service.bulk_delete_tasks.return_value = {
            'success': True,
            'message': 'Deleted 3 tasks'
        }
        
        with patch('larrybot.plugins.advanced_tasks.bulk_operations.get_task_service', return_value=mock_task_service):
            # Act
            await bulk_delete_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.bulk_delete_tasks.assert_called_once_with([1, 2, 3])
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "✅ **Success**" in call_args[0][0]
            assert "Deleted 3 tasks" in call_args[0][0]
            assert call_args[1]['parse_mode'] == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_time_entry_command_success(self, mock_update, mock_context, mock_task_service):
        """Test successful time entry command."""
        # Arrange
        mock_context.args = ["1", "120", "Code review"]
        mock_task_service.add_manual_time_entry.return_value = {
            'success': True,
            'message': 'Added 120 minutes to task 1'
        }
        
        with patch('larrybot.plugins.advanced_tasks.time_tracking.get_task_service', return_value=mock_task_service):
            # Act
            await time_entry_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.add_manual_time_entry.assert_called_once_with(1, 120, "Code review")
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "✅ **Success**" in call_args[0][0]
            assert "Added 120 minutes to task 1" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_time_summary_command_success(self, mock_update, mock_context, mock_task_service):
        """Test successful time summary command."""
        # Arrange
        mock_context.args = ["1"]
        mock_task_service.get_task_time_summary.return_value = {
            'success': True,
            'data': {
                'task_description': 'Test task',
                'estimated_hours': 2.0,
                'actual_hours': 1.5,
                'time_entries_hours': 1.5,
                'time_entries_count': 2,
                'comments_count': 1,
                'efficiency': 133.3
            }
        }
        
        with patch('larrybot.plugins.advanced_tasks.time_tracking.get_task_service', return_value=mock_task_service):
            # Act
            await time_summary_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.get_task_time_summary.assert_called_once_with(1)
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "⏱️ Time Summary for Task \\#1" in call_args[0][0]
            assert "✅ **Success**" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_command_error_handling(self, mock_update, mock_context, mock_task_service):
        """Test error handling in commands."""
        # Arrange
        mock_context.args = ["invalid", "High"]
        mock_task_service.bulk_update_priority.return_value = {
            'success': False,
            'message': 'Invalid task ID format'
        }
        
        with patch('larrybot.plugins.advanced_tasks.bulk_operations.get_task_service', return_value=mock_task_service):
            # Act
            await bulk_priority_handler(mock_update, mock_context)
            
            # Assert
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "❌ **Error**" in call_args[0][0]
            # The actual error message will be different, but should contain error info
            assert call_args[1]['parse_mode'] == 'MarkdownV2' 