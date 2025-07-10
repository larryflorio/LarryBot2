import pytest
import asyncio
from unittest.mock import Mock, patch
from larrybot.scheduler import set_main_event_loop, schedule_daily_report, scheduler


class TestDailyReportScheduler:
    """Test daily report scheduler functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Start the scheduler if it's not running
        if not scheduler.running:
            scheduler.start()

    def teardown_method(self):
        """Clean up test environment."""
        # Remove any test jobs
        for job in scheduler.get_jobs():
            if 'daily_report_12345' in job.id:
                scheduler.remove_job(job.id)

    def test_set_main_event_loop(self):
        """Test that the main event loop can be set for the scheduler."""
        loop = asyncio.new_event_loop()
        set_main_event_loop(loop)
        # The function should complete without error
        assert True

    @patch('larrybot.scheduler._main_loop')
    @patch('larrybot.scheduler.asyncio.run_coroutine_threadsafe')
    def test_daily_report_job_execution(self, mock_run_coroutine, mock_main_loop):
        """Test that the daily report job can execute without event loop errors."""
        # Mock the main loop
        mock_main_loop.is_running.return_value = True
        
        # Create a mock bot handler
        mock_bot_handler = Mock()
        mock_bot_handler._send_daily_report = Mock()
        
        # Schedule the daily report
        schedule_daily_report(mock_bot_handler, 12345, hour=8, minute=30)
        
        # Get the job and verify it exists
        job_id = 'daily_report_12345'
        job = scheduler.get_job(job_id)
        assert job is not None, "Daily report job should be scheduled"

    def test_scheduler_job_creation(self):
        """Test that daily report jobs are created correctly."""
        mock_bot_handler = Mock()
        mock_bot_handler._send_daily_report = Mock()
        
        # Schedule the daily report
        schedule_daily_report(mock_bot_handler, 12345, hour=8, minute=30)
        
        # Verify the job exists
        job_id = 'daily_report_12345'
        job = scheduler.get_job(job_id)
        assert job is not None, "Job should be created"
        assert job.id == job_id, "Job ID should match"

    @pytest.mark.asyncio
    async def test_daily_report_sending_with_chat_id_only(self):
        """Test that daily report can be sent when only chat_id is provided (scheduled scenario)."""
        from larrybot.handlers.bot import TelegramBotHandler
        from larrybot.config.loader import Config
        from larrybot.core.command_registry import CommandRegistry
        
        # Create a mock config
        mock_config = Mock(spec=Config)
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        mock_config.ALLOWED_TELEGRAM_USER_ID = 12345
        
        # Create a mock command registry
        mock_registry = Mock(spec=CommandRegistry)
        
        # Create bot handler with mocked application
        bot_handler = TelegramBotHandler(mock_config, mock_registry)
        bot_handler.application = Mock()
        bot_handler.application.bot = Mock()
        
        # Track calls to send_message
        send_message_calls = []
        async def mock_send_message(*args, **kwargs):
            send_message_calls.append((args, kwargs))
            return Mock()
        bot_handler.application.bot.send_message = mock_send_message
        
        # Test the _send_daily_report method with only chat_id (no context)
        await bot_handler._send_daily_report(chat_id=12345, context=None)
        
        # Verify that send_message was called with the correct parameters
        assert len(send_message_calls) == 1, "send_message should be called exactly once"
        args, kwargs = send_message_calls[0]
        assert kwargs['chat_id'] == 12345
        assert 'Daily Report' in kwargs['text']
        assert kwargs['parse_mode'] == 'Markdown' 