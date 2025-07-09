"""
Advanced filtering module for the Advanced Tasks plugin.

This module handles advanced filtering operations like multi-tag filtering,
time range filtering, and priority range filtering.
"""
from telegram import Update
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.utils.decorators import command_handler, require_args
from larrybot.utils.ux_helpers import MessageFormatter
from larrybot.core.event_utils import emit_task_event
from larrybot.utils.datetime_utils import parse_date_string

_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    """Register advanced filtering commands."""
    global _event_bus
    _event_bus = event_bus
    command_registry.register('/filter_advanced', filter_advanced_handler)
    command_registry.register('/tags_multi', tags_multi_handler)
    command_registry.register('/time_range', time_range_handler)
    command_registry.register('/priority_range', priority_range_handler)


async def _filter_advanced_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of filter advanced handler."""
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
    if len(context.args) > 3:
        filters['sort_by'] = context.args[3]
    if len(context.args) > 4:
        filters['sort_order'] = context.args[4]
    result = await task_service.get_tasks_with_filters(filters)
    if result['success']:
        tasks = result['data']
        if not tasks:
            await update.message.reply_text(MessageFormatter.
                format_info_message('🔍 Advanced Filter Results', {'Status':
                'No tasks found matching criteria'}), parse_mode='MarkdownV2')
        else:
            message = MessageFormatter.format_task_list(tasks, 'Advanced Filter Results')
            await update.message.reply_text(message, parse_mode='MarkdownV2')
            emit_task_event(_event_bus, 'advanced_filter_applied', {
                'filters': filters, 'count': len(tasks)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check your filter criteria and try again.'), parse_mode=
            'MarkdownV2')


async def _tags_multi_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of tags multi handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    tags = [tag.strip() for tag in context.args[0].split(',') if tag.strip()]
    if not tags:
        await update.message.reply_text(MessageFormatter.
            format_error_message('No tags provided',
            'Provide at least one tag'), parse_mode='MarkdownV2')
        return
    match_type = 'any'
    if len(context.args) > 1:
        match_type = context.args[1].lower()
        if match_type not in ['all', 'any']:
            await update.message.reply_text(MessageFormatter.
                format_error_message('Invalid match type',
                "Use 'all' or 'any'"), parse_mode='MarkdownV2')
            return
    filters = {'tags': tags, 'tag_match_type': match_type}
    result = await task_service.get_tasks_with_filters(filters)
    if result['success']:
        tasks = result['data']
        if not tasks:
            await update.message.reply_text(MessageFormatter.
                format_info_message(f'🏷️ Multi-Tag Filter ({match_type})',
                {'Tags': ', '.join(tags), 'Status': 'No tasks found'}),
                parse_mode='MarkdownV2')
        else:
            message = MessageFormatter.format_task_list(tasks, f'Multi-Tag Filter ({match_type})')
            await update.message.reply_text(message, parse_mode='MarkdownV2')
            emit_task_event(_event_bus, 'multi_tag_filter_applied', {'tags':
                tags, 'match_type': match_type, 'count': len(tasks)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check your tags and try again.'), parse_mode='MarkdownV2')


async def _time_range_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of time range handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    try:
        start_date = parse_date_string(context.args[0], '%Y-%m-%d')
        end_date = parse_date_string(context.args[1], '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Invalid date format',
            'Use YYYY-MM-DD format for dates'), parse_mode='MarkdownV2')
        return
    include_completed = False
    if len(context.args) > 2:
        include_completed = context.args[2].lower() in ['true', 'yes', '1',
            'include']
    filters = {'start_date': start_date, 'end_date': end_date,
        'include_completed': include_completed}
    result = await task_service.get_tasks_with_filters(filters)
    if result['success']:
        tasks = result['data']
        if not tasks:
            await update.message.reply_text(MessageFormatter.
                format_info_message('⏰ Time Range Filter', {'Period':
                f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                , 'Include Completed': 'Yes' if include_completed else 'No',
                'Status': 'No tasks found'}), parse_mode='MarkdownV2')
        else:
            message = MessageFormatter.format_task_list(tasks, 'Time Range Filter')
            await update.message.reply_text(message, parse_mode='MarkdownV2')
            emit_task_event(_event_bus, 'time_range_filter_applied', {
                'start_date': start_date.isoformat(), 'end_date': end_date.
                isoformat(), 'include_completed': include_completed,
                'count': len(tasks)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check your date range and try again.'), parse_mode='MarkdownV2')


async def _priority_range_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of priority range handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    try:
        min_priority = context.args[0]
        max_priority = context.args[1]
    except (IndexError, ValueError):
        await update.message.reply_text(MessageFormatter.
            format_error_message('Invalid priority values',
            'Provide valid priority values (Low, Medium, High, Critical)'),
            parse_mode='MarkdownV2')
        return
    valid_priorities = ['Low', 'Medium', 'High', 'Critical']
    if (min_priority not in valid_priorities or max_priority not in
        valid_priorities):
        await update.message.reply_text(MessageFormatter.
            format_error_message('Invalid priority values',
            'Use: Low, Medium, High, Critical'), parse_mode='MarkdownV2')
        return
    filters = {'min_priority': min_priority, 'max_priority': max_priority}
    result = await task_service.get_tasks_with_filters(filters)
    if result['success']:
        tasks = result['data']
        if not tasks:
            await update.message.reply_text(MessageFormatter.
                format_info_message('🎯 Priority Range Filter', {'Range':
                f'{min_priority} to {max_priority}', 'Status':
                'No tasks found'}), parse_mode='MarkdownV2')
        else:
            message = MessageFormatter.format_task_list(tasks, 'Priority Range Filter')
            await update.message.reply_text(message, parse_mode='MarkdownV2')
            emit_task_event(_event_bus, 'priority_range_filter_applied', {
                'min_priority': min_priority, 'max_priority': max_priority,
                'count': len(tasks)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check your priority range and try again.'), parse_mode=
            'MarkdownV2')


@command_handler('/filter_advanced', 'Advanced filtering',
    'Usage: /filter_advanced [status] [priority] [category] [sort_by] [sort_order]'
    , 'tasks')
async def filter_advanced_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Advanced filtering."""
    await _filter_advanced_handler_internal(update, context)


@command_handler('/tags_multi', 'Multi-tag filtering',
    'Usage: /tags_multi <tag1,tag2,tag3> [all|any]', 'tasks')
@require_args(1, 2)
async def tags_multi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Multi-tag filtering."""
    await _tags_multi_handler_internal(update, context)


@command_handler('/time_range', 'Time range filtering',
    'Usage: /time_range <start_date> <end_date> [include_completed]', 'tasks')
@require_args(2, 3)
async def time_range_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Time range filtering."""
    await _time_range_handler_internal(update, context)


@command_handler('/priority_range', 'Priority range filtering',
    'Usage: /priority_range <min_priority> <max_priority>', 'tasks')
@require_args(2, 2)
async def priority_range_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Priority range filtering."""
    await _priority_range_handler_internal(update, context)
