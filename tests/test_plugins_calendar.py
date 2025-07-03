import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open, call
from datetime import datetime, timezone
from larrybot.plugins.calendar import (
    register,
    agenda_handler,
    connect_google_handler,
    disconnect_handler,
    run_in_thread,
    extract_video_call_link
)
from larrybot.storage.calendar_token_repository import CalendarTokenRepository


def test_register_commands(command_registry, event_bus):
    """Test that calendar plugin registers all commands correctly."""
    register(event_bus, command_registry)
    
    registered_commands = list(command_registry._commands.keys())
    assert "/agenda" in registered_commands
    assert "/connect_google" in registered_commands
    assert "/disconnect" in registered_commands
    assert "/accounts" in registered_commands
    assert "/account_primary" in registered_commands
    assert "/account_rename" in registered_commands
    assert "/account_deactivate" in registered_commands
    assert "/account_reactivate" in registered_commands
    assert "/account_delete" in registered_commands
    assert "/calendar_all" in registered_commands


@pytest.mark.asyncio
async def test_agenda_handler_no_token(test_session, mock_update, mock_context):
    """Test agenda handler when no Google token is stored."""
    mock_update.message.reply_text = AsyncMock()
    
    with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
        await agenda_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "No Google Calendar accounts connected" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_agenda_handler_with_token_api_error(test_session, mock_update, mock_context):
    """Test agenda handler when Google API call fails."""
    mock_update.message.reply_text = AsyncMock()
    
    # Create a token in the database with future expiry to avoid refresh
    repo = CalendarTokenRepository(test_session)
    token = repo.add_token(
        provider="google",
        account_id="test_account",
        account_name="Test Account",
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
                        
                        assert "Unexpected error" in response_text
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
        account_id="test_account",
        account_name="Test Account",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expiry=datetime.now(timezone.utc)
    )
    
    with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session, test_session])):
        with patch("os.path.exists", return_value=True):
            # Patch OAuth flow to simulate successful connection
            with patch("larrybot.plugins.calendar.InstalledAppFlow") as mock_flow_class:
                mock_flow = MagicMock()
                mock_creds = MagicMock()
                mock_creds.token = "new_access_token"
                mock_creds.refresh_token = "new_refresh_token"
                # Use a real datetime for expiry
                import datetime as dt
                mock_creds.expiry = dt.datetime.now(dt.timezone.utc)
                mock_flow.run_local_server.return_value = mock_creds
                mock_flow_class.from_client_secrets_file.return_value = mock_flow
                with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                    # Simulate userinfo API
                    def run_in_thread_side_effect(func, *args, **kwargs):
                        if hasattr(func, '__name__') and func.__name__ == 'build':
                            mock_service = MagicMock()
                            mock_userinfo = MagicMock()
                            # Ensure .get().execute() returns a real dict with a string email
                            mock_userinfo.get.return_value.execute.return_value = {"email": "test2@example.com"}
                            mock_service.userinfo.return_value = mock_userinfo
                            return mock_service
                        return mock_creds
                    mock_run_in_thread.side_effect = run_in_thread_side_effect
                    
                    await connect_google_handler(mock_update, mock_context)
                    
                    # Should allow connecting another account (no limit)
                    assert mock_update.message.reply_text.call_count == 2
                    first_call = mock_update.message.reply_text.call_args_list[0]
                    assert "Connecting Google Calendar" in first_call[0][0]
                    second_call = mock_update.message.reply_text.call_args_list[1]
                    assert "Google Calendar Connected" in second_call[0][0]


@pytest.mark.asyncio
async def test_disconnect_handler_no_token(test_session, mock_update, mock_context):
    """Test disconnect handler when no token exists."""
    mock_update.message.reply_text = AsyncMock()
    
    with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
        await disconnect_handler(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "No Connection Found" in response_text
        assert parse_mode == 'MarkdownV2'


@pytest.mark.asyncio
async def test_disconnect_handler_success(test_session, mock_update, mock_context):
    """Test disconnect handler when token exists."""
    mock_update.message.reply_text = AsyncMock()
    
    # Create a token in the database
    repo = CalendarTokenRepository(test_session)
    token = repo.add_token(
        provider="google",
        account_id="test_account",
        account_name="Test Account",
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
    def test_func(x, y):
        return x + y
    
    result = await run_in_thread(test_func, 2, 3)
    assert result == 5


@pytest.mark.asyncio
async def test_run_in_thread_with_args():
    """Test the run_in_thread helper function with keyword arguments."""
    def test_func(x, y, z=0):
        return x + y + z
    
    result = await run_in_thread(test_func, 2, 3, z=5)
    assert result == 10


def test_extract_video_call_link():
    """Test video call link extraction from calendar events."""
    # Test Google Meet conference data
    google_meet_event = {
        'conferenceData': {
            'entryPoints': [
                {
                    'entryPointType': 'video',
                    'uri': 'https://meet.google.com/abc-defg-hij',
                    'label': 'meet.google.com/abc-defg-hij'
                }
            ]
        }
    }
    
    result = extract_video_call_link(google_meet_event)
    assert result is not None
    assert result['platform'] == 'Google Meet'
    assert result['url'] == 'https://meet.google.com/abc-defg-hij'
    
    # Test Zoom link in description
    zoom_event = {
        'description': 'Join our meeting: https://zoom.us/j/123456789?pwd=abc123'
    }
    
    result = extract_video_call_link(zoom_event)
    assert result is not None
    assert result['platform'] == 'Zoom'
    assert 'zoom.us' in result['url']
    
    # Test Teams link in description
    teams_event = {
        'description': 'Meeting link: https://teams.microsoft.com/l/meetup-join/19:meeting_abc123'
    }
    
    result = extract_video_call_link(teams_event)
    assert result is not None
    assert result['platform'] == 'Microsoft Teams'
    assert 'teams.microsoft.com' in result['url']
    
    # Test event with no video link
    regular_event = {
        'description': 'This is a regular meeting with no video call.'
    }
    
    result = extract_video_call_link(regular_event)
    assert result is None
    
    # Test event with no description
    empty_event = {}
    
    result = extract_video_call_link(empty_event)
    assert result is None


def test_url_obfuscation():
    """Test URL obfuscation to prevent Telegram link embedding."""
    from larrybot.utils.ux_helpers import MessageFormatter
    
    # Test basic URL obfuscation
    test_url = "https://meet.google.com/abc-defg-hij"
    obfuscated = MessageFormatter.obfuscate_url(test_url)
    
    # Should contain zero-width characters
    assert '\u200b' in obfuscated
    
    # Should be visually identical when displayed
    # (zero-width characters are invisible)
    assert len(obfuscated) > len(test_url)
    
    # Should still contain the original URL characters
    for char in test_url:
        assert char in obfuscated
    
    # Test empty URL
    assert MessageFormatter.obfuscate_url("") == ""
    assert MessageFormatter.obfuscate_url(None) == None
    
    # Test various URL formats
    urls_to_test = [
        "https://zoom.us/j/123456789",
        "https://teams.microsoft.com/l/meetup-join/19:meeting_abc123",
        "https://webex.com/meeting/123456",
        "https://discord.gg/abc123"
    ]
    
    for url in urls_to_test:
        obfuscated = MessageFormatter.obfuscate_url(url)
        assert '\u200b' in obfuscated
        assert len(obfuscated) > len(url)
        # All original characters should be present
        for char in url:
            assert char in obfuscated 