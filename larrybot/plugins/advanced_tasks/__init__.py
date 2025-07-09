"""
Advanced Tasks Plugin - Modular Architecture

This plugin provides comprehensive task management with advanced features including:
- Metadata-rich task creation
- Time tracking
- Subtasks and dependencies  
- Tags and comments
- Advanced filtering and search
- Analytics and insights
- Bulk operations

The plugin is organized into modular components for maintainability.
"""
from telegram.ext import ContextTypes
from telegram import Update
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from . import core
from . import time_tracking
from . import subtasks_dependencies
from . import tags_comments
from . import filtering
from . import analytics
from . import bulk_operations
from . import advanced_filtering
from . import deprecated
from . import utils
from .core import add_task_with_metadata_handler, priority_handler, due_date_handler, category_handler, status_handler
from .core import _add_task_with_metadata_handler_internal, _priority_handler_internal, _due_date_handler_internal, _category_handler_internal, _status_handler_internal
from .time_tracking import start_time_tracking_handler, stop_time_tracking_handler, time_entry_handler, time_summary_handler
from .subtasks_dependencies import subtask_handler, dependency_handler
from .subtasks_dependencies import _subtask_handler_internal, _dependency_handler_internal
from .tags_comments import tags_handler, comment_handler, comments_handler
from .tags_comments import _tags_handler_internal, _comment_handler_internal, _comments_handler_internal
from .filtering import advanced_tasks_handler, overdue_tasks_handler, today_tasks_handler, week_tasks_handler, search_tasks_handler
from .filtering import _advanced_tasks_handler_internal, _overdue_tasks_handler_internal, _today_tasks_handler_internal, _week_tasks_handler_internal, _search_tasks_handler_internal
from .analytics import analytics_handler, analytics_detailed_handler, suggest_priority_handler, productivity_report_handler
from .analytics import _analytics_handler_internal, _analytics_detailed_handler_internal, _suggest_priority_handler_internal, _productivity_report_handler_internal
from .bulk_operations import bulk_status_handler, bulk_priority_handler, bulk_assign_handler, bulk_delete_handler, bulk_operations_handler
from .bulk_operations import _bulk_status_handler_internal, _bulk_priority_handler_internal, _bulk_assign_handler_internal, _bulk_delete_handler_internal, _bulk_operations_handler_internal
from .advanced_filtering import filter_advanced_handler, tags_multi_handler, time_range_handler, priority_range_handler
from .advanced_filtering import _filter_advanced_handler_internal, _tags_multi_handler_internal, _time_range_handler_internal, _priority_range_handler_internal
from .deprecated import deprecated_search_advanced_handler
search_advanced_handler = deprecated_search_advanced_handler
analytics_advanced_handler = analytics_handler
productivity_report_handler = productivity_report_handler
_tag_handler_internal = _tags_handler_internal
_filter_priority_handler_internal = _priority_handler_internal
from .utils import get_task_service, validate_task_id
_get_task_service = get_task_service
_advanced_task_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    """
    Register all advanced task management commands with the command registry.
    
    This function coordinates registration across all modular components.
    """
    global _advanced_task_event_bus
    _advanced_task_event_bus = event_bus
    core.register(event_bus, command_registry)
    time_tracking.register(event_bus, command_registry)
    subtasks_dependencies.register(event_bus, command_registry)
    tags_comments.register(event_bus, command_registry)
    filtering.register(event_bus, command_registry)
    analytics.register(event_bus, command_registry)
    bulk_operations.register(event_bus, command_registry)
    advanced_filtering.register(event_bus, command_registry)
    deprecated.register(event_bus, command_registry)


def get_event_bus():
    """Get the global event bus instance for task events."""
    return _advanced_task_event_bus


PLUGIN_METADATA = {'name': 'advanced_tasks', 'version': '2.0.0',
    'description':
    'Advanced task management with metadata, time tracking, and analytics',
    'author': 'LarryBot2 Team', 'dependencies': ['event_bus',
    'command_registry', 'task_service'], 'enabled': True, 'modular': True,
    'components': ['core', 'time_tracking', 'subtasks_dependencies',
    'tags_comments', 'filtering', 'analytics', 'bulk_operations',
    'advanced_filtering', 'deprecated']}
