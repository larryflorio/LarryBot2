"""
Tests for the timezone system.
"""

import pytest
from datetime import datetime, timezone
from larrybot.core.timezone import TimeZoneService, get_timezone_service


def test_timezone_service_initialization():
    """Test basic timezone service initialization."""
    service = TimeZoneService("America/New_York")
    assert service.timezone_name == "America/New_York"


def test_timezone_service_auto_detection():
    """Test automatic timezone detection."""
    service = TimeZoneService()
    assert service.timezone is not None


def test_timezone_conversion():
    """Test timezone conversion."""
    service = TimeZoneService("America/New_York")
    
    # Test UTC to local conversion
    utc_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    local_dt = service.to_local(utc_dt)
    assert local_dt.tzinfo == service.timezone


def test_get_timezone_service():
    """Test getting the global timezone service."""
    service1 = get_timezone_service()
    service2 = get_timezone_service()
    assert service1 is service2 