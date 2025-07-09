"""
Basic filtering and search module for the Advanced Tasks plugin.

This module handles basic task filtering and search operations.
"""
from telegram import Update
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.utils.decorators import command_handler, require_args
from larrybot.utils.ux_helpers import MessageFormatter
from larrybot.core.event_utils import emit_task_event
_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    """Register basic filtering and search commands."""
    global _event_bus
    _event_bus = event_bus
    command_registry.register('/tasks', advanced_tasks_handler)
    command_registry.register('/overdue', overdue_tasks_handler)
    command_registry.register('/today', today_tasks_handler)
    command_registry.register('/week', week_tasks_handler)
    command_registry.register('/search', search_tasks_handler)


async def _advanced_tasks_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of advanced tasks handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    filters = {}
    if len(context.args) > 0:
        filters['status'] = context.args[0]
    if len(context.args) > 1:
        filters['priority'] = context.args[1]
    if len(context.args) > 2:
        filters['category'] = context.args[2]
    result = await task_service.get_tasks_with_filters(filters)
    if result['success']:
        tasks = result['data']
        if not tasks:
            await update.message.reply_text(MessageFormatter.
                format_info_message('📋 Advanced Task Filter', {'Status':
                'No tasks found matching criteria'}), parse_mode='MarkdownV2')
        else:
            message = MessageFormatter.format_task_list(tasks, 'Advanced Task Filter')
            await update.message.reply_text(message, parse_mode='MarkdownV2')
            emit_task_event(_event_bus, 'tasks_filtered', {'filters':
                filters, 'count': len(tasks)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check your filter criteria and try again.'), parse_mode=
            'MarkdownV2')


async def _overdue_tasks_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of overdue tasks handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    result = await task_service.get_tasks_with_filters({'overdue': True})
    if result['success']:
        tasks = result['data']
        if not tasks:
            await update.message.reply_text(MessageFormatter.
                format_success_message('✅ Overdue Tasks', {'Status':
                'No overdue tasks found'}), parse_mode='MarkdownV2')
        else:
            message = MessageFormatter.format_task_list(tasks, 'Overdue Tasks')
            await update.message.reply_text(message, parse_mode='MarkdownV2')
            emit_task_event(_event_bus, 'overdue_tasks_viewed', {'count':
                len(tasks)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Unable to retrieve overdue tasks.'), parse_mode='MarkdownV2')


async def _today_tasks_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of today tasks handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    
    # Use DateTimeService for proper timezone handling
    from larrybot.services.datetime_service import DateTimeService
    start_of_today = DateTimeService.get_start_of_day()
    end_of_today = DateTimeService.get_end_of_day()
    
    result = await task_service.get_tasks_with_filters(
        due_after=start_of_today, 
        due_before=end_of_today,
        done=False
    )
    if result['success']:
        tasks = result['data']
        if not tasks:
            await update.message.reply_text(MessageFormatter.
                format_info_message("📅 Today's Tasks", {'Status':
                'No tasks due today'}), parse_mode='MarkdownV2')
        else:
            message = MessageFormatter.format_task_list(tasks, "Today's Tasks")
            await update.message.reply_text(message, parse_mode='MarkdownV2')
            emit_task_event(_event_bus, 'today_tasks_viewed', {'count': len
                (tasks)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            "Unable to retrieve today's tasks."), parse_mode='MarkdownV2')


async def _week_tasks_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of week tasks handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    result = await task_service.get_tasks_with_filters({'due_this_week': True})
    if result['success']:
        tasks = result['data']
        if not tasks:
            await update.message.reply_text(MessageFormatter.
                format_info_message("📅 This Week's Tasks", {'Status':
                'No tasks due this week'}), parse_mode='MarkdownV2')
        else:
            message = MessageFormatter.format_task_list(tasks, "This Week's Tasks")
            await update.message.reply_text(message, parse_mode='MarkdownV2')
            emit_task_event(_event_bus, 'week_tasks_viewed', {'count': len(
                tasks)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            "Unable to retrieve this week's tasks."), parse_mode='MarkdownV2')


async def _search_tasks_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of search tasks handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    query = context.args[0]
    search_options = {}
    if len(context.args) > 1 and context.args[1] == '--advanced':
        search_options['advanced'] = True
    if len(context.args) > 2 and context.args[2] == '--case-sensitive':
        search_options['case_sensitive'] = True
    result = await task_service.search_tasks_by_text(query, case_sensitive=
        search_options.get('case_sensitive', False))
    if result['success']:
        tasks = result['data']
        if not tasks:
            await update.message.reply_text(MessageFormatter.
                format_info_message(f"🔍 Search Results: '{query}'", {
                'Status': 'No tasks found'}), parse_mode='MarkdownV2')
        else:
            message = MessageFormatter.format_task_list(tasks, f"Search Results: '{query}'")
            await update.message.reply_text(message, parse_mode='MarkdownV2')
            emit_task_event(_event_bus, 'tasks_searched', {'query': query,
                'options': search_options, 'count': len(tasks)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check your search query and try again.'), parse_mode='MarkdownV2')


@command_handler('/tasks', 'Advanced task filtering',
    'Usage: /tasks [status] [priority] [category]', 'tasks')
async def advanced_tasks_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Advanced task filtering."""
    await _advanced_tasks_handler_internal(update, context)


@command_handler('/overdue', 'Show overdue tasks', 'Usage: /overdue', 'tasks')
async def overdue_tasks_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Show overdue tasks."""
    await _overdue_tasks_handler_internal(update, context)


@command_handler('/today', 'Show tasks due today', 'Usage: /today', 'tasks')
async def today_tasks_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Show tasks due today."""
    await _today_tasks_handler_internal(update, context)


@command_handler('/week', 'Show tasks due this week', 'Usage: /week', 'tasks')
async def week_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Show tasks due this week."""
    await _week_tasks_handler_internal(update, context)


@command_handler('/search', 'Enhanced search with basic and advanced modes',
    'Usage: /search <query> [--advanced] [--case-sensitive]', 'tasks')
@require_args(1, 3)
async def search_tasks_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Enhanced search with basic and advanced modes."""
    await _search_tasks_handler_internal(update, context)
