"""
Timezone-aware datetime utilities for LarryBot2.

This module provides timezone-aware replacements for common datetime operations
used throughout the system, ensuring consistent timezone handling.
"""

from typing import Optional, Union
from datetime import datetime, timedelta, date
from larrybot.core.timezone import get_timezone_service, now, utc_now, to_local, to_utc, format_datetime


def get_current_datetime() -> datetime:
    """
    Get current datetime in local timezone.
    
    Returns:
        Current datetime in local timezone
    """
    return now()


def get_current_utc_datetime() -> datetime:
    """
    Get current datetime in UTC.
    
    Returns:
        Current datetime in UTC
    """
    return utc_now()


def get_today_date() -> date:
    """
    Get today's date in local timezone.
    
    Returns:
        Today's date
    """
    return now().date()


def get_start_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    Get start of day (00:00:00) for the given datetime or today.
    
    Args:
        dt: Datetime to get start of day for, or None for today
        
    Returns:
        Start of day datetime in local timezone
    """
    if dt is None:
        dt = now()
    elif dt.tzinfo is None:
        # Assume local timezone if naive
        dt = dt.replace(tzinfo=get_timezone_service().timezone)
    
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_end_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    Get end of day (23:59:59) for the given datetime or today.
    
    Args:
        dt: Datetime to get end of day for, or None for today
        
    Returns:
        End of day datetime in local timezone
    """
    if dt is None:
        dt = now()
    elif dt.tzinfo is None:
        # Assume local timezone if naive
        dt = dt.replace(tzinfo=get_timezone_service().timezone)
    
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def get_start_of_week(dt: Optional[datetime] = None) -> datetime:
    """
    Get start of week (Monday 00:00:00) for the given datetime or current week.
    
    Args:
        dt: Datetime to get start of week for, or None for current week
        
    Returns:
        Start of week datetime in local timezone
    """
    if dt is None:
        dt = now()
    elif dt.tzinfo is None:
        # Assume local timezone if naive
        dt = dt.replace(tzinfo=get_timezone_service().timezone)
    
    # Get Monday of the week
    days_since_monday = dt.weekday()
    start_of_week = dt - timedelta(days=days_since_monday)
    return get_start_of_day(start_of_week)


def get_end_of_week(dt: Optional[datetime] = None) -> datetime:
    """
    Get end of week (Sunday 23:59:59) for the given datetime or current week.
    
    Args:
        dt: Datetime to get end of week for, or None for current week
        
    Returns:
        End of week datetime in local timezone
    """
    if dt is None:
        dt = now()
    elif dt.tzinfo is None:
        # Assume local timezone if naive
        dt = dt.replace(tzinfo=get_timezone_service().timezone)
    
    # Get Sunday of the week
    days_until_sunday = 6 - dt.weekday()
    end_of_week = dt + timedelta(days=days_until_sunday)
    return get_end_of_day(end_of_week)


def is_overdue(due_date: datetime) -> bool:
    """
    Check if a due date is overdue.
    
    Args:
        due_date: Due date to check
        
    Returns:
        True if overdue, False otherwise
    """
    if due_date.tzinfo is None:
        # Assume local timezone if naive
        due_date = due_date.replace(tzinfo=get_timezone_service().timezone)
    
    return now() > due_date


def days_until_due(due_date: datetime) -> Optional[int]:
    """
    Calculate days until due date.
    
    Args:
        due_date: Due date to calculate
        
    Returns:
        Days until due (negative if overdue), or None if no due date
    """
    if due_date is None:
        return None
    
    if due_date.tzinfo is None:
        # Assume local timezone if naive
        due_date = due_date.replace(tzinfo=get_timezone_service().timezone)
    
    delta = due_date - now()
    return delta.days


def hours_elapsed_since(start_time: datetime) -> float:
    """
    Calculate hours elapsed since a start time.
    
    Args:
        start_time: Start time to calculate from
        
    Returns:
        Hours elapsed
    """
    if start_time.tzinfo is None:
        # Assume local timezone if naive
        start_time = start_time.replace(tzinfo=get_timezone_service().timezone)
    
    delta = now() - start_time
    return delta.total_seconds() / 3600


def format_datetime_for_display(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime for display in local timezone.
    
    Args:
        dt: Datetime to format
        format_str: Format string
        
    Returns:
        Formatted datetime string
    """
    return format_datetime(dt, format_str)


def format_date_for_display(dt: datetime) -> str:
    """
    Format date for display (date only).
    
    Args:
        dt: Datetime to format
        
    Returns:
        Formatted date string
    """
    return format_datetime(dt, "%Y-%m-%d")


def format_time_for_display(dt: datetime) -> str:
    """
    Format time for display (time only).
    
    Args:
        dt: Datetime to format
        
    Returns:
        Formatted time string
    """
    return format_datetime(dt, "%H:%M")


def parse_datetime_string(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse datetime string and return in local timezone.
    
    Args:
        dt_str: Datetime string to parse
        format_str: Format string
        
    Returns:
        Parsed datetime in local timezone
    """
    return get_timezone_service().parse_datetime(dt_str, format_str)


def parse_date_string(date_str: str, format_str: str = "%Y-%m-%d") -> datetime:
    """
    Parse date string and return start of day in local timezone.
    
    Args:
        date_str: Date string to parse
        format_str: Format string
        
    Returns:
        Parsed datetime (start of day) in local timezone
    """
    dt = get_timezone_service().parse_datetime(date_str, format_str)
    return get_start_of_day(dt)


def convert_to_utc_for_storage(dt: datetime) -> datetime:
    """
    Convert datetime to UTC for database storage.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        Datetime in UTC
    """
    return to_utc(dt)


def convert_from_utc_for_display(dt: datetime) -> datetime:
    """
    Convert UTC datetime to local timezone for display.
    
    Args:
        dt: UTC datetime to convert
        
    Returns:
        Datetime in local timezone
    """
    return to_local(dt)


def create_future_datetime(days: int = 1, hours: int = 0, minutes: int = 0) -> datetime:
    """
    Create a datetime in the future from now.
    
    Args:
        days: Days to add
        hours: Hours to add
        minutes: Minutes to add
        
    Returns:
        Future datetime in local timezone
    """
    return now() + timedelta(days=days, hours=hours, minutes=minutes)


def create_past_datetime(days: int = 1, hours: int = 0, minutes: int = 0) -> datetime:
    """
    Create a datetime in the past from now.
    
    Args:
        days: Days to subtract
        hours: Hours to subtract
        minutes: Minutes to subtract
        
    Returns:
        Past datetime in local timezone
    """
    return now() - timedelta(days=days, hours=hours, minutes=minutes)


def is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """
    Check if two datetimes are on the same day.
    
    Args:
        dt1: First datetime
        dt2: Second datetime
        
    Returns:
        True if same day, False otherwise
    """
    # Convert both to local timezone for comparison
    if dt1.tzinfo is None:
        dt1 = dt1.replace(tzinfo=get_timezone_service().timezone)
    if dt2.tzinfo is None:
        dt2 = dt2.replace(tzinfo=get_timezone_service().timezone)
    
    return dt1.date() == dt2.date()


def is_today(dt: datetime) -> bool:
    """
    Check if datetime is today.
    
    Args:
        dt: Datetime to check
        
    Returns:
        True if today, False otherwise
    """
    return is_same_day(dt, now())


def is_this_week(dt: datetime) -> bool:
    """
    Check if datetime is in the current week.
    
    Args:
        dt: Datetime to check
        
    Returns:
        True if this week, False otherwise
    """
    start_of_week = get_start_of_week()
    end_of_week = get_end_of_week()
    
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_timezone_service().timezone)
    
    return start_of_week <= dt <= end_of_week


def get_timezone_info() -> dict:
    """
    Get current timezone information.
    
    Returns:
        Dictionary with timezone information
    """
    return get_timezone_service().get_timezone_info()


def set_timezone(timezone_name: str) -> bool:
    """
    Set timezone manually.
    
    Args:
        timezone_name: Timezone name to set
        
    Returns:
        True if successful, False otherwise
    """
    return get_timezone_service().set_timezone(timezone_name)


def reset_timezone_to_auto() -> bool:
    """
    Reset timezone to automatic detection.
    
    Returns:
        True if successful, False otherwise
    """
    return get_timezone_service().reset_to_auto_detection() 