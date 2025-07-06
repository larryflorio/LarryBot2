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
from larrybot.core.event_utils import emit_task_event
from .utils import get_task_service, validate_task_id
_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    """Register subtasks and dependencies commands."""
    global _event_bus
    _event_bus = event_bus
    command_registry.register('/subtask', subtask_handler)
    command_registry.register('/depend', dependency_handler)


async def _subtask_handler_internal(update: Update, context: ContextTypes.
    DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of subtask handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, parent_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg,
            'Usage: /subtask <parent_id> <description>'), parse_mode=
            'MarkdownV2')
        return
    description = context.args[1]
    result = await task_service.add_subtask(parent_id, description)
    if result['success']:
        subtask = result['data']
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"✅ {result['message']}", {'Parent Task':
            parent_id, 'Subtask ID': subtask['id'], 'Description': subtask[
            'description']}), parse_mode='MarkdownV2')
        emit_task_event(_event_bus, 'subtask_created', subtask)
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the parent task ID and try again.'), parse_mode='MarkdownV2'
            )


async def _dependency_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of dependency handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg,
            'Usage: /depend <task_id> <dependency_id>'), parse_mode=
            'MarkdownV2')
        return
    is_valid, dependency_id, error_msg = validate_task_id(context.args[1])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg,
            'Usage: /depend <task_id> <dependency_id>'), parse_mode=
            'MarkdownV2')
        return
    result = await task_service.add_task_dependency(task_id, dependency_id)
    if result['success']:
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"✅ {result['message']}", {'Task ID':
            task_id, 'Dependency ID': dependency_id}), parse_mode='MarkdownV2')
        emit_task_event(_event_bus, 'dependency_added', {'task_id': task_id,
            'dependency_id': dependency_id})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task IDs and try again.'), parse_mode='MarkdownV2')


@command_handler('/subtask', 'Create subtask',
    'Usage: /subtask <parent_id> <description>', 'tasks')
@require_args(2, 2)
async def subtask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Create a subtask."""
    await _subtask_handler_internal(update, context)


@command_handler('/depend', 'Add task dependency',
    'Usage: /depend <task_id> <dependency_id>', 'tasks')
@require_args(2, 2)
async def dependency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Add task dependency."""
    await _dependency_handler_internal(update, context)
