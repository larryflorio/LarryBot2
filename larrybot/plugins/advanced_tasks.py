from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.storage.db import get_session
from larrybot.storage.task_repository import TaskRepository
from larrybot.services.task_service import TaskService
from larrybot.utils.decorators import command_handler, require_args
from larrybot.core.event_utils import emit_task_event
from typing import Optional, List
from datetime import datetime, timedelta
import json
import re
from larrybot.utils.ux_helpers import KeyboardBuilder, MessageFormatter, ChartBuilder, AnalyticsFormatter
from larrybot.utils.datetime_utils import get_current_datetime, get_today_date, get_start_of_day, get_end_of_day, get_start_of_week, get_end_of_week, parse_date_string
from larrybot.utils.enhanced_ux_helpers import escape_markdown_v2

# Global reference to event bus for task events
_advanced_task_event_bus = None

def register(event_bus: EventBus, command_registry: CommandRegistry) -> None:
    """
    Register advanced task management commands with the command registry.
    """
    global _advanced_task_event_bus
    _advanced_task_event_bus = event_bus
    
    # Enhanced task creation and management
    command_registry.register("/addtask", add_task_with_metadata_handler)
    command_registry.register("/priority", priority_handler)
    command_registry.register("/due", due_date_handler)
    command_registry.register("/category", category_handler)
    command_registry.register("/status", status_handler)
    
    # Time tracking
    command_registry.register("/time_start", start_time_tracking_handler)
    command_registry.register("/time_stop", stop_time_tracking_handler)
    
    # Subtasks and dependencies
    command_registry.register("/subtask", subtask_handler)
    command_registry.register("/depend", dependency_handler)
    
    # Tags and comments
    command_registry.register("/tags", tags_handler)
    command_registry.register("/comment", comment_handler)
    command_registry.register("/comments", comments_handler)
    
    # Advanced filtering and search
    command_registry.register("/tasks", advanced_tasks_handler)
    command_registry.register("/overdue", overdue_tasks_handler)
    command_registry.register("/today", today_tasks_handler)
    command_registry.register("/week", week_tasks_handler)
    command_registry.register("/search", search_tasks_handler)
    
    # Analytics and insights
    command_registry.register("/analytics", analytics_handler)
    command_registry.register("/analytics_detailed", analytics_detailed_handler)
    command_registry.register("/suggest", suggest_priority_handler)
    
    # Bulk operations
    command_registry.register("/bulk_status", bulk_status_handler)
    command_registry.register("/bulk_priority", bulk_priority_handler)
    command_registry.register("/bulk_assign", bulk_assign_handler)
    command_registry.register("/bulk_delete", bulk_delete_handler)
    command_registry.register("/bulk_operations", bulk_operations_handler)
    
    # Manual time entry
    command_registry.register("/time_entry", time_entry_handler)
    command_registry.register("/time_summary", time_summary_handler)
    
    # Enhanced filtering and search
    command_registry.register("/search_advanced", search_advanced_handler)
    command_registry.register("/filter_advanced", filter_advanced_handler)
    command_registry.register("/tags_multi", tags_multi_handler)
    command_registry.register("/time_range", time_range_handler)
    command_registry.register("/priority_range", priority_range_handler)
    
    # Enhanced analytics and reporting
    command_registry.register("/analytics_advanced", analytics_advanced_handler)
    command_registry.register("/productivity_report", productivity_report_handler)
    
    # DEPRECATED COMMANDS - Redirect to consolidated versions
    command_registry.register("/addtask", deprecated_addtask_handler)
    command_registry.register("/tasks", deprecated_tasks_handler)
    command_registry.register("/search_advanced", deprecated_search_advanced_handler)
    command_registry.register("/analytics_detailed", deprecated_analytics_detailed_handler)
    command_registry.register("/analytics_advanced", deprecated_analytics_advanced_handler)
    command_registry.register("/start", deprecated_start_handler)
    command_registry.register("/stop", deprecated_stop_handler)

def _get_task_service() -> TaskService:
    """Get task service instance."""
    session = next(get_session())
    task_repository = TaskRepository(session)
    return TaskService(task_repository)

@command_handler("/addtask", "Create task with advanced metadata", "Usage: /addtask <description> [priority] [due_date] [category]", "tasks")
@require_args(1, 4)
async def add_task_with_metadata_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a task with advanced metadata."""
    args = context.args
    description = args[0]
    
    # Parse optional arguments
    priority = "Medium"
    due_date = None
    category = None
    
    if len(args) > 1:
        priority = args[1]
    if len(args) > 2:
        try:
            due_date = parse_date_string(args[2], "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text(escape_markdown_v2("Invalid date format. Use YYYY-MM-DD"), parse_mode='MarkdownV2')
            return
    if len(args) > 3:
        category = args[3]
    
    task_service = _get_task_service()
    result = await task_service.create_task_with_metadata(
        description=description,
        priority=priority,
        due_date=due_date,
        category=category
    )
    
    if result['success']:
        task = result['data']
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                "✅ Task created!",
                {
                    "ID": task['id'],
                    "Description": task['description'],
                    "Priority": task['priority'],
                    "Due Date": task['due_date'] or 'None',
                    "Category": task['category'] or 'None'
                }
            ),
            parse_mode='MarkdownV2'
        )
        
        # Emit event using standardized format
        emit_task_event(_advanced_task_event_bus, "task_created", task)
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                f"❌ Error: {result['message']}",
                "Check your input format and try again."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/priority", "Set task priority", "Usage: /priority <task_id> <Low|Medium|High|Critical>", "tasks")
@require_args(2, 2)
async def priority_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set task priority."""
    if not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Task ID must be a number",
                "Usage: /priority <task_id> <Low|Medium|High|Critical>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    priority = context.args[1]
    
    task_service = _get_task_service()
    result = await task_service.update_task_priority(task_id, priority)
    
    if result['success']:
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"✅ {result['message']}",
                {"New Priority": priority}
            ),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check the task ID and priority value."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/due", "Set task due date", "Usage: /due <task_id> <YYYY-MM-DD>", "tasks")
@require_args(2, 2)
async def due_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set task due date."""
    if not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Task ID must be a number",
                "Usage: /due <task_id> <YYYY-MM-DD>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    
    try:
        due_date = parse_date_string(context.args[1], "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text(escape_markdown_v2("Invalid date format. Use YYYY-MM-DD"), parse_mode='MarkdownV2')
        return
    
    task_service = _get_task_service()
    result = await task_service.update_task_due_date(task_id, due_date)
    
    if result['success']:
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"✅ {result['message']}",
                {"New Due Date": due_date.strftime("%Y-%m-%d")}
            ),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check the task ID and date format (YYYY-MM-DD)."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/category", "Set task category", "Usage: /category <task_id> <category>", "tasks")
@require_args(2, 2)
async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set task category."""
    if not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Task ID must be a number",
                "Usage: /category <task_id> <category>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    category = context.args[1]
    
    task_service = _get_task_service()
    result = await task_service.update_task_category(task_id, category)
    
    if result['success']:
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"✅ {result['message']}",
                {"New Category": category}
            ),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check the task ID and category name."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/status", "Update task status", "Usage: /status <task_id> <Todo|In Progress|Review|Done>", "tasks")
@require_args(2, 2)
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update task status."""
    if not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Task ID must be a number",
                "Usage: /status <task_id> <Todo|In Progress|Review|Done>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    status = context.args[1]
    
    task_service = _get_task_service()
    result = await task_service.update_task_status(task_id, status)
    
    if result['success']:
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"✅ {result['message']}",
                {"New Status": status}
            ),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check the task ID and status value."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/time_start", "Start time tracking for task", "Usage: /time_start <task_id>", "tasks")
@require_args(1, 1)
async def start_time_tracking_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start time tracking for a task.
    
    Note: Renamed from /start to /time_start to avoid conflict with bot's core /start command.
    """
    if not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Task ID must be a number",
                "Usage: /time_start <task_id>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    task_service = _get_task_service()
    result = await task_service.start_time_tracking(task_id)
    
    if result['success']:
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"⏱️ {result['message']}",
                {"Task ID": task_id, "Status": "Time tracking started"}
            ),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check the task ID and try again."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/time_stop", "Stop time tracking for task", "Usage: /time_stop <task_id>", "tasks")
@require_args(1, 1)
async def stop_time_tracking_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Stop time tracking for a task.
    
    Note: Renamed from /stop to /time_stop for consistency with /time_start.
    """
    if not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Task ID must be a number",
                "Usage: /time_stop <task_id>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    task_service = _get_task_service()
    result = await task_service.stop_time_tracking(task_id)
    
    if result['success']:
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"⏹️ {result['message']}",
                {
                    "Task ID": task_id, 
                    "Status": "Time tracking stopped",
                    "Duration": result.get('duration', 'N/A')
                }
            ),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check the task ID and try again."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/subtask", "Create subtask", "Usage: /subtask <parent_id> <description>", "tasks")
@require_args(2, 2)
async def subtask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a subtask."""
    if not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Parent task ID must be a number",
                "Usage: /subtask <parent_id> <description>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    parent_id = int(context.args[0])
    description = context.args[1]
    
    task_service = _get_task_service()
    result = await task_service.add_subtask(parent_id, description)
    
    if result['success']:
        subtask = result['data']
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"✅ Subtask created!",
                {
                    "Subtask ID": subtask['id'],
                    "Parent Task": parent_id,
                    "Description": subtask['description']
                }
            ),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check the parent task ID and description."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/depend", "Add task dependency", "Usage: /depend <task_id> <dependency_id>", "tasks")
@require_args(2, 2)
async def dependency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a dependency between tasks."""
    if not context.args[0].isdigit() or not context.args[1].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Task IDs must be numbers",
                "Usage: /depend <task_id> <dependency_id>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    dependency_id = int(context.args[1])
    
    task_service = _get_task_service()
    result = await task_service.add_task_dependency(task_id, dependency_id)
    
    if result['success']:
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"✅ {result['message']}",
                {
                    "Task ID": task_id,
                    "Depends On": dependency_id
                }
            ),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check both task IDs and ensure they exist."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/tags", "Manage task tags", "Usage: /tags <task_id> <add|remove> <tag1,tag2,tag3>", "tasks")
@require_args(3, 3)
async def tags_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage task tags."""
    if not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Task ID must be a number",
                "Usage: /tags <task_id> <add|remove> <tag1,tag2,tag3>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    action = context.args[1]
    tags = [tag.strip() for tag in context.args[2].split(',')]
    
    task_service = _get_task_service()
    
    if action == "add":
        result = await task_service.add_tags(task_id, tags)
    elif action == "remove":
        result = await task_service.remove_tags(task_id, tags)
    else:
        await update.message.reply_text("Action must be 'add' or 'remove'")
        return
    
    if result['success']:
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"✅ {result['message']}",
                {
                    "Task ID": task_id,
                    "Action": action,
                    "Tags": ', '.join(tags)
                }
            ),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check the task ID, action (add/remove), and tag format."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/comment", "Add comment to task", "Usage: /comment <task_id> <comment>", "tasks")
@require_args(2, 2)
async def comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a comment to a task."""
    if not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Task ID must be a number",
                "Usage: /comment <task_id> <comment>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    comment = context.args[1]
    
    task_service = _get_task_service()
    result = await task_service.add_comment(task_id, comment)
    
    if result['success']:
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"✅ {result['message']}",
                {"Comment": comment}
            ),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check the task ID and comment text."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/comments", "Show task comments", "Usage: /comments <task_id>", "tasks")
@require_args(1, 1)
async def comments_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show comments for a task."""
    if not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Task ID must be a number",
                "Usage: /comments <task_id>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    
    task_service = _get_task_service()
    result = await task_service.get_comments(task_id)
    
    if result['success']:
        comments = result['data']
        if comments:
            msg = f"💬 **Comments for Task #{task_id}** \\({len(comments)} found\\)\n\n"
            for comment in comments:
                msg += f"📝 **{MessageFormatter.escape_markdown(comment['comment'])}**\n"
                msg += f"   📅 {comment['created_at'][:19]}\n\n"
        else:
            msg = f"💬 **Comments for Task #{task_id}**\n\nNo comments found."
        
        await update.message.reply_text(escape_markdown_v2(msg), parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check the task ID."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/tasks", "Advanced task filtering", "Usage: /tasks [status] [priority] [category]", "tasks")
async def advanced_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show tasks with advanced filtering and inline keyboards."""
    args = context.args
    
    # Parse filters
    status = None
    priority = None
    category = None
    
    if len(args) > 0:
        status = args[0]
    if len(args) > 1:
        priority = args[1]
    if len(args) > 2:
        category = args[2]
    
    task_service = _get_task_service()
    result = await task_service.get_tasks_with_filters(
        status=status,
        priority=priority,
        category=category,
        done=False
    )
    
    if result['success']:
        tasks = result['data']
        if tasks:
            # Format message using MessageFormatter
            title = "Tasks"
            if status or priority or category:
                filters = []
                if status:
                    filters.append(f"Status: {status}")
                if priority:
                    filters.append(f"Priority: {priority}")
                if category:
                    filters.append(f"Category: {category}")
                title = f"Tasks ({', '.join(filters)})"
            
            message = MessageFormatter.format_task_list(tasks, title)
            
            # Create inline keyboards for each task
            # For now, we'll show the first task with keyboard as an example
            # In a full implementation, we'd need to handle pagination
            if len(tasks) > 0:
                first_task = tasks[0]
                keyboard = KeyboardBuilder.build_task_keyboard(
                    first_task['id'], 
                    first_task['status']
                )
                
                await update.message.reply_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
            else:
                await update.message.reply_text(
                    message,
                    parse_mode='MarkdownV2'
                )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "No tasks found with the specified filters.",
                    "Try adjusting your filter criteria."
                ),
                parse_mode='MarkdownV2'
            )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check your filter parameters."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/overdue", "Show overdue tasks", "Usage: /overdue", "tasks")
async def overdue_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show overdue tasks."""
    task_service = _get_task_service()
    result = await task_service.get_tasks_with_filters(overdue_only=True)
    
    if result['success']:
        tasks = result['data']
        if tasks:
            msg = f"⚠️ Overdue tasks ({len(tasks)} found):\n\n"
            for task in tasks:
                msg += f"⚠️ {task['description']} (ID: {task['id']})\n"
                msg += f"   Due: {task['due_date']}\n"
                msg += f"   Priority: {task['priority']}\n\n"
        else:
            msg = "No overdue tasks! 🎉"
        
        await update.message.reply_text(escape_markdown_v2(msg))
    else:
        await update.message.reply_text(f"❌ Error: {result['message']}")

@command_handler("/today", "Show tasks due today", "Usage: /today", "tasks")
async def today_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show tasks due today."""
    today = get_today_date()
    start_of_day = get_start_of_day()
    end_of_day = get_end_of_day()
    
    task_service = _get_task_service()
    result = await task_service.get_tasks_with_filters(
        due_after=start_of_day,
        due_before=end_of_day,
        done=False
    )
    
    if result['success']:
        tasks = result['data']
        if tasks:
            msg = f"📅 Tasks due today ({len(tasks)} found):\n\n"
            for task in tasks:
                msg += f"📅 {task['description']} (ID: {task['id']})\n"
                msg += f"   Priority: {task['priority']} | Status: {task['status']}\n\n"
        else:
            msg = "No tasks due today! 🎉"
        
        await update.message.reply_text(escape_markdown_v2(msg))
    else:
        await update.message.reply_text(f"❌ Error: {result['message']}")

@command_handler("/week", "Show tasks due this week", "Usage: /week", "tasks")
async def week_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show tasks due this week."""
    start_of_week_dt = get_start_of_week()
    end_of_week_dt = get_end_of_week()
    
    task_service = _get_task_service()
    result = await task_service.get_tasks_with_filters(
        due_after=start_of_week_dt,
        due_before=end_of_week_dt,
        done=False
    )
    
    if result['success']:
        tasks = result['data']
        if tasks:
            msg = f"📅 Tasks due this week ({len(tasks)} found):\n\n"
            for task in tasks:
                msg += f"📅 {task['description']} (ID: {task['id']})\n"
                msg += f"   Due: {task['due_date']}\n"
                msg += f"   Priority: {task['priority']}\n\n"
        else:
            msg = "No tasks due this week! 🎉"
        
        await update.message.reply_text(escape_markdown_v2(msg))
    else:
        await update.message.reply_text(f"❌ Error: {result['message']}")

@command_handler("/search", "Enhanced search with basic and advanced modes", "Usage: /search <query> [--advanced] [--case-sensitive]", "tasks")
@require_args(1, 3)
async def search_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Enhanced search functionality combining basic and advanced search.
    
    Usage:
    - Basic: /search <query>
    - Advanced: /search <query> --advanced
    - Case-sensitive: /search <query> --case-sensitive
    - Full advanced: /search <query> --advanced --case-sensitive
    
    This consolidates the functionality of both /search and /search_advanced commands.
    """
    if not context.args:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Missing search query",
                "Usage: /search <query> [--advanced] [--case-sensitive]\n\n"
                "Examples:\n"
                "• Basic: /search project\n"
                "• Advanced: /search project --advanced\n"
                "• Case-sensitive: /search Project --case-sensitive"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    args = context.args
    query = args[0]
    
    # Parse optional flags
    use_advanced = "--advanced" in args
    case_sensitive = "--case-sensitive" in args
    
    try:
        task_service = _get_task_service()
        
        if use_advanced:
            # Use advanced search functionality
            result = await task_service.search_tasks_by_text(query, case_sensitive=case_sensitive)
        else:
            # Use basic search functionality (original behavior)
            result = await task_service.get_tasks_with_filters(done=False)
            
            if result['success']:
                tasks = result['data']
                # Simple text search (case-insensitive unless flag specified)
                search_query = query if case_sensitive else query.lower()
                matching_tasks = []
                
                for task in tasks:
                    task_desc = task['description'] if case_sensitive else task['description'].lower()
                    if search_query in task_desc:
                        matching_tasks.append(task)
                
                # Update result with filtered tasks
                result = {
                    'success': True,
                    'data': matching_tasks
                }
        
        if result['success']:
            tasks = result['data']
            if tasks:
                # Build search result title
                search_mode = "Advanced" if use_advanced else "Basic"
                sensitivity = " (Case-sensitive)" if case_sensitive else ""
                title = f"{search_mode} Search Results for '{query}'{sensitivity}"
                
                message = MessageFormatter.format_task_list(tasks[:10], title)
                if len(tasks) > 10:
                    message += f"\n\n📊 Showing first 10 of {len(tasks)} results"
                
                # Create action buttons for search results
                keyboard_buttons = []
                for task in tasks[:5]:  # Limit to first 5 for UI performance
                    task_row = [
                        InlineKeyboardButton(f"👁️ {task['id']}", callback_data=f"task_view:{task['id']}"),
                        InlineKeyboardButton(f"✅ {task['id']}", callback_data=f"task_done:{task['id']}"),
                        InlineKeyboardButton(f"✏️ {task['id']}", callback_data=f"task_edit:{task['id']}"),
                        InlineKeyboardButton(f"🗑️ {task['id']}", callback_data=f"task_delete:{task['id']}")
                    ]
                    keyboard_buttons.append(task_row)
                
                # Add navigation buttons
                keyboard_buttons.append([
                    InlineKeyboardButton("🔄 New Search", callback_data="search_new"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="nav_main")
                ])
                
                keyboard = InlineKeyboardMarkup(keyboard_buttons)
                
                await update.message.reply_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
            else:
                search_mode = "advanced" if use_advanced else "basic"
                await update.message.reply_text(
                    MessageFormatter.format_info_message(
                        "🔍 No Results Found",
                        {
                            "Query": query,
                            "Mode": search_mode.title(),
                            "Suggestion": "Try a different search term or use --advanced flag for enhanced search"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Unable to perform search. Try again with different parameters."
                ),
                parse_mode='MarkdownV2'
            )
    
    except Exception as e:
        # Fallback to basic search if advanced search fails
        if use_advanced:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Advanced search failed, falling back to basic search",
                    f"Searching for: {query}"
                ),
                parse_mode='MarkdownV2'
            )
            # Retry with basic search
            context.args = [query]  # Remove flags for basic search
            await _basic_search_fallback(update, query, case_sensitive)
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Search failed",
                    "Please try again with a different query."
                ),
                parse_mode='MarkdownV2'
            )

async def _basic_search_fallback(update: Update, query: str, case_sensitive: bool = False) -> None:
    """Fallback basic search functionality."""
    try:
        task_service = _get_task_service()
        result = await task_service.get_tasks_with_filters(done=False)
        
        if result['success']:
            tasks = result['data']
            search_query = query if case_sensitive else query.lower()
            matching_tasks = []
            
            for task in tasks:
                task_desc = task['description'] if case_sensitive else task['description'].lower()
                if search_query in task_desc:
                    matching_tasks.append(task)
            
            if matching_tasks:
                message = f"🔍 Basic search results for '{query}' ({len(matching_tasks)} found):\n\n"
                for task in matching_tasks[:10]:
                    message += f"🔍 {task['description']} (ID: {task['id']})\n"
                    message += f"   Priority: {task.get('priority', 'Medium')} | Status: {task.get('status', 'Todo')}\n\n"
            else:
                message = f"No tasks found matching '{query}'"
            
            await update.message.reply_text(escape_markdown_v2(message))
        else:
            await update.message.reply_text(f"❌ Error: {result['message']}")
    except Exception as e:
        await update.message.reply_text("❌ Search failed. Please try again later.")

@command_handler("/analytics", "Unified analytics with multiple complexity levels", "Usage: /analytics [basic|detailed|advanced] [days]", "tasks")
async def analytics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Unified task analytics with multiple complexity levels.
    
    Usage:
    - Basic: /analytics or /analytics basic
    - Detailed: /analytics detailed [days]
    - Advanced: /analytics advanced [days]
    
    This consolidates /analytics, /analytics_detailed, and /analytics_advanced commands.
    """
    args = context.args
    
    # Parse complexity level and days parameter
    complexity = "basic"  # Default
    days = 30  # Default
    
    if len(args) > 0:
        first_arg = args[0].lower()
        if first_arg in ["basic", "detailed", "advanced"]:
            complexity = first_arg
            # Days parameter is the second argument if complexity is specified
            if len(args) > 1:
                try:
                    days = int(args[1])
                    if days <= 0 or days > 365:
                        await update.message.reply_text(
                            MessageFormatter.format_error_message(
                                "Invalid number of days",
                                "Please specify a number between 1 and 365."
                            ),
                            parse_mode='MarkdownV2'
                        )
                        return
                except ValueError:
                    await update.message.reply_text(
                        MessageFormatter.format_error_message(
                            "Invalid number format",
                            "Please specify a valid number of days."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
        else:
            # First argument is days (backward compatibility)
            try:
                days = int(args[0])
                if days <= 0 or days > 365:
                    await update.message.reply_text(
                        MessageFormatter.format_error_message(
                            "Invalid number of days",
                            "Please specify a number between 1 and 365."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                complexity = "detailed"  # Default when days specified
            except ValueError:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        "Invalid parameter",
                        "Usage: /analytics [basic|detailed|advanced] [days]"
                    ),
                    parse_mode='MarkdownV2'
                )
                return
    
    try:
        task_service = _get_task_service()
        
        if complexity == "basic":
            # Basic analytics (original /analytics functionality)
            result = await task_service.get_task_analytics()
            
            if result['success']:
                analytics = result['data']
                message = AnalyticsFormatter.format_task_analytics(analytics)
                
                # Add complexity indicator
                message = f"📊 **Basic Analytics**\n\n{message}"
                
        elif complexity == "detailed":
            # Detailed analytics with time-based trends
            result = await task_service.get_detailed_analytics(days)
            
            if result['success']:
                analytics = result['data']
                
                message = f"📊 **Detailed Analytics** \\({days} days\\)\n\n"
                
                # Time-based trends
                if analytics.get('daily_completion_trends'):
                    message += f"📈 **Daily Completion Trends**\n"
                    trend_data = []
                    for date, count in analytics['daily_completion_trends'].items():
                        trend_data.append((date, count, f"{count} tasks"))
                    
                    message += ChartBuilder.build_timeline_chart(trend_data, "Daily Completions") + "\n"
                
                # Weekly patterns
                if analytics.get('weekly_patterns'):
                    message += f"📅 **Weekly Patterns**\n"
                    message += ChartBuilder.build_bar_chart(
                        analytics['weekly_patterns'], 
                        "Tasks by Day of Week"
                    ) + "\n"
                
                # Priority trends
                if analytics.get('priority_trends'):
                    message += f"🎯 **Priority Trends**\n"
                    message += ChartBuilder.build_heatmap(
                        analytics['priority_trends'], 
                        "Priority Distribution Over Time"
                    ) + "\n"
                
        elif complexity == "advanced":
            # Advanced analytics with comprehensive insights
            result = await task_service.get_advanced_task_analytics(days)
            
            if result['success']:
                analytics = result['data']
                message = f"📊 **Advanced Analytics** \\({days} days\\)\n\n"
                message += AnalyticsFormatter.format_task_analytics(analytics)
        
        if result['success']:
            # Create navigation keyboard for analytics actions
            keyboard_buttons = [
                [
                    InlineKeyboardButton("📊 Basic", callback_data="analytics_basic"),
                    InlineKeyboardButton("📈 Detailed", callback_data="analytics_detailed"),
                    InlineKeyboardButton("🚀 Advanced", callback_data="analytics_advanced")
                ],
                [
                    InlineKeyboardButton("📊 Custom Days", callback_data="analytics_custom"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="nav_main")
                ]
            ]
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
            
            # Add usage tip for different complexity levels
            if complexity == "basic":
                message += f"\n\n💡 **Tip**: Try `/analytics detailed` or `/analytics advanced` for more insights!"
            
            await update.message.reply_text(escape_markdown_v2(message), parse_mode='MarkdownV2')
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    f"Unable to generate {complexity} analytics. Please try again."
                ),
                parse_mode='MarkdownV2'
            )
    
    except Exception as e:
        # Fallback to basic analytics if advanced features fail
        if complexity != "basic":
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"{complexity.title()} analytics failed, falling back to basic",
                    "Generating basic analytics..."
                ),
                parse_mode='MarkdownV2'
            )
            # Retry with basic analytics
            context.args = []  # Remove complexity arguments
            await _basic_analytics_fallback(update)
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Analytics generation failed",
                    "Please try again later."
                ),
                parse_mode='MarkdownV2'
            )

async def _basic_analytics_fallback(update: Update) -> None:
    """Fallback basic analytics functionality."""
    try:
        task_service = _get_task_service()
        result = await task_service.get_task_analytics()
        
        if result['success']:
            analytics = result['data']
            message = f"📊 **Basic Analytics** \\(Fallback\\)\n\n"
            message += AnalyticsFormatter.format_task_analytics(analytics)
            
            await update.message.reply_text(escape_markdown_v2(message))
        else:
            await update.message.reply_text(
                f"❌ Error: {result['message']}"
            )
    except Exception as e:
        await update.message.reply_text("❌ Analytics failed. Please try again later.")

@command_handler("/analytics_detailed", "Show detailed analytics", "Usage: /analytics_detailed [days]", "tasks")
async def analytics_detailed_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed analytics with time-based trends."""
    days = 30  # Default to 30 days
    if context.args:
        try:
            days = int(context.args[0])
            if days <= 0 or days > 365:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        "Invalid number of days",
                        "Please specify a number between 1 and 365."
                    ),
                    parse_mode='MarkdownV2'
                )
                return
        except ValueError:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Invalid number format",
                    "Please specify a valid number of days."
                ),
                parse_mode='MarkdownV2'
            )
            return
    
    task_service = _get_task_service()
    result = await task_service.get_detailed_analytics(days)
    
    if result['success']:
        analytics = result['data']
        
        message = f"📊 **Detailed Analytics** \\({days} days\\)\n\n"
        
        # Time-based trends
        if analytics.get('daily_completion_trends'):
            message += f"📈 **Daily Completion Trends**\n"
            trend_data = []
            for date, count in analytics['daily_completion_trends'].items():
                trend_data.append((date, count, f"{count} tasks"))
            
            message += ChartBuilder.build_timeline_chart(trend_data, "Daily Completions") + "\n"
        
        # Weekly patterns
        if analytics.get('weekly_patterns'):
            message += f"📅 **Weekly Patterns**\n"
            message += ChartBuilder.build_bar_chart(
                analytics['weekly_patterns'], 
                "Tasks by Day of Week"
            ) + "\n"
        
        # Priority trends
        if analytics.get('priority_trends'):
            message += f"🎯 **Priority Trends**\n"
            message += ChartBuilder.build_heatmap(
                analytics['priority_trends'], 
                "Priority Distribution Over Time"
            ) + "\n"
        
        # Performance metrics
        if analytics.get('performance_metrics'):
            metrics = analytics['performance_metrics']
            message += f"🎯 **Performance Metrics**\n"
            message += ChartBuilder.build_progress_bar(
                metrics.get('efficiency', 0), 100, 15, "Overall Efficiency"
            ) + "\n"
            message += ChartBuilder.build_progress_bar(
                metrics.get('consistency', 0), 100, 15, "Consistency"
            ) + "\n"
        
        await update.message.reply_text(escape_markdown_v2(message), parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Unable to generate detailed analytics. Please try again."
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/suggest", "Suggest task priority", "Usage: /suggest <description>", "tasks")
@require_args(1, 1)
async def suggest_priority_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Suggest priority based on task description."""
    description = context.args[0]
    
    task_service = _get_task_service()
    result = await task_service.suggest_priority(description)
    
    if result['success']:
        suggestion = result['data']
        await update.message.reply_text(
            f"🤖 Priority Suggestion\n\n"
            f"Description: {suggestion['description']}\n"
            f"Suggested Priority: {suggestion['suggested_priority']}\n\n"
            f"Use: /addtask {description} {suggestion['suggested_priority']}"
        )
    else:
        await update.message.reply_text(f"❌ Error: {result['message']}")

@command_handler("/bulk_status", "Bulk update task status", "Usage: /bulk_status <task_id1,task_id2,task_id3> <status>", "tasks")
@require_args(2, 2)
async def bulk_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bulk update task status with rich feedback."""
    try:
        task_ids = [int(id.strip()) for id in context.args[0].split(',')]
        status = context.args[1]
        
        # Validate status
        valid_statuses = ['Todo', 'In Progress', 'Review', 'Done']
        if status not in valid_statuses:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Invalid status",
                    f"Valid statuses: {', '.join(valid_statuses)}"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        task_service = _get_task_service()
        result = await task_service.bulk_update_status(task_ids, status)
        
        if result['success']:
            await update.message.reply_text(
                MessageFormatter.format_success_message(
                    f"✅ Bulk Status Update Complete!",
                    {
                        "Tasks Updated": len(task_ids),
                        "New Status": status,
                        "Details": result.get('details', 'All tasks updated successfully')
                    }
                ),
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Please check the task IDs and status value."
                ),
                parse_mode='MarkdownV2'
            )
    except ValueError:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid task ID format",
                "Usage: /bulk_status 1,2,3 <status>"
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/bulk_priority", "Bulk update task priority", "Usage: /bulk_priority <task_id1,task_id2,task_id3> <priority>", "tasks")
@require_args(2, 2)
async def bulk_priority_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bulk update task priority with rich feedback."""
    try:
        task_ids = [int(id.strip()) for id in context.args[0].split(',')]
        priority = context.args[1]
        
        # Validate priority
        valid_priorities = ['Low', 'Medium', 'High', 'Critical']
        if priority not in valid_priorities:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Invalid priority",
                    f"Valid priorities: {', '.join(valid_priorities)}"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        task_service = _get_task_service()
        result = await task_service.bulk_update_priority(task_ids, priority)
        
        if result['success']:
            await update.message.reply_text(
                MessageFormatter.format_success_message(
                    f"✅ Bulk Priority Update Complete!",
                    {
                        "Tasks Updated": len(task_ids),
                        "New Priority": priority,
                        "Details": result.get('details', 'All tasks updated successfully')
                    }
                ),
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Please check the task IDs and priority value."
                ),
                parse_mode='MarkdownV2'
            )
    except ValueError:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid task ID format",
                "Usage: /bulk_priority 1,2,3 <priority>"
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/bulk_assign", "Bulk assign tasks to client", "Usage: /bulk_assign <task_id1,task_id2,task_id3> <client_name>", "tasks")
@require_args(2, 2)
async def bulk_assign_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bulk assign tasks to a client with rich feedback."""
    try:
        task_ids = [int(id.strip()) for id in context.args[0].split(',')]
        client_name = context.args[1]
        
        task_service = _get_task_service()
        result = await task_service.bulk_assign_to_client(task_ids, client_name)
        
        if result['success']:
            await update.message.reply_text(
                MessageFormatter.format_success_message(
                    f"✅ Bulk Assignment Complete!",
                    {
                        "Tasks Assigned": len(task_ids),
                        "Client": client_name,
                        "Details": result.get('details', 'All tasks assigned successfully')
                    }
                ),
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Please check the task IDs and client name."
                ),
                parse_mode='MarkdownV2'
            )
    except ValueError:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid task ID format",
                "Usage: /bulk_assign 1,2,3 <client_name>"
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/bulk_delete", "Bulk delete tasks", "Usage: /bulk_delete <task_id1,task_id2,task_id3> [confirm]", "tasks")
@require_args(1, 2)
async def bulk_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bulk delete tasks with confirmation dialog."""
    try:
        task_ids = [int(id.strip()) for id in context.args[0].split(',')]
        confirm = len(context.args) > 1 and context.args[1].lower() == "confirm"
        
        if not confirm:
            # Show confirmation dialog with rich formatting
            message = MessageFormatter.format_warning_message(
                f"⚠️ Bulk Delete Confirmation Required",
                {
                    "Tasks to Delete": len(task_ids),
                    "Task IDs": context.args[0],
                    "Action": "This action cannot be undone",
                    "Confirmation": f"Use: /bulk_delete {context.args[0]} confirm"
                }
            )
            
            # Create confirmation keyboard
            keyboard = KeyboardBuilder.build_confirmation_keyboard(
                f"bulk_delete_confirm:{context.args[0]}",
                f"bulk_delete_cancel"
            )
            
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
            return
        
        task_service = _get_task_service()
        result = await task_service.bulk_delete_tasks(task_ids)
        
        if result['success']:
            await update.message.reply_text(
                MessageFormatter.format_success_message(
                    f"🗑️ Bulk Delete Complete!",
                    {
                        "Tasks Deleted": len(task_ids),
                        "Details": result.get('details', 'All tasks deleted successfully'),
                        "Note": "This action cannot be undone"
                    }
                ),
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Please check the task IDs and try again."
                ),
                parse_mode='MarkdownV2'
            )
    except ValueError:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid task ID format",
                "Usage: /bulk_delete 1,2,3 [confirm]"
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/bulk_operations", "Bulk operations menu", "Usage: /bulk_operations", "tasks")
async def bulk_operations_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bulk operations menu with rich formatting."""
    message = MessageFormatter.format_info_message(
        "🔄 Bulk Operations Menu",
        {
            "Status Update": "/bulk_status <ids> <status>",
            "Priority Update": "/bulk_priority <ids> <priority>",
            "Client Assignment": "/bulk_assign <ids> <client>",
            "Bulk Delete": "/bulk_delete <ids> [confirm]",
            "Format": "Task IDs: 1,2,3,4,5"
        }
    )
    
    # Create bulk operations keyboard
    keyboard = KeyboardBuilder.build_bulk_operations_keyboard()
    
    await update.message.reply_text(
        message,
        reply_markup=keyboard,
        parse_mode='MarkdownV2'
    )

@command_handler("/time_entry", "Add manual time entry", "Usage: /time_entry <task_id> <duration_minutes> [description]", "tasks")
@require_args(2, 3)
async def time_entry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add manual time entry for a task."""
    try:
        task_id = int(context.args[0])
        duration_minutes = int(context.args[1])
        description = context.args[2] if len(context.args) > 2 else ""
        
        task_service = _get_task_service()
        result = await task_service.add_manual_time_entry(task_id, duration_minutes, description)
        
        if result['success']:
            await update.message.reply_text(f"✅ {result['message']}")
        else:
            await update.message.reply_text(f"❌ Error: {result['message']}")
    except ValueError:
        await update.message.reply_text("❌ Error: Invalid format. Use: /time_entry <task_id> <duration_minutes> [description]")

@command_handler("/time_summary", "Show time summary for task", "Usage: /time_summary <task_id>", "tasks")
@require_args(1, 1)
async def time_summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show comprehensive time summary for a task."""
    try:
        task_id = int(context.args[0])
        
        task_service = _get_task_service()
        result = await task_service.get_task_time_summary(task_id)
        
        if result['success']:
            summary = result['data']
            msg = f"⏱️ Time Summary for Task \\#{task_id}\n\n"
            msg += f"📋 Task: {summary['task_description']}\n\n"
            msg += f"⏰ Estimated Hours: {summary['estimated_hours']:.2f}\n"
            msg += f"⏰ Actual Hours: {summary['actual_hours']:.2f}\n"
            msg += f"⏰ Time Entries: {summary['time_entries_hours']:.2f} hours ({summary['time_entries_count']} entries)\n"
            msg += f"💬 Comments: {summary['comments_count']}\n"
            msg += f"📊 Efficiency: {summary['efficiency']:.1f}%"
            
            await update.message.reply_text(escape_markdown_v2(msg))
        else:
            await update.message.reply_text(f"❌ Error: {result['message']}")
    except ValueError:
        await update.message.reply_text("❌ Error: Invalid task ID. Use: /time_summary <task_id>")

@command_handler("/search_advanced", "Advanced text search", "Usage: /search_advanced <search_text>", "tasks")
@require_args(1, 1)
async def search_advanced_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Advanced text search in tasks with rich UX."""
    search_text = context.args[0]
    task_service = _get_task_service()
    result = await task_service.search_tasks_by_text(search_text, case_sensitive=False)
    if result['success']:
        tasks = result['data']
        if tasks:
            title = f"Search results for '{search_text}'"
            message = MessageFormatter.format_task_list(tasks[:10], title)
            if len(tasks) > 10:
                message += f"\n... and {len(tasks) - 10} more results"
            keyboard = KeyboardBuilder.build_filter_keyboard()
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"No tasks found matching '{search_text}'",
                    "Try a different search term."
                ),
                reply_markup=KeyboardBuilder.build_filter_keyboard(),
                parse_mode='MarkdownV2'
            )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Unable to perform search."
            ),
            reply_markup=KeyboardBuilder.build_filter_keyboard(),
            parse_mode='MarkdownV2'
        )

@command_handler("/filter_advanced", "Advanced filtering", "Usage: /filter_advanced [status] [priority] [category] [sort_by] [sort_order]", "tasks")
async def filter_advanced_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Advanced task filtering with sorting and interactive UX."""
    args = context.args
    status = args[0] if len(args) > 0 else None
    priority = args[1] if len(args) > 1 else None
    category = args[2] if len(args) > 2 else None
    sort_by = args[3] if len(args) > 3 else "created_at"
    sort_order = args[4] if len(args) > 4 else "desc"

    task_service = _get_task_service()
    result = await task_service.get_tasks_with_advanced_filters(
        status=status,
        priority=priority,
        category=category,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=20
    )

    if result['success']:
        tasks = result['data']
        if tasks:
            title = "Advanced Filter Results"
            filters = []
            if status:
                filters.append(f"Status: {status}")
            if priority:
                filters.append(f"Priority: {priority}")
            if category:
                filters.append(f"Category: {category}")
            if filters:
                title += f" ({', '.join(filters)})"
            message = MessageFormatter.format_task_list(tasks, title)
            keyboard = KeyboardBuilder.build_filter_keyboard()
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "No tasks found with the specified filters.",
                    "Try adjusting your filter criteria."
                ),
                reply_markup=KeyboardBuilder.build_filter_keyboard(),
                parse_mode='MarkdownV2'
            )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Check your filter parameters."
            ),
            reply_markup=KeyboardBuilder.build_filter_keyboard(),
            parse_mode='MarkdownV2'
        )

@command_handler("/tags_multi", "Multi-tag filtering", "Usage: /tags_multi <tag1,tag2,tag3> [all|any]", "tasks")
@require_args(1, 2)
async def tags_multi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Filter tasks by multiple tags with rich UX."""
    try:
        tags = [tag.strip() for tag in context.args[0].split(',')]
        match_all = len(context.args) > 1 and context.args[1].lower() == "all"
        task_service = _get_task_service()
        result = await task_service.get_tasks_by_multiple_tags(tags, match_all)
        match_type = "all" if match_all else "any"
        if result['success']:
            tasks = result['data']
            if tasks:
                title = f"Tasks matching {match_type} of tags: {', '.join(tags)}"
                message = MessageFormatter.format_task_list(tasks, title)
                keyboard = KeyboardBuilder.build_filter_keyboard()
                await update.message.reply_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
            else:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        f"No tasks found matching {match_type} of tags: {', '.join(tags)}",
                        "Try different tags or match type."
                    ),
                    reply_markup=KeyboardBuilder.build_filter_keyboard(),
                    parse_mode='MarkdownV2'
                )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Check your tag format and try again."
                ),
                reply_markup=KeyboardBuilder.build_filter_keyboard(),
                parse_mode='MarkdownV2'
            )
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid format for multi-tag filtering.",
                "Usage: /tags_multi <tag1,tag2,tag3> [all|any]"
            ),
            reply_markup=KeyboardBuilder.build_filter_keyboard(),
            parse_mode='MarkdownV2'
        )

@command_handler("/time_range", "Time range filtering", "Usage: /time_range <start_date> <end_date> [include_completed]", "tasks")
@require_args(2, 3)
async def time_range_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Filter tasks by time range with rich UX."""
    try:
        start_date = datetime.strptime(context.args[0], "%Y-%m-%d")
        end_date = datetime.strptime(context.args[1], "%Y-%m-%d")
        include_completed = len(context.args) > 2 and context.args[2].lower() == "true"
        task_service = _get_task_service()
        result = await task_service.get_tasks_by_time_range(start_date, end_date, include_completed)
        completed_text = "including completed" if include_completed else "excluding completed"
        if result['success']:
            tasks = result['data']
            if tasks:
                title = f"Tasks in time range {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({completed_text})"
                message = MessageFormatter.format_task_list(tasks, title)
                keyboard = KeyboardBuilder.build_filter_keyboard()
                await update.message.reply_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
            else:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        f"No tasks found in the specified time range ({completed_text})",
                        "Try a different date range."
                    ),
                    reply_markup=KeyboardBuilder.build_filter_keyboard(),
                    parse_mode='MarkdownV2'
                )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Unable to filter by time range."
                ),
                reply_markup=KeyboardBuilder.build_filter_keyboard(),
                parse_mode='MarkdownV2'
            )
    except ValueError:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid date format for time range filtering.",
                "Usage: /time_range <YYYY-MM-DD> <YYYY-MM-DD> [true|false]"
            ),
            reply_markup=KeyboardBuilder.build_filter_keyboard(),
            parse_mode='MarkdownV2'
        )

@command_handler("/priority_range", "Priority range filtering", "Usage: /priority_range <min_priority> <max_priority>", "tasks")
@require_args(2, 2)
async def priority_range_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Filter tasks by priority range with rich UX."""
    min_priority = context.args[0]
    max_priority = context.args[1]
    task_service = _get_task_service()
    result = await task_service.get_tasks_by_priority_range(min_priority, max_priority)
    if result['success']:
        tasks = result['data']
        if tasks:
            title = f"Tasks in priority range {min_priority} to {max_priority}"
            message = MessageFormatter.format_task_list(tasks, title)
            keyboard = KeyboardBuilder.build_filter_keyboard()
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"No tasks found in priority range {min_priority} to {max_priority}",
                    "Try a different range."
                ),
                reply_markup=KeyboardBuilder.build_filter_keyboard(),
                parse_mode='MarkdownV2'
            )
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                result['message'],
                "Unable to filter by priority range."
            ),
            reply_markup=KeyboardBuilder.build_filter_keyboard(),
            parse_mode='MarkdownV2'
        )

@command_handler("/analytics_advanced", "Advanced analytics", "Usage: /analytics_advanced [days]", "tasks")
async def analytics_advanced_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get advanced task analytics with rich UX."""
    try:
        days = int(context.args[0]) if len(context.args) > 0 else 30
        task_service = _get_task_service()
        result = await task_service.get_advanced_task_analytics(days)
        if result['success']:
            analytics = result['data']
            message = AnalyticsFormatter.format_task_analytics(analytics)
            keyboard = KeyboardBuilder.build_analytics_keyboard()
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Unable to generate advanced analytics. Please try again."
                ),
                reply_markup=KeyboardBuilder.build_analytics_keyboard(),
                parse_mode='MarkdownV2'
            )
    except ValueError:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid days format for analytics.",
                "Usage: /analytics_advanced [days]"
            ),
            reply_markup=KeyboardBuilder.build_analytics_keyboard(),
            parse_mode='MarkdownV2'
        )

@command_handler("/productivity_report", "Productivity report", "Usage: /productivity_report <start_date> <end_date>", "tasks")
@require_args(2, 2)
async def productivity_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get detailed productivity report with rich UX."""
    try:
        start_date = datetime.strptime(context.args[0], "%Y-%m-%d")
        end_date = datetime.strptime(context.args[1], "%Y-%m-%d")
        task_service = _get_task_service()
        result = await task_service.get_productivity_report(start_date, end_date)
        if result['success']:
            report = result['data']
            message = AnalyticsFormatter.format_productivity_report(report)
            keyboard = KeyboardBuilder.build_analytics_keyboard()
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Unable to generate productivity report. Please try again."
                ),
                reply_markup=KeyboardBuilder.build_analytics_keyboard(),
                parse_mode='MarkdownV2'
            )
    except ValueError:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid date format for productivity report.",
                "Usage: /productivity_report <YYYY-MM-DD> <YYYY-MM-DD>"
            ),
            reply_markup=KeyboardBuilder.build_analytics_keyboard(),
            parse_mode='MarkdownV2'
        )

# ============================================================================
# DEPRECATED COMMAND HANDLERS - Consolidation Phase
# ============================================================================
# These handlers provide backward compatibility and smooth transition
# for users still using the old command names.

async def deprecated_addtask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /addtask to enhanced /add command."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Consolidated",
            {
                "Old Command": "/addtask",
                "New Command": "/add",
                "Migration": "The /addtask command has been merged into /add",
                "Usage": "/add <description> [priority] [due_date] [category]",
                "Benefits": "Same functionality with cleaner interface"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to the enhanced /add handler
    from larrybot.plugins.tasks import add_task_handler
    await add_task_handler(update, context)

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
                "Benefits": "Unified task listing with optional filtering"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to the enhanced /list handler
    from larrybot.plugins.tasks import list_tasks_handler
    await list_tasks_handler(update, context)

async def deprecated_search_advanced_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /search_advanced to enhanced /search command."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Consolidated",
            {
                "Old Command": "/search_advanced",
                "New Command": "/search",
                "Migration": "The /search_advanced command has been merged into /search",
                "Usage": "/search <query> --advanced",
                "Benefits": "Unified search with basic and advanced modes"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to enhanced search with --advanced flag
    if context.args:
        context.args.append("--advanced")
        await search_tasks_handler(update, context)
    else:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Missing search query",
                "Usage: /search <query> --advanced"
            ),
            parse_mode='MarkdownV2'
        )

async def deprecated_analytics_detailed_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /analytics_detailed to unified /analytics command."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Consolidated",
            {
                "Old Command": "/analytics_detailed",
                "New Command": "/analytics",
                "Migration": "The /analytics_detailed command has been merged into /analytics",
                "Usage": "/analytics detailed [days]",
                "Benefits": "Unified analytics with multiple complexity levels"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to unified analytics with detailed level
    new_args = ["detailed"]
    if context.args:
        new_args.extend(context.args)
    context.args = new_args
    await analytics_handler(update, context)

async def deprecated_analytics_advanced_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /analytics_advanced to unified /analytics command."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Consolidated",
            {
                "Old Command": "/analytics_advanced",
                "New Command": "/analytics",
                "Migration": "The /analytics_advanced command has been merged into /analytics",
                "Usage": "/analytics advanced [days]",
                "Benefits": "Unified analytics with multiple complexity levels"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to unified analytics with advanced level
    new_args = ["advanced"]
    if context.args:
        new_args.extend(context.args)
    context.args = new_args
    await analytics_handler(update, context)

async def deprecated_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /start to /time_start for time tracking."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Renamed",
            {
                "Old Command": "/start",
                "New Command": "/time_start", 
                "Reason": "Namespace conflict resolution with bot's core /start command",
                "Usage": "/time_start <task_id>",
                "Benefits": "Clearer command naming and no conflicts"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to renamed time tracking handler
    await start_time_tracking_handler(update, context)

async def deprecated_stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Redirect /stop to /time_stop for consistency."""
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "🔄 Command Renamed",
            {
                "Old Command": "/stop",
                "New Command": "/time_stop",
                "Reason": "Consistency with /time_start naming",
                "Usage": "/time_stop <task_id>",
                "Benefits": "Consistent time tracking command naming"
            }
        ),
        parse_mode='MarkdownV2'
    )
    
    # Redirect to renamed time tracking handler
    await stop_time_tracking_handler(update, context) 