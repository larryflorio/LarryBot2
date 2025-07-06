"""
Tags and comments module for the Advanced Tasks plugin.

This module handles task tagging and comment management.
"""
from telegram import Update
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.utils.decorators import command_handler, require_args
from larrybot.utils.ux_helpers import MessageFormatter
from larrybot.core.event_utils import emit_task_event
from .utils import validate_task_id
_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    """Register tags and comments commands."""
    global _event_bus
    _event_bus = event_bus
    command_registry.register('/tags', tags_handler)
    command_registry.register('/comment', comment_handler)
    command_registry.register('/comments', comments_handler)


async def _tags_handler_internal(update: Update, context: ContextTypes.
    DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of tags handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    is_valid, task_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg,
            'Usage: /tags <task_id> <add|remove> <tag1,tag2,tag3>'),
            parse_mode='MarkdownV2')
        return
    action = context.args[1].lower()
    if action not in ['add', 'remove']:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Invalid action',
            "Action must be 'add' or 'remove'"), parse_mode='MarkdownV2')
        return
    tags = [tag.strip() for tag in context.args[2].split(',') if tag.strip()]
    if not tags:
        await update.message.reply_text(MessageFormatter.
            format_error_message('No tags provided',
            'Provide at least one tag'), parse_mode='MarkdownV2')
        return
    result = await task_service.add_tags(task_id, tags, action)
    if result['success']:
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"✅ {result['message']}", {'Task ID':
            task_id, 'Action': action.title(), 'Tags': ', '.join(tags)}),
            parse_mode='MarkdownV2')
        emit_task_event(_event_bus, 'tags_updated', {'task_id': task_id,
            'action': action, 'tags': tags})
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task ID and tags.'), parse_mode='MarkdownV2')


async def _comment_handler_internal(update: Update, context: ContextTypes.
    DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of comment handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    is_valid, task_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg,
            'Usage: /comment <task_id> <comment>'), parse_mode='MarkdownV2')
        return
    comment = context.args[1]
    result = await task_service.add_comment(task_id, comment)
    if result['success']:
        comment_data = result['data']
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"✅ {result['message']}", {'Task ID':
            task_id, 'Comment ID': comment_data['id'], 'Comment': comment[:
            50] + '...' if len(comment) > 50 else comment}), parse_mode=
            'MarkdownV2')
        emit_task_event(_event_bus, 'comment_added', comment_data)
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task ID and try again.'), parse_mode='MarkdownV2')


async def _comments_handler_internal(update: Update, context: ContextTypes.
    DEFAULT_TYPE, task_service=None) ->None:
    """Internal implementation of comments handler."""
    if task_service is None:
        from larrybot.plugins.advanced_tasks import get_task_service
        task_service = get_task_service()
    is_valid, task_id, error_msg = validate_task_id(context.args[0])
    if not is_valid:
        await update.message.reply_text(MessageFormatter.
            format_error_message(error_msg, 'Usage: /comments <task_id>'),
            parse_mode='MarkdownV2')
        return
    result = await task_service.get_comments(task_id)
    if result['success']:
        comments = result['data']
        if not comments:
            await update.message.reply_text(MessageFormatter.
                format_info_message(f'📝 Comments for Task #{task_id}', {
                'Status': 'No comments found'}), parse_mode='MarkdownV2')
        else:
            comment_list = []
            for i, comment in enumerate(comments[:10], 1):
                comment_list.append(f"{i}. {comment['content'][:100]}...")
            if len(comments) > 10:
                comment_list.append(
                    f'... and {len(comments) - 10} more comments')
            await update.message.reply_text(MessageFormatter.
                format_success_message(f'📝 Comments for Task #{task_id}', {
                'Total Comments': len(comments), 'Comments': '\n'.join(
                comment_list)}), parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(MessageFormatter.
            format_error_message(result['message'],
            'Check the task ID and try again.'), parse_mode='MarkdownV2')


@command_handler('/tags', 'Manage task tags',
    'Usage: /tags <task_id> <add|remove> <tag1,tag2,tag3>', 'tasks')
@require_args(3, 3)
async def tags_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Manage task tags."""
    await _tags_handler_internal(update, context)


@command_handler('/comment', 'Add comment to task',
    'Usage: /comment <task_id> <comment>', 'tasks')
@require_args(2, 2)
async def comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Add comment to task."""
    await _comment_handler_internal(update, context)


@command_handler('/comments', 'Show task comments',
    'Usage: /comments <task_id>', 'tasks')
@require_args(1, 1)
async def comments_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Show task comments."""
    await _comments_handler_internal(update, context)
