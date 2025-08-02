from telegram import Update, Document, PhotoSize, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.storage.db import get_session
from larrybot.storage.task_attachment_repository import TaskAttachmentRepository
from larrybot.storage.task_repository import TaskRepository
from larrybot.services.task_attachment_service import TaskAttachmentService
from larrybot.utils.decorators import command_handler, require_args
from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
from larrybot.core.event_utils import emit_task_event
from typing import Optional, Tuple
import io
_attachment_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    """Register file attachment commands with the command registry."""
    global _attachment_event_bus
    _attachment_event_bus = event_bus
    command_registry.register('/attach', attach_file_handler)
    command_registry.register('/attachments', list_attachments_handler)
    command_registry.register('/remove_attachment', remove_attachment_handler)
    command_registry.register('/attachment_description',
        update_description_handler)
    command_registry.register('/attachment_stats', attachment_stats_handler)


def _get_attachment_service() ->TaskAttachmentService:
    """Get attachment service instance."""
    session = next(get_session())
    task_attachment_repository = TaskAttachmentRepository(session)
    task_repository = TaskRepository(session)
    return TaskAttachmentService(task_attachment_repository, task_repository)


@command_handler('/attach', 'Attach file to task',
    'Usage: /attach <task_id> [description]', 'attachments')
@require_args(1, 2)
async def attach_file_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Handle file attachment via command with file upload."""
    try:
        if not update.message.document and not update.message.photo:
            await update.message.reply_text(MessageFormatter.
                format_info_message('📎 File Attachment Required', {
                'Instructions': 'Please attach a file to this message',
                'Usage':
                'Send a file, then reply with: /attach <task_id> [description]'
                , 'Supported Formats':
                'All file types are supported', 'Max Size':
                '10MB'}), parse_mode='MarkdownV2')
            return
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(MessageFormatter.
                format_error_message('Invalid task ID',
                'Usage: /attach <task_id> [description]'), parse_mode=
                'MarkdownV2')
            return
        task_id = int(context.args[0])
        description = context.args[1] if len(context.args) > 1 else None
        file_data, original_filename = await _extract_file_data(update.message)
        if not file_data:
            await update.message.reply_text(MessageFormatter.
                format_error_message('Failed to extract file data',
                'Please try again with a different file.'), parse_mode=
                'MarkdownV2')
            return
        attachment_service = _get_attachment_service()
        result = await attachment_service.attach_file(task_id=task_id,
            file_data=file_data, original_filename=original_filename,
            description=description)
        if result['success']:
            attachment_data = result['data']
            message = MessageFormatter.format_success_message(
                f'📎 File attached successfully!', {'File': attachment_data[
                'filename'], 'Task': f'#{task_id}', 'Size':
                f"{attachment_data['size']:,} bytes", 'Type':
                attachment_data['mime_type'], 'ID': str(attachment_data['id'])}
                )
            keyboard = KeyboardBuilder.build_attachment_keyboard(
                attachment_data['id'], task_id)
            await update.message.reply_text(message, reply_markup=keyboard,
                parse_mode='MarkdownV2')
            emit_task_event(_attachment_event_bus, 'file_attached', {
                'task_id': task_id, 'attachment_id': attachment_data['id'],
                'filename': attachment_data['filename']})
        else:
            await update.message.reply_text(MessageFormatter.
                format_error_message(result['error'],
                'Please check the task ID and file format.'), parse_mode=
                'MarkdownV2')
    except Exception as e:
        await update.message.reply_text(MessageFormatter.
            format_error_message(f'Unexpected error: {str(e)}',
            'Please try again or contact support.'), parse_mode='MarkdownV2')


@command_handler('/attachments', 'List task attachments',
    'Usage: /attachments <task_id>', 'attachments')
@require_args(1, 1)
async def list_attachments_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """List all attachments for a task with rich formatting."""
    try:
        if not context.args[0].isdigit():
            await update.message.reply_text(MessageFormatter.
                format_error_message('Invalid task ID',
                'Usage: /attachments <task_id>'), parse_mode='MarkdownV2')
            return
        task_id = int(context.args[0])
        attachment_service = _get_attachment_service()
        result = await attachment_service.get_task_attachments(task_id)
        if result['success']:
            data = result['data']
            attachments = data['attachments']
            stats = data['stats']
            if not attachments:
                await update.message.reply_text(MessageFormatter.
                    format_info_message(f'📎 No Attachments Found', {'Task':
                    f'#{task_id}', 'Status': 'No files attached'}),
                    parse_mode='MarkdownV2')
                return
            message = f'📎 **Attachments for Task #{task_id}**\n\n'
            message += f'📊 **Summary**\n'
            message += f"• Total Files: {stats['count']}\n"
            message += f"""• Total Size: {stats['total_size']:,} bytes \\({stats['total_size_mb']:.2f} MB\\)
"""
            message += f"• Average Size: {stats['avg_size']:,} bytes\n\n"
            if stats.get('type_distribution'):
                message += f'📄 **File Types**\n'
                for file_type, count in stats['type_distribution'].items():
                    message += f'• {file_type}: {count} files\n'
                message += '\n'
            message += f'📋 **Files**\n'
            for i, att in enumerate(attachments[:5], 1):
                message += (
                    f"{i}\\. **{MessageFormatter.escape_markdown(att['filename'])}**\n"
                    )
                message += (
                    f"   📏 {att['size']:,} bytes \\| 📅 {att['created_at'][:19]}\n"
                    )
                if att['description']:
                    message += (
                        f"   📝 {MessageFormatter.escape_markdown(att['description'])}\n"
                        )
                message += '\n'
            if len(attachments) > 5:
                message += f'*... and {len(attachments) - 5} more files*\n\n'
            keyboard = KeyboardBuilder.build_attachments_list_keyboard(task_id,
                len(attachments))
            await update.message.reply_text(message, reply_markup=keyboard,
                parse_mode='MarkdownV2')
        else:
            await update.message.reply_text(MessageFormatter.
                format_error_message(result['error'],
                'Please check the task ID.'), parse_mode='MarkdownV2')
    except Exception as e:
        await update.message.reply_text(MessageFormatter.
            format_error_message(f'Unexpected error: {str(e)}',
            'Please try again or contact support.'), parse_mode='MarkdownV2')


@command_handler('/remove_attachment', 'Remove attachment',
    'Usage: /remove_attachment <attachment_id>', 'attachments')
@require_args(1, 1)
async def remove_attachment_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Remove an attachment with confirmation."""
    try:
        if not context.args[0].isdigit():
            await update.message.reply_text(MessageFormatter.
                format_error_message('Invalid attachment ID',
                'Usage: /remove_attachment <attachment_id>'), parse_mode=
                'MarkdownV2')
            return
        attachment_id = int(context.args[0])
        attachment_service = _get_attachment_service()
        result = await attachment_service.remove_attachment(attachment_id)
        if result['success']:
            await update.message.reply_text(MessageFormatter.
                format_success_message(
                f'🗑️ Attachment removed successfully!', {'File': result[
                'data']['filename'], 'ID': str(attachment_id), 'Size':
                f"{result['data']['size']:,} bytes"}), parse_mode='MarkdownV2')
        else:
            await update.message.reply_text(MessageFormatter.
                format_error_message(result['error'],
                'Please check the attachment ID.'), parse_mode='MarkdownV2')
    except Exception as e:
        await update.message.reply_text(MessageFormatter.
            format_error_message(f'Unexpected error: {str(e)}',
            'Please try again or contact support.'), parse_mode='MarkdownV2')


@command_handler('/attachment_description', 'Update attachment description',
    'Usage: /attachment_description <attachment_id> <description>',
    'attachments')
@require_args(2, 2)
async def update_description_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Update attachment description."""
    try:
        if not context.args[0].isdigit():
            await update.message.reply_text(MessageFormatter.
                format_error_message('Invalid attachment ID',
                'Usage: /attachment_description <attachment_id> <description>'
                ), parse_mode='MarkdownV2')
            return
        attachment_id = int(context.args[0])
        description = context.args[1]
        attachment_service = _get_attachment_service()
        result = await attachment_service.update_attachment_description(
            attachment_id, description)
        if result['success']:
            await update.message.reply_text(MessageFormatter.
                format_success_message(
                f'✅ Description updated successfully!', {'File': result[
                'data']['filename'], 'Description': result['data'][
                'description'], 'ID': str(attachment_id)}), parse_mode=
                'MarkdownV2')
        else:
            await update.message.reply_text(MessageFormatter.
                format_error_message(result['error'],
                'Please check the attachment ID and description.'),
                parse_mode='MarkdownV2')
    except Exception as e:
        await update.message.reply_text(MessageFormatter.
            format_error_message(f'Unexpected error: {str(e)}',
            'Please try again or contact support.'), parse_mode='MarkdownV2')


@command_handler('/attachment_stats', 'Show attachment statistics',
    'Usage: /attachment_stats [task_id]', 'attachments')
async def attachment_stats_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Show comprehensive attachment statistics."""
    try:
        task_id = None
        if context.args and context.args[0].isdigit():
            task_id = int(context.args[0])
        attachment_service = _get_attachment_service()
        result = await attachment_service.get_attachment_statistics(task_id)
        if result['success']:
            stats = result['data']
            message = f'📊 **Attachment Statistics**\n\n'
            if task_id:
                message += f'📋 **Task #{task_id}**\n'
            else:
                message += f'📋 **All Tasks**\n'
            message += f'📈 **Overview**\n'
            message += f"• Total Attachments: {stats['total_attachments']}\n"
            message += f"""• Total Size: {stats['total_size']:,} bytes \\({stats['total_size_mb']:.2f} MB\\)
"""
            message += f"• Average Size: {stats['avg_size']:,} bytes\n"
            message += (
                f"• Largest File: {stats['largest_file_size']:,} bytes\n\n")
            if stats.get('type_distribution'):
                message += f'📄 **File Type Distribution**\n'
                for file_type, count in stats['type_distribution'].items():
                    percentage = count / stats['total_attachments'] * 100
                    message += (
                        f'• {file_type}: {count} \\({percentage:.1f}%\\)\n')
                message += '\n'
            if stats.get('size_distribution'):
                message += f'📏 **Size Distribution**\n'
                for size_range, count in stats['size_distribution'].items():
                    message += f'• {size_range}: {count} files\n'
                message += '\n'
            if stats.get('recent_activity'):
                message += f'🕒 **Recent Activity**\n'
                for activity in stats['recent_activity'][:5]:
                    message += f"""• {activity['action']}: {activity['filename']} \\({activity['date']}\\)
"""
            await update.message.reply_text(message, parse_mode='MarkdownV2')
        else:
            await update.message.reply_text(MessageFormatter.
                format_error_message(result['error'],
                'Unable to generate statistics.'), parse_mode='MarkdownV2')
    except Exception as e:
        await update.message.reply_text(MessageFormatter.
            format_error_message(f'Unexpected error: {str(e)}',
            'Please try again or contact support.'), parse_mode='MarkdownV2')


async def _extract_file_data(message) ->Tuple[Optional[bytes], Optional[str]]:
    """Extract file data from Telegram message."""
    try:
        if message.document:
            file = await message.document.get_file()
            file_data = await file.download_as_bytearray()
            return bytes(file_data), message.document.file_name
        elif message.photo:
            largest_photo = max(message.photo, key=lambda p: p.file_size)
            file = await largest_photo.get_file()
            file_data = await file.download_as_bytearray()
            return bytes(file_data), f'photo_{largest_photo.file_id}.jpg'
        else:
            return None, None
    except Exception as e:
        print(f'Error extracting file data: {e}')
        return None, None
