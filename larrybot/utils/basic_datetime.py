"""
Basic datetime utilities for LarryBot2

This module provides core datetime functions that have no dependencies on other
larrybot modules to avoid circular imports.
"""
from datetime import datetime, timezone
from typing import Optional


def get_utc_now() ->datetime:
    """
    Get current UTC datetime with timezone awareness.
    
    Returns:
        datetime: Current UTC datetime with timezone info
    """
    return datetime.now(timezone.utc)


def get_current_datetime() ->datetime:
    """
    Get current local datetime with timezone awareness.
    
    Returns:
        datetime: Current local datetime with timezone info
    """
    return datetime.now().replace(tzinfo=timezone.utc)


def get_local_now() ->datetime:
    """
    Get current local datetime (alias for get_current_datetime).
    
    Returns:
        datetime: Current local datetime with timezone info
    """
    return get_current_datetime()


def is_timezone_aware(dt: datetime) ->bool:
    """
    Check if a datetime object is timezone aware.
    
    Args:
        dt: datetime object to check
        
    Returns:
        bool: True if timezone aware, False otherwise
    """
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def ensure_timezone_aware(dt: datetime, default_tz: Optional[timezone]=None
    ) ->datetime:
    """
    Ensure a datetime object is timezone aware.
    
    Args:
        dt: datetime object to make timezone aware
        default_tz: timezone to use if dt is naive (defaults to UTC)
        
    Returns:
        datetime: Timezone aware datetime
    """
    if is_timezone_aware(dt):
        return dt
    if default_tz is None:
        default_tz = timezone.utc
    return dt.replace(tzinfo=default_tz)
