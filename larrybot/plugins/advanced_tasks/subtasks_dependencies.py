"""
Subtasks and dependencies module for the Advanced Tasks plugin.

This module handles subtask creation and task dependency management.
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
    """Register subtasks and dependencies commands."""
    global _event_bus
    _event_bus = event_bus
    
    # Subtasks and dependencies
    command_registry.register("/subtask", subtask_handler)
    command_registry.register("/depend", dependency_handler)


@command_handler("/subtask", "Create subtask", "Usage: /subtask <parent_id> <description>", "tasks")
@require_args(2, 2)
async def subtask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a subtask."""
    # Implementation extracted from original advanced_tasks.py
    # This is a simplified version - full implementation would be moved here
    await update.message.reply_text("Subtask functionality - to be implemented in modular refactor")


@command_handler("/depend", "Add task dependency", "Usage: /depend <task_id> <dependency_id>", "tasks")
@require_args(2, 2)
async def dependency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add task dependency."""
    # Implementation extracted from original advanced_tasks.py
    # This is a simplified version - full implementation would be moved here
    await update.message.reply_text("Dependency functionality - to be implemented in modular refactor") 