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
        
        self._register_core_handlers()
        self._register_core_commands()
        
        # NLP pipeline initialization
        self.intent_recognizer = IntentRecognizer()
        self.entity_extractor = EntityExtractor()
        self.sentiment_analyzer = SentimentAnalyzer()
        
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
        for command in self.command_registry._commands:
            if command not in ("/start", "/help"):
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
                await query.edit_message_text(
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
                await query.edit_message_text(
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
                await query.edit_message_text(
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
        else:
            # Unknown callback data
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    "Unknown action",
                    "This button action is not implemented yet."
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_task_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle task-related callback queries."""
        callback_data = query.data
        
        if callback_data.startswith("task_done:"):
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
        
        await query.edit_message_text(
            "📋 **Task Management**\n\nSelect an option:",
            reply_markup=NavigationHelper.get_task_menu_keyboard(),
            parse_mode='MarkdownV2'
        )

    async def _show_client_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show client management menu."""
        await query.edit_message_text(
            "👥 **Client Management**\n\nUse commands:\n• /allclients - List all clients\n• /addclient - Add new client\n• /client - View client details",
            parse_mode='MarkdownV2'
        )

    async def _show_habit_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show habit management menu."""
        await query.edit_message_text(
            "🔄 **Habit Management**\n\nUse commands:\n• /habit_list - List all habits\n• /habit_add - Add new habit\n• /habit_done - Mark habit complete",
            parse_mode='MarkdownV2'
        )

    async def _show_reminder_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show reminder management menu."""
        await query.edit_message_text(
            "⏰ **Reminder Management**\n\nUse commands:\n• /reminders - List all reminders\n• /addreminder - Add new reminder\n• /delreminder - Delete reminder",
            parse_mode='MarkdownV2'
        )

    async def _show_analytics_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show analytics menu."""
        await query.edit_message_text(
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
        
        await query.edit_message_text(
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
        
        await query.edit_message_text(
            "🎯 **Bulk Priority Update**\n\nSelect the new priority for your tasks:",
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )

    async def _show_bulk_assign_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bulk assign menu."""
        await query.edit_message_text(
            "👥 **Bulk Assignment**\n\nUse the command:\n`/bulk_assign <task_ids> <client_name>`\n\nExample: `/bulk_assign 1,2,3 John Doe`",
            parse_mode='MarkdownV2'
        )

    async def _show_bulk_delete_menu(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bulk delete menu."""
        await query.edit_message_text(
            "🗑️ **Bulk Delete**\n\nUse the command:\n`/bulk_delete <task_ids> [confirm]`\n\nExample: `/bulk_delete 1,2,3 confirm`",
            parse_mode='MarkdownV2'
        )

    async def _show_bulk_preview(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bulk operations preview."""
        await query.edit_message_text(
            "📊 **Bulk Operations Preview**\n\nThis feature will show a preview of tasks before applying bulk operations.",
            parse_mode='MarkdownV2'
        )

    async def _save_bulk_selection(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Save bulk selection."""
        await query.edit_message_text(
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
                await query.edit_message_text(
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
                await query.edit_message_text(
                    MessageFormatter.format_error_message(
                        result['message'],
                        "Please check the task IDs and try again."
                    ),
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    "Error during bulk delete",
                    str(e)
                ),
                parse_mode='MarkdownV2'
            )

    async def _cancel_bulk_delete(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Cancel bulk delete operation."""
        await query.edit_message_text(
            "❌ **Bulk Delete Cancelled**\n\nNo tasks were deleted.",
            parse_mode='MarkdownV2'
        )

    async def _handle_navigation_back(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle back navigation."""
        # For now, just show a simple message
        await query.edit_message_text(
            "⬅️ **Back Navigation**\n\nUse commands or the main menu to navigate.",
            parse_mode='MarkdownV2'
        )

    async def _handle_navigation_main(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle main menu navigation."""
        from larrybot.utils.ux_helpers import NavigationHelper
        
        await query.edit_message_text(
            "🏠 **Main Menu**\n\nSelect an option:",
            reply_markup=NavigationHelper.get_main_menu_keyboard(),
            parse_mode='MarkdownV2'
        )

    async def _handle_cancel_action(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle action cancellation."""
        await query.edit_message_text(
            "❌ **Action Cancelled**\n\nNo changes were made.",
            parse_mode='MarkdownV2'
        )

    async def _handle_task_done(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle task completion via callback with timeout protection and loading indicator."""
        try:
            # Show immediate loading feedback
            await query.edit_message_text(
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
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    "⏱️ Operation Timeout",
                    "Task completion took too long. Please check if it was completed and try again if needed."
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error completing task {task_id}: {e}")
            await query.edit_message_text(
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
                await query.edit_message_text(
                    MessageFormatter.format_error_message(
                        f"Task ID {task_id} not found",
                        "This task may have been deleted or the ID is invalid."
                    ),
                    parse_mode='Markdown'
                )
                return
            
            if task.done:
                await query.edit_message_text(
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
                
                await query.edit_message_text(
                    MessageFormatter.format_success_message(
                        "✅ Task Completed!",
                        {
                            "Task": completed_task.description,
                            "Status": "Completed",
                            "Message": "🎉 Great work! Keep up the momentum!"
                        }
                    ),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
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
                    await query.edit_message_text(
                        MessageFormatter.format_error_message(
                            f"Task ID {task_id} not found",
                            "The task may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                if task.done:
                    await query.edit_message_text(
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
                
                await query.edit_message_text(
                    f"✏️ **Edit Task**\n\n"
                    f"**Current**: {MessageFormatter.escape_markdown(task.description)}\n"
                    f"**ID**: {task_id}\n\n"
                    f"Please reply with the new description for this task\\.",
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            logger.error(f"Error starting task edit for task {task_id}: {e}")
            await query.edit_message_text(
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
        
        await query.edit_message_text(
            "❌ **Edit Cancelled**\n\nTask editing was cancelled. No changes were made.",
            parse_mode='MarkdownV2'
        )

    async def _handle_task_delete(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Handle task deletion via callback."""
        from larrybot.utils.ux_helpers import KeyboardBuilder
        
        await query.edit_message_text(
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
                    
                    await query.edit_message_text(
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
                    await query.edit_message_text(
                        MessageFormatter.format_error_message(
                            f"Task ID {task_id} not found",
                            "The task may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
        except Exception as e:
            await query.edit_message_text(
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
                    await query.edit_message_text(
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
                
                await query.edit_message_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            logger.error(f"Error showing client tasks for {client_id}: {e}")
            await query.edit_message_text(
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
                    await query.edit_message_text(
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
                await query.edit_message_text(
                    message,
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            logger.error(f"Error showing client analytics for {client_id}: {e}")
            await query.edit_message_text(
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
                    await query.edit_message_text(
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
                await query.edit_message_text(
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
            await query.edit_message_text(
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
                    await query.edit_message_text(
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
                await query.edit_message_text(
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
            await query.edit_message_text(
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
                    await query.edit_message_text(
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
                    await query.edit_message_text(
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
                
                await query.edit_message_text(
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
            await query.edit_message_text(
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
                    await query.edit_message_text(
                        MessageFormatter.format_error_message(
                            f"Habit #{habit_id} not found",
                            "The habit may have been deleted."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                # Calculate progress metrics
                today = datetime.now().date()
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
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    "Failed to load habit progress",
                    f"Error: {str(e)}"
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_habit_delete(self, query, context: ContextTypes.DEFAULT_TYPE, habit_id: int) -> None:
        """Handle habit deletion."""
        from larrybot.utils.ux_helpers import KeyboardBuilder
        
        await query.edit_message_text(
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
                    
                    await query.edit_message_text(
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
                    await query.edit_message_text(
                        MessageFormatter.format_error_message(
                            f"Habit #{habit_id} not found",
                            "The habit may have already been deleted."
                        ),
                        parse_mode='MarkdownV2'
                    )
        except Exception as e:
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    "Failed to delete habit",
                    f"Error: {str(e)}"
                ),
                parse_mode='MarkdownV2'
            )

    async def _handle_habit_add(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle habit add button click."""
        from larrybot.utils.ux_helpers import MessageFormatter
        
        await query.edit_message_text(
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
                    await query.edit_message_text(
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
                today = datetime.now().date()
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
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            await query.edit_message_text(
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
                    await query.edit_message_text(
                        MessageFormatter.format_error_message(
                            "No habits found",
                            "Use /habit_add to create your first habit"
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                # Calculate today's date for streak calculations
                today = datetime.now().date()
                
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
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            await query.edit_message_text(
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
        await update.message.reply_text(
            f"🎉 **Welcome to LarryBot2!**\n\n"
            f"✅ **Authorized User**: {user_info['authorized_user_id']}\n"
            f"🤖 **Bot Status**: {'Connected' if user_info['bot_token_configured'] else 'Not Configured'}\n"
            f"📊 **Rate Limit**: {user_info['rate_limit_per_minute']} commands/minute\n\n"
            f"Use `/help` to see available commands."
        )

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
            await update.message.reply_text(help_text, parse_mode='MarkdownV2')
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
        """Handle text messages for task editing and NLP-driven commands."""
        user_message = update.message.text.strip() if update.message and update.message.text else None
        if not user_message:
            return

        # --- NLP Processing (additive, non-breaking) ---
        nlp_intent = self.intent_recognizer.recognize_intent(user_message)
        nlp_entities = self.entity_extractor.extract_entities(user_message)
        nlp_sentiment = self.sentiment_analyzer.analyze_sentiment(user_message)
        context.user_data['nlp_intent'] = nlp_intent
        context.user_data['nlp_entities'] = nlp_entities
        context.user_data['nlp_sentiment'] = nlp_sentiment
        # ------------------------------------------------

        # --- NLP-driven routing (future expansion) ---
        # If you want to route based on NLP intent/entities, add logic here.
        # For now, all legacy flows are preserved. Only log NLP results for debugging.
        # Example (disabled):
        # if nlp_intent == 'create_task' and 'task_name' in nlp_entities:
        #     # Route to task creation handler (future)
        #     pass
        # ------------------------------------------------

        # Existing logic: task editing mode
        if 'editing_task_id' in context.user_data:
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
        else:
            # Not in editing mode, ignore the message (future: NLP intent routing here)
            return

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
                                "Modified": datetime.now().strftime("%Y-%m-%d %H:%M")
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
            await query.edit_message_text("🔄 Refreshing tasks\\.\\.\\.", parse_mode='MarkdownV2')
            
            # Add timeout to prevent blocking during network/database issues
            await asyncio.wait_for(self._handle_tasks_refresh_operation(query, context), timeout=10.0)
                    
        except asyncio.TimeoutError:
            logger.error("Tasks refresh timeout")
            try:
                await query.edit_message_text(
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
                await query.edit_message_text(
                    MessageFormatter.format_error_message(
                        "❌ Refresh failed",
                        "Please try again later\\."
                    ),
                    parse_mode='MarkdownV2'
                )
            except Exception as nested_e:
                logger.error(f"Failed to send error message: {nested_e}")

    async def _handle_tasks_refresh_operation(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the actual tasks refresh operation with enhanced UX."""
        from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
        
        with next(get_session()) as session:
            repo = TaskRepository(session)
            tasks = repo.list_incomplete_tasks()
            
            # Create context for enhanced UX processing
            ux_context = {
                'current_context': 'tasks',
                'tasks': tasks,
                'navigation_path': ['Main Menu', 'Tasks'],
                'available_actions': [
                    {'text': '➕ Add Task', 'callback_data': 'add_task', 'type': 'primary'},
                    {'text': '🔄 Refresh', 'callback_data': 'tasks_refresh', 'type': 'primary'},
                    {'text': '🔍 Search', 'callback_data': 'tasks_search', 'type': 'secondary'},
                    {'text': '📊 Analytics', 'callback_data': 'tasks_analytics', 'type': 'secondary'},
                    {'text': '🏠 Main Menu', 'callback_data': 'nav_main', 'type': 'navigation'}
                ]
            }
            
            if not tasks:
                message = "📋 **All Tasks Complete\\!** 🎉\n\nNo incomplete tasks found\\."
                keyboard = KeyboardBuilder.build_add_task_keyboard()
            else:
                # Use enhanced message processing
                message, keyboard = await self.enhanced_message_processor.process_message(
                    MessageFormatter.format_task_list(tasks, title="📋 **Incomplete Tasks**"),
                    ux_context,
                    user_id=query.from_user.id if query.from_user else None
                )
            
            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )

    async def _handle_task_view(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
        """Show detailed view of a task with action buttons and back navigation."""
        from larrybot.storage.db import get_session
        from larrybot.storage.task_repository import TaskRepository
        from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
        
        try:
            with next(get_session()) as session:
                repo = TaskRepository(session)
                task = repo.get_task_by_id(task_id)
                if not task:
                    await query.edit_message_text(
                        MessageFormatter.format_error_message(
                            f"Task ID {task_id} not found",
                            "The task may have already been deleted or doesn't exist."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                # Build detailed message with enhanced UX
                details = {
                    "Task": task.description,
                    "ID": task.id,
                    "Status": getattr(task, 'status', 'Todo'),
                    "Priority": getattr(task, 'priority', 'Medium'),
                    "Due": getattr(task, 'due_date', None),
                    "Category": getattr(task, 'category', None),
                    "Tags": getattr(task, 'tags', None),
                    "Created": getattr(task, 'created_at', None)
                }
                # Remove None values
                details = {k: v for k, v in details.items() if v is not None}
                
                # Create context for enhanced UX processing
                ux_context = {
                    'current_context': 'task_view',
                    'task': task,
                    'entity_type': 'task',
                    'entity_id': task.id,
                    'navigation_path': ['Main Menu', 'Tasks', f'Task #{task.id}'],
                    'available_actions': [
                        {'text': '✅ Done', 'callback_data': f'task_done:{task.id}', 'type': 'primary'},
                        {'text': '✏️ Edit', 'callback_data': f'task_edit:{task.id}', 'type': 'secondary'},
                        {'text': '🗑️ Delete', 'callback_data': f'task_delete:{task.id}', 'type': 'secondary'},
                        {'text': '⬅️ Back to List', 'callback_data': 'tasks_refresh', 'type': 'navigation'}
                    ]
                }
                
                # Use enhanced message processing
                message, keyboard = await self.enhanced_message_processor.process_message(
                    MessageFormatter.format_success_message("Task Details", details),
                    ux_context,
                    user_id=query.from_user.id if query.from_user else None
                )
                await query.edit_message_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            logger.error(f"Error showing task view for {task_id}: {e}")
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    "Error showing task details",
                    "Please try again or use /list command."
                ),
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
                    await query.edit_message_text(
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
                await query.edit_message_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            logger.error(f"Error showing client view for {client_id}: {e}")
            await query.edit_message_text(
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
                    await query.edit_message_text(
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
                
                await query.edit_message_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
                
        except Exception as e:
            logger.error(f"Error showing client edit for {client_id}: {e}")
            await query.edit_message_text(
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
            await query.edit_message_text(
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
            await query.edit_message_text(
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
        else:
            await query.edit_message_text(
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
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    "Unknown filter action",
                    "Please use the filter commands for now."
                ),
                parse_mode='MarkdownV2'
            )

    # Bulk operations handlers
    async def _handle_bulk_status_update(self, query, context: ContextTypes.DEFAULT_TYPE, status: str) -> None:
        """Handle bulk status update operations."""
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        
        await query.edit_message_text(
            "📋 **Bulk Operations**\n\nSelect an operation:",
            reply_markup=KeyboardBuilder.build_bulk_operations_keyboard(),
            parse_mode='MarkdownV2'
        )

    # Stub handlers for individual features - following existing patterns
    async def _handle_reminder_add(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reminder add action."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "⏰ Add Reminder",
                {"Action": "Feature coming soon - use /addreminder command for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_reminder_stats(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reminder stats action."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "📊 Reminder Statistics",
                {"Action": "Feature coming soon - use /reminders command for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_reminder_refresh(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reminder refresh action."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "🔄 Refresh Reminders",
                {"Action": "Feature coming soon - use /reminders command for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_reminder_dismiss(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reminder dismiss action."""
        await query.edit_message_text(
            MessageFormatter.format_success_message(
                "❌ Reminder Dismissed",
                {"Action": "Notification dismissed successfully"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_reminder_snooze(self, query, context: ContextTypes.DEFAULT_TYPE, reminder_id: int, duration: str) -> None:
        """Handle reminder snooze action."""
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        await query.edit_message_text(
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
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "📅 Today's Calendar",
                {"Action": "Feature coming soon - use calendar commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_calendar_week(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar week view."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "📅 Week Calendar",
                {"Action": "Feature coming soon - use calendar commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_calendar_month(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar month view."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "📅 Month Calendar",
                {"Action": "Feature coming soon - use calendar commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_calendar_upcoming(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar upcoming view."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "📅 Upcoming Events",
                {"Action": "Feature coming soon - use calendar commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_calendar_sync(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar sync."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "🔄 Sync Calendar",
                {"Action": "Feature coming soon - use calendar commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_calendar_settings(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle calendar settings."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "⚙️ Calendar Settings",
                {"Action": "Feature coming soon - use calendar commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    # Filter stub handlers
    async def _handle_filter_date_range(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle date range filter."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "📅 Date Range Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_priority(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle priority filter."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "🎯 Priority Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_status(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle status filter."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "📋 Status Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_tags(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle tags filter."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "🏷️ Tags Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_category(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle category filter."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "📂 Category Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_time(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle time tracking filter."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "⏰ Time Tracking Filter",
                {"Action": "Feature coming soon - use filter commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_advanced_search(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle advanced search filter."""
        await query.edit_message_text(
            MessageFormatter.format_info_message(
                "🔍 Advanced Search",
                {"Action": "Feature coming soon - use search commands for now"}
            ),
            parse_mode='MarkdownV2'
        )

    async def _handle_filter_save(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle save filter."""
        await query.edit_message_text(
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