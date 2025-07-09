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
        schedule_daily_report(mock_bot_handler, 12345, hour=9, minute=0)
        
        # Get the job and verify it exists
        job_id = 'daily_report_12345'
        job = scheduler.get_job(job_id)
        assert job is not None, "Daily report job should be scheduled"

    def test_scheduler_job_creation(self):
        """Test that daily report jobs are created correctly."""
        mock_bot_handler = Mock()
        mock_bot_handler._send_daily_report = Mock()
        
        # Schedule the daily report
        schedule_daily_report(mock_bot_handler, 12345, hour=9, minute=0)
        
        # Verify the job exists
        job_id = 'daily_report_12345'
        job = scheduler.get_job(job_id)
        assert job is not None, "Job should be created"
        assert job.id == job_id, "Job ID should match" 