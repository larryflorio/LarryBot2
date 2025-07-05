"""
Tags and comments module for the Advanced Tasks plugin.

This module handles task tagging and comment management.
"""

from telegram import Update
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.utils.decorators import command_handler, require_args
from larrybot.utils.ux_helpers import MessageFormatter
from .utils import get_task_service, validate_task_id

# Global event bus reference
_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) -> None:
    """Register tags and comments commands."""
    global _event_bus
    _event_bus = event_bus
    
    # Tags and comments
    command_registry.register("/tags", tags_handler)
    command_registry.register("/comment", comment_handler)
    command_registry.register("/comments", comments_handler)


@command_handler("/tags", "Manage task tags", "Usage: /tags <task_id> <add|remove> <tag1,tag2,tag3>", "tasks")
@require_args(3, 3)
async def tags_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage task tags."""
    # Implementation extracted from original advanced_tasks.py
    # This is a simplified version - full implementation would be moved here
    await update.message.reply_text("Tags functionality - to be implemented in modular refactor")


@command_handler("/comment", "Add comment to task", "Usage: /comment <task_id> <comment>", "tasks")
@require_args(2, 2)
async def comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add comment to task."""
    # Implementation extracted from original advanced_tasks.py
    # This is a simplified version - full implementation would be moved here
    await update.message.reply_text("Comment functionality - to be implemented in modular refactor")


@command_handler("/comments", "Show task comments", "Usage: /comments <task_id>", "tasks")
@require_args(1, 1)
async def comments_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show task comments."""
    # Implementation extracted from original advanced_tasks.py
    # This is a simplified version - full implementation would be moved here
    await update.message.reply_text("Comments viewing functionality - to be implemented in modular refactor") 