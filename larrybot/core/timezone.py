"""
Timezone management for LarryBot2.

This module provides centralized timezone handling with automatic detection,
manual override capability, and robust fallback handling for all datetime operations.
"""

import os
import logging
from typing import Optional, Union, Tuple, Any
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo, available_timezones
    ZONEINFO_AVAILABLE = True
except ImportError:
    ZONEINFO_AVAILABLE = False
    ZoneInfo = None
    available_timezones = None
import pytz

logger = logging.getLogger(__name__)


class TimeZoneService:
    """
    Centralized timezone management service.
    
    Provides automatic timezone detection, manual override capability,
    and robust fallback handling for all datetime operations.
    """
    
    def __init__(self, timezone_name: Optional[str] = None):
        """
        Initialize the timezone service.
        
        Args:
            timezone_name: Optional timezone name to override automatic detection
        """
        self._timezone_name = timezone_name
        self._timezone = None
        self._detected_timezone = None
        self._initialize_timezone()
    
    def _initialize_timezone(self) -> None:
        """Initialize timezone with automatic detection and fallback handling."""
        try:
            # Use manual override if provided
            if self._timezone_name:
                self._timezone = self._get_timezone_by_name(self._timezone_name)
                if self._timezone:
                    logger.info(f"Using manually configured timezone: {self._timezone_name}")
                    return
                else:
                    logger.warning(f"Invalid timezone name '{self._timezone_name}', falling back to automatic detection")
            
            # Automatic timezone detection
            self._detected_timezone = self._detect_system_timezone()
            self._timezone = self._detected_timezone
            
            if self._timezone:
                logger.info(f"Using automatically detected timezone: {self._timezone}")
            else:
                logger.warning("Timezone detection failed, falling back to UTC")
                self._timezone = timezone.utc
                
        except Exception as e:
            logger.error(f"Error initializing timezone service: {e}")
            self._timezone = timezone.utc
    
    def _detect_system_timezone(self) -> Optional[Union[ZoneInfo, Any]]:
        """
        Detect system timezone using multiple methods.
        
        Returns:
            Detected timezone or None if detection fails
        """
        # Method 1: Check TZ environment variable
        tz_env = os.environ.get('TZ')
        if tz_env:
            try:
                if ZONEINFO_AVAILABLE:
                    return ZoneInfo(tz_env)
                else:
                    return pytz.timezone(tz_env)
            except Exception:
                logger.debug(f"Invalid TZ environment variable: {tz_env}")
        
        # Method 2: Check system timezone files (Unix/Linux)
        try:
            # Read /etc/timezone (Debian/Ubuntu)
            if os.path.exists('/etc/timezone'):
                with open('/etc/timezone', 'r') as f:
                    tz_name = f.read().strip()
                    if tz_name:
                        if ZONEINFO_AVAILABLE:
                            return ZoneInfo(tz_name)
                        else:
                            return pytz.timezone(tz_name)
        except Exception:
            pass
        
        try:
            # Read /etc/localtime symlink (most Unix systems)
            if os.path.exists('/etc/localtime'):
                real_path = os.path.realpath('/etc/localtime')
                # Extract timezone from path like /usr/share/zoneinfo/America/New_York
                if '/zoneinfo/' in real_path:
                    tz_name = real_path.split('/zoneinfo/')[-1]
                    if ZONEINFO_AVAILABLE:
                        return ZoneInfo(tz_name)
                    else:
                        return pytz.timezone(tz_name)
        except Exception:
            pass
        
        # Method 3: Use datetime.now() to get local timezone
        try:
            local_now = datetime.now()
            utc_now = datetime.now(timezone.utc)
            offset = local_now.replace(tzinfo=None) - utc_now.replace(tzinfo=None)
            
            # Find timezone with matching offset
            if ZONEINFO_AVAILABLE and available_timezones:
                for tz_name in available_timezones():
                    try:
                        tz = ZoneInfo(tz_name)
                        tz_now = datetime.now(tz)
                        tz_offset = tz_now.replace(tzinfo=None) - utc_now.replace(tzinfo=None)
                        
                        if abs((tz_offset - offset).total_seconds()) < 60:  # Within 1 minute
                            return tz
                    except Exception:
                        continue
            else:
                # Fallback to pytz for timezone detection
                for tz_name in pytz.all_timezones:
                    try:
                        tz = pytz.timezone(tz_name)
                        tz_now = datetime.now(tz)
                        tz_offset = tz_now.replace(tzinfo=None) - utc_now.replace(tzinfo=None)
                        
                        if abs((tz_offset - offset).total_seconds()) < 60:  # Within 1 minute
                            return tz
                    except Exception:
                        continue
        except Exception:
            pass
        
        return None
    
    def _get_timezone_by_name(self, timezone_name: str) -> Optional[Union[ZoneInfo, Any]]:
        """
        Get timezone by name with validation.
        
        Args:
            timezone_name: Timezone name to validate and get
            
        Returns:
            ZoneInfo or pytz timezone object, or None if invalid
        """
        try:
            # First try zoneinfo if available
            if ZONEINFO_AVAILABLE:
                return ZoneInfo(timezone_name)
            else:
                # Fallback to pytz
                return pytz.timezone(timezone_name)
        except Exception:
            try:
                # Fallback to pytz for legacy timezone names
                return pytz.timezone(timezone_name)
            except Exception:
                return None
    
    @property
    def timezone(self) -> Union[ZoneInfo, Any]:
        """Get the current timezone."""
        return self._timezone
    
    @property
    def timezone_name(self) -> str:
        """Get the current timezone name."""
        return str(self._timezone)
    
    @property
    def pytz_timezone(self) -> Any:
        """Get the current timezone as a pytz timezone object for compatibility."""
        if isinstance(self._timezone, pytz.tzinfo):
            return self._timezone
        else:
            # Convert ZoneInfo to pytz timezone
            return pytz.timezone(str(self._timezone))
    
    @property
    def detected_timezone(self) -> Optional[ZoneInfo]:
        """Get the automatically detected timezone."""
        return self._detected_timezone
    
    def set_timezone(self, timezone_name: str) -> bool:
        """
        Set timezone manually.
        
        Args:
            timezone_name: Timezone name to set
            
        Returns:
            True if successful, False otherwise
        """
        new_timezone = self._get_timezone_by_name(timezone_name)
        if new_timezone:
            self._timezone = new_timezone
            self._timezone_name = timezone_name
            logger.info(f"Timezone manually set to: {timezone_name}")
            return True
        else:
            logger.error(f"Invalid timezone name: {timezone_name}")
            return False
    
    def reset_to_auto_detection(self) -> bool:
        """
        Reset to automatic timezone detection.
        
        Returns:
            True if successful, False otherwise
        """
        if self._detected_timezone:
            self._timezone = self._detected_timezone
            self._timezone_name = None
            logger.info("Reset to automatically detected timezone")
            return True
        else:
            logger.warning("No detected timezone available, keeping current timezone")
            return False
    
    def now(self) -> datetime:
        """
        Get current datetime in the configured timezone.
        
        Returns:
            Current datetime with timezone info
        """
        return datetime.now(self._timezone)
    
    def utc_now(self) -> datetime:
        """
        Get current datetime in UTC.
        
        Returns:
            Current datetime in UTC
        """
        return datetime.now(timezone.utc)
    
    def to_local(self, utc_dt: datetime) -> datetime:
        """
        Convert UTC datetime to local timezone.
        
        Args:
            utc_dt: UTC datetime (naive or timezone-aware)
            
        Returns:
            Datetime in local timezone
        """
        if utc_dt.tzinfo is None:
            # Assume UTC if naive
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        elif utc_dt.tzinfo != timezone.utc:
            # Convert to UTC first
            utc_dt = utc_dt.astimezone(timezone.utc)
        
        return utc_dt.astimezone(self._timezone)
    
    def to_utc(self, local_dt: datetime) -> datetime:
        """
        Convert local datetime to UTC.
        
        Args:
            local_dt: Local datetime (naive or timezone-aware)
            
        Returns:
            Datetime in UTC
        """
        if local_dt.tzinfo is None:
            # Assume local timezone if naive
            local_dt = local_dt.replace(tzinfo=self._timezone)
        elif local_dt.tzinfo != self._timezone:
            # Convert to local timezone first
            local_dt = local_dt.astimezone(self._timezone)
        
        return local_dt.astimezone(timezone.utc)
    
    def format_datetime(self, dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Format datetime in local timezone.
        
        Args:
            dt: Datetime to format (UTC or local)
            format_str: Format string
            
        Returns:
            Formatted datetime string
        """
        local_dt = self.to_local(dt) if dt.tzinfo == timezone.utc else dt
        return local_dt.strftime(format_str)
    
    def parse_datetime(self, dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
        """
        Parse datetime string and return in local timezone.
        
        Args:
            dt_str: Datetime string to parse
            format_str: Format string
            
        Returns:
            Parsed datetime in local timezone
        """
        naive_dt = datetime.strptime(dt_str, format_str)
        return naive_dt.replace(tzinfo=self._timezone)
    
    def get_timezone_info(self) -> dict:
        """
        Get comprehensive timezone information.
        
        Returns:
            Dictionary with timezone information
        """
        now = self.now()
        utc_now = self.utc_now()
        
        return {
            "timezone_name": self.timezone_name,
            "is_auto_detected": self._detected_timezone == self._timezone,
            "detected_timezone": str(self._detected_timezone) if self._detected_timezone else None,
            "manual_override": self._timezone_name,
            "current_local_time": now.isoformat(),
            "current_utc_time": utc_now.isoformat(),
            "utc_offset": now.utcoffset().total_seconds() / 3600,  # Hours
            "is_dst": now.dst() != timedelta(0),
            "dst_offset": now.dst().total_seconds() / 3600 if now.dst() else 0
        }
    
    def list_available_timezones(self, search_term: Optional[str] = None) -> list:
        """
        List available timezones, optionally filtered by search term.
        
        Args:
            search_term: Optional search term to filter timezones
            
        Returns:
            List of available timezone names
        """
        if ZONEINFO_AVAILABLE and available_timezones:
            timezones = list(available_timezones())
        else:
            timezones = list(pytz.all_timezones)
        
        if search_term:
            search_term = search_term.lower()
            timezones = [tz for tz in timezones if search_term in tz.lower()]
        
        return sorted(timezones)


# Global timezone service instance
_timezone_service: Optional[TimeZoneService] = None


def get_timezone_service() -> TimeZoneService:
    """
    Get the global timezone service instance.
    
    Returns:
        TimeZoneService instance
    """
    global _timezone_service
    if _timezone_service is None:
        _timezone_service = TimeZoneService()
    return _timezone_service


def initialize_timezone_service(timezone_name: Optional[str] = None) -> TimeZoneService:
    """
    Initialize the global timezone service.
    
    Args:
        timezone_name: Optional timezone name to override automatic detection
        
    Returns:
        Initialized TimeZoneService instance
    """
    global _timezone_service
    _timezone_service = TimeZoneService(timezone_name)
    return _timezone_service


# Convenience functions for common operations
def now() -> datetime:
    """Get current datetime in local timezone."""
    return get_timezone_service().now()


def utc_now() -> datetime:
    """Get current datetime in UTC."""
    return get_timezone_service().utc_now()


def to_local(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to local timezone."""
    return get_timezone_service().to_local(utc_dt)


def to_utc(local_dt: datetime) -> datetime:
    """Convert local datetime to UTC."""
    return get_timezone_service().to_utc(local_dt)


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime in local timezone."""
    return get_timezone_service().format_datetime(dt, format_str)


def parse_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """Parse datetime string and return in local timezone."""
    return get_timezone_service().parse_datetime(dt_str, format_str) 