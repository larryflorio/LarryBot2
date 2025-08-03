from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.request import HTTPXRequest
from larrybot.config.loader import Config
from larrybot.core.command_registry import CommandRegistry
from larrybot.plugins.reminder import set_main_event_loop
from larrybot.utils.ux_helpers import MessageFormatter
from larrybot.core.enhanced_message_processor import EnhancedMessageProcessor
import asyncio
import logging
from larrybot.storage.db import get_optimized_session
from larrybot.storage.task_repository import TaskRepository
from larrybot.core.event_utils import emit_task_event
from datetime import datetime
from larrybot.storage.client_repository import ClientRepository
from larrybot.core.dependency_injection import ServiceLocator
from larrybot.nlp.intent_recognizer import IntentRecognizer
from larrybot.nlp.entity_extractor import EntityExtractor
from larrybot.nlp.sentiment_analyzer import SentimentAnalyzer
from larrybot.nlp.enhanced_narrative_processor import EnhancedNarrativeProcessor, TaskCreationState, ContextType
from larrybot.utils.datetime_utils import get_current_datetime
from larrybot.utils.enhanced_ux_helpers import escape_markdown_v2, UnifiedButtonBuilder, ButtonType
import random
from datetime import datetime, timedelta
from larrybot.services.task_service import TaskService
from larrybot.storage.db import get_optimized_session
from larrybot.storage.habit_repository import HabitRepository
from larrybot.utils.datetime_utils import get_current_datetime
from larrybot.utils.datetime_utils import ensure_timezone_aware
from larrybot.utils.telegram_safe import safe_edit
logger = logging.getLogger(__name__)


class TelegramBotHandler:
    """
    Handles Telegram bot initialization and command routing.
    Single-user system: only the configured user can access the bot.
    """

    def __init__(self, config: Config, command_registry: CommandRegistry):
        self.config = config
        self.command_registry = command_registry
        
        # Configure Google API logging to suppress deprecated warnings
        from larrybot.utils.telegram_safe import configure_google_api_logging
        configure_google_api_logging(self.config)
        
        request = HTTPXRequest(connection_pool_size=8, connect_timeout=10.0,
            read_timeout=20.0, write_timeout=20.0, pool_timeout=5.0)
        self.application = Application.builder().token(self.config.
            TELEGRAM_BOT_TOKEN).request(request).build()
        self.application.add_error_handler(self._global_error_handler)
        self._register_core_commands()
        self._register_core_handlers()
        self.intent_recognizer = IntentRecognizer()
        self.entity_extractor = EntityExtractor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.enhanced_narrative_processor = EnhancedNarrativeProcessor()
        self.enhanced_message_processor = EnhancedMessageProcessor()

    def _is_authorized(self, update: Update) ->bool:
        """Check if the user is authorized to use this single-user bot."""
        user = getattr(update, 'effective_user', None)
        if not user:
            return False
        try:
            if not self.config:
                return False
            return user.id == self.config.ALLOWED_TELEGRAM_USER_ID
        except (AttributeError, TypeError):
            return False

    def _register_core_handlers(self) ->None:
        """Register core handlers including callback query handler."""
        self.application.add_handler(CommandHandler('start', self._start))
        self.application.add_handler(CommandHandler('help', self._help))
        self.application.add_handler(CallbackQueryHandler(self.
            _handle_callback_query))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters
            .COMMAND, self._handle_text_message))
        self.application.add_handler(MessageHandler(filters.ATTACHMENT,
            self._handle_file_upload))
        if hasattr(self.command_registry, '_commands') and isinstance(self.
            command_registry._commands, dict):
            for command, handler in self.command_registry._commands.items():
                if command in ('/start', '/help'):
                    continue
                if hasattr(handler, '__self__') and handler.__self__ is self:
                    self.application.add_handler(CommandHandler(command.
                        lstrip('/'), handler))
                else:
                    self.application.add_handler(CommandHandler(command.
                        lstrip('/'), self._dispatch_command))

    def _register_core_commands(self) ->None:
        """Register core commands with the command registry."""
        from larrybot.core.command_registry import CommandMetadata
        help_metadata = CommandMetadata(name='/help', description=
            'Show available commands and their descriptions', usage='/help',
            category='system')
        self.command_registry.register('/help', self._help, help_metadata)
        start_metadata = CommandMetadata(name='/start', description=
            'Start the bot and show welcome message', usage='/start',
            category='system')
        self.command_registry.register('/start', self._start, start_metadata)
        daily_metadata = CommandMetadata(name='/daily', description=
            'Send daily report with tasks, habits, and calendar events',
            usage='/daily', category='system')
        self.command_registry.register('/daily', self.daily_command,
            daily_metadata)
        
        scheduler_status_metadata = CommandMetadata(name='/scheduler_status', 
            description='Check scheduler and daily report status',
            usage='/scheduler_status', category='system')
        self.command_registry.register('/scheduler_status', self.scheduler_status_command,
            scheduler_status_metadata)
        
        trigger_daily_metadata = CommandMetadata(name='/trigger_daily', 
            description='Manually trigger the daily report',
            usage='/trigger_daily', category='system')
        self.command_registry.register('/trigger_daily', self.trigger_daily_report_command,
            trigger_daily_metadata)

    async def _handle_callback_query(self, update: Update, context:
        ContextTypes.DEFAULT_TYPE) ->None:
        """
        Handle callback queries from inline keyboards with timeout protection.
        Follows Telegram bot best practices for callback query handling.
        """
        query = update.callback_query
        try:
            await asyncio.wait_for(query.answer(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning('Timeout acknowledging callback query')
            return
        except Exception as e:
            logger.error(f'Failed to acknowledge callback query: {e}')
            return
        if not self._is_authorized(update):
            try:
                await safe_edit(query.edit_message_text, MessageFormatter.
                    format_error_message('Unauthorized access',
                    'Only the configured user can use this bot.'),
                    parse_mode='MarkdownV2')
            except Exception as e:
                logger.error(f'Failed to send unauthorized message: {e}')
            return
        try:
            await asyncio.wait_for(self._handle_callback_operations(query,
                context), timeout=15.0)
        except asyncio.TimeoutError:
            logger.error(f'Callback query timeout for action: {query.data}')
            try:
                await safe_edit(query.edit_message_text, MessageFormatter.
                    format_error_message('⏱️ Action timed out',
                    'Please try again\\. If the issue persists, try using text commands\\.'
                    ), parse_mode='MarkdownV2')
            except Exception as e:
                logger.error(f'Failed to send timeout message: {e}')
        except Exception as e:
            logger.error(f'Error handling callback query: {e}')
            try:
                await safe_edit(query.edit_message_text, MessageFormatter.
                    format_error_message('❌ An error occurred',
                    'Please try again or use a command instead\\.'),
                    parse_mode='MarkdownV2')
            except Exception as nested_e:
                logger.error(f'Failed to send error message: {nested_e}')

    async def _handle_callback_operations(self, query, context:
        ContextTypes.DEFAULT_TYPE) ->None:
        """Handle the actual callback operations with proper routing."""
        callback_data = query.data
        
        # Try to get callback handler from registry first
        callback_handler = self.command_registry.get_callback_handler(callback_data)
        if callback_handler:
            await callback_handler(query, context)
            return
        
        # Fallback to existing hardcoded handlers
        if callback_data == 'no_action':
            return
        elif callback_data == 'nav_back':
            await self._handle_navigation_back(query, context)
        elif callback_data == 'nav_main':
            await self._handle_navigation_main(query, context)
        elif callback_data == 'cancel_action':
            await self._handle_cancel_action(query, context)

        elif callback_data.startswith('task_'):
            await self._handle_task_callback(query, context)
        elif callback_data.startswith('client_'):
            await self._handle_client_callback(query, context)
        elif callback_data.startswith('habit_'):
            await self._handle_habit_callback(query, context)
        elif callback_data.startswith('confirm_'):
            await self._handle_confirmation_callback(query, context)
        elif callback_data.startswith('menu_'):
            await self._handle_menu_callback(query, context)
        elif callback_data.startswith('bulk_'):
            await self._handle_bulk_operations_callback(query, context)
        elif callback_data == 'task_edit_cancel':
            await self._handle_task_edit_cancel(query, context)
        elif callback_data == 'tasks_list':
            await self._handle_tasks_list(query, context)
        elif callback_data == 'tasks_refresh':
            await self._handle_tasks_refresh(query, context)
        elif callback_data.startswith('reminder_'):
            await self._handle_reminder_callback(query, context)
        elif callback_data.startswith('attachment_'):
            await self._handle_attachment_callback(query, context)
        elif callback_data.startswith('calendar_'):
            await self._handle_calendar_callback(query, context)
        elif callback_data.startswith('filter_'):
            await self._handle_filter_callback(query, context)
        elif callback_data == 'add_task':
            await self._handle_add_task(query, context)
        elif callback_data == 'help_quick':
            await self._handle_help_quick(query, context)
        elif callback_data.startswith('help_'):
            await self._handle_help_section(query, context)
        else:
            from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
            error_keyboard = InlineKeyboardMarkup([[UnifiedButtonBuilder.
                create_button(text='🔙 Back', callback_data='nav_back',
                button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.
                create_button(text='🏠 Main Menu', callback_data='nav_main',
                button_type=ButtonType.PRIMARY)]])
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Unknown action',
                'This button action is not implemented yet.'), reply_markup
                =error_keyboard, parse_mode='MarkdownV2')

    async def _handle_task_callback(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle task-related callback queries."""
        callback_data = query.data
        if callback_data.startswith('task_done:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_task_done(query, context, task_id)
        elif callback_data.startswith('task_edit:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_task_edit(query, context, task_id)
        elif callback_data.startswith('task_delete:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_task_delete(query, context, task_id)
        elif callback_data.startswith('task_view:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_task_view(query, context, task_id)
        elif callback_data.startswith('task_attach_file:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_task_attach_file(query, context, task_id)
        elif callback_data.startswith('task_add_note:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_task_add_note(query, context, task_id)
        elif callback_data.startswith('task_time_menu:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_task_time_menu(query, context, task_id)
        elif callback_data.startswith('task_start_time:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_task_start_time(query, context, task_id)
        elif callback_data.startswith('task_stop_time:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_task_stop_time(query, context, task_id)
        elif callback_data.startswith('task_time_stats:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_task_time_stats(query, context, task_id)

        elif callback_data.startswith('task_dependencies:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_task_dependencies(query, context, task_id)
        elif callback_data == 'task_edit_cancel':
            await self._handle_task_edit_cancel(query, context)
        elif callback_data == 'tasks_list':
            await self._handle_tasks_list(query, context)
        elif callback_data == 'tasks_refresh':
            await self._handle_tasks_refresh(query, context)

    async def _handle_client_callback(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle client-related callback queries."""
        callback_data = query.data
        if callback_data.startswith('client_tasks:'):
            client_id = int(callback_data.split(':')[1])
            await self._handle_client_tasks(query, context, client_id)
        # Other client callbacks are now handled by the registry

    async def _handle_habit_callback(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle habit-related callback queries."""
        # All habit callbacks are now handled by the registry

    async def _handle_confirmation_callback(self, query, context:
        ContextTypes.DEFAULT_TYPE) ->None:
        """Handle confirmation callback queries."""
        callback_data = query.data
        if callback_data.startswith('confirm_task_delete:'):
            task_id = int(callback_data.split(':')[1])
            await self._confirm_task_delete(query, context, task_id)
        elif callback_data.startswith('confirm_client_delete:'):
            client_id = int(callback_data.split(':')[1])
            await self._confirm_client_delete(query, context, client_id)
        elif callback_data.startswith('confirm_habit_delete:'):
            habit_id = int(callback_data.split(':')[1])
            await self._confirm_habit_delete(query, context, habit_id)

    async def _handle_menu_callback(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle menu navigation callback queries."""
        callback_data = query.data
        if callback_data == 'menu_tasks':
            await self._show_task_menu(query, context)
        elif callback_data == 'menu_clients':
            await self._show_client_menu(query, context)
        elif callback_data == 'menu_habits':
            await self._show_habit_menu(query, context)
        elif callback_data == 'menu_reminders':
            await self._show_reminder_menu(query, context)
        elif callback_data == 'menu_analytics':
            await self._show_analytics_menu(query, context)

    async def _handle_bulk_operations_callback(self, query, context:
        ContextTypes.DEFAULT_TYPE) ->None:
        """Handle bulk operations callback queries."""
        callback_data = query.data
        if callback_data == 'bulk_status_menu':
            await self._show_bulk_status_menu(query, context)
        elif callback_data == 'bulk_priority_menu':
            await self._show_bulk_priority_menu(query, context)
        elif callback_data == 'bulk_assign_menu':
            await self._show_bulk_assign_menu(query, context)
        elif callback_data == 'bulk_delete_menu':
            await self._show_bulk_delete_menu(query, context)
        elif callback_data == 'bulk_preview':
            await self._show_bulk_preview(query, context)
        elif callback_data == 'bulk_save_selection':
            await self._save_bulk_selection(query, context)
        elif callback_data.startswith('bulk_delete_confirm:'):
            task_ids = callback_data.split(':')[1]
            await self._confirm_bulk_delete(query, context, task_ids)
        elif callback_data == 'bulk_delete_cancel':
            await self._cancel_bulk_delete(query, context)
        elif callback_data.startswith('bulk_status:'):
            status = callback_data.split(':')[1]
            await self._handle_bulk_status_update(query, context, status)
        elif callback_data.startswith('bulk_priority:'):
            priority = callback_data.split(':')[1]
            await self._handle_bulk_priority_update(query, context, priority)
        elif callback_data == 'bulk_operations_back':
            await self._handle_bulk_operations_back(query, context)

    async def _show_task_menu(self, query, context: ContextTypes.DEFAULT_TYPE
        ) ->None:
        """[DEPRECATED] Show task management menu. Use /list instead."""
        await safe_edit(query.edit_message_text,
            '📋 **Task Management**\n\nThis menu is deprecated. Use the main menu or /list to view your tasks.',
            parse_mode='MarkdownV2')

    async def _show_client_menu(self, query, context: ContextTypes.DEFAULT_TYPE
        ) ->None:
        """Show client management menu."""
        await safe_edit(query.edit_message_text,
            """👥 **Client Management**

Use commands:
• /allclients - List all clients
• /addclient - Add new client
• /client - View client details"""
            , parse_mode='MarkdownV2')

    async def _show_habit_menu(self, query, context: ContextTypes.DEFAULT_TYPE
        ) ->None:
        """Show habit management menu."""
        await safe_edit(query.edit_message_text,
            """🔄 **Habit Management**

Use commands:
• /habit_list - List all habits
• /habit_add - Add new habit
• /habit_done - Mark habit complete"""
            , parse_mode='MarkdownV2')

    async def _show_reminder_menu(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Show reminder management menu."""
        await safe_edit(query.edit_message_text,
            """⏰ **Reminder Management**

Use commands:
• /reminders - List all reminders
• /addreminder - Add new reminder
• /delreminder - Delete reminder"""
            , parse_mode='MarkdownV2')

    async def _show_analytics_menu(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Show analytics menu."""
        await safe_edit(query.edit_message_text,
            """📊 **Analytics**

Use commands:
• /analytics - Task analytics
• /clientanalytics - Client analytics
• /productivity_report - Detailed report"""
            , parse_mode='MarkdownV2')

    async def _show_bulk_status_menu(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Show bulk status update menu."""
        from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
        keyboard = InlineKeyboardMarkup([[UnifiedButtonBuilder.
            create_button(text='📝 Todo', callback_data='bulk_status:Todo',
            button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.
            create_button(text='🔄 In Progress', callback_data=
            'bulk_status:In Progress', button_type=ButtonType.SECONDARY)],
            [UnifiedButtonBuilder.create_button(text='👀 Review',
            callback_data='bulk_status:Review', button_type=ButtonType.
            WARNING), UnifiedButtonBuilder.create_button(text='✅ Done',
            callback_data='bulk_status:Done', button_type=ButtonType.
            SUCCESS)], [UnifiedButtonBuilder.create_button(text='🔙 Back',
            callback_data='bulk_operations_back', button_type=ButtonType.
            SECONDARY)]])
        await safe_edit(query.edit_message_text,
            """📋 **Bulk Status Update**

Select the new status for your tasks:"""
            , reply_markup=keyboard, parse_mode='MarkdownV2')

    async def _show_bulk_priority_menu(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Show bulk priority update menu."""
        from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
        keyboard = InlineKeyboardMarkup([[UnifiedButtonBuilder.
            create_button(text='🟢 Low', callback_data='bulk_priority:Low',
            button_type=ButtonType.SUCCESS), UnifiedButtonBuilder.
            create_button(text='🟡 Medium', callback_data=
            'bulk_priority:Medium', button_type=ButtonType.WARNING)], [
            UnifiedButtonBuilder.create_button(text='🟠 High', callback_data
            ='bulk_priority:High', button_type=ButtonType.WARNING),
            UnifiedButtonBuilder.create_button(text='🔴 Critical',
            callback_data='bulk_priority:Critical', button_type=ButtonType.
            DANGER)], [UnifiedButtonBuilder.create_button(text='🔙 Back',
            callback_data='bulk_operations_back', button_type=ButtonType.
            SECONDARY)]])
        await safe_edit(query.edit_message_text,
            """🎯 **Bulk Priority Update**

Select the new priority for your tasks:"""
            , reply_markup=keyboard, parse_mode='MarkdownV2')

    async def _show_bulk_assign_menu(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Show bulk assign menu."""
        await safe_edit(query.edit_message_text,
            """👥 **Bulk Assignment**

Use the command:
`/bulk_assign <task_ids> <client_name>`

Example: `/bulk_assign 1,2,3 John Doe`"""
            , parse_mode='MarkdownV2')

    async def _show_bulk_delete_menu(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Show bulk delete menu."""
        await safe_edit(query.edit_message_text,
            """🗑️ **Bulk Delete**

Use the command:
`/bulk_delete <task_ids> [confirm]`

Example: `/bulk_delete 1,2,3 confirm`"""
            , parse_mode='MarkdownV2')

    async def _show_bulk_preview(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Show bulk operations preview."""
        await safe_edit(query.edit_message_text,
            """📊 **Bulk Operations Preview**

This feature will show a preview of tasks before applying bulk operations."""
            , parse_mode='MarkdownV2')

    async def _save_bulk_selection(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Save bulk selection."""
        await safe_edit(query.edit_message_text,
            """💾 **Bulk Selection Saved**

Your task selection has been saved for bulk operations."""
            , parse_mode='MarkdownV2')

    async def _confirm_bulk_delete(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_ids: str) ->None:
        """Confirm bulk delete operation."""
        from larrybot.services.task_service import TaskService
        try:
            task_service = TaskService()
            result = await task_service.bulk_delete_tasks([int(id.strip()) for
                id in task_ids.split(',')])
            if result['success']:
                await safe_edit(query.edit_message_text, MessageFormatter.
                    format_success_message('🗑️ Bulk Delete Complete!', {
                    'Tasks Deleted': len(task_ids.split(',')), 'Details':
                    result.get('details', 'All tasks deleted successfully')
                    }), parse_mode='MarkdownV2')
            else:
                await safe_edit(query.edit_message_text, MessageFormatter.
                    format_error_message(result['message'],
                    'Please check the task IDs and try again.'), parse_mode
                    ='MarkdownV2')
        except Exception as e:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Error during bulk delete', str(e)),
                parse_mode='MarkdownV2')

    async def _cancel_bulk_delete(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Cancel bulk delete operation."""
        await safe_edit(query.edit_message_text,
            """❌ **Bulk Delete Cancelled**

No tasks were deleted.""",
            parse_mode='MarkdownV2')

    async def _handle_navigation_back(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle back navigation."""
        await safe_edit(query.edit_message_text,
            """⬅️ **Back Navigation**

Use commands or the main menu to navigate."""
            , parse_mode='MarkdownV2')

    async def _handle_navigation_main(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle main menu navigation."""
        from larrybot.utils.ux_helpers import NavigationHelper
        await safe_edit(query.edit_message_text,
            '🏠 **Main Menu**\n\nSelect an option:', reply_markup=
            NavigationHelper.get_main_menu_keyboard(), parse_mode='MarkdownV2')

    async def _handle_cancel_action(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle action cancellation."""
        await safe_edit(query.edit_message_text,
            '❌ **Action Cancelled**\n\nNo changes were made.', parse_mode=
            'MarkdownV2')

    async def _handle_task_done(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """Handle task completion via callback with timeout protection and loading indicator."""
        try:
            await safe_edit(query.edit_message_text,
                f"""✅ **Completing Task...**

Marking task {task_id} as complete..."""
                , parse_mode='Markdown')
            await asyncio.wait_for(self._handle_task_done_operation(query,
                context, task_id), timeout=8.0)
        except asyncio.TimeoutError:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('⏱️ Operation Timeout',
                'Task completion took too long. Please check if it was completed and try again if needed.'
                ), parse_mode='Markdown')
        except Exception as e:
            logger.error(f'Error completing task {task_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('🚫 Completion Error',
                f"""Failed to complete task: {str(e)}

Please try again or use the command interface."""
                ), parse_mode='Markdown')

    async def _handle_task_done_operation(self, query, context:
        ContextTypes.DEFAULT_TYPE, task_id: int) ->None:
        """Handle task completion operation."""
        print(
            f'[DEBUG] _handle_task_done_operation entered with task_id: {task_id}'
            )
        print(
            f'[DEBUG] query type: {type(query)}, context type: {type(context)}'
            )
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        print(f'[DEBUG] Imports completed successfully')
        try:
            with get_optimized_session() as session:
                print(f'[DEBUG] Entered DB session context: {session}')
                repo = TaskRepository(session)
                print(f'[DEBUG] TaskRepository instantiated: {repo}')
                task = repo.get_task_by_id(task_id)
                print(f'[DEBUG] Task fetched: {task}')
                if not task:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Task ID {task_id} not found',
                        'This task may have been deleted or the ID is invalid.'
                        ), parse_mode='Markdown')
                    return
                print(f'[DEBUG] About to check task.done: {task.done}')
                if task.is_done():
                    print(
                        f'[DEBUG] About to call format_info_message for already completed task'
                        )
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_info_message(
                        '✅ Already Complete', {'Task': task.description,
                        'Status': 'Already marked as done!'}), parse_mode=
                        'Markdown')
                    return
                print(f'[DEBUG] About to call repo.mark_task_done({task_id})')
                completed_task = repo.mark_task_done(task_id)
                print(f'[DEBUG] repo.mark_task_done returned: {completed_task}'
                    )
                if completed_task:
                    try:
                        if ServiceLocator.has('event_bus'):
                            event_bus = ServiceLocator.get('event_bus')
                            emit_task_event(event_bus, 'task.completed',
                                completed_task)
                    except Exception as e:
                        logger.debug(
                            f'Event emission failed for task completion: {e}')
                    from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType, ActionType
                    remaining_tasks = repo.list_incomplete_tasks()
                    high_priority_remaining = sum(1 for t in
                        remaining_tasks if getattr(t, 'priority', 'Medium') in
                        ['High', 'Critical'])
                    details = {'Task': completed_task.description, 'Status':
                        'Completed', 'Message':
                        '🎉 Great work\\! Keep up the momentum\\!'}
                    print(
                        f'[DEBUG] About to call format_success_message with details type: {type(details)}, value: {details}'
                        )
                    success_message = MessageFormatter.format_success_message(
                        '✅ Task Completed!', details)
                    suggestions = []
                    if remaining_tasks:
                        suggestions.append(
                            f'📋 **{len(remaining_tasks)} tasks remaining**')
                        if high_priority_remaining > 0:
                            suggestions.append(
                                f'⚠️ **{high_priority_remaining} high priority tasks** need attention'
                                )
                        suggestions.append('💡 **Suggestions:**')
                        suggestions.append('• Review your task list')
                        suggestions.append('• Focus on high priority items')
                        if len(remaining_tasks) > 5:
                            suggestions.append(
                                '• Use filters to organize tasks')
                    else:
                        suggestions.append(
                            '🎉 **All tasks complete\\!** Time to celebrate\\!')
                        suggestions.append('💡 **Suggestions:**')
                        suggestions.append('• Add new tasks to stay productive'
                            )
                        suggestions.append('• Review your analytics')
                    if suggestions:
                        success_message += '\n\n' + '\n'.join(suggestions)
                    custom_actions = [{'text': '📋 View Tasks',
                        'callback_data': 'tasks_refresh', 'type':
                        ButtonType.PRIMARY, 'emoji': '📋'}]
                    if remaining_tasks and high_priority_remaining > 0:
                        custom_actions.append({'text': '⚠️ High Priority',
                            'callback_data': 'tasks_filter_priority_high',
                            'type': ButtonType.WARNING, 'emoji': '⚠️'})
                    if remaining_tasks:
                        custom_actions.append({'text': '➕ Add Task',
                            'callback_data': 'add_task', 'type': ButtonType
                            .SECONDARY, 'emoji': '➕'})
                    else:
                        custom_actions.append({'text': '📊 Analytics',
                            'callback_data': 'tasks_analytics', 'type':
                            ButtonType.INFO, 'emoji': '📊'})
                    print(
                        f'[DEBUG] About to call build_entity_keyboard with custom_actions: {custom_actions}'
                        )
                    keyboard = UnifiedButtonBuilder.build_entity_keyboard(
                        entity_id=0, entity_type='task_completed',
                        available_actions=[ActionType.REFRESH],
                        custom_actions=custom_actions)
                    await safe_edit(query.edit_message_text,
                        success_message, reply_markup=keyboard, parse_mode=
                        'MarkdownV2')
                else:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        '❌ Completion Failed',
                        'Unable to mark the task as complete. Please try again.'
                        ), parse_mode='Markdown')
        except Exception as e:
            logger.error(f'Error completing task {task_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('🚫 Completion Error',
                f"""Failed to complete task: {str(e)}

Please try again or use the command interface."""
                ), parse_mode='Markdown')

    async def _handle_task_edit(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """Handle task editing via callback."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
        try:
            with get_optimized_session() as session:
                print(f'[DEBUG] Entered DB session context: {session}')
                repo = TaskRepository(session)
                print(f'[DEBUG] TaskRepository instantiated: {repo}')
                task = repo.get_task_by_id(task_id)
                print(f'[DEBUG] Task fetched: {task}')
                if not task:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Task ID {task_id} not found',
                        "The task may have already been deleted or doesn't exist."
                        ), parse_mode='MarkdownV2')
                    return
                if task.done:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        'Cannot edit completed task',
                        'Completed tasks cannot be edited. Use /edit command to unmark and edit.'
                        ), parse_mode='MarkdownV2')
                    return
                context.user_data['editing_task_id'] = task_id
                keyboard = InlineKeyboardMarkup([[UnifiedButtonBuilder.
                    create_button(text='❌ Cancel', callback_data=
                    'task_edit_cancel', button_type=ButtonType.INFO)]])
                await safe_edit(query.edit_message_text,
                    f"""✏️ **Edit Task**

**Current**: {MessageFormatter.escape_markdown(task.description)}
**ID**: {task_id}

Please reply with the new description for this task\\."""
                    , reply_markup=keyboard, parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f'Error starting task edit for task {task_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Error editing task',
                'Please try again or use /edit command.'), parse_mode=
                'MarkdownV2')

    async def _handle_task_edit_cancel(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle cancellation of task editing."""
        if 'editing_task_id' in context.user_data:
            del context.user_data['editing_task_id']
        await safe_edit(query.edit_message_text,
            """❌ **Edit Cancelled**

Task editing was cancelled. No changes were made."""
            , parse_mode='MarkdownV2')

    async def _handle_file_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle an incoming file and attach it to a task if in the correct state."""
        if 'attaching_file_to_task' not in context.user_data:
            return

        task_id = context.user_data.pop('attaching_file_to_task')

        from larrybot.plugins.file_attachments import attach_file_handler
        
        context.args = [str(task_id)]
        
        await attach_file_handler(update, context)

    async def _handle_task_delete(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """Handle task deletion via callback."""
        from larrybot.utils.ux_helpers import KeyboardBuilder
        await safe_edit(query.edit_message_text,
            f"""🗑️ **Confirm Task Deletion**

Are you sure you want to delete Task #{task_id}?"""
            , reply_markup=KeyboardBuilder.build_confirmation_keyboard(
            'task_delete', task_id), parse_mode='MarkdownV2')

    async def _confirm_task_delete(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """Confirm task deletion."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.core.event_utils import emit_task_event
        from larrybot.utils.ux_helpers import MessageFormatter
        try:
            with get_optimized_session() as session:
                repo = TaskRepository(session)
                task = repo.remove_task(task_id)
                if task:
                    emit_task_event(None, 'task_removed', task)
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_success_message(
                        '🗑️ Task deleted successfully!', {'Task': task.
                        description, 'ID': task_id, 'Status': 'Deleted',
                        'Action': 'Task removed from database'}),
                        parse_mode='MarkdownV2')
                else:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Task ID {task_id} not found',
                        "The task may have already been deleted or doesn't exist."
                        ), parse_mode='MarkdownV2')
        except Exception as e:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Error deleting task', str(e)),
                parse_mode='MarkdownV2')

    async def _handle_client_tasks(self, query, context: ContextTypes.
        DEFAULT_TYPE, client_id: int) ->None:
        """Handle client tasks view."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.client_repository import ClientRepository
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        try:
            with get_optimized_session() as session:
                client_repo = ClientRepository(session)
                task_repo = TaskRepository(session)
                client = client_repo.get_client_by_id(client_id)
                if not client:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Client ID {client_id} not found',
                        "The client may have already been deleted or doesn't exist."
                        ), parse_mode='MarkdownV2')
                    return
                tasks = task_repo.get_tasks_with_filters(client_id=client_id)
                if not tasks:
                    message = (
                        f'📋 **Tasks for {MessageFormatter.escape_markdown(client.name)}**\n\n'
                        )
                    message += 'No tasks assigned to this client\\.'
                    keyboard = InlineKeyboardMarkup([[UnifiedButtonBuilder.
                        create_button(text='⬅️ Back to Client',
                        callback_data=f'client_view:{client.id}',
                        button_type=ButtonType.INFO)]])
                else:
                    message = MessageFormatter.format_task_list(tasks,
                        title=f'📋 **Tasks for {client.name}**')
                    buttons = []
                    for task in tasks[:5]:
                        task_buttons = [UnifiedButtonBuilder.create_button(
                            text='✅', callback_data=f'task_done:{task.id}',
                            button_type=ButtonType.INFO),
                            UnifiedButtonBuilder.create_button(text='✏️',
                            callback_data=f'task_edit:{task.id}',
                            button_type=ButtonType.INFO),
                            UnifiedButtonBuilder.create_button(text='👁️',
                            callback_data=f'task_view:{task.id}',
                            button_type=ButtonType.INFO)]
                        buttons.append(task_buttons)
                    buttons.append([UnifiedButtonBuilder.create_button(text
                        ='⬅️ Back to Client', callback_data=
                        f'client_view:{client.id}', button_type=ButtonType.
                        INFO), UnifiedButtonBuilder.create_button(text=
                        '🔄 Refresh', callback_data=
                        f'client_tasks:{client.id}', button_type=ButtonType
                        .INFO)])
                    keyboard = InlineKeyboardMarkup(buttons)
                await safe_edit(query.edit_message_text, message,
                    reply_markup=keyboard, parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f'Error showing client tasks for {client_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Error showing client tasks',
                'Please try again or use /client command.'), parse_mode=
                'MarkdownV2')

    async def _handle_client_analytics(self, query, context: ContextTypes.
        DEFAULT_TYPE, client_id: int) ->None:
        """Show analytics for the selected client."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.client_repository import ClientRepository
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        try:
            with get_optimized_session() as session:
                client_repo = ClientRepository(session)
                task_repo = TaskRepository(session)
                client = client_repo.get_client_by_id(client_id)
                if not client:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Client ID {client_id} not found',
                        "The client may have already been deleted or doesn't exist."
                        ), parse_mode='MarkdownV2')
                    return
                tasks = task_repo.get_tasks_by_client(client.name)
                completed = sum(1 for t in tasks if t.done)
                pending = len(tasks) - completed
                completion_rate = completed / len(tasks) * 100 if tasks else 0
                message = f'📊 **Client Analytics**\n\n'
                message += (
                    f'**Client**: {MessageFormatter.escape_markdown(client.name)}\n'
                    )
                message += f'**ID**: {client.id}\n'
                message += f'**Total Tasks**: {len(tasks)}\n'
                message += f'**Completed**: {completed} ✅\n'
                message += f'**Pending**: {pending} ⏳\n'
                message += f'**Completion Rate**: {completion_rate:.1f}%\n'
                await safe_edit(query.edit_message_text, message,
                    parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f'Error showing client analytics for {client_id}: {e}'
                )
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Error showing client analytics',
                'Please try again or use /allclients command.'), parse_mode
                ='MarkdownV2')

    async def _handle_client_delete(self, query, context: ContextTypes.
        DEFAULT_TYPE, client_id: int) ->None:
        """Handle client deletion: show confirmation dialog with client info and task count."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.client_repository import ClientRepository
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
        try:
            with get_optimized_session() as session:
                client_repo = ClientRepository(session)
                task_repo = TaskRepository(session)
                client = client_repo.get_client_by_id(client_id)
                if not client:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Client ID {client_id} not found',
                        "The client may have already been deleted or doesn't exist."
                        ), parse_mode='MarkdownV2')
                    return
                tasks = task_repo.get_tasks_by_client(client.name)
                keyboard = KeyboardBuilder.build_confirmation_keyboard(
                    'client_delete', client.id)
                await safe_edit(query.edit_message_text,
                    f"""🗑️ **Confirm Client Deletion**

**Client**: {MessageFormatter.escape_markdown(client.name)}
**ID**: {client.id}
**Tasks**: {len(tasks)} assigned

⚠️ **Warning**: This will unassign all tasks from this client.

Are you sure you want to delete this client?"""
                    , reply_markup=keyboard, parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(
                f'Error showing client delete confirmation for {client_id}: {e}'
                )
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Error preparing client deletion',
                'Please try again or use /allclients command.'), parse_mode
                ='MarkdownV2')

    async def _confirm_client_delete(self, query, context: ContextTypes.
        DEFAULT_TYPE, client_id: int) ->None:
        """Confirm client deletion: delete client, unassign tasks, show success message."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.client_repository import ClientRepository
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.core.event_utils import emit_client_event
        from larrybot.utils.ux_helpers import MessageFormatter
        try:
            with get_optimized_session() as session:
                client_repo = ClientRepository(session)
                task_repo = TaskRepository(session)
                client = client_repo.get_client_by_id(client_id)
                if not client:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Client ID {client_id} not found',
                        "The client may have already been deleted or doesn't exist."
                        ), parse_mode='MarkdownV2')
                    return
                tasks = task_repo.get_tasks_by_client(client.name)
                for task in tasks:
                    task_repo.unassign_task(task.id)
                client_repo.remove_client(client.name)
                emit_client_event(None, 'client_removed', client)
                await safe_edit(query.edit_message_text, MessageFormatter.
                    format_success_message(
                    f'🗑️ Client deleted successfully!', {'Client': client.
                    name, 'ID': client.id, 'Unassigned Tasks': len(tasks),
                    'Action': 'Client removed from database'}), parse_mode=
                    'MarkdownV2')
        except Exception as e:
            logger.error(f'Error deleting client {client_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Error deleting client',
                'Please try again or use /allclients command.'), parse_mode
                ='MarkdownV2')

    async def _handle_habit_done(self, query, context: ContextTypes.
        DEFAULT_TYPE, habit_id: int) ->None:
        """Handle habit completion."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.habit_repository import HabitRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        from datetime import datetime
        try:
            with get_optimized_session() as session:
                repo = HabitRepository(session)
                habit = repo.get_habit_by_id(habit_id)
                if not habit:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Habit #{habit_id} not found',
                        'The habit may have been deleted.'), parse_mode=
                        'MarkdownV2')
                    return
                updated_habit = repo.mark_habit_done_by_id(habit_id)
                if not updated_habit:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f"Failed to complete habit '{habit.name}'",
                        'Please try again.'), parse_mode='MarkdownV2')
                    return
                streak_emoji = ('🔥' if updated_habit.streak >= 7 else '📈' if
                    updated_habit.streak >= 3 else '✅')
                milestone_message = ''
                if updated_habit.streak == 7:
                    milestone_message = '\n🎉 **7-day streak milestone!**'
                elif updated_habit.streak == 30:
                    milestone_message = '\n🏆 **30-day streak milestone!**'
                elif updated_habit.streak == 100:
                    milestone_message = '\n👑 **100-day streak milestone!**'
                await safe_edit(query.edit_message_text, MessageFormatter.
                    format_success_message(
                    f'Habit completed for today! {streak_emoji}', {'Habit':
                    updated_habit.name, 'Current Streak':
                    f'{updated_habit.streak} days {streak_emoji}',
                    'Last Completed': updated_habit.last_completed.strftime
                    ('%Y-%m-%d %H:%M') if updated_habit.last_completed else
                    'N/A'}) + milestone_message, parse_mode='MarkdownV2')
        except Exception as e:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to complete habit',
                f'Error: {str(e)}'), parse_mode='MarkdownV2')

    async def _handle_habit_progress(self, query, context: ContextTypes.
        DEFAULT_TYPE, habit_id: int) ->None:
        """Handle habit progress view."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.habit_repository import HabitRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        from datetime import datetime
        try:
            with get_optimized_session() as session:
                repo = HabitRepository(session)
                habit = repo.get_habit_by_id(habit_id)
                if not habit:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Habit #{habit_id} not found',
                        'The habit may have been deleted.'), parse_mode=
                        'MarkdownV2')
                    return
                today = get_current_datetime().date()
                days_since_creation = (today - habit.created_at.date()
                    ).days + 1 if habit.created_at else 0
                completion_rate = (habit.streak / days_since_creation * 100 if
                    days_since_creation > 0 else 0)
                progress_length = int(habit.streak / max(
                    days_since_creation, 1) * 30)
                progress_bar = '█' * progress_length + '░' * (30 -
                    progress_length)
                next_milestone = None
                if habit.streak < 7:
                    next_milestone = 7
                elif habit.streak < 30:
                    next_milestone = 30
                elif habit.streak < 100:
                    next_milestone = 100
                else:
                    next_milestone = habit.streak + 10
                days_to_milestone = next_milestone - habit.streak
                message = f'📊 **Habit Progress Report**\n\n'
                message += (
                    f'**Habit**: {MessageFormatter.escape_markdown(habit.name)}\n'
                    )
                message += f'**Current Streak**: {habit.streak} days\n'
                message += f'**Days Tracked**: {days_since_creation} days\n'
                message += f'**Completion Rate**: {completion_rate:.1f}%\n\n'
                message += f'📈 **Progress Bar**\n'
                message += f'`{progress_bar}`\n'
                message += (
                    f'`{habit.streak:>3} / {days_since_creation:>3} days`\n\n')
                if next_milestone:
                    message += f'🎯 **Next Milestone**\n'
                    message += f'• Target: {next_milestone} days\n'
                    message += f'• Days needed: {days_to_milestone}\n\n'
                if habit.last_completed:
                    if hasattr(habit.last_completed, 'date'):
                        last_completed_date = habit.last_completed.date()
                    else:
                        last_completed_date = habit.last_completed
                    days_since_last = (today - last_completed_date).days
                    message += f'📅 **Recent Activity**\n'
                    if days_since_last == 0:
                        message += f'• Last completed: Today ✅\n'
                    elif days_since_last == 1:
                        message += f'• Last completed: Yesterday ⚠️\n'
                    else:
                        message += (
                            f'• Last completed: {days_since_last} days ago ❌\n'
                            )
                keyboard = [[UnifiedButtonBuilder.create_button(text=
                    '✅ Complete Today', callback_data=
                    f'habit_done:{habit_id}', button_type=ButtonType.INFO)],
                    [UnifiedButtonBuilder.create_button(text=
                    '⬅️ Back to Habits', callback_data='habit_refresh',
                    button_type=ButtonType.INFO)]]
                await safe_edit(query.edit_message_text, message,
                    reply_markup=InlineKeyboardMarkup(keyboard), parse_mode
                    ='MarkdownV2')
        except Exception as e:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to load habit progress',
                f'Error: {str(e)}'), parse_mode='MarkdownV2')

    async def _handle_habit_delete(self, query, context: ContextTypes.
        DEFAULT_TYPE, habit_id: int) ->None:
        """Handle habit deletion."""
        from larrybot.utils.ux_helpers import KeyboardBuilder
        await safe_edit(query.edit_message_text,
            f"""🗑️ **Confirm Habit Deletion**

Are you sure you want to delete this habit?"""
            , reply_markup=KeyboardBuilder.build_confirmation_keyboard(
            'habit_delete', habit_id), parse_mode='MarkdownV2')

    async def _confirm_habit_delete(self, query, context: ContextTypes.
        DEFAULT_TYPE, habit_id: int) ->None:
        """Confirm habit deletion."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.habit_repository import HabitRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        try:
            with get_optimized_session() as session:
                repo = HabitRepository(session)
                habit = repo.get_habit_by_id(habit_id)
                if habit:
                    repo.delete_habit_by_id(habit_id)
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_success_message(
                        f"Habit '{habit.name}' deleted successfully!", {
                        'Habit ID': habit_id, 'Action': 'deleted',
                        'Streak Lost': f'{habit.streak} days'}), parse_mode
                        ='MarkdownV2')
                else:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Habit #{habit_id} not found',
                        'The habit may have already been deleted.'),
                        parse_mode='MarkdownV2')
        except Exception as e:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to delete habit',
                f'Error: {str(e)}'), parse_mode='MarkdownV2')

    async def _handle_habit_add(self, query, context: ContextTypes.DEFAULT_TYPE
        ) ->None:
        """Handle habit add button click."""
        from larrybot.utils.ux_helpers import MessageFormatter
        await safe_edit(query.edit_message_text, MessageFormatter.
            format_info_message('Add New Habit', {'Command':
            '/habit_add <name>', 'Example': '/habit_add Morning Exercise',
            'Description': 'Create a new habit to track daily'}),
            parse_mode='MarkdownV2')

    async def _handle_habit_stats(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle habit statistics button click."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.habit_repository import HabitRepository
        from larrybot.utils.ux_helpers import MessageFormatter, ChartBuilder
        from datetime import datetime
        try:
            with get_optimized_session() as session:
                repo = HabitRepository(session)
                habits = repo.list_habits()
                if not habits:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        'No habits found',
                        'Use /habit_add to create your first habit'),
                        parse_mode='MarkdownV2')
                    return
                total_habits = len(habits)
                total_streak = sum(habit.streak for habit in habits)
                avg_streak = (total_streak / total_habits if total_habits >
                    0 else 0)
                best_habit = max(habits, key=lambda h: h.streak
                    ) if habits else None
                today = get_current_datetime().date()
                completed_today = 0
                for habit in habits:
                    if habit.last_completed:
                        if hasattr(habit.last_completed, 'date'):
                            last_date = habit.last_completed.date()
                        else:
                            last_date = habit.last_completed
                        if last_date == today:
                            completed_today += 1
                completion_rate = (completed_today / total_habits * 100 if 
                    total_habits > 0 else 0)
                message = f'📊 **Habit Statistics**\n\n'
                message += f'**Total Habits**: {total_habits}\n'
                message += f'**Total Streak Days**: {total_streak}\n'
                message += f'**Average Streak**: {avg_streak:.1f} days\n'
                message += (
                    f'**Completed Today**: {completed_today}/{total_habits}\n')
                message += f"**Today's Rate**: {completion_rate:.1f}%\n\n"
                if best_habit:
                    message += f'🏆 **Best Performer**\n'
                    message += (
                        f'• {MessageFormatter.escape_markdown(best_habit.name)}\n'
                        )
                    message += f'• Streak: {best_habit.streak} days\n\n'
                if habits:
                    streak_data = {habit.name: habit.streak for habit in habits
                        }
                    progress_chart = ChartBuilder.build_bar_chart(streak_data,
                        'Current Streaks', max_width=15)
                    message += f'📈 **Streak Overview**\n{progress_chart}\n'
                keyboard = [[UnifiedButtonBuilder.create_button(text=
                    '🔄 Refresh', callback_data='habit_refresh', button_type
                    =ButtonType.INFO)], [UnifiedButtonBuilder.create_button
                    (text='⬅️ Back to Habits', callback_data='habit_list',
                    button_type=ButtonType.INFO)]]
                await safe_edit(query.edit_message_text, message,
                    reply_markup=InlineKeyboardMarkup(keyboard), parse_mode
                    ='MarkdownV2')
        except Exception as e:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to load habit statistics',
                f'Error: {str(e)}'), parse_mode='MarkdownV2')

    async def _handle_habit_refresh(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle habit refresh button click."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.habit_repository import HabitRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        from datetime import datetime
        try:
            with get_optimized_session() as session:
                repo = HabitRepository(session)
                habits = repo.list_habits()
                if not habits:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        'No habits found',
                        'Use /habit_add to create your first habit'),
                        parse_mode='MarkdownV2')
                    return
                today = get_current_datetime().date()
                message = f'🔄 **All Habits** \\({len(habits)} found\\)\n\n'
                keyboard = []
                for i, habit in enumerate(habits, 1):
                    if habit.last_completed:
                        if hasattr(habit.last_completed, 'date'):
                            last_completed_date = habit.last_completed.date()
                        else:
                            last_completed_date = habit.last_completed
                        days_since_last = (today - last_completed_date).days
                        if days_since_last == 0:
                            status_emoji = '✅'
                            status_text = 'Completed today'
                            completed_today = True
                        elif days_since_last == 1:
                            status_emoji = '⚠️'
                            status_text = 'Missed yesterday'
                            completed_today = False
                        else:
                            status_emoji = '❌'
                            status_text = f'Missed {days_since_last} days'
                            completed_today = False
                    else:
                        status_emoji = '⏳'
                        status_text = 'Never completed'
                        completed_today = False
                    if habit.streak >= 30:
                        streak_emoji = '👑'
                    elif habit.streak >= 7:
                        streak_emoji = '🔥'
                    elif habit.streak >= 3:
                        streak_emoji = '📈'
                    else:
                        streak_emoji = '✅'
                    message += f"""{i}\\. {status_emoji} **{MessageFormatter.escape_markdown(habit.name)}**
"""
                    message += (
                        f'   {streak_emoji} Streak: {habit.streak} days\n')
                    message += f'   📅 {status_text}\n'
                    if habit.last_completed:
                        message += (
                            f"   🕐 Last: {MessageFormatter.escape_markdown(habit.last_completed.strftime('%Y-%m-%d'))}\n"
                            )
                    if habit.created_at:
                        message += (
                            f"   📅 Created: {MessageFormatter.escape_markdown(habit.created_at.strftime('%Y-%m-%d'))}\n"
                            )
                    message += '\n'
                    habit_buttons = []
                    if not completed_today:
                        habit_buttons.append(UnifiedButtonBuilder.
                            create_button(text='✅ Complete', callback_data=
                            f'habit_done:{habit.id}', button_type=
                            ButtonType.INFO))
                    habit_buttons.extend([UnifiedButtonBuilder.
                        create_button(text='📊 Progress', callback_data=
                        f'habit_progress:{habit.id}', button_type=
                        ButtonType.INFO), UnifiedButtonBuilder.
                        create_button(text='🗑️ Delete', callback_data=
                        f'habit_delete:{habit.id}', button_type=ButtonType.
                        INFO)])
                    keyboard.append(habit_buttons)
                keyboard.append([UnifiedButtonBuilder.create_button(text=
                    '➕ Add Habit', callback_data='habit_add', button_type=
                    ButtonType.INFO), UnifiedButtonBuilder.create_button(
                    text='📊 Statistics', callback_data='habit_stats',
                    button_type=ButtonType.INFO)])
                keyboard.append([UnifiedButtonBuilder.create_button(text=
                    '🔄 Refresh', callback_data='habit_refresh', button_type
                    =ButtonType.INFO), UnifiedButtonBuilder.create_button(
                    text='⬅️ Back', callback_data='nav_main', button_type=
                    ButtonType.INFO)])
                await safe_edit(query.edit_message_text, message,
                    reply_markup=InlineKeyboardMarkup(keyboard), parse_mode
                    ='MarkdownV2')
        except Exception as e:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to refresh habits',
                f'Error: {str(e)}'), parse_mode='MarkdownV2')

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE
        ) ->None:
        if not self._is_authorized(update):
            await update.message.reply_text(
                """🚫 **Unauthorized Access**

This is a single-user bot designed for personal use. Only the configured user can access this bot.

If you believe this is an error, please check your configuration."""
                )
            return
        
        user_first_name = (update.effective_user.first_name if update.
            effective_user.first_name else 'there')
        
        # Concise welcome message
        welcome_message = f"""🎉 **Welcome back, {user_first_name}!**

Ready to boost your productivity? Here's what you can do:"""
        
        # Streamlined button layout - 2x3 grid with essential actions
        keyboard = [
            [
                UnifiedButtonBuilder.create_button('➕ Add Task', 'add_task', ButtonType.PRIMARY),
                UnifiedButtonBuilder.create_button('📋 View Tasks', 'tasks_list', ButtonType.INFO)
            ],
            [
                UnifiedButtonBuilder.create_button('📅 Today', 'calendar_today', ButtonType.INFO),
                UnifiedButtonBuilder.create_button('🔄 Habits', 'menu_habits', ButtonType.INFO)
            ],
            [
                UnifiedButtonBuilder.create_button('⏰ Reminders', 'menu_reminders', ButtonType.INFO),
                UnifiedButtonBuilder.create_button('❓ Help', 'help_quick', ButtonType.SECONDARY)
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_message, parse_mode=
            'Markdown', reply_markup=reply_markup)

    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE
        ) ->None:
        if not self._is_authorized(update):
            await update.message.reply_text('🚫 Unauthorized access.')
            return
        commands = list(self.command_registry._commands.keys())
        command_metadata = {}
        for cmd in commands:
            metadata = self.command_registry.get_command_metadata(cmd)
            if metadata:
                command_metadata[cmd] = metadata
        categories = {}
        for cmd, metadata in command_metadata.items():
            category = metadata.category
            if category not in categories:
                categories[category] = []
            categories[category].append((cmd, metadata))
        help_text = '📋 *Available Commands*\n\n'
        category_order = [('tasks', 'Advanced Task Features'), ('task',
            'Basic Task Management'), ('client', 'Client Management'), (
            'habit', 'Habit Tracking'), ('calendar', 'Calendar Integration'
            ), ('reminder', 'Reminders'), ('analytics', 'Analytics'), (
            'system', 'System'), ('examples', 'Examples'), ('general',
            'General')]

        def escape_markdown(text: str) ->str:
            """Escape special characters that could break Markdown parsing."""
            if not text:
                return text
            escaped = text.replace('_', '\\_').replace('*', '\\*').replace('[',
                '\\[').replace(']', '\\]')
            escaped = escaped.replace('(', '\\(').replace(')', '\\)').replace(
                '~', '\\~').replace('`', '\\`')
            escaped = escaped.replace('>', '\\>').replace('#', '\\#').replace(
                '+', '\\+').replace('-', '\\-')
            escaped = escaped.replace('=', '\\=').replace('|', '\\|').replace(
                '{', '\\{').replace('}', '\\}')
            escaped = escaped.replace('.', '\\.').replace('!', '\\!')
            return escaped
        for category_key, category_name in category_order:
            if category_key in categories:
                help_text += f'*{escape_markdown(category_name)}:*\n'
                for cmd, metadata in sorted(categories[category_key]):
                    cmd_name = cmd.lstrip('/')
                    description = metadata.description or f'Handler for {cmd}'
                    safe_description = escape_markdown(description)
                    help_text += f'• `/{cmd_name}` \\- {safe_description}\n'
                help_text += '\n'
        uncategorized = []
        for cmd in commands:
            if cmd not in command_metadata:
                uncategorized.append(cmd)
        if uncategorized:
            help_text += '*Other Commands:*\n'
            for cmd in sorted(uncategorized):
                cmd_name = cmd.lstrip('/')
                help_text += f'• `/{cmd_name}`\n'
            help_text += '\n'
        help_text += f'*Total Commands*: {len(commands)}'
        try:
            await update.message.reply_text(escape_markdown_v2(help_text),
                parse_mode='MarkdownV2')
        except Exception as e:
            fallback_text = '📋 Available Commands\n\n'
            for category_key, category_name in category_order:
                if category_key in categories:
                    fallback_text += f'{category_name}:\n'
                    for cmd, metadata in sorted(categories[category_key]):
                        cmd_name = cmd.lstrip('/')
                        description = (metadata.description or
                            f'Handler for {cmd}')
                        fallback_text += f'• /{cmd_name} - {description}\n'
                    fallback_text += '\n'
            if uncategorized:
                fallback_text += 'Other Commands:\n'
                for cmd in sorted(uncategorized):
                    cmd_name = cmd.lstrip('/')
                    fallback_text += f'• /{cmd_name}\n'
                fallback_text += '\n'
            fallback_text += f'Total Commands: {len(commands)}'
            await update.message.reply_text(fallback_text)

    async def _dispatch_command(self, update: Update, context: ContextTypes
        .DEFAULT_TYPE) ->None:
        if not update.message or not update.message.text:
            return
        if not self._is_authorized(update):
            await update.message.reply_text('🚫 Unauthorized access.')
            return
        command = f"/{update.message.text.split()[0].lstrip('/')}"
        try:
            result = self.command_registry.dispatch(command, update, context)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            await update.message.reply_text(f'❌ Error: {e}')

    def run(self) ->None:
        try:
            loop = asyncio.get_event_loop()
            from larrybot.plugins.reminder import set_main_event_loop as set_reminder_loop
            from larrybot.scheduler import set_main_event_loop as set_scheduler_loop
            set_reminder_loop(loop)
            set_scheduler_loop(loop)
            print('Main event loop set for reminder handler and scheduler', flush=True)
        except RuntimeError:
            print('Could not set event loop before bot start', flush=True)
        from larrybot.scheduler import schedule_daily_report
        schedule_daily_report(self, self.config.ALLOWED_TELEGRAM_USER_ID,
            hour=8, minute=30)
        self.application.run_polling()

    async def run_async(self) ->None:
        """
        Async version of run() that integrates with the unified event loop.
        This allows for proper task management and graceful shutdown.
        """
        try:
            loop = asyncio.get_running_loop()
            from larrybot.plugins.reminder import set_main_event_loop as set_reminder_loop
            from larrybot.scheduler import set_main_event_loop as set_scheduler_loop
            set_reminder_loop(loop)
            set_scheduler_loop(loop)
            logger.info('Main event loop set for reminder handler and scheduler')
        except RuntimeError as e:
            logger.warning(f'Could not set event loop: {e}')
        
        # Schedule daily report for 8:30am
        from larrybot.scheduler import schedule_daily_report
        schedule_daily_report(self, self.config.ALLOWED_TELEGRAM_USER_ID, hour=8, minute=30)
        logger.info('📅 Daily report scheduled for 8:30 AM')
        
        from larrybot.core.task_manager import get_task_manager
        task_manager = get_task_manager()
        try:
            await self.application.initialize()
            await self.application.start()
            logger.info('🚀 Telegram bot started successfully')
            await self.application.updater.start_polling()
            try:
                logger.info('🔄 Bot running - waiting for shutdown signal...')
                while not task_manager.is_shutdown_requested:
                    try:
                        await asyncio.wait_for(task_manager._shutdown_event
                            .wait(), timeout=0.5)
                        break
                    except asyncio.TimeoutError:
                        continue
                logger.info('🛑 Shutdown signal received - stopping bot...')
            except asyncio.CancelledError:
                logger.info('🛑 Bot task cancelled')
                raise
        except asyncio.CancelledError:
            logger.info('🛑 Bot cancelled gracefully')
            raise
        except Exception as e:
            logger.error(f'❌ Bot error: {e}')
            raise
        finally:
            try:
                logger.info('🧹 Stopping bot updater...')
                await self.application.updater.stop()
                logger.info('🧹 Stopping bot application...')
                await self.application.stop()
                logger.info('🧹 Shutting down bot application...')
                await self.application.shutdown()
                try:
                    from larrybot.plugins.reminder import cleanup_reminder_handler
                    await cleanup_reminder_handler()
                except Exception as e:
                    logger.warning(
                        f'Error during reminder handler cleanup: {e}')
                logger.info('✅ Bot shutdown completed')
            except Exception as e:
                logger.error(f'Error during bot shutdown: {e}')

    async def _handle_text_message(self, update: Update, context:
        ContextTypes.DEFAULT_TYPE) ->None:
        """Handle text messages with enhanced narrative processing and task editing."""
        user_message = update.message.text.strip(
            ) if update.message and update.message.text else None
        if not user_message:
            return
        if 'editing_task_id' in context.user_data:
            await self._handle_task_edit_mode(update, context, user_message)
            return
        if 'task_creation_state' in context.user_data:
            from larrybot.plugins.tasks import handle_narrative_task_creation
            await handle_narrative_task_creation(update, context, user_message)
            return
        user_id = update.effective_user.id if update.effective_user else None
        processed_input = self.enhanced_narrative_processor.process_input(
            user_message, user_id)
        context.user_data['nlp_intent'] = processed_input.intent.value
        context.user_data['nlp_entities'] = processed_input.entities
        context.user_data['nlp_sentiment'] = processed_input.context.sentiment
        if processed_input.confidence > 0.5:
            await self._handle_narrative_intent(update, context,
                processed_input)
        else:
            await self._handle_low_confidence_input(update, context,
                processed_input)

    async def _handle_task_edit_mode(self, update: Update, context:
        ContextTypes.DEFAULT_TYPE, user_message: str) ->None:
        """Handle text input when user is in task editing mode."""
        task_id = context.user_data['editing_task_id']
        new_description = user_message
        if not new_description:
            await update.message.reply_text(MessageFormatter.
                format_error_message('Description cannot be empty',
                'Please provide a valid task description.'))
            return
        await self._process_task_edit(update, context, task_id, new_description
            )

    async def _handle_narrative_intent(self, update: Update, context:
        ContextTypes.DEFAULT_TYPE, processed_input) ->None:
        """Handle narrative input based on detected intent."""
        from larrybot.nlp.enhanced_narrative_processor import IntentType
        await update.message.reply_text(processed_input.response_message,
            parse_mode='MarkdownV2')
        if processed_input.suggested_command:
            await self._execute_suggested_command(update, context,
                processed_input)

    async def _handle_low_confidence_input(self, update: Update, context:
        ContextTypes.DEFAULT_TYPE, processed_input) ->None:
        """Handle input with low confidence - show help and context-aware command suggestions."""
        suggestions = []
        user_context = context.user_data
        if 'editing_task_id' in user_context:
            suggestions.append(
                '/edit <new description> — Edit the current task')
            suggestions.append('/cancel — Cancel editing')
        elif user_context.get('current_context'
            ) == 'task_view' or user_context.get('last_viewed_task_id'):
            suggestions.append('/edit <desc> — Edit this task')
            suggestions.append('/done — Mark as complete')
            suggestions.append('/delete — Delete this task')
        elif user_context.get('current_context') == 'tasks':
            suggestions.append('/add <desc> — Add a new task')
            suggestions.append('/list — Show all tasks')
            suggestions.append('/search <query> — Search tasks')
            suggestions.append('/analytics — View analytics')
        else:
            suggestions.append('/add <desc> — Add a new task')
            suggestions.append('/list — Show all tasks')
            suggestions.append('/remind <desc> — Add a reminder')
            suggestions.append('/help — Show all commands')
        if '/help — Show all commands' not in suggestions:
            suggestions.append('/help — Show all commands')
        if '/list — Show all tasks' not in suggestions:
            suggestions.append('/list — Show all tasks')
        help_message = (
            """🤔 I'm not sure what you'd like to do. Here are some things you can try:

"""
             + '\n'.join(f'• {s}' for s in suggestions))
        await update.message.reply_text(help_message)

    async def _execute_suggested_command(self, update: Update, context:
        ContextTypes.DEFAULT_TYPE, processed_input) ->None:
        """Execute the suggested command with extracted parameters."""
        from larrybot.plugins.tasks import add_task
        from larrybot.plugins.tasks import list_tasks
        from larrybot.plugins.tasks import search_tasks
        from larrybot.plugins.reminder import add_reminder
        # Removed incorrect import - analytics functionality is handled by advanced_tasks plugin
        command = processed_input.suggested_command
        params = processed_input.suggested_parameters
        try:
            if command == '/add' and params.get('description'):
                description = params['description']
                priority = params.get('priority', 'Medium')
                category = params.get('category')
                due_date = params.get('due_date')
                await add_task(update, context, description, priority,
                    category, due_date)
            elif command == '/list':
                priority = params.get('priority')
                category = params.get('category')
                await list_tasks(update, context, priority, category)
            elif command == '/search' and params.get('query'):
                query = params['query']
                await search_tasks(update, context, query)
            elif command == '/remind' and params.get('task_name'):
                task_name = params['task_name']
                due_date = params.get('due_date')
                await add_reminder(update, context, task_name, due_date)
            elif command == '/analytics':
                # Analytics functionality is handled by the advanced_tasks plugin
                # The user should use /analytics command directly
                await update.message.reply_text(
                    "📊 Use the /analytics command to view task analytics.",
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            logger.error(f'Error executing suggested command {command}: {e}')
            await update.message.reply_text(
                "❌ Sorry, I couldn't execute that command automatically. Please try using the command directly."
                )



    async def _process_task_edit(self, update: Update, context:
        ContextTypes.DEFAULT_TYPE, task_id: int, new_description: str) ->None:
        """Process the actual task editing."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.core.event_utils import emit_task_event
        from larrybot.utils.ux_helpers import MessageFormatter
        from datetime import datetime
        try:
            with get_optimized_session() as session:
                repo = TaskRepository(session)
                task = repo.edit_task(task_id, new_description)
                if task:
                    emit_task_event(None, 'task_edited', task)
                    del context.user_data['editing_task_id']
                    await update.message.reply_text(MessageFormatter.
                        format_success_message(
                        '✏️ Task updated successfully!', {'Task': task.
                        description, 'ID': task_id, 'Status': 'Updated',
                        'Modified': get_current_datetime().strftime(
                        '%Y-%m-%d %H:%M')}), parse_mode='MarkdownV2')
                else:
                    await update.message.reply_text(MessageFormatter.
                        format_error_message(f'Task ID {task_id} not found',
                        "The task may have already been deleted or doesn't exist."
                        ), parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f'Error editing task {task_id}: {e}')
            await update.message.reply_text(MessageFormatter.
                format_error_message('Error updating task',
                'Please try again or use /edit command.'), parse_mode=
                'MarkdownV2')

    async def _handle_tasks_refresh(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle task list refresh with timeout protection and loading indicator."""
        try:
            await safe_edit(query.edit_message_text,
                '🔄 Refreshing tasks\\.\\.\\.', parse_mode='MarkdownV2')
            await asyncio.wait_for(self._handle_tasks_refresh_operation(
                query, context), timeout=10.0)
        except asyncio.TimeoutError:
            logger.error('Tasks refresh timeout')
            try:
                await safe_edit(query.edit_message_text, MessageFormatter.
                    format_error_message('⏱️ Refresh timed out',
                    'Please try the command again\\.'), parse_mode='MarkdownV2'
                    )
            except Exception as e:
                logger.error(f'Failed to send timeout message: {e}')
        except Exception as e:
            logger.error(f'Error refreshing tasks: {e}')
            try:
                await safe_edit(query.edit_message_text, MessageFormatter.
                    format_error_message('❌ Refresh failed',
                    'Please try again later.'), parse_mode='MarkdownV2')
            except Exception as nested_e:
                logger.error(f'Failed to send error message: {nested_e}')
                try:
                    await safe_edit(query.edit_message_text,
                        '❌ Refresh failed. Please try again later.',
                        parse_mode=None)
                except Exception:
                    pass

    async def _handle_tasks_refresh_operation(self, query, context:
        ContextTypes.DEFAULT_TYPE) ->None:
        """Handle the actual tasks refresh operation with progressive disclosure and smart suggestions."""
        from larrybot.utils.ux_helpers import MessageFormatter
        from larrybot.utils.enhanced_ux_helpers import MessageLayoutBuilder, UnifiedButtonBuilder, ButtonType
        with get_optimized_session() as session:
            repo = TaskRepository(session)
            tasks = repo.list_incomplete_tasks()
            if not tasks:
                message = (
                    '📋 **All Tasks Complete\\!** 🎉\n\nNo incomplete tasks found\\.'
                    )
                keyboard = UnifiedButtonBuilder.build_entity_keyboard(entity_id
                    =0, entity_type='add_task', available_actions=[],
                    custom_actions=[{'text': '➕ Add New Task',
                    'callback_data': 'add_task', 'type': ButtonType.PRIMARY,
                    'emoji': '➕'}, {'text': '🏠 Main Menu', 'callback_data':
                    'nav_main', 'type': ButtonType.SECONDARY, 'emoji': '🏠'}])
            else:
                message = MessageLayoutBuilder.build_progressive_list(items
                    =tasks, max_visible=5, title='Incomplete Tasks')
                suggestions = []
                high_priority_count = sum(1 for t in tasks if getattr(t,
                    'priority', 'Medium') in ['High', 'Critical'])
                from larrybot.utils.datetime_utils import ensure_timezone_aware
                now_dt = get_current_datetime()
                overdue_count = sum(1 for t in tasks if t.due_date and 
                    ensure_timezone_aware(t.due_date) < now_dt)
                if high_priority_count > 0:
                    suggestions.append(
                        f'⚠️ **{high_priority_count} high priority tasks** need attention'
                        )
                if overdue_count > 0:
                    suggestions.append(
                        f'🚨 **{overdue_count} overdue tasks** require immediate action'
                        )
                if len(tasks) > 10:
                    suggestions.append(
                        '💡 **Tip:** Use filters to focus on specific tasks')
                if suggestions:
                    escaped_suggestions = [MessageFormatter.escape_markdown
                        (suggestion) for suggestion in suggestions]
                    message += '\n\n' + '\n'.join(escaped_suggestions)
                custom_actions = [{'text': '➕ Add Task', 'callback_data':
                    'add_task', 'type': ButtonType.PRIMARY, 'emoji': '➕'},
                    {'text': '🔍 Search', 'callback_data': 'tasks_search',
                    'type': ButtonType.SECONDARY, 'emoji': '🔍'}]
                if len(tasks) > 5:
                    custom_actions.append({'text': '🔧 Filter',
                        'callback_data': 'tasks_filter', 'type': ButtonType
                        .SECONDARY, 'emoji': '🔧'})
                if tasks:
                    custom_actions.append({'text': '📊 Analytics',
                        'callback_data': 'tasks_analytics', 'type':
                        ButtonType.INFO, 'emoji': '📊'})
                keyboard = UnifiedButtonBuilder.build_list_keyboard(items=[
                    {'id': t.id, 'description': t.description} for t in
                    tasks[:5]], item_type='task', max_items=5,
                    show_navigation=True, navigation_actions=[])
                existing_buttons = list(keyboard.inline_keyboard)
                custom_action_buttons = [UnifiedButtonBuilder.create_button
                    (text=action['text'], callback_data=action[
                    'callback_data'], button_type=action['type'],
                    custom_emoji=action['emoji']) for action in custom_actions]
                existing_buttons.append(custom_action_buttons)
                keyboard = InlineKeyboardMarkup(existing_buttons)
            await safe_edit(query.edit_message_text, message, reply_markup=
                keyboard, parse_mode='MarkdownV2')

    async def _handle_task_view(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """Show detailed view of a task with progressive disclosure and smart suggestions."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.services.task_attachment_service import TaskAttachmentService
        from larrybot.storage.task_attachment_repository import TaskAttachmentRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        from larrybot.utils.enhanced_ux_helpers import ProgressiveDisclosureBuilder, ContextAwareButtonBuilder
        try:
            with get_optimized_session() as session:
                repo = TaskRepository(session)
                task = repo.get_task_by_id(task_id)
                if not task:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Task ID {task_id} not found',
                        "The task may have already been deleted or doesn't exist."
                        ), parse_mode='MarkdownV2')
                    return

                attachment_service = TaskAttachmentService(TaskAttachmentRepository(session), repo)
                attachments_result = await attachment_service.get_task_attachments(task_id)
                attachment_count = len(attachments_result['data']['attachments']) if attachments_result['success'] else 0

                task_data = {'id': task.id, 'description': task.description,
                    'status': getattr(task, 'status', 'Todo'), 'priority':
                    getattr(task, 'priority', 'Medium'), 'due_date':
                    getattr(task, 'due_date', None), 'category': getattr(
                    task, 'category', None), 'tags': getattr(task, 'tags',
                    None), 'created_at': getattr(task, 'created_at', None),
                    'attachment_count': attachment_count}
                details = {k: v for k, v in task_data.items() if v is not
                    None and k != 'id'}
                suggestions = []
                if task_data['status'] == 'Todo' and not task_data.get(
                    'due_date'):
                    suggestions.append(
                        '💡 **Suggestion:** Add a due date to track progress')
                if task_data['priority'] == 'Medium' and task_data['status'
                    ] == 'Todo':
                    suggestions.append(
                        '💡 **Suggestion:** Consider setting priority for better organization'
                        )
                if task_data['status'] == 'In Progress':
                    suggestions.append(
                        '💡 **Suggestion:** Use time tracking to monitor progress'
                        )
                # Use new UX formatting for task details
                message = MessageFormatter.format_task_details_for_view(details)
                if suggestions:
                    escaped_suggestions = [MessageFormatter.escape_markdown(suggestion) for suggestion in suggestions]
                    message += '\n\n' + '\n'.join(escaped_suggestions)
                keyboard = (ProgressiveDisclosureBuilder.
                    build_progressive_task_keyboard(task_id=task_id,
                    task_data=task_data, attachment_count=attachment_count))
                await safe_edit(query.edit_message_text, message,
                    reply_markup=keyboard, parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f'Error showing task view for {task_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Error showing task details',
                'Please try again or use /list command.'), parse_mode=
                'MarkdownV2')

    async def _handle_add_task(self, query, context: ContextTypes.DEFAULT_TYPE
        ) ->None:
        """Handle add task button press - start the narrative task creation flow."""
        from larrybot.plugins.tasks import narrative_add_task_handler
        from larrybot.utils.ux_helpers import MessageFormatter
        from unittest.mock import Mock
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Create a mock update object for the narrative handler
            class MockUpdate:
                def __init__(self, query):
                    self.effective_user = query.from_user
                    self.message = Mock()
                    self.message.reply_text = query.edit_message_text
            
            # Start the narrative flow
            mock_update = MockUpdate(query)
            await narrative_add_task_handler(mock_update, context)
            
        except Exception as e:
            # Fallback to original behavior if narrative flow fails
            logger.error(f"Error starting narrative task creation: {e}")
            message = '📝 **Add New Task**\n\n'
            message += '**How to add a task:**\n'
            message += '• Use `/addtask` for guided task creation\n'
            message += '• Use `/add <description>` for a simple task\n'
            message += '• Use `/add <description> priority:<level>` for priority\n'
            message += '• Use `/add <description> due:<date>` for due date\n'
            message += (
                '• Use `/add <description> client:<name>` for client assignment\n\n'
                )
            message += '**Examples:**\n'
            message += '• `/addtask` - Start guided task creation\n'
            message += '• `/add Review quarterly reports`\n'
            message += '• `/add Call client priority:High due:tomorrow`\n\n'
            message += '**Tip:** Try `/addtask` for the best experience!'
            escaped_message = MessageFormatter.escape_markdown(message)
            keyboard = InlineKeyboardMarkup([[UnifiedButtonBuilder.
                create_button(text='📋 View Tasks', callback_data=
                'tasks_refresh', button_type=ButtonType.INFO),
                UnifiedButtonBuilder.create_button(text='❌ Cancel',
                callback_data='cancel_action', button_type=ButtonType.INFO)]])
            await safe_edit(query.edit_message_text, escaped_message,
                reply_markup=keyboard, parse_mode='MarkdownV2')

    async def _handle_help_quick(self, query, context: ContextTypes.DEFAULT_TYPE
        ) ->None:
        """Handle quick help button click."""
        try:
            help_message = """❓ **Quick Help**

Choose what you'd like to learn about:"""
            
            keyboard = [
                [
                    UnifiedButtonBuilder.create_button('📋 Tasks', 'help_tasks', ButtonType.INFO),
                    UnifiedButtonBuilder.create_button('📅 Calendar', 'help_calendar', ButtonType.INFO)
                ],
                [
                    UnifiedButtonBuilder.create_button('🔄 Habits', 'help_habits', ButtonType.INFO),
                    UnifiedButtonBuilder.create_button('👥 Clients', 'help_clients', ButtonType.INFO)
                ],
                [
                    UnifiedButtonBuilder.create_button('⏰ Reminders', 'help_reminders', ButtonType.INFO),
                    UnifiedButtonBuilder.create_button('📊 Analytics', 'help_analytics', ButtonType.INFO)
                ],
                [
                    UnifiedButtonBuilder.create_button('🔧 Advanced', 'help_advanced', ButtonType.SECONDARY),
                    UnifiedButtonBuilder.create_button('🏠 Back', 'nav_main', ButtonType.SECONDARY)
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(help_message, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception as e:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to show help menu',
                f'Error: {str(e)}'), parse_mode='MarkdownV2')

    async def _handle_help_section(self, query, context: ContextTypes.DEFAULT_TYPE
        ) ->None:
        """Handle help section button clicks."""
        try:
            callback_data = query.data
            section = callback_data.split('_')[1] if '_' in callback_data else 'general'
            
            help_sections = {
                'tasks': {
                    'title': '📋 **Task Management**',
                    'content': """**Quick Commands:**
• `/addtask <description>` - Create a new task
• `/list` - View all tasks
• `/done <id>` - Mark task complete
• `/edit <id> <new description>` - Edit task

**Advanced Features:**
• Set priorities: `/addtask "Call client" priority:High`
• Add due dates: `/addtask "Review docs" due:tomorrow`
• Assign to clients: `/addtask "Project work" client:John`
• Time tracking: `/time_start <id>` and `/time_stop <id>`"""
                },
                'calendar': {
                    'title': '📅 **Calendar Integration**',
                    'content': """**Calendar Commands:**
• `/calendar_today` - View today's schedule
• `/calendar_week` - This week's agenda
• `/calendar_sync` - Sync with Google Calendar
• `/calendar_settings` - Configure calendar

**Smart Scheduling:**
• Tasks with due dates appear in calendar
• Automatic time zone handling
• Integration with Google Calendar
• Reminder notifications"""
                },
                'habits': {
                    'title': '🔄 **Habit Tracking**',
                    'content': """**Habit Commands:**
• `/habit_add <name> <description>` - Create habit
• `/habit_done <id>` - Mark habit complete
• `/habit_stats` - View habit progress
• `/habit_list` - List all habits

**Features:**
• Daily streak tracking
• Progress visualization
• Habit analytics
• Reminder notifications"""
                },
                'clients': {
                    'title': '👥 **Client Management**',
                    'content': """**Client Commands:**
• `/client_add <name>` - Add new client
• `/client_tasks <name>` - View client's tasks
• `/client_analytics <name>` - Client insights
• `/client_list` - List all clients

**Benefits:**
• Organize tasks by client
• Track time per client
• Client-specific analytics
• Project management"""
                },
                'reminders': {
                    'title': '⏰ **Reminders**',
                    'content': """**Reminder Commands:**
• `/addreminder <description> <datetime>` - Create reminder
• `/reminders` - View active reminders
• `/reminder_snooze <id> <duration>` - Snooze reminder
• `/reminder_dismiss <id>` - Dismiss reminder

**Features:**
• Flexible scheduling
• Snooze options
• Notification system
• Integration with tasks"""
                },
                'analytics': {
                    'title': '📊 **Analytics & Insights**',
                    'content': """**Analytics Commands:**
• `/analytics` - General productivity insights
• `/analytics detailed` - Detailed breakdown
• `/analytics advanced` - Advanced metrics
• `/productivity_report` - Full report

**Metrics Tracked:**
• Task completion rates
• Time tracking data
• Habit streaks
• Client productivity
• Performance trends"""
                },
                'advanced': {
                    'title': '🔧 **Advanced Features**',
                    'content': """**Advanced Commands:**
• `/bulk_operations` - Manage multiple tasks
• `/search --advanced` - Advanced search
• `/filter_advanced` - Complex filtering
• `/time_tracking` - Detailed time analysis

**Power Features:**
• Bulk task operations
• Advanced filtering
• File attachments
• Task dependencies
• Subtasks
• Performance monitoring"""
                }
            }
            
            if section in help_sections:
                content = help_sections[section]
                message = f"{content['title']}\n\n{content['content']}"
                
                keyboard = [
                    [UnifiedButtonBuilder.create_button('🏠 Back to Help', 'help_quick', ButtonType.SECONDARY)]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                await query.edit_message_text("❓ Help section not found. Use /help for full command reference.", parse_mode='Markdown')
                
        except Exception as e:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to show help section',
                f'Error: {str(e)}'), parse_mode='MarkdownV2')

    async def _handle_client_view(self, query, context: ContextTypes.
        DEFAULT_TYPE, client_id: int) ->None:
        """Show detailed view of a client with action buttons and navigation."""
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.client_repository import ClientRepository
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        try:
            with get_optimized_session() as session:
                client_repo = ClientRepository(session)
                task_repo = TaskRepository(session)
                client = client_repo.get_client_by_id(client_id)
                if not client:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Client ID {client_id} not found',
                        "The client may have already been deleted or doesn't exist."
                        ), parse_mode='MarkdownV2')
                    return
                tasks = task_repo.get_tasks_by_client(client.name)
                completed_tasks = sum(1 for t in tasks if t.done)
                pending_tasks = len(tasks) - completed_tasks
                completion_rate = completed_tasks / len(tasks
                    ) * 100 if tasks else 0
                details = {'Name': client.name, 'ID': client.id, 'Created':
                    client.created_at.strftime('%Y-%m-%d %H:%M') if client.
                    created_at else None, 'Total Tasks': len(tasks),
                    'Completed': completed_tasks, 'Pending': pending_tasks,
                    'Completion Rate': f'{completion_rate:.1f}%'}
                details = {k: v for k, v in details.items() if v is not None}
                message = MessageFormatter.format_success_message(
                    'Client Details', details)
                keyboard = InlineKeyboardMarkup([[UnifiedButtonBuilder.
                    create_button(text='✏️ Edit', callback_data=
                    f'client_edit:{client.id}', button_type=ButtonType.INFO
                    ), UnifiedButtonBuilder.create_button(text='🗑️ Delete',
                    callback_data=f'client_delete:{client.id}', button_type
                    =ButtonType.INFO), UnifiedButtonBuilder.create_button(
                    text='📊 Analytics', callback_data=
                    f'client_analytics:{client.id}', button_type=ButtonType
                    .INFO)], [UnifiedButtonBuilder.create_button(text=
                    '⬅️ Back to List', callback_data='client_refresh',
                    button_type=ButtonType.INFO)]])
                await safe_edit(query.edit_message_text, message,
                    reply_markup=keyboard, parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f'Error showing client view for {client_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Error showing client details',
                'Please try again or use /allclients command.'), parse_mode
                ='MarkdownV2')

    async def _handle_client_edit(self, query, context: ContextTypes.
        DEFAULT_TYPE, client_id: int) ->None:
        """Handle client edit action."""
        try:
            from larrybot.plugins.client import edit_client_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(client_id), 'Updated Name']
            await edit_client_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error editing client {client_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to edit client',
                'Please try again or use /editclient command.'), parse_mode
                ='MarkdownV2')

    async def _handle_reminder_callback(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle reminder-related callback queries."""
        callback_data = query.data
        if callback_data == 'reminder_add':
            await self._handle_reminder_add(query, context)
        elif callback_data == 'reminder_stats':
            await self._handle_reminder_stats(query, context)
        elif callback_data == 'reminder_refresh':
            await self._handle_reminder_refresh(query, context)
        elif callback_data == 'reminder_dismiss':
            await self._handle_reminder_dismiss(query, context)
        elif callback_data.startswith('reminder_snooze:'):
            parts = callback_data.split(':')
            reminder_id = int(parts[1])
            duration = parts[2] if len(parts) > 2 else '1h'
            await self._handle_reminder_snooze(query, context, reminder_id,
                duration)
        elif callback_data.startswith('reminder_delete:'):
            reminder_id = int(callback_data.split(':')[1])
            await self._handle_reminder_delete(query, context, reminder_id)
        elif callback_data.startswith('reminder_complete:'):
            reminder_id = int(callback_data.split(':')[1])
            await self._handle_reminder_complete(query, context, reminder_id)
        elif callback_data.startswith('reminder_edit:'):
            reminder_id = int(callback_data.split(':')[1])
            await self._handle_reminder_edit(query, context, reminder_id)
        elif callback_data.startswith('reminder_reactivate:'):
            reminder_id = int(callback_data.split(':')[1])
            await self._handle_reminder_reactivate(query, context, reminder_id)
        else:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Unknown reminder action',
                'Please use the /reminders command for now.'), parse_mode=
                'MarkdownV2')

    async def _handle_attachment_callback(self, query, context:
        ContextTypes.DEFAULT_TYPE) ->None:
        """Handle attachment-related callback queries."""
        callback_data = query.data
        if callback_data.startswith('attachment_list:'):
            task_id = int(callback_data.split(':')[1])
            await self._list_task_attachments(query, context, task_id)
        elif callback_data.startswith('attachment_download:'):
            attachment_id = int(callback_data.split(':')[1])
            await self._handle_attachment_download(query, context, attachment_id)
        elif callback_data.startswith('attachment_edit_desc:'):
            attachment_id = int(callback_data.split(':')[1])
            await self._handle_attachment_edit_desc(query, context,
                attachment_id)
        elif callback_data.startswith('attachment_details:'):
            attachment_id = int(callback_data.split(':')[1])
            await self._handle_attachment_details(query, context, attachment_id
                )
        elif callback_data.startswith('attachment_remove:'):
            attachment_id = int(callback_data.split(':')[1])
            await self._handle_attachment_remove(query, context, attachment_id)
        elif callback_data.startswith('attachment_stats:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_attachment_stats(query, context, task_id)
        elif callback_data.startswith('attachment_add_desc:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_attachment_add_desc(query, context, task_id)
        elif callback_data.startswith('attachment_bulk_remove:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_attachment_bulk_remove(query, context, task_id)
        elif callback_data.startswith('attachment_export:'):
            task_id = int(callback_data.split(':')[1])
            await self._handle_attachment_export(query, context, task_id)

    async def _list_task_attachments(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """List attachments for a given task."""
        from larrybot.services.task_attachment_service import TaskAttachmentService
        from larrybot.storage.db import get_session
        from larrybot.storage.task_attachment_repository import TaskAttachmentRepository
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
        from telegram import InlineKeyboardMarkup

        session = next(get_session())
        attachment_service = TaskAttachmentService(TaskAttachmentRepository(session), TaskRepository(session))
        result = await attachment_service.get_task_attachments(task_id)

        if result['success'] and result['data']['attachments']:
            attachments = result['data']['attachments']
            message = f"📎 **Attachments for Task #{task_id}**\n\n"
            for att in attachments:
                message += f"📄 {MessageFormatter.escape_markdown(att['filename'])} ({att['size'] // 1024} KB)\n"
            
            # Build keyboard with download buttons for each attachment
            buttons = []
            for attachment in attachments:
                button = UnifiedButtonBuilder.create_button(
                    text=f"📥 {attachment['filename']}",
                    callback_data=f"attachment_download:{attachment['id']}",
                    button_type=ButtonType.INFO
                )
                buttons.append([button])
            
            # Add back button
            back_button = UnifiedButtonBuilder.create_button(
                text="🔙 Back to Task",
                callback_data=f"task_view:{task_id}",
                button_type=ButtonType.SECONDARY
            )
            buttons.append([back_button])
            
            keyboard = InlineKeyboardMarkup(buttons)
            await safe_edit(query.edit_message_text, MessageFormatter.escape_markdown(message), reply_markup=keyboard, parse_mode='MarkdownV2')
        else:
            # No attachments found
            message = f"📎 **No Attachments Found**\n\nTask #{task_id} has no attachments."
            back_button = UnifiedButtonBuilder.create_button(
                text="🔙 Back to Task",
                callback_data=f"task_view:{task_id}",
                button_type=ButtonType.SECONDARY
            )
            keyboard = InlineKeyboardMarkup([[back_button]])
            await safe_edit(query.edit_message_text, MessageFormatter.escape_markdown(message), reply_markup=keyboard, parse_mode='MarkdownV2')

    async def _handle_attachment_download(self, query, context: ContextTypes.DEFAULT_TYPE, attachment_id: int) -> None:
        """Handle attachment download."""
        from larrybot.services.task_attachment_service import TaskAttachmentService
        from larrybot.storage.db import get_session
        from larrybot.storage.task_attachment_repository import TaskAttachmentRepository
        from larrybot.storage.task_repository import TaskRepository
        import io
        import os
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Starting attachment download for ID: {attachment_id}")

        try:
            session = next(get_session())
            attachment_repository = TaskAttachmentRepository(session)
            attachment_service = TaskAttachmentService(attachment_repository, TaskRepository(session))
            result = await attachment_service.get_attachment_by_id(attachment_id)

            logger.info(f"Service result: {result}")

            if result['success']:
                attachment = attachment_repository.get_attachment_by_id(attachment_id)
                logger.info(f"Retrieved attachment: {attachment}")
                
                if attachment and os.path.exists(attachment.file_path):
                    logger.info(f"File exists at path: {attachment.file_path}")
                    try:
                        with open(attachment.file_path, 'rb') as f:
                            file_data = f.read()
                        
                        logger.info(f"Read file data, size: {len(file_data)} bytes")
                        
                        await context.bot.send_document(
                            chat_id=query.message.chat.id,
                            document=io.BytesIO(file_data),
                            filename=attachment.original_filename
                        )
                        logger.info("File sent successfully")
                        await query.answer("File sent successfully!")
                    except Exception as e:
                        logger.error(f"Error reading/sending file: {e}")
                        await query.answer(f"Error reading file: {str(e)}", show_alert=True)
                else:
                    logger.error(f"File not found. Attachment: {attachment}, Path exists: {os.path.exists(attachment.file_path) if attachment else 'No attachment'}")
                    await query.answer("File not found on disk.", show_alert=True)
            else:
                logger.error(f"Service call failed: {result}")
                await query.answer("Could not retrieve attachment.", show_alert=True)
        except Exception as e:
            logger.error(f"Unexpected error in attachment download: {e}")
            await query.answer(f"Unexpected error: {str(e)}", show_alert=True)

    async def _handle_calendar_callback(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle calendar-related callback queries."""
        callback_data = query.data
        if callback_data == 'calendar_today':
            await self._handle_calendar_today(query, context)
        elif callback_data == 'calendar_week':
            await self._handle_calendar_week(query, context)
        elif callback_data == 'calendar_month':
            await self._handle_calendar_month(query, context)
        elif callback_data == 'calendar_upcoming':
            await self._handle_calendar_upcoming(query, context)
        elif callback_data == 'calendar_sync':
            await self._handle_calendar_sync(query, context)
        elif callback_data == 'calendar_settings':
            await self._handle_calendar_settings(query, context)
        # calendar_refresh is now handled by the registry
        else:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Unknown calendar action',
                'Please use the calendar commands for now.'), parse_mode=
                'MarkdownV2')

    async def _handle_filter_callback(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle filter-related callback queries."""
        callback_data = query.data
        if callback_data == 'filter_date_range':
            await self._handle_filter_date_range(query, context)
        elif callback_data == 'filter_priority':
            await self._handle_filter_priority(query, context)
        elif callback_data == 'filter_status':
            await self._handle_filter_status(query, context)
        elif callback_data == 'filter_tags':
            await self._handle_filter_tags(query, context)
        elif callback_data == 'filter_category':
            await self._handle_filter_category(query, context)
        elif callback_data == 'filter_time':
            await self._handle_filter_time(query, context)
        elif callback_data == 'filter_advanced_search':
            await self._handle_filter_advanced_search(query, context)
        elif callback_data == 'filter_save':
            await self._handle_filter_save(query, context)
        else:
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Unknown filter action',
                'Please use the filter commands for now.'), parse_mode=
                'MarkdownV2')

    async def _handle_bulk_status_update(self, query, context: ContextTypes
        .DEFAULT_TYPE, status: str) ->None:
        """Handle bulk status update operations."""
        await safe_edit(query.edit_message_text, MessageFormatter.
            format_info_message(f'🔄 Bulk Status Update: {status}', {
            'Status': status, 'Instructions': 'To use bulk status updates:',
            'Command': f'/bulk_status <task_ids> {status}', 'Example':
            f'/bulk_status 1,2,3 {status}', 'Note':
            'Select tasks first, then apply the status change'}),
            parse_mode='MarkdownV2')

    async def _handle_bulk_priority_update(self, query, context:
        ContextTypes.DEFAULT_TYPE, priority: str) ->None:
        """Handle bulk priority update operations."""
        await safe_edit(query.edit_message_text, MessageFormatter.
            format_info_message(f'🎯 Bulk Priority Update: {priority}', {
            'Priority': priority, 'Instructions':
            'To use bulk priority updates:', 'Command':
            f'/bulk_priority <task_ids> {priority}', 'Example':
            f'/bulk_priority 1,2,3 {priority}', 'Note':
            'Select tasks first, then apply the priority change'}),
            parse_mode='MarkdownV2')

    async def _handle_bulk_operations_back(self, query, context:
        ContextTypes.DEFAULT_TYPE) ->None:
        """Handle back navigation from bulk operations."""
        from larrybot.utils.ux_helpers import KeyboardBuilder
        await safe_edit(query.edit_message_text,
            '📋 **Bulk Operations**\n\nSelect an operation:', reply_markup=
            KeyboardBuilder.build_bulk_operations_keyboard(), parse_mode=
            'MarkdownV2')

    async def _handle_reminder_add(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle reminder add action."""
        try:
            from larrybot.plugins.reminder import add_reminder_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = ['Test reminder', '1h']
            await add_reminder_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error adding reminder: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to add reminder',
                'Please try again or use /addreminder command.'),
                parse_mode='MarkdownV2')

    async def _handle_reminder_stats(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle reminder stats action."""
        try:
            from larrybot.plugins.reminder import reminder_stats_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await reminder_stats_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error showing reminder stats: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to load reminder statistics',
                'Please try again or use /reminder_stats command.'),
                parse_mode='MarkdownV2')

    async def _handle_reminder_refresh(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle reminder refresh action."""
        try:
            from larrybot.plugins.reminder import list_reminders_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await list_reminders_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error refreshing reminders: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to refresh reminders',
                'Please try again or use /reminders command.'), parse_mode=
                'MarkdownV2')

    async def _handle_reminder_dismiss(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle reminder dismiss action."""
        try:
            from larrybot.plugins.reminder import dismiss_reminder_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = ['1']
            await dismiss_reminder_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error dismissing reminder: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to dismiss reminder',
                'Please try again or use /dismiss_reminder command.'),
                parse_mode='MarkdownV2')

    async def _handle_reminder_snooze(self, query, context: ContextTypes.
        DEFAULT_TYPE, reminder_id: int, duration: str) ->None:
        """Handle reminder snooze action."""
        try:
            from larrybot.plugins.reminder import snooze_reminder_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(reminder_id), duration]
            await snooze_reminder_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error snoozing reminder: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to snooze reminder',
                'Please try again or use /snooze_reminder command.'),
                parse_mode='MarkdownV2')

    async def _handle_reminder_delete(self, query, context: ContextTypes.
        DEFAULT_TYPE, reminder_id: int) ->None:
        """Handle reminder delete action."""
        try:
            from larrybot.plugins.reminder import delete_reminder_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(reminder_id)]
            await delete_reminder_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error deleting reminder: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to delete reminder',
                'Please try again or use /delreminder command.'),
                parse_mode='MarkdownV2')

    async def _handle_reminder_complete(self, query, context: ContextTypes.
        DEFAULT_TYPE, reminder_id: int) ->None:
        """Handle reminder complete action."""
        try:
            from larrybot.plugins.reminder import complete_reminder_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(reminder_id)]
            await complete_reminder_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error completing reminder: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to complete reminder',
                'Please try again or use /complete_reminder command.'),
                parse_mode='MarkdownV2')

    async def _handle_reminder_edit(self, query, context: ContextTypes.
        DEFAULT_TYPE, reminder_id: int) ->None:
        """Handle reminder edit action."""
        try:
            from larrybot.plugins.reminder import edit_reminder_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(reminder_id), 'Updated reminder text']
            await edit_reminder_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error editing reminder: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to edit reminder',
                'Please try again or use /edit_reminder command.'),
                parse_mode='MarkdownV2')

    async def _handle_reminder_reactivate(self, query, context:
        ContextTypes.DEFAULT_TYPE, reminder_id: int) ->None:
        """Handle reminder reactivate action."""
        try:
            from larrybot.plugins.reminder import reactivate_reminder_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(reminder_id)]
            await reactivate_reminder_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error reactivating reminder: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to reactivate reminder',
                'Please try again or use /reactivate_reminder command.'),
                parse_mode='MarkdownV2')

    async def _handle_attachment_edit_desc(self, query, context:
        ContextTypes.DEFAULT_TYPE, attachment_id: int) ->None:
        """Handle attachment description edit."""
        try:
            from larrybot.plugins.file_attachments import edit_attachment_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(attachment_id), 'Updated description']
            await edit_attachment_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error editing attachment: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to edit attachment',
                'Please try again or use /edit_attachment command.'),
                parse_mode='MarkdownV2')

    async def _handle_attachment_details(self, query, context: ContextTypes
        .DEFAULT_TYPE, attachment_id: int) ->None:
        """Handle attachment details view."""
        try:
            from larrybot.plugins.file_attachments import attachment_details_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(attachment_id)]
            await attachment_details_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error showing attachment details: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to load attachment details',
                'Please try again or use /attachment_details command.'),
                parse_mode='MarkdownV2')

    async def _handle_attachment_remove(self, query, context: ContextTypes.
        DEFAULT_TYPE, attachment_id: int) ->None:
        """Handle attachment removal."""
        try:
            from larrybot.plugins.file_attachments import remove_attachment_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(attachment_id)]
            await remove_attachment_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error removing attachment: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to remove attachment',
                'Please try again or use /remove_attachment command.'),
                parse_mode='MarkdownV2')

    async def _handle_attachment_stats(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """Handle attachment statistics."""
        try:
            from larrybot.plugins.file_attachments import attachment_stats_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(task_id)]
            await attachment_stats_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error showing attachment stats: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to load attachment statistics',
                'Please try again or use /attachment_stats command.'),
                parse_mode='MarkdownV2')

    async def _handle_attachment_add_desc(self, query, context:
        ContextTypes.DEFAULT_TYPE, task_id: int) ->None:
        """Handle attachment description addition."""
        try:
            from larrybot.plugins.file_attachments import add_attachment_desc_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(task_id), 'New attachment description']
            await add_attachment_desc_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error adding attachment description: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to add attachment description',
                'Please try again or use /add_attachment_desc command.'),
                parse_mode='MarkdownV2')

    async def _handle_attachment_bulk_remove(self, query, context:
        ContextTypes.DEFAULT_TYPE, task_id: int) ->None:
        """Handle bulk attachment removal."""
        try:
            from larrybot.plugins.file_attachments import bulk_remove_attachments_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(task_id)]
            await bulk_remove_attachments_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error bulk removing attachments: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to bulk remove attachments',
                'Please try again or use /bulk_remove_attachments command.'
                ), parse_mode='MarkdownV2')

    async def _handle_attachment_export(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """Handle attachment export."""
        try:
            from larrybot.plugins.file_attachments import export_attachments_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(task_id)]
            await export_attachments_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error exporting attachments: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to export attachments',
                'Please try again or use /export_attachments command.'),
                parse_mode='MarkdownV2')



    async def _handle_calendar_today(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle calendar today view."""
        try:
            from larrybot.plugins.calendar import agenda_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = ['today']
            await agenda_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error showing calendar today: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('📅 Calendar Loading Failed', {'Issue':
                "Unable to load today's calendar view", 'Solution':
                'Try using `/agenda today` command directly', 'Alternative':
                'Check calendar sync status with `/accounts`'}), parse_mode
                ='MarkdownV2')

    async def _handle_calendar_week(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle calendar week view."""
        try:
            from larrybot.plugins.calendar import agenda_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = ['week']
            await agenda_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error showing calendar week: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('📅 Week Calendar Failed', {'Issue':
                'Unable to load week calendar view', 'Solution':
                'Try using `/agenda week` command directly', 'Alternative':
                'Check calendar sync status with `/accounts`'}), parse_mode
                ='MarkdownV2')

    async def _handle_calendar_month(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle calendar month view."""
        try:
            from larrybot.plugins.calendar import agenda_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = ['month']
            await agenda_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error showing calendar month: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('📅 Month Calendar Failed', {'Issue':
                'Unable to load month calendar view', 'Solution':
                'Try using `/agenda month` command directly', 'Alternative':
                'Check calendar sync status with `/accounts`'}), parse_mode
                ='MarkdownV2')

    async def _handle_calendar_upcoming(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle calendar upcoming view."""
        try:
            from larrybot.plugins.calendar import agenda_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = ['upcoming']
            await agenda_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error showing calendar upcoming: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('📅 Upcoming Events Failed', {'Issue':
                'Unable to load upcoming events view', 'Solution':
                'Try using `/agenda upcoming` command directly',
                'Alternative':
                'Check calendar sync status with `/accounts`'}), parse_mode
                ='MarkdownV2')

    async def _handle_calendar_sync(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle calendar sync."""
        try:
            from larrybot.plugins.calendar import sync_calendar_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await sync_calendar_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error syncing calendar: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('🔄 Calendar Sync Failed', {'Issue':
                'Unable to sync calendar data', 'Solution':
                'Try using `/sync_calendar` command directly',
                'Alternative': 'Check calendar connection with `/accounts`'
                }), parse_mode='MarkdownV2')

    async def _handle_calendar_settings(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle calendar settings."""
        try:
            from larrybot.plugins.calendar import accounts_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await accounts_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error showing calendar settings: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('⚙️ Calendar Settings Failed', {
                'Issue': 'Unable to load calendar settings', 'Solution':
                'Try using `/accounts` command directly', 'Alternative':
                'Check calendar plugin status'}), parse_mode='MarkdownV2')

    async def _handle_calendar_refresh(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle calendar refresh - re-run agenda handler to get fresh data."""
        try:
            from larrybot.plugins.calendar import agenda_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await agenda_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error refreshing calendar: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to refresh calendar',
                'Please try again or use /agenda command.'), parse_mode=
                'MarkdownV2')

    async def _handle_filter_date_range(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle date range filter."""
        try:
            from larrybot.plugins.advanced_tasks.filtering import date_range_filter_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await date_range_filter_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error applying date range filter: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('📅 Date Filter Failed', {'Issue':
                'Unable to apply date range filter', 'Solution':
                'Try using `/filter date` command directly', 'Alternative':
                'Use `/tasks` with date parameters'}), parse_mode='MarkdownV2')

    async def _handle_filter_priority(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle priority filter."""
        try:
            from larrybot.plugins.advanced_tasks.filtering import priority_filter_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await priority_filter_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error applying priority filter: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('🎯 Priority Filter Failed', {'Issue':
                'Unable to apply priority filter', 'Solution':
                'Try using `/filter priority` command directly',
                'Alternative': 'Use `/tasks` with priority parameters'}),
                parse_mode='MarkdownV2')

    async def _handle_filter_status(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle status filter."""
        try:
            from larrybot.plugins.advanced_tasks.filtering import status_filter_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await status_filter_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error applying status filter: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('📋 Status Filter Failed', {'Issue':
                'Unable to apply status filter', 'Solution':
                'Try using `/filter status` command directly',
                'Alternative': 'Use `/tasks` with status parameters'}),
                parse_mode='MarkdownV2')

    async def _handle_filter_tags(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle tags filter."""
        try:
            from larrybot.plugins.advanced_tasks.filtering import tags_filter_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await tags_filter_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error applying tags filter: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('🏷️ Tags Filter Failed', {'Issue':
                'Unable to apply tags filter', 'Solution':
                'Try using `/filter tags` command directly', 'Alternative':
                'Use `/tasks` with tag parameters'}), parse_mode='MarkdownV2')

    async def _handle_filter_category(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle category filter."""
        try:
            from larrybot.plugins.advanced_tasks.filtering import category_filter_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await category_filter_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error applying category filter: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('📂 Category Filter Failed', {'Issue':
                'Unable to apply category filter', 'Solution':
                'Try using `/filter category` command directly',
                'Alternative': 'Use `/tasks` with category parameters'}),
                parse_mode='MarkdownV2')

    async def _handle_filter_time(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle time tracking filter."""
        try:
            from larrybot.plugins.advanced_tasks.filtering import time_tracking_filter_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await time_tracking_filter_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error applying time tracking filter: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('⏰ Time Filter Failed', {'Issue':
                'Unable to apply time tracking filter', 'Solution':
                'Try using `/filter time` command directly', 'Alternative':
                'Use `/tasks` with time parameters'}), parse_mode='MarkdownV2')

    async def _handle_filter_advanced_search(self, query, context:
        ContextTypes.DEFAULT_TYPE) ->None:
        """Handle advanced search filter."""
        try:
            from larrybot.plugins.advanced_tasks.filtering import advanced_search_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await advanced_search_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error performing advanced search: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('🔍 Advanced Search Failed', {'Issue':
                'Unable to perform advanced search', 'Solution':
                'Try using `/search` command directly', 'Alternative':
                'Use `/tasks` with search parameters'}), parse_mode=
                'MarkdownV2')

    async def _handle_filter_save(self, query, context: ContextTypes.
        DEFAULT_TYPE) ->None:
        """Handle save filter."""
        try:
            from larrybot.plugins.advanced_tasks.filtering import save_filter_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            await save_filter_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error saving filter: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('💾 Save Filter Failed', {'Issue':
                'Unable to save current filter', 'Solution':
                'Try using `/filter save` command directly', 'Alternative':
                'Use `/tasks` to apply filters manually'}), parse_mode=
                'MarkdownV2')

    async def _global_error_handler(self, update: object, context:
        ContextTypes.DEFAULT_TYPE) ->None:
        """Handle all uncaught exceptions to prevent bot crashes with enhanced error recovery."""
        logger.error(f'Exception while handling update: {context.error}')
        if update and hasattr(update, 'effective_message'
            ) and update.effective_message:
            try:
                error_context = {'current_context': 'error', 'error_type':
                    'system_error', 'navigation_path': ['Error Recovery'],
                    'available_actions': [{'text': '🔄 Retry',
                    'callback_data': 'retry_action', 'type': 'primary'}, {
                    'text': '🏠 Main Menu', 'callback_data': 'nav_main',
                    'type': 'navigation'}, {'text': '❓ Help',
                    'callback_data': 'show_help', 'type': 'secondary'}]}
                error_message, recovery_keyboard = (self.
                    enhanced_message_processor.create_error_response(
                    'system_error',
                    '⚠️ System temporarily unavailable. Please try again in a moment.'
                    , error_context))
                await update.effective_message.reply_text(error_message,
                    reply_markup=recovery_keyboard, parse_mode='MarkdownV2')
            except Exception as e:
                logger.error(
                    f'Failed to send enhanced error message to user: {e}')
                try:
                    await update.effective_message.reply_text(MessageFormatter
                        .format_error_message(
                        '⚠️ System temporarily unavailable',
                        'Please try again in a moment\\. If the issue persists, check your network connection\\.'
                        ), parse_mode='MarkdownV2')
                except Exception as fallback_e:
                    logger.error(
                        f'Failed to send fallback error message: {fallback_e}')

    async def _send_daily_report(self, update=None, context=None, chat_id=None
        ):
        """Send a comprehensive daily report with tasks, habits, and motivational content."""
        logger.info('Generating daily report')
        try:
            from larrybot.services.datetime_service import DateTimeService
            start_of_today = DateTimeService.get_start_of_day()
            end_of_today = DateTimeService.get_end_of_day()
            with get_optimized_session() as session:
                task_repository = TaskRepository(session)
                task_service = TaskService(task_repository)
                overdue_result = await task_service.get_tasks_with_filters(
                    overdue_only=True)
                due_today_result = await task_service.get_tasks_with_filters(
                    due_after=start_of_today, due_before=end_of_today, done=False)
                overdue_tasks = overdue_result['data'] if overdue_result[
                    'success'] else []
                due_today_tasks = due_today_result['data'] if due_today_result[
                    'success'] else []
                habit_repo = HabitRepository(session)
                habits = habit_repo.list_habits()
                habits_due = []
                today_date = get_current_datetime().date()
                for habit in habits:
                    last_completed = habit.last_completed.date(
                        ) if habit.last_completed else None
                    if last_completed != today_date:
                        habits_due.append(habit)
            from larrybot.services.calendar_service import CalendarService
            calendar_service = CalendarService(config=self.config)
            calendar_events = await calendar_service.get_todays_events()
            events = []
            for event in calendar_events:
                formatted_event = (calendar_service.
                    format_event_for_daily_report(event))
                events.append((formatted_event['time'], formatted_event[
                    'name'], formatted_event['duration']))
            quotes = ['Well begun is half done.',
                'Success is the sum of small efforts repeated day in and day out.'
                , 'The secret of getting ahead is getting started.',
                "You don't have to be great to start, but you have to start to be great."
                , 'Discipline is the bridge between goals and accomplishment.']
            quote = random.choice(quotes)
            lines = []
            lines.append(
                f"🗓️ **Daily Report – {today_date.strftime('%A, %b %d')}**\n")
            lines.append("📅 **Today's Calendar Events:**")
            if events:
                for time, name, duration in events:
                    lines.append(f'- {time} — {name}{duration}')
            else:
                lines.append('- _No calendar events scheduled._')
            lines.append('')
            lines.append('🚨 **Overdue Tasks:**')
            if overdue_tasks:
                for t in overdue_tasks[:5]:
                    client = f" _(Client: {t.get('client_name')})_" if t.get(
                        'client_name') else ''
                    lines.append(f"- ❗ {t['description']}{client}")
                if len(overdue_tasks) > 5:
                    lines.append(
                        f'- ...and {len(overdue_tasks) - 5} more overdue tasks'
                        )
            else:
                lines.append('- _No overdue tasks!_')
            lines.append('')
            lines.append('📅 **Due Today:**')
            if due_today_tasks:
                for t in due_today_tasks[:5]:
                    client = f" _(Client: {t.get('client_name')})_" if t.get(
                        'client_name') else ''
                    lines.append(f"- {t['description']}{client}")
                if len(due_today_tasks) > 5:
                    lines.append(
                        f'- ...and {len(due_today_tasks) - 5} more due today')
            else:
                lines.append('- _No tasks due today!_')
            lines.append('')
            lines.append('🔄 **Habits Due Today:**')
            if habits_due:
                for h in habits_due:
                    streak = (f' — 🔥 Streak: {h.streak} days' if h.streak >
                        1 else '')
                    lines.append(f'- {h.name}{streak}')
            else:
                lines.append('- _No habits due today!_')
            lines.append('')
            lines.append(f'💡 _"{quote}"_')
            message = '\n'.join(lines)
            logger.info('Daily report generated successfully')
            if update:
                await update.message.reply_text(message, parse_mode='Markdown')
            elif context and chat_id:
                await context.bot.send_message(chat_id=chat_id, text=
                    message, parse_mode='Markdown')
            elif chat_id:  # Handle case where only chat_id is provided (scheduled jobs)
                await self.application.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            else:
                logger.error(
                    'No valid message target provided for daily report')
        except Exception as e:
            logger.error(f'Exception in _send_daily_report: {e}')
            raise

    async def daily_command(self, update, context):
        """Handle /daily command to send daily report."""
        logger.info('Daily command invoked by user')
        if not self._is_authorized(update):
            await update.message.reply_text('🚫 Unauthorized access.')
            return
        try:
            await self._send_daily_report(update, context)
        except Exception as e:
            logger.error(f'Error in daily command: {e}')
            await update.message.reply_text(MessageFormatter.
                format_error_message('Failed to generate daily report',
                'Please try again later.'), parse_mode='MarkdownV2')

    async def scheduler_status_command(self, update, context):
        """Handle /scheduler_status command to check scheduler and daily report status."""
        logger.info('Scheduler status command invoked by user')
        if not self._is_authorized(update):
            await update.message.reply_text('🚫 Unauthorized access.')
            return
        try:
            from larrybot.scheduler import scheduler
            job_id = f'daily_report_{self.config.ALLOWED_TELEGRAM_USER_ID}'
            job = scheduler.get_job(job_id)
            
            if job:
                next_run = job.next_run_time
                message = f"""⏰ **Scheduler Status**

✅ **Daily Report Job**: Active
📅 **Next Run**: {next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else 'Unknown'}
🆔 **Job ID**: `{job_id}`
            ⏱️ **Schedule**: Daily at 8:30 AM

🔄 **Scheduler Status**: {'Running' if scheduler.running else 'Stopped'}"""
            else:
                message = f"""⏰ **Scheduler Status**

❌ **Daily Report Job**: Not Found
🆔 **Expected Job ID**: `{job_id}`
⚠️ **Issue**: Daily report not scheduled

🔄 **Scheduler Status**: {'Running' if scheduler.running else 'Stopped'}

💡 **Solution**: Restart the bot to re-schedule the daily report."""
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f'Error in scheduler status command: {e}')
            await update.message.reply_text(MessageFormatter.
                format_error_message('Failed to check scheduler status',
                str(e)), parse_mode='MarkdownV2')

    async def trigger_daily_report_command(self, update, context):
        """Handle /trigger_daily command to manually trigger the daily report."""
        logger.info('Manual daily report trigger command invoked by user')
        if not self._is_authorized(update):
            await update.message.reply_text('🚫 Unauthorized access.')
            return
        try:
            await update.message.reply_text('🔄 Manually triggering daily report...', parse_mode='Markdown')
            await self._send_daily_report(chat_id=self.config.ALLOWED_TELEGRAM_USER_ID, context=context)
            logger.info('✅ Manual daily report triggered successfully')
        except Exception as e:
            logger.error(f'Error in manual daily report trigger: {e}')
            await update.message.reply_text(MessageFormatter.
                format_error_message('Failed to trigger daily report',
                str(e)), parse_mode='MarkdownV2')

    async def _handle_task_attach_file(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """Handle task file attachment via callback."""
        from larrybot.utils.ux_helpers import MessageFormatter
        from larrybot.utils.telegram_safe import escape_markdown_v2
        try:
            # Set context for file attachment mode
            context.user_data['attaching_file_to_task'] = task_id
            
            message_text = f"""📎 **Attach File to Task #{task_id}**

Please send the file you want to attach to this task.

**Supported formats:** Documents, images, PDFs, etc.
**Max size:** 20MB"""
            await safe_edit(query.edit_message_text,
                escape_markdown_v2(message_text), 
                parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f'Error starting file attachment for task {task_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Error starting file attachment',
                'Please try again or use /add_attachment command.'), parse_mode='MarkdownV2')

    async def _handle_task_add_note(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """Handle task note/comment addition via callback."""
        from larrybot.utils.ux_helpers import MessageFormatter
        from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
        try:
            # Set context for note addition mode
            context.user_data['adding_note_to_task'] = task_id
            keyboard = InlineKeyboardMarkup([
                [UnifiedButtonBuilder.create_button(text='❌ Cancel', 
                    callback_data=f'task_view:{task_id}', 
                    button_type=ButtonType.SECONDARY)]
            ])
            await safe_edit(query.edit_message_text,
                f"""📝 **Add Note to Task \\#{task_id}**

Please reply with the note or comment you want to add to this task\\.

**Examples:**
• "Started working on this task"
• "Waiting for client feedback"
• "Blocked by dependency X"

You can also use `/comment {task_id} <your note>` command\\.""", 
                reply_markup=keyboard, parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f'Error starting note addition for task {task_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Error starting note addition',
                'Please try again or use /comment command.'), parse_mode='MarkdownV2')

    async def _handle_task_time_menu(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle task time tracking menu via callback."""
        from larrybot.utils.ux_helpers import MessageFormatter
        from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
        from larrybot.storage.db import get_optimized_session
        from larrybot.storage.task_repository import TaskRepository
        try:
            with get_optimized_session() as session:
                repo = TaskRepository(session)
                task = repo.get_task_by_id(task_id)
                if not task:
                    await safe_edit(query.edit_message_text,
                        MessageFormatter.format_error_message(
                        f'Task ID {task_id} not found',
                        "The task may have already been deleted or doesn't exist."
                        ), parse_mode='MarkdownV2')
                    return
                
                is_tracking = getattr(task, 'started_at', None) is not None
                
                if is_tracking:
                    buttons = [
                        [
                            UnifiedButtonBuilder.create_button(text='⏹️ Stop Tracking', 
                                callback_data=f'task_stop_time:{task_id}', 
                                button_type=ButtonType.DANGER),
                            UnifiedButtonBuilder.create_button(text='📊 View Time', 
                                callback_data=f'task_time_stats:{task_id}', 
                                button_type=ButtonType.INFO)
                        ],
                        [
                            UnifiedButtonBuilder.create_button(text='🔙 Back to Task', 
                                callback_data=f'task_view:{task_id}', 
                                button_type=ButtonType.SECONDARY)
                        ]
                    ]
                    keyboard = InlineKeyboardMarkup(buttons)
                    message = f"""⏱️ *Time Tracking Active \\- Task \\#{task_id}*

Time tracking is currently running for this task\\.

*Task:* {MessageFormatter.escape_markdown(task.description)}"""
                else:
                    buttons = [
                        [
                            UnifiedButtonBuilder.create_button(text='▶️ Start Tracking', 
                                callback_data=f'task_start_time:{task_id}', 
                                button_type=ButtonType.SUCCESS),
                            UnifiedButtonBuilder.create_button(text='📊 View Time', 
                                callback_data=f'task_time_stats:{task_id}', 
                                button_type=ButtonType.INFO)
                        ],
                        [
                            UnifiedButtonBuilder.create_button(text='🔙 Back to Task', 
                                callback_data=f'task_view:{task_id}', 
                                button_type=ButtonType.SECONDARY)
                        ]
                    ]
                    keyboard = InlineKeyboardMarkup(buttons)
                    message = f"""⏱️ *Time Tracking \\- Task \\#{task_id}*

Track time spent on this task to monitor productivity\\.

*Task:* {MessageFormatter.escape_markdown(task.description)}"""
                
                await safe_edit(query.edit_message_text, message, 
                    reply_markup=keyboard, parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f'Error showing time tracking menu for task {task_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Error showing time tracking menu',
                'Please try again or use /start\\_time\\_tracking command\\.'), parse_mode='MarkdownV2')

    async def _handle_task_start_time(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """Handle task start time tracking."""
        try:
            from larrybot.plugins.advanced_tasks.time_tracking import start_time_tracking_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(task_id)]
            await start_time_tracking_handler(mock_update, context)
            
            # Refresh the time tracking menu to show updated state
            await self._handle_task_time_menu(query, context, task_id)
        except Exception as e:
            logger.error(f'Error starting time tracking for task {task_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to start time tracking',
                'Please try again or use /time_start command.'),
                parse_mode='MarkdownV2')

    async def _handle_task_stop_time(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """Handle task stop time tracking."""
        try:
            from larrybot.plugins.advanced_tasks.time_tracking import stop_time_tracking_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(task_id)]
            await stop_time_tracking_handler(mock_update, context)
            
            # Refresh the time tracking menu to show updated state
            await self._handle_task_time_menu(query, context, task_id)
        except Exception as e:
            logger.error(f'Error stopping time tracking for task {task_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to stop time tracking',
                'Please try again or use /time_stop command.'),
                parse_mode='MarkdownV2')

    async def _handle_task_time_stats(self, query, context: ContextTypes.
        DEFAULT_TYPE, task_id: int) ->None:
        """Handle task time statistics."""
        try:
            from larrybot.plugins.advanced_tasks.time_tracking import time_summary_handler
            mock_update = type('MockUpdate', (), {'message': query.message,
                'effective_user': query.from_user})()
            context.args = [str(task_id)]
            await time_summary_handler(mock_update, context)
        except Exception as e:
            logger.error(f'Error showing time statistics for task {task_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to load time statistics',
                'Please try again or use /time_summary command.'), parse_mode=
                'MarkdownV2')



    async def _handle_task_dependencies(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle task dependencies button press."""
        try:
            from larrybot.plugins.advanced_tasks import get_task_service
            from larrybot.utils.ux_helpers import MessageFormatter
            
            # Get the task service
            task_service = get_task_service()
            
            # Get task dependencies
            result = await task_service.get_task_dependencies(task_id)
            
            if result['success']:
                dependencies = result['data']  # data is already the list of dependencies
                
                # Format dependencies message
                if dependencies:
                    message = f"🔗 **Task Dependencies**\n\n"
                    message += f"**Task \\#{task_id} depends on:**\n"
                    for i, dep in enumerate(dependencies, 1):
                        status_emoji = "✅" if dep.get('done', False) else "⏳"
                        message += f"{i}. {status_emoji} **{MessageFormatter.escape_markdown(dep.get('description', 'Unknown task'))}**\n"
                        message += f"   ID: {dep.get('id', 'N/A')} | Priority: {dep.get('priority', 'Medium')}\n"
                    
                    if any(not dep.get('done', False) for dep in dependencies):
                        message += f"\n⚠️ **Note**: Complete the pending dependencies before starting this task\\."
                else:
                    message = f"🔗 **Task Dependencies**\n\n"
                    message += f"Task \\#{task_id} has no dependencies\\. You can start working on it anytime\\!"
                
                # Add back to task button
                from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
                keyboard = InlineKeyboardMarkup([[
                    UnifiedButtonBuilder.create_button(
                        text='🔙 Back to Task', 
                        callback_data=f'task_view:{task_id}', 
                        button_type=ButtonType.SECONDARY
                    )
                ]])
                
                await safe_edit(query.edit_message_text, message, 
                    reply_markup=keyboard, parse_mode='MarkdownV2')
            else:
                await safe_edit(query.edit_message_text, MessageFormatter.
                    format_error_message('Failed to load dependencies',
                    result.get('message', 'Unable to get task dependencies.')), 
                    parse_mode='MarkdownV2')
            
        except Exception as e:
            logger.error(f'Error showing dependencies for task {task_id}: {e}')
            await safe_edit(query.edit_message_text, MessageFormatter.
                format_error_message('Failed to load task dependencies',
                'Please try again or use /dependency command.'), parse_mode=
                'MarkdownV2')

    async def _handle_tasks_list(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Unified task list view for all entry points (callback version of /list)."""
        from larrybot.plugins.tasks import _list_incomplete_tasks_default
        class DummyUpdate:
            def __init__(self, query):
                self.message = query.message
        dummy_update = DummyUpdate(query)
        await _list_incomplete_tasks_default(dummy_update)
