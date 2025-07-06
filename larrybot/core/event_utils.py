"""
Event utilities for LarryBot2.

This module provides utilities for standardizing event data formats
and handling event data conversion between different formats.
"""
from typing import Dict, Any, Union, Optional
from datetime import datetime
import json


class EventDataFormatter:
    """Utility class for formatting event data consistently."""

    @staticmethod
    def format_task_data(task: Union[Dict[str, Any], Any]) ->Dict[str, Any]:
        """
        Format task data to a consistent dictionary format.
        
        Args:
            task: Task object or dictionary
            
        Returns:
            Standardized task dictionary
        """
        if isinstance(task, dict):
            return task
        try:
            return {'id': getattr(task, 'id', None), 'description': getattr
                (task, 'description', ''), 'done': getattr(task, 'done', 
                False), 'priority': getattr(task, 'priority', 'Medium'),
                'due_date': task.due_date.isoformat() if hasattr(task,
                'due_date') and task.due_date else None, 'category':
                getattr(task, 'category', None), 'status': getattr(task,
                'status', 'Todo'), 'estimated_hours': float(task.
                estimated_hours) if hasattr(task, 'estimated_hours') and
                task.estimated_hours else None, 'actual_hours': float(task.
                actual_hours) if hasattr(task, 'actual_hours') and task.
                actual_hours else None, 'started_at': task.started_at.
                isoformat() if hasattr(task, 'started_at') and task.
                started_at else None, 'parent_id': getattr(task,
                'parent_id', None), 'tags': json.loads(task.tags) if 
                hasattr(task, 'tags') and task.tags else [], 'client_id':
                getattr(task, 'client_id', None), 'created_at': task.
                created_at.isoformat() if hasattr(task, 'created_at') else
                None, 'updated_at': task.updated_at.isoformat() if hasattr(
                task, 'updated_at') else None}
        except Exception as e:
            return {'id': getattr(task, 'id', None), 'description': str(
                getattr(task, 'description', 'Unknown Task')), 'done':
                getattr(task, 'done', False), 'priority': getattr(task,
                'priority', 'Medium'), 'due_date': None, 'category': None,
                'status': 'Todo', 'error': f'Data conversion error: {str(e)}'}

    @staticmethod
    def format_client_data(client: Union[Dict[str, Any], Any]) ->Dict[str, Any
        ]:
        """
        Format client data to a consistent dictionary format.
        
        Args:
            client: Client object or dictionary
            
        Returns:
            Standardized client dictionary
        """
        if isinstance(client, dict):
            return client
        try:
            return {'id': getattr(client, 'id', None), 'name': getattr(
                client, 'name', ''), 'created_at': client.created_at.
                isoformat() if hasattr(client, 'created_at') else None,
                'updated_at': client.updated_at.isoformat() if hasattr(
                client, 'updated_at') else None}
        except Exception as e:
            return {'id': getattr(client, 'id', None), 'name': str(getattr(
                client, 'name', 'Unknown Client')), 'error':
                f'Data conversion error: {str(e)}'}


def safe_event_handler(handler_func):
    """
    Decorator to make event handlers safe and handle different data formats.
    
    Args:
        handler_func: The original event handler function
        
    Returns:
        Wrapped handler function that safely handles different data formats
    """

    def wrapper(event_data, *args, **kwargs):
        try:
            return handler_func(event_data, *args, **kwargs)
        except AttributeError as e:
            if 'description' in str(e) or 'id' in str(e):
                if isinstance(event_data, dict):


                    class DictAsObject:

                        def __init__(self, data):
                            for key, value in data.items():
                                setattr(self, key, value)
                    converted_data = DictAsObject(event_data)
                    return handler_func(converted_data, *args, **kwargs)
            raise
        except Exception as e:
            print(f'Event handler error in {handler_func.__name__}: {str(e)}')
            return None
    return wrapper


def emit_task_event(event_bus, event_name: str, task_data: Union[Dict[str,
    Any], Any]) ->None:
    """
    Safely emit a task-related event with standardized data format.
    
    Args:
        event_bus: The event bus instance
        event_name: Name of the event to emit
        task_data: Task data (object or dictionary)
    """
    if event_bus:
        formatted_data = EventDataFormatter.format_task_data(task_data)
        event_bus.emit(event_name, formatted_data)


def emit_client_event(event_bus, event_name: str, client_data: Union[Dict[
    str, Any], Any]) ->None:
    """
    Safely emit a client-related event with standardized data format.
    
    Args:
        event_bus: The event bus instance
        event_name: Name of the event to emit
        client_data: Client data (object or dictionary)
    """
    if event_bus:
        formatted_data = EventDataFormatter.format_client_data(client_data)
        event_bus.emit(event_name, formatted_data)
