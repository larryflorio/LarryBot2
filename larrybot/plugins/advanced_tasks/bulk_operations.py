"""
Bulk operations module for the Advanced Tasks plugin.

This module handles bulk task operations for efficient task management.
"""
from telegram import Update
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.utils.decorators import command_handler, require_args
from larrybot.utils.ux_helpers import MessageFormatter
from larrybot.core.event_utils import emit_task_event
from .utils import get_task_service, parse_task_ids
_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    """Register bulk operations commands."""
    global _event_bus
    _event_bus = event_bus
    command_registry.register('/bulk_status', bulk_status_handler)
    command_registry.register('/bulk_priority', bulk_priority_handler)
    command_registry.register('/bulk_assign', bulk_assign_handler)
    command_registry.register('/bulk_delete', bulk_delete_handler)
    command_registry.register('/bulk_operations', bulk_operations_handler)


async def _bulk_status_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of bulk status handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_ids, error_message = parse_task_ids(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Invalid task IDs',
            error_message), parse_mode='MarkdownV2')
        return
    status = context.args[1]
    result = await task_service.bulk_update_status(task_ids, status)
    if result['success']:
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"✅ {result['message']}", {
            'Tasks Updated': len(task_ids), 'New Status': status,
            'Task IDs': ', '.join(map(str, task_ids))}), parse_mode=
            'MarkdownV2')
        emit_task_event(_event_bus, 'bulk_status_updated', {'task_ids':
            task_ids, 'status': status, 'count': len(task_ids)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task IDs and status value.'), parse_mode='MarkdownV2')


async def _bulk_priority_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of bulk priority handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_ids, error_message = parse_task_ids(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Invalid task IDs',
            error_message), parse_mode='MarkdownV2')
        return
    priority = context.args[1]
    result = await task_service.bulk_update_priority(task_ids, priority)
    if result['success']:
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"✅ {result['message']}", {
            'Tasks Updated': len(task_ids), 'New Priority': priority,
            'Task IDs': ', '.join(map(str, task_ids))}), parse_mode=
            'MarkdownV2')
        emit_task_event(_event_bus, 'bulk_priority_updated', {'task_ids':
            task_ids, 'priority': priority, 'count': len(task_ids)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task IDs and priority value.'), parse_mode='MarkdownV2')


async def _bulk_assign_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of bulk assign handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_ids, error_message = parse_task_ids(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Invalid task IDs',
            error_message), parse_mode='MarkdownV2')
        return
    client_name = context.args[1]
    result = await task_service.bulk_assign_to_client(task_ids, client_name)
    if result['success']:
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"✅ {result['message']}", {
            'Tasks Assigned': len(task_ids), 'Client': client_name,
            'Task IDs': ', '.join(map(str, task_ids))}), parse_mode=
            'MarkdownV2')
        emit_task_event(_event_bus, 'bulk_tasks_assigned', {'task_ids':
            task_ids, 'client_name': client_name, 'count': len(task_ids)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task IDs and client name.'), parse_mode='MarkdownV2')


async def _bulk_delete_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of bulk delete handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_ids, error_message = parse_task_ids(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Invalid task IDs',
            error_message), parse_mode='MarkdownV2')
        return
    confirm = len(context.args) > 1 and context.args[1].lower() == 'confirm'
    if not confirm:
        await update.message.reply_text(MessageFormatter.
            format_warning_message('⚠️ Bulk Delete Confirmation Required',
            {'Tasks to Delete': len(task_ids), 'Task IDs': ', '.join(map(
            str, task_ids)), 'Action':
            "Add 'confirm' to proceed with deletion"}), parse_mode='MarkdownV2'
            )
        return
    result = await task_service.bulk_delete_tasks(task_ids)
    if result['success']:
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"✅ {result['message']}", {
            'Tasks Deleted': len(task_ids), 'Task IDs': ', '.join(map(str,
            task_ids))}), parse_mode='MarkdownV2')
        emit_task_event(_event_bus, 'bulk_tasks_deleted', {'task_ids':
            task_ids, 'count': len(task_ids)})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task IDs and try again.'), parse_mode='MarkdownV2')


async def _bulk_operations_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of bulk operations handler."""
    if task_service is None:
        task_service = get_task_service()
    await update.message.reply_text(MessageFormatter.format_info_message(
        '🔄 Bulk Operations Menu', {'Bulk Status':
        '/bulk_status <task_ids> <status>', 'Bulk Priority':
        '/bulk_priority <task_ids> <priority>', 'Bulk Assign':
        '/bulk_assign <task_ids> <client>', 'Bulk Delete':
        '/bulk_delete <task_ids> confirm', 'Note':
        'Use comma-separated task IDs (e.g., 1,2,3)'}), parse_mode='MarkdownV2'
        )
    emit_task_event(_event_bus, 'bulk_operations_menu_viewed', {})


@command_handler('/bulk_status', 'Bulk update task status',
    'Usage: /bulk_status <task_id1,task_id2,task_id3> <status>', 'tasks')
@require_args(2, 2)
async def bulk_status_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Bulk update task status."""
    await _bulk_status_handler_internal(update, context)


@command_handler('/bulk_priority', 'Bulk update task priority',
    'Usage: /bulk_priority <task_id1,task_id2,task_id3> <priority>', 'tasks')
@require_args(2, 2)
async def bulk_priority_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Bulk update task priority."""
    await _bulk_priority_handler_internal(update, context)


@command_handler('/bulk_assign', 'Bulk assign tasks to client',
    'Usage: /bulk_assign <task_id1,task_id2,task_id3> <client_name>', 'tasks')
@require_args(2, 2)
async def bulk_assign_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Bulk assign tasks to client."""
    await _bulk_assign_handler_internal(update, context)


@command_handler('/bulk_delete', 'Bulk delete tasks',
    'Usage: /bulk_delete <task_id1,task_id2,task_id3> [confirm]', 'tasks')
@require_args(1, 2)
async def bulk_delete_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Bulk delete tasks."""
    await _bulk_delete_handler_internal(update, context)


@command_handler('/bulk_operations', 'Bulk operations menu',
    'Usage: /bulk_operations', 'tasks')
async def bulk_operations_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Bulk operations menu."""
    await _bulk_operations_handler_internal(update, context)
