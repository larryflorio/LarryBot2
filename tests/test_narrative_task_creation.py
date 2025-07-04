import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes
from larrybot.plugins.tasks import (
    narrative_add_task_handler, handle_narrative_task_creation,
    _handle_description_step, _handle_due_date_step, _handle_priority_step,
    _handle_category_step, _handle_client_step, _show_confirmation,
    _create_final_task, _cancel_task_creation, _clear_task_creation_state
)
from larrybot.nlp.enhanced_narrative_processor import TaskCreationState
from larrybot.models.task import Task
from larrybot.models.client import Client

class TestNarrativeTaskCreation:
    """Test the narrative task creation flow."""
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock Update object."""
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.text = "Test task description"
        update.message.reply_text = AsyncMock()
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 12345
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Context object."""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        context.args = []
        return context
    
    @pytest.fixture
    def mock_query(self):
        """Create a mock CallbackQuery object."""
        query = Mock()
        query.data = "addtask_step:priority:High"
        query.edit_message_text = AsyncMock()
        query.answer = AsyncMock()
        return query
    
    @pytest.mark.asyncio
    async def test_narrative_add_task_handler_initializes_state(self, mock_update, mock_context):
        """Test that the narrative add task handler initializes the state correctly."""
        await narrative_add_task_handler(mock_update, mock_context)
        
        assert 'task_creation_state' in mock_context.user_data
        assert mock_context.user_data['task_creation_state'] == TaskCreationState.AWAITING_DESCRIPTION.value
        assert 'partial_task' in mock_context.user_data
        assert 'step_history' in mock_context.user_data
        assert 'started_at' in mock_context.user_data
        
        # Check partial task structure
        partial_task = mock_context.user_data['partial_task']
        assert partial_task['description'] is None
        assert partial_task['due_date'] is None
        assert partial_task['priority'] == 'Medium'
        assert partial_task['category'] is None
        assert partial_task['client_id'] is None
        assert partial_task['estimated_hours'] is None
        
        # Verify initial message was sent
        mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_description_step(self, mock_update, mock_context):
        """Test handling description step."""
        # Setup initial state
        mock_context.user_data['task_creation_state'] = TaskCreationState.AWAITING_DESCRIPTION.value
        mock_context.user_data['partial_task'] = {
            'description': None,
            'due_date': None,
            'priority': 'Medium',
            'category': None,
            'client_id': None,
            'estimated_hours': None
        }
        mock_context.user_data['step_history'] = []
        
        await _handle_description_step(mock_update, mock_context, "Fix the critical bug")
        
        # Check state was updated
        assert mock_context.user_data['task_creation_state'] == TaskCreationState.AWAITING_DUE_DATE.value
        assert mock_context.user_data['partial_task']['description'] == "Fix the critical bug"
        assert len(mock_context.user_data['step_history']) == 1
        assert mock_context.user_data['step_history'][0]['step'] == 'description'
        
        # Verify message was sent with buttons
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_handle_description_step_empty_description(self, mock_update, mock_context):
        """Test handling empty description."""
        mock_context.user_data['task_creation_state'] = TaskCreationState.AWAITING_DESCRIPTION.value
        mock_context.user_data['partial_task'] = {
            'description': None,
            'due_date': None,
            'priority': 'Medium',
            'category': None,
            'client_id': None,
            'estimated_hours': None
        }
        
        await _handle_description_step(mock_update, mock_context, "")
        
        # Check state was not updated
        assert mock_context.user_data['task_creation_state'] == TaskCreationState.AWAITING_DESCRIPTION.value
        assert mock_context.user_data['partial_task']['description'] is None
        
        # Verify error message was sent
        mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_due_date_step_with_callback(self, mock_query, mock_context):
        """Test handling due date step with callback query."""
        mock_context.user_data['task_creation_state'] = TaskCreationState.AWAITING_DUE_DATE.value
        mock_context.user_data['partial_task'] = {
            'description': 'Test task',
            'due_date': None,
            'priority': 'Medium',
            'category': None,
            'client_id': None,
            'estimated_hours': None
        }
        mock_context.user_data['step_history'] = []
        
        await _handle_due_date_step(mock_query, mock_context, "tomorrow")
        
        # Check state was updated
        assert mock_context.user_data['task_creation_state'] == TaskCreationState.AWAITING_PRIORITY.value
        assert mock_context.user_data['partial_task']['due_date'] is not None
        assert len(mock_context.user_data['step_history']) == 1
        
        # Verify message was edited with buttons
        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args
        assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_handle_priority_step(self, mock_query, mock_context):
        """Test handling priority step."""
        mock_context.user_data['task_creation_state'] = TaskCreationState.AWAITING_PRIORITY.value
        mock_context.user_data['partial_task'] = {
            'description': 'Test task',
            'due_date': None,
            'priority': 'Medium',
            'category': None,
            'client_id': None,
            'estimated_hours': None
        }
        mock_context.user_data['step_history'] = []
        
        with patch('larrybot.plugins.tasks.get_session') as mock_session:
            mock_session_instance = Mock()
            mock_session_instance.__enter__ = Mock(return_value=mock_session_instance)
            mock_session_instance.__exit__ = Mock(return_value=None)
            mock_session.return_value.__next__.return_value = mock_session_instance
            
            with patch('larrybot.plugins.tasks.TaskRepository') as mock_repo:
                mock_repo.return_value.get_all_categories.return_value = ["Work", "Personal"]
                
                await _handle_priority_step(mock_query, mock_context, "High")
        
        # Check state was updated
        assert mock_context.user_data['task_creation_state'] == TaskCreationState.AWAITING_CATEGORY.value
        assert mock_context.user_data['partial_task']['priority'] == "High"
        assert len(mock_context.user_data['step_history']) == 1
        
        # Verify message was edited with category buttons
        mock_query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_category_step_work_category(self, mock_query, mock_context):
        """Test handling category step with Work category."""
        mock_context.user_data['task_creation_state'] = TaskCreationState.AWAITING_CATEGORY.value
        mock_context.user_data['partial_task'] = {
            'description': 'Test task',
            'due_date': None,
            'priority': 'High',
            'category': None,
            'client_id': None,
            'estimated_hours': None
        }
        mock_context.user_data['step_history'] = []
        
        with patch('larrybot.plugins.tasks.get_session') as mock_session:
            mock_session_instance = Mock()
            mock_session_instance.__enter__ = Mock(return_value=mock_session_instance)
            mock_session_instance.__exit__ = Mock(return_value=None)
            mock_session.return_value.__next__.return_value = mock_session_instance
            
            with patch('larrybot.plugins.tasks.ClientRepository') as mock_repo:
                mock_client = Mock(spec=Client)
                mock_client.id = 1
                mock_client.name = "Test Client"
                mock_client.tasks = []
                mock_repo.return_value.list_clients.return_value = [mock_client]
                
                await _handle_category_step(mock_query, mock_context, "Work")
        
        # Check state was updated to client selection
        assert mock_context.user_data['task_creation_state'] == TaskCreationState.AWAITING_CLIENT.value
        assert mock_context.user_data['partial_task']['category'] == "Work"
        
        # Verify message was edited with client buttons
        mock_query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_category_step_personal_category(self, mock_query, mock_context):
        """Test handling category step with Personal category."""
        mock_context.user_data['task_creation_state'] = TaskCreationState.AWAITING_CATEGORY.value
        mock_context.user_data['partial_task'] = {
            'description': 'Test task',
            'due_date': None,
            'priority': 'High',
            'category': None,
            'client_id': None,
            'estimated_hours': None
        }
        mock_context.user_data['step_history'] = []
        
        await _handle_category_step(mock_query, mock_context, "Personal")
        
        # Check state was updated to confirmation
        assert mock_context.user_data['task_creation_state'] == TaskCreationState.CONFIRMATION.value
        assert mock_context.user_data['partial_task']['category'] == "Personal"
        
        # Verify confirmation was shown
        mock_query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_show_confirmation(self, mock_query, mock_context):
        """Test showing task confirmation."""
        mock_context.user_data['partial_task'] = {
            'description': 'Test task',
            'due_date': '2025-01-15',
            'priority': 'High',
            'category': 'Work',
            'client_id': 1,
            'estimated_hours': None
        }
        
        with patch('larrybot.plugins.tasks.get_session') as mock_session:
            mock_session_instance = Mock()
            mock_session_instance.__enter__ = Mock(return_value=mock_session_instance)
            mock_session_instance.__exit__ = Mock(return_value=None)
            mock_session.return_value.__next__.return_value = mock_session_instance
            
            with patch('larrybot.plugins.tasks.ClientRepository') as mock_repo:
                mock_client = Mock(spec=Client)
                mock_client.name = "Test Client"
                mock_repo.return_value.get_client_by_id.return_value = mock_client
                
                await _show_confirmation(mock_query, mock_context)
        
        # Verify confirmation message was shown
        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args
        assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_create_final_task_success(self, mock_query, mock_context):
        """Test successful final task creation."""
        mock_context.user_data['partial_task'] = {
            'description': 'Test task',
            'due_date': '2025-01-15',
            'priority': 'High',
            'category': 'Work',
            'client_id': 1,
            'estimated_hours': None
        }
        
        with patch('larrybot.plugins.tasks._get_task_service') as mock_service:
            mock_service_instance = Mock()
            mock_service_instance.create_task_with_metadata = AsyncMock(return_value={
                'success': True,
                'data': {
                    'id': 123,
                    'description': 'Test task',
                    'priority': 'High',
                    'due_date': '2025-01-15',
                    'category': 'Work'
                }
            })
            mock_service.return_value = mock_service_instance
            
            await _create_final_task(mock_query, mock_context)
        
        # Verify success message was shown
        mock_query.edit_message_text.assert_called_once()
        
        # Verify state was cleared
        assert 'task_creation_state' not in mock_context.user_data
        assert 'partial_task' not in mock_context.user_data
    
    @pytest.mark.asyncio
    async def test_create_final_task_failure(self, mock_query, mock_context):
        """Test failed final task creation."""
        mock_context.user_data['task_creation_state'] = TaskCreationState.CONFIRMATION.value
        mock_context.user_data['partial_task'] = {
            'description': 'Test task',
            'due_date': '2025-01-15',
            'priority': 'High',
            'category': 'Work',
            'client_id': 1,
            'estimated_hours': None
        }
        
        with patch('larrybot.plugins.tasks._get_task_service') as mock_service:
            mock_service_instance = Mock()
            mock_service_instance.create_task_with_metadata = AsyncMock(return_value={
                'success': False,
                'message': 'Database error'
            })
            mock_service.return_value = mock_service_instance
            
            await _create_final_task(mock_query, mock_context)
        
        # Verify error message was shown
        mock_query.edit_message_text.assert_called_once()
        
        # Verify state was not cleared (user can retry)
        assert 'task_creation_state' in mock_context.user_data
    
    @pytest.mark.asyncio
    async def test_cancel_task_creation(self, mock_query, mock_context):
        """Test canceling task creation."""
        mock_context.user_data['task_creation_state'] = TaskCreationState.AWAITING_DESCRIPTION.value
        mock_context.user_data['partial_task'] = {'description': 'Test'}
        mock_context.user_data['step_history'] = []
        mock_context.user_data['started_at'] = '2025-01-15T10:00:00'
        
        await _cancel_task_creation(mock_query, mock_context)
        
        # Verify cancel message was shown
        mock_query.edit_message_text.assert_called_once()
        
        # Verify state was cleared
        assert 'task_creation_state' not in mock_context.user_data
        assert 'partial_task' not in mock_context.user_data
        assert 'step_history' not in mock_context.user_data
        assert 'started_at' not in mock_context.user_data
    
    def test_clear_task_creation_state(self, mock_context):
        """Test clearing task creation state."""
        mock_context.user_data.update({
            'task_creation_state': 'test',
            'partial_task': {'test': 'data'},
            'step_history': [],
            'started_at': '2025-01-15T10:00:00',
            'awaiting_custom_category': True,
            'awaiting_new_client': True,
            'other_data': 'should_remain'
        })
        
        _clear_task_creation_state(mock_context)
        
        # Verify task creation keys were removed
        assert 'task_creation_state' not in mock_context.user_data
        assert 'partial_task' not in mock_context.user_data
        assert 'step_history' not in mock_context.user_data
        assert 'started_at' not in mock_context.user_data
        assert 'awaiting_custom_category' not in mock_context.user_data
        assert 'awaiting_new_client' not in mock_context.user_data
        
        # Verify other data remains
        assert 'other_data' in mock_context.user_data 