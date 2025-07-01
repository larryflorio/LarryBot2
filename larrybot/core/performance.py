"""
Advanced Performance Monitoring System for LarryBot2 Phase 2

This module provides comprehensive performance tracking, metrics collection,
and monitoring capabilities for enterprise-grade performance analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, ContextManager
from contextlib import contextmanager
import time
import psutil
import threading
import asyncio
from collections import defaultdict, deque
import logging
import weakref
from enum import Enum

# Performance monitoring logger
perf_logger = logging.getLogger('performance')


class MetricType(Enum):
    """Types of performance metrics."""
    OPERATION = "operation"
    DATABASE = "database" 
    MEMORY = "memory"
    CACHE = "cache"
    BACKGROUND_JOB = "background_job"
    NETWORK = "network"


class Severity(Enum):
    """Performance issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceMetrics:
    """Comprehensive performance tracking."""
    operation_name: str
    execution_time: float
    memory_usage: int
    cache_hit_rate: float
    database_queries: int
    background_jobs: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metric_type: MetricType = MetricType.OPERATION
    severity: Severity = Severity.INFO
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format."""
        return {
            'operation_name': self.operation_name,
            'execution_time': self.execution_time,
            'memory_usage': self.memory_usage,
            'cache_hit_rate': self.cache_hit_rate,
            'database_queries': self.database_queries,
            'background_jobs': self.background_jobs,
            'timestamp': self.timestamp.isoformat(),
            'metric_type': self.metric_type.value,
            'severity': self.severity.value,
            'context': self.context
        }


@dataclass
class PerformanceThresholds:
    """Configurable performance thresholds."""
    operation_warning: float = 1.0  # seconds
    operation_critical: float = 5.0  # seconds
    memory_warning: int = 100_000_000  # 100MB
    memory_critical: int = 500_000_000  # 500MB
    cache_hit_warning: float = 0.5  # 50%
    cache_hit_critical: float = 0.2  # 20%
    db_query_warning: int = 10
    db_query_critical: int = 50


class PerformanceCollector:
    """Collect and analyze performance metrics with enterprise-grade capabilities."""
    
    def __init__(self, max_metrics: int = 10000, retention_hours: int = 24):
        self._metrics: List[PerformanceMetrics] = []
        self._aggregates: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self.max_metrics = max_metrics
        self.retention_hours = retention_hours
        self.thresholds = PerformanceThresholds()
        
        # Active tracking
        self._active_operations: Dict[str, float] = {}
        self._operation_counts: Dict[str, int] = defaultdict(int)
        self._recent_metrics: deque = deque(maxlen=1000)
        
        # Performance statistics
        self._hourly_stats: Dict[str, Dict] = defaultdict(dict)
        
    @contextmanager
    def track_operation(self, operation_name: str, context: Optional[Dict] = None) -> ContextManager[None]:
        """
        Context manager for comprehensive operation tracking.
        
        Usage:
            with performance_collector.track_operation("database_query", {"table": "tasks"}):
                # Your operation here
                pass
        """
        start_time = time.time()
        start_memory = self._get_memory_usage()
        operation_id = f"{operation_name}_{start_time}"
        
        # Track active operation
        self._active_operations[operation_id] = start_time
        
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            end_memory = self._get_memory_usage()
            memory_delta = end_memory - start_memory
            
            # Remove from active operations
            self._active_operations.pop(operation_id, None)
            
            # Create comprehensive metrics
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                execution_time=execution_time,
                memory_usage=memory_delta,
                cache_hit_rate=self._get_cache_hit_rate(),
                database_queries=self._get_db_query_count(),
                background_jobs=self._get_background_job_count(),
                context=context or {},
                severity=self._determine_severity(execution_time, memory_delta)
            )
            
            self._record_metrics(metrics)
            
            # Log performance warnings
            if metrics.severity != Severity.INFO:
                perf_logger.warning(
                    f"Performance {metrics.severity.value}: {operation_name} "
                    f"took {execution_time:.2f}s (memory: {memory_delta/1024/1024:.1f}MB)"
                )
    
    def _record_metrics(self, metrics: PerformanceMetrics) -> None:
        """Record metrics with thread safety and aggregation."""
        with self._lock:
            # Add to main metrics list
            self._metrics.append(metrics)
            self._recent_metrics.append(metrics)
            
            # Update operation counts
            self._operation_counts[metrics.operation_name] += 1
            
            # Maintain max size
            if len(self._metrics) > self.max_metrics:
                self._metrics.pop(0)
            
            # Update aggregates
            self._update_aggregates(metrics)
            
            # Clean old metrics periodically
            if len(self._metrics) % 100 == 0:
                self._clean_old_metrics()
    
    def _update_aggregates(self, metrics: PerformanceMetrics) -> None:
        """Update aggregate statistics."""
        op_name = metrics.operation_name
        
        if op_name not in self._aggregates:
            self._aggregates[op_name] = {
                'count': 0,
                'total_time': 0.0,
                'avg_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0,
                'total_memory': 0,
                'avg_memory': 0.0,
                'last_execution': None
            }
        
        agg = self._aggregates[op_name]
        agg['count'] += 1
        agg['total_time'] += metrics.execution_time
        agg['avg_time'] = agg['total_time'] / agg['count']
        agg['min_time'] = min(agg['min_time'], metrics.execution_time)
        agg['max_time'] = max(agg['max_time'], metrics.execution_time)
        agg['total_memory'] += metrics.memory_usage
        agg['avg_memory'] = agg['total_memory'] / agg['count']
        agg['last_execution'] = metrics.timestamp
    
    def _determine_severity(self, execution_time: float, memory_usage: int) -> Severity:
        """Determine severity based on thresholds."""
        if (execution_time >= self.thresholds.operation_critical or 
            memory_usage >= self.thresholds.memory_critical):
            return Severity.CRITICAL
        elif (execution_time >= self.thresholds.operation_warning or 
              memory_usage >= self.thresholds.memory_warning):
            return Severity.WARNING
        return Severity.INFO
    
    def _clean_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        self._metrics = [
            m for m in self._metrics 
            if m.timestamp > cutoff_time
        ]
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage."""
        try:
            return psutil.Process().memory_info().rss
        except Exception:
            return 0
    
    def _get_cache_hit_rate(self) -> float:
        """Get current cache hit rate."""
        try:
            from larrybot.utils.caching import cache_stats
            stats = cache_stats()
            return stats.get('hit_rate', 0.0)
        except Exception:
            return 0.0
    
    def _get_db_query_count(self) -> int:
        """Get current database query count."""
        try:
            from larrybot.storage.db import get_session_stats
            stats = get_session_stats()
            return stats.get('total_queries', 0)
        except Exception:
            return 0
    
    def _get_background_job_count(self) -> int:
        """Get current background job count."""
        try:
            from larrybot.utils.background_processing import get_background_queue_stats
            stats = get_background_queue_stats()
            return stats.get('pending_jobs', 0)
        except Exception:
            return 0
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data."""
        with self._lock:
            recent_metrics = [
                m for m in self._metrics 
                if m.timestamp > datetime.utcnow() - timedelta(hours=1)
            ]
            
            if not recent_metrics:
                return self._empty_dashboard()
            
            return {
                'summary': self._get_summary_stats(recent_metrics),
                'operations': self._get_operation_stats(),
                'system': self._get_system_stats(),
                'alerts': self._get_performance_alerts(),
                'trends': self._get_performance_trends(),
                'top_operations': self._get_top_operations(),
                'active_operations': len(self._active_operations),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _empty_dashboard(self) -> Dict[str, Any]:
        """Return empty dashboard when no metrics available."""
        return {
            'summary': {'total_operations': 0, 'avg_execution_time': 0.0},
            'operations': {},
            'system': {'memory_usage': 0.0, 'cpu_usage': 0.0},
            'alerts': [],
            'trends': {},
            'top_operations': [],
            'active_operations': 0,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _get_summary_stats(self, metrics: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Get summary statistics from metrics."""
        total_ops = len(metrics)
        avg_time = sum(m.execution_time for m in metrics) / total_ops if total_ops > 0 else 0.0
        warning_count = len([m for m in metrics if m.severity == Severity.WARNING])
        critical_count = len([m for m in metrics if m.severity == Severity.CRITICAL])
        
        return {
            'total_operations': total_ops,
            'avg_execution_time': round(avg_time, 3),
            'warning_operations': warning_count,
            'critical_operations': critical_count,
            'success_rate': round((total_ops - critical_count) / total_ops * 100, 2) if total_ops > 0 else 100.0
        }
    
    def _get_operation_stats(self) -> Dict[str, Dict]:
        """Get per-operation statistics."""
        return {
            op_name: {
                'count': stats['count'],
                'avg_time': round(stats['avg_time'], 3),
                'min_time': round(stats['min_time'], 3) if stats['min_time'] != float('inf') else 0.0,
                'max_time': round(stats['max_time'], 3),
                'avg_memory': round(stats['avg_memory'] / 1024 / 1024, 2),  # MB
                'last_execution': stats['last_execution'].isoformat() if stats['last_execution'] else None
            }
            for op_name, stats in self._aggregates.items()
        }
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        try:
            memory_percent = psutil.virtual_memory().percent
            cpu_percent = psutil.cpu_percent(interval=None)
            disk_usage = psutil.disk_usage('/').percent
            
            return {
                'memory_usage': round(memory_percent, 2),
                'cpu_usage': round(cpu_percent, 2),
                'disk_usage': round(disk_usage, 2),
                'memory_available': round(psutil.virtual_memory().available / 1024 / 1024 / 1024, 2),  # GB
                'cpu_count': psutil.cpu_count()
            }
        except Exception as e:
            perf_logger.warning(f"Could not get system stats: {e}")
            return {'memory_usage': 0.0, 'cpu_usage': 0.0, 'disk_usage': 0.0}
    
    def _get_performance_alerts(self) -> List[Dict[str, Any]]:
        """Get current performance alerts."""
        alerts = []
        
        # Check recent critical operations
        recent_critical = [
            m for m in self._recent_metrics 
            if m.severity == Severity.CRITICAL and 
               m.timestamp > datetime.utcnow() - timedelta(minutes=15)
        ]
        
        for metric in recent_critical:
            alerts.append({
                'type': 'critical_operation',
                'operation': metric.operation_name,
                'execution_time': metric.execution_time,
                'timestamp': metric.timestamp.isoformat(),
                'message': f"Critical performance: {metric.operation_name} took {metric.execution_time:.2f}s"
            })
        
        # Check active long-running operations
        current_time = time.time()
        for op_id, start_time in self._active_operations.items():
            duration = current_time - start_time
            if duration > self.thresholds.operation_warning:
                alerts.append({
                    'type': 'long_running_operation',
                    'operation': op_id.split('_')[0],
                    'duration': duration,
                    'timestamp': datetime.utcnow().isoformat(),
                    'message': f"Long-running operation: {op_id.split('_')[0]} running for {duration:.1f}s"
                })
        
        return alerts
    
    def _get_performance_trends(self) -> Dict[str, List[float]]:
        """Get performance trends over time."""
        # Get last 10 metrics for trending
        recent = list(self._recent_metrics)[-10:] if self._recent_metrics else []
        
        return {
            'execution_times': [m.execution_time for m in recent],
            'memory_usage': [m.memory_usage / 1024 / 1024 for m in recent],  # MB
            'cache_hit_rates': [m.cache_hit_rate for m in recent],
            'timestamps': [m.timestamp.isoformat() for m in recent]
        }
    
    def _get_top_operations(self) -> List[Dict[str, Any]]:
        """Get top operations by various metrics."""
        sorted_by_time = sorted(
            self._aggregates.items(), 
            key=lambda x: x[1]['avg_time'], 
            reverse=True
        )[:5]
        
        sorted_by_count = sorted(
            self._aggregates.items(), 
            key=lambda x: x[1]['count'], 
            reverse=True
        )[:5]
        
        return {
            'slowest_operations': [
                {'operation': op, 'avg_time': round(stats['avg_time'], 3)}
                for op, stats in sorted_by_time
            ],
            'most_frequent': [
                {'operation': op, 'count': stats['count']}
                for op, stats in sorted_by_count
            ]
        }
    
    def export_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Export metrics for external analysis."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            recent_metrics = [
                m for m in self._metrics 
                if m.timestamp > cutoff_time
            ]
            
            return [m.to_dict() for m in recent_metrics]
    
    def clear_metrics(self, hours: Optional[int] = None) -> int:
        """Clear metrics older than specified hours. Returns count of cleared metrics."""
        with self._lock:
            original_count = len(self._metrics)
            
            if hours is None:
                self._metrics.clear()
                self._aggregates.clear()
                self._recent_metrics.clear()
                return original_count
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            self._metrics = [
                m for m in self._metrics 
                if m.timestamp > cutoff_time
            ]
            
            # Rebuild aggregates for remaining metrics
            self._aggregates.clear()
            for metric in self._metrics:
                self._update_aggregates(metric)
            
            return original_count - len(self._metrics)


# Global performance collector instance
_performance_collector: Optional[PerformanceCollector] = None


def get_performance_collector() -> PerformanceCollector:
    """Get the global performance collector instance."""
    global _performance_collector
    if _performance_collector is None:
        _performance_collector = PerformanceCollector()
    return _performance_collector


def track_performance(operation_name: str, context: Optional[Dict] = None):
    """Decorator for automatic performance tracking."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                with get_performance_collector().track_operation(operation_name, context):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with get_performance_collector().track_operation(operation_name, context):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator 