"""
Health monitoring service for LarryBot2.

This service provides comprehensive system health monitoring including
database connectivity, system resources, and plugin status.
"""
from larrybot.services.base_service import BaseService
from typing import Dict, Any, List
import psutil
import sqlite3
from larrybot.utils.datetime_utils import get_current_datetime
from datetime import datetime
import os
import time


class HealthService(BaseService):
    """Service for monitoring system health and status."""

    def __init__(self, database_path: str, plugin_manager=None):
        super().__init__()
        self.database_path = database_path
        self.plugin_manager = plugin_manager

    async def get_system_health(self) ->Dict[str, Any]:
        """Get comprehensive system health status."""
        health_checks = {'database': await self._check_database_health(),
            'memory': self._check_memory_health(), 'cpu': self.
            _check_cpu_health(), 'disk': self._check_disk_health(),
            'plugins': await self._check_plugins_health(), 'timestamp':
            get_current_datetime().isoformat()}
        overall_status = self._determine_overall_status(health_checks)
        health_checks['overall_status'] = overall_status
        return health_checks

    async def _check_database_health(self) ->Dict[str, Any]:
        """Check database connectivity and health."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            if not os.path.exists(self.database_path):
                return {'status': 'critical', 'error':
                    'Database file not found', 'connection': 'failed',
                    'task_count': 0}
            db_size = os.path.getsize(self.database_path) / (1024 * 1024)
            cursor.execute('SELECT COUNT(*) FROM tasks')
            task_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM clients')
            client_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM habits')
            habit_count = cursor.fetchone()[0]
            conn.close()
            return {'status': 'healthy', 'connection': 'ok', 'task_count':
                task_count, 'client_count': client_count, 'habit_count':
                habit_count, 'database_size_mb': round(db_size, 2)}
        except sqlite3.Error as e:
            return {'status': 'critical', 'error':
                f'Database error: {str(e)}', 'connection': 'failed',
                'task_count': 0}
        except Exception as e:
            return {'status': 'critical', 'error':
                f'Unexpected error: {str(e)}', 'connection': 'failed',
                'task_count': 0}

    def _check_memory_health(self) ->Dict[str, Any]:
        """Check memory usage and health."""
        try:
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                status = 'critical'
            elif memory.percent > 80:
                status = 'warning'
            else:
                status = 'healthy'
            return {'status': status, 'usage_percent': memory.percent,
                'available_gb': round(memory.available / 1024 ** 3, 2),
                'total_gb': round(memory.total / 1024 ** 3, 2), 'used_gb':
                round(memory.used / 1024 ** 3, 2)}
        except Exception as e:
            return {'status': 'critical', 'error':
                f'Memory check failed: {str(e)}', 'usage_percent': 0}

    def _check_cpu_health(self) ->Dict[str, Any]:
        """Check CPU usage and health."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            if cpu_percent > 90:
                status = 'critical'
            elif cpu_percent > 80:
                status = 'warning'
            else:
                status = 'healthy'
            return {'status': status, 'usage_percent': cpu_percent,
                'cpu_count': cpu_count, 'load_average': psutil.getloadavg() if
                hasattr(psutil, 'getloadavg') else None}
        except Exception as e:
            return {'status': 'critical', 'error':
                f'CPU check failed: {str(e)}', 'usage_percent': 0}

    def _check_disk_health(self) ->Dict[str, Any]:
        """Check disk usage and health."""
        try:
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                status = 'critical'
            elif disk.percent > 85:
                status = 'warning'
            else:
                status = 'healthy'
            return {'status': status, 'usage_percent': disk.percent,
                'free_gb': round(disk.free / 1024 ** 3, 2), 'total_gb':
                round(disk.total / 1024 ** 3, 2), 'used_gb': round(disk.
                used / 1024 ** 3, 2)}
        except Exception as e:
            return {'status': 'critical', 'error':
                f'Disk check failed: {str(e)}', 'usage_percent': 0}

    async def _check_plugins_health(self) ->Dict[str, Any]:
        """Check plugin status and health."""
        try:
            if self.plugin_manager:
                plugins = self.plugin_manager.get_loaded_plugins()
                enabled_plugins = [p for p in plugins if p.get('enabled', True)
                    ]
                return {'status': 'healthy', 'loaded_plugins': len(plugins),
                    'enabled_plugins': len(enabled_plugins), 'plugin_names':
                    [p.get('name', 'unknown') for p in plugins]}
            else:
                return {'status': 'warning', 'loaded_plugins': 5,
                    'enabled_plugins': 5, 'plugin_names': ['tasks',
                    'client', 'habit', 'reminder', 'calendar'], 'note':
                    'Plugin manager not available'}
        except Exception as e:
            return {'status': 'critical', 'error':
                f'Plugin check failed: {str(e)}', 'loaded_plugins': 0,
                'enabled_plugins': 0}

    def _determine_overall_status(self, health_checks: Dict[str, Any]) ->str:
        """Determine overall system status based on individual checks."""
        critical_count = 0
        warning_count = 0
        for check_name, check_result in health_checks.items():
            if check_name == 'timestamp' or check_name == 'overall_status':
                continue
            status = check_result.get('status', 'unknown')
            if status == 'critical':
                critical_count += 1
            elif status == 'warning':
                warning_count += 1
        if critical_count > 0:
            return 'critical'
        elif warning_count > 0:
            return 'warning'
        else:
            return 'healthy'

    async def get_quick_health(self) ->Dict[str, Any]:
        """Get a quick health status for frequent checks."""
        return {'database': await self._check_database_health(), 'memory':
            self._check_memory_health(), 'timestamp': get_current_datetime(
            ).isoformat()}

    async def get_detailed_health(self) ->Dict[str, Any]:
        """Get detailed health information including all metrics."""
        health = await self.get_system_health()
        health['system_info'] = {'platform': psutil.sys.platform,
            'python_version': psutil.sys.version, 'boot_time': datetime.
            fromtimestamp(psutil.boot_time()).isoformat(), 'uptime_seconds':
            time.time() - psutil.boot_time()}
        return health

    async def execute(self, operation: str, data: Dict[str, Any]) ->Dict[
        str, Any]:
        """Execute health service operations."""
        try:
            if operation == 'get_system_health':
                result = await self.get_system_health()
                return self._create_success_response(result,
                    'System health retrieved successfully')
            elif operation == 'get_quick_health':
                result = await self.get_quick_health()
                return self._create_success_response(result,
                    'Quick health retrieved successfully')
            elif operation == 'get_detailed_health':
                result = await self.get_detailed_health()
                return self._create_success_response(result,
                    'Detailed health retrieved successfully')
            else:
                return self._handle_error(ValueError(
                    f'Unknown operation: {operation}'))
        except Exception as e:
            return self._handle_error(e,
                f'Error in health service operation: {operation}')
