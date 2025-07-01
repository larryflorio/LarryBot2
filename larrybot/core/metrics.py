"""
Metrics collection system for LarryBot2.

This module provides comprehensive metrics collection for command execution,
system performance, and user activity tracking.
Single-user system: all metrics belong to the authorized user.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import time
import psutil
import threading
from collections import defaultdict


@dataclass
class CommandMetrics:
    """Metrics for individual command execution."""
    command: str
    execution_time: float
    success: bool
    timestamp: datetime
    error_message: Optional[str] = None


@dataclass
class SystemMetrics:
    """System performance metrics."""
    memory_usage: float
    cpu_usage: float
    active_connections: int
    timestamp: datetime


class MetricsCollector:
    """Collects and manages metrics for the bot."""
    
    def __init__(self, max_metrics: int = 10000):
        self.command_metrics: List[CommandMetrics] = []
        self.system_metrics: List[SystemMetrics] = []
        self._lock = threading.Lock()
        self.max_metrics = max_metrics
    
    def record_command(self, command: str, execution_time: float, success: bool, 
                      error_message: Optional[str] = None) -> None:
        """Record metrics for a command execution."""
        with self._lock:
            # Add new metric
            metric = CommandMetrics(
                command=command,
                execution_time=execution_time,
                success=success,
                timestamp=datetime.now(),
                error_message=error_message
            )
            self.command_metrics.append(metric)
            
            # Maintain max size
            if len(self.command_metrics) > self.max_metrics:
                self.command_metrics.pop(0)
    
    def record_system_metrics(self) -> None:
        """Record current system metrics."""
        with self._lock:
            try:
                # Get system metrics with error handling
                memory_usage = psutil.virtual_memory().percent
                cpu_usage = psutil.cpu_percent()
                
                # Handle network connections with permission error handling
                try:
                    active_connections = len(psutil.net_connections())
                except (psutil.AccessDenied, PermissionError):
                    # On macOS and some systems, network connections require special permissions
                    active_connections = 0
                
                metric = SystemMetrics(
                    memory_usage=memory_usage,
                    cpu_usage=cpu_usage,
                    active_connections=active_connections,
                    timestamp=datetime.now()
                )
                self.system_metrics.append(metric)
                
                # Maintain max size
                if len(self.system_metrics) > self.max_metrics:
                    self.system_metrics.pop(0)
            except Exception as e:
                # Log error but don't fail - metrics are optional
                print(f"Warning: Could not record system metrics: {e}")
    
    def get_command_stats(self, hours: int = 24) -> Dict:
        """Get command execution statistics for the specified time period."""
        with self._lock:
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            recent_metrics = [
                m for m in self.command_metrics 
                if m.timestamp.timestamp() > cutoff_time
            ]
            
            if not recent_metrics:
                return {
                    "total_commands": 0,
                    "successful_commands": 0,
                    "failed_commands": 0,
                    "avg_execution_time": 0.0,
                    "commands_by_type": {},
                    "error_rate": 0.0
                }
            
            # Calculate statistics
            total_commands = len(recent_metrics)
            successful_commands = len([m for m in recent_metrics if m.success])
            failed_commands = total_commands - successful_commands
            avg_execution_time = sum(m.execution_time for m in recent_metrics) / total_commands
            
            # Commands by type
            commands_by_type = defaultdict(int)
            for metric in recent_metrics:
                commands_by_type[metric.command] += 1
            
            return {
                "total_commands": total_commands,
                "successful_commands": successful_commands,
                "failed_commands": failed_commands,
                "avg_execution_time": round(avg_execution_time, 3),
                "commands_by_type": dict(commands_by_type),
                "error_rate": round((failed_commands / total_commands) * 100, 2)
            }
    
    def get_system_stats(self, hours: int = 24) -> Dict:
        """Get system performance statistics for the specified time period."""
        with self._lock:
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            recent_metrics = [
                m for m in self.system_metrics 
                if m.timestamp.timestamp() > cutoff_time
            ]
            
            if not recent_metrics:
                return {
                    "avg_memory_usage": 0.0,
                    "avg_cpu_usage": 0.0,
                    "max_memory_usage": 0.0,
                    "max_cpu_usage": 0.0,
                    "current_memory_usage": 0.0,
                    "current_cpu_usage": 0.0
                }
            
            # Calculate statistics
            memory_usages = [m.memory_usage for m in recent_metrics]
            cpu_usages = [m.cpu_usage for m in recent_metrics]
            
            return {
                "avg_memory_usage": round(sum(memory_usages) / len(memory_usages), 2),
                "avg_cpu_usage": round(sum(cpu_usages) / len(cpu_usages), 2),
                "max_memory_usage": round(max(memory_usages), 2),
                "max_cpu_usage": round(max(cpu_usages), 2),
                "current_memory_usage": round(memory_usages[-1], 2),
                "current_cpu_usage": round(cpu_usages[-1], 2)
            }
    
    def get_user_activity(self, hours: int = 24) -> Dict:
        """Get user activity statistics for the specified time period."""
        with self._lock:
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            recent_metrics = [
                m for m in self.command_metrics 
                if m.timestamp.timestamp() > cutoff_time
            ]
            
            if not recent_metrics:
                return {
                    "total_commands": 0,
                    "activity_summary": "No recent activity"
                }
            
            # Calculate activity summary
            total_commands = len(recent_metrics)
            successful_commands = len([m for m in recent_metrics if m.success])
            failed_commands = total_commands - successful_commands
            
            return {
                "total_commands": total_commands,
                "successful_commands": successful_commands,
                "failed_commands": failed_commands,
                "activity_summary": f"{total_commands} commands in last {hours}h"
            }
    
    def clear_old_metrics(self, hours: int = 24) -> None:
        """Clear metrics older than the specified hours."""
        with self._lock:
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            
            self.command_metrics = [
                m for m in self.command_metrics 
                if m.timestamp.timestamp() > cutoff_time
            ]
            
            self.system_metrics = [
                m for m in self.system_metrics 
                if m.timestamp.timestamp() > cutoff_time
            ] 