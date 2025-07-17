"""
Telegram-safe utilities for LarryBot2.

This module provides utilities that are safe to use with Telegram's API,
including message formatting, keyboard building, and other Telegram-specific
functionality.
"""
import logging
import os
from typing import Optional, Dict, Any, List
from functools import wraps
import asyncio
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def configure_google_api_logging(config=None):
    """
    Configure Google API client logging to suppress deprecated warnings.
    
    Args:
        config: Optional configuration object with Google API settings
    """
    # Suppress the deprecated file cache warnings
    google_logger = logging.getLogger('googleapiclient.discovery_cache')
    google_logger.setLevel(logging.ERROR)
    
    # Configure other Google API loggers
    google_auth_logger = logging.getLogger('google.auth')
    google_auth_logger.setLevel(logging.WARNING)
    
    # If config specifies to suppress warnings, set to ERROR
    if config and getattr(config, 'GOOGLE_API_SUPPRESS_WARNINGS', True):
        google_logger.setLevel(logging.ERROR)
        google_auth_logger.setLevel(logging.ERROR)
    
    logger.debug('Google API logging configured')


def safe_edit(edit_func, *args, **kwargs):
    """
    Safely execute Telegram edit operations with error handling.
    
    Args:
        edit_func: The edit function to call
        *args: Arguments for the edit function
        **kwargs: Keyword arguments for the edit function
    
    Returns:
        The result of the edit function or None if it fails
    """
    try:
        return edit_func(*args, **kwargs)
    except Exception as e:
        logger.warning(f'Edit operation failed: {e}')
        return None


def safe_send(send_func, *args, **kwargs):
    """
    Safely execute Telegram send operations with error handling.
    
    Args:
        send_func: The send function to call
        *args: Arguments for the send function
        **kwargs: Keyword arguments for the send function
    
    Returns:
        The result of the send function or None if it fails
    """
    try:
        return send_func(*args, **kwargs)
    except Exception as e:
        logger.warning(f'Send operation failed: {e}')
        return None


def truncate_text(text: str, max_length: int = 4096, suffix: str = "...") -> str:
    """
    Truncate text to fit Telegram's message length limits.
    
    Args:
        text: The text to truncate
        max_length: Maximum length (default: 4096 for Telegram)
        suffix: Suffix to add when truncating
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    # Account for suffix length
    actual_max = max_length - len(suffix)
    return text[:actual_max] + suffix


def escape_markdown_v2(text: str) -> str:
    """
    Escape text for Telegram's MarkdownV2 format.
    
    Args:
        text: Text to escape
    
    Returns:
        Escaped text
    """
    if not text:
        return text
    
    # Characters that need escaping in MarkdownV2
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    escaped_text = text
    for char in escape_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')
    
    return escaped_text


def format_timestamp(timestamp: datetime, timezone_name: Optional[str] = None) -> str:
    """
    Format timestamp for display in Telegram messages.
    
    Args:
        timestamp: The timestamp to format
        timezone_name: Optional timezone name for conversion
    
    Returns:
        Formatted timestamp string
    """
    if not timestamp:
        return "N/A"
    
    try:
        if timezone_name:
            import pytz
            tz = pytz.timezone(timezone_name)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=pytz.UTC)
            timestamp = timestamp.astimezone(tz)
        
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.warning(f'Error formatting timestamp: {e}')
        return str(timestamp)


def create_inline_keyboard(buttons: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Create an inline keyboard markup for Telegram.
    
    Args:
        buttons: List of button rows, each containing button dictionaries
    
    Returns:
        Inline keyboard markup dictionary
    """
    return {
        'inline_keyboard': buttons
    }


def create_button(text: str, callback_data: str, url: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a button for Telegram inline keyboards.
    
    Args:
        text: Button text
        callback_data: Callback data for the button
        url: Optional URL for the button
    
    Returns:
        Button dictionary
    """
    button = {
        'text': text,
        'callback_data': callback_data
    }
    
    if url:
        button['url'] = url
    
    return button


def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry operations on error.
    
    Args:
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f'Attempt {attempt + 1} failed for {func.__name__}: {e}')
                        await asyncio.sleep(delay * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(f'All {max_retries + 1} attempts failed for {func.__name__}: {e}')
            
            raise last_exception
        
        return wrapper
    return decorator


def validate_telegram_token(token: str) -> bool:
    """
    Validate Telegram bot token format.
    
    Args:
        token: The token to validate
    
    Returns:
        True if token format is valid, False otherwise
    """
    if not token:
        return False
    
    # Basic format validation: should be numbers:letters format
    parts = token.split(':')
    if len(parts) != 2:
        return False
    
    try:
        int(parts[0])  # Bot ID should be numeric
        return len(parts[1]) > 0  # Token part should not be empty
    except ValueError:
        return False


def get_environment_info() -> Dict[str, Any]:
    """
    Get information about the current environment.
    
    Returns:
        Dictionary with environment information
    """
    return {
        'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        'platform': os.sys.platform,
        'timezone': datetime.now().astimezone().tzname(),
        'environment_variables': {
            'TELEGRAM_BOT_TOKEN': bool(os.getenv('TELEGRAM_BOT_TOKEN')),
            'ALLOWED_TELEGRAM_USER_ID': bool(os.getenv('ALLOWED_TELEGRAM_USER_ID')),
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
            'DATABASE_PATH': os.getenv('DATABASE_PATH', 'larrybot.db'),
        }
    }


# Initialize Google API logging configuration
configure_google_api_logging()
