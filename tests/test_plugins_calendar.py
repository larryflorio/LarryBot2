import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open, call
from datetime import datetime, timezone
from larrybot.plugins.calendar import (
    register,
    agenda_handler,
    connect_google_handler,
    disconnect_handler,
    run_in_thread
)
from larrybot.storage.calendar_token_repository import CalendarTokenRepository


def test_register_commands(command_registry, event_bus):
    """Test that calendar plugin registers all commands correctly."""
    register(event_bus, command_registry)
    
    registered_commands = list(command_registry._commands.keys())
    assert "/agenda" in registered_commands
    assert "/connect_google" in registered_commands
    assert "/disconnect" in registered_commands


@pytest.mark.asyncio
async def test_agenda_handler_no_token(test_session, mock_update, mock_context):
    """Test agenda handler when no Google token is stored."""
    mock_update.message.reply_text = AsyncMock()
    
    with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
        await agenda_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Google Calendar is not connected" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_agenda_handler_with_token_api_error(test_session, mock_update, mock_context):
    """Test agenda handler when Google API call fails."""
    mock_update.message.reply_text = AsyncMock()
    
    # Create a token in the database with future expiry to avoid refresh
    repo = CalendarTokenRepository(test_session)
    token = repo.add_token(
        provider="google",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expiry=datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 1)  # Future expiry
    )
    
    with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
        with patch("builtins.open", mock_open(read_data='{"installed": {"client_id": "test_client_id", "client_secret": "test_client_secret"}}')):
            with patch("json.load", return_value={"installed": {"client_id": "test_client_id", "client_secret": "test_client_secret"}}):
                with patch("larrybot.plugins.calendar.build") as mock_build:
                    mock_build.side_effect = Exception("API Error")
                    
                    with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                        mock_run_in_thread.side_effect = Exception("API Error")
                        
                        await agenda_handler(mock_update, mock_context)
                        
                        call_args = mock_update.message.reply_text.call_args
                        response_text = call_args[0][0]
                        parse_mode = call_args[1].get('parse_mode')
                        
                        assert "Failed to fetch events" in response_text
                        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_connect_google_handler_no_client_secret_file(test_session, mock_update, mock_context):
    """Test connect_google handler when client_secret.json is missing."""
    mock_update.message.reply_text = AsyncMock()
    
    with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
        with patch("os.path.exists", return_value=False):
            await connect_google_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "❌ **Error**" in response_text
            assert "Configuration Missing" in response_text
            assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_connect_google_handler_already_connected(test_session, mock_update, mock_context):
    """Test connect_google handler when already connected."""
    mock_update.message.reply_text = AsyncMock()
    
    # Create a token in the database
    repo = CalendarTokenRepository(test_session)
    token = repo.add_token(
        provider="google",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expiry=datetime.now(timezone.utc)
    )
    
    with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
        with patch("os.path.exists", return_value=True):
            await connect_google_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Google Calendar is already connected" in response_text
            assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_disconnect_handler_no_token(test_session, mock_update, mock_context):
    """Test disconnect handler when no token exists."""
    mock_update.message.reply_text = AsyncMock()
    
    with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
        await disconnect_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "No Google Calendar connection found" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_disconnect_handler_success(test_session, mock_update, mock_context):
    """Test disconnect handler when token exists."""
    mock_update.message.reply_text = AsyncMock()
    
    # Create a token in the database
    repo = CalendarTokenRepository(test_session)
    token = repo.add_token(
        provider="google",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expiry=datetime.now(timezone.utc)
    )
    
    with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
        await disconnect_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Google Calendar Disconnected" in response_text
        assert parse_mode == 'MarkdownV2'
        
        # Verify token was removed using the correct repository method
        assert repo.get_token_by_provider("google") is None


@pytest.mark.asyncio
async def test_run_in_thread_helper():
    """Test the run_in_thread helper function."""
    def test_function():
        return "test_result"
    
    result = await run_in_thread(test_function)
    assert result == "test_result"


@pytest.mark.asyncio
async def test_run_in_thread_with_args():
    """Test run_in_thread with arguments."""
    def test_function(arg1, arg2, kwarg=None):
        return f"{arg1}_{arg2}_{kwarg}"
    
    result = await run_in_thread(test_function, "test", "1", kwarg="2")
    assert result == "test_1_2" 