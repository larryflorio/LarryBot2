import functools
import asyncio
from typing import Callable, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes
from larrybot.core.interfaces import CommandHandler


def command_handler(command: str, description: str='', usage: str='',
    category: str='general'):
    """
    Decorator to register a function as a command handler with metadata.
    
    Usage:
        @command_handler("/mycommand", "Description", "Usage: /mycommand <arg>", "category")
        async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # handler implementation
    """

    def decorator(func: Callable) ->Callable:

        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE
            ) ->Any:
            return await func(update, context)
        wrapper._command_metadata = {'command': command, 'description': 
            description or f'Handler for {command}', 'usage': usage or
            f'{command} [args]', 'category': category}
        return wrapper
    return decorator


def callback_handler(pattern: str, description: str='', plugin: str='general', 
                    requires_auth: bool=True, expected_parts: int=2):
    """
    Decorator to register a function as a callback handler with metadata.
    
    Usage:
        @callback_handler("my_callback", "Description", "plugin_name", True, 3)
        async def my_callback_handler(query, context: ContextTypes.DEFAULT_TYPE):
            # callback handler implementation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(query, context: ContextTypes.DEFAULT_TYPE) -> Any:
            return await func(query, context)
        wrapper._callback_metadata = {
            'pattern': pattern,
            'description': description or f'Handler for {pattern}',
            'plugin': plugin,
            'requires_auth': requires_auth,
            'expected_parts': expected_parts
        }
        return wrapper
    return decorator


def event_listener(event_name: str):
    """
    Decorator to register a function as an event listener.
    
    Usage:
        @event_listener("task_created")
        def handle_task_created(task):
            # handle the event
    """

    def decorator(func: Callable) ->Callable:

        @functools.wraps(func)
        def wrapper(data: Any) ->Any:
            return func(data)
        wrapper._event_name = event_name
        return wrapper
    return decorator


def require_args(min_args: int, max_args: Optional[int] = None):
    """
    Decorator to require a minimum number of arguments for a command.
    
    Usage:
        @require_args(1, 3)  # Require 1-3 arguments
        @require_args(1)     # Require at least 1 argument
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
            args = context.args if hasattr(context, 'args') else []
            if len(args) < min_args:
                await update.message.reply_text(
                    f'❌ This command requires at least {min_args} argument(s).'
                )
                return
            if max_args is not None and len(args) > max_args:
                await update.message.reply_text(
                    f'❌ This command accepts at most {max_args} argument(s).'
                )
                return
            return await func(update, context)
        return wrapper
    return decorator


def async_retry(max_attempts: int=3, delay: float=1.0):
    """
    Decorator to retry async functions on failure.
    
    Usage:
        @async_retry(max_attempts=3, delay=1.0)
        async def my_async_function():
            # function implementation
    """

    def decorator(func: Callable) ->Callable:

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) ->Any:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * 2 ** attempt)
            raise last_exception
        return wrapper
    return decorator


def validate_user_id(allowed_user_id: int):
    """
    Decorator to validate user authorization.
    
    Usage:
        @validate_user_id(123456789)
        async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # handler implementation
    """

    def decorator(func: Callable) ->Callable:

        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE
            ) ->Any:
            if (update.effective_user and update.effective_user.id !=
                allowed_user_id):
                await update.message.reply_text(
                    'You are not authorized to use this command.')
                return
            return await func(update, context)
        return wrapper
    return decorator


def cache_result(ttl_seconds: int=300):
    """
    Decorator to cache function results.
    
    Usage:
        @cache_result(ttl_seconds=300)
        async def expensive_operation():
            # expensive operation
    """

    def decorator(func: Callable) ->Callable:
        cache = {}

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) ->Any:
            import time
            current_time = time.time()
            cache_key = (
                f'{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}'
                )
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if current_time - timestamp < ttl_seconds:
                    return result
            result = await func(*args, **kwargs)
            cache[cache_key] = result, current_time
            return result
        return wrapper
    return decorator


def validate_callback_data(callback_data: str, expected_parts: int) -> bool:
    """
    Validate callback data format.
    
    Args:
        callback_data: The callback data string
        expected_parts: Minimum number of parts expected when split by ':'
        
    Returns:
        True if validation passes, False otherwise
    """
    parts = callback_data.split(':')
    return len(parts) >= expected_parts
