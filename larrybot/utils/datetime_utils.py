"""
Timezone-aware datetime utilities for LarryBot2.

This module provides timezone-aware replacements for common datetime operations
used throughout the system, ensuring consistent timezone handling.
"""
from typing import Optional, Union
from datetime import datetime, timedelta, date, timezone
from larrybot.utils.basic_datetime import get_utc_now, get_current_datetime, is_timezone_aware, ensure_timezone_aware as ensure_timezone_aware_basic


def ensure_timezone_aware(dt: datetime, assume_local: bool=True) ->datetime:
    """
    Ensure datetime is timezone-aware.
    
    Args:
        dt: Datetime to make timezone-aware
        assume_local: If True, assume naive datetimes are in local timezone
        
    Returns:
        Timezone-aware datetime
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        if assume_local:
            return dt.replace(tzinfo=timezone.utc)
        else:
            return dt.replace(tzinfo=timezone.utc)
    return dt


def ensure_utc(dt: datetime) ->datetime:
    """
    Ensure datetime is in UTC timezone.
    
    Args:
        dt: Datetime to convert to UTC
        
    Returns:
        UTC datetime
    """
    if dt is None:
        return None
    dt = ensure_timezone_aware(dt)
    if dt.tzinfo == timezone.utc:
        return dt
    return dt.astimezone(timezone.utc)


def ensure_local(dt: datetime) ->datetime:
    """
    Ensure datetime is in local timezone.
    
    Args:
        dt: Datetime to convert to local timezone
        
    Returns:
        Local timezone datetime
    """
    if dt is None:
        return None
    dt = ensure_timezone_aware(dt)
    return dt


def safe_datetime_arithmetic(dt1: datetime, dt2: datetime) ->timedelta:
    """
    Perform safe datetime arithmetic between two datetimes.
    
    Args:
        dt1: First datetime
        dt2: Second datetime
        
    Returns:
        Time difference as timedelta
    """
    if dt1 is None or dt2 is None:
        raise ValueError('Cannot perform arithmetic with None datetimes')
    dt1 = ensure_timezone_aware(dt1)
    dt2 = ensure_timezone_aware(dt2)
    dt1_utc = ensure_utc(dt1)
    dt2_utc = ensure_utc(dt2)
    return dt1_utc - dt2_utc


def get_current_datetime() ->datetime:
    """
    Get current datetime in local timezone.
    
    Returns:
        Current datetime in local timezone
    """
    from larrybot.utils.basic_datetime import get_current_datetime as basic_get_current_datetime
    return basic_get_current_datetime()


def get_current_utc_datetime() ->datetime:
    """
    Get current datetime in UTC.
    
    Returns:
        Current datetime in UTC
    """
    from larrybot.utils.basic_datetime import get_utc_now
    return get_utc_now()


def get_today_date() ->date:
    """
    Get today's date in local timezone.
    
    Returns:
        Today's date
    """
    from larrybot.utils.basic_datetime import get_current_datetime
    return get_current_datetime().date()


def get_start_of_day(dt: Optional[datetime]=None) ->datetime:
    """
    Get start of day (00:00:00) for the given datetime or today.
    
    Args:
        dt: Datetime to get start of day for, or None for today
        
    Returns:
        Start of day datetime in local timezone
    """
    if dt is None:
        from larrybot.utils.basic_datetime import get_current_datetime
        dt = get_current_datetime()
    else:
        dt = ensure_local(dt)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_end_of_day(dt: Optional[datetime]=None) ->datetime:
    """
    Get end of day (23:59:59) for the given datetime or today.
    
    Args:
        dt: Datetime to get end of day for, or None for today
        
    Returns:
        End of day datetime in local timezone
    """
    if dt is None:
        from larrybot.utils.basic_datetime import get_current_datetime
        dt = get_current_datetime()
    else:
        dt = ensure_local(dt)
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def get_start_of_week(dt: Optional[datetime]=None) ->datetime:
    """
    Get start of week (Monday 00:00:00) for the given datetime or current week.
    
    Args:
        dt: Datetime to get start of week for, or None for current week
        
    Returns:
        Start of week datetime in local timezone
    """
    if dt is None:
        from larrybot.utils.basic_datetime import get_current_datetime
        dt = get_current_datetime()
    else:
        dt = ensure_local(dt)
    days_since_monday = dt.weekday()
    start_of_week = dt - timedelta(days=days_since_monday)
    return get_start_of_day(start_of_week)


def get_end_of_week(dt: Optional[datetime]=None) ->datetime:
    """
    Get end of week (Sunday 23:59:59) for the given datetime or current week.
    
    Args:
        dt: Datetime to get end of week for, or None for current week
        
    Returns:
        End of week datetime in local timezone
    """
    if dt is None:
        from larrybot.utils.basic_datetime import get_current_datetime
        dt = get_current_datetime()
    else:
        dt = ensure_local(dt)
    days_until_sunday = 6 - dt.weekday()
    end_of_week = dt + timedelta(days=days_until_sunday)
    return get_end_of_day(end_of_week)


def is_overdue(due_date: datetime) ->bool:
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
    
    # Use DateTimeService for consistent date-based comparison
    from larrybot.services.datetime_service import DateTimeService
    return DateTimeService.is_overdue(due_date)


def days_until_due(due_date: datetime) ->Optional[int]:
    """
    Calculate days until due date.
    
    Args:
        due_date: Due date to calculate
        
    Returns:
        Days until due (negative if overdue), or None if no due date
    """
    if due_date is None:
        return None
    due_date = ensure_local(due_date)
    from larrybot.utils.basic_datetime import get_current_datetime
    delta = due_date - get_current_datetime()
    return delta.days


def hours_elapsed_since(start_time: datetime) ->float:
    """
    Calculate hours elapsed since a start time.
    
    Args:
        start_time: Start time to calculate from
        
    Returns:
        Hours elapsed
    """
    if start_time is None:
        return 0.0
    from larrybot.utils.basic_datetime import get_current_datetime
    delta = safe_datetime_arithmetic(get_current_datetime(), start_time)
    return delta.total_seconds() / 3600


def format_datetime(dt: datetime, format_str: str='%Y-%m-%d %H:%M:%S') ->str:
    """
    Format datetime with the given format string.
    
    Args:
        dt: Datetime to format
        format_str: Format string
        
    Returns:
        Formatted datetime string
    """
    if dt is None:
        return 'N/A'
    return dt.strftime(format_str)


def format_datetime_for_display(dt: datetime, format_str: str=
    '%Y-%m-%d %H:%M:%S') ->str:
    """
    Format datetime for display in local timezone.
    
    Args:
        dt: Datetime to format
        format_str: Format string
        
    Returns:
        Formatted datetime string
    """
    if dt is None:
        return 'N/A'
    dt = ensure_local(dt)
    return format_datetime(dt, format_str)


def format_date_for_display(dt: datetime) ->str:
    """
    Format date for display (date only).
    
    Args:
        dt: Datetime to format
        
    Returns:
        Formatted date string
    """
    if dt is None:
        return 'N/A'
    dt = ensure_local(dt)
    return dt.strftime('%Y-%m-%d')


def format_time_for_display(dt: datetime) ->str:
    """
    Format time for display (time only).
    
    Args:
        dt: Datetime to format
        
    Returns:
        Formatted time string
    """
    if dt is None:
        return 'N/A'
    dt = ensure_local(dt)
    return dt.strftime('%H:%M:%S')


def parse_datetime_string(dt_str: str, format_str: str='%Y-%m-%d %H:%M:%S'
    ) ->datetime:
    """
    Parse datetime string and return timezone-aware datetime.
    
    Args:
        dt_str: Datetime string to parse
        format_str: Format string
        
    Returns:
        Timezone-aware datetime in local timezone
    """
    dt = datetime.strptime(dt_str, format_str)
    return ensure_timezone_aware(dt, assume_local=True)


def parse_date_string(date_str: str, format_str: str='%Y-%m-%d') ->datetime:
    """
    Parse date string and return timezone-aware datetime at start of day.
    
    Args:
        date_str: Date string to parse
        format_str: Format string
        
    Returns:
        Timezone-aware datetime at start of day in local timezone
    """
    dt = datetime.strptime(date_str, format_str)
    dt = ensure_timezone_aware(dt, assume_local=True)
    return get_start_of_day(dt)


def convert_to_utc_for_storage(dt: datetime) ->datetime:
    """
    Convert datetime to UTC for database storage.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        UTC datetime for storage
    """
    if dt is None:
        return None
    return ensure_utc(dt)


def convert_from_utc_for_display(dt: datetime) ->datetime:
    """
    Convert UTC datetime from database to local timezone for display.
    
    Args:
        dt: UTC datetime from database
        
    Returns:
        Local timezone datetime for display
    """
    if dt is None:
        return None
    return ensure_local(dt)


def create_future_datetime(days: int=1, hours: int=0, minutes: int=0
    ) ->datetime:
    """
    Create a future datetime relative to now.
    
    Args:
        days: Days to add
        hours: Hours to add
        minutes: Minutes to add
        
    Returns:
        Future datetime in local timezone
    """
    from larrybot.utils.basic_datetime import get_current_datetime
    return get_current_datetime() + timedelta(days=days, hours=hours,
        minutes=minutes)


def create_past_datetime(days: int=1, hours: int=0, minutes: int=0) ->datetime:
    """
    Create a past datetime relative to now.
    
    Args:
        days: Days to subtract
        hours: Hours to subtract
        minutes: Minutes to subtract
        
    Returns:
        Past datetime in local timezone
    """
    from larrybot.utils.basic_datetime import get_current_datetime
    return get_current_datetime() - timedelta(days=days, hours=hours,
        minutes=minutes)


def is_same_day(dt1: datetime, dt2: datetime) ->bool:
    """
    Check if two datetimes are on the same day.
    
    Args:
        dt1: First datetime
        dt2: Second datetime
        
    Returns:
        True if same day, False otherwise
    """
    if dt1 is None or dt2 is None:
        return False
    dt1 = ensure_local(dt1)
    dt2 = ensure_local(dt2)
    return dt1.date() == dt2.date()


def is_today(dt: datetime) ->bool:
    """
    Check if datetime is today.
    
    Args:
        dt: Datetime to check
        
    Returns:
        True if today, False otherwise
    """
    if dt is None:
        return False
    dt = ensure_local(dt)
    return dt.date() == now().date()


def is_this_week(dt: datetime) ->bool:
    """
    Check if datetime is in the current week.
    
    Args:
        dt: Datetime to check
        
    Returns:
        True if this week, False otherwise
    """
    if dt is None:
        return False
    dt = ensure_local(dt)
    start_of_week = get_start_of_week()
    end_of_week = get_end_of_week()
    return start_of_week <= dt <= end_of_week


def get_timezone_info() ->dict:
    """
    Get current timezone information.
    
    Returns:
        Dictionary with timezone information
    """
    tz_service = get_timezone_service()
    return {'timezone_name': tz_service.timezone_name, 'is_auto_detected': 
        tz_service.detected_timezone is not None, 'current_offset': now().
        strftime('%z'), 'current_time': format_datetime_for_display(now())}


def set_timezone(timezone_name: str) ->bool:
    """
    Set timezone manually.
    
    Args:
        timezone_name: Timezone name to set
        
    Returns:
        True if successful, False otherwise
    """
    tz_service = get_timezone_service()
    return tz_service.set_timezone(timezone_name)


def reset_timezone_to_auto() ->bool:
    """
    Reset timezone to automatic detection.
    
    Returns:
        True if successful, False otherwise
    """
    tz_service = get_timezone_service()
    return tz_service.reset_to_auto_detection()
