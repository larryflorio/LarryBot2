"""
Centralized DateTime Service for LarryBot2

This service provides consistent datetime handling across the entire application,
ensuring proper timezone management, validation, and formatting.
"""
from typing import Optional, Union
from datetime import datetime, timedelta, date, timezone
import logging
from larrybot.utils.basic_datetime import get_utc_now, get_current_datetime

logger = logging.getLogger(__name__)


class DateTimeService:
    """
    Centralized datetime handling for the entire application.
    
    This service ensures consistent timezone-aware datetime operations
    across all commands, services, and models.
    """
    
    @staticmethod
    def parse_user_date(date_str: str, use_nlp: bool = True) -> Optional[datetime]:
        """
        Parse user input to timezone-aware datetime.
        
        Supports both structured (YYYY-MM-DD) and natural language formats.
        
        Args:
            date_str: Date string (YYYY-MM-DD or natural language like "Monday", "next week")
            use_nlp: Whether to attempt NLP parsing after structured parsing fails
            
        Returns:
            Timezone-aware datetime at end of day (23:59:59) in local timezone,
            or None if parsing fails
        """
        if not date_str or not date_str.strip():
            logger.warning("Empty date string provided")
            return None
            
        date_str = date_str.strip()
        
        # Try structured parsing first (faster for known formats)
        try:
            local_date = datetime.strptime(date_str, '%Y-%m-%d')
            local_datetime = local_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            timezone_aware = local_datetime.replace(tzinfo=timezone.utc)
            logger.debug(f"Parsed structured date '{date_str}' to {timezone_aware}")
            return timezone_aware
        except ValueError:
            logger.debug(f"Structured parsing failed for '{date_str}', attempting NLP parsing")
        
        # Fallback to NLP parsing if enabled
        if use_nlp:
            try:
                from dateparser import parse as parse_date
                parsed_date = parse_date(date_str, settings={'PREFER_DATES_FROM': 'future'})
                if parsed_date:
                    # Ensure timezone-aware
                    if parsed_date.tzinfo is None:
                        parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    
                    # Convert to end of day for consistency with structured parsing
                    end_of_day = parsed_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                    logger.debug(f"Parsed NLP date '{date_str}' to {end_of_day}")
                    return end_of_day
                else:
                    logger.debug(f"NLP parsing returned None for '{date_str}'")
            except Exception as e:
                logger.debug(f"NLP parsing failed for '{date_str}': {e}")
        
        logger.warning(f"Failed to parse date '{date_str}' with both structured and NLP methods")
        return None
    
    @staticmethod
    def parse_user_datetime(datetime_str: str, format_str: str = '%Y-%m-%d %H:%M:%S') -> Optional[datetime]:
        """
        Parse user input datetime to timezone-aware datetime.
        
        Args:
            datetime_str: Datetime string
            format_str: Format string for parsing
            
        Returns:
            Timezone-aware datetime in local timezone, or None if parsing fails
        """
        try:
            # Parse as local datetime
            local_datetime = datetime.strptime(datetime_str, format_str)
            # Make timezone-aware (assume local timezone)
            timezone_aware = local_datetime.replace(tzinfo=timezone.utc)
            logger.debug(f"Parsed datetime '{datetime_str}' to {timezone_aware}")
            return timezone_aware
        except ValueError as e:
            logger.warning(f"Failed to parse datetime '{datetime_str}': {e}")
            return None
    
    @staticmethod
    def create_due_date_for_today() -> datetime:
        """
        Create end-of-day datetime for today.
        
        Returns:
            Timezone-aware datetime at 23:59:59 today in local timezone
        """
        today = get_current_datetime().date()
        end_of_day = datetime.combine(today, datetime.max.time())
        timezone_aware = end_of_day.replace(tzinfo=timezone.utc)
        logger.debug(f"Created due date for today: {timezone_aware}")
        return timezone_aware
    
    @staticmethod
    def create_due_date_for_tomorrow() -> datetime:
        """
        Create end-of-day datetime for tomorrow.
        
        Returns:
            Timezone-aware datetime at 23:59:59 tomorrow in local timezone
        """
        tomorrow = get_current_datetime().date() + timedelta(days=1)
        end_of_day = datetime.combine(tomorrow, datetime.max.time())
        timezone_aware = end_of_day.replace(tzinfo=timezone.utc)
        logger.debug(f"Created due date for tomorrow: {timezone_aware}")
        return timezone_aware
    
    @staticmethod
    def create_due_date_for_week() -> datetime:
        """
        Create end-of-day datetime for end of current week (Sunday).
        
        Returns:
            Timezone-aware datetime at 23:59:59 on Sunday in local timezone
        """
        today = get_current_datetime().date()
        days_until_sunday = (6 - today.weekday()) % 7
        end_of_week = today + timedelta(days=days_until_sunday)
        end_of_day = datetime.combine(end_of_week, datetime.max.time())
        timezone_aware = end_of_day.replace(tzinfo=timezone.utc)
        logger.debug(f"Created due date for end of week: {timezone_aware}")
        return timezone_aware
    
    @staticmethod
    def create_due_date_for_next_week() -> datetime:
        """
        Create end-of-day datetime for end of next week (Sunday).
        
        Returns:
            Timezone-aware datetime at 23:59:59 on Sunday next week in local timezone
        """
        today = get_current_datetime().date()
        days_until_next_sunday = (6 - today.weekday()) % 7 + 7
        end_of_next_week = today + timedelta(days=days_until_next_sunday)
        end_of_day = datetime.combine(end_of_next_week, datetime.max.time())
        timezone_aware = end_of_day.replace(tzinfo=timezone.utc)
        logger.debug(f"Created due date for end of next week: {timezone_aware}")
        return timezone_aware
    
    @staticmethod
    def validate_due_date(due_date: datetime) -> bool:
        """
        Validate due date is not in the past.
        
        Args:
            due_date: Datetime to validate
            
        Returns:
            True if due date is valid (not in the past), False otherwise
        """
        if due_date is None:
            return True  # No due date is valid
        
        # Ensure timezone-aware for comparison
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=timezone.utc)
        
        now = get_utc_now()
        is_valid = due_date > now
        
        if not is_valid:
            logger.warning(f"Due date {due_date} is in the past (current time: {now})")
        
        return is_valid
    
    @staticmethod
    def format_for_display(dt: Optional[Union[datetime, str]]) -> str:
        """
        Format datetime for user display.
        
        Args:
            dt: Datetime to format, or None, or string
            
        Returns:
            Formatted string for display, or 'None' if dt is None
        """
        if dt is None:
            return 'None'
        
        # Handle string input (for backward compatibility)
        if isinstance(dt, str):
            return dt
        
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Convert to local time for display
        local_dt = dt.astimezone(timezone.utc)  # For now, using UTC as local
        return local_dt.strftime('%Y-%m-%d %H:%M')
    
    @staticmethod
    def format_date_for_display(dt: Optional[Union[datetime, str]]) -> str:
        """
        Format datetime as date only for user display.
        
        Args:
            dt: Datetime to format, or None, or string
            
        Returns:
            Formatted date string, or 'None' if dt is None
        """
        if dt is None:
            return 'None'
        
        # Handle string input (for backward compatibility)
        if isinstance(dt, str):
            return dt
        
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Convert to local time for display
        local_dt = dt.astimezone(timezone.utc)  # For now, using UTC as local
        return local_dt.strftime('%Y-%m-%d')
    
    @staticmethod
    def format_for_storage(dt: Optional[Union[datetime, str]]) -> Optional[datetime]:
        """
        Convert datetime to UTC for database storage.
        
        Args:
            dt: Datetime to convert, or None, or string
            
        Returns:
            UTC datetime for storage, or None if dt is None
        """
        if dt is None:
            return None
        
        # Handle string input (for backward compatibility)
        if isinstance(dt, str):
            parsed = DateTimeService.parse_user_date(dt)
            if parsed is None:
                return None
            dt = parsed
        
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Convert to UTC
        utc_dt = dt.astimezone(timezone.utc)
        logger.debug(f"Converted {dt} to UTC for storage: {utc_dt}")
        return utc_dt
    
    @staticmethod
    def get_start_of_day(dt: Optional[datetime] = None) -> datetime:
        """
        Get start of day (00:00:00) for the given datetime or today.
        
        For calendar operations, this returns the start of the local day.
        For general use, this respects the input timezone.
        
        Args:
            dt: Datetime to get start of day for, or None for today
            
        Returns:
            Start of day datetime in the same timezone as input
        """
        if dt is None:
            dt = get_current_datetime()
        
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Use TimeZoneService for proper timezone handling
        from larrybot.core.timezone import get_timezone_service
        tz_service = get_timezone_service()
        
        # Convert to local timezone for day boundary calculation
        local_dt = tz_service.to_local(dt)
        local_start_of_day = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Convert back to the original timezone
        if dt.tzinfo == timezone.utc:
            # For UTC input, return the local start of day converted to UTC
            result = tz_service.to_utc(local_start_of_day)
        else:
            # For other timezones, convert local start of day to that timezone
            result = local_start_of_day.astimezone(dt.tzinfo)
        
        logger.debug(f"Start of day for {dt}: {result}")
        return result

    @staticmethod
    def get_end_of_day(dt: Optional[datetime] = None) -> datetime:
        """
        Get end of day (23:59:59) for the given datetime or today.
        
        For calendar operations, this returns the end of the local day.
        For general use, this respects the input timezone.
        
        Args:
            dt: Datetime to get end of day for, or None for today
            
        Returns:
            End of day datetime in the same timezone as input
        """
        if dt is None:
            dt = get_current_datetime()
        
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Use TimeZoneService for proper timezone handling
        from larrybot.core.timezone import get_timezone_service
        tz_service = get_timezone_service()
        
        # Convert to local timezone for day boundary calculation
        local_dt = tz_service.to_local(dt)
        local_end_of_day = local_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Convert back to the original timezone
        if dt.tzinfo == timezone.utc:
            # For UTC input, return the local end of day converted to UTC
            result = tz_service.to_utc(local_end_of_day)
        else:
            # For other timezones, convert local end of day to that timezone
            result = local_end_of_day.astimezone(dt.tzinfo)
        
        logger.debug(f"End of day for {dt}: {result}")
        return result
    
    @staticmethod
    def is_today(dt: datetime) -> bool:
        """
        Check if datetime is today.
        
        Args:
            dt: Datetime to check
            
        Returns:
            True if datetime is today, False otherwise
        """
        if dt is None:
            return False
        
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        today = get_current_datetime().date()
        return dt.date() == today
    
    @staticmethod
    def is_overdue(due_date: datetime) -> bool:
        """
        Check if a due date is overdue.
        
        A task is overdue only if its due date is before today's calendar date.
        Tasks due today (same calendar date) are NOT considered overdue.
        
        Args:
            due_date: Due date to check
            
        Returns:
            True if overdue (due date is before today), False otherwise
        """
        if due_date is None:
            return False
        
        # Use timezone service for proper local date comparison
        from larrybot.core.timezone import get_timezone_service
        tz_service = get_timezone_service()
        
        # Get today's date in local timezone
        today_local = tz_service.now().date()
        
        # Convert due date to local timezone and extract date
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=timezone.utc)
        
        due_date_local = tz_service.to_local(due_date).date()
        
        # Task is overdue only if due date is before today
        return due_date_local < today_local
    
    @staticmethod
    def days_until_due(due_date: datetime) -> Optional[int]:
        """
        Calculate days until due date.
        
        Args:
            due_date: Due date to calculate
            
        Returns:
            Number of days until due, or None if due_date is None
        """
        if due_date is None:
            return None
        
        # Ensure timezone-aware
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=timezone.utc)
        
        now = get_utc_now()
        delta = due_date.date() - now.date()
        return delta.days 