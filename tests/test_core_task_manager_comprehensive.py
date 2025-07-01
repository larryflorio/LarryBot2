"""
Comprehensive TaskManager Testing Suite

This test suite validates the actual TaskManager component functionality,
focusing on real methods and proper async context handling.
"""

import pytest
import asyncio
import signal
import time
from unittest.mock import Mock, patch, AsyncMock

from larrybot.core.task_manager import (
    TaskManager, 
    get_task_manager, 
    create_managed_task,
    shutdown_all_tasks,
    managed_task_context
)


class TestTaskManagerCore:
    """Test core TaskManager functionality with proper async context."""

    @pytest.mark.asyncio
    async def test_task_manager_initialization(self):
        """Test TaskManager initializes correctly within async context."""
        task_manager = TaskManager(shutdown_timeout=2.0)
        
        assert task_manager._shutdown_timeout == 2.0
        assert len(task_manager._tasks) == 0
        assert not task_manager._shutdown_event.is_set()
        assert not task_manager._running
        assert len(task_manager._cleanup_callbacks) == 0

    @pytest.mark.asyncio
    async def test_create_and_track_task(self):
        """Test creating and tracking tasks."""
        task_manager = TaskManager()
        
        async def sample_task():
            await asyncio.sleep(0.01)
            return "completed"

        task = task_manager.create_task(sample_task(), name="test_task")
        
        # Task should be tracked
        assert task in task_manager._tasks
        assert len(task_manager._tasks) == 1
        
        # Wait for completion
        result = await task
        assert result == "completed"
        
        # Allow callback to execute
        await asyncio.sleep(0.01)
        
        # Task should be automatically removed from tracking
        assert task not in task_manager._tasks

    @pytest.mark.asyncio
    async def test_task_exception_handling(self):
        """Test that task exceptions are logged but don't crash manager."""
        task_manager = TaskManager()
        
        async def failing_task():
            raise ValueError("Task failed")

        task = task_manager.create_task(failing_task(), name="failing_task")
        
        with pytest.raises(ValueError):
            await task
        
        await asyncio.sleep(0.01)  # Allow callback to execute
        assert task not in task_manager._tasks

    @pytest.mark.asyncio
    async def test_cleanup_callbacks(self):
        """Test cleanup callback functionality."""
        task_manager = TaskManager()
        task_manager._running = True  # Set running state for shutdown to execute callbacks
        callback_executed = []
        
        def cleanup_callback():
            callback_executed.append(True)
        
        task_manager.add_cleanup_callback(cleanup_callback)
        assert len(task_manager._cleanup_callbacks) == 1
        
        # Cleanup callbacks are called during shutdown
        await task_manager.shutdown()
        assert len(callback_executed) == 1

    @pytest.mark.asyncio
    async def test_shutdown_property(self):
        """Test shutdown requested property."""
        task_manager = TaskManager()
        
        assert not task_manager.is_shutdown_requested
        task_manager._shutdown_event.set()
        assert task_manager.is_shutdown_requested

    @pytest.mark.asyncio
    async def test_task_stats(self):
        """Test task statistics functionality."""
        task_manager = TaskManager()
        
        async def sample_task():
            await asyncio.sleep(0.1)
        
        # Create tasks
        task1 = task_manager.create_task(sample_task(), name="task1")
        task2 = task_manager.create_task(sample_task(), name="task2")
        
        stats = task_manager.get_task_stats()
        assert stats["total_tasks"] == 2
        assert stats["running_tasks"] >= 0  # May vary by timing
        assert not stats["is_running"]  # Background services not started
        assert not stats["shutdown_requested"]
        
        # Cleanup
        task1.cancel()
        task2.cancel()
        try:
            await asyncio.gather(task1, task2, return_exceptions=True)
        except:
            pass


class TestTaskManagerBackgroundServices:
    """Test background services functionality."""

    @pytest.mark.asyncio
    async def test_start_background_services_test_mode(self):
        """Test starting background services in test mode."""
        task_manager = TaskManager()
        
        with patch('larrybot.utils.background_processing.start_background_processing') as mock_start_bg, \
             patch('larrybot.utils.caching.cache_cleanup_task') as mock_cache_cleanup, \
             patch('larrybot.utils.background_processing.background_cleanup_task') as mock_bg_cleanup:
            
            mock_start_bg.return_value = None
            
            await task_manager.start_background_services(test_mode=True)
            
            assert task_manager._running
            mock_start_bg.assert_called_once()
            
            # Should have created periodic tasks
            assert len(task_manager._tasks) >= 2  # Cache and background cleanup

    @pytest.mark.asyncio
    async def test_duplicate_background_service_start(self):
        """Test that starting services twice doesn't duplicate."""
        task_manager = TaskManager()
        
        with patch('larrybot.utils.background_processing.start_background_processing') as mock_start_bg:
            mock_start_bg.return_value = None
            
            await task_manager.start_background_services(test_mode=True)
            initial_task_count = len(task_manager._tasks)
            
            await task_manager.start_background_services(test_mode=True)
            
            # Should not create duplicate tasks
            assert len(task_manager._tasks) == initial_task_count

    @pytest.mark.asyncio
    async def test_background_service_failure(self):
        """Test handling of background service startup failure."""
        task_manager = TaskManager()
        
        with patch('larrybot.utils.background_processing.start_background_processing') as mock_start_bg:
            mock_start_bg.side_effect = Exception("Background processing failed")
            
            with pytest.raises(Exception, match="Background processing failed"):
                await task_manager.start_background_services(test_mode=True)
            
            assert not task_manager._running


class TestTaskManagerShutdown:
    """Test shutdown functionality."""

    @pytest.mark.asyncio
    async def test_shutdown_with_no_tasks(self):
        """Test shutdown when no tasks are running."""
        task_manager = TaskManager()
        task_manager._running = True  # Simulate started state
        
        await task_manager.shutdown()
        
        assert task_manager.is_shutdown_requested
        assert not task_manager._running

    @pytest.mark.asyncio
    async def test_shutdown_with_quick_tasks(self):
        """Test shutdown waits for quick tasks to complete."""
        task_manager = TaskManager()
        task_manager._running = True
        task_completed = []
        
        async def quick_task():
            await asyncio.sleep(0.1)
            task_completed.append(True)
            return "completed"
        
        # Start a task
        task = task_manager.create_task(quick_task(), name="quick_task")
        
        # Shutdown should wait for task completion
        await task_manager.shutdown()
        
        # Task should have completed
        assert len(task_completed) == 1
        assert task_manager.is_shutdown_requested

    @pytest.mark.asyncio
    async def test_shutdown_timeout_handling(self):
        """Test shutdown timeout behavior with very short timeout."""
        task_manager = TaskManager(shutdown_timeout=0.05)  # Very short timeout
        task_manager._running = True
        
        async def slow_task():
            await asyncio.sleep(1.0)  # Longer than timeout
            return "should_timeout"
        
        task = task_manager.create_task(slow_task(), name="slow_task")
        
        # Shutdown should timeout and cancel tasks
        start_time = time.time()
        await task_manager.shutdown()
        shutdown_duration = time.time() - start_time
        
        # Should not wait the full task duration
        assert shutdown_duration < 0.5
        assert task_manager.is_shutdown_requested


class TestTaskManagerSignalHandling:
    """Test signal handling functionality with proper async context."""

    @pytest.mark.asyncio
    async def test_signal_handler_setup(self):
        """Test signal handlers are set up during initialization."""
        with patch('signal.signal') as mock_signal:
            task_manager = TaskManager()
            
            # Should register SIGTERM and SIGINT handlers
            assert mock_signal.call_count == 2
            signal_calls = [call[0][0] for call in mock_signal.call_args_list]
            assert signal.SIGTERM in signal_calls
            assert signal.SIGINT in signal_calls

    @pytest.mark.asyncio
    async def test_signal_handler_setup_failure(self):
        """Test graceful handling when signal setup fails."""
        with patch('signal.signal', side_effect=ValueError("Signal setup failed")):
            # Should not raise exception
            task_manager = TaskManager()
            assert task_manager is not None

    @pytest.mark.asyncio
    async def test_signal_handler_sets_shutdown_event(self):
        """Test signal handler sets shutdown event."""
        task_manager = TaskManager()
        
        # Simulate signal handler call
        task_manager._signal_handler(signal.SIGTERM, None)
        
        assert task_manager._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_signal_handler_duplicate_signals(self):
        """Test signal handler handles duplicate signals gracefully."""
        task_manager = TaskManager()
        
        # First signal
        task_manager._signal_handler(signal.SIGTERM, None)
        assert task_manager._shutdown_event.is_set()
        
        # Second signal should not cause issues
        task_manager._signal_handler(signal.SIGINT, None)
        assert task_manager._shutdown_event.is_set()


class TestTaskManagerGlobalFunctions:
    """Test global task manager functions with proper async context."""

    @pytest.mark.asyncio
    async def test_get_task_manager_singleton(self):
        """Test get_task_manager returns consistent instance."""
        # Reset global state
        import larrybot.core.task_manager
        larrybot.core.task_manager._global_task_manager = None
        
        manager1 = get_task_manager()
        manager2 = get_task_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, TaskManager)

    @pytest.mark.asyncio
    async def test_create_managed_task(self):
        """Test create_managed_task uses global manager."""
        # Reset global state
        import larrybot.core.task_manager
        larrybot.core.task_manager._global_task_manager = None
        
        async def test_task():
            return "global_task_completed"
        
        task = create_managed_task(test_task(), name="global_test")
        result = await task
        
        assert result == "global_task_completed"

    @pytest.mark.asyncio
    async def test_shutdown_all_tasks(self):
        """Test shutdown_all_tasks shuts down global manager."""
        # Reset global state
        import larrybot.core.task_manager
        larrybot.core.task_manager._global_task_manager = None
        
        # Create a task using global manager
        async def test_task():
            await asyncio.sleep(0.1)
            return "completed"
        
        # Force start background services to set _running = True
        manager = get_task_manager()
        manager._running = True
        
        create_managed_task(test_task(), name="test_shutdown")
        
        # Shutdown all tasks
        await shutdown_all_tasks()
        
        # Global manager should be shutdown
        assert manager.is_shutdown_requested


class TestManagedTaskContext:
    """Test managed_task_context functionality."""

    @pytest.mark.asyncio
    async def test_managed_task_context_test_mode(self):
        """Test managed_task_context in test mode."""
        # Reset global state to avoid event loop conflicts
        import larrybot.core.task_manager
        larrybot.core.task_manager._global_task_manager = None
        
        tasks_created = []
        
        with patch('larrybot.utils.background_processing.start_background_processing'), \
             patch('larrybot.utils.caching.cache_cleanup_task'), \
             patch('larrybot.utils.background_processing.background_cleanup_task'):
            
            async with managed_task_context(test_mode=True) as task_manager:
                assert isinstance(task_manager, TaskManager)
                assert task_manager._running
                
                # Create a task within the context
                async def test_task():
                    tasks_created.append("task_executed")
                    return "completed"
                
                task = task_manager.create_task(test_task(), name="context_task")
                await task
        
        # Task should have executed
        assert "task_executed" in tasks_created
        # Manager should be shutdown after context exit
        assert task_manager.is_shutdown_requested

    @pytest.mark.asyncio
    async def test_managed_task_context_exception_handling(self):
        """Test managed_task_context handles exceptions and still shuts down."""
        # Reset global state
        import larrybot.core.task_manager
        larrybot.core.task_manager._global_task_manager = None
        
        task_manager_ref = None
        
        with patch('larrybot.utils.background_processing.start_background_processing'), \
             patch('larrybot.utils.caching.cache_cleanup_task'), \
             patch('larrybot.utils.background_processing.background_cleanup_task'):
            
            try:
                async with managed_task_context(test_mode=True) as task_manager:
                    task_manager_ref = task_manager
                    raise ValueError("Context exception")
            except ValueError:
                pass
        
        # Manager should still be shutdown despite exception
        assert task_manager_ref.is_shutdown_requested


class TestTaskManagerRealWorld:
    """Test real-world usage patterns."""

    @pytest.mark.asyncio
    async def test_concurrent_task_creation(self):
        """Test creating multiple tasks concurrently."""
        task_manager = TaskManager()
        
        async def numbered_task(number):
            await asyncio.sleep(0.01)
            return f"task_{number}"
        
        # Create multiple tasks
        tasks = []
        for i in range(5):
            task = task_manager.create_task(numbered_task(i), name=f"task_{i}")
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        expected_results = [f"task_{i}" for i in range(5)]
        assert results == expected_results

    @pytest.mark.asyncio
    async def test_mixed_success_failure_tasks(self):
        """Test handling mixed successful and failing tasks."""
        task_manager = TaskManager()
        
        async def success_task():
            return "success"
        
        async def failure_task():
            raise ValueError("failure")
        
        success_task_obj = task_manager.create_task(success_task(), name="success")
        failure_task_obj = task_manager.create_task(failure_task(), name="failure")
        
        # Gather with return_exceptions to handle failures
        results = await asyncio.gather(success_task_obj, failure_task_obj, return_exceptions=True)
        
        assert results[0] == "success"
        assert isinstance(results[1], ValueError)
        
        # Both tasks should be removed from tracking
        await asyncio.sleep(0.01)
        assert len(task_manager._tasks) == 0

    @pytest.mark.asyncio
    async def test_performance_many_tasks(self):
        """Test performance with many short tasks."""
        task_manager = TaskManager()
        
        async def quick_task(task_id):
            return task_id
        
        # Create many tasks
        tasks = []
        start_time = time.time()
        for i in range(100):
            task = task_manager.create_task(quick_task(i), name=f"perf_task_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Should complete quickly
        assert end_time - start_time < 2.0
        assert len(results) == 100
        assert results == list(range(100)) 