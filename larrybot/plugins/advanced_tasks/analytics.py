"""
Analytics module for the Advanced Tasks plugin.

This module handles task analytics and reporting functionality.
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
    """Register analytics commands."""
    global _event_bus
    _event_bus = event_bus
    command_registry.register('/analytics', analytics_handler)
    command_registry.register('/analytics_detailed', analytics_detailed_handler
        )
    command_registry.register('/suggest', suggest_priority_handler)
    command_registry.register('/productivity_report',
        productivity_report_handler)


async def _analytics_handler_internal(update: Update, context: ContextTypes
    .DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of analytics handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    level = 'basic'
    days = 30
    if len(context.args) > 0:
        level = context.args[0].lower()
    if len(context.args) > 1:
        try:
            days = int(context.args[1])
        except ValueError:
            await update.message.reply_text(MessageFormatter.
                format_error_message('Invalid days parameter',
                'Days must be a number'), parse_mode='MarkdownV2')
            return
    result = await task_service.get_advanced_task_analytics(days)
    if result['success']:
        analytics_data = result['data']
        await update.message.reply_text(MessageFormatter.
            format_success_message(f'📊 Analytics ({level.title()})',
            analytics_data), parse_mode='MarkdownV2')
        emit_task_event(_event_bus, 'analytics_viewed', {'level': level,
            'days': days, 'data': analytics_data})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Unable to generate analytics.'), parse_mode='MarkdownV2')


async def _analytics_detailed_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of analytics detailed handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    days = 30
    if len(context.args) > 0:
        try:
            days = int(context.args[0])
        except ValueError:
            await update.message.reply_text(MessageFormatter.
                format_error_message('Invalid days parameter',
                'Days must be a number'), parse_mode='MarkdownV2')
            return
    result = await task_service.get_task_analytics('detailed', days)
    if result['success']:
        analytics_data = result['data']
        await update.message.reply_text(MessageFormatter.
            format_success_message(f'📊 Detailed Analytics ({days} days)',
            analytics_data), parse_mode='MarkdownV2')
        emit_task_event(_event_bus, 'detailed_analytics_viewed', {'days':
            days, 'data': analytics_data})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Unable to generate detailed analytics.'), parse_mode='MarkdownV2')


async def _suggest_priority_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of suggest priority handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    description = context.args[0]
    result = await task_service.suggest_priority(description)
    if result['success']:
        suggestion_data = result['data']
        await update.message.reply_text(MessageFormatter.
            format_success_message('🎯 Priority Suggestion', {'Description':
            description[:50] + '...' if len(description) > 50 else
            description, 'Suggested Priority': suggestion_data['priority'],
            'Confidence': f"{suggestion_data['confidence']}%", 'Reasoning':
            suggestion_data['reasoning']}), parse_mode='MarkdownV2')
        emit_task_event(_event_bus, 'priority_suggested', {'description':
            description, 'suggestion': suggestion_data})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Unable to generate priority suggestion.'), parse_mode='MarkdownV2'
            )


async def _productivity_report_handler_internal(update: Update, context:
    ContextTypes.DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of productivity report handler."""
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
    result = await task_service.get_productivity_report(start_date, end_date)
    if result['success']:
        report_data = result['data']
        await update.message.reply_text(MessageFormatter.
            format_success_message(
            f"📈 Productivity Report ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
            , report_data), parse_mode='MarkdownV2')
        emit_task_event(_event_bus, 'productivity_report_generated', {
            'start_date': start_date.isoformat(), 'end_date': end_date.
            isoformat(), 'data': report_data})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Unable to generate productivity report.'), parse_mode='MarkdownV2'
            )


@command_handler('/analytics',
    'Unified analytics with multiple complexity levels',
    'Usage: /analytics [basic|detailed|advanced] [days]', 'tasks')
async def analytics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Unified analytics with multiple complexity levels."""
    await _analytics_handler_internal(update, context)


@command_handler('/analytics_detailed', 'Show detailed analytics',
    'Usage: /analytics_detailed [days]', 'tasks')
async def analytics_detailed_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Show detailed analytics."""
    await _analytics_detailed_handler_internal(update, context)


@command_handler('/suggest', 'Suggest task priority',
    'Usage: /suggest <description>', 'tasks')
@require_args(1, 1)
async def suggest_priority_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Suggest task priority."""
    await _suggest_priority_handler_internal(update, context)


@command_handler('/productivity_report', 'Productivity report',
    'Usage: /productivity_report <start_date> <end_date>', 'tasks')
@require_args(2, 2)
async def productivity_report_handler(update: Update, context: ContextTypes
    .DEFAULT_TYPE) ->None:
    """Productivity report."""
    await _productivity_report_handler_internal(update, context)
