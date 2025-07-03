from apscheduler.schedulers.background import BackgroundScheduler
from larrybot.storage.db import get_session
from larrybot.storage.reminder_repository import ReminderRepository
from larrybot.storage.task_repository import TaskRepository
from larrybot.core.events import ReminderDueEvent
from datetime import datetime
from sqlalchemy import text
import logging
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from larrybot.utils.datetime_utils import get_current_datetime, get_current_utc_datetime

scheduler = BackgroundScheduler()
_event_bus = None

# Configure logging for scheduler
logger = logging.getLogger(__name__)

# Thread pool for database operations to prevent blocking
_thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="scheduler")


def check_due_reminders():
    """Check for due reminders with enhanced error handling and performance."""
    try:
        # Run the actual reminder check in a separate function with timeout
        _check_reminders_safe()
    except Exception as e:
        logger.error(f"Critical error in reminder check: {e}")
        # Never let scheduler errors crash the system - just log and continue


def _check_reminders_safe():
    """Safe reminder checking with proper error isolation."""
    start_time = time.time()
    now = get_current_datetime()
    
    try:
        # Use shorter-lived session with aggressive timeout
        with next(get_session()) as session:
            # Set aggressive timeout to prevent long locks during network issues
            session.execute(text("PRAGMA busy_timeout = 3000"))  # 3 seconds max wait
            
            repo = ReminderRepository(session)
            due_reminders = repo.list_due_reminders(now)
            
            # Only process if there are actually reminders (reduce noise)
            if due_reminders:
                logger.info(f"Processing {len(due_reminders)} due reminders")
                _process_reminders_batch(session, due_reminders)
            
            # Fast commit - don't hold locks
            session.commit()
            
    except Exception as e:
        logger.error(f"Database error in reminder check: {e}")
        # Continue - don't crash scheduler for DB issues
    
    finally:
        # Performance monitoring - only log if slow
        execution_time = time.time() - start_time
        if execution_time > 2.0:  # Only log if it took more than 2 seconds
            logger.warning(f"Reminder check took {execution_time:.2f}s - potential performance issue")


def _process_reminders_batch(session, due_reminders):
    """Process reminders in batch with error isolation."""
    task_repo = TaskRepository(session)
    processed_reminder_ids = []
    
    for reminder in due_reminders:
        try:
            # Get task info with minimal DB impact
            task = task_repo.get_task_by_id(reminder.task_id)
            desc = task.description if task else f"Task {reminder.task_id}"
            
            # Create and emit the reminder event (non-blocking)
            event = ReminderDueEvent(
                reminder_id=reminder.id,
                task_id=reminder.task_id,
                task_description=desc,
                remind_at=reminder.remind_at
            )
            
            # Emit event if available (don't block if event bus unavailable)
            if _event_bus:
                try:
                    _event_bus.emit("reminder_due", event)
                except Exception as e:
                    logger.error(f"Event emission failed for reminder {reminder.id}: {e}")
                    # Continue processing even if event emission fails
            
            # Track for cleanup regardless of event emission status
            processed_reminder_ids.append(reminder.id)
            
        except Exception as e:
            logger.error(f"Error processing individual reminder {reminder.id}: {e}")
            # Continue with other reminders even if one fails
            continue
    
    # Bulk cleanup processed reminders
    if processed_reminder_ids:
        try:
            repo = ReminderRepository(session)
            deleted_count = repo.delete_multiple_reminders(processed_reminder_ids)
            logger.info(f"Cleaned up {deleted_count} processed reminders")
        except Exception as e:
            logger.error(f"Failed to cleanup reminders: {e}")


def start_scheduler(event_bus=None):
    """Start the scheduler with enhanced configuration for reliability."""
    global _event_bus
    _event_bus = event_bus
    
    # Remove existing job to avoid conflicts
    if scheduler.get_job('reminder_checker'):
        scheduler.remove_job('reminder_checker')
    
    # Configure job with enhanced resilience settings
    scheduler.add_job(
        check_due_reminders, 
        'interval', 
        minutes=1, 
        id='reminder_checker',
        max_instances=1,      # Prevent overlapping executions
        coalesce=True,        # Combine missed executions into one
        misfire_grace_time=15, # Reduce grace time to 15 seconds
        replace_existing=True  # Replace if job already exists
    )
    
    logger.info("Reminder scheduler started with enhanced reliability configuration")
    
    try:
        scheduler.start()
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise 

def schedule_daily_report(bot_handler, chat_id, hour=9, minute=0):
    """Schedule the daily report to be sent every day at the specified time (default 9am)."""
    def send_report_job():
        # Run in event loop
        loop = asyncio.get_event_loop()
        coro = bot_handler._send_daily_report(chat_id=chat_id, context=None)
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
        else:
            loop.run_until_complete(coro)
    job_id = f"daily_report_{chat_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    scheduler.add_job(
        send_report_job,
        'cron',
        hour=hour,
        minute=minute,
        id=job_id,
        replace_existing=True
    )
    logger.info(f"Scheduled daily report for chat_id {chat_id} at {hour:02d}:{minute:02d}") 