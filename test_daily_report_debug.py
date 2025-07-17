#!/usr/bin/env python3
"""
Debug script to test daily report scheduling functionality.
This will help identify why the daily report at 8:30am might not be working.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from larrybot.config.loader import Config
from larrybot.core.command_registry import CommandRegistry
from larrybot.handlers.bot import TelegramBotHandler
from larrybot.scheduler import scheduler, set_main_event_loop, schedule_daily_report

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_daily_report_scheduling():
    """Test the daily report scheduling functionality."""
    logger.info("🔍 Testing daily report scheduling...")
    
    try:
        # Load configuration
        config = Config()
        logger.info(f"✅ Configuration loaded - User ID: {config.ALLOWED_TELEGRAM_USER_ID}")
        
        # Create command registry
        command_registry = CommandRegistry()
        logger.info("✅ Command registry created")
        
        # Create bot handler
        bot_handler = TelegramBotHandler(config, command_registry)
        logger.info("✅ Bot handler created")
        
        # Set up event loop
        loop = asyncio.get_running_loop()
        set_main_event_loop(loop)
        logger.info("✅ Event loop set for scheduler")
        
        # Check if scheduler is running
        logger.info(f"📊 Scheduler running: {scheduler.running}")
        logger.info(f"📊 Current jobs: {[job.id for job in scheduler.get_jobs()]}")
        
        # Start scheduler if not running
        if not scheduler.running:
            logger.info("🚀 Starting scheduler...")
            from larrybot.scheduler import start_scheduler
            start_scheduler()
            logger.info("✅ Scheduler started")
        
        # Schedule daily report for testing (1 minute from now)
        test_time = datetime.now() + timedelta(minutes=1)
        logger.info(f"⏰ Scheduling test daily report for: {test_time.strftime('%H:%M:%S')}")
        
        schedule_daily_report(
            bot_handler, 
            config.ALLOWED_TELEGRAM_USER_ID, 
            hour=test_time.hour, 
            minute=test_time.minute
        )
        
        # Check scheduled jobs
        job_id = f'daily_report_{config.ALLOWED_TELEGRAM_USER_ID}'
        job = scheduler.get_job(job_id)
        
        if job:
            logger.info(f"✅ Daily report job scheduled successfully")
            logger.info(f"📅 Job ID: {job.id}")
            logger.info(f"📅 Next run: {job.next_run_time}")
            logger.info(f"📅 Trigger: {job.trigger}")
        else:
            logger.error(f"❌ Failed to schedule daily report job")
        
        # List all jobs
        logger.info("📋 All scheduled jobs:")
        for job in scheduler.get_jobs():
            logger.info(f"   - {job.id}: {job.next_run_time} ({job.trigger})")
        
        # Test manual daily report
        logger.info("🧪 Testing manual daily report...")
        try:
            await bot_handler._send_daily_report(chat_id=config.ALLOWED_TELEGRAM_USER_ID, context=None)
            logger.info("✅ Manual daily report sent successfully")
        except Exception as e:
            logger.error(f"❌ Manual daily report failed: {e}")
        
        # Wait a bit to see if scheduled job runs
        logger.info("⏳ Waiting 2 minutes to see if scheduled job runs...")
        await asyncio.sleep(120)
        
        logger.info("✅ Test completed")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_daily_report_scheduling()) 