from telegram import Update
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.core.events import ReminderDueEvent
from larrybot.storage.db import get_session
from larrybot.storage.reminder_repository import ReminderRepository
from larrybot.storage.task_repository import TaskRepository
from larrybot.utils.ux_helpers import KeyboardBuilder, MessageFormatter
from datetime import datetime, timedelta
import asyncio
import logging
import threading
from queue import Queue
import weakref

class ReminderEventHandler:
    """Handles reminder events by sending messages to the user."""
    
    def __init__(self, bot_application, user_id: int):
        self.bot_application = bot_application
        self.user_id = user_id
        self._loop = None
        # Thread-safe queue for cross-thread event delivery
        self._event_queue = Queue()
        self._processing_task = None
    
    def set_event_loop(self, loop):
        """Set the event loop for async operations and start event processing."""
        self._loop = loop
        if loop and loop.is_running():
            # Start the event processing task using the task manager for proper lifecycle
            try:
                from larrybot.core.task_manager import get_task_manager
                task_manager = get_task_manager()
                self._processing_task = task_manager.create_task(
                    self._process_events(),
                    name="reminder_event_processor"
                )
                logging.getLogger(__name__).info("Reminder event processor registered with task manager")
            except (ImportError, RuntimeError) as e:
                # Fallback for when task manager not available or no running event loop
                logging.getLogger(__name__).warning(f"Task manager or event loop not available: {e}")
                if hasattr(asyncio, 'get_running_loop'):
                    try:
                        # Only create task if there's actually a running loop
                        asyncio.get_running_loop()
                        self._processing_task = asyncio.create_task(self._process_events())
                        logging.getLogger(__name__).info("Reminder event processor created directly")
                    except RuntimeError:
                        # No running event loop - this is expected in test environments
                        logging.getLogger(__name__).debug("No running event loop - skipping task creation")
                        # Don't create the coroutine if there's no loop to run it
                        return
    
    async def _process_events(self):
        """Process events from the thread-safe queue."""
        logger = logging.getLogger(__name__)
        logger.info("Reminder event processor started")
        
        while True:
            try:
                # Check for events in queue (non-blocking)
                try:
                    event = self._event_queue.get_nowait()
                    await self.handle_reminder_due(event)
                    self._event_queue.task_done()
                except Exception as queue_empty:
                    # No events in queue, wait a bit
                    await asyncio.sleep(1.0)
                    continue
                    
            except asyncio.CancelledError:
                logger.info("Reminder event processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in reminder event processor: {e}")
                await asyncio.sleep(1.0)  # Brief pause on error
    
    def queue_reminder_event(self, event: ReminderDueEvent):
        """
        Thread-safe method to queue a reminder event for processing.
        This is called from the scheduler thread.
        """
        try:
            self._event_queue.put_nowait(event)
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to queue reminder event: {e}")
    
    async def handle_reminder_due(self, event: ReminderDueEvent) -> None:
        """Handle a reminder due event by sending a message to the user."""
        try:
            # Enhanced reminder message with rich formatting
            message_text = (
                f"⏰ **Reminder Due!**\n\n"
                f"📋 **Task**: {event.task_description}\n"
                f"🕐 **Scheduled**: {event.remind_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"⏰ **Due**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                f"💡 *Don't forget to complete this task!*"
            )
            
            # Create action keyboard for the reminder
            keyboard = KeyboardBuilder.build_reminder_action_keyboard(event.task_id, event.reminder_id)
            
            # Send message using the bot application
            await self.bot_application.bot.send_message(
                chat_id=self.user_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
            
            logging.info(f"Enhanced reminder sent successfully for task: {event.task_description}")
            print(f"Enhanced reminder sent successfully for task: {event.task_description}", flush=True)
            
        except Exception as e:
            logging.error(f"Failed to send reminder message: {e}")
            print(f"Failed to send reminder message: {e}", flush=True)
    
    async def cleanup(self):
        """Clean up the reminder event handler."""
        if hasattr(self, '_processing_task') and self._processing_task:
            try:
                if not self._processing_task.done():
                    self._processing_task.cancel()
                    try:
                        await self._processing_task
                    except asyncio.CancelledError:
                        logging.getLogger(__name__).info("Reminder event processor cancelled")
                    except Exception as e:
                        logging.getLogger(__name__).warning(f"Error during reminder processor cleanup: {e}")
            except Exception as e:
                logging.getLogger(__name__).warning(f"Error cancelling reminder processor: {e}")

# Global references for registration
_reminder_event_handler = None
_main_loop = None

def register(event_bus: EventBus, command_registry: CommandRegistry) -> None:
    """Register reminder commands and event handlers with enhanced UX."""
    command_registry.register("/addreminder", add_reminder_handler)
    command_registry.register("/reminders", list_reminders_handler)
    command_registry.register("/delreminder", delete_reminder_handler)
    command_registry.register("/reminder_quick", quick_reminder_handler)
    command_registry.register("/reminder_stats", reminder_stats_handler)

def register_event_handler(bot_application, user_id: int) -> None:
    """Register the reminder event handler with the event bus."""
    global _reminder_event_handler
    _reminder_event_handler = ReminderEventHandler(bot_application, user_id)

def set_main_event_loop(loop):
    """Set the main event loop for the reminder handler."""
    global _main_loop
    _main_loop = loop
    if _reminder_event_handler:
        _reminder_event_handler.set_event_loop(loop)

async def cleanup_reminder_handler():
    """Clean up the global reminder event handler."""
    global _reminder_event_handler
    if _reminder_event_handler:
        try:
            await _reminder_event_handler.cleanup()
            logging.getLogger(__name__).info("Reminder event handler cleanup completed")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error during reminder handler cleanup: {e}")

def subscribe_to_events(event_bus: EventBus) -> None:
    """Subscribe to reminder events using thread-safe queue mechanism."""
    if _reminder_event_handler:
        def event_wrapper(event: ReminderDueEvent):
            """
            Thread-safe wrapper to handle async reminder events from scheduler thread.
            Uses a queue instead of run_coroutine_threadsafe to avoid cross-loop issues.
            """
            try:
                # Queue the event for processing in the main loop
                _reminder_event_handler.queue_reminder_event(event)
                logging.info("Reminder event queued successfully")
            except Exception as e:
                logging.error(f"Failed to queue reminder event: {e}")
                print(f"Failed to queue reminder event: {e}", flush=True)
        
        event_bus.subscribe("reminder_due", event_wrapper)
        logging.info("Reminder event handler subscribed to reminder_due events (thread-safe)")

async def add_reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a reminder with enhanced UX."""
    if len(context.args) < 2 or not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid arguments",
                "Usage: /addreminder <task_id> <YYYY-MM-DD HH:MM>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    try:
        remind_at = datetime.strptime(" ".join(context.args[1:]), "%Y-%m-%d %H:%M")
        
        # Check if reminder time is in the past
        if remind_at <= datetime.now():
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Reminder time is in the past",
                    "Please set a future date and time for the reminder"
                ),
                parse_mode='MarkdownV2'
            )
            return
            
    except ValueError:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid date/time format",
                "Use format: YYYY-MM-DD HH:MM\nExample: 2024-01-15 14:30"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    with next(get_session()) as session:
        task_repo = TaskRepository(session)
        task = task_repo.get_task_by_id(task_id)
        
        if not task:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"Task ID {task_id} not found",
                    "Check the task ID or use /tasks to see available tasks"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        repo = ReminderRepository(session)
        reminder = repo.add_reminder(task_id, remind_at)
        
        # Calculate time until reminder
        time_until = remind_at - datetime.now()
        hours_until = int(time_until.total_seconds() // 3600)
        minutes_until = int((time_until.total_seconds() % 3600) // 60)
        
        time_text = ""
        if hours_until > 0:
            time_text += f"{hours_until} hours "
        if minutes_until > 0:
            time_text += f"{minutes_until} minutes"
        
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"Reminder set successfully!",
                {
                    "Task ID": task_id,
                    "Task": task.description,
                    "Reminder Time": remind_at.strftime("%Y-%m-%d %H:%M"),
                    "Time Until": time_text.strip(),
                    "Reminder ID": reminder.id
                }
            ),
            parse_mode='MarkdownV2'
        )

async def quick_reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a quick reminder with relative time (e.g., 30m, 2h, 1d)."""
    if len(context.args) < 2 or not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid arguments",
                "Usage: /reminder_quick <task_id> <time>\nExamples:\n• /reminder_quick 123 30m (30 minutes)\n• /reminder_quick 123 2h (2 hours)\n• /reminder_quick 123 1d (1 day)"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    time_str = context.args[1].lower()
    
    # Parse relative time
    try:
        if time_str.endswith('m'):
            minutes = int(time_str[:-1])
            remind_at = datetime.now() + timedelta(minutes=minutes)
        elif time_str.endswith('h'):
            hours = int(time_str[:-1])
            remind_at = datetime.now() + timedelta(hours=hours)
        elif time_str.endswith('d'):
            days = int(time_str[:-1])
            remind_at = datetime.now() + timedelta(days=days)
        else:
            # Try to parse as minutes if no suffix
            minutes = int(time_str)
            remind_at = datetime.now() + timedelta(minutes=minutes)
    except ValueError:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid time format",
                "Use format: <number><unit>\nUnits: m (minutes), h (hours), d (days)\nExample: 30m, 2h, 1d"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    with next(get_session()) as session:
        task_repo = TaskRepository(session)
        task = task_repo.get_task_by_id(task_id)
        
        if not task:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"Task ID {task_id} not found",
                    "Check the task ID or use /tasks to see available tasks"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        repo = ReminderRepository(session)
        reminder = repo.add_reminder(task_id, remind_at)
        
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"Quick reminder set!",
                {
                    "Task ID": task_id,
                    "Task": task.description,
                    "Reminder Time": remind_at.strftime("%Y-%m-%d %H:%M"),
                    "Time Until": time_str,
                    "Reminder ID": reminder.id
                }
            ),
            parse_mode='MarkdownV2'
        )

async def list_reminders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all reminders with enhanced formatting and inline keyboards."""
    with next(get_session()) as session:
        repo = ReminderRepository(session)
        reminders = repo.list_reminders()
        
        if not reminders:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "No reminders found",
                    "Use /addreminder to create your first reminder"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Sort reminders by time
        reminders.sort(key=lambda r: r.remind_at)
        
        # Format reminder list with rich formatting
        message = f"⏰ **All Reminders** \\({len(reminders)} active\\)\n\n"
        
        now = datetime.now()
        
        for i, reminder in enumerate(reminders, 1):
            # Get task details
            task_repo = TaskRepository(session)
            task = task_repo.get_task_by_id(reminder.task_id)
            task_description = task.description if task else f"Task {reminder.task_id}"
            
            # Calculate time until reminder
            time_until = reminder.remind_at - now
            
            if time_until.total_seconds() <= 0:
                status_emoji = "🔴"  # Overdue
                status_text = "Overdue"
            elif time_until.total_seconds() <= 3600:  # 1 hour
                status_emoji = "🟠"  # Due soon
                status_text = "Due soon"
            elif time_until.total_seconds() <= 86400:  # 1 day
                status_emoji = "🟡"  # Due today
                status_text = "Due today"
            else:
                status_emoji = "🟢"  # Future
                status_text = "Future"
            
            # Format time until
            if time_until.total_seconds() <= 0:
                time_text = "Overdue"
            else:
                hours = int(time_until.total_seconds() // 3600)
                minutes = int((time_until.total_seconds() % 3600) // 60)
                if hours > 24:
                    days = hours // 24
                    hours = hours % 24
                    time_text = f"{days}d {hours}h"
                elif hours > 0:
                    time_text = f"{hours}h {minutes}m"
                else:
                    time_text = f"{minutes}m"
            
            message += f"{i}\\. {status_emoji} **{MessageFormatter.escape_markdown(task_description)}**\n"
            message += f"   🕐 {reminder.remind_at.strftime('%Y-%m-%d %H:%M')}\n"
            message += f"   ⏰ {time_text} \\({status_text}\\)\n"
            message += f"   📋 Task ID: {reminder.task_id}\n"
            message += f"   🆔 Reminder ID: {reminder.id}\n\n"
        
        # Create navigation keyboard for reminder actions
        keyboard = KeyboardBuilder.build_reminder_list_keyboard()
        
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )

async def delete_reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a reminder with confirmation dialog."""
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid reminder ID",
                "Usage: /delreminder <reminder_id>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    reminder_id = int(context.args[0])
    
    with next(get_session()) as session:
        repo = ReminderRepository(session)
        reminder = repo.get_reminder_by_id(reminder_id)
        
        if not reminder:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"Reminder ID {reminder_id} not found",
                    "Check the reminder ID or use /reminders to see available reminders"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Get task details for confirmation
        task_repo = TaskRepository(session)
        task = task_repo.get_task_by_id(reminder.task_id)
        task_description = task.description if task else f"Task {reminder.task_id}"
        
        # Show confirmation dialog with inline keyboard
        keyboard = KeyboardBuilder.build_confirmation_keyboard("reminder_delete", reminder_id)
        
        await update.message.reply_text(
            f"🗑️ **Confirm Reminder Deletion**\n\n"
            f"**Task**: {MessageFormatter.escape_markdown(task_description)}\n"
            f"**Reminder Time**: {reminder.remind_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"**Reminder ID**: {reminder.id}\n\n"
            f"Are you sure you want to delete this reminder?",
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )

async def reminder_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show reminder statistics and insights."""
    with next(get_session()) as session:
        repo = ReminderRepository(session)
        reminders = repo.list_reminders()
        
        if not reminders:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "No reminders to analyze",
                    "Add some reminders first with /addreminder"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Calculate statistics
        total_reminders = len(reminders)
        now = datetime.now()
        
        overdue = sum(1 for r in reminders if r.remind_at <= now)
        due_soon = sum(1 for r in reminders if 0 < (r.remind_at - now).total_seconds() <= 3600)  # 1 hour
        due_today = sum(1 for r in reminders if 3600 < (r.remind_at - now).total_seconds() <= 86400)  # 1 day
        future = sum(1 for r in reminders if (r.remind_at - now).total_seconds() > 86400)
        
        # Find next reminder
        future_reminders = [r for r in reminders if r.remind_at > now]
        next_reminder = min(future_reminders, key=lambda r: r.remind_at) if future_reminders else None
        
        message = f"📊 **Reminder Statistics**\n\n"
        
        message += f"📈 **Overview**\n"
        message += f"• Total Reminders: {total_reminders}\n"
        message += f"• Overdue: {overdue} 🔴\n"
        message += f"• Due Soon (≤1h): {due_soon} 🟠\n"
        message += f"• Due Today: {due_today} 🟡\n"
        message += f"• Future: {future} 🟢\n\n"
        
        if next_reminder:
            task_repo = TaskRepository(session)
            task = task_repo.get_task_by_id(next_reminder.task_id)
            task_description = task.description if task else f"Task {next_reminder.task_id}"
            
            time_until = next_reminder.remind_at - now
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            
            message += f"⏰ **Next Reminder**\n"
            message += f"• Task: {MessageFormatter.escape_markdown(task_description)}\n"
            message += f"• Time: {next_reminder.remind_at.strftime('%Y-%m-%d %H:%M')}\n"
            message += f"• In: {hours}h {minutes}m\n\n"
        
        # Insights
        message += f"💡 **Insights**\n"
        
        if overdue > 0:
            message += f"• ⚠️ **{overdue} overdue reminders** - Consider reviewing them\n"
        
        if due_soon > 0:
            message += f"• 🚨 **{due_soon} reminders due soon** - Check your schedule\n"
        
        if total_reminders > 10:
            message += f"• 📋 **Many active reminders** - Consider consolidating\n"
        elif total_reminders == 0:
            message += f"• 📝 **No reminders set** - Use reminders to stay on track\n"
        
        await update.message.reply_text(
            message,
            parse_mode='MarkdownV2'
        ) 