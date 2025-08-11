"""
Tests for DateTimeService

This module tests the centralized datetime handling service to ensure
consistent timezone-aware datetime operations across the application.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from larrybot.services.datetime_service import DateTimeService


class TestDateTimeService:
    """Test cases for DateTimeService."""

    def test_parse_user_date_valid(self):
        """Test parsing valid date string."""
        result = DateTimeService.parse_user_date("2025-07-15")
        
        assert result is not None
        assert result.tzinfo is not None
        
        # Convert back to local timezone to verify the date
        from larrybot.core.timezone import get_timezone_service
        tz_service = get_timezone_service()
        local_result = tz_service.to_local(result)
        
        assert local_result.date() == datetime(2025, 7, 15).date()
        assert local_result.hour == 23
        assert local_result.minute == 59
        assert local_result.second == 59

    def test_parse_user_date_invalid(self):
        """Test parsing invalid date string."""
        result = DateTimeService.parse_user_date("invalid-date")
        assert result is None

    def test_parse_user_date_empty(self):
        """Test parsing empty date string."""
        result = DateTimeService.parse_user_date("")
        assert result is None

    def test_parse_user_date_whitespace(self):
        """Test parsing date string with whitespace."""
        result = DateTimeService.parse_user_date("  2025-07-15  ")
        
        assert result is not None
        assert result.tzinfo is not None
        
        # Convert back to local timezone to verify the date
        from larrybot.core.timezone import get_timezone_service
        tz_service = get_timezone_service()
        local_result = tz_service.to_local(result)
        
        assert local_result.date() == datetime(2025, 7, 15).date()

    def test_parse_user_date_nlp_disabled(self):
        """Test parsing with NLP disabled."""
        # This should fail because "Monday" is not a valid YYYY-MM-DD format
        result = DateTimeService.parse_user_date("Monday", use_nlp=False)
        assert result is None

    @patch('dateparser.parse')
    def test_parse_user_date_nlp_success(self, mock_parse_date):
        """Test successful NLP date parsing."""
        # Mock dateparser to return a specific date
        mock_date = datetime(2025, 7, 15, 14, 30, 0)
        mock_parse_date.return_value = mock_date
        
        result = DateTimeService.parse_user_date("next Monday")
        
        assert result is not None
        assert result.tzinfo is not None
        assert result.date() == datetime(2025, 7, 15).date()
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        mock_parse_date.assert_called_once()

    @patch('dateparser.parse')
    def test_parse_user_date_nlp_timezone_aware(self, mock_parse_date):
        """Test NLP parsing with timezone-aware datetime."""
        # Mock dateparser to return a timezone-aware datetime
        mock_date = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
        mock_parse_date.return_value = mock_date
        
        result = DateTimeService.parse_user_date("tomorrow")
        
        assert result is not None
        assert result.tzinfo is not None
        assert result.date() == datetime(2025, 7, 15).date()
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59

    @patch('dateparser.parse')
    def test_parse_user_date_nlp_failure(self, mock_parse_date):
        """Test NLP parsing failure."""
        mock_parse_date.return_value = None
        
        result = DateTimeService.parse_user_date("invalid natural language")
        assert result is None

    @patch('dateparser.parse')
    def test_parse_user_date_nlp_exception(self, mock_parse_date):
        """Test NLP parsing with exception."""
        mock_parse_date.side_effect = Exception("NLP parsing error")
        
        result = DateTimeService.parse_user_date("some date")
        assert result is None

    def test_parse_user_date_natural_language_examples(self):
        """Test various natural language date inputs."""
        # These tests require dateparser to be available
        try:
            from dateparser import parse as parse_date
        except ImportError:
            pytest.skip("dateparser not available")
        
        # Test common natural language patterns
        test_cases = [
            "Monday",
            "next Monday", 
            "tomorrow",
            "next week",
            "in 3 days",
            "next month",
            "Friday"
        ]
        
        for test_input in test_cases:
            result = DateTimeService.parse_user_date(test_input)
            # Should either parse successfully or return None, but not raise exception
            if result is not None:
                assert result.tzinfo is not None
                assert result.hour == 23
                assert result.minute == 59
                assert result.second == 59

    def test_parse_user_datetime_valid(self):
        """Test parsing valid datetime string."""
        result = DateTimeService.parse_user_datetime("2025-07-15 14:30:00")
        
        assert result is not None
        assert result.tzinfo is not None
        assert result.date() == datetime(2025, 7, 15).date()
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 0

    def test_parse_user_datetime_invalid(self):
        """Test parsing invalid datetime string."""
        result = DateTimeService.parse_user_datetime("invalid-datetime")
        assert result is None

    def test_create_due_date_for_today(self):
        """Test creating due date for today."""
        result = DateTimeService.create_due_date_for_today()
        
        assert result is not None
        assert result.tzinfo is not None
        
        # Convert back to local timezone to verify it's end of today
        from larrybot.core.timezone import get_timezone_service
        tz_service = get_timezone_service()
        local_result = tz_service.to_local(result)
        today_local = tz_service.now().date()
        
        assert local_result.date() == today_local
        assert local_result.hour == 23
        assert local_result.minute == 59
        assert local_result.second == 59

    def test_create_due_date_for_tomorrow(self):
        """Test creating due date for tomorrow."""
        result = DateTimeService.create_due_date_for_tomorrow()
        
        assert result is not None
        assert result.tzinfo is not None
        
        # Convert back to local timezone to verify it's end of tomorrow
        from larrybot.core.timezone import get_timezone_service
        tz_service = get_timezone_service()
        local_result = tz_service.to_local(result)
        tomorrow_local = tz_service.now().date() + timedelta(days=1)
        
        assert local_result.date() == tomorrow_local
        assert local_result.hour == 23
        assert local_result.minute == 59
        assert local_result.second == 59

    def test_create_due_date_for_week(self):
        """Test creating due date for end of current week."""
        result = DateTimeService.create_due_date_for_week()
        
        assert result is not None
        assert result.tzinfo is not None
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        
        # Should be a Sunday (weekday 6)
        assert result.weekday() == 6

    def test_create_due_date_for_next_week(self):
        """Test creating due date for end of next week."""
        result = DateTimeService.create_due_date_for_next_week()
        
        assert result is not None
        assert result.tzinfo is not None
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        
        # Should be a Sunday (weekday 6)
        assert result.weekday() == 6
        
        # Should be at least 7 days in the future
        today = datetime.now(timezone.utc).date()
        assert (result.date() - today).days >= 7

    def test_validate_due_date_future(self):
        """Test validating future due date."""
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        result = DateTimeService.validate_due_date(future_date)
        assert result is True

    def test_validate_due_date_past(self):
        """Test validating past due date."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        result = DateTimeService.validate_due_date(past_date)
        assert result is False

    def test_validate_due_date_none(self):
        """Test validating None due date."""
        result = DateTimeService.validate_due_date(None)
        assert result is True

    def test_validate_due_date_naive(self):
        """Test validating naive datetime."""
        naive_date = datetime.now()
        result = DateTimeService.validate_due_date(naive_date)
        # Should handle naive datetime gracefully
        assert isinstance(result, bool)

    def test_format_for_display_none(self):
        """Test formatting None datetime."""
        result = DateTimeService.format_for_display(None)
        assert result == 'None'

    def test_format_for_display_string(self):
        """Test formatting string datetime."""
        result = DateTimeService.format_for_display("2025-07-15")
        assert result == "2025-07-15"

    def test_format_for_display_datetime(self):
        """Test formatting datetime object."""
        dt = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = DateTimeService.format_for_display(dt)
        assert "2025-07-15" in result

    def test_format_date_for_display_none(self):
        """Test formatting None date."""
        result = DateTimeService.format_date_for_display(None)
        assert result == 'None'

    def test_format_date_for_display_string(self):
        """Test formatting string date."""
        result = DateTimeService.format_date_for_display("2025-07-15")
        assert result == "2025-07-15"

    def test_format_date_for_display_datetime(self):
        """Test formatting datetime object as date."""
        dt = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = DateTimeService.format_date_for_display(dt)
        assert result == "2025-07-15"

    def test_format_for_storage_none(self):
        """Test formatting None for storage."""
        result = DateTimeService.format_for_storage(None)
        assert result is None

    def test_format_for_storage_string(self):
        """Test formatting string for storage."""
        result = DateTimeService.format_for_storage("2025-07-15")
        assert result is not None
        assert result.tzinfo is not None

    def test_format_for_storage_datetime(self):
        """Test formatting datetime for storage."""
        dt = datetime(2025, 7, 15, 14, 30, 0)
        result = DateTimeService.format_for_storage(dt)
        assert result is not None
        assert result.tzinfo is not None

    def test_get_start_of_day(self):
        """Test getting start of day."""
        dt = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = DateTimeService.get_start_of_day(dt)
        
        assert result is not None
        assert result.tzinfo is not None
        # For calendar operations, this should return the start of the local day
        # converted to the input timezone (UTC)
        assert result.date() == datetime(2025, 7, 15).date()
        # The hour will depend on the local timezone, but should be consistent
        assert result.minute == 0
        assert result.second == 0

    def test_get_start_of_day_none(self):
        """Test getting start of day with None input."""
        result = DateTimeService.get_start_of_day()
        
        assert result is not None
        assert result.tzinfo is not None
        # Should return start of local day in UTC
        assert result.minute == 0
        assert result.second == 0

    def test_get_end_of_day(self):
        """Test getting end of day."""
        dt = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = DateTimeService.get_end_of_day(dt)
        
        assert result is not None
        assert result.tzinfo is not None
        # For calendar operations, this should return the end of the local day
        # converted to the input timezone (UTC). Due to timezone conversion,
        # the end of day might be on the next day in UTC.
        # The important thing is that it represents the end of the local day.
        assert result.minute == 59
        assert result.second == 59

    def test_get_end_of_day_none(self):
        """Test getting end of day with None input."""
        result = DateTimeService.get_end_of_day()
        
        assert result is not None
        assert result.tzinfo is not None
        # Should return end of local day in UTC
        assert result.minute == 59
        assert result.second == 59

    def test_is_today(self):
        """Test checking if date is today."""
        today = datetime.now(timezone.utc)
        result = DateTimeService.is_today(today)
        assert result is True

    def test_is_today_different_date(self):
        """Test checking if date is not today."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        result = DateTimeService.is_today(tomorrow)
        assert result is False

    def test_is_overdue_future(self):
        """Test checking if future date is overdue."""
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        result = DateTimeService.is_overdue(future_date)
        assert result is False

    def test_is_overdue_past(self):
        """Test checking if past date is overdue."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        result = DateTimeService.is_overdue(past_date)
        assert result is True

    def test_days_until_due_future(self):
        """Test calculating days until due for future date."""
        future_date = datetime.now(timezone.utc) + timedelta(days=5)
        result = DateTimeService.days_until_due(future_date)
        assert result is not None
        assert result > 0

    def test_days_until_due_past(self):
        """Test calculating days until due for past date."""
        past_date = datetime.now(timezone.utc) - timedelta(days=5)
        result = DateTimeService.days_until_due(past_date)
        assert result is not None
        assert result < 0

    def test_days_until_due_today(self):
        """Test calculating days until due for today."""
        today = datetime.now(timezone.utc)
        result = DateTimeService.days_until_due(today)
        assert result is not None
        assert result == 0

    def test_edge_case_year_boundary(self):
        """Test date parsing around year boundary."""
        result = DateTimeService.parse_user_date("2024-12-31")
        assert result is not None
        
        # Convert back to local timezone to verify the date
        from larrybot.core.timezone import get_timezone_service
        tz_service = get_timezone_service()
        local_result = tz_service.to_local(result)
        
        assert local_result.date() == datetime(2024, 12, 31).date()
        assert local_result.hour == 23
        assert local_result.minute == 59
        assert local_result.second == 59

    def test_edge_case_leap_year(self):
        """Test date parsing for leap year."""
        result = DateTimeService.parse_user_date("2024-02-29")
        assert result is not None
        
        # Convert back to local timezone to verify the date
        from larrybot.core.timezone import get_timezone_service
        tz_service = get_timezone_service()
        local_result = tz_service.to_local(result)
        
        assert local_result.date() == datetime(2024, 2, 29).date()

    def test_edge_case_invalid_leap_year(self):
        """Test date parsing for invalid leap year date."""
        result = DateTimeService.parse_user_date("2023-02-29")
        assert result is None 