"""
Time tracking module for the Advanced Tasks plugin.

This module handles time tracking functionality including:
- Starting/stopping time tracking
- Manual time entry
- Time summaries
"""
from telegram import Update
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.utils.decorators import command_handler, require_args
from larrybot.utils.ux_helpers import MessageFormatter
from .utils import get_task_service, validate_task_id, format_duration
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    """Register time tracking commands."""
    global _event_bus
    _event_bus = event_bus
    command_registry.register('/time_start', start_time_tracking_handler)
    command_registry.register('/time_stop', stop_time_tracking_handler)
    command_registry.register('/time_entry', time_entry_handler)
    command_registry.register('/time_summary', time_summary_handler)


async def _start_time_tracking_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of start time tracking handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg, 'Usage: /time_start <task_id>'),
            parse_mode='MarkdownV2')
        return
    result = await task_service.start_time_tracking(task_id)
    if result['success']:
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"⏱️ {result['message']}", {'Task ID':
            task_id}), parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task ID and try again.'), parse_mode='MarkdownV2')


async def _stop_time_tracking_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of stop time tracking handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg, 'Usage: /time_stop <task_id>'),
            parse_mode='MarkdownV2')
        return
    result = await task_service.stop_time_tracking(task_id)
    if result['success']:
        # Get session duration in minutes and hours
        duration_hours = result.get('duration_hours', 0)
        total_minutes = int(round(duration_hours * 60))
        if total_minutes < 1 and duration_hours > 0:
            session_str = '<1m (0.00h)'
        else:
            h, m = divmod(total_minutes, 60)
            session_str = (f'{h}h {m}m' if h else f'{m}m') + f' ({duration_hours:.2f}h)'
        # Get total tracked time for the task
        summary_result = await task_service.get_task_time_summary(task_id)
        if summary_result.get('success'):
            total_hours = summary_result['data'].get('actual_hours', 0)
            total_total_minutes = int(round(total_hours * 60))
            if total_total_minutes < 1 and total_hours > 0:
                total_str = '<1m (0.00h)'
            else:
                h, m = divmod(total_total_minutes, 60)
                total_str = (f'{h}h {m}m' if h else f'{m}m') + f' ({total_hours:.2f}h)'
        else:
            total_str = 'N/A'
        # Escape all dynamic content for MarkdownV2
        esc = MessageFormatter.escape_markdown
        esc_task_id = esc(str(task_id))
        esc_session_str = esc(session_str)
        esc_total_str = esc(total_str)
        message = (
            f"✅ Time tracking stopped for Task \#{esc_task_id}\n\n"
            f"⏱️ Session duration: {esc_session_str}\n"
            f"🕒 Total tracked: {esc_total_str}"
        )
        # Add Time Summary action button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('⏱️ Time Summary', callback_data=f'task_time_stats:{task_id}')]
        ])
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task ID and try again.'), parse_mode='MarkdownV2')


async def _time_entry_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of time entry handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg,
            'Usage: /time_entry <task_id> <duration_minutes> [description]'
            ), parse_mode='MarkdownV2')
        return
    try:
        duration_minutes = int(context.args[1])
        if duration_minutes <= 0:
            raise ValueError('Duration must be positive')
    except ValueError:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Invalid duration',
            'Duration must be a positive number of minutes'), parse_mode=
            'MarkdownV2')
        return
    description = context.args[2] if len(context.args) > 2 else None
    result = await task_service.add_manual_time_entry(task_id, duration_minutes,
        description)
    if result['success']:
        formatted_duration = format_duration(duration_minutes)
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"⏱️ {result['message']}", {'Task ID':
            task_id, 'Duration': formatted_duration, 'Description': 
            description or 'None'}), parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task ID and duration.'), parse_mode='MarkdownV2')


async def _time_summary_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of time summary handler."""
    if task_service is None:
        task_service = get_task_service()
    is_valid, task_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg,
            'Usage: /time_summary <task_id>'), parse_mode='MarkdownV2')
        return
    result = await task_service.get_task_time_summary(task_id)
    if result['success']:
        time_data = result['data']
        total_minutes = time_data.get('total_minutes', 0)
        entry_count = time_data.get('entry_count', 0)
        formatted_total = format_duration(total_minutes)
        await update.message.reply_text(MessageFormatter.
            format_success_message(f'⏱️ Time Summary for Task #{task_id}',
            {'Total Time': formatted_total, 'Entries': entry_count,
            'Average per Entry': format_duration(total_minutes //
            entry_count) if entry_count > 0 else '0m'}), parse_mode=
            'MarkdownV2')
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task ID and try again.'), parse_mode='MarkdownV2')


@command_handler('/time_start', 'Start time tracking for task',
    'Usage: /time_start <task_id>', 'tasks')
@require_args(1, 1)
async def start_time_tracking_handler(update: Update, context: ContextTypes
    .DEFAULT_TYPE) ->None:
    """Start time tracking for a task."""
    await _start_time_tracking_handler_internal(update, context)


@command_handler('/time_stop', 'Stop time tracking for task',
    'Usage: /time_stop <task_id>', 'tasks')
@require_args(1, 1)
async def stop_time_tracking_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Stop time tracking for a task."""
    await _stop_time_tracking_handler_internal(update, context)


@command_handler('/time_entry', 'Add manual time entry',
    'Usage: /time_entry <task_id> <duration_minutes> [description]', 'tasks')
@require_args(2, 3)
async def time_entry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Add manual time entry for a task."""
    await _time_entry_handler_internal(update, context)


@command_handler('/time_summary', 'Show time summary for task',
    'Usage: /time_summary <task_id>', 'tasks')
@require_args(1, 1)
async def time_summary_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Show time summary for a task."""
    await _time_summary_handler_internal(update, context)
