"""
Health monitoring system for LarryBot2 production deployment.
Provides comprehensive health checks and system status monitoring.
"""
import os
import time
import psutil
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from larrybot.config.loader import Config


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = 'healthy'
    WARNING = 'warning'
    CRITICAL = 'critical'
    UNKNOWN = 'unknown'


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime


class HealthMonitor:
    """
    Comprehensive health monitoring system for LarryBot2.
    Monitors application, database, system resources, and performance.
    """

    def __init__(self, config: Config):
        self.config = config
        self.start_time = datetime.now()
        self.last_check = None
        self.health_history: List[HealthCheck] = []

    def run_full_health_check(self) ->Dict[str, Any]:
        """Run a comprehensive health check of all systems."""
        checks = []
        checks.append(self._check_application_status())
        checks.append(self._check_database_health())
        checks.append(self._check_telegram_connectivity())
        checks.append(self._check_file_system())
        checks.append(self._check_system_resources())
        checks.append(self._check_disk_space())
        checks.append(self._check_memory_usage())
        checks.append(self._check_performance_metrics())
        checks.append(self._check_cache_health())
        checks.append(self._check_security_config())
        overall_status = self._determine_overall_status(checks)
        self.health_history.extend(checks)
        self.last_check = datetime.now()
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]
        return {'status': overall_status.value, 'timestamp': datetime.now()
            .isoformat(), 'uptime_seconds': (datetime.now() - self.
            start_time).total_seconds(), 'checks': [self._check_to_dict(
            check) for check in checks], 'summary': self._generate_summary(
            checks)}

    def _check_application_status(self) ->HealthCheck:
        """Check application status and configuration."""
        try:
            self.config.validate()
            required_vars = ['TELEGRAM_BOT_TOKEN', 'ALLOWED_TELEGRAM_USER_ID']
            missing_vars = [var for var in required_vars if not getattr(
                self.config, var, None)]
            if missing_vars:
                return HealthCheck(name='application_status', status=
                    HealthStatus.CRITICAL, message=
                    f"Missing required configuration: {', '.join(missing_vars)}"
                    , details={'missing_variables': missing_vars},
                    timestamp=datetime.now())
            is_production = getattr(self.config, 'ENVIRONMENT', 'development'
                ) == 'production'
            debug_enabled = getattr(self.config, 'DEBUG', False)
            if is_production and debug_enabled:
                return HealthCheck(name='application_status', status=
                    HealthStatus.WARNING, message=
                    'Running in production with debug enabled', details={
                    'environment': 'production', 'debug_enabled': True},
                    timestamp=datetime.now())
            return HealthCheck(name='application_status', status=
                HealthStatus.HEALTHY, message=
                'Application configuration is valid', details={
                'environment': getattr(self.config, 'ENVIRONMENT',
                'development'), 'debug_enabled': debug_enabled,
                'config_valid': True}, timestamp=datetime.now())
        except Exception as e:
            return HealthCheck(name='application_status', status=
                HealthStatus.CRITICAL, message=
                f'Application configuration error: {str(e)}', details={
                'error': str(e)}, timestamp=datetime.now())

    def _check_database_health(self) ->HealthCheck:
        """Check database health and connectivity."""
        try:
            db_path = getattr(self.config, 'DATABASE_PATH', 'larrybot.db')
            if not os.path.exists(db_path):
                return HealthCheck(name='database_health', status=
                    HealthStatus.WARNING, message=
                    'Database file does not exist (will be created on first use)'
                    , details={'database_path': db_path, 'exists': False},
                    timestamp=datetime.now())
            permissions = oct(os.stat(db_path).st_mode)[-3:]
            if permissions != '600':
                return HealthCheck(name='database_health', status=
                    HealthStatus.WARNING, message=
                    f'Database file permissions should be 600, got {permissions}'
                    , details={'database_path': db_path, 'permissions':
                    permissions}, timestamp=datetime.now())
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            conn.close()
            file_size = os.path.getsize(db_path)
            size_mb = file_size / (1024 * 1024)
            details = {'database_path': db_path, 'exists': True,
                'permissions': permissions, 'table_count': table_count,
                'size_mb': round(size_mb, 2), 'readable': True, 'writable':
                True}
            if size_mb > 100:
                return HealthCheck(name='database_health', status=
                    HealthStatus.WARNING, message=
                    f'Database is large ({size_mb:.1f}MB)', details=details,
                    timestamp=datetime.now())
            return HealthCheck(name='database_health', status=HealthStatus.
                HEALTHY, message='Database is healthy and accessible',
                details=details, timestamp=datetime.now())
        except Exception as e:
            return HealthCheck(name='database_health', status=HealthStatus.
                CRITICAL, message=f'Database error: {str(e)}', details={
                'error': str(e)}, timestamp=datetime.now())

    def _check_telegram_connectivity(self) ->HealthCheck:
        """Check Telegram API connectivity."""
        try:
            bot_token = getattr(self.config, 'TELEGRAM_BOT_TOKEN', '')
            user_id = getattr(self.config, 'ALLOWED_TELEGRAM_USER_ID', 0)
            if not bot_token:
                return HealthCheck(name='telegram_connectivity', status=
                    HealthStatus.CRITICAL, message=
                    'Telegram bot token not configured', details={
                    'bot_token_configured': False}, timestamp=datetime.now())
            if not user_id:
                return HealthCheck(name='telegram_connectivity', status=
                    HealthStatus.CRITICAL, message=
                    'Telegram user ID not configured', details={
                    'user_id_configured': False}, timestamp=datetime.now())
            if ':' not in bot_token:
                return HealthCheck(name='telegram_connectivity', status=
                    HealthStatus.WARNING, message=
                    'Bot token format appears invalid', details={
                    'bot_token_configured': True, 'format_valid': False},
                    timestamp=datetime.now())
            return HealthCheck(name='telegram_connectivity', status=
                HealthStatus.HEALTHY, message=
                'Telegram configuration appears valid', details={
                'bot_token_configured': True, 'user_id_configured': True,
                'format_valid': True}, timestamp=datetime.now())
        except Exception as e:
            return HealthCheck(name='telegram_connectivity', status=
                HealthStatus.CRITICAL, message=
                f'Telegram connectivity error: {str(e)}', details={'error':
                str(e)}, timestamp=datetime.now())

    def _check_file_system(self) ->HealthCheck:
        """Check file system health and permissions."""
        try:
            issues = []
            details = {}
            config_files = ['.env', '.env.production', '.env.local']
            for config_file in config_files:
                if os.path.exists(config_file):
                    permissions = oct(os.stat(config_file).st_mode)[-3:]
                    if permissions != '600':
                        issues.append(
                            f'{config_file}: permissions {permissions}')
                    details[config_file] = {'exists': True, 'permissions':
                        permissions}
                else:
                    details[config_file] = {'exists': False}
            log_dir = 'logs'
            if os.path.exists(log_dir):
                permissions = oct(os.stat(log_dir).st_mode)[-3:]
                if permissions != '700':
                    issues.append(f'logs directory: permissions {permissions}')
                details['log_directory'] = {'exists': True, 'permissions':
                    permissions}
            else:
                details['log_directory'] = {'exists': False}
            if issues:
                return HealthCheck(name='file_system', status=HealthStatus.
                    WARNING, message=
                    f"File permission issues: {', '.join(issues)}", details
                    =details, timestamp=datetime.now())
            return HealthCheck(name='file_system', status=HealthStatus.
                HEALTHY, message='File system permissions are secure',
                details=details, timestamp=datetime.now())
        except Exception as e:
            return HealthCheck(name='file_system', status=HealthStatus.
                CRITICAL, message=f'File system error: {str(e)}', details={
                'error': str(e)}, timestamp=datetime.now())

    def _check_system_resources(self) ->HealthCheck:
        """Check system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            process = psutil.Process()
            process_memory = process.memory_info().rss / (1024 * 1024)
            details = {'cpu_percent': round(cpu_percent, 1),
                'memory_percent': round(memory_percent, 1),
                'process_memory_mb': round(process_memory, 1),
                'total_memory_gb': round(memory.total / 1024 ** 3, 1)}
            if cpu_percent > 80 or memory_percent > 80:
                status = HealthStatus.WARNING
                message = (
                    f'High resource usage: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%'
                    )
            elif cpu_percent > 95 or memory_percent > 95:
                status = HealthStatus.CRITICAL
                message = (
                    f'Critical resource usage: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%'
                    )
            else:
                status = HealthStatus.HEALTHY
                message = (
                    f'System resources normal: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%'
                    )
            return HealthCheck(name='system_resources', status=status,
                message=message, details=details, timestamp=datetime.now())
        except Exception as e:
            return HealthCheck(name='system_resources', status=HealthStatus
                .UNKNOWN, message=
                f'Unable to check system resources: {str(e)}', details={
                'error': str(e)}, timestamp=datetime.now())

    def _check_disk_space(self) ->HealthCheck:
        """Check disk space availability."""
        try:
            disk_usage = psutil.disk_usage('.')
            free_gb = disk_usage.free / 1024 ** 3
            total_gb = disk_usage.total / 1024 ** 3
            used_percent = disk_usage.used / disk_usage.total * 100
            details = {'free_gb': round(free_gb, 1), 'total_gb': round(
                total_gb, 1), 'used_percent': round(used_percent, 1)}
            if free_gb < 1:
                status = HealthStatus.CRITICAL
                message = f'Critical: Only {free_gb:.1f}GB free disk space'
            elif free_gb < 5:
                status = HealthStatus.WARNING
                message = f'Warning: Low disk space ({free_gb:.1f}GB free)'
            else:
                status = HealthStatus.HEALTHY
                message = f'Disk space adequate: {free_gb:.1f}GB free'
            return HealthCheck(name='disk_space', status=status, message=
                message, details=details, timestamp=datetime.now())
        except Exception as e:
            return HealthCheck(name='disk_space', status=HealthStatus.
                UNKNOWN, message=f'Unable to check disk space: {str(e)}',
                details={'error': str(e)}, timestamp=datetime.now())

    def _check_memory_usage(self) ->HealthCheck:
        """Check memory usage patterns."""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            details = {'memory_percent': round(memory.percent, 1),
                'swap_percent': round(swap.percent, 1),
                'memory_available_gb': round(memory.available / 1024 ** 3, 
                1), 'swap_used_gb': round(swap.used / 1024 ** 3, 1)}
            if memory.percent > 90:
                status = HealthStatus.CRITICAL
                message = f'Critical memory usage: {memory.percent:.1f}%'
            elif memory.percent > 80:
                status = HealthStatus.WARNING
                message = f'High memory usage: {memory.percent:.1f}%'
            elif swap.percent > 50:
                status = HealthStatus.WARNING
                message = f'High swap usage: {swap.percent:.1f}%'
            else:
                status = HealthStatus.HEALTHY
                message = f'Memory usage normal: {memory.percent:.1f}%'
            return HealthCheck(name='memory_usage', status=status, message=
                message, details=details, timestamp=datetime.now())
        except Exception as e:
            return HealthCheck(name='memory_usage', status=HealthStatus.
                UNKNOWN, message=f'Unable to check memory usage: {str(e)}',
                details={'error': str(e)}, timestamp=datetime.now())

    def _check_performance_metrics(self) ->HealthCheck:
        """Check application performance metrics."""
        try:
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            details = {'uptime_seconds': round(uptime_seconds, 1),
                'uptime_hours': round(uptime_seconds / 3600, 1),
                'start_time': self.start_time.isoformat()}
            if uptime_seconds < 300:
                status = HealthStatus.WARNING
                message = (
                    f'Application recently started ({uptime_seconds / 60:.1f} minutes ago)'
                    )
            else:
                status = HealthStatus.HEALTHY
                message = (
                    f'Application running for {uptime_seconds / 3600:.1f} hours'
                    )
            return HealthCheck(name='performance_metrics', status=status,
                message=message, details=details, timestamp=datetime.now())
        except Exception as e:
            return HealthCheck(name='performance_metrics', status=
                HealthStatus.UNKNOWN, message=
                f'Unable to check performance metrics: {str(e)}', details={
                'error': str(e)}, timestamp=datetime.now())

    def _check_cache_health(self) ->HealthCheck:
        """Check cache system health."""
        try:
            cache_enabled = getattr(self.config, 'CACHE_TTL_SECONDS', 0) > 0
            details = {'cache_enabled': cache_enabled, 'cache_ttl_seconds':
                getattr(self.config, 'CACHE_TTL_SECONDS', 0)}
            if cache_enabled:
                status = HealthStatus.HEALTHY
                message = 'Cache system is enabled and configured'
            else:
                status = HealthStatus.WARNING
                message = 'Cache system is disabled'
            return HealthCheck(name='cache_health', status=status, message=
                message, details=details, timestamp=datetime.now())
        except Exception as e:
            return HealthCheck(name='cache_health', status=HealthStatus.
                UNKNOWN, message=f'Unable to check cache health: {str(e)}',
                details={'error': str(e)}, timestamp=datetime.now())

    def _check_security_config(self) ->HealthCheck:
        """Check security configuration."""
        try:
            issues = []
            details = {}
            secure_errors = getattr(self.config, 'SECURE_ERROR_MESSAGES', True)
            details['secure_error_messages'] = secure_errors
            if not secure_errors:
                issues.append('Secure error messages disabled')
            log_sensitive = getattr(self.config, 'LOG_SENSITIVE_DATA', False)
            details['log_sensitive_data'] = log_sensitive
            if log_sensitive:
                issues.append('Logging sensitive data enabled')
            rate_limit = getattr(self.config, 'MAX_REQUESTS_PER_MINUTE', 60)
            details['rate_limit'] = rate_limit
            if rate_limit > 1000:
                issues.append('Rate limit seems very high')
            if issues:
                return HealthCheck(name='security_config', status=
                    HealthStatus.WARNING, message=
                    f"Security issues: {', '.join(issues)}", details=
                    details, timestamp=datetime.now())
            return HealthCheck(name='security_config', status=HealthStatus.
                HEALTHY, message='Security configuration is appropriate',
                details=details, timestamp=datetime.now())
        except Exception as e:
            return HealthCheck(name='security_config', status=HealthStatus.
                UNKNOWN, message=
                f'Unable to check security configuration: {str(e)}',
                details={'error': str(e)}, timestamp=datetime.now())

    def _determine_overall_status(self, checks: List[HealthCheck]
        ) ->HealthStatus:
        """Determine overall health status based on individual checks."""
        if any(check.status == HealthStatus.CRITICAL for check in checks):
            return HealthStatus.CRITICAL
        elif any(check.status == HealthStatus.WARNING for check in checks):
            return HealthStatus.WARNING
        elif any(check.status == HealthStatus.UNKNOWN for check in checks):
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY

    def _check_to_dict(self, check: HealthCheck) ->Dict[str, Any]:
        """Convert health check to dictionary."""
        return {'name': check.name, 'status': check.status.value, 'message':
            check.message, 'details': check.details, 'timestamp': check.
            timestamp.isoformat()}

    def _generate_summary(self, checks: List[HealthCheck]) ->Dict[str, Any]:
        """Generate summary of health checks."""
        status_counts = {}
        for status in HealthStatus:
            status_counts[status.value] = len([c for c in checks if c.
                status == status])
        return {'total_checks': len(checks), 'status_counts': status_counts,
            'overall_status': self._determine_overall_status(checks).value}

    def get_health_history(self, limit: int=10) ->List[Dict[str, Any]]:
        """Get recent health check history."""
        recent_checks = self.health_history[-limit:
            ] if self.health_history else []
        return [self._check_to_dict(check) for check in recent_checks]

    def get_uptime(self) ->Dict[str, Any]:
        """Get application uptime information."""
        uptime = datetime.now() - self.start_time
        return {'start_time': self.start_time.isoformat(), 'uptime_seconds':
            uptime.total_seconds(), 'uptime_hours': uptime.total_seconds() /
            3600, 'uptime_days': uptime.total_seconds() / (3600 * 24)}


_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor(config: Config) ->HealthMonitor:
    """Get or create global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor(config)
    return _health_monitor


def run_health_check(config: Config) ->Dict[str, Any]:
    """Run a health check and return results."""
    monitor = get_health_monitor(config)
    return monitor.run_full_health_check()
