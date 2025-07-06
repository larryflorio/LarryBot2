"""
Core task operations for the Advanced Tasks plugin.

This module handles the primary task creation and basic task management
operations including /addtask, /priority, /due, /category, and /status.
"""
from telegram import Update
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.utils.decorators import command_handler, require_args
from larrybot.utils.ux_helpers import MessageFormatter
from larrybot.utils.datetime_utils import parse_date_string
from larrybot.utils.enhanced_ux_helpers import escape_markdown_v2
from larrybot.core.event_utils import emit_task_event
from .utils import get_task_service, validate_task_id
_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    """Register core task operation commands."""
    global _event_bus
    _event_bus = event_bus
    command_registry.register('/addtask', add_task_with_metadata_handler)
    command_registry.register('/priority', priority_handler)
    command_registry.register('/due', due_date_handler)
    command_registry.register('/category', category_handler)
    command_registry.register('/status', status_handler)


async def _add_task_with_metadata_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of add task with metadata handler."""
    if task_service is None:
        task_service = get_task_service()
    args = context.args
    description = args[0]
    priority = 'Medium'
    due_date = None
    category = None
    if len(args) > 1:
        priority = args[1]
    if len(args) > 2:
        try:
            due_date = parse_date_string(args[2], '%Y-%m-%d')
        except ValueError:
            await update.message.reply_text(escape_markdown_v2(
                'Invalid date format. Use YYYY-MM-DD'), parse_mode='MarkdownV2'
                )
            return
    if len(args) > 3:
        category = args[3]
    result = await task_service.create_task_with_metadata(description=
        description, priority=priority, due_date=due_date, category=category)
    if result['success']:
        task = result['data']
        await update.message.reply_text(MessageFormatter.
            format_success_message('✅ Task created!', {'ID': task['id'],
            'Description': task['description'], 'Priority': task['priority'
            ], 'Due Date': task['due_date'] or 'None', 'Category': task[
            'category'] or 'None'}), parse_mode='MarkdownV2')
        emit_task_event(_event_bus, 'task_created', task)
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(f"❌ Error: {result['message']}",
            'Check your input format and try again.'), parse_mode='MarkdownV2')


async def _priority_handler_internal(update: Update, context: ContextTypes.
    DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of priority handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg,
            'Usage: /priority <task_id> <Low|Medium|High|Critical>'),
            parse_mode='MarkdownV2')
        return
    priority = context.args[1]
    result = await task_service.update_task_priority(task_id, priority)
    if result['success']:
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"✅ {result['message']}", {
            'New Priority': priority}), parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task ID and priority value.'), parse_mode='MarkdownV2')


async def _due_date_handler_internal(update: Update, context: ContextTypes.
    DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of due date handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg,
            'Usage: /due <task_id> <YYYY-MM-DD>'), parse_mode='MarkdownV2')
        return
    try:
        due_date = parse_date_string(context.args[1], '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text(escape_markdown_v2(
            'Invalid date format. Use YYYY-MM-DD'), parse_mode='MarkdownV2')
        return
    result = await task_service.update_task_due_date(task_id, due_date)
    if result['success']:
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"✅ {result['message']}", {
            'New Due Date': due_date.strftime('%Y-%m-%d')}), parse_mode=
            'MarkdownV2')
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task ID and date format (YYYY-MM-DD).'), parse_mode=
            'MarkdownV2')


async def _category_handler_internal(update: Update, context: ContextTypes.
    DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of category handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg,
            'Usage: /category <task_id> <category>'), parse_mode='MarkdownV2')
        return
    category = context.args[1]
    result = await task_service.update_task_category(task_id, category)
    if result['success']:
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"✅ {result['message']}", {
            'New Category': category}), parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task ID and category name.'), parse_mode='MarkdownV2')


async def _status_handler_internal(update: Update, context: ContextTypes.
    DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of status handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg,
            'Usage: /status <task_id> <Todo|In Progress|Review|Done>'),
            parse_mode='MarkdownV2')
        return
    status = context.args[1]
    result = await task_service.update_task_status(task_id, status)
    if result['success']:
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"✅ {result['message']}", {'New Status':
            status}), parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task ID and status value.'), parse_mode='MarkdownV2')


@command_handler('/addtask', 'Create task with advanced metadata',
    'Usage: /addtask <description> [priority] [due_date] [category]', 'tasks')
@require_args(1, 4)
async def add_task_with_metadata_handler(update: Update, context:
    ContextTypes.DEFAULT_TYPE) ->None:
    """Create a task with advanced metadata."""
    await _add_task_with_metadata_handler_internal(update, context)


@command_handler('/priority', 'Set task priority',
    'Usage: /priority <task_id> <Low|Medium|High|Critical>', 'tasks')
@require_args(2, 2)
async def priority_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Set task priority."""
    await _priority_handler_internal(update, context)


@command_handler('/due', 'Set task due date',
    'Usage: /due <task_id> <YYYY-MM-DD>', 'tasks')
@require_args(2, 2)
async def due_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Set task due date."""
    await _due_date_handler_internal(update, context)


@command_handler('/category', 'Set task category',
    'Usage: /category <task_id> <category>', 'tasks')
@require_args(2, 2)
async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Set task category."""
    await _category_handler_internal(update, context)


@command_handler('/status', 'Update task status',
    'Usage: /status <task_id> <Todo|In Progress|Review|Done>', 'tasks')
@require_args(2, 2)
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Update task status."""
    await _status_handler_internal(update, context)
