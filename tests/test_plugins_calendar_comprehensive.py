import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open, call
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import json
import os

from larrybot.plugins.calendar import (
    register,
    agenda_handler,
    connect_google_handler,
    disconnect_handler,
    run_in_thread,
    SCOPES,
    CLIENT_SECRET_FILE,
    calendar_handler,
    calendar_sync_handler,
    calendar_events_handler
)
from larrybot.storage.calendar_token_repository import CalendarTokenRepository


class TestCalendarPluginComprehensive:
    """Comprehensive tests for Calendar Plugin with best practice patterns."""

    @pytest.mark.asyncio
    async def test_agenda_handler_successful_event_fetch(self, test_session, mock_update, mock_context):
        """Test agenda handler with successful event fetch."""
        mock_update.message.reply_text = AsyncMock()
        
        repo = CalendarTokenRepository(test_session)
        token = repo.add_token(
            provider="google",
            account_id="test_account",
            account_name="Test Account",
            access_token="valid_token",
            refresh_token="valid_refresh",
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Mock events with different formats
        mock_events = {
            "items": [
                {
                    "summary": "Team Meeting",
                    "start": {"dateTime": "2025-06-28T10:00:00Z"}
                },
                {
                    "summary": "Lunch",
                    "start": {"date": "2025-06-28"}  # All-day event
                },
                {
                    # Event without summary
                    "start": {"dateTime": "2025-06-28T15:00:00Z"}
                }
            ]
        }
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            with patch("builtins.open", mock_open(read_data='{"installed": {"client_id": "test", "client_secret": "test"}}')):
                with patch("json.load", return_value={"installed": {"client_id": "test", "client_secret": "test"}}):
                    with patch("larrybot.plugins.calendar.build") as mock_build:
                        mock_service = MagicMock()
                        mock_events_list = MagicMock()
                        mock_events_list.execute.return_value = mock_events
                        mock_service.events.return_value.list.return_value = mock_events_list
                        mock_build.return_value = mock_service
                        
                        with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                            mock_run_in_thread.side_effect = [mock_service, mock_events_list, mock_events]
                            
                            await agenda_handler(mock_update, mock_context)
                            
                            # Check response with new UX format
                            mock_update.message.reply_text.assert_called_once()
                            call_args = mock_update.message.reply_text.call_args
                            response_text = call_args[0][0]
                            reply_markup = call_args[1].get('reply_markup')
                            parse_mode = call_args[1].get('parse_mode')
                            
                            assert "📅 **Today's Agenda**" in response_text
                            assert "3 Events Scheduled" in response_text
                            assert "Team Meeting" in response_text
                            assert "Lunch" in response_text
                            assert "\\(No title\\)" in response_text  # MarkdownV2 escaped
                            assert reply_markup is not None
                            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_agenda_handler_empty_events(self, test_session, mock_update, mock_context):
        """Test agenda handler with empty events list."""
        mock_update.message.reply_text = AsyncMock()
        
        repo = CalendarTokenRepository(test_session)
        token = repo.add_token(
            provider="google",
            account_id="test_account",
            account_name="Test Account",
            access_token="valid_token",
            refresh_token="valid_refresh",
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Mock empty events
        mock_events = {"items": []}
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            with patch("builtins.open", mock_open(read_data='{"installed": {"client_id": "test", "client_secret": "test"}}')):
                with patch("json.load", return_value={"installed": {"client_id": "test", "client_secret": "test"}}):
                    with patch("larrybot.plugins.calendar.build") as mock_build:
                        mock_service = MagicMock()
                        mock_events_list = MagicMock()
                        mock_events_list.execute.return_value = mock_events
                        mock_service.events.return_value.list.return_value = mock_events_list
                        mock_build.return_value = mock_service
                        
                        with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                            mock_run_in_thread.side_effect = [mock_service, mock_events_list, mock_events]
                            
                            await agenda_handler(mock_update, mock_context)
                            
                            # Check response with new UX format
                            mock_update.message.reply_text.assert_called_once()
                            call_args = mock_update.message.reply_text.call_args
                            response_text = call_args[0][0]
                            parse_mode = call_args[1].get('parse_mode')
                            
                            assert "No events scheduled for today" in response_text
                            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_agenda_handler_token_refresh(self, test_session, mock_update, mock_context):
        """Test agenda handler with token refresh."""
        mock_update.message.reply_text = AsyncMock()
        
        repo = CalendarTokenRepository(test_session)
        token = repo.add_token(
            provider="google",
            account_id="test_account",
            account_name="Test Account",
            access_token="expired_token",
            refresh_token="valid_refresh",
            expiry=datetime.now(timezone.utc) - timedelta(hours=1)  # Expired token
        )
        
        # Mock events
        mock_events = {
            "items": [
                {
                    "summary": "Test Event",
                    "start": {"dateTime": "2025-06-28T10:00:00Z"}
                }
            ]
        }
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            with patch("builtins.open", mock_open(read_data='{"installed": {"client_id": "test", "client_secret": "test"}}')):
                with patch("json.load", return_value={"installed": {"client_id": "test", "client_secret": "test"}}):
                    with patch("larrybot.plugins.calendar.build") as mock_build:
                        mock_service = MagicMock()
                        mock_events_list = MagicMock()
                        mock_events_list.execute.return_value = mock_events
                        mock_service.events.return_value.list.return_value = mock_events_list
                        mock_build.return_value = mock_service
                        
                        with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                            # Simplify the mocking - just return the expected values in sequence
                            mock_run_in_thread.side_effect = [
                                None,  # creds.refresh() call
                                mock_service,  # build() call
                                mock_events_list,  # events().list() call
                                mock_events  # execute() call
                            ]
                            
                            await agenda_handler(mock_update, mock_context)
                            
                            # Check response with new UX format
                            mock_update.message.reply_text.assert_called_once()
                            call_args = mock_update.message.reply_text.call_args
                            response_text = call_args[0][0]
                            reply_markup = call_args[1].get('reply_markup')
                            parse_mode = call_args[1].get('parse_mode')
                            
                            assert "📅 **Today's Agenda**" in response_text
                            assert "Test Event" in response_text
                            assert reply_markup is not None
                            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_agenda_handler_token_refresh_failure(self, test_session, mock_update, mock_context):
        """Test agenda handler when token refresh fails."""
        mock_update.message.reply_text = AsyncMock()
        
        repo = CalendarTokenRepository(test_session)
        token = repo.add_token(
            provider="google",
            account_id="test_account",
            account_name="Test Account",
            access_token="expired_token",
            refresh_token="invalid_refresh",
            expiry=datetime.now(timezone.utc) - timedelta(hours=1)  # Expired token
        )
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            with patch("builtins.open", mock_open(read_data='{"installed": {"client_id": "test", "client_secret": "test"}}')):
                with patch("json.load", return_value={"installed": {"client_id": "test", "client_secret": "test"}}):
                    with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                        mock_run_in_thread.side_effect = Exception("Refresh failed")
                        
                        await agenda_handler(mock_update, mock_context)
                        
                        # Check error response with new UX format
                        mock_update.message.reply_text.assert_called_once()
                        call_args = mock_update.message.reply_text.call_args
                        response_text = call_args[0][0]
                        parse_mode = call_args[1].get('parse_mode')
                        
                        assert "Unexpected error" in response_text
                        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_agenda_handler_malformed_client_secret(self, test_session, mock_update, mock_context):
        """Test agenda handler with malformed client_secret.json."""
        mock_update.message.reply_text = AsyncMock()
        
        repo = CalendarTokenRepository(test_session)
        token = repo.add_token(
            provider="google",
            account_id="test_account",
            account_name="Test Account",
            access_token="valid_token",
            refresh_token="valid_refresh",
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            with patch("builtins.open", mock_open(read_data='invalid json')):
                with patch("json.load", side_effect=json.JSONDecodeError("Invalid JSON", "", 0)):
                    await agenda_handler(mock_update, mock_context)
                    
                    mock_update.message.reply_text.assert_called_once()
                    assert "Failed to load client configuration" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_agenda_handler_api_timeout(self, test_session, mock_update, mock_context):
        """Test agenda handler when API calls timeout."""
        mock_update.message.reply_text = AsyncMock()
        
        repo = CalendarTokenRepository(test_session)
        token = repo.add_token(
            provider="google",
            account_id="test_account",
            account_name="Test Account",
            access_token="valid_token",
            refresh_token="valid_refresh",
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            with patch("builtins.open", mock_open(read_data='{"installed": {"client_id": "test", "client_secret": "test"}}')):
                with patch("json.load", return_value={"installed": {"client_id": "test", "client_secret": "test"}}):
                    with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                        mock_run_in_thread.side_effect = Exception("Request timeout")
                        
                        await agenda_handler(mock_update, mock_context)
                        
                        # Check for error message with new UX format
                        mock_update.message.reply_text.assert_called_once()
                        call_args = mock_update.message.reply_text.call_args
                        response_text = call_args[0][0]
                        parse_mode = call_args[1].get('parse_mode')
                        
                        assert "Unexpected error" in response_text
                        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_connect_google_handler_success(self, test_session, mock_update, mock_context):
        """Test successful Google Calendar connection."""
        mock_update.message.reply_text = AsyncMock()
        
        # Mock successful OAuth flow
        mock_creds = MagicMock(spec=Credentials)
        mock_creds.token = "new_access_token"
        mock_creds.refresh_token = "new_refresh_token"
        mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        mock_flow = MagicMock(spec=InstalledAppFlow)
        mock_flow.run_local_server.return_value = mock_creds
        
        # Patch get_session to yield test_session twice
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session, test_session])):
            with patch("os.path.exists", return_value=True):
                with patch("larrybot.plugins.calendar.InstalledAppFlow") as mock_flow_class:
                    mock_flow_class.from_client_secrets_file.return_value = mock_flow
                    with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                        mock_run_in_thread.return_value = mock_creds
                        
                        await connect_google_handler(mock_update, mock_context)
                        
                        # Verify success messages with new UX format
                        assert mock_update.message.reply_text.call_count == 2
                        
                        # Check first call (instructions)
                        first_call = mock_update.message.reply_text.call_args_list[0]
                        first_response = first_call[0][0]
                        first_parse_mode = first_call[1].get('parse_mode')
                        assert "ℹ️ **🔗 Connecting Google Calendar**" in first_response
                        assert "browser window will open" in first_response
                        assert first_parse_mode == 'MarkdownV2'
                        
                        # Check second call (success)
                        second_call = mock_update.message.reply_text.call_args_list[1]
                        second_response = second_call[0][0]
                        second_parse_mode = second_call[1].get('parse_mode')
                        assert "✅ **Success**" in second_response
                        assert "Google Calendar Connected" in second_response
                        assert second_parse_mode == 'MarkdownV2'
                        
                        # Verify token was stored
                        repo = CalendarTokenRepository(test_session)
                        stored_token = repo.get_token_by_provider("google")
                        assert stored_token.access_token == "new_access_token"
                        assert stored_token.refresh_token == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_connect_google_handler_oauth_failure(self, test_session, mock_update, mock_context):
        """Test Google Calendar connection when OAuth fails."""
        mock_update.message.reply_text = AsyncMock()
        
        mock_flow = MagicMock(spec=InstalledAppFlow)
        mock_flow.run_local_server.side_effect = Exception("OAuth failed")
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session, test_session])):
            with patch("os.path.exists", return_value=True):
                with patch("larrybot.plugins.calendar.InstalledAppFlow", return_value=mock_flow):
                    with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                        mock_run_in_thread.side_effect = Exception("OAuth failed")
                        
                        await connect_google_handler(mock_update, mock_context)
                        
                        # Verify error messages with new UX format
                        assert mock_update.message.reply_text.call_count == 2
                        
                        # Check first call (instructions)
                        first_call = mock_update.message.reply_text.call_args_list[0]
                        first_response = first_call[0][0]
                        first_parse_mode = first_call[1].get('parse_mode')
                        assert "ℹ️ **🔗 Connecting Google Calendar**" in first_response
                        assert first_parse_mode == 'MarkdownV2'
                        
                        # Check second call (error)
                        second_call = mock_update.message.reply_text.call_args_list[1]
                        second_response = second_call[0][0]
                        second_parse_mode = second_call[1].get('parse_mode')
                        assert "❌ **Error**" in second_response
                        assert "Authentication Failed" in second_response
                        assert "OAuth failed" in second_response
                        assert second_parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_connect_google_handler_malformed_client_secret_file(self, test_session, mock_update, mock_context):
        """Test connect_google handler with malformed client_secret.json."""
        mock_update.message.reply_text = AsyncMock()
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session, test_session])):
            with patch("os.path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data='invalid json')):
                    with patch("json.load", side_effect=json.JSONDecodeError("Invalid JSON", "", 0)):
                        await connect_google_handler(mock_update, mock_context)
                        
                        # Verify error messages with new UX format
                        assert mock_update.message.reply_text.call_count == 2
                        
                        # Check first call (instructions)
                        first_call = mock_update.message.reply_text.call_args_list[0]
                        first_response = first_call[0][0]
                        first_parse_mode = first_call[1].get('parse_mode')
                        assert "ℹ️ **🔗 Connecting Google Calendar**" in first_response
                        assert first_parse_mode == 'MarkdownV2'
                        
                        # Check second call (error)
                        second_call = mock_update.message.reply_text.call_args_list[1]
                        second_response = second_call[0][0]
                        second_parse_mode = second_call[1].get('parse_mode')
                        assert "❌ **Error**" in second_response
                        assert "Authentication Failed" in second_response
                        assert "Invalid JSON" in second_response
                        assert second_parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_disconnect_handler_token_removal_verification(self, test_session, mock_update, mock_context):
        """Test disconnect handler verifies token removal."""
        mock_update.message.reply_text = AsyncMock()
        
        # Create a token
        repo = CalendarTokenRepository(test_session)
        token = repo.add_token(
            provider="google",
            account_id="test_account",
            account_name="Test Account",
            access_token="test_token",
            refresh_token="test_refresh",
            expiry=datetime.now(timezone.utc)
        )
        
        # Verify token exists before disconnect
        assert repo.get_token_by_provider("google") is not None
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            await disconnect_handler(mock_update, mock_context)
            
            # Check success message with new UX format
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "✅ **Success**" in response_text
            assert "Google Calendar Disconnected" in response_text
            assert "token removed" in response_text
            assert parse_mode == 'MarkdownV2'
            
            # Verify token was actually removed
            assert repo.get_token_by_provider("google") is None


class TestCalendarPluginEdgeCases:
    """Edge case tests for Calendar Plugin."""

    @pytest.mark.asyncio
    async def test_agenda_handler_missing_start_field(self, test_session, mock_update, mock_context):
        """Test agenda handler with events missing start field."""
        mock_update.message.reply_text = AsyncMock()
        
        repo = CalendarTokenRepository(test_session)
        token = repo.add_token(
            provider="google",
            account_id="test_account",
            account_name="Test Account",
            access_token="valid_token",
            refresh_token="valid_refresh",
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Event missing start field
        mock_events = {
            "items": [
                {
                    "summary": "Test Event",
                    # Missing start field
                }
            ]
        }
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            with patch("builtins.open", mock_open(read_data='{"installed": {"client_id": "test", "client_secret": "test"}}')):
                with patch("json.load", return_value={"installed": {"client_id": "test", "client_secret": "test"}}):
                    with patch("larrybot.plugins.calendar.build") as mock_build:
                        mock_service = MagicMock()
                        mock_events_list = MagicMock()
                        mock_events_list.execute.return_value = mock_events
                        mock_service.events.return_value.list.return_value = mock_events_list
                        mock_build.return_value = mock_service
                        
                        with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                            mock_run_in_thread.side_effect = [mock_service, mock_events_list, mock_events]
                            
                            await agenda_handler(mock_update, mock_context)
                            
                            # Should handle missing start field gracefully
                            mock_update.message.reply_text.assert_called_once()
                            assert "Unexpected error" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_agenda_handler_rate_limit_exceeded(self, test_session, mock_update, mock_context):
        """Test agenda handler when API rate limit is exceeded."""
        mock_update.message.reply_text = AsyncMock()
        
        repo = CalendarTokenRepository(test_session)
        token = repo.add_token(
            provider="google",
            account_id="test_account",
            account_name="Test Account",
            access_token="valid_token",
            refresh_token="valid_refresh",
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            with patch("builtins.open", mock_open(read_data='{"installed": {"client_id": "test", "client_secret": "test"}}')):
                with patch("json.load", return_value={"installed": {"client_id": "test", "client_secret": "test"}}):
                    with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                        mock_run_in_thread.side_effect = Exception("Rate limit exceeded")
                        
                        await agenda_handler(mock_update, mock_context)
                        
                        # Check for error message with new UX format
                        mock_update.message.reply_text.assert_called_once()
                        call_args = mock_update.message.reply_text.call_args
                        response_text = call_args[0][0]
                        parse_mode = call_args[1].get('parse_mode')
                        
                        assert "Unexpected error" in response_text
                        assert parse_mode == 'MarkdownV2'


class TestCalendarPluginIntegration:
    """Integration tests for Calendar Plugin."""

    @pytest.mark.asyncio
    async def test_full_calendar_workflow(self, test_session, mock_update, mock_context):
        """Test complete calendar workflow: connect -> agenda -> disconnect."""
        mock_update.message.reply_text = AsyncMock()
        
        # Step 1: Connect Google Calendar
        mock_creds = MagicMock(spec=Credentials)
        mock_creds.token = "workflow_token"
        mock_creds.refresh_token = "workflow_refresh"
        mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        mock_flow = MagicMock(spec=InstalledAppFlow)
        mock_flow.run_local_server.return_value = mock_creds
        
        # Patch get_session to yield test_session twice for connect_google_handler
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session, test_session])):
            with patch("os.path.exists", return_value=True):
                with patch("larrybot.plugins.calendar.InstalledAppFlow") as mock_flow_class:
                    mock_flow_class.from_client_secrets_file.return_value = mock_flow
                    with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                        mock_run_in_thread.return_value = mock_creds
                        
                        await connect_google_handler(mock_update, mock_context)
                        
                        # Verify connection
                        repo = CalendarTokenRepository(test_session)
                        assert repo.get_token_by_provider("google") is not None
        
        # Step 2: Fetch agenda
        mock_update.message.reply_text.reset_mock()
        mock_events = {"items": [{"summary": "Workflow Event", "start": {"dateTime": "2025-06-28T10:00:00Z"}}]}
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            with patch("builtins.open", mock_open(read_data='{"installed": {"client_id": "test", "client_secret": "test"}}')):
                with patch("json.load", return_value={"installed": {"client_id": "test", "client_secret": "test"}}):
                    with patch("larrybot.plugins.calendar.build") as mock_build:
                        mock_service = MagicMock()
                        mock_events_list = MagicMock()
                        mock_events_list.execute.return_value = mock_events
                        mock_service.events.return_value.list.return_value = mock_events_list
                        mock_build.return_value = mock_service
                        
                        with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                            mock_run_in_thread.side_effect = [mock_service, mock_events_list, mock_events]
                            
                            await agenda_handler(mock_update, mock_context)
                            
                            # Check agenda response with new UX format
                            mock_update.message.reply_text.assert_called_once()
                            call_args = mock_update.message.reply_text.call_args
                            response_text = call_args[0][0]
                            reply_markup = call_args[1].get('reply_markup')
                            parse_mode = call_args[1].get('parse_mode')
                            
                            assert "📅 **Today's Agenda**" in response_text
                            assert "Workflow Event" in response_text
                            assert "10:00" in response_text
                            assert reply_markup is not None  # Should have inline keyboard
                            assert parse_mode == 'MarkdownV2'
        
        # Step 3: Disconnect
        mock_update.message.reply_text.reset_mock()
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            await disconnect_handler(mock_update, mock_context)
            
            # Check disconnect response
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "✅ **Success**" in response_text
            assert "Google Calendar Disconnected" in response_text
            assert parse_mode == 'MarkdownV2'
            
            # Verify token was removed
            assert repo.get_token_by_provider("google") is None

    @pytest.mark.asyncio
    async def test_calendar_handler_default_and_custom_days(self, test_session, mock_update, mock_context):
        """Test /calendar handler for default and custom day ranges."""
        mock_update.message.reply_text = AsyncMock()
        
        repo = CalendarTokenRepository(test_session)
        repo.add_token(
            provider="google",
            account_id="test_account",
            account_name="Test Account",
            access_token="valid_token",
            refresh_token="valid_refresh",
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Simulate /calendar with invalid account
        mock_context.args = ["abc"]
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            await calendar_handler(mock_update, mock_context)
            assert "Account Not Found" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_calendar_sync_handler_info_message(self, mock_update, mock_context):
        """Test /calendar_sync handler info message."""
        mock_update.message.reply_text = AsyncMock()
        await calendar_sync_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        assert "🔄 Calendar Sync" in response_text
        assert "coming soon" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_calendar_events_handler_info_and_validation(self, mock_update, mock_context):
        """Test /calendar_events handler info and validation."""
        mock_update.message.reply_text = AsyncMock()
        
        # Simulate /calendar_events with invalid number
        mock_context.args = ["abc"]
        await calendar_events_handler(mock_update, mock_context)
        assert "Feature coming soon" in mock_update.message.reply_text.call_args[0][0]


class TestCalendarPluginPerformance:
    """Performance tests for Calendar Plugin."""

    @pytest.mark.asyncio
    async def test_agenda_handler_performance(self, test_session, mock_update, mock_context):
        """Test agenda handler performance with large event list."""
        import time
        
        mock_update.message.reply_text = AsyncMock()
        
        repo = CalendarTokenRepository(test_session)
        token = repo.add_token(
            provider="google",
            account_id="test_account",
            account_name="Test Account",
            access_token="valid_token",
            refresh_token="valid_refresh",
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Create large event list
        large_events = {
            "items": [
                {
                    "summary": f"Event {i}",
                    "start": {"dateTime": f"2025-06-28T{i:02d}:00:00Z"}
                }
                for i in range(100)  # 100 events
            ]
        }
        
        with patch("larrybot.plugins.calendar.get_session", return_value=iter([test_session])):
            with patch("builtins.open", mock_open(read_data='{"installed": {"client_id": "test", "client_secret": "test"}}')):
                with patch("json.load", return_value={"installed": {"client_id": "test", "client_secret": "test"}}):
                    with patch("larrybot.plugins.calendar.build") as mock_build:
                        mock_service = MagicMock()
                        mock_events_list = MagicMock()
                        mock_events_list.execute.return_value = large_events
                        mock_service.events.return_value.list.return_value = mock_events_list
                        mock_build.return_value = mock_service
                        
                        with patch("larrybot.plugins.calendar.run_in_thread") as mock_run_in_thread:
                            mock_run_in_thread.side_effect = [mock_service, mock_events_list, large_events]
                            
                            start_time = time.time()
                            await agenda_handler(mock_update, mock_context)
                            end_time = time.time()
                            
                            # Should complete within reasonable time
                            assert end_time - start_time < 1.0  # 1 second threshold
                            
                            # Check response format and content
                            mock_update.message.reply_text.assert_called_once()
                            call_args = mock_update.message.reply_text.call_args
                            response_text = call_args[0][0]
                            reply_markup = call_args[1].get('reply_markup')
                            parse_mode = call_args[1].get('parse_mode')
                            
                            # Should have proper formatting
                            assert "📅 **Today's Agenda**" in response_text
                            assert "100 Events Scheduled" in response_text
                            assert reply_markup is not None
                            assert parse_mode == 'MarkdownV2'
                            
                            # Should show all events (count the numbered list items)
                            # Events are formatted as "1. *Event Name*", "2. *Event Name*", etc.
                            event_count = response_text.count("\\.")
                            assert event_count >= 100  # Should have at least 100 numbered events

    @pytest.mark.asyncio
    async def test_run_in_thread_performance(self):
        """Test run_in_thread helper performance."""
        import time
        
        def slow_function():
            time.sleep(0.1)  # Simulate slow operation
            return "slow_result"
        
        start_time = time.time()
        result = await run_in_thread(slow_function)
        end_time = time.time()
        
        assert result == "slow_result"
        assert end_time - start_time >= 0.1  # Should take at least 100ms
        assert end_time - start_time < 0.5   # But not too much longer 