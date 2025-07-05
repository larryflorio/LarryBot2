"""
Deprecated commands module for the Advanced Tasks plugin.

This module handles backward compatibility by providing deprecation notices
and redirecting users to the new consolidated commands.
"""

from telegram import Update
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.utils.ux_helpers import MessageFormatter

# Import handlers from other modules for redirection
from .core import add_task_with_metadata_handler
from .time_tracking import start_time_tracking_handler, stop_time_tracking_handler

# Global event bus reference
_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) -> None:
    """Register deprecated command handlers."""
    global _event_bus
    _event_bus = event_bus
    
    # DEPRECATED COMMANDS - Redirect to consolidated versions
    # NOTE: /addtask is NOT deprecated - it's the primary command registered in core
    command_registry.register("/add", deprecated_add_handler)  # /add → /addtask
    command_registry.register("/tasks", deprecated_tasks_handler)
    command_registry.register("/search_advanced", deprecated_search_advanced_handler)
    command_registry.register("/analytics_detailed", deprecated_analytics_detailed_handler)
    command_registry.register("/analytics_advanced", deprecated_analytics_advanced_handler)
    command_registry.register("/start", deprecated_start_handler)
    command_registry.register("/stop", deprecated_stop_handler)


async def deprecated_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /add to enhanced /addtask command."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Consolidated",
            {
                "Old Command": "/add",
                "New Command": "/addtask",
                "Migration": "The /add command has been merged into /addtask",
                "Usage": "/addtask <description> [priority] [due_date] [category]",
                "Benefits": "Enhanced functionality with metadata support"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to the enhanced /addtask handler
    await add_task_with_metadata_handler(update, context)


async def deprecated_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /tasks to enhanced /list command."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Consolidated",
            {
                "Old Command": "/tasks",
                "New Command": "/list",
                "Migration": "The /tasks command has been merged into /list",
                "Usage": "/list [status] [priority] [category]",
                "Benefits": "Simplified interface with same filtering power"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to the enhanced /list handler
    from larrybot.plugins.tasks import list_tasks_handler
    await list_tasks_handler(update, context)


async def deprecated_search_advanced_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /search_advanced to enhanced /search --advanced command."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Consolidated",
            {
                "Old Command": "/search_advanced",
                "New Command": "/search --advanced",
                "Migration": "Advanced search is now a flag in the main search command",
                "Usage": "/search <query> --advanced [--case-sensitive]",
                "Benefits": "Unified search interface with mode selection"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to the enhanced /search handler with advanced flag
    if context.args:
        # Convert to advanced search format
        new_args = [context.args[0], "--advanced"]
        if len(context.args) > 1:
            new_args.extend(context.args[1:])
        context.args = new_args
        
        from .filtering import search_tasks_handler
        await search_tasks_handler(update, context)


async def deprecated_analytics_detailed_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /analytics_detailed to enhanced /analytics detailed command."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Consolidated",
            {
                "Old Command": "/analytics_detailed",
                "New Command": "/analytics detailed",
                "Migration": "Detailed analytics is now a mode in the main analytics command",
                "Usage": "/analytics detailed [days]",
                "Benefits": "Unified analytics interface with complexity levels"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to the enhanced /analytics handler with detailed mode
    new_args = ["detailed"]
    if context.args:
        new_args.extend(context.args)
    context.args = new_args
    
    from .analytics import analytics_handler
    await analytics_handler(update, context)


async def deprecated_analytics_advanced_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /analytics_advanced to enhanced /analytics advanced command."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Consolidated",
            {
                "Old Command": "/analytics_advanced",
                "New Command": "/analytics advanced",
                "Migration": "Advanced analytics is now a mode in the main analytics command",
                "Usage": "/analytics advanced [days]",
                "Benefits": "Unified analytics interface with complexity levels"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to the enhanced /analytics handler with advanced mode
    new_args = ["advanced"]
    if context.args:
        new_args.extend(context.args)
    context.args = new_args
    
    from .analytics import analytics_handler
    await analytics_handler(update, context)


async def deprecated_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /start (time tracking) to /time_start command."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Renamed",
            {
                "Old Command": "/start",
                "New Command": "/time_start",
                "Migration": "Time tracking commands have been clarified",
                "Usage": "/time_start <task_id>",
                "Benefits": "Clearer command naming to avoid confusion with bot /start"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to the /time_start handler
    await start_time_tracking_handler(update, context)


async def deprecated_stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /stop (time tracking) to /time_stop command."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Renamed",
            {
                "Old Command": "/stop",
                "New Command": "/time_stop",
                "Migration": "Time tracking commands have been clarified",
                "Usage": "/time_stop <task_id>",
                "Benefits": "Clearer command naming and consistent interface"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to the /time_stop handler
    await stop_time_tracking_handler(update, context) 