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
_main_loop = None  # Store reference to main event loop
logger = logging.getLogger(__name__)
_thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='scheduler'
    )


def set_main_event_loop(loop):
    """Set the main event loop for the scheduler."""
    global _main_loop
    _main_loop = loop
    logger.info('Main event loop set for scheduler')


def check_due_reminders():
    """Check for due reminders with enhanced error handling and performance."""
    try:
        _check_reminders_safe()
    except Exception as e:
        logger.error(f'Critical error in reminder check: {e}')


def _check_reminders_safe():
    """Safe reminder checking with proper error isolation."""
    start_time = time.time()
    now = get_current_datetime()
    try:
        with next(get_session()) as session:
            session.execute(text('PRAGMA busy_timeout = 3000'))
            repo = ReminderRepository(session)
            due_reminders = repo.list_due_reminders(now)
            if due_reminders:
                logger.info(f'Processing {len(due_reminders)} due reminders')
                _process_reminders_batch(session, due_reminders)
            session.commit()
    except Exception as e:
        logger.error(f'Database error in reminder check: {e}')
    finally:
        execution_time = time.time() - start_time
        if execution_time > 2.0:
            logger.warning(
                f'Reminder check took {execution_time:.2f}s - potential performance issue'
                )


def _process_reminders_batch(session, due_reminders):
    """Process reminders in batch with error isolation."""
    task_repo = TaskRepository(session)
    processed_reminder_ids = []
    for reminder in due_reminders:
        try:
            task = task_repo.get_task_by_id(reminder.task_id)
            desc = task.description if task else f'Task {reminder.task_id}'
            event = ReminderDueEvent(reminder_id=reminder.id, task_id=
                reminder.task_id, task_description=desc, remind_at=reminder
                .remind_at)
            if _event_bus:
                try:
                    _event_bus.emit('reminder_due', event)
                except Exception as e:
                    logger.error(
                        f'Event emission failed for reminder {reminder.id}: {e}'
                        )
            processed_reminder_ids.append(reminder.id)
        except Exception as e:
            logger.error(
                f'Error processing individual reminder {reminder.id}: {e}')
            continue
    if processed_reminder_ids:
        try:
            repo = ReminderRepository(session)
            deleted_count = repo.delete_multiple_reminders(
                processed_reminder_ids)
            logger.info(f'Cleaned up {deleted_count} processed reminders')
        except Exception as e:
            logger.error(f'Failed to cleanup reminders: {e}')


def start_scheduler(event_bus=None):
    """Start the scheduler with enhanced configuration for reliability."""
    global _event_bus
    _event_bus = event_bus
    if scheduler.get_job('reminder_checker'):
        scheduler.remove_job('reminder_checker')
    scheduler.add_job(check_due_reminders, 'interval', minutes=1, id=
        'reminder_checker', max_instances=1, coalesce=True,
        misfire_grace_time=15, replace_existing=True)
    logger.info(
        'Reminder scheduler started with enhanced reliability configuration')
    try:
        scheduler.start()
    except Exception as e:
        logger.error(f'Failed to start scheduler: {e}')
        raise


def schedule_daily_report(bot_handler, chat_id, hour=9, minute=0):
    """Schedule the daily report to be sent every day at the specified time (default 9am)."""

    def send_report_job():
        try:
            logger.info(f'🔄 Executing scheduled daily report for chat_id {chat_id}')
            
            # Use the stored main event loop instead of trying to get it from the scheduler thread
            if _main_loop is None:
                logger.error(f'❌ No main event loop available for daily report job for chat_id {chat_id}')
                return
                
            coro = bot_handler._send_daily_report(chat_id=chat_id, context=None)
            
            if _main_loop.is_running():
                # Submit to the main event loop if it's running
                asyncio.run_coroutine_threadsafe(coro, _main_loop)
                logger.info(f'✅ Daily report job submitted to event loop for chat_id {chat_id}')
            else:
                # This shouldn't happen in normal operation, but handle it gracefully
                logger.warning(f'⚠️ Main event loop not running for daily report job for chat_id {chat_id}')
                
        except Exception as e:
            logger.error(f'❌ Error in daily report job for chat_id {chat_id}: {e}')
    
    job_id = f'daily_report_{chat_id}'
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f'🔄 Replaced existing daily report job for chat_id {chat_id}')
    
    try:
        scheduler.add_job(send_report_job, 'cron', hour=hour, minute=minute, id
            =job_id, replace_existing=True, misfire_grace_time=300)
        logger.info(
            f'✅ Scheduled daily report for chat_id {chat_id} at {hour:02d}:{minute:02d}')
        
        # Log next run time for verification (only if scheduler is running)
        if scheduler.running:
            job = scheduler.get_job(job_id)
            if job and hasattr(job, 'next_run_time') and job.next_run_time:
                next_run = job.next_run_time
                logger.info(f'📅 Next daily report scheduled for: {next_run}')
            else:
                logger.info(f'📅 Daily report job created (next run time not available)')
        else:
            logger.info(f'📅 Daily report job created (scheduler not running)')
            
    except Exception as e:
        logger.error(f'❌ Failed to schedule daily report for chat_id {chat_id}: {e}')
        raise


def schedule_end_of_day_reminder(bot_handler, chat_id, hour=17, minute=0):
    """Schedule end-of-day reminder to be sent every day at the specified time (default 5pm)."""

    def send_eod_reminder_job():
        try:
            logger.info(f'🔄 Executing scheduled end-of-day reminder for chat_id {chat_id}')
            
            # Use the stored main event loop instead of trying to get it from the scheduler thread
            if _main_loop is None:
                logger.error(f'❌ No main event loop available for end-of-day reminder job for chat_id {chat_id}')
                return
                
            coro = bot_handler._send_end_of_day_reminder(chat_id=chat_id, context=None)
            
            if _main_loop.is_running():
                # Submit to the main event loop if it's running
                asyncio.run_coroutine_threadsafe(coro, _main_loop)
                logger.info(f'✅ End-of-day reminder job submitted to event loop for chat_id {chat_id}')
            else:
                # This shouldn't happen in normal operation, but handle it gracefully
                logger.warning(f'⚠️ Main event loop not running for end-of-day reminder job for chat_id {chat_id}')
                
        except Exception as e:
            logger.error(f'❌ Error in end-of-day reminder job for chat_id {chat_id}: {e}')
    
    job_id = f'end_of_day_reminder_{chat_id}'
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f'🔄 Replaced existing end-of-day reminder job for chat_id {chat_id}')
    
    try:
        scheduler.add_job(
            send_eod_reminder_job,
            'cron',
            hour=hour,
            minute=minute,
            id=job_id,
            replace_existing=True,
            misfire_grace_time=300
        )
        logger.info(
            f'✅ Scheduled end-of-day reminder for chat_id {chat_id} at {hour:02d}:{minute:02d}')
        
        # Log next run time for verification (only if scheduler is running)
        if scheduler.running:
            job = scheduler.get_job(job_id)
            if job and hasattr(job, 'next_run_time') and job.next_run_time:
                next_run = job.next_run_time
                logger.info(f'📅 Next end-of-day reminder scheduled for: {next_run}')
            else:
                logger.info(f'📅 End-of-day reminder job created (next run time not available)')
        else:
            logger.info(f'📅 End-of-day reminder job created (scheduler not running)')
            
    except Exception as e:
        logger.error(f'❌ Failed to schedule end-of-day reminder for chat_id {chat_id}: {e}')
        raise
