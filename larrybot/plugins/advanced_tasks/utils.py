"""
Shared utilities for the Advanced Tasks plugin.

This module provides common functions and utilities used across
all components of the advanced tasks plugin.
"""
from larrybot.storage.db import get_session
from larrybot.storage.task_repository import TaskRepository
from larrybot.services.task_service import TaskService


def get_task_service() ->TaskService:
    """
    Get task service instance with proper session management.
    
    Returns:
        TaskService: Configured task service instance
    """
    session = next(get_session())
    task_repository = TaskRepository(session)
    return TaskService(task_repository)


def validate_task_id(task_id_str: str) ->tuple[bool, int, str]:
    """
    Validate and convert task ID string to integer.
    
    Args:
        task_id_str: String representation of task ID
        
    Returns:
        tuple: (is_valid, task_id, error_message)
    """
    if not task_id_str.isdigit():
        return False, 0, 'Task ID must be a number'
    task_id = int(task_id_str)
    if task_id <= 0:
        return False, 0, 'Task ID must be positive'
    return True, task_id, ''


def parse_task_ids(task_ids_str: str) ->tuple[bool, list[int], str]:
    """
    Parse comma-separated task IDs string into list of integers.
    
    Args:
        task_ids_str: Comma-separated task IDs (e.g., "1,2,3")
        
    Returns:
        tuple: (is_valid, task_ids_list, error_message)
    """
    try:
        task_ids = [int(tid.strip()) for tid in task_ids_str.split(',')]
        if any(tid <= 0 for tid in task_ids):
            return False, [], 'All task IDs must be positive numbers'
        unique_ids = list(dict.fromkeys(task_ids))
        return True, unique_ids, ''
    except ValueError:
        return False, [
            ], 'Invalid task ID format. Use comma-separated numbers (e.g., 1,2,3)'





def get_priority_emoji(priority: str) ->str:
    """
    Get emoji representation for task priority.
    
    Args:
        priority: Priority level string
        
    Returns:
        str: Emoji representation
    """
    priority_emojis = {'Low': '🟢', 'Medium': '🟡', 'High': '🟠', 'Critical': '🔴'}
    return priority_emojis.get(priority, '⚪')


def get_status_emoji(status: str) ->str:
    """
    Get emoji representation for task status.
    
    Args:
        status: Status string
        
    Returns:
        str: Emoji representation
    """
    status_emojis = {'Todo': '⏳', 'In Progress': '🔄', 'Review': '👀', 'Done':
        '✅', 'Cancelled': '❌'}
    return status_emojis.get(status, '📋')


def format_duration(minutes: int) ->str:
    """
    Format duration in minutes to human-readable string.
    
    Args:
        minutes: Duration in minutes
        
    Returns:
        str: Formatted duration string
    """
    if minutes < 60:
        return f'{minutes}m'
    hours = minutes // 60
    remaining_minutes = minutes % 60
    if remaining_minutes == 0:
        return f'{hours}h'
    else:
        return f'{hours}h {remaining_minutes}m'


def truncate_text(text: str, max_length: int=50) ->str:
    """
    Truncate text to specified length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'
