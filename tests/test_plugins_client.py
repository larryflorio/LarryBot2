import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from larrybot.plugins import client as client_plugin
from larrybot.storage.client_repository import ClientRepository
from larrybot.storage.task_repository import TaskRepository


def test_register_commands(command_registry, event_bus):
    """Test that client plugin registers all commands correctly."""
    client_plugin.register(event_bus, command_registry)
    
    registered_commands = list(command_registry._commands.keys())
    assert "/addclient" in registered_commands
    assert "/removeclient" in registered_commands
    assert "/allclients" in registered_commands
    assert "/assign" in registered_commands
    assert "/unassign" in registered_commands
    assert "/client" in registered_commands
    assert "/clientanalytics" in registered_commands


@pytest.mark.asyncio
async def test_addclient_handler_no_args(test_session, mock_update, mock_context):
    """Test addclient handler when no arguments are provided."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = []
    
    with patch("larrybot.plugins.client.get_session", return_value=iter([test_session])):
        await client_plugin.addclient_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Missing client name" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_addclient_handler_success(test_session, mock_update, mock_context):
    """Test addclient handler with valid arguments."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["AcmeCorp"]
    
    with patch("larrybot.plugins.client.get_session", return_value=iter([test_session])):
        await client_plugin.addclient_handler(mock_update, mock_context)
        
        # Check that the client was created
        repo = ClientRepository(test_session)
        client = repo.get_client_by_name("AcmeCorp")
        assert client is not None
        assert client.name == "AcmeCorp"
        
        # Check the response message
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Client 'AcmeCorp' added successfully" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_addclient_handler_duplicate(test_session, mock_update, mock_context, db_client_factory):
    """Test addclient handler when client already exists."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["AcmeCorp"]
    
    db_client_factory(name="AcmeCorp")
    
    with patch("larrybot.plugins.client.get_session", return_value=iter([test_session])):
        await client_plugin.addclient_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Client 'AcmeCorp' already exists" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_removeclient_handler_not_found(test_session, mock_update, mock_context):
    """Test removeclient handler when client doesn't exist."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["NoSuchClient"]
    
    with patch("larrybot.plugins.client.get_session", return_value=iter([test_session])):
        await client_plugin.removeclient_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Client 'NoSuchClient' not found" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_removeclient_handler_confirm(test_session, mock_update, mock_context, db_client_factory):
    """Test removeclient handler with confirmation."""
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["AcmeCorp", "confirm"]
    
    db_client_factory(name="AcmeCorp")
    
    with patch("larrybot.plugins.client.get_session", return_value=iter([test_session])):
        await client_plugin.removeclient_handler(mock_update, mock_context)
        
        # Check that the client was removed
        repo = ClientRepository(test_session)
        client = repo.get_client_by_name("AcmeCorp")
        assert client is None
        
        # Check the response message
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Client 'AcmeCorp' removed successfully" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_allclients_handler_no_clients(test_session, mock_update, mock_context):
    """Test allclients handler when no clients exist."""
    mock_update.message.reply_text = AsyncMock()
    
    with patch("larrybot.plugins.client.get_session", return_value=iter([test_session])):
        await client_plugin.allclients_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "No clients found" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_allclients_handler_with_clients(test_session, mock_update, mock_context, db_client_factory):
    """Test allclients handler when clients exist."""
    mock_update.message.reply_text = AsyncMock()
    
    db_client_factory(name="AcmeCorp")
    db_client_factory(name="BetaLLC")
    
    with patch("larrybot.plugins.client.get_session", return_value=iter([test_session])):
        await client_plugin.allclients_handler(mock_update, mock_context)
        
        # Check that the message contains both clients
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "All Clients" in response_text
        assert "AcmeCorp" in response_text
        assert "BetaLLC" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_assign_handler_success(test_session, mock_update, mock_context, db_client_factory, db_task_factory):
    """Test assign handler with valid arguments."""
    mock_update.message.reply_text = AsyncMock()
    client = db_client_factory(name="AcmeCorp")
    task = db_task_factory(description="Test Task")
    task_id = task.id  # Store before session closes
    mock_context.args = [str(task_id), "AcmeCorp"]
    
    with patch("larrybot.plugins.client.get_session", return_value=iter([test_session])):
        await client_plugin.assign_handler(mock_update, mock_context)
        
        # Check the response message
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task assigned successfully" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_unassign_handler_success(test_session, mock_update, mock_context, db_client_factory, db_task_factory):
    """Test unassign handler with valid arguments."""
    mock_update.message.reply_text = AsyncMock()
    client = db_client_factory(name="AcmeCorp")
    task = db_task_factory(description="Test Task")
    task_repo = TaskRepository(test_session)
    task_repo.assign_task_to_client(task.id, "AcmeCorp")
    mock_context.args = [str(task.id)]
    
    with patch("larrybot.plugins.client.get_session", return_value=iter([test_session])):
        await client_plugin.unassign_handler(mock_update, mock_context)
        
        # Check the response message
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task unassigned" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_client_handler_success(test_session, mock_update, mock_context, db_client_factory, db_task_factory):
    """Test client handler with valid arguments."""
    mock_update.message.reply_text = AsyncMock()
    client = db_client_factory(name="AcmeCorp")
    task = db_task_factory(description="Test Task")
    task_id = task.id  # Store before session closes
    task_repo = TaskRepository(test_session)
    task_repo.assign_task_to_client(task_id, "AcmeCorp")
    mock_context.args = ["AcmeCorp"]
    
    with patch("larrybot.plugins.client.get_session", return_value=iter([test_session])):
        await client_plugin.client_handler(mock_update, mock_context)
        
        # Check that the message contains the task
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Client Details" in response_text
        assert "AcmeCorp" in response_text
        assert "Test Task" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_clientanalytics_handler(test_session, mock_update, mock_context, db_client_factory, db_task_factory):
    """Test clientanalytics handler."""
    mock_update.message.reply_text = AsyncMock()
    
    client = db_client_factory(name="AcmeCorp")
    task = db_task_factory(description="Test Task")
    task_repo = TaskRepository(test_session)
    task_repo.assign_task_to_client(task.id, "AcmeCorp")
    
    with patch("larrybot.plugins.client.get_session", return_value=iter([test_session])):
        await client_plugin.clientanalytics_handler(mock_update, mock_context)
        
        # Check that the message contains analytics
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Client Analytics Report" in response_text
        assert "AcmeCorp" in response_text
        assert parse_mode == 'MarkdownV2' 