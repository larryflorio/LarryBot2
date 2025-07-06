from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.storage.db import get_session
from larrybot.storage.client_repository import ClientRepository
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.client import Client
from larrybot.models.task import Task
from larrybot.core.event_utils import emit_client_event, emit_task_event
from larrybot.utils.ux_helpers import KeyboardBuilder, MessageFormatter
from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
from typing import Optional
_client_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    global _client_event_bus
    _client_event_bus = event_bus
    command_registry.register('/addclient', addclient_handler)
    command_registry.register('/removeclient', removeclient_handler)
    command_registry.register('/allclients', allclients_handler)
    command_registry.register('/assign', assign_handler)
    command_registry.register('/unassign', unassign_handler)
    command_registry.register('/client', client_handler)
    command_registry.register('/clientanalytics', clientanalytics_handler)


async def addclient_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Add a new client with enhanced UX."""
    if not context.args:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Missing client name',
            'Usage: /addclient <name>'), parse_mode='MarkdownV2')
        return
    name = ' '.join(context.args).strip()
    if not name:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Client name cannot be empty',
            'Please provide a valid client name.'), parse_mode='MarkdownV2')
        return
    with next(get_session()) as session:
        repo = ClientRepository(session)
        if repo.get_client_by_name(name):
            await update.message.reply_text(MessageFormatter.
                format_error_message(f"Client '{name}' already exists",
                'Use a different name or check existing clients with /allclients'
                ), parse_mode='MarkdownV2')
            return
        client = repo.add_client(name)
        emit_client_event(_client_event_bus, 'client_created', client)
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"Client '{name}' added successfully!",
            {'Client ID': client.id, 'Client Name': client.name,
            'Created At': client.created_at.strftime('%Y-%m-%d %H:%M') if
            client.created_at else 'N/A'}), parse_mode='MarkdownV2')


async def removeclient_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Remove a client with confirmation dialog."""
    if not context.args:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Missing client name',
            'Usage: /removeclient <name> [confirm]'), parse_mode='MarkdownV2')
        return
    name = context.args[0]
    confirm = len(context.args) > 1 and context.args[1].lower() == 'confirm'
    with next(get_session()) as session:
        repo = ClientRepository(session)
        task_repo = TaskRepository(session)
        client = repo.get_client_by_name(name)
        if not client:
            await update.message.reply_text(MessageFormatter.
                format_error_message(f"Client '{name}' not found",
                'Check the client name or use /allclients to see available clients'
                ), parse_mode='MarkdownV2')
            return
        tasks = task_repo.get_tasks_by_client(name)
        if tasks and not confirm:
            keyboard = KeyboardBuilder.build_confirmation_keyboard(
                'client_delete', client.id)
            await update.message.reply_text(
                f"""🗑️ **Confirm Client Deletion**

**Client**: {MessageFormatter.escape_markdown(name)}
**Tasks**: {len(tasks)} assigned tasks

⚠️ **Warning**: This will unassign all {len(tasks)} tasks from this client\\.

Are you sure you want to delete this client?"""
                , reply_markup=keyboard, parse_mode='MarkdownV2')
            return
        for task in tasks:
            task_repo.unassign_task(task.id)
        repo.remove_client(name)
        emit_client_event(_client_event_bus, 'client_removed', client)
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"Client '{name}' removed successfully!",
            {'Unassigned Tasks': len(tasks), 'Client ID': client.id}),
            parse_mode='MarkdownV2')


async def allclients_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """List all clients with enhanced formatting and per-client action buttons."""
    with next(get_session()) as session:
        repo = ClientRepository(session)
        clients = repo.list_all_clients()
        if not clients:
            await update.message.reply_text(MessageFormatter.
                format_error_message('No clients found',
                'Use /addclient to create your first client'), parse_mode=
                'MarkdownV2')
            return
        message = f'👥 **All Clients** \\({len(clients)} found\\)\n\n'
        keyboard_buttons = []
        for i, client in enumerate(clients, 1):
            task_repo = TaskRepository(session)
            tasks = task_repo.get_tasks_by_client(client.name)
            completed_tasks = sum(1 for t in tasks if t.done)
            if len(tasks) == 0:
                status_emoji = '⚪'
            elif completed_tasks == len(tasks):
                status_emoji = '🟢'
            elif completed_tasks > 0:
                status_emoji = '🟡'
            else:
                status_emoji = '🔴'
            message += f"""{i}\\. {status_emoji} **{MessageFormatter.escape_markdown(client.name)}** \\(ID: {client.id}\\)
"""
            message += (
                f'   📋 Tasks: {len(tasks)} \\({completed_tasks} completed\\)\n'
                )
            if client.created_at:
                message += (
                    f"   📅 Created: {client.created_at.strftime('%Y-%m-%d')}\n"
                    )
            message += '\n'
            keyboard_buttons.append([UnifiedButtonBuilder.create_button(
                text='👁️ View', callback_data=f'client_view:{client.id}',
                button_type=ButtonType.INFO), UnifiedButtonBuilder.
                create_button(text='✏️ Edit', callback_data=
                f'client_edit:{client.id}', button_type=ButtonType.INFO),
                UnifiedButtonBuilder.create_button(text='🗑️ Delete',
                callback_data=f'client_delete:{client.id}', button_type=ButtonType.DANGER), UnifiedButtonBuilder.create_button(text
                ='📊 Analytics', callback_data=
                f'client_analytics:{client.id}', button_type=ButtonType.SECONDARY)])
        keyboard_buttons.append([UnifiedButtonBuilder.create_button(text=
            '➕ Add Client', callback_data='client_add', button_type=ButtonType.PRIMARY), UnifiedButtonBuilder.create_button(text=
            '🔄 Refresh', callback_data='client_refresh', button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.create_button(text=
            '⬅️ Back', callback_data='nav_main', button_type=ButtonType.INFO)])
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        await update.message.reply_text(message, reply_markup=keyboard,
            parse_mode='MarkdownV2')


async def assign_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Assign a task to a client with enhanced UX."""
    if len(context.args) < 2 or not context.args[0].isdigit():
        await update.message.reply_text(MessageFormatter.
            format_error_message('Invalid arguments',
            'Usage: /assign <task_id> <client_name>'), parse_mode='MarkdownV2')
        return
    task_id = int(context.args[0])
    client_name = ' '.join(context.args[1:]).strip()
    with next(get_session()) as session:
        task_repo = TaskRepository(session)
        client_repo = ClientRepository(session)
        task = task_repo.get_task_by_id(task_id)
        if not task:
            await update.message.reply_text(MessageFormatter.
                format_error_message(f'Task ID {task_id} not found',
                'Check the task ID or use /tasks to see available tasks'),
                parse_mode='MarkdownV2')
            return
        client = client_repo.get_client_by_name(client_name)
        if not client:
            await update.message.reply_text(MessageFormatter.
                format_error_message(f"Client '{client_name}' not found",
                'Check the client name or use /allclients to see available clients'
                ), parse_mode='MarkdownV2')
            return
        if task.client_id:
            current_client = client_repo.get_client_by_id(task.client_id)
            current_client_name = (current_client.name if current_client else
                'Unknown')
            await update.message.reply_text(MessageFormatter.
                format_error_message(f'Task {task_id} is already assigned',
                f"""Currently assigned to: {current_client_name}
Use /unassign first to change assignment"""
                ), parse_mode='MarkdownV2')
            return
        task_repo.assign_task_to_client(task_id, client_name)
        emit_task_event(_client_event_bus, 'task_assigned', {'task': task,
            'client': client})
        await update.message.reply_text(MessageFormatter.
            format_success_message(f'Task assigned successfully!', {
            'Task ID': task_id, 'Task': task.description, 'Client':
            client_name, 'Client ID': client.id}), parse_mode='MarkdownV2')


async def unassign_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Unassign a task from a client with enhanced UX."""
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(MessageFormatter.
            format_error_message('Invalid task ID',
            'Usage: /unassign <task_id>'), parse_mode='MarkdownV2')
        return
    task_id = int(context.args[0])
    with next(get_session()) as session:
        task_repo = TaskRepository(session)
        client_repo = ClientRepository(session)
        task = task_repo.get_task_by_id(task_id)
        if not task:
            await update.message.reply_text(MessageFormatter.
                format_error_message(f'Task ID {task_id} not found',
                'Check the task ID or use /tasks to see available tasks'),
                parse_mode='MarkdownV2')
            return
        if not task.client_id:
            await update.message.reply_text(MessageFormatter.
                format_error_message(f'Task {task_id} is not assigned',
                'This task is not assigned to any client'), parse_mode=
                'MarkdownV2')
            return
        current_client = client_repo.get_client_by_id(task.client_id)
        current_client_name = (current_client.name if current_client else
            'Unknown')
        task_repo.unassign_task(task_id)
        emit_task_event(_client_event_bus, 'task_unassigned', task)
        await update.message.reply_text(MessageFormatter.
            format_success_message(f'Task unassigned successfully!', {
            'Task ID': task_id, 'Task': task.description, 'Previous Client':
            current_client_name}), parse_mode='MarkdownV2')


async def client_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Show detailed client information with inline keyboards."""
    if not context.args:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Missing client name',
            'Usage: /client <client_name>'), parse_mode='MarkdownV2')
        return
    client_name = ' '.join(context.args).strip()
    with next(get_session()) as session:
        client_repo = ClientRepository(session)
        task_repo = TaskRepository(session)
        client = client_repo.get_client_by_name(client_name)
        if not client:
            await update.message.reply_text(MessageFormatter.
                format_error_message(f"Client '{client_name}' not found",
                'Check the client name or use /allclients to see available clients'
                ), parse_mode='MarkdownV2')
            return
        tasks = task_repo.get_tasks_by_client(client_name)
        completed_tasks = sum(1 for t in tasks if t.done)
        pending_tasks = len(tasks) - completed_tasks
        completion_rate = completed_tasks / len(tasks) * 100 if tasks else 0
        message = f'👥 **Client Details**\n\n'
        message += (
            f'**Name**: {MessageFormatter.escape_markdown(client.name)}\n')
        message += f'**ID**: {client.id}\n'
        if client.created_at:
            message += (
                f"**Created**: {client.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                )
        message += f'\n📊 **Task Statistics**\n'
        message += f'• Total Tasks: {len(tasks)}\n'
        message += f'• Completed: {completed_tasks} ✅\n'
        message += f'• Pending: {pending_tasks} ⏳\n'
        message += f'• Completion Rate: {completion_rate:.1f}%\n\n'
        if tasks:
            message += f'📋 **Assigned Tasks**\n'
            for i, task in enumerate(tasks[:5], 1):
                status_emoji = '✅' if task.done else '⏳'
                priority_emoji = {'Low': '🟢', 'Medium': '🟡', 'High': '🟠',
                    'Critical': '🔴'}.get(task.priority, '⚪')
                message += f"""{i}\\. {status_emoji} {priority_emoji} **{MessageFormatter.escape_markdown(task.description)}** \\(ID: {task.id}\\)
"""
                message += f'   {task.status} \\| {task.priority}\n'
                if task.due_date:
                    message += (
                        f"   📅 Due: {task.due_date.strftime('%Y-%m-%d')}\n")
                message += '\n'
            if len(tasks) > 5:
                message += f'*... and {len(tasks) - 5} more tasks*\n\n'
        else:
            message += f'📋 **No tasks assigned**\n\n'
        keyboard = KeyboardBuilder.build_client_detail_keyboard(client.id,
            client.name)
        await update.message.reply_text(message, reply_markup=keyboard,
            parse_mode='MarkdownV2')


async def clientanalytics_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Show comprehensive client analytics with enhanced formatting."""
    with next(get_session()) as session:
        client_repo = ClientRepository(session)
        task_repo = TaskRepository(session)
        clients = client_repo.list_all_clients()
        if not clients:
            await update.message.reply_text(MessageFormatter.
                format_error_message('No clients to analyze',
                'Add some clients first with /addclient'), parse_mode=
                'MarkdownV2')
            return
        message = f'📊 **Client Analytics Report**\n\n'
        total_tasks = 0
        total_completed = 0
        client_stats = []
        for client in clients:
            tasks = task_repo.get_tasks_by_client(client.name)
            completed = sum(1 for t in tasks if t.done)
            pending = len(tasks) - completed
            completion_rate = completed / len(tasks) * 100 if tasks else 0
            total_tasks += len(tasks)
            total_completed += completed
            client_stats.append({'name': client.name, 'total': len(tasks),
                'completed': completed, 'pending': pending, 'rate':
                completion_rate})
        client_stats.sort(key=lambda x: x['rate'], reverse=True)
        overall_rate = (total_completed / total_tasks * 100 if total_tasks else
            0)
        message += f'📈 **Overall Statistics**\n'
        message += f'• Total Clients: {len(clients)}\n'
        message += f'• Total Tasks: {total_tasks}\n'
        message += f'• Completed: {total_completed} ✅\n'
        message += f'• Pending: {total_tasks - total_completed} ⏳\n'
        message += f'• Overall Completion Rate: {overall_rate:.1f}%\n\n'
        message += f'🏆 **Client Rankings**\n'
        for i, stats in enumerate(client_stats, 1):
            if stats['rate'] >= 80:
                performance = '🥇'
            elif stats['rate'] >= 60:
                performance = '🥈'
            elif stats['rate'] >= 40:
                performance = '🥉'
            elif stats['rate'] > 0:
                performance = '📈'
            else:
                performance = '📊'
            message += f"""{i}\\. {performance} **{MessageFormatter.escape_markdown(stats['name'])}**
"""
            message += f"""   📋 {stats['total']} tasks \\({stats['completed']} ✅, {stats['pending']} ⏳\\)
"""
            message += f"   📊 {stats['rate']:.1f}% completion rate\n\n"
        message += f'💡 **Insights**\n'
        if client_stats:
            best_client = client_stats[0]
            worst_client = client_stats[-1]
            if best_client['rate'] > 0:
                message += f"""• 🏆 **Top Performer**: {MessageFormatter.escape_markdown(best_client['name'])} \\({best_client['rate']:.1f}%\\)
"""
            if worst_client['rate'] < 100 and worst_client['total'] > 0:
                message += f"""• 📉 **Needs Attention**: {MessageFormatter.escape_markdown(worst_client['name'])} \\({worst_client['rate']:.1f}%\\)
"""
            if overall_rate < 50:
                message += f'• ⚠️ **Overall performance is below 50%**\n'
            elif overall_rate >= 80:
                message += f'• 🎉 **Excellent overall performance!**\n'
        await update.message.reply_text(message, parse_mode='MarkdownV2')
