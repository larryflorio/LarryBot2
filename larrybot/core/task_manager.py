"""
Centralized AsyncIO Task Manager for LarryBot2.

Provides unified task lifecycle management, graceful shutdown, and error handling
for all background tasks, worker processes, and cleanup routines.
"""

import asyncio
import logging
import signal
import weakref
from typing import Set, Optional, Callable, Any, Dict, List
from contextlib import asynccontextmanager
import time

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Centralized manager for all asyncio tasks with graceful shutdown and error handling.
    
    Features:
    - Automatic task tracking and cleanup
    - Graceful shutdown with timeout
    - Signal handling for proper termination
    - Error isolation and logging
    - Resource cleanup on exit
    """
    
    def __init__(self, shutdown_timeout: float = 5.0):
        self._tasks: Set[asyncio.Task] = set()
        self._shutdown_timeout = shutdown_timeout
        self._shutdown_event = asyncio.Event()
        self._running = False
        self._cleanup_callbacks: List[Callable[[], None]] = []
        self._weak_refs: Set[weakref.ReferenceType] = set()
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        logger.info("TaskManager initialized with graceful shutdown support")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        try:
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)
        except ValueError:
            # Signal setup may fail in some environments (e.g., threads)
            logger.debug("Could not setup signal handlers - running in thread context")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        if self._shutdown_event.is_set():
            logger.warning(f"Received signal {signum} - shutdown already in progress")
            return
            
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self._shutdown_event.set()
        
        # Schedule shutdown in the event loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._signal_shutdown())
        except RuntimeError:
            # No running event loop, shutdown will be handled elsewhere
            logger.debug("No running event loop for signal shutdown")
    
    async def _signal_shutdown(self):
        """Handle shutdown triggered by signal."""
        logger.info("Processing signal-triggered shutdown...")
        await self.shutdown()
        
        # Cancel the main task to trigger return from async_main
        try:
            # Find and cancel the main bot task
            current_task = asyncio.current_task()
            if current_task and current_task.get_name() != "signal_shutdown":
                logger.info("Cancelling main task to complete shutdown...")
                for task in self._tasks:
                    if not task.done() and task != current_task:
                        logger.debug(f"Cancelling task: {task.get_name()}")
                        task.cancel()
        except Exception as e:
            logger.error(f"Error during task cancellation: {e}")
    
    def create_task(self, coro, *, name: Optional[str] = None) -> asyncio.Task:
        """
        Create and track a new asyncio task with automatic cleanup.
        
        Args:
            coro: Coroutine to execute
            name: Optional task name for debugging
            
        Returns:
            The created task
        """
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        
        # Add done callback to remove from tracking
        task.add_done_callback(self._task_done_callback)
        
        logger.debug(f"Created task: {task.get_name() if hasattr(task, 'get_name') else 'unnamed'}")
        return task
    
    def _task_done_callback(self, task: asyncio.Task):
        """Callback when a task completes."""
        self._tasks.discard(task)
        
        # Log any unhandled exceptions
        if not task.cancelled():
            try:
                exception = task.exception()
                if exception:
                    logger.error(f"Task {getattr(task, 'get_name', lambda: 'unnamed')()} failed: {exception}")
            except asyncio.CancelledError:
                pass  # Task was cancelled, this is expected
            except Exception as e:
                logger.error(f"Error checking task exception: {e}")
    
    def add_cleanup_callback(self, callback: Callable[[], None]):
        """Add a cleanup callback to be called during shutdown."""
        self._cleanup_callbacks.append(callback)
    
    async def start_background_services(self, test_mode: bool = False):
        """Start essential background services."""
        # Prevent duplicate initialization
        if self._running:
            logger.debug("Background services already running, skipping duplicate start")
            return
            
        from larrybot.utils.background_processing import start_background_processing
        from larrybot.utils.caching import cache_cleanup_task
        from larrybot.utils.background_processing import background_cleanup_task
        
        # Use shorter intervals for testing
        cache_interval = 2.0 if test_mode else 300.0    # 2 seconds vs 5 minutes
        background_interval = 5.0 if test_mode else 1800.0  # 5 seconds vs 30 minutes
        
        try:
            # Start background processing system
            await start_background_processing()
            
            # Start cache cleanup task
            self.create_task(
                self._managed_periodic_task(
                    cache_cleanup_task, 
                    interval=cache_interval,
                    name="cache_cleanup"
                ),
                name="cache_cleanup"
            )
            logger.info(f"✅ Cache cleanup task started (interval: {cache_interval}s)")
            
            # Start background cleanup task
            self.create_task(
                self._managed_periodic_task(
                    background_cleanup_task,
                    interval=background_interval,
                    name="background_cleanup"
                ),
                name="background_cleanup"
            )
            logger.info(f"✅ Background maintenance tasks started (interval: {background_interval}s)")
            
            self._running = True
            
        except Exception as e:
            logger.error(f"❌ Failed to start background services: {e}")
            raise
    
    async def _managed_periodic_task(self, task_func, interval: float, name: str):
        """
        Wrapper for periodic tasks that can be gracefully shutdown.
        
        Args:
            task_func: The task function to run periodically (should not sleep internally)
            interval: Interval in seconds between runs
            name: Task name for logging
        """
        logger.debug(f"Starting periodic task: {name}")
        
        # Run initial task immediately (non-blocking)
        try:
            if asyncio.iscoroutinefunction(task_func):
                await task_func()
            else:
                await asyncio.get_event_loop().run_in_executor(None, task_func)
            logger.debug(f"Initial run of {name} completed")
        except Exception as e:
            logger.error(f"Initial run of {name} failed: {e}")
        
        # Then run periodically until shutdown
        while not self._shutdown_event.is_set():
            try:
                # Wait for the interval or shutdown signal
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=interval)
                # If we get here, shutdown was requested
                break
                
            except asyncio.TimeoutError:
                # Timeout means it's time for the next run
                try:
                    if asyncio.iscoroutinefunction(task_func):
                        await task_func()
                    else:
                        await asyncio.get_event_loop().run_in_executor(None, task_func)
                    logger.debug(f"Periodic run of {name} completed")
                except Exception as e:
                    logger.error(f"Periodic task {name} error: {e}")
            except asyncio.CancelledError:
                logger.debug(f"Periodic task {name} cancelled gracefully")
                raise
        
        logger.debug(f"Periodic task {name} shutdown completed")
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown all managed tasks.
        
        This will:
        1. Signal all tasks to stop
        2. Wait for tasks to complete gracefully
        3. Cancel remaining tasks if timeout exceeded
        4. Run cleanup callbacks
        """
        if not self._running:
            return
        
        logger.info("🛑 Starting graceful shutdown...")
        start_time = time.time()
        
        # Signal shutdown to all managed tasks
        self._shutdown_event.set()
        self._running = False
        
        if self._tasks:
            logger.info(f"Waiting for {len(self._tasks)} tasks to complete...")
            
            try:
                # Wait for tasks to complete gracefully with proper exception handling
                done, pending = await asyncio.wait(
                    self._tasks,
                    timeout=self._shutdown_timeout,
                    return_when=asyncio.ALL_COMPLETED
                )
                
                # Handle completed tasks
                for task in done:
                    try:
                        # Check for exceptions in completed tasks
                        if not task.cancelled():
                            exception = task.exception()
                            if exception:
                                logger.warning(f"Task {getattr(task, 'get_name', lambda: 'unnamed')()} completed with exception: {exception}")
                    except asyncio.CancelledError:
                        # Task was cancelled, this is expected during shutdown
                        pass
                    except Exception as e:
                        logger.debug(f"Error checking task {getattr(task, 'get_name', lambda: 'unnamed')()} status: {e}")
                
                # Cancel any remaining tasks
                if pending:
                    logger.warning(f"⏱️ Shutdown timeout ({self._shutdown_timeout}s), cancelling {len(pending)} remaining tasks...")
                    for task in pending:
                        task.cancel()
                    
                    # Wait for cancellation to complete
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*pending, return_exceptions=True),
                            timeout=2.0
                        )
                        logger.info("✅ All remaining tasks cancelled successfully")
                    except asyncio.TimeoutError:
                        logger.warning("Some tasks did not respond to cancellation")
                    except Exception as e:
                        logger.debug(f"Error during task cancellation: {e}")
                else:
                    logger.info("✅ All tasks completed gracefully")
                
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
        
        # Run cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Cleanup callback error: {e}")
        
        # Stop background processing
        try:
            from larrybot.utils.background_processing import stop_background_processing
            await stop_background_processing()
        except Exception as e:
            logger.error(f"Error stopping background processing: {e}")
        
        shutdown_duration = time.time() - start_time
        logger.info(f"✅ Shutdown completed in {shutdown_duration:.2f}s")
    
    @property
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_event.is_set()
    
    def get_task_stats(self) -> Dict[str, Any]:
        """Get statistics about managed tasks."""
        return {
            'total_tasks': len(self._tasks),
            'running_tasks': len([t for t in self._tasks if not t.done()]),
            'completed_tasks': len([t for t in self._tasks if t.done() and not t.cancelled()]),
            'cancelled_tasks': len([t for t in self._tasks if t.cancelled()]),
            'is_running': self._running,
            'shutdown_requested': self._shutdown_event.is_set()
        }


# Global task manager instance
_global_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """Get the global task manager instance."""
    global _global_task_manager
    if _global_task_manager is None:
        _global_task_manager = TaskManager()
    return _global_task_manager


def create_managed_task(coro, *, name: Optional[str] = None) -> asyncio.Task:
    """Create a task using the global task manager."""
    return get_task_manager().create_task(coro, name=name)


async def shutdown_all_tasks():
    """Shutdown all managed tasks."""
    global _global_task_manager
    if _global_task_manager:
        await _global_task_manager.shutdown()


@asynccontextmanager
async def managed_task_context(test_mode: bool = False):
    """Context manager for automatic task cleanup."""
    task_manager = get_task_manager()
    try:
        await task_manager.start_background_services(test_mode=test_mode)
        yield task_manager
    finally:
        await task_manager.shutdown() 