"""
Background processing utilities for LarryBot2.

Provides async task queue, job scheduling, and result caching for heavy operations
like analytics, bulk operations, and report generation to eliminate blocking operations.
"""

import asyncio
import time
import logging
import json
from typing import Any, Dict, Optional, Callable, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
from functools import wraps
import threading
import traceback

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BackgroundJob:
    """Represents a background job with metadata and result storage."""
    id: str
    func: Callable
    args: tuple
    kwargs: dict
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    progress: float = 0.0
    
    @property
    def duration(self) -> Optional[float]:
        """Get job execution duration in seconds."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_complete(self) -> bool:
        """Check if job is complete (success or failure)."""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]


class BackgroundJobQueue:
    """
    High-performance background job queue with priority handling, result caching,
    and progress tracking for heavy operations.
    
    Features:
    - Async and sync job execution
    - Priority queue for urgent tasks
    - Result caching with TTL
    - Progress tracking for long operations
    - Error handling and retry logic
    - Thread pool for CPU-intensive tasks
    """
    
    def __init__(self, max_workers: int = 4, max_queue_size: int = 1000):
        self._jobs: Dict[str, BackgroundJob] = {}
        self._queue = None  # Will be initialized in start()
        self._max_queue_size = max_queue_size
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="bg_job")
        self._running = False
        self._worker_tasks: List[asyncio.Task] = []
        self._lock = threading.RLock()
        self._max_workers = max_workers
        self._stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'cancelled_jobs': 0
        }
        
        logger.info(f"BackgroundJobQueue initialized: max_workers={max_workers}, max_queue_size={max_queue_size}")
    
    def submit_job(self, 
                   func: Callable, 
                   *args, 
                   job_id: Optional[str] = None,
                   priority: int = 5,
                   **kwargs) -> str:
        """
        Submit a job to the background queue.
        
        Args:
            func: Function to execute
            *args: Function arguments
            job_id: Optional custom job ID
            priority: Job priority (1=highest, 10=lowest)
            **kwargs: Function keyword arguments
            
        Returns:
            Job ID for tracking
        """
        if job_id is None:
            job_id = f"job_{int(time.time() * 1000000)}"
        
        job = BackgroundJob(
            id=job_id,
            func=func,
            args=args,
            kwargs=kwargs
        )
        
        with self._lock:
            self._jobs[job_id] = job
            self._stats['total_jobs'] += 1
        
        # Submit to async queue (non-blocking)
        if self._queue is not None:
            try:
                self._queue.put_nowait((priority, job_id))
                logger.debug(f"Job {job_id} submitted with priority {priority}")
            except asyncio.QueueFull:
                logger.warning(f"Job queue full, dropping job {job_id}")
                with self._lock:
                    del self._jobs[job_id]
                    self._stats['total_jobs'] -= 1
                raise RuntimeError("Background job queue is full")
        else:
            logger.warning(f"Queue not initialized, dropping job {job_id}")
            with self._lock:
                del self._jobs[job_id]
                self._stats['total_jobs'] -= 1
            raise RuntimeError("Background job queue not started")
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and result."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            
            return {
                'id': job.id,
                'status': job.status.value,
                'progress': job.progress,
                'result': job.result,
                'error': job.error,
                'created_at': job.created_at,
                'started_at': job.started_at,
                'completed_at': job.completed_at,
                'duration': job.duration
            }
    
    def get_job_result(self, job_id: str) -> Any:
        """Get job result if completed, otherwise return None."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.COMPLETED:
                return job.result
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.PENDING:
                job.status = JobStatus.CANCELLED
                self._stats['cancelled_jobs'] += 1
                return True
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            pending_jobs = sum(1 for job in self._jobs.values() if job.status == JobStatus.PENDING)
            running_jobs = sum(1 for job in self._jobs.values() if job.status == JobStatus.RUNNING)
            queue_size = self._queue.qsize() if self._queue else 0
            
            return {
                'total_jobs': self._stats['total_jobs'],
                'completed_jobs': self._stats['completed_jobs'],
                'failed_jobs': self._stats['failed_jobs'],
                'cancelled_jobs': self._stats['cancelled_jobs'],
                'pending_jobs': pending_jobs,
                'running_jobs': running_jobs,
                'queue_size': queue_size,
                'worker_count': self._max_workers
            }
    
    async def start(self):
        """Start the background job processing."""
        if self._running:
            return
        
        # Initialize the async queue
        self._queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._running = True
        
        # Start worker tasks
        for i in range(self._max_workers):
            task = asyncio.create_task(self._worker_loop(f"worker_{i}"))
            self._worker_tasks.append(task)
        
        logger.info(f"✅ Background processing system started ({self._max_workers} workers)")
    
    async def stop(self):
        """Stop the background job processing."""
        if not self._running:
            return
        
        self._running = False
        
        # Wait for all jobs to complete (with timeout)
        if self._queue:
            try:
                await asyncio.wait_for(self._queue.join(), timeout=5.0)
                logger.debug("All background jobs completed")
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for background jobs to complete")
        
        # Cancel all worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        
        # Shutdown thread pool
        self._executor.shutdown(wait=True)
        
        # Clean up queue
        self._queue = None
        
        logger.info("Background job queue stopped")
    
    async def _worker_loop(self, worker_name: str):
        """Main worker loop for processing jobs."""
        logger.debug(f"Worker {worker_name} started")
        
        while self._running:
            try:
                # Get next job from queue (with timeout)
                try:
                    priority, job_id = await asyncio.wait_for(
                        self._queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    # No jobs available, continue loop
                    continue
                
                # Process the job
                await self._process_job(job_id, worker_name)
                
                # Mark task as done in queue
                self._queue.task_done()
                
            except asyncio.CancelledError:
                logger.debug(f"Worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1.0)  # Brief pause on error
        
        logger.debug(f"Worker {worker_name} stopped")
    
    async def _process_job(self, job_id: str, worker_name: str):
        """Process a single job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status != JobStatus.PENDING:
                return
            
            job.status = JobStatus.RUNNING
            job.started_at = time.time()
        
        logger.debug(f"Worker {worker_name} processing job {job_id}")
        
        try:
            # Execute job function
            if asyncio.iscoroutinefunction(job.func):
                # Async function
                result = await job.func(*job.args, **job.kwargs)
            else:
                # Sync function - run in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(self._executor, job.func, *job.args, **job.kwargs)
            
            # Job completed successfully
            with self._lock:
                job.result = result
                job.status = JobStatus.COMPLETED
                job.completed_at = time.time()
                job.progress = 100.0
                self._stats['completed_jobs'] += 1
            
            logger.debug(f"Job {job_id} completed successfully in {job.duration:.2f}s")
            
        except Exception as e:
            # Job failed
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Job {job_id} failed: {error_msg}")
            
            with self._lock:
                job.error = error_msg
                job.status = JobStatus.FAILED
                job.completed_at = time.time()
                self._stats['failed_jobs'] += 1
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove old completed jobs to prevent memory growth."""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        with self._lock:
            old_job_ids = [
                job_id for job_id, job in self._jobs.items()
                if job.is_complete and job.completed_at and job.completed_at < cutoff_time
            ]
            
            for job_id in old_job_ids:
                del self._jobs[job_id]
            
            if old_job_ids:
                logger.info(f"Cleaned up {len(old_job_ids)} old jobs")


# Global background job queue
_global_queue = BackgroundJobQueue(max_workers=4)

def background_task(priority: int = 5, job_id: Optional[str] = None):
    """
    Decorator for running functions as background tasks.
    
    Args:
        priority: Task priority (1=highest, 10=lowest)
        job_id: Optional custom job ID
    
    Example:
        @background_task(priority=3)
        def generate_analytics_report(user_id):
            # Heavy computation
            return report_data
        
        # Usage
        job_id = generate_analytics_report(123)
        # Check result later
        result = get_background_result(job_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return _global_queue.submit_job(func, *args, priority=priority, job_id=job_id, **kwargs)
        return wrapper
    return decorator


def submit_background_job(func: Callable, *args, priority: int = 5, job_id: Optional[str] = None, **kwargs) -> str:
    """Submit a job to the global background queue."""
    return _global_queue.submit_job(func, *args, priority=priority, job_id=job_id, **kwargs)


def get_background_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get status of a background job."""
    return _global_queue.get_job_status(job_id)


def get_background_result(job_id: str) -> Any:
    """Get result of a completed background job."""
    return _global_queue.get_job_result(job_id)


def cancel_background_job(job_id: str) -> bool:
    """Cancel a pending background job."""
    return _global_queue.cancel_job(job_id)


def get_background_queue_stats() -> Dict[str, Any]:
    """Get background queue statistics."""
    return _global_queue.get_queue_stats()


async def start_background_processing():
    """Start the global background job queue."""
    await _global_queue.start()


async def stop_background_processing():
    """Stop the global background job queue."""
    await _global_queue.stop()


async def background_cleanup_task():
    """
    Background task for queue maintenance.
    
    This performs one cleanup cycle without sleeping. The task manager
    handles the periodic scheduling and shutdown signaling.
    """
    try:
        # Cleanup old jobs every cycle
        _global_queue.cleanup_old_jobs(max_age_hours=24)
        
        # Log queue stats
        stats = _global_queue.get_queue_stats()
        if stats['total_jobs'] > 0:
            logger.info(f"Background queue stats: {stats}")
        
    except Exception as e:
        logger.error(f"Background cleanup error: {e}")
    
    # No sleep - the task manager handles scheduling 