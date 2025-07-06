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
logger = logging.getLogger(__name__)
_thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='scheduler'
    )


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
        loop = asyncio.get_event_loop()
        coro = bot_handler._send_daily_report(chat_id=chat_id, context=None)
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
        else:
            loop.run_until_complete(coro)
    job_id = f'daily_report_{chat_id}'
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    scheduler.add_job(send_report_job, 'cron', hour=hour, minute=minute, id
        =job_id, replace_existing=True)
    logger.info(
        f'Scheduled daily report for chat_id {chat_id} at {hour:02d}:{minute:02d}'
        )
