"""
Comprehensive test suite for the main module (larrybot.__main__)

Tests the main entry point, async_main startup sequence, logging setup,
and error handling scenarios.
"""

import pytest
import asyncio
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from contextlib import AsyncExitStack
import logging

from larrybot.__main__ import main, async_main, setup_enhanced_logging, startup_system_monitoring


class TestMain:
    """Test the main entry point function."""

    @patch('larrybot.__main__.async_main', new_callable=AsyncMock)
    @patch('larrybot.__main__.logging')
    def test_main_successful_startup(self, mock_logging, mock_async_main):
        """Test successful main function execution."""
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        
        main()
        
        mock_async_main.assert_called_once()
        mock_logger.info.assert_called_with("🏁 LarryBot2 main process terminated")

    @patch('larrybot.__main__.async_main', new_callable=AsyncMock)
    @patch('larrybot.__main__.logging')
    def test_main_config_validation_error(self, mock_logging, mock_async_main):
        """Test main handles configuration validation errors."""
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        
        mock_async_main.side_effect = ValueError("Invalid configuration")
        
        with pytest.raises(SystemExit):
            main()
        
        mock_logger.error.assert_called_with("❌ Application failed: Invalid configuration")

    @patch('larrybot.__main__.async_main', new_callable=AsyncMock)
    @patch('larrybot.__main__.logging')
    def test_main_database_init_error(self, mock_logging, mock_async_main):
        """Test main handles database initialization errors."""
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        
        mock_async_main.side_effect = Exception("Database connection failed")
        
        with pytest.raises(SystemExit):
            main()
        
        mock_logger.error.assert_called_with("❌ Application failed: Database connection failed")

    @patch('larrybot.__main__.async_main', new_callable=AsyncMock)
    @patch('larrybot.__main__.logging')
    def test_main_plugin_loading_error(self, mock_logging, mock_async_main):
        """Test main handles plugin loading errors."""
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        
        mock_async_main.side_effect = ImportError("Plugin not found")
        
        with pytest.raises(SystemExit):
            main()
        
        mock_logger.error.assert_called_with("❌ Application failed: Plugin not found")

    @patch('larrybot.__main__.async_main', new_callable=AsyncMock)
    @patch('larrybot.__main__.logging')
    def test_main_bot_handler_error(self, mock_logging, mock_async_main):
        """Test main handles bot handler initialization errors."""
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        
        mock_async_main.side_effect = Exception("Bot token invalid")
        
        with pytest.raises(SystemExit):
            main()
        
        mock_logger.error.assert_called_with("❌ Application failed: Bot token invalid")

    @patch('larrybot.__main__.async_main', new_callable=AsyncMock)
    @patch('larrybot.__main__.logging')
    def test_main_scheduler_error(self, mock_logging, mock_async_main):
        """Test main handles scheduler initialization errors."""
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        
        mock_async_main.side_effect = Exception("Scheduler startup failed")
        
        with pytest.raises(SystemExit):
            main()
        
        mock_logger.error.assert_called_with("❌ Application failed: Scheduler startup failed")

    @patch('larrybot.__main__.async_main', new_callable=AsyncMock)
    @patch('larrybot.__main__.logging')
    def test_main_bot_run_error(self, mock_logging, mock_async_main):
        """Test main handles bot runtime errors."""
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        
        mock_async_main.side_effect = Exception("Network connection lost")
        
        with pytest.raises(SystemExit):
            main()
        
        mock_logger.error.assert_called_with("❌ Application failed: Network connection lost")

    @patch('larrybot.__main__.async_main', new_callable=AsyncMock)
    @patch('larrybot.__main__.logging')
    def test_main_keyboard_interrupt(self, mock_logging, mock_async_main):
        """Test main handles keyboard interrupt gracefully."""
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        
        mock_async_main.side_effect = KeyboardInterrupt()
        
        main()
        
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("🛑 Received keyboard interrupt - shutting down" in msg for msg in info_calls)

    @patch('larrybot.__main__.async_main', new_callable=AsyncMock)
    def test_main_module_execution(self, mock_async_main):
        """Test main module can be executed directly."""
        # This tests that the if __name__ == "__main__" logic works
        # We just verify the main function exists and is callable
        assert callable(main)
        
        # Call main to verify it doesn't crash
        main()
        mock_async_main.assert_called_once()


class TestAsyncMainStartupSequence:
    """Test the async_main startup sequence with proper mocking."""

    @pytest.mark.asyncio
    async def test_async_main_complete_startup_sequence(self):
        """Test complete async_main startup sequence with all components."""
        
        # Create a proper async context manager mock
        mock_task_manager = MagicMock()
        # Create a proper awaitable task that will raise an exception to stop execution
        async def mock_bot_task():
            raise Exception("Bot task started - test complete")
        
        mock_task_manager.create_task.return_value = mock_bot_task()

        # Create an actual working async context manager
        class MockTaskContext:
            async def __aenter__(self):
                return mock_task_manager
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        # Use individual patches instead of patch.multiple
        with patch('larrybot.__main__.managed_task_context', return_value=MockTaskContext()), \
             patch('larrybot.__main__.startup_system_monitoring', new_callable=AsyncMock), \
             patch('larrybot.__main__.init_db'), \
             patch('larrybot.__main__.Config') as mock_config, \
             patch('larrybot.__main__.DependencyContainer'), \
             patch('larrybot.__main__.EventBus'), \
             patch('larrybot.__main__.CommandRegistry'), \
             patch('larrybot.__main__.PluginManager'), \
             patch('larrybot.__main__.HealthService'), \
             patch('larrybot.__main__.ServiceLocator'), \
             patch('larrybot.__main__.start_scheduler'), \
             patch('larrybot.__main__.TelegramBotHandler') as mock_bot_handler, \
             patch('larrybot.__main__.register_event_handler'), \
             patch('larrybot.__main__.subscribe_to_events'):
            
            # Setup config instance
            mock_config_instance = MagicMock()
            mock_config_instance.DATABASE_PATH = ":memory:"
            mock_config_instance.ALLOWED_TELEGRAM_USER_ID = 123456789
            mock_config.return_value = mock_config_instance
            
            # Setup bot handler with async run method
            mock_bot_handler_instance = MagicMock()
            mock_bot_handler_instance.run_async = AsyncMock()
            mock_bot_handler_instance.application = MagicMock()
            mock_bot_handler.return_value = mock_bot_handler_instance
            
            # Call async_main - expect it to fail when trying to await the mock task
            with pytest.raises(Exception, match="Bot task started - test complete"):
                await async_main()
            
            # Verify key initialization calls
            mock_config.assert_called_once()
            mock_task_manager.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_main_database_init_failure(self):
        """Test async_main handles database initialization failure."""
        
        # Create proper async context manager
        mock_task_manager = MagicMock()
        
        class MockTaskContext:
            async def __aenter__(self):
                return mock_task_manager
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        with patch('larrybot.__main__.managed_task_context', return_value=MockTaskContext()), \
             patch('larrybot.__main__.init_db', side_effect=Exception("Database init failed")):
            
            with pytest.raises(Exception, match="Database init failed"):
                await async_main()

    @pytest.mark.asyncio
    async def test_async_main_system_monitoring_failure(self):
        """Test async_main handles system monitoring startup failure."""
        
        # Create proper async context manager
        mock_task_manager = MagicMock()
        
        class MockTaskContext:
            async def __aenter__(self):
                return mock_task_manager
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        with patch('larrybot.__main__.managed_task_context', return_value=MockTaskContext()), \
             patch('larrybot.__main__.init_db'), \
             patch('larrybot.__main__.startup_system_monitoring', side_effect=Exception("System monitoring failed")):
            
            with pytest.raises(Exception, match="System monitoring failed"):
                await async_main()

    @pytest.mark.asyncio
    async def test_async_main_config_failure(self):
        """Test async_main handles configuration loading failure."""
        
        # Create proper async context manager
        mock_task_manager = MagicMock()
        
        class MockTaskContext:
            async def __aenter__(self):
                return mock_task_manager
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        with patch('larrybot.__main__.managed_task_context', return_value=MockTaskContext()), \
             patch('larrybot.__main__.init_db'), \
             patch('larrybot.__main__.startup_system_monitoring'), \
             patch('larrybot.__main__.Config', side_effect=Exception("Config loading failed")):
            
            with pytest.raises(Exception, match="Config loading failed"):
                await async_main()

    @pytest.mark.asyncio
    async def test_async_main_plugin_discovery_failure(self):
        """Test async_main handles plugin discovery failure."""
        
        # Create proper async context manager
        mock_task_manager = MagicMock()
        
        class MockTaskContext:
            async def __aenter__(self):
                return mock_task_manager
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        with patch('larrybot.__main__.managed_task_context', return_value=MockTaskContext()), \
             patch('larrybot.__main__.init_db'), \
             patch('larrybot.__main__.startup_system_monitoring', new_callable=AsyncMock), \
             patch('larrybot.__main__.Config'), \
             patch('larrybot.__main__.DependencyContainer'), \
             patch('larrybot.__main__.EventBus'), \
             patch('larrybot.__main__.CommandRegistry'), \
             patch('larrybot.__main__.PluginManager') as mock_plugin_manager:
            
            # Setup plugin manager to fail
            mock_plugin_instance = MagicMock()
            mock_plugin_instance.discover_and_load.side_effect = Exception("Plugin discovery failed")
            mock_plugin_manager.return_value = mock_plugin_instance
            
            with pytest.raises(Exception, match="Plugin discovery failed"):
                await async_main()

    @pytest.mark.asyncio 
    async def test_async_main_task_context_failure(self):
        """Test async_main handles task context initialization failure."""
        
        with patch('larrybot.__main__.managed_task_context', side_effect=Exception("Task context failed")):
            with pytest.raises(Exception, match="Task context failed"):
                await async_main()


class TestSetupEnhancedLogging:
    """Test the setup_enhanced_logging function."""

    def test_setup_enhanced_logging_configuration(self):
        """Test that enhanced logging is configured correctly."""
        
        # Call the actual function (don't mock it entirely)
        result_logger = setup_enhanced_logging()
        
        # Verify it returns a logger
        assert isinstance(result_logger, logging.Logger)
        
        # Verify the logger name is correct (full module name)
        assert result_logger.name == 'larrybot.__main__'
        
        # Verify root logger has handlers
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
        
        # Verify log level is set correctly
        assert root_logger.level == logging.INFO


class TestStartupSystemMonitoring:
    """Test the startup_system_monitoring function."""

    @pytest.mark.asyncio
    @patch('larrybot.__main__.cache_stats')
    @patch('larrybot.__main__.get_session_stats')
    @patch('larrybot.__main__.optimize_database')
    async def test_startup_system_monitoring_success(self, mock_optimize_db, mock_session_stats, mock_cache_stats):
        """Test successful system monitoring startup."""
        
        mock_cache_stats.return_value = {"total_size": 1024, "hits": 100}
        mock_session_stats.return_value = {"active_sessions": 5, "total_queries": 50}
        
        # Should not raise any exceptions
        await startup_system_monitoring()
        
        mock_cache_stats.assert_called_once()
        mock_session_stats.assert_called_once()
        mock_optimize_db.assert_called_once()

    @pytest.mark.asyncio
    @patch('larrybot.__main__.cache_stats', side_effect=Exception("Cache stats failed"))
    @patch('larrybot.__main__.get_session_stats')
    @patch('larrybot.__main__.optimize_database')
    async def test_startup_system_monitoring_cache_stats_failure(self, mock_optimize_db, mock_session_stats, mock_cache_stats):
        """Test system monitoring handles cache stats failure."""
        
        with pytest.raises(Exception, match="Cache stats failed"):
            await startup_system_monitoring()

    @pytest.mark.asyncio
    @patch('larrybot.__main__.cache_stats')
    @patch('larrybot.__main__.get_session_stats')
    @patch('larrybot.__main__.optimize_database', side_effect=Exception("Database optimization failed"))
    async def test_startup_system_monitoring_database_optimization_failure(self, mock_optimize_db, mock_session_stats, mock_cache_stats):
        """Test system monitoring handles database optimization failure."""
        
        mock_cache_stats.return_value = {}
        mock_session_stats.return_value = {}
        
        with pytest.raises(Exception, match="Database optimization failed"):
            await startup_system_monitoring()


class TestMainModuleIntegration:
    """Test integration aspects of the main module."""

    def test_main_function_exists_and_callable(self):
        """Test that main function exists and is callable."""
        assert callable(main)
        assert main.__name__ == "main"

    def test_async_main_function_exists_and_callable(self):
        """Test that async_main function exists and is callable."""
        assert callable(async_main)
        assert async_main.__name__ == "async_main"

    def test_setup_enhanced_logging_function_exists(self):
        """Test that setup_enhanced_logging function exists."""
        assert callable(setup_enhanced_logging)
        assert setup_enhanced_logging.__name__ == "setup_enhanced_logging"

    def test_startup_system_monitoring_function_exists(self):
        """Test that startup_system_monitoring function exists."""
        assert callable(startup_system_monitoring)
        assert startup_system_monitoring.__name__ == "startup_system_monitoring"

    def test_logging_setup_called_in_async_main(self):
        """Test that logging setup is called within async_main, not main."""
        # This tests the actual architecture where setup_enhanced_logging 
        # is called within async_main, not in main()
        
        # Create proper async context manager
        mock_task_manager = MagicMock()
        
        class MockTaskContext:
            async def __aenter__(self):
                return mock_task_manager
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        with patch('larrybot.__main__.setup_enhanced_logging') as mock_setup, \
             patch('larrybot.__main__.managed_task_context', return_value=MockTaskContext()), \
             patch('larrybot.__main__.init_db', side_effect=Exception("Stop early")):
            
            try:
                asyncio.run(async_main())
            except Exception:
                pass  # We expect it to fail, we just want to check logging setup
            
            mock_setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_module_imports_successfully(self):
        """Test that the module imports successfully."""
        # This is an integration test to ensure all imports work
        from larrybot.__main__ import main, async_main, setup_enhanced_logging, startup_system_monitoring
        
        assert callable(main)
        assert callable(async_main)
        assert callable(setup_enhanced_logging)
        assert callable(startup_system_monitoring) 