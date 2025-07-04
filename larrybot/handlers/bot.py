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
from larrybot.storage.db import get_session
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
from larrybot.utils.enhanced_ux_helpers import escape_markdown_v2
import random
from datetime import datetime, timedelta
from larrybot.services.task_service import TaskService
from larrybot.storage.db import get_session
from larrybot.storage.habit_repository import HabitRepository
from larrybot.utils.datetime_utils import get_current_datetime
from larrybot.utils.datetime_utils import ensure_timezone_aware
from larrybot.utils.telegram_safe import safe_edit

# Set up logging
logger = logging.getLogger(__name__)

class TelegramBotHandler:
    """
    Handles Telegram bot initialization and command routing.
    Single-user system: only the configured user can access the bot.
    """
    def __init__(self, config: Config, command_registry: CommandRegistry):
        self.config = config
        self.command_registry = command_registry
        
        # Configure HTTP request with timeout and retry settings
        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=10.0,     # 10 second connection timeout
            read_timeout=20.0,        # 20 second read timeout  
            write_timeout=20.0,       # 20 second write timeout
            pool_timeout=5.0,         # 5 second pool timeout
        )
        
        self.application = Application.builder()\
            .token(self.config.TELEGRAM_BOT_TOKEN)\
            .request(request)\
            .build()
            
        # Add global error handler to prevent crashes
        self.application.add_error_handler(self._global_error_handler)
        
        # Register commands first, then handlers to ensure proper registration order
        self._register_core_commands()
        self._register_core_handlers()
        
        # NLP pipeline initialization
        self.intent_recognizer = IntentRecognizer()
        self.entity_extractor = EntityExtractor()
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Enhanced narrative processor initialization
        self.enhanced_narrative_processor = EnhancedNarrativeProcessor()
        
        # Enhanced UX system initialization
        self.enhanced_message_processor = EnhancedMessageProcessor()

    def _is_authorized(self, update: Update) -> bool:
        """Check if the user is authorized to use this single-user bot."""
        user = getattr(update, 'effective_user', None)
        if not user:
            return False
        
        # Handle config failures gracefully
        try:
            if not self.config:
                return False
            return user.id == self.config.ALLOWED_TELEGRAM_USER_ID
        except (AttributeError, TypeError):
            # Config is corrupted or has wrong type
            return False

    def _register_core_handlers(self) -> None:
        """Register core handlers including callback query handler."""
        self.application.add_handler(CommandHandler("start", self._start))
        self.application.add_handler(CommandHandler("help", self._help))
        
        # Add callback query handler for inline keyboard interactions
        self.application.add_handler(CallbackQueryHandler(self._handle_callback_query))
        
        # Add message handler for text messages (for task editing)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text_message))
        
        # Dynamically add handlers for all registered commands (except /start and /help)
        if hasattr(self.command_registry, '_commands') and isinstance(self.command_registry._commands, dict):
            for command, handler in self.command_registry._commands.items():
                if command in ("/start", "/help"):
                    continue
                # If the handler is a bound method of this instance, register it directly
                if hasattr(handler, "__self__") and handler.__self__ is self:
                    self.application.add_handler(CommandHandler(command.lstrip("/"), handler))
                else:
                    self.application.add_handler(CommandHandler(command.lstrip("/"), self._dispatch_command))

    def _register_core_commands(self) -> None:
        """Register core commands with the command registry."""
        from larrybot.core.command_registry import CommandMetadata
        
        # Register /help command
        help_metadata = CommandMetadata(
            name="/help",
            description="Show available commands and their descriptions",
            usage="/help",
            category="system"
        )
        self.command_registry.register("/help", self._help, help_metadata)
        
        # Register /start command
        start_metadata = CommandMetadata(
            name="/start",
            description="Start the bot and show welcome message",
            usage="/start",
            category="system"
        )
        self.command_registry.register("/start", self._start, start_metadata)
        
        daily_metadata = CommandMetadata(
            name="/daily",
            description="Send a daily report of events, overdue tasks, due today, and habits.",
            usage="/daily",
            category="system"
        )
        self.command_registry.register("/daily", self.daily_command, daily_metadata)

    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle callback queries from inline keyboards with timeout protection.
        Follows Telegram bot best practices for callback query handling.
        """
        query = update.callback_query
        
        # Acknowledge the callback query immediately to prevent timeout
        try:
            await asyncio.wait_for(query.answer(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Timeout acknowledging callback query")
            return  # Don't proceed if we can't acknowledge
        except Exception as e:
            logger.error(f"Failed to acknowledge callback query: {e}")
            return
        
        # Validate authorization
        if not self._is_authorized(update):
            try:
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_error_message(
                        "Unauthorized access",
                        "Only the configured user can use this bot."
                    ),
                    parse_mode='MarkdownV2'
                )
            except Exception as e:
                logger.error(f"Failed to send unauthorized message: {e}")
            return
        
        try:
            # Add timeout to prevent hanging during network issues
            await asyncio.wait_for(self._handle_callback_operations(query, context), timeout=15.0)
                    
        except asyncio.TimeoutError:
            logger.error(f"Callback query timeout for action: {query.data}")
            try:
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_error_message(
                        "⏱️ Action timed out",
                        "Please try again\\. If the issue persists, try using text commands\\."
                    ),
                    parse_mode='MarkdownV2'
                )
            except Exception as e:
                logger.error(f"Failed to send timeout message: {e}")
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            try:
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_error_message(
                        "❌ An error occurred",
                        "Please try again or use a command instead\\."
                    ),
                    parse_mode='MarkdownV2'
                )
            except Exception as nested_e:
                logger.error(f"Failed to send error message: {nested_e}")

    async def _handle_callback_operations(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the actual callback operations with proper routing."""
        # Route callback data to appropriate handler
        callback_data = query.data
        
        if callback_data == "no_action":
            # No action needed (e.g., page number display)
            return
        elif callback_data == "nav_back":
            await self._handle_navigation_back(query, context)
        elif callback_data == "nav_main":
            await self._handle_navigation_main(query, context)
        elif callback_data == "cancel_action":
            await self._handle_cancel_action(query, context)
        elif callback_data.startswith("task_"):
            await self._handle_task_callback(query, context)
        elif callback_data.startswith("client_"):
            await self._handle_client_callback(query, context)
        elif callback_data.startswith("habit_"):
            await self._handle_habit_callback(query, context)
        elif callback_data.startswith("confirm_"):
            await self._handle_confirmation_callback(query, context)
        elif callback_data.startswith("menu_"):
            await self._handle_menu_callback(query, context)
        elif callback_data.startswith("bulk_"):
            await self._handle_bulk_operations_callback(query, context)
        elif callback_data.startswith("task_disclose:"):
            await self._handle_task_disclosure(query, context)
        elif callback_data == "task_edit_cancel":
            await self._handle_task_edit_cancel(query, context)
        elif callback_data == "tasks_refresh":
            await self._handle_tasks_refresh(query, context)
        elif callback_data.startswith("reminder_"):
            await self._handle_reminder_callback(query, context)
        elif callback_data.startswith("attachment_"):
            await self._handle_attachment_callback(query, context)
        elif callback_data.startswith("calendar_"):
            await self._handle_calendar_callback(query, context)
        elif callback_data.startswith("filter_"):
            await self._handle_filter_callback(query, context)
        elif callback_data == "add_task":
            await self._handle_add_task(query, context)
        elif callback_data.startswith("addtask_step:"):
            await self._handle_narrative_task_callback(query, context)
        else:
            # Unknown callback data
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Unknown action",
                    "This button action is not implemented yet."
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_task_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle task-related callback queries."""
        callback_data = query.data
        
        if callback_data.startswith("task_done:") or callback_data.startswith("task_complete:"):
            task_id = int(callback_data.split(":")[1])
            await self._handle_task_done(query, context, task_id)
        elif callback_data.startswith("task_edit:"):
            task_id = int(callback_data.split(":")[1])
            await self._handle_task_edit(query, context, task_id)
        elif callback_data.startswith("task_delete:"):
            task_id = int(callback_data.split(":")[1])
            await self._handle_task_delete(query, context, task_id)
        elif callback_data.startswith("task_view:"):
            task_id = int(callback_data.split(":")[1])
            await self._handle_task_view(query, context, task_id)
        elif callback_data == "task_edit_cancel":
            await self._handle_task_edit_cancel(query, context)
        elif callback_data == "tasks_refresh":
            await self._handle_tasks_refresh(query, context)

    async def _handle_client_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle client-related callback queries."""
        callback_data = query.data
        
        if callback_data.startswith("client_tasks:"):
            client_id = int(callback_data.split(":")[1])
            await self._handle_client_tasks(query, context, client_id)
        elif callback_data.startswith("client_analytics:"):
            client_id = int(callback_data.split(":")[1])
            await self._handle_client_analytics(query, context, client_id)
        elif callback_data.startswith("client_delete:"):
            client_id = int(callback_data.split(":")[1])
            await self._handle_client_delete(query, context, client_id)
        elif callback_data.startswith("client_view:"):
            client_id = int(callback_data.split(":")[1])
            await self._handle_client_view(query, context, client_id)
        elif callback_data.startswith("client_edit:"):
            client_id = int(callback_data.split(":")[1])
            await self._handle_client_edit(query, context, client_id)

    async def _handle_habit_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle habit-related callback queries."""
        callback_data = query.data
        
        if callback_data.startswith("habit_done:"):
            habit_id = int(callback_data.split(":")[1])
            await self._handle_habit_done(query, context, habit_id)
        elif callback_data.startswith("habit_progress:"):
            habit_id = int(callback_data.split(":")[1])
            await self._handle_habit_progress(query, context, habit_id)
        elif callback_data.startswith("habit_delete:"):
            habit_id = int(callback_data.split(":")[1])
            await self._handle_habit_delete(query, context, habit_id)
        elif callback_data == "habit_add":
            await self._handle_habit_add(query, context)
        elif callback_data == "habit_stats":
            await self._handle_habit_stats(query, context)
        elif callback_data == "habit_refresh":
            await self._handle_habit_refresh(query, context)
        elif callback_data == "habit_list":
            await self._handle_habit_refresh(query, context)

    async def _handle_confirmation_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle confirmation callback queries."""
        callback_data = query.data
        
        if callback_data.startswith("confirm_task_delete:"):
            task_id = int(callback_data.split(":")[1])
            await self._confirm_task_delete(query, context, task_id)
        elif callback_data.startswith("confirm_client_delete:"):
            client_id = int(callback_data.split(":")[1])
            await self._confirm_client_delete(query, context, client_id)
        elif callback_data.startswith("confirm_habit_delete:"):
            habit_id = int(callback_data.split(":")[1])
            await self._confirm_habit_delete(query, context, habit_id)

    async def _handle_menu_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle menu navigation callback queries."""
        callback_data = query.data
        
        if callback_data == "menu_tasks":
            await self._show_task_menu(query, context)
        elif callback_data == "menu_clients":
            await self._show_client_menu(query, context)
        elif callback_data == "menu_habits":
            await self._show_habit_menu(query, context)
        elif callback_data == "menu_reminders":
            await self._show_reminder_menu(query, context)
        elif callback_data == "menu_analytics":
            await self._show_analytics_menu(query, context)

    async def _handle_bulk_operations_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle bulk operations callback queries."""
        callback_data = query.data
        
        if callback_data == "bulk_status_menu":
            await self._show_bulk_status_menu(query, context)
        elif callback_data == "bulk_priority_menu":
            await self._show_bulk_priority_menu(query, context)
        elif callback_data == "bulk_assign_menu":
            await self._show_bulk_assign_menu(query, context)
        elif callback_data == "bulk_delete_menu":
            await self._show_bulk_delete_menu(query, context)
        elif callback_data == "bulk_preview":
            await self._show_bulk_preview(query, context)
        elif callback_data == "bulk_save_selection":
            await self._save_bulk_selection(query, context)
        elif callback_data.startswith("bulk_delete_confirm:"):
            task_ids = callback_data.split(":")[1]
            await self._confirm_bulk_delete(query, context, task_ids)
        elif callback_data == "bulk_delete_cancel":
            await self._cancel_bulk_delete(query, context)
        elif callback_data.startswith("bulk_status:"):
            status = callback_data.split(":")[1]
            await self._handle_bulk_status_update(query, context, status)
        elif callback_data.startswith("bulk_priority:"):
            priority = callback_data.split(":")[1]
            await self._handle_bulk_priority_update(query, context, priority)
        elif callback_data == "bulk_operations_back":
            await self._handle_bulk_operations_back(query, context)

    async def _show_task_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show task management menu."""
        from larrybot.utils.ux_helpers import NavigationHelper
        
        await safe_edit(query.edit_message_text, 
            "📋 **Task Management**\n\nSelect an option:",
            reply_markup=NavigationHelper.get_task_menu_keyboard(),
            parse_mode='MarkdownV2'
        )

    async def _show_client_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show client management menu."""
        await safe_edit(query.edit_message_text, 
            "👥 **Client Management**\n\nUse commands:\n• /allclients - List all clients\n• /addclient - Add new client\n• /client - View client details",
            parse_mode='MarkdownV2'
        )

    async def _show_habit_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show habit management menu."""
        await safe_edit(query.edit_message_text, 
            "🔄 **Habit Management**\n\nUse commands:\n• /habit_list - List all habits\n• /habit_add - Add new habit\n• /habit_done - Mark habit complete",
            parse_mode='MarkdownV2'
        )

    async def _show_reminder_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show reminder management menu."""
        await safe_edit(query.edit_message_text, 
            "⏰ **Reminder Management**\n\nUse commands:\n• /reminders - List all reminders\n• /addreminder - Add new reminder\n• /delreminder - Delete reminder",
            parse_mode='MarkdownV2'
        )

    async def _show_analytics_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show analytics menu."""
        await safe_edit(query.edit_message_text, 
            "📊 **Analytics**\n\nUse commands:\n• /analytics - Task analytics\n• /clientanalytics - Client analytics\n• /productivity_report - Detailed report",
            parse_mode='MarkdownV2'
        )

    async def _show_bulk_status_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bulk status update menu."""
        from larrybot.utils.ux_helpers import KeyboardBuilder
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📝 Todo", callback_data="bulk_status:Todo"),
                InlineKeyboardButton("🔄 In Progress", callback_data="bulk_status:In Progress")
            ],
            [
                InlineKeyboardButton("👀 Review", callback_data="bulk_status:Review"),
                InlineKeyboardButton("✅ Done", callback_data="bulk_status:Done")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="bulk_operations_back")]
        ])
        
        await safe_edit(query.edit_message_text, 
            "📋 **Bulk Status Update**\n\nSelect the new status for your tasks:",
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )

    async def _show_bulk_priority_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bulk priority update menu."""
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🟢 Low", callback_data="bulk_priority:Low"),
                InlineKeyboardButton("🟡 Medium", callback_data="bulk_priority:Medium")
            ],
            [
                InlineKeyboardButton("🟠 High", callback_data="bulk_priority:High"),
                InlineKeyboardButton("🔴 Critical", callback_data="bulk_priority:Critical")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="bulk_operations_back")]
        ])
        
        await safe_edit(query.edit_message_text, 
            "🎯 **Bulk Priority Update**\n\nSelect the new priority for your tasks:",
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )

    async def _show_bulk_assign_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bulk assign menu."""
        await safe_edit(query.edit_message_text, 
            "👥 **Bulk Assignment**\n\nUse the command:\n`/bulk_assign <task_ids> <client_name>`\n\nExample: `/bulk_assign 1,2,3 John Doe`",
            parse_mode='MarkdownV2'
        )

    async def _show_bulk_delete_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bulk delete menu."""
        await safe_edit(query.edit_message_text, 
            "🗑️ **Bulk Delete**\n\nUse the command:\n`/bulk_delete <task_ids> [confirm]`\n\nExample: `/bulk_delete 1,2,3 confirm`",
            parse_mode='MarkdownV2'
        )

    async def _show_bulk_preview(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bulk operations preview."""
        await safe_edit(query.edit_message_text, 
            "📊 **Bulk Operations Preview**\n\nThis feature will show a preview of tasks before applying bulk operations.",
            parse_mode='MarkdownV2'
        )

    async def _save_bulk_selection(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Save bulk selection."""
        await safe_edit(query.edit_message_text, 
            "💾 **Bulk Selection Saved**\n\nYour task selection has been saved for bulk operations.",
            parse_mode='MarkdownV2'
        )

    async def _confirm_bulk_delete(self, query, context: ContextTypes.DEFAULT_TYPE, task_ids: str) -> None:
        """Confirm bulk delete operation."""
        from larrybot.services.task_service import TaskService
        
        try:
            task_service = TaskService()
            result = await task_service.bulk_delete_tasks([int(id.strip()) for id in task_ids.split(',')])
            
            if result['success']:
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_success_message(
                        "🗑️ Bulk Delete Complete!",
                        {
                            "Tasks Deleted": len(task_ids.split(',')),
                            "Details": result.get('details', 'All tasks deleted successfully')
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
            else:
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_error_message(
                        result['message'],
                        "Please check the task IDs and try again."
                    ),
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Error during bulk delete",
                    str(e)
                ),
                parse_mode='MarkdownV2'
            )

    async def _cancel_bulk_delete(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Cancel bulk delete operation."""
        await safe_edit(query.edit_message_text, 
            "❌ **Bulk Delete Cancelled**\n\nNo tasks were deleted.",
            parse_mode='MarkdownV2'
        )

    async def _handle_navigation_back(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle back navigation."""
        # For now, just show a simple message
        await safe_edit(query.edit_message_text, 
            "⬅️ **Back Navigation**\n\nUse commands or the main menu to navigate.",
            parse_mode='MarkdownV2'
        )

    async def _handle_navigation_main(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle main menu navigation."""
        from larrybot.utils.ux_helpers import NavigationHelper
        
        await safe_edit(query.edit_message_text, 
            "🏠 **Main Menu**\n\nSelect an option:",
            reply_markup=NavigationHelper.get_main_menu_keyboard(),
            parse_mode='MarkdownV2'
        )

    async def _handle_cancel_action(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle action cancellation."""
        await safe_edit(query.edit_message_text, 
            "❌ **Action Cancelled**\n\nNo changes were made.",
            parse_mode='MarkdownV2'
        )

    async def _handle_task_done(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle task completion via callback with timeout protection and loading indicator."""
        try:
            # Show immediate loading feedback
            await safe_edit(query.edit_message_text, 
                "✅ **Completing Task...**\n\n"
                f"Marking task {task_id} as complete...",
                parse_mode='Markdown'
            )
            
            # Add timeout to prevent blocking during network issues
            await asyncio.wait_for(
                self._handle_task_done_operation(query, context, task_id),
                timeout=8.0
            )
        
        except asyncio.TimeoutError:
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "⏱️ Operation Timeout",
                    "Task completion took too long. Please check if it was completed and try again if needed."
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error completing task {task_id}: {e}")
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "🚫 Completion Error",
                    f"Failed to complete task: {str(e)}\n\n"
                    "Please try again or use the command interface."
                ),
                parse_mode='Markdown'
            )

    async def _handle_task_done_operation(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle the actual task completion operation."""
        from larrybot.storage.db import get_session
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        
        with next(get_session()) as session:
            repo = TaskRepository(session)
            task = repo.get_task_by_id(task_id)
            
            if not task:
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_error_message(
                        f"Task ID {task_id} not found",
                        "This task may have been deleted or the ID is invalid."
                    ),
                    parse_mode='Markdown'
                )
                return
            
            if task.done:
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_info_message(
                        "✅ Already Complete",
                        f"Task '{task.description}' is already marked as done!"
                    ),
                    parse_mode='Markdown'
                )
                return
            
            # Mark task as complete
            completed_task = repo.mark_task_done(task_id)
            if completed_task:
                # Emit event for analytics (non-blocking)
                try:
                    event_bus = ServiceLocator.get('event_bus')
                    emit_task_event(event_bus, 'task.completed', completed_task)
                except Exception:
                    # Event emission is non-critical, continue if it fails
                    pass
                
                # Build smart suggestions after task completion
                from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
                
                # Get remaining tasks for context
                remaining_tasks = repo.list_incomplete_tasks()
                high_priority_remaining = sum(1 for t in remaining_tasks if getattr(t, 'priority', 'Medium') in ['High', 'Critical'])
                
                # Build success message with smart suggestions
                success_message = MessageFormatter.format_success_message(
                    "✅ Task Completed!",
                    {
                        "Task": completed_task.description,
                        "Status": "Completed",
                        "Message": "🎉 Great work! Keep up the momentum!"
                    }
                )
                
                # Add smart suggestions based on remaining tasks
                suggestions = []
                if remaining_tasks:
                    suggestions.append(f"📋 **{len(remaining_tasks)} tasks remaining**")
                    if high_priority_remaining > 0:
                        suggestions.append(f"⚠️ **{high_priority_remaining} high priority tasks** need attention")
                    suggestions.append("💡 **Suggestions:**")
                    suggestions.append("• Review your task list")
                    suggestions.append("• Focus on high priority items")
                    if len(remaining_tasks) > 5:
                        suggestions.append("• Use filters to organize tasks")
                else:
                    suggestions.append("🎉 **All tasks complete!** Time to celebrate!")
                    suggestions.append("💡 **Suggestions:**")
                    suggestions.append("• Add new tasks to stay productive")
                    suggestions.append("• Review your analytics")
                
                if suggestions:
                    success_message += "\n\n" + "\n".join(suggestions)
                
                # Build smart action keyboard
                custom_actions = [
                    {
                        "text": "📋 View Tasks",
                        "callback_data": "tasks_refresh",
                        "type": ButtonType.PRIMARY,
                        "emoji": "📋"
                    }
                ]
                
                if remaining_tasks and high_priority_remaining > 0:
                    custom_actions.append({
                        "text": "⚠️ High Priority",
                        "callback_data": "tasks_filter_priority_high",
                        "type": ButtonType.WARNING,
                        "emoji": "⚠️"
                    })
                
                if remaining_tasks:
                    custom_actions.append({
                        "text": "➕ Add Task",
                        "callback_data": "add_task",
                        "type": ButtonType.SECONDARY,
                        "emoji": "➕"
                    })
                else:
                    custom_actions.append({
                        "text": "📊 Analytics",
                        "callback_data": "tasks_analytics",
                        "type": ButtonType.INFO,
                        "emoji": "📊"
                    })
                
                keyboard = UnifiedButtonBuilder.build_entity_keyboard(
                    entity_id=0,
                    entity_type="task_completed",
                    available_actions=[],
                    custom_actions=custom_actions
                )
                
                await safe_edit(query.edit_message_text, 
                    success_message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
            else:
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_error_message(
                        "❌ Completion Failed",
                        "Unable to mark the task as complete. Please try again."
                    ),
                    parse_mode='Markdown'
                )

    async def _handle_task_edit(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle task editing via callback."""
        from larrybot.storage.db import get_session
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
        
        try:
            with next(get_session()) as session:
                repo = TaskRepository(session)
                task = repo.get_task_by_id(task_id)
                
                if not task:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Task ID {task_id} not found",
                            "The task may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                if task.done:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            "Cannot edit completed task",
                            "Completed tasks cannot be edited. Use /edit command to unmark and edit."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                # Store task_id in context for the edit flow
                context.user_data['editing_task_id'] = task_id
                
                # Create keyboard with cancel option
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="task_edit_cancel")]
                ])
                
                await safe_edit(query.edit_message_text, 
                    f"✏️ **Edit Task**\n\n"
                    f"**Current**: {MessageFormatter.escape_markdown(task.description)}\n"
                    f"**ID**: {task_id}\n\n"
                    f"Please reply with the new description for this task\\.",
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            logger.error(f"Error starting task edit for task {task_id}: {e}")
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Error editing task",
                    "Please try again or use /edit command."
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_task_edit_cancel(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle cancellation of task editing."""
        # Clear the editing state
        if 'editing_task_id' in context.user_data:
            del context.user_data['editing_task_id']
        
        await safe_edit(query.edit_message_text, 
            "❌ **Edit Cancelled**\n\nTask editing was cancelled. No changes were made.",
            parse_mode='MarkdownV2'
        )

    async def _handle_task_delete(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle task deletion via callback."""
        from larrybot.utils.ux_helpers import KeyboardBuilder
        
        await safe_edit(query.edit_message_text, 
            f"🗑️ **Confirm Task Deletion**\n\nAre you sure you want to delete Task #{task_id}?",
            reply_markup=KeyboardBuilder.build_confirmation_keyboard("task_delete", task_id),
            parse_mode='MarkdownV2'
        )

    async def _confirm_task_delete(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Confirm task deletion."""
        from larrybot.storage.db import get_session
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.core.event_utils import emit_task_event
        from larrybot.utils.ux_helpers import MessageFormatter
        
        try:
            with next(get_session()) as session:
                repo = TaskRepository(session)
                task = repo.remove_task(task_id)
                
                if task:
                    # Emit event for task removal
                    emit_task_event(None, "task_removed", task)
                    
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_success_message(
                            "🗑️ Task deleted successfully!",
                            {
                                "Task": task.description,
                                "ID": task_id,
                                "Status": "Deleted",
                                "Action": "Task removed from database"
                            }
                        ),
                        parse_mode='MarkdownV2'
                    )
                else:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Task ID {task_id} not found",
                            "The task may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
        except Exception as e:
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Error deleting task",
                    str(e)
                ),
                parse_mode='MarkdownV2'
            )

    # Placeholder methods for client callbacks
    async def _handle_client_tasks(self, query, context: ContextTypes.DEFAULT_TYPE, client_id: int) -> None:
        """Handle client tasks view."""
        from larrybot.storage.db import get_session
        from larrybot.storage.client_repository import ClientRepository
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        try:
            with next(get_session()) as session:
                client_repo = ClientRepository(session)
                task_repo = TaskRepository(session)
                
                client = client_repo.get_client_by_id(client_id)
                if not client:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Client ID {client_id} not found",
                            "The client may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                tasks = task_repo.get_tasks_by_client(client.name)
                
                if not tasks:
                    message = f"📋 **Tasks for {MessageFormatter.escape_markdown(client.name)}**\n\n"
                    message += "No tasks assigned to this client\\."
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Back to Client", callback_data=f"client_view:{client.id}")]
                    ])
                else:
                    message = MessageFormatter.format_task_list(tasks, title=f"📋 **Tasks for {client.name}**")
                    
                    # Create keyboard with task action buttons and navigation
                    buttons = []
                    for task in tasks[:5]:  # Show first 5 tasks with action buttons
                        task_buttons = [
                            InlineKeyboardButton("✅", callback_data=f"task_done:{task.id}"),
                            InlineKeyboardButton("✏️", callback_data=f"task_edit:{task.id}"),
                            InlineKeyboardButton("👁️", callback_data=f"task_view:{task.id}")
                        ]
                        buttons.append(task_buttons)
                    
                    # Add navigation buttons
                    buttons.append([
                        InlineKeyboardButton("⬅️ Back to Client", callback_data=f"client_view:{client.id}"),
                        InlineKeyboardButton("🔄 Refresh", callback_data=f"client_tasks:{client.id}")
                    ])
                    
                    keyboard = InlineKeyboardMarkup(buttons)
                
                await safe_edit(query.edit_message_text, 
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            logger.error(f"Error showing client tasks for {client_id}: {e}")
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Error showing client tasks",
                    "Please try again or use /client command."
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_client_analytics(self, query, context: ContextTypes.DEFAULT_TYPE, client_id: int) -> None:
        """Show analytics for the selected client."""
        from larrybot.storage.db import get_session
        from larrybot.storage.client_repository import ClientRepository
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        try:
            with next(get_session()) as session:
                client_repo = ClientRepository(session)
                task_repo = TaskRepository(session)
                client = client_repo.get_client_by_id(client_id)
                if not client:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Client ID {client_id} not found",
                            "The client may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                tasks = task_repo.get_tasks_by_client(client.name)
                completed = sum(1 for t in tasks if t.done)
                pending = len(tasks) - completed
                completion_rate = (completed / len(tasks) * 100) if tasks else 0
                message = f"📊 **Client Analytics**\n\n"
                message += f"**Client**: {MessageFormatter.escape_markdown(client.name)}\n"
                message += f"**ID**: {client.id}\n"
                message += f"**Total Tasks**: {len(tasks)}\n"
                message += f"**Completed**: {completed} ✅\n"
                message += f"**Pending**: {pending} ⏳\n"
                message += f"**Completion Rate**: {completion_rate:.1f}%\n"
                await safe_edit(query.edit_message_text, 
                    message,
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            logger.error(f"Error showing client analytics for {client_id}: {e}")
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Error showing client analytics",
                    "Please try again or use /allclients command."
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_client_delete(self, query, context: ContextTypes.DEFAULT_TYPE, client_id: int) -> None:
        """Handle client deletion: show confirmation dialog with client info and task count."""
        from larrybot.storage.db import get_session
        from larrybot.storage.client_repository import ClientRepository
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
        try:
            with next(get_session()) as session:
                client_repo = ClientRepository(session)
                task_repo = TaskRepository(session)
                client = client_repo.get_client_by_id(client_id)
                if not client:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Client ID {client_id} not found",
                            "The client may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                tasks = task_repo.get_tasks_by_client(client.name)
                # Show confirmation dialog
                keyboard = KeyboardBuilder.build_confirmation_keyboard("client_delete", client.id)
                await safe_edit(query.edit_message_text, 
                    f"🗑️ **Confirm Client Deletion**\n\n"
                    f"**Client**: {MessageFormatter.escape_markdown(client.name)}\n"
                    f"**ID**: {client.id}\n"
                    f"**Tasks**: {len(tasks)} assigned\n\n"
                    f"⚠️ **Warning**: This will unassign all tasks from this client.\n\n"
                    f"Are you sure you want to delete this client?",
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            logger.error(f"Error showing client delete confirmation for {client_id}: {e}")
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Error preparing client deletion",
                    "Please try again or use /allclients command."
                ),
                parse_mode='MarkdownV2'
            )

    async def _confirm_client_delete(self, query, context: ContextTypes.DEFAULT_TYPE, client_id: int) -> None:
        """Confirm client deletion: delete client, unassign tasks, show success message."""
        from larrybot.storage.db import get_session
        from larrybot.storage.client_repository import ClientRepository
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.core.event_utils import emit_client_event
        from larrybot.utils.ux_helpers import MessageFormatter
        try:
            with next(get_session()) as session:
                client_repo = ClientRepository(session)
                task_repo = TaskRepository(session)
                client = client_repo.get_client_by_id(client_id)
                if not client:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Client ID {client_id} not found",
                            "The client may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                tasks = task_repo.get_tasks_by_client(client.name)
                # Unassign all tasks
                for task in tasks:
                    task_repo.unassign_task(task.id)
                client_repo.remove_client(client.name)
                emit_client_event(None, "client_removed", client)
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_success_message(
                        f"🗑️ Client deleted successfully!",
                        {
                            "Client": client.name,
                            "ID": client.id,
                            "Unassigned Tasks": len(tasks),
                            "Action": "Client removed from database"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            logger.error(f"Error deleting client {client_id}: {e}")
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Error deleting client",
                    "Please try again or use /allclients command."
                ),
                parse_mode='MarkdownV2'
            )

    # Placeholder methods for habit callbacks
    async def _handle_habit_done(self, query, context: ContextTypes.DEFAULT_TYPE, habit_id: int) -> None:
        """Handle habit completion."""
        from larrybot.storage.db import get_session
        from larrybot.storage.habit_repository import HabitRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        from datetime import datetime
        
        try:
            with next(get_session()) as session:
                repo = HabitRepository(session)
                habit = repo.get_habit_by_id(habit_id)
                
                if not habit:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Habit #{habit_id} not found",
                            "The habit may have been deleted."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                # Mark habit as done
                updated_habit = repo.mark_habit_done(habit.name)
                
                if not updated_habit:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Failed to complete habit '{habit.name}'",
                            "Please try again."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                # Calculate streak emoji
                streak_emoji = "🔥" if updated_habit.streak >= 7 else "📈" if updated_habit.streak >= 3 else "✅"
                
                # Check if this is a milestone
                milestone_message = ""
                if updated_habit.streak == 7:
                    milestone_message = "\n🎉 **7-day streak milestone!**"
                elif updated_habit.streak == 30:
                    milestone_message = "\n🏆 **30-day streak milestone!**"
                elif updated_habit.streak == 100:
                    milestone_message = "\n👑 **100-day streak milestone!**"
                
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_success_message(
                        f"Habit completed for today! {streak_emoji}",
                        {
                            "Habit": updated_habit.name,
                            "Current Streak": f"{updated_habit.streak} days {streak_emoji}",
                            "Last Completed": updated_habit.last_completed.strftime("%Y-%m-%d %H:%M") if updated_habit.last_completed else "N/A"
                        }
                    ) + milestone_message,
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Failed to complete habit",
                    f"Error: {str(e)}"
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_habit_progress(self, query, context: ContextTypes.DEFAULT_TYPE, habit_id: int) -> None:
        """Handle habit progress view."""
        from larrybot.storage.db import get_session
        from larrybot.storage.habit_repository import HabitRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        from datetime import datetime
        
        try:
            with next(get_session()) as session:
                repo = HabitRepository(session)
                habit = repo.get_habit_by_id(habit_id)
                
                if not habit:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Habit #{habit_id} not found",
                            "The habit may have been deleted."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                # Calculate progress metrics
                today = get_current_datetime().date()
                days_since_creation = (today - habit.created_at.date()).days + 1 if habit.created_at else 0
                completion_rate = (habit.streak / days_since_creation * 100) if days_since_creation > 0 else 0
                
                # Visual progress bar (30 characters)
                progress_length = int((habit.streak / max(days_since_creation, 1)) * 30)
                progress_bar = "█" * progress_length + "░" * (30 - progress_length)
                
                # Streak milestone
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
                
                # Format progress details
                message = f"📊 **Habit Progress Report**\n\n"
                message += f"**Habit**: {MessageFormatter.escape_markdown(habit.name)}\n"
                message += f"**Current Streak**: {habit.streak} days\n"
                message += f"**Days Tracked**: {days_since_creation} days\n"
                message += f"**Completion Rate**: {completion_rate:.1f}%\n\n"
                
                message += f"📈 **Progress Bar**\n"
                message += f"`{progress_bar}`\n"
                message += f"`{habit.streak:>3} / {days_since_creation:>3} days`\n\n"
                
                if next_milestone:
                    message += f"🎯 **Next Milestone**\n"
                    message += f"• Target: {next_milestone} days\n"
                    message += f"• Days needed: {days_to_milestone}\n\n"
                
                if habit.last_completed:
                    # Handle both datetime and date objects
                    if hasattr(habit.last_completed, 'date'):
                        last_completed_date = habit.last_completed.date()
                    else:
                        last_completed_date = habit.last_completed
                    days_since_last = (today - last_completed_date).days
                    
                    message += f"📅 **Recent Activity**\n"
                    if days_since_last == 0:
                        message += f"• Last completed: Today ✅\n"
                    elif days_since_last == 1:
                        message += f"• Last completed: Yesterday ⚠️\n"
                    else:
                        message += f"• Last completed: {days_since_last} days ago ❌\n"
                
                # Add navigation keyboard
                keyboard = [
                    [InlineKeyboardButton("✅ Complete Today", callback_data=f"habit_done:{habit_id}")],
                    [InlineKeyboardButton("⬅️ Back to Habits", callback_data="habit_refresh")]
                ]
                
                await safe_edit(query.edit_message_text, 
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Failed to load habit progress",
                    f"Error: {str(e)}"
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_habit_delete(self, query, context: ContextTypes.DEFAULT_TYPE, habit_id: int) -> None:
        """Handle habit deletion."""
        from larrybot.utils.ux_helpers import KeyboardBuilder
        
        await safe_edit(query.edit_message_text, 
            f"🗑️ **Confirm Habit Deletion**\n\nAre you sure you want to delete this habit?",
            reply_markup=KeyboardBuilder.build_confirmation_keyboard("habit_delete", habit_id),
            parse_mode='MarkdownV2'
        )

    async def _confirm_habit_delete(self, query, context: ContextTypes.DEFAULT_TYPE, habit_id: int) -> None:
        """Confirm habit deletion."""
        from larrybot.storage.db import get_session
        from larrybot.storage.habit_repository import HabitRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        
        try:
            with next(get_session()) as session:
                repo = HabitRepository(session)
                habit = repo.get_habit_by_id(habit_id)
                
                if habit:
                    repo.delete_habit(habit_id)
                    
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_success_message(
                            f"Habit '{habit.name}' deleted successfully!",
                            {
                                "Habit ID": habit_id,
                                "Action": "deleted",
                                "Streak Lost": f"{habit.streak} days"
                            }
                        ),
                        parse_mode='MarkdownV2'
                    )
                else:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Habit #{habit_id} not found",
                            "The habit may have already been deleted."
                        ),
                        parse_mode='MarkdownV2'
                    )
        except Exception as e:
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Failed to delete habit",
                    f"Error: {str(e)}"
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_habit_add(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle habit add button click."""
        from larrybot.utils.ux_helpers import MessageFormatter
        
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "Add New Habit",
                {
                    "Command": "/habit_add <name>",
                    "Example": "/habit_add Morning Exercise",
                    "Description": "Create a new habit to track daily"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_habit_stats(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle habit statistics button click."""
        from larrybot.storage.db import get_session
        from larrybot.storage.habit_repository import HabitRepository
        from larrybot.utils.ux_helpers import MessageFormatter, ChartBuilder
        from datetime import datetime
        
        try:
            with next(get_session()) as session:
                repo = HabitRepository(session)
                habits = repo.list_habits()
                
                if not habits:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            "No habits found",
                            "Use /habit_add to create your first habit"
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                # Calculate statistics
                total_habits = len(habits)
                total_streak = sum(habit.streak for habit in habits)
                avg_streak = total_streak / total_habits if total_habits > 0 else 0
                
                # Find best performing habit
                best_habit = max(habits, key=lambda h: h.streak) if habits else None
                
                # Calculate completion rates
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
                
                completion_rate = (completed_today / total_habits * 100) if total_habits > 0 else 0
                
                # Build statistics message
                message = f"📊 **Habit Statistics**\n\n"
                message += f"**Total Habits**: {total_habits}\n"
                message += f"**Total Streak Days**: {total_streak}\n"
                message += f"**Average Streak**: {avg_streak:.1f} days\n"
                message += f"**Completed Today**: {completed_today}/{total_habits}\n"
                message += f"**Today's Rate**: {completion_rate:.1f}%\n\n"
                
                if best_habit:
                    message += f"🏆 **Best Performer**\n"
                    message += f"• {MessageFormatter.escape_markdown(best_habit.name)}\n"
                    message += f"• Streak: {best_habit.streak} days\n\n"
                
                # Add progress chart
                if habits:
                    streak_data = {habit.name: habit.streak for habit in habits}
                    progress_chart = ChartBuilder.build_bar_chart(
                        streak_data, 
                        "Current Streaks", 
                        max_width=15
                    )
                    message += f"📈 **Streak Overview**\n{progress_chart}\n"
                
                # Add navigation keyboard
                keyboard = [
                    [InlineKeyboardButton("🔄 Refresh", callback_data="habit_refresh")],
                    [InlineKeyboardButton("⬅️ Back to Habits", callback_data="habit_list")]
                ]
                
                await safe_edit(query.edit_message_text, 
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Failed to load habit statistics",
                    f"Error: {str(e)}"
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_habit_refresh(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle habit refresh button click."""
        from larrybot.storage.db import get_session
        from larrybot.storage.habit_repository import HabitRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        from datetime import datetime
        
        try:
            with next(get_session()) as session:
                repo = HabitRepository(session)
                habits = repo.list_habits()
                
                if not habits:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            "No habits found",
                            "Use /habit_add to create your first habit"
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                # Calculate today's date for streak calculations
                today = get_current_datetime().date()
                
                # Format habit list with rich formatting and action buttons
                message = f"🔄 **All Habits** \\({len(habits)} found\\)\n\n"
                
                # Create inline keyboard with per-habit action buttons
                keyboard = []
                
                for i, habit in enumerate(habits, 1):
                    # Calculate streak status
                    if habit.last_completed:
                        # Handle both datetime and date objects
                        if hasattr(habit.last_completed, 'date'):
                            last_completed_date = habit.last_completed.date()
                        else:
                            last_completed_date = habit.last_completed
                        days_since_last = (today - last_completed_date).days
                        
                        if days_since_last == 0:
                            status_emoji = "✅"  # Done today
                            status_text = "Completed today"
                            completed_today = True
                        elif days_since_last == 1:
                            status_emoji = "⚠️"  # Missed yesterday
                            status_text = "Missed yesterday"
                            completed_today = False
                        else:
                            status_emoji = "❌"  # Missed multiple days
                            status_text = f"Missed {days_since_last} days"
                            completed_today = False
                    else:
                        status_emoji = "⏳"  # Never completed
                        status_text = "Never completed"
                        completed_today = False
                    
                    # Streak emoji based on length
                    if habit.streak >= 30:
                        streak_emoji = "👑"
                    elif habit.streak >= 7:
                        streak_emoji = "🔥"
                    elif habit.streak >= 3:
                        streak_emoji = "📈"
                    else:
                        streak_emoji = "✅"
                    
                    message += f"{i}\\. {status_emoji} **{MessageFormatter.escape_markdown(habit.name)}**\n"
                    message += f"   {streak_emoji} Streak: {habit.streak} days\n"
                    message += f"   📅 {status_text}\n"
                    
                    if habit.last_completed:
                        message += f"   🕐 Last: {habit.last_completed.strftime('%Y-%m-%d')}\n"
                    
                    if habit.created_at:
                        message += f"   📅 Created: {habit.created_at.strftime('%Y-%m-%d')}\n"
                    message += "\n"
                    
                    # Add per-habit action buttons
                    habit_buttons = []
                    
                    # Show complete button only if not completed today
                    if not completed_today:
                        habit_buttons.append(InlineKeyboardButton(
                            "✅ Complete", 
                            callback_data=f"habit_done:{habit.id}"
                        ))
                    
                    habit_buttons.extend([
                        InlineKeyboardButton(
                            "📊 Progress", 
                            callback_data=f"habit_progress:{habit.id}"
                        ),
                        InlineKeyboardButton(
                            "🗑️ Delete", 
                            callback_data=f"habit_delete:{habit.id}"
                        )
                    ])
                    
                    keyboard.append(habit_buttons)
                
                # Add navigation buttons at the bottom
                keyboard.append([
                    InlineKeyboardButton("➕ Add Habit", callback_data="habit_add"),
                    InlineKeyboardButton("📊 Statistics", callback_data="habit_stats")
                ])
                keyboard.append([
                    InlineKeyboardButton("🔄 Refresh", callback_data="habit_refresh"),
                    InlineKeyboardButton("⬅️ Back", callback_data="nav_main")
                ])
                
                await safe_edit(query.edit_message_text, 
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Failed to refresh habits",
                    f"Error: {str(e)}"
                ),
                parse_mode='MarkdownV2'
            )

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            await update.message.reply_text(
                "🚫 **Unauthorized Access**\n\n"
                "This is a single-user bot designed for personal use. "
                "Only the configured user can access this bot.\n\n"
                "If you believe this is an error, please check your configuration."
            )
            return
        
        user_info = self.config.get_single_user_info()
        
        # Get user's first name from Telegram
        user_first_name = update.effective_user.first_name if update.effective_user.first_name else "there"
        
        welcome_message = (
            f"🎉 **Welcome to LarryBot2**\n\n"
            
            f"🎯 **What I Can Do For You:**\n\n"
            f"📋 **Task Management**\n"
            f"• Create tasks with natural language: `/add \"Call client tomorrow at 2pm\"`\n"
            f"• Set priorities, due dates, and categories\n"
            f"• Track time spent on tasks\n"
            f"• Bulk operations for efficiency\n\n"
            
            f"📅 **Smart Scheduling**\n"
            f"• Google Calendar integration\n"
            f"• Intelligent reminders and notifications\n"
            f"• Time zone awareness\n"
            f"• Agenda management\n\n"
            
            f"📈 **Productivity Insights**\n"
            f"• Analytics and progress tracking\n"
            f"• Performance monitoring\n"
            f"• Productivity reports\n"
            f"• Smart task suggestions\n\n"
            
            f"🔄 **Habit Building**\n"
            f"• Track daily habits\n"
            f"• Streak monitoring\n"
            f"• Progress visualization\n"
            f"• Habit analytics\n\n"
            
            f"👥 **Client Management**\n"
            f"• Organize tasks by client\n"
            f"• Client-specific analytics\n"
            f"• Project tracking\n"
            f"• Time allocation insights\n\n"
            
            f"🎮 **Quick Start Commands:**\n"
            f"• `/add \"Your first task\"` - Create a task\n"
            f"• `/list` - View all tasks\n"
            f"• `/today` - See today's agenda\n"
            f"• `/analytics` - View productivity insights\n"
            f"• `/help` - Full command reference\n\n"
            
            f"💡 **Pro Tips:**\n"
            f"• Use natural language for task creation\n"
            f"• Try `/suggest` for intelligent task recommendations\n"
            f"• Use `/bulk_operations` for managing multiple tasks\n"
            f"• Check `/health` for system status\n\n"
            
            f"🔧 **Need Help?**\n"
            f"• `/help` - Complete command reference\n"
            f"• `/health` - System status and diagnostics\n"
            f"• `/examples` - See usage examples\n\n"
            
            f"🌟 **Ready to boost your productivity?** Use the buttons below to get started!"
        )
        
        # Create action buttons using confirmed working callback handlers
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [
                InlineKeyboardButton("➕ Add Task", callback_data="add_task"),
                InlineKeyboardButton("📋 View Tasks", callback_data="menu_tasks"),
                InlineKeyboardButton("🔄 Refresh Tasks", callback_data="tasks_refresh")
            ],
            [
                InlineKeyboardButton("🔄 Habits", callback_data="menu_habits"),
                InlineKeyboardButton("👥 Clients", callback_data="menu_clients"),
                InlineKeyboardButton("📅 Today's Calendar", callback_data="calendar_today")
            ],
            [
                InlineKeyboardButton("📊 Analytics", callback_data="menu_analytics"),
                InlineKeyboardButton("⏰ Reminders", callback_data="menu_reminders"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="nav_main")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            await update.message.reply_text("🚫 Unauthorized access.")
            return
        
        commands = list(self.command_registry._commands.keys())
        
        # Get command metadata for better organization
        command_metadata = {}
        for cmd in commands:
            metadata = self.command_registry.get_command_metadata(cmd)
            if metadata:
                command_metadata[cmd] = metadata
        
        # Organize commands by category
        categories = {}
        for cmd, metadata in command_metadata.items():
            category = metadata.category
            if category not in categories:
                categories[category] = []
            categories[category].append((cmd, metadata))
        
        # Build help text with proper Markdown escaping
        help_text = "📋 *Available Commands*\n\n"
        
        # Define category display order and names
        category_order = [
            ("tasks", "Advanced Task Features"),
            ("task", "Basic Task Management"),
            ("client", "Client Management"),
            ("habit", "Habit Tracking"),
            ("calendar", "Calendar Integration"),
            ("reminder", "Reminders"),
            ("analytics", "Analytics"),
            ("system", "System"),
            ("examples", "Examples"),
            ("general", "General")
        ]
        
        def escape_markdown(text: str) -> str:
            """Escape special characters that could break Markdown parsing."""
            if not text:
                return text
            # Escape characters that have special meaning in Markdown
            escaped = text.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
            escaped = escaped.replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`')
            escaped = escaped.replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-')
            escaped = escaped.replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}')
            escaped = escaped.replace('.', '\\.').replace('!', '\\!')
            return escaped
        
        for category_key, category_name in category_order:
            if category_key in categories:
                help_text += f"*{escape_markdown(category_name)}:*\n"
                for cmd, metadata in sorted(categories[category_key]):
                    # Format command with description
                    cmd_name = cmd.lstrip("/")
                    description = metadata.description or f"Handler for {cmd}"
                    # Escape the description to prevent Markdown parsing errors
                    safe_description = escape_markdown(description)
                    help_text += f"• `/{cmd_name}` \\- {safe_description}\n"
                help_text += "\n"
        
        # Add any uncategorized commands
        uncategorized = []
        for cmd in commands:
            if cmd not in command_metadata:
                uncategorized.append(cmd)
        
        if uncategorized:
            help_text += "*Other Commands:*\n"
            for cmd in sorted(uncategorized):
                cmd_name = cmd.lstrip("/")
                help_text += f"• `/{cmd_name}`\n"
            help_text += "\n"
        
        help_text += f"*Total Commands*: {len(commands)}"
        
        try:
            await update.message.reply_text(escape_markdown_v2(help_text), parse_mode='MarkdownV2')
        except Exception as e:
            # Fallback to plain text if Markdown fails
            fallback_text = "📋 Available Commands\n\n"
            for category_key, category_name in category_order:
                if category_key in categories:
                    fallback_text += f"{category_name}:\n"
                    for cmd, metadata in sorted(categories[category_key]):
                        cmd_name = cmd.lstrip("/")
                        description = metadata.description or f"Handler for {cmd}"
                        fallback_text += f"• /{cmd_name} - {description}\n"
                    fallback_text += "\n"
            
            if uncategorized:
                fallback_text += "Other Commands:\n"
                for cmd in sorted(uncategorized):
                    cmd_name = cmd.lstrip("/")
                    fallback_text += f"• /{cmd_name}\n"
                fallback_text += "\n"
            
            fallback_text += f"Total Commands: {len(commands)}"
            await update.message.reply_text(fallback_text)

    async def _dispatch_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return  # Ignore non-text messages
        if not self._is_authorized(update):
            await update.message.reply_text("🚫 Unauthorized access.")
            return
        command = f"/{update.message.text.split()[0].lstrip('/')}"
        try:
            result = self.command_registry.dispatch(command, update, context)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    def run(self) -> None:
        # Set the main event loop for the reminder handler before starting
        try:
            loop = asyncio.get_event_loop()
            set_main_event_loop(loop)
            print("Main event loop set for reminder handler", flush=True)
        except RuntimeError:
            print("Could not set event loop before bot start", flush=True)
        
        # Schedule daily report at 9am
        from larrybot.scheduler import schedule_daily_report
        schedule_daily_report(self, self.config.ALLOWED_TELEGRAM_USER_ID, hour=9, minute=0)
        
        # Start the bot
        self.application.run_polling()
    
    async def run_async(self) -> None:
        """
        Async version of run() that integrates with the unified event loop.
        This allows for proper task management and graceful shutdown.
        """
        # Set the main event loop for the reminder handler
        try:
            loop = asyncio.get_running_loop()
            set_main_event_loop(loop)
            logger.info("Main event loop set for reminder handler")
        except RuntimeError as e:
            logger.warning(f"Could not set event loop: {e}")
        
        # Get the task manager to monitor for shutdown signals
        from larrybot.core.task_manager import get_task_manager
        task_manager = get_task_manager()
        
        # Initialize and start the application
        try:
            await self.application.initialize()
            await self.application.start()
            
            logger.info("🚀 Telegram bot started successfully")
            
            # Start polling in a way that can be gracefully shutdown
            await self.application.updater.start_polling()
            
            # Keep running until shutdown is requested
            # Monitor the task manager's shutdown event
            try:
                logger.info("🔄 Bot running - waiting for shutdown signal...")
                
                # Wait for the task manager's shutdown signal
                while not task_manager.is_shutdown_requested:
                    try:
                        # Check shutdown signal every 0.5 seconds for faster response
                        await asyncio.wait_for(
                            task_manager._shutdown_event.wait(), 
                            timeout=0.5
                        )
                        # If we get here, shutdown was requested
                        break
                    except asyncio.TimeoutError:
                        # Continue running - check again
                        continue
                
                logger.info("🛑 Shutdown signal received - stopping bot...")
                
            except asyncio.CancelledError:
                logger.info("🛑 Bot task cancelled")
                raise
                
        except asyncio.CancelledError:
            logger.info("🛑 Bot cancelled gracefully")
            raise
        except Exception as e:
            logger.error(f"❌ Bot error: {e}")
            raise
        finally:
            # Cleanup
            try:
                logger.info("🧹 Stopping bot updater...")
                await self.application.updater.stop()
                
                logger.info("🧹 Stopping bot application...")
                await self.application.stop()
                
                logger.info("🧹 Shutting down bot application...")
                await self.application.shutdown()
                
                # Clean up reminder handler
                try:
                    from larrybot.plugins.reminder import cleanup_reminder_handler
                    await cleanup_reminder_handler()
                except Exception as e:
                    logger.warning(f"Error during reminder handler cleanup: {e}")
                
                logger.info("✅ Bot shutdown completed")
                
            except Exception as e:
                logger.error(f"Error during bot shutdown: {e}")

    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages with enhanced narrative processing and task editing."""
        user_message = update.message.text.strip() if update.message and update.message.text else None
        if not user_message:
            return

        # Check if user is in task editing mode
        if 'editing_task_id' in context.user_data:
            await self._handle_task_edit_mode(update, context, user_message)
            return

        # Check if user is in narrative task creation mode
        if 'task_creation_state' in context.user_data:
            from larrybot.plugins.tasks import handle_narrative_task_creation
            await handle_narrative_task_creation(update, context, user_message)
            return

        # Enhanced narrative processing for free-form text
        user_id = update.effective_user.id if update.effective_user else None
        processed_input = self.enhanced_narrative_processor.process_input(user_message, user_id)
        
        # Store NLP results in context for debugging/legacy compatibility
        context.user_data['nlp_intent'] = processed_input.intent.value
        context.user_data['nlp_entities'] = processed_input.entities
        context.user_data['nlp_sentiment'] = processed_input.context.sentiment
        
        # Route based on intent with confidence threshold
        if processed_input.confidence > 0.5:
            await self._handle_narrative_intent(update, context, processed_input)
        else:
            # Low confidence - show help and suggestions
            await self._handle_low_confidence_input(update, context, processed_input)

    async def _handle_task_edit_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str) -> None:
        """Handle text input when user is in task editing mode."""
        task_id = context.user_data['editing_task_id']
        new_description = user_message
        if not new_description:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Description cannot be empty",
                    "Please provide a valid task description."
                ),
            )
            return
        await self._process_task_edit(update, context, task_id, new_description)

    async def _handle_narrative_intent(self, update: Update, context: ContextTypes.DEFAULT_TYPE, processed_input) -> None:
        """Handle narrative input based on detected intent."""
        from larrybot.nlp.enhanced_narrative_processor import IntentType
        
        # Send the narrative processor's response message
        await update.message.reply_text(
            processed_input.response_message,
            parse_mode='MarkdownV2'
        )
        
        # Route to appropriate command handler if suggested
        if processed_input.suggested_command:
            await self._execute_suggested_command(update, context, processed_input)

    async def _handle_low_confidence_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, processed_input) -> None:
        """Handle input with low confidence - show help and context-aware command suggestions."""
        # Determine context-aware suggestions
        suggestions = []
        user_context = context.user_data
        
        # If user is editing a task
        if 'editing_task_id' in user_context:
            suggestions.append("/edit <new description> — Edit the current task")
            suggestions.append("/cancel — Cancel editing")
        # If user is viewing a task
        elif user_context.get('current_context') == 'task_view' or user_context.get('last_viewed_task_id'):
            suggestions.append("/edit <desc> — Edit this task")
            suggestions.append("/done — Mark as complete")
            suggestions.append("/delete — Delete this task")
        # If user is in the main task list
        elif user_context.get('current_context') == 'tasks':
            suggestions.append("/add <desc> — Add a new task")
            suggestions.append("/list — Show all tasks")
            suggestions.append("/search <query> — Search tasks")
            suggestions.append("/analytics — View analytics")
        else:
            # General suggestions
            suggestions.append("/add <desc> — Add a new task")
            suggestions.append("/list — Show all tasks")
            suggestions.append("/remind <desc> — Add a reminder")
            suggestions.append("/help — Show all commands")
        
        # Always include help and list as fallback
        if "/help — Show all commands" not in suggestions:
            suggestions.append("/help — Show all commands")
        if "/list — Show all tasks" not in suggestions:
            suggestions.append("/list — Show all tasks")
        
        help_message = (
            "🤔 I'm not sure what you'd like to do. Here are some things you can try:\n\n" +
            "\n".join(f"• {s}" for s in suggestions)
        )
        
        await update.message.reply_text(help_message)

    async def _execute_suggested_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, processed_input) -> None:
        """Execute the suggested command with extracted parameters."""
        from larrybot.plugins.tasks import add_task
        from larrybot.plugins.tasks import list_tasks
        from larrybot.plugins.tasks import search_tasks
        from larrybot.plugins.reminder import add_reminder
        from larrybot.plugins.analytics import show_analytics
        
        command = processed_input.suggested_command
        params = processed_input.suggested_parameters
        
        try:
            if command == "/add" and params.get('description'):
                # Create task with extracted parameters
                description = params['description']
                priority = params.get('priority', 'Medium')
                category = params.get('category')
                due_date = params.get('due_date')
                
                # Call the add_task function directly
                await add_task(update, context, description, priority, category, due_date)
                
            elif command == "/list":
                # List tasks with optional filters
                priority = params.get('priority')
                category = params.get('category')
                await list_tasks(update, context, priority, category)
                
            elif command == "/search" and params.get('query'):
                # Search tasks
                query = params['query']
                await search_tasks(update, context, query)
                
            elif command == "/remind" and params.get('task_name'):
                # Add reminder
                task_name = params['task_name']
                due_date = params.get('due_date')
                await add_reminder(update, context, task_name, due_date)
                
            elif command == "/analytics":
                # Show analytics
                await show_analytics(update, context)
                
        except Exception as e:
            logger.error(f"Error executing suggested command {command}: {e}")
            await update.message.reply_text(
                "❌ Sorry, I couldn't execute that command automatically. Please try using the command directly."
            )

    async def _handle_task_disclosure(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle progressive disclosure for task views."""
        try:
            # Always answer the callback query first
            await query.answer()
            
            # Parse disclosure data: task_disclose:task_id:level
            parts = query.data.split(':')
            if len(parts) >= 3:
                task_id = int(parts[1])
                disclosure_level = int(parts[2])
                
                # Store disclosure level in context
                context.user_data[f'task_disclosure_{task_id}'] = disclosure_level
                
                # Re-show task view with new disclosure level
                await self._handle_task_view(query, context, task_id)
            else:
                logger.error(f"Invalid task disclosure callback data: {query.data}")
                # Send error message so tests can see it
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_error_message(
                        "Invalid disclosure data",
                        "Please try again or use a different action."
                    ),
                    parse_mode='MarkdownV2'
                )
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing task disclosure callback: {e}")
            await safe_edit(query.edit_message_text,
                MessageFormatter.format_error_message(
                    "Error processing request",
                    "Please try again or use a different action."
                ),
                parse_mode='MarkdownV2'
            )

    async def _process_task_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int, new_description: str) -> None:
        """Process the actual task editing."""
        from larrybot.storage.db import get_session
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.core.event_utils import emit_task_event
        from larrybot.utils.ux_helpers import MessageFormatter
        from datetime import datetime
        
        try:
            with next(get_session()) as session:
                repo = TaskRepository(session)
                task = repo.edit_task(task_id, new_description)
                
                if task:
                    # Emit event for task editing
                    emit_task_event(None, "task_edited", task)
                    
                    # Clear the editing state
                    del context.user_data['editing_task_id']
                    
                    await update.message.reply_text(
                        MessageFormatter.format_success_message(
                            "✏️ Task updated successfully!",
                            {
                                "Task": task.description,
                                "ID": task_id,
                                "Status": "Updated",
                                "Modified": get_current_datetime().strftime("%Y-%m-%d %H:%M")
                            }
                        ),
                        parse_mode='MarkdownV2'
                    )
                else:
                    await update.message.reply_text(
                        MessageFormatter.format_error_message(
                            f"Task ID {task_id} not found",
                            "The task may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    
        except Exception as e:
            logger.error(f"Error editing task {task_id}: {e}")
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Error updating task",
                    "Please try again or use /edit command."
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_tasks_refresh(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle task list refresh with timeout protection and loading indicator."""
        try:
            # Show loading indicator
            await safe_edit(query.edit_message_text, "🔄 Refreshing tasks\\.\\.\\.", parse_mode='MarkdownV2')
            
            # Add timeout to prevent blocking during network/database issues
            await asyncio.wait_for(self._handle_tasks_refresh_operation(query, context), timeout=10.0)
                    
        except asyncio.TimeoutError:
            logger.error("Tasks refresh timeout")
            try:
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_error_message(
                        "⏱️ Refresh timed out",
                        "Please try the command again\\."
                    ),
                    parse_mode='MarkdownV2'
                )
            except Exception as e:
                logger.error(f"Failed to send timeout message: {e}")
        except Exception as e:
            logger.error(f"Error refreshing tasks: {e}")
            try:
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_error_message(
                        "❌ Refresh failed",
                        "Please try again later."
                    ),
                    parse_mode='MarkdownV2'
                )
            except Exception as nested_e:
                logger.error(f"Failed to send error message: {nested_e}")
                # Fallback to simple text without Markdown if escaping fails
                try:
                    await safe_edit(query.edit_message_text, 
                        "❌ Refresh failed. Please try again later.",
                        parse_mode=None
                    )
                except Exception:
                    pass  # Last resort - don't let error handling cause more errors

    async def _handle_tasks_refresh_operation(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the actual tasks refresh operation with progressive disclosure and smart suggestions."""
        from larrybot.utils.ux_helpers import MessageFormatter
        from larrybot.utils.enhanced_ux_helpers import MessageLayoutBuilder, UnifiedButtonBuilder, ButtonType
        
        with next(get_session()) as session:
            repo = TaskRepository(session)
            tasks = repo.list_incomplete_tasks()
            
            if not tasks:
                message = "📋 **All Tasks Complete\\!** 🎉\n\nNo incomplete tasks found\\."
                keyboard = UnifiedButtonBuilder.build_entity_keyboard(
                    entity_id=0,
                    entity_type="add_task",
                    available_actions=[],
                    custom_actions=[
                        {
                            "text": "➕ Add New Task",
                            "callback_data": "add_task",
                            "type": ButtonType.PRIMARY,
                            "emoji": "➕"
                        },
                        {
                            "text": "🏠 Main Menu",
                            "callback_data": "nav_main",
                            "type": ButtonType.SECONDARY,
                            "emoji": "🏠"
                        }
                    ]
                )
            else:
                # Use progressive list with smart suggestions
                message = MessageLayoutBuilder.build_progressive_list(
                    items=tasks,
                    max_visible=5,
                    title="Incomplete Tasks"
                )
                
                # Add smart suggestions based on task list
                suggestions = []
                high_priority_count = sum(1 for t in tasks if getattr(t, 'priority', 'Medium') in ['High', 'Critical'])
                from larrybot.utils.datetime_utils import ensure_timezone_aware
                now_dt = get_current_datetime()
                overdue_count = sum(
                    1
                    for t in tasks
                    if t.due_date and ensure_timezone_aware(t.due_date) < now_dt
                )
                
                if high_priority_count > 0:
                    suggestions.append(f"⚠️ **{high_priority_count} high priority tasks** need attention")
                if overdue_count > 0:
                    suggestions.append(f"🚨 **{overdue_count} overdue tasks** require immediate action")
                if len(tasks) > 10:
                    suggestions.append("💡 **Tip:** Use filters to focus on specific tasks")
                
                if suggestions:
                    # Escape suggestions for MarkdownV2 format
                    escaped_suggestions = [MessageFormatter.escape_markdown(suggestion) for suggestion in suggestions]
                    message += "\n\n" + "\n".join(escaped_suggestions)
                
                # Build progressive keyboard with smart actions
                custom_actions = [
                    {
                        "text": "➕ Add Task",
                        "callback_data": "add_task",
                        "type": ButtonType.PRIMARY,
                        "emoji": "➕"
                    },
                    {
                        "text": "🔍 Search",
                        "callback_data": "tasks_search",
                        "type": ButtonType.SECONDARY,
                        "emoji": "🔍"
                    }
                ]
                
                # Add filter suggestions if many tasks
                if len(tasks) > 5:
                    custom_actions.append({
                        "text": "🔧 Filter",
                        "callback_data": "tasks_filter",
                        "type": ButtonType.SECONDARY,
                        "emoji": "🔧"
                    })
                
                # Add analytics if there are tasks
                if tasks:
                    custom_actions.append({
                        "text": "📊 Analytics",
                        "callback_data": "tasks_analytics",
                        "type": ButtonType.INFO,
                        "emoji": "📊"
                    })
                
                keyboard = UnifiedButtonBuilder.build_list_keyboard(
                    items=[{"id": t.id, "description": t.description} for t in tasks[:5]],
                    item_type="task",
                    max_items=5,
                    show_navigation=True,
                    navigation_actions=[]
                )
                
                # Add custom actions row
                # Create new keyboard with additional custom actions since inline_keyboard is read-only
                existing_buttons = list(keyboard.inline_keyboard)
                custom_action_buttons = [
                    UnifiedButtonBuilder.create_button(
                        text=action["text"],
                        callback_data=action["callback_data"],
                        button_type=action["type"],
                        custom_emoji=action["emoji"]
                    ) for action in custom_actions
                ]
                existing_buttons.append(custom_action_buttons)
                keyboard = InlineKeyboardMarkup(existing_buttons)
            
            await safe_edit(query.edit_message_text, 
                message,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )

    async def _handle_task_view(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Show detailed view of a task with progressive disclosure and smart suggestions."""
        from larrybot.storage.db import get_session
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        from larrybot.utils.enhanced_ux_helpers import ProgressiveDisclosureBuilder, ContextAwareButtonBuilder
        
        try:
            with next(get_session()) as session:
                repo = TaskRepository(session)
                task = repo.get_task_by_id(task_id)
                if not task:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Task ID {task_id} not found",
                            "The task may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                # Build task data for progressive disclosure
                task_data = {
                    'id': task.id,
                    'description': task.description,
                    'status': getattr(task, 'status', 'Todo'),
                    'priority': getattr(task, 'priority', 'Medium'),
                    'due_date': getattr(task, 'due_date', None),
                    'category': getattr(task, 'category', None),
                    'tags': getattr(task, 'tags', None),
                    'created_at': getattr(task, 'created_at', None)
                }
                
                # Build detailed message with smart suggestions
                details = {k: v for k, v in task_data.items() if v is not None and k != 'id'}
                
                # Add smart suggestions based on task state
                suggestions = []
                if task_data['status'] == 'Todo' and not task_data.get('due_date'):
                    suggestions.append("💡 **Suggestion:** Add a due date to track progress")
                if task_data['priority'] == 'Medium' and task_data['status'] == 'Todo':
                    suggestions.append("💡 **Suggestion:** Consider setting priority for better organization")
                if task_data['status'] == 'In Progress':
                    suggestions.append("💡 **Suggestion:** Use time tracking to monitor progress")
                
                # Build message with suggestions
                message = MessageFormatter.format_success_message("Task Details", details)
                if suggestions:
                    # Escape suggestions for MarkdownV2 format
                    escaped_suggestions = [MessageFormatter.escape_markdown(suggestion) for suggestion in suggestions]
                    message += "\n\n" + "\n".join(escaped_suggestions)
                
                # Get disclosure level from context (default to 1 for progressive disclosure)
                disclosure_level = context.user_data.get(f'task_disclosure_{task_id}', 1)
                
                # Use progressive disclosure keyboard
                keyboard = ProgressiveDisclosureBuilder.build_progressive_task_keyboard(
                    task_id=task_id,
                    task_data=task_data,
                    disclosure_level=disclosure_level
                )
                
                await safe_edit(query.edit_message_text, 
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            logger.error(f"Error showing task view for {task_id}: {e}")
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Error showing task details",
                    "Please try again or use /list command."
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_add_task(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle add task button press - guide user to use the /add command."""
        from larrybot.utils.ux_helpers import MessageFormatter
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        # Set user in add task mode for better UX
        context.user_data['add_task_mode'] = True
        
        message = "📝 **Add New Task**\n\n"
        message += "**How to add a task:**\n"
        message += "• Use `/add <description>` for a simple task\n"
        message += "• Use `/add <description> priority:<level>` for priority\n"
        message += "• Use `/add <description> due:<date>` for due date\n"
        message += "• Use `/add <description> client:<name>` for client assignment\n\n"
        message += "**Examples:**\n"
        message += "• `/add Review quarterly reports`\n"
        message += "• `/add Call client priority:High due:tomorrow`\n"
        message += "• `/add Prepare presentation client:John Doe`\n\n"
        message += "**Tip:** You can combine multiple options in one command!"
        
        # Escape the message for MarkdownV2
        escaped_message = MessageFormatter.escape_markdown(message)
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 View Tasks", callback_data="tasks_refresh"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
            ]
        ])
        
        await safe_edit(query.edit_message_text, 
            escaped_message,
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )

    async def _handle_client_view(self, query, context: ContextTypes.DEFAULT_TYPE, client_id: int) -> None:
        """Show detailed view of a client with action buttons and navigation."""
        from larrybot.storage.db import get_session
        from larrybot.storage.client_repository import ClientRepository
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        try:
            with next(get_session()) as session:
                client_repo = ClientRepository(session)
                task_repo = TaskRepository(session)
                client = client_repo.get_client_by_id(client_id)
                if not client:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Client ID {client_id} not found",
                            "The client may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                tasks = task_repo.get_tasks_by_client(client.name)
                completed_tasks = sum(1 for t in tasks if t.done)
                pending_tasks = len(tasks) - completed_tasks
                completion_rate = (completed_tasks / len(tasks) * 100) if tasks else 0
                details = {
                    "Name": client.name,
                    "ID": client.id,
                    "Created": client.created_at.strftime("%Y-%m-%d %H:%M") if client.created_at else None,
                    "Total Tasks": len(tasks),
                    "Completed": completed_tasks,
                    "Pending": pending_tasks,
                    "Completion Rate": f"{completion_rate:.1f}%"
                }
                details = {k: v for k, v in details.items() if v is not None}
                message = MessageFormatter.format_success_message("Client Details", details)
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✏️ Edit", callback_data=f"client_edit:{client.id}"),
                        InlineKeyboardButton("🗑️ Delete", callback_data=f"client_delete:{client.id}"),
                        InlineKeyboardButton("📊 Analytics", callback_data=f"client_analytics:{client.id}")
                    ],
                    [InlineKeyboardButton("⬅️ Back to List", callback_data="client_refresh")]
                ])
                await safe_edit(query.edit_message_text, 
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            logger.error(f"Error showing client view for {client_id}: {e}")
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Error showing client details",
                    "Please try again or use /allclients command."
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_client_edit(self, query, context: ContextTypes.DEFAULT_TYPE, client_id: int) -> None:
        """Handle client edit action."""
        from larrybot.storage.db import get_session
        from larrybot.storage.client_repository import ClientRepository
        from larrybot.utils.ux_helpers import MessageFormatter
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        try:
            with next(get_session()) as session:
                client_repo = ClientRepository(session)
                client = client_repo.get_client_by_id(client_id)
                
                if not client:
                    await safe_edit(query.edit_message_text, 
                        MessageFormatter.format_error_message(
                            f"Client ID {client_id} not found",
                            "The client may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                # Show edit instructions - following the pattern of other edit handlers
                message = f"✏️ **Edit Client: {MessageFormatter.escape_markdown(client.name)}**\n\n"
                message += f"**Current Information:**\n"
                message += f"• Name: {MessageFormatter.escape_markdown(client.name)}\n"
                message += f"• ID: {client.id}\n"
                message += f"• Created: {client.created_at.strftime('%Y-%m-%d %H:%M') if client.created_at else 'Unknown'}\n\n"
                message += "**To edit this client:**\n"
                message += f"Use: `/editclient {client.id} <new_name>`\n\n"
                message += f"Example: `/editclient {client.id} Updated Client Name`"
                
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("⬅️ Back to Client", callback_data=f"client_view:{client.id}"),
                        InlineKeyboardButton("🗑️ Delete Client", callback_data=f"client_delete:{client.id}")
                    ]
                ])
                
                await safe_edit(query.edit_message_text, 
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            logger.error(f"Error showing client edit for {client_id}: {e}")
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Error showing client edit",
                    "Please try again or use /editclient command."
                ),
                parse_mode='MarkdownV2'
            )

    # New callback handlers
    async def _handle_reminder_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reminder-related callback queries."""
        callback_data = query.data
        
        if callback_data == "reminder_add":
            await self._handle_reminder_add(query, context)
        elif callback_data == "reminder_stats":
            await self._handle_reminder_stats(query, context)
        elif callback_data == "reminder_refresh":
            await self._handle_reminder_refresh(query, context)
        elif callback_data == "reminder_dismiss":
            await self._handle_reminder_dismiss(query, context)
        elif callback_data.startswith("reminder_snooze:"):
            parts = callback_data.split(":")
            reminder_id = int(parts[1])
            duration = parts[2] if len(parts) > 2 else "1h"
            await self._handle_reminder_snooze(query, context, reminder_id, duration)
        elif callback_data.startswith("reminder_delete:"):
            reminder_id = int(callback_data.split(":")[1])
            await self._handle_reminder_delete(query, context, reminder_id)
        elif callback_data.startswith("reminder_complete:"):
            reminder_id = int(callback_data.split(":")[1])
            await self._handle_reminder_complete(query, context, reminder_id)
        elif callback_data.startswith("reminder_edit:"):
            reminder_id = int(callback_data.split(":")[1])
            await self._handle_reminder_edit(query, context, reminder_id)
        elif callback_data.startswith("reminder_reactivate:"):
            reminder_id = int(callback_data.split(":")[1])
            await self._handle_reminder_reactivate(query, context, reminder_id)
        else:
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Unknown reminder action",
                    "Please use the /reminders command for now."
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_attachment_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle attachment-related callback queries."""
        callback_data = query.data
        
        if callback_data.startswith("attachment_edit_desc:"):
            attachment_id = int(callback_data.split(":")[1])
            await self._handle_attachment_edit_desc(query, context, attachment_id)
        elif callback_data.startswith("attachment_details:"):
            attachment_id = int(callback_data.split(":")[1])
            await self._handle_attachment_details(query, context, attachment_id)
        elif callback_data.startswith("attachment_remove:"):
            attachment_id = int(callback_data.split(":")[1])
            await self._handle_attachment_remove(query, context, attachment_id)
        elif callback_data.startswith("attachment_stats:"):
            task_id = int(callback_data.split(":")[1])
            await self._handle_attachment_stats(query, context, task_id)
        elif callback_data.startswith("attachment_add_desc:"):
            task_id = int(callback_data.split(":")[1])
            await self._handle_attachment_add_desc(query, context, task_id)
        elif callback_data.startswith("attachment_bulk_remove:"):
            task_id = int(callback_data.split(":")[1])
            await self._handle_attachment_bulk_remove(query, context, task_id)
        elif callback_data.startswith("attachment_export:"):
            task_id = int(callback_data.split(":")[1])
            await self._handle_attachment_export(query, context, task_id)
        elif callback_data.startswith("attachment_add:"):
            task_id = int(callback_data.split(":")[1])
            await self._handle_attachment_add(query, context, task_id)
        else:
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Unknown attachment action",
                    "Please use the file attachment commands for now."
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_calendar_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar-related callback queries."""
        callback_data = query.data
        
        if callback_data == "calendar_today":
            await self._handle_calendar_today(query, context)
        elif callback_data == "calendar_week":
            await self._handle_calendar_week(query, context)
        elif callback_data == "calendar_month":
            await self._handle_calendar_month(query, context)
        elif callback_data == "calendar_upcoming":
            await self._handle_calendar_upcoming(query, context)
        elif callback_data == "calendar_sync":
            await self._handle_calendar_sync(query, context)
        elif callback_data == "calendar_settings":
            await self._handle_calendar_settings(query, context)
        elif callback_data == "calendar_refresh":
            await self._handle_calendar_refresh(query, context)
        else:
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Unknown calendar action",
                    "Please use the calendar commands for now."
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_filter_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle filter-related callback queries."""
        callback_data = query.data
        
        if callback_data == "filter_date_range":
            await self._handle_filter_date_range(query, context)
        elif callback_data == "filter_priority":
            await self._handle_filter_priority(query, context)
        elif callback_data == "filter_status":
            await self._handle_filter_status(query, context)
        elif callback_data == "filter_tags":
            await self._handle_filter_tags(query, context)
        elif callback_data == "filter_category":
            await self._handle_filter_category(query, context)
        elif callback_data == "filter_time":
            await self._handle_filter_time(query, context)
        elif callback_data == "filter_advanced_search":
            await self._handle_filter_advanced_search(query, context)
        elif callback_data == "filter_save":
            await self._handle_filter_save(query, context)
        else:
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Unknown filter action",
                    "Please use the filter commands for now."
                ),
                parse_mode='MarkdownV2'
            )

    # Bulk operations handlers
    async def _handle_bulk_status_update(self, query, context: ContextTypes.DEFAULT_TYPE, status: str) -> None:
        """Handle bulk status update operations."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                f"🔄 Bulk Status Update: {status}",
                {
                    "Status": status,
                    "Instructions": "To use bulk status updates:",
                    "Command": f"/bulk_status <task_ids> {status}",
                    "Example": f"/bulk_status 1,2,3 {status}",
                    "Note": "Select tasks first, then apply the status change"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_bulk_priority_update(self, query, context: ContextTypes.DEFAULT_TYPE, priority: str) -> None:
        """Handle bulk priority update operations."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                f"🎯 Bulk Priority Update: {priority}",
                {
                    "Priority": priority,
                    "Instructions": "To use bulk priority updates:",
                    "Command": f"/bulk_priority <task_ids> {priority}",
                    "Example": f"/bulk_priority 1,2,3 {priority}",
                    "Note": "Select tasks first, then apply the priority change"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_bulk_operations_back(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle back navigation from bulk operations."""
        from larrybot.utils.ux_helpers import KeyboardBuilder
        
        await safe_edit(query.edit_message_text, 
            "📋 **Bulk Operations**\n\nSelect an operation:",
            reply_markup=KeyboardBuilder.build_bulk_operations_keyboard(),
            parse_mode='MarkdownV2'
        )

    # Stub handlers for individual features - following existing patterns
    async def _handle_reminder_add(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reminder add action."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "⏰ Add Reminder",
                {"Action": "Feature coming soon - use /addreminder command for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_reminder_stats(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reminder stats action."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📊 Reminder Statistics",
                {"Action": "Feature coming soon - use /reminders command for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_reminder_refresh(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reminder refresh action."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "🔄 Refresh Reminders",
                {"Action": "Feature coming soon - use /reminders command for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_reminder_dismiss(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reminder dismiss action."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_success_message(
                "❌ Reminder Dismissed",
                {"Action": "Notification dismissed successfully"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_reminder_snooze(self, query, context: ContextTypes.DEFAULT_TYPE, reminder_id: int, duration: str) -> None:
        """Handle reminder snooze action."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                f"⏰ Snooze Reminder ({duration})",
                {
                    "Reminder ID": reminder_id,
                    "Duration": duration,
                    "Action": "Feature coming soon - use /reminders command for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_reminder_delete(self, query, context: ContextTypes.DEFAULT_TYPE, reminder_id: int) -> None:
        """Handle reminder delete action."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "🗑️ Delete Reminder",
                {
                    "Reminder ID": reminder_id,
                    "Action": "Feature coming soon - use /delreminder command for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_reminder_complete(self, query, context: ContextTypes.DEFAULT_TYPE, reminder_id: int) -> None:
        """Handle reminder complete action."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "✅ Complete Reminder",
                {
                    "Reminder ID": reminder_id,
                    "Action": "Feature coming soon - use /reminders command for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_reminder_edit(self, query, context: ContextTypes.DEFAULT_TYPE, reminder_id: int) -> None:
        """Handle reminder edit action."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📝 Edit Reminder",
                {
                    "Reminder ID": reminder_id,
                    "Action": "Feature coming soon - use /reminders command for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_reminder_reactivate(self, query, context: ContextTypes.DEFAULT_TYPE, reminder_id: int) -> None:
        """Handle reminder reactivate action."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "🔄 Reactivate Reminder",
                {
                    "Reminder ID": reminder_id,
                    "Action": "Feature coming soon - use /reminders command for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    # Attachment stub handlers
    async def _handle_attachment_edit_desc(self, query, context: ContextTypes.DEFAULT_TYPE, attachment_id: int) -> None:
        """Handle attachment description edit."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📝 Edit Attachment Description",
                {
                    "Attachment ID": attachment_id,
                    "Action": "Feature coming soon - use attachment commands for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_attachment_details(self, query, context: ContextTypes.DEFAULT_TYPE, attachment_id: int) -> None:
        """Handle attachment details view."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📊 Attachment Details",
                {
                    "Attachment ID": attachment_id,
                    "Action": "Feature coming soon - use attachment commands for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_attachment_remove(self, query, context: ContextTypes.DEFAULT_TYPE, attachment_id: int) -> None:
        """Handle attachment removal."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "🗑️ Remove Attachment",
                {
                    "Attachment ID": attachment_id,
                    "Action": "Feature coming soon - use attachment commands for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_attachment_stats(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle attachment statistics."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📊 Attachment Statistics",
                {
                    "Task ID": task_id,
                    "Action": "Feature coming soon - use attachment commands for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_attachment_add_desc(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle attachment description addition."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📝 Add Attachment Description",
                {
                    "Task ID": task_id,
                    "Action": "Feature coming soon - use attachment commands for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_attachment_bulk_remove(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle bulk attachment removal."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "🗑️ Bulk Remove Attachments",
                {
                    "Task ID": task_id,
                    "Action": "Feature coming soon - use attachment commands for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_attachment_export(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle attachment export."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📋 Export Attachments",
                {
                    "Task ID": task_id,
                    "Action": "Feature coming soon - use attachment commands for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_attachment_add(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle attachment addition."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📎 Add Attachment",
                {
                    "Task ID": task_id,
                    "Action": "Feature coming soon - use attachment commands for now"
                }
            ),
            parse_mode='MarkdownV2'
        )

    # Calendar stub handlers
    async def _handle_calendar_today(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar today view."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📅 Today's Calendar",
                {"Action": "Feature coming soon - use calendar commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_calendar_week(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar week view."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📅 Week Calendar",
                {"Action": "Feature coming soon - use calendar commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_calendar_month(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar month view."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📅 Month Calendar",
                {"Action": "Feature coming soon - use calendar commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_calendar_upcoming(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar upcoming view."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📅 Upcoming Events",
                {"Action": "Feature coming soon - use calendar commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_calendar_sync(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar sync."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "🔄 Sync Calendar",
                {"Action": "Feature coming soon - use calendar commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_calendar_settings(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar settings."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "⚙️ Calendar Settings",
                {"Action": "Feature coming soon - use calendar commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_calendar_refresh(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar refresh - re-run agenda handler to get fresh data."""
        try:
            # Import the agenda handler from calendar plugin
            from larrybot.plugins.calendar import agenda_handler
            
            # Create a mock update object with the query's message
            mock_update = type('MockUpdate', (), {
                'message': query.message,
                'effective_user': query.from_user
            })()
            
            # Re-run the agenda handler to get fresh data
            await agenda_handler(mock_update, context)
            
        except Exception as e:
            logger.error(f"Error refreshing calendar: {e}")
            await safe_edit(query.edit_message_text, 
                MessageFormatter.format_error_message(
                    "Failed to refresh calendar",
                    "Please try again or use /agenda command."
                ),
                parse_mode='MarkdownV2'
            )

    # Filter stub handlers
    async def _handle_filter_date_range(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle date range filter."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📅 Date Range Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_priority(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle priority filter."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "🎯 Priority Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_status(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle status filter."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📋 Status Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_tags(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle tags filter."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "🏷️ Tags Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_category(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle category filter."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "📂 Category Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_time(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle time tracking filter."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "⏰ Time Tracking Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_advanced_search(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle advanced search filter."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "🔍 Advanced Search",
                {"Action": "Feature coming soon - use search commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_save(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle save filter."""
        await safe_edit(query.edit_message_text, 
            MessageFormatter.format_info_message(
                "💾 Save Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _global_error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all uncaught exceptions to prevent bot crashes with enhanced error recovery."""
        logger.error(f"Exception while handling update: {context.error}")
        
        # If update has a message, try to inform user with enhanced error handling
        if update and hasattr(update, 'effective_message') and update.effective_message:
            try:
                # Create error context for enhanced UX
                error_context = {
                    'current_context': 'error',
                    'error_type': 'system_error',
                    'navigation_path': ['Error Recovery'],
                    'available_actions': [
                        {'text': '🔄 Retry', 'callback_data': 'retry_action', 'type': 'primary'},
                        {'text': '🏠 Main Menu', 'callback_data': 'nav_main', 'type': 'navigation'},
                        {'text': '❓ Help', 'callback_data': 'show_help', 'type': 'secondary'}
                    ]
                }
                
                # Use enhanced error response
                error_message, recovery_keyboard = self.enhanced_message_processor.create_error_response(
                    'system_error',
                    "⚠️ System temporarily unavailable. Please try again in a moment.",
                    error_context
                )
                
                await update.effective_message.reply_text(
                    error_message,
                    reply_markup=recovery_keyboard,
                    parse_mode='MarkdownV2'
                )
            except Exception as e:
                logger.error(f"Failed to send enhanced error message to user: {e}")
                # Fallback to basic error message
                try:
                    await update.effective_message.reply_text(
                        MessageFormatter.format_error_message(
                            "⚠️ System temporarily unavailable",
                            "Please try again in a moment\\. If the issue persists, check your network connection\\."
                        ),
                        parse_mode='MarkdownV2'
                    )
                except Exception as fallback_e:
                    logger.error(f"Failed to send fallback error message: {fallback_e}")
                    # Don't let error handling cause more errors 

    async def _send_daily_report(self, update=None, context=None, chat_id=None):
        """Send a comprehensive daily report with tasks, habits, and motivational content."""
        logger.info("Generating daily report")
        try:
            # Get today's date
            today = get_current_datetime().date()
            start_of_today = datetime.combine(today, datetime.min.time())
            end_of_today = datetime.combine(today, datetime.max.time())
            
            # Fetch tasks
            with next(get_session()) as session:
                task_repository = TaskRepository(session)
                task_service = TaskService(task_repository)
                overdue_result = await task_service.get_tasks_with_filters(overdue_only=True)
                due_today_result = await task_service.get_tasks_with_filters(due_after=start_of_today, due_before=end_of_today)
                overdue_tasks = overdue_result['data'] if overdue_result['success'] else []
                due_today_tasks = due_today_result['data'] if due_today_result['success'] else []
                
                # Fetch habits
                habit_repo = HabitRepository(session)
                habits = habit_repo.list_habits()
                habits_due = []
                for habit in habits:
                    last_completed = habit.last_completed.date() if habit.last_completed else None
                    if last_completed != today:
                        habits_due.append(habit)
            
            # Fetch calendar events
            from larrybot.services.calendar_service import CalendarService
            calendar_service = CalendarService()
            calendar_events = await calendar_service.get_todays_events()
            
            # Format calendar events for display
            events = []
            for event in calendar_events:
                formatted_event = calendar_service.format_event_for_daily_report(event)
                events.append((
                    formatted_event["time"],
                    formatted_event["name"],
                    formatted_event["duration"]
                ))
            
            # Motivational quotes
            quotes = [
                "Well begun is half done.",
                "Success is the sum of small efforts repeated day in and day out.",
                "The secret of getting ahead is getting started.",
                "You don't have to be great to start, but you have to start to be great.",
                "Discipline is the bridge between goals and accomplishment."
            ]
            quote = random.choice(quotes)
            
            # Format message
            lines = []
            lines.append(f"🗓️ **Daily Report – {today.strftime('%A, %b %d')}**\n")
            # Events
            lines.append("📅 **Today's Calendar Events:**")
            if events:
                for time, name, duration in events:
                    lines.append(f"- {time} — {name}{duration}")
            else:
                lines.append("- _No calendar events scheduled._")
            lines.append("")
            # Overdue tasks
            lines.append("🚨 **Overdue Tasks:**")
            if overdue_tasks:
                for t in overdue_tasks[:5]:
                    client = f" _(Client: {t.get('client_name')})_" if t.get('client_name') else ""
                    lines.append(f"- ❗ {t['description']}{client}")
                if len(overdue_tasks) > 5:
                    lines.append(f"- ...and {len(overdue_tasks) - 5} more overdue tasks")
            else:
                lines.append("- _No overdue tasks!_")
            lines.append("")
            # Due today
            lines.append("📅 **Due Today:**")
            if due_today_tasks:
                for t in due_today_tasks[:5]:
                    client = f" _(Client: {t.get('client_name')})_" if t.get('client_name') else ""
                    lines.append(f"- {t['description']}{client}")
                if len(due_today_tasks) > 5:
                    lines.append(f"- ...and {len(due_today_tasks) - 5} more due today")
            else:
                lines.append("- _No tasks due today!_")
            lines.append("")
            # Habits
            lines.append("🔄 **Habits Due Today:**")
            if habits_due:
                for h in habits_due:
                    streak = f" — 🔥 Streak: {h.streak} days" if h.streak > 1 else ""
                    lines.append(f"- {h.name}{streak}")
            else:
                lines.append("- _No habits due today!_")
            lines.append("")
            # Quote
            lines.append(f"💡 _\"{quote}\"_")
            message = "\n".join(lines)
            logger.info("Daily report generated successfully")
            
            # Send message
            if update:
                await update.message.reply_text(message, parse_mode='Markdown')
            elif context and chat_id:
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            else:
                logger.error("No valid message target provided for daily report")
                
        except Exception as e:
            logger.error(f"Exception in _send_daily_report: {e}")
            raise  # Re-raise to be handled by calling method

    async def daily_command(self, update, context):
        """Handle /daily command to send daily report."""
        logger.info("Daily command invoked by user")
        
        # Check authorization
        if not self._is_authorized(update):
            await update.message.reply_text("🚫 Unauthorized access.")
            return
        
        try:
            await self._send_daily_report(update, context)
        except Exception as e:
            logger.error(f"Error in daily command: {e}")
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Failed to generate daily report",
                    "Please try again later."
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_narrative_task_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        print(f"[DEBUG] Received callback: {query.data}, state={context.user_data.get('task_creation_state')}")
        try:
            if 'task_creation_state' not in context.user_data:
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_error_message(
                        "No active task creation session",
                        "Use /addtask to start creating a task."
                    ),
                    parse_mode='MarkdownV2'
                )
                return
            # Parse callback data
            parts = query.data.split(":")
            # Need at least addtask_step:<action>
            if len(parts) < 2:
                return

            step_type = parts[1]
            # Some actions (e.g., confirm/edit/cancel) don't have a value segment
            step_value = ":".join(parts[2:]) if len(parts) > 2 else ""
            from larrybot.plugins.tasks import (
                _handle_description_step, _handle_due_date_step, _handle_priority_step,
                _handle_category_step, _handle_client_step, _handle_confirmation_step
            )
            from larrybot.nlp.enhanced_narrative_processor import TaskCreationState
            current_state = context.user_data['task_creation_state']
            # Add some debugging
            logger.info(f"Narrative callback: step_type={step_type}, current_state={current_state}, step_value={step_value}")
            print(f"[DEBUG] step_type={step_type!r}, current_state={current_state!r}")
            if step_type == "due_date" and current_state == TaskCreationState.AWAITING_DUE_DATE.value:
                await _handle_due_date_step(query, context, step_value)
            elif step_type == "priority" and current_state == TaskCreationState.AWAITING_PRIORITY.value:
                await _handle_priority_step(query, context, step_value)
            elif step_type == "category" and current_state == TaskCreationState.AWAITING_CATEGORY.value:
                await _handle_category_step(query, context, step_value)
            elif step_type == "client" and current_state == TaskCreationState.AWAITING_CLIENT.value:
                await _handle_client_step(query, context, step_value)
            elif step_type in ["confirm", "edit", "cancel"] and current_state == TaskCreationState.CONFIRMATION.value:
                await _handle_confirmation_step(query, context, step_type)
            else:
                logger.warning(f"Invalid narrative step: step_type={step_type}, current_state={current_state}")
                await safe_edit(query.edit_message_text, 
                    MessageFormatter.format_error_message(
                        "Invalid step in task creation flow",
                        "Please use /addtask to start over."
                    ),
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            print(f"[DEBUG] Exception in _handle_narrative_task_callback: {e}")
            import traceback
            traceback.print_exc()