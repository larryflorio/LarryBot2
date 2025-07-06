"""
Production configuration for LarryBot2.
Enhanced security and monitoring settings for production use.
"""
import os
from typing import Dict, Any
from .loader import Config


class ProductionConfig(Config):
    """
    Production configuration with enhanced security and monitoring.
    Extends the base Config with production-specific settings.
    """

    def __init__(self, env_file: str='.env.production'):
        super().__init__(env_file)
        self.ENVIRONMENT: str = 'production'
        self.DEBUG: bool = False
        self.SECURE_ERROR_MESSAGES: bool = os.getenv('SECURE_ERROR_MESSAGES',
            'true').lower() == 'true'
        self.LOG_SENSITIVE_DATA: bool = os.getenv('LOG_SENSITIVE_DATA', 'false'
            ).lower() == 'true'
        self.MAX_LOG_SIZE_MB: int = int(os.getenv('MAX_LOG_SIZE_MB', '10'))
        self.LOG_BACKUP_COUNT: int = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        self.CACHE_TTL_SECONDS: int = int(os.getenv('CACHE_TTL_SECONDS', '300')
            )
        self.MAX_CONCURRENT_REQUESTS: int = int(os.getenv(
            'MAX_CONCURRENT_REQUESTS', '5'))
        self.REQUEST_TIMEOUT_SECONDS: int = int(os.getenv(
            'REQUEST_TIMEOUT_SECONDS', '30'))
        self.HEALTH_CHECK_ENABLED: bool = os.getenv('HEALTH_CHECK_ENABLED',
            'true').lower() == 'true'
        self.PERFORMANCE_MONITORING: bool = os.getenv('PERFORMANCE_MONITORING',
            'true').lower() == 'true'
        self.ERROR_REPORTING: bool = os.getenv('ERROR_REPORTING', 'true'
            ).lower() == 'true'
        self.DATABASE_PERMISSIONS: int = int(os.getenv(
            'DATABASE_PERMISSIONS', '600'), 8)
        self.LOG_PERMISSIONS: int = int(os.getenv('LOG_PERMISSIONS', '600'), 8)
        self.CONFIG_PERMISSIONS: int = int(os.getenv('CONFIG_PERMISSIONS',
            '600'), 8)

    def validate(self) ->None:
        """Enhanced validation for production configuration."""
        super().validate()
        errors = []
        if self.DEBUG:
            errors.append('DEBUG should be False in production.')
        if self.LOG_SENSITIVE_DATA:
            errors.append('LOG_SENSITIVE_DATA should be False in production.')
        if self.MAX_LOG_SIZE_MB <= 0 or self.MAX_LOG_SIZE_MB > 100:
            errors.append('MAX_LOG_SIZE_MB must be between 1 and 100.')
        if self.LOG_BACKUP_COUNT <= 0 or self.LOG_BACKUP_COUNT > 10:
            errors.append('LOG_BACKUP_COUNT must be between 1 and 10.')
        if self.CACHE_TTL_SECONDS <= 0:
            errors.append('CACHE_TTL_SECONDS must be positive.')
        if self.MAX_CONCURRENT_REQUESTS <= 0:
            errors.append('MAX_CONCURRENT_REQUESTS must be positive.')
        if self.REQUEST_TIMEOUT_SECONDS <= 0:
            errors.append('REQUEST_TIMEOUT_SECONDS must be positive.')
        if errors:
            error_message = '\n'.join(errors)
            raise ValueError(
                f'Production configuration validation failed:\n{error_message}'
                )

    def get_production_info(self) ->Dict[str, Any]:
        """Get production-specific configuration information."""
        base_info = self.get_single_user_info()
        production_info = {'environment': self.ENVIRONMENT, 'debug_enabled':
            self.DEBUG, 'secure_error_messages': self.SECURE_ERROR_MESSAGES,
            'log_sensitive_data': self.LOG_SENSITIVE_DATA,
            'max_log_size_mb': self.MAX_LOG_SIZE_MB, 'log_backup_count':
            self.LOG_BACKUP_COUNT, 'cache_ttl_seconds': self.
            CACHE_TTL_SECONDS, 'max_concurrent_requests': self.
            MAX_CONCURRENT_REQUESTS, 'request_timeout_seconds': self.
            REQUEST_TIMEOUT_SECONDS, 'health_check_enabled': self.
            HEALTH_CHECK_ENABLED, 'performance_monitoring': self.
            PERFORMANCE_MONITORING, 'error_reporting': self.ERROR_REPORTING,
            'database_permissions': oct(self.DATABASE_PERMISSIONS),
            'log_permissions': oct(self.LOG_PERMISSIONS),
            'config_permissions': oct(self.CONFIG_PERMISSIONS)}
        base_info.update(production_info)
        return base_info

    def is_production(self) ->bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == 'production' and not self.DEBUG

    def get_log_config(self) ->Dict[str, Any]:
        """Get logging configuration for production."""
        return {'level': self.LOG_LEVEL, 'max_size_mb': self.
            MAX_LOG_SIZE_MB, 'backup_count': self.LOG_BACKUP_COUNT,
            'log_sensitive_data': self.LOG_SENSITIVE_DATA,
            'secure_error_messages': self.SECURE_ERROR_MESSAGES}

    def get_security_config(self) ->Dict[str, Any]:
        """Get security configuration for production."""
        return {'secure_error_messages': self.SECURE_ERROR_MESSAGES,
            'log_sensitive_data': self.LOG_SENSITIVE_DATA,
            'database_permissions': self.DATABASE_PERMISSIONS,
            'log_permissions': self.LOG_PERMISSIONS, 'config_permissions':
            self.CONFIG_PERMISSIONS, 'max_requests_per_minute': self.
            MAX_REQUESTS_PER_MINUTE}

    def get_performance_config(self) ->Dict[str, Any]:
        """Get performance configuration for production."""
        return {'cache_ttl_seconds': self.CACHE_TTL_SECONDS,
            'max_concurrent_requests': self.MAX_CONCURRENT_REQUESTS,
            'request_timeout_seconds': self.REQUEST_TIMEOUT_SECONDS,
            'performance_monitoring': self.PERFORMANCE_MONITORING}
