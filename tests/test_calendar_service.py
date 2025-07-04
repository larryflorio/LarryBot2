"""
Tests for Calendar Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from larrybot.services.calendar_service import CalendarService


class TestCalendarService:
    """Test CalendarService functionality."""
    
    def test_calendar_service_initialization(self):
        """Test CalendarService can be initialized."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            service = CalendarService()
            assert service.client_secrets is None
    
    def test_format_event_for_daily_report(self):
        """Test formatting calendar events for daily report."""
        service = CalendarService()
        
        # Test timed event
        event = {
            "start": {"dateTime": "2024-01-15T10:30:00Z"},
            "end": {"dateTime": "2024-01-15T11:30:00Z"},
            "summary": "Test Meeting",
            "_account_name": "Test Account"
        }
        
        formatted = service.format_event_for_daily_report(event)
        assert formatted["time"] == "10:30 AM"
        assert formatted["name"] == "Test Meeting"
        assert formatted["duration"] == " (1h)"
        assert formatted["account"] == "Test Account"
        
        # Test all-day event
        event = {
            "start": {"date": "2024-01-15"},
            "end": {"date": "2024-01-16"},
            "summary": "All Day Event",
            "_account_name": "Test Account"
        }
        
        formatted = service.format_event_for_daily_report(event)
        assert formatted["time"] == "All day"
        assert formatted["name"] == "All Day Event"
        assert formatted["duration"] == ""
        assert formatted["account"] == "Test Account"
    
    @pytest.mark.asyncio
    async def test_get_todays_events_no_secrets(self):
        """Test get_todays_events when no client secrets are available."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            service = CalendarService()
            events = await service.get_todays_events()
            assert events == []
    
    @pytest.mark.asyncio
    async def test_get_todays_events_no_tokens(self):
        """Test get_todays_events when no tokens are available."""
        mock_secrets = {"client_id": "test", "client_secret": "test"}
        
        with patch('builtins.open', return_value=MagicMock()) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = '{"installed": {"client_id": "test", "client_secret": "test"}}'
            
            with patch('larrybot.storage.calendar_token_repository.CalendarTokenRepository') as mock_repo:
                mock_repo.return_value.get_active_tokens.return_value = []
                
                service = CalendarService()
                events = await service.get_todays_events()
                assert events == [] 