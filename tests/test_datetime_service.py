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
        assert result.date() == datetime(2025, 7, 15).date()
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59

    def test_parse_user_date_invalid(self):
        """Test parsing invalid date string."""
        result = DateTimeService.parse_user_date("invalid-date")
        assert result is None

    def test_parse_user_date_empty(self):
        """Test parsing empty date string."""
        result = DateTimeService.parse_user_date("")
        assert result is None

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
        with patch('larrybot.services.datetime_service.get_current_datetime') as mock_get_current:
            mock_get_current.return_value = datetime(2025, 7, 15, 10, 30, 0, tzinfo=timezone.utc)
            
            result = DateTimeService.create_due_date_for_today()
            
            assert result is not None
            assert result.tzinfo is not None
            assert result.date() == datetime(2025, 7, 15).date()
            assert result.hour == 23
            assert result.minute == 59
            assert result.second == 59

    def test_create_due_date_for_tomorrow(self):
        """Test creating due date for tomorrow."""
        with patch('larrybot.services.datetime_service.get_current_datetime') as mock_get_current:
            mock_get_current.return_value = datetime(2025, 7, 15, 10, 30, 0, tzinfo=timezone.utc)
            
            result = DateTimeService.create_due_date_for_tomorrow()
            
            assert result is not None
            assert result.tzinfo is not None
            assert result.date() == datetime(2025, 7, 16).date()
            assert result.hour == 23
            assert result.minute == 59
            assert result.second == 59

    def test_create_due_date_for_week(self):
        """Test creating due date for end of week."""
        with patch('larrybot.services.datetime_service.get_current_datetime') as mock_get_current:
            # Tuesday, July 15, 2025
            mock_get_current.return_value = datetime(2025, 7, 15, 10, 30, 0, tzinfo=timezone.utc)
            
            result = DateTimeService.create_due_date_for_week()
            
            assert result is not None
            assert result.tzinfo is not None
            # Should be Sunday, July 20, 2025
            assert result.date() == datetime(2025, 7, 20).date()
            assert result.hour == 23
            assert result.minute == 59
            assert result.second == 59

    def test_create_due_date_for_next_week(self):
        """Test creating due date for end of next week."""
        with patch('larrybot.services.datetime_service.get_current_datetime') as mock_get_current:
            # Tuesday, July 15, 2025
            mock_get_current.return_value = datetime(2025, 7, 15, 10, 30, 0, tzinfo=timezone.utc)
            
            result = DateTimeService.create_due_date_for_next_week()
            
            assert result is not None
            assert result.tzinfo is not None
            # Should be Sunday, July 27, 2025
            assert result.date() == datetime(2025, 7, 27).date()
            assert result.hour == 23
            assert result.minute == 59
            assert result.second == 59

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
        naive_date = datetime(2025, 7, 15, 23, 59, 59)
        result = DateTimeService.validate_due_date(naive_date)
        # Should handle naive datetime gracefully
        assert isinstance(result, bool)

    def test_format_for_display_with_datetime(self):
        """Test formatting datetime for display."""
        dt = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = DateTimeService.format_for_display(dt)
        assert result == "2025-07-15 14:30"

    def test_format_for_display_none(self):
        """Test formatting None for display."""
        result = DateTimeService.format_for_display(None)
        assert result == "None"

    def test_format_date_for_display_with_datetime(self):
        """Test formatting datetime as date for display."""
        dt = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = DateTimeService.format_date_for_display(dt)
        assert result == "2025-07-15"

    def test_format_date_for_display_none(self):
        """Test formatting None as date for display."""
        result = DateTimeService.format_date_for_display(None)
        assert result == "None"

    def test_format_for_storage_with_datetime(self):
        """Test formatting datetime for storage."""
        dt = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = DateTimeService.format_for_storage(dt)
        assert result == dt
        assert result.tzinfo == timezone.utc

    def test_format_for_storage_none(self):
        """Test formatting None for storage."""
        result = DateTimeService.format_for_storage(None)
        assert result is None

    def test_format_for_storage_naive(self):
        """Test formatting naive datetime for storage."""
        naive_dt = datetime(2025, 7, 15, 14, 30, 0)
        result = DateTimeService.format_for_storage(naive_dt)
        assert result.tzinfo == timezone.utc
        assert result.date() == naive_dt.date()
        assert result.hour == naive_dt.hour
        assert result.minute == naive_dt.minute

    def test_get_start_of_day_with_datetime(self):
        """Test getting start of day for specific datetime."""
        dt = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = DateTimeService.get_start_of_day(dt)
        assert result.date() == datetime(2025, 7, 15).date()
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.tzinfo == timezone.utc

    def test_get_start_of_day_none(self):
        """Test getting start of day for today."""
        with patch('larrybot.services.datetime_service.get_current_datetime') as mock_get_current:
            mock_get_current.return_value = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
            
            result = DateTimeService.get_start_of_day(None)
            assert result.date() == datetime(2025, 7, 15).date()
            assert result.hour == 0
            assert result.minute == 0
            assert result.second == 0

    def test_get_end_of_day_with_datetime(self):
        """Test getting end of day for specific datetime."""
        dt = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = DateTimeService.get_end_of_day(dt)
        assert result.date() == datetime(2025, 7, 15).date()
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        assert result.tzinfo == timezone.utc

    def test_get_end_of_day_none(self):
        """Test getting end of day for today."""
        with patch('larrybot.services.datetime_service.get_current_datetime') as mock_get_current:
            mock_get_current.return_value = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
            
            result = DateTimeService.get_end_of_day(None)
            assert result.date() == datetime(2025, 7, 15).date()
            assert result.hour == 23
            assert result.minute == 59
            assert result.second == 59

    def test_is_today_true(self):
        """Test checking if datetime is today."""
        with patch('larrybot.services.datetime_service.get_current_datetime') as mock_get_current:
            mock_get_current.return_value = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
            
            dt = datetime(2025, 7, 15, 10, 0, 0, tzinfo=timezone.utc)
            result = DateTimeService.is_today(dt)
            assert result is True

    def test_is_today_false(self):
        """Test checking if datetime is not today."""
        with patch('larrybot.services.datetime_service.get_current_datetime') as mock_get_current:
            mock_get_current.return_value = datetime(2025, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
            
            dt = datetime(2025, 7, 16, 10, 0, 0, tzinfo=timezone.utc)
            result = DateTimeService.is_today(dt)
            assert result is False

    def test_is_today_none(self):
        """Test checking if None datetime is today."""
        result = DateTimeService.is_today(None)
        assert result is False

    def test_is_overdue_true(self):
        """Test checking if due date is overdue."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        result = DateTimeService.is_overdue(past_date)
        assert result is True

    def test_is_overdue_false(self):
        """Test checking if due date is not overdue."""
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        result = DateTimeService.is_overdue(future_date)
        assert result is False

    def test_is_overdue_none(self):
        """Test checking if None due date is overdue."""
        result = DateTimeService.is_overdue(None)
        assert result is False

    def test_days_until_due_future(self):
        """Test calculating days until due date in future."""
        future_date = datetime.now(timezone.utc) + timedelta(days=5)
        result = DateTimeService.days_until_due(future_date)
        assert result == 5

    def test_days_until_due_past(self):
        """Test calculating days until due date in past."""
        past_date = datetime.now(timezone.utc) - timedelta(days=5)
        result = DateTimeService.days_until_due(past_date)
        assert result == -5

    def test_days_until_due_none(self):
        """Test calculating days until None due date."""
        result = DateTimeService.days_until_due(None)
        assert result is None

    def test_edge_case_weekend_week_calculation(self):
        """Test week calculation when today is Sunday."""
        with patch('larrybot.services.datetime_service.get_current_datetime') as mock_get_current:
            # Sunday, July 20, 2025
            mock_get_current.return_value = datetime(2025, 7, 20, 10, 30, 0, tzinfo=timezone.utc)
            
            result = DateTimeService.create_due_date_for_week()
            # Should still be Sunday, July 20, 2025 (same day)
            assert result.date() == datetime(2025, 7, 20).date()

    def test_edge_case_year_boundary(self):
        """Test date parsing around year boundary."""
        result = DateTimeService.parse_user_date("2024-12-31")
        assert result is not None
        assert result.date() == datetime(2024, 12, 31).date()
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59

    def test_edge_case_leap_year(self):
        """Test date parsing for leap year."""
        result = DateTimeService.parse_user_date("2024-02-29")
        assert result is not None
        assert result.date() == datetime(2024, 2, 29).date()

    def test_edge_case_invalid_leap_year(self):
        """Test date parsing for invalid leap year date."""
        result = DateTimeService.parse_user_date("2023-02-29")
        assert result is None 