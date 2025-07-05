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

# Import modular components
from . import core
from . import time_tracking
from . import subtasks_dependencies
from . import tags_comments
from . import filtering
from . import analytics
from . import bulk_operations
from . import advanced_filtering
from . import deprecated

# Global reference to event bus for task events
_advanced_task_event_bus = None

def register(event_bus: EventBus, command_registry: CommandRegistry) -> None:
    """
    Register all advanced task management commands with the command registry.
    
    This function coordinates registration across all modular components.
    """
    global _advanced_task_event_bus
    _advanced_task_event_bus = event_bus
    
    # Register commands from each module
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

# Plugin metadata
PLUGIN_METADATA = {
    "name": "advanced_tasks",
    "version": "2.0.0",
    "description": "Advanced task management with metadata, time tracking, and analytics",
    "author": "LarryBot2 Team",
    "dependencies": ["event_bus", "command_registry", "task_service"],
    "enabled": True,
    "modular": True,
    "components": [
        "core",
        "time_tracking", 
        "subtasks_dependencies",
        "tags_comments",
        "filtering",
        "analytics",
        "bulk_operations",
        "advanced_filtering",
        "deprecated"
    ]
} 