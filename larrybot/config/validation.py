"""
Configuration validation utilities for LarryBot2 production deployment.
Provides comprehensive validation and security checks.
"""
import os
import stat
from typing import List, Dict, Any, Tuple
from pathlib import Path


class ConfigValidator:
    """
    Comprehensive configuration validator for production deployment.
    Validates environment, security, and system requirements.
    """

    def __init__(self, config):
        self.config = config
        self.errors = []
        self.warnings = []

    def validate_all(self) ->Tuple[bool, List[str], List[str]]:
        """Run all validation checks."""
        self.errors = []
        self.warnings = []
        self._validate_environment()
        self._validate_security()
        self._validate_file_permissions()
        self._validate_dependencies()
        self._validate_telegram_config()
        self._validate_database_config()
        self._validate_performance_config()
        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_environment(self) ->None:
        """Validate environment configuration."""
        required_vars = ['TELEGRAM_BOT_TOKEN', 'ALLOWED_TELEGRAM_USER_ID']
        for var in required_vars:
            if not os.getenv(var):
                self.errors.append(
                    f'Required environment variable {var} is not set')
        if not hasattr(self.config, 'ENVIRONMENT'):
            self.warnings.append(
                'Environment not explicitly set (assuming development)')
        if hasattr(self.config, 'DEBUG') and self.config.DEBUG:
            self.warnings.append(
                'Debug mode is enabled (not recommended for production)')

    def _validate_security(self) ->None:
        """Validate security configuration."""
        if hasattr(self.config, 'TELEGRAM_BOT_TOKEN'):
            token = self.config.TELEGRAM_BOT_TOKEN
            if token and not self._is_valid_bot_token(token):
                self.errors.append('TELEGRAM_BOT_TOKEN format appears invalid')
        if hasattr(self.config, 'ALLOWED_TELEGRAM_USER_ID'):
            user_id = self.config.ALLOWED_TELEGRAM_USER_ID
            if user_id <= 0:
                self.errors.append(
                    'ALLOWED_TELEGRAM_USER_ID must be a positive integer')
        if hasattr(self.config, 'MAX_REQUESTS_PER_MINUTE'):
            rate_limit = self.config.MAX_REQUESTS_PER_MINUTE
            if rate_limit <= 0:
                self.errors.append('MAX_REQUESTS_PER_MINUTE must be positive')
            elif rate_limit > 1000:
                self.warnings.append(
                    'MAX_REQUESTS_PER_MINUTE seems very high for single user')
        if hasattr(self.config, 'SECURE_ERROR_MESSAGES'):
            if not self.config.SECURE_ERROR_MESSAGES:
                self.warnings.append(
                    'SECURE_ERROR_MESSAGES is disabled (may expose sensitive data)'
                    )

    def _validate_file_permissions(self) ->None:
        """Validate file system permissions."""
        db_path = getattr(self.config, 'DATABASE_PATH', 'larrybot.db')
        if os.path.exists(db_path):
            permissions = oct(os.stat(db_path).st_mode)[-3:]
            if permissions != '600':
                self.warnings.append(
                    f'Database file permissions should be 600, got {permissions}'
                    )
        env_files = ['.env', '.env.production', '.env.local']
        for env_file in env_files:
            if os.path.exists(env_file):
                permissions = oct(os.stat(env_file).st_mode)[-3:]
                if permissions != '600':
                    self.warnings.append(
                        f'Config file {env_file} permissions should be 600, got {permissions}'
                        )

    def _validate_dependencies(self) ->None:
        """Validate system dependencies."""
        import sys
        if sys.version_info < (3, 8):
            self.errors.append('Python 3.8 or higher is required')
        required_packages = ['telegram', 'sqlalchemy', 'alembic', 'dotenv',
            'httpx', 'asyncio', 'logging']
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                self.errors.append(
                    f'Required package {package} is not installed')

    def _validate_telegram_config(self) ->None:
        """Validate Telegram-specific configuration."""
        if hasattr(self.config, 'TELEGRAM_BOT_TOKEN'):
            token = self.config.TELEGRAM_BOT_TOKEN
            if token and not self._is_valid_bot_token(token):
                self.errors.append('TELEGRAM_BOT_TOKEN appears to be invalid')
        if hasattr(self.config, 'ALLOWED_TELEGRAM_USER_ID'):
            user_id = self.config.ALLOWED_TELEGRAM_USER_ID
            if not isinstance(user_id, int) or user_id <= 0:
                self.errors.append(
                    'ALLOWED_TELEGRAM_USER_ID must be a positive integer')

    def _validate_database_config(self) ->None:
        """Validate database configuration."""
        db_path = getattr(self.config, 'DATABASE_PATH', 'larrybot.db')
        if os.path.exists(db_path):
            if not os.access(db_path, os.R_OK | os.W_OK):
                self.errors.append(
                    f'Database file {db_path} is not readable/writable')
            file_size = os.path.getsize(db_path)
            if file_size > 100 * 1024 * 1024:
                self.warnings.append(
                    f'Database file is large ({file_size / 1024 / 1024:.1f}MB)'
                    )
        else:
            self.warnings.append(
                f'Database file {db_path} does not exist (will be created)')

    def _validate_performance_config(self) ->None:
        """Validate performance-related configuration."""
        if hasattr(self.config, 'CACHE_TTL_SECONDS'):
            ttl = self.config.CACHE_TTL_SECONDS
            if ttl <= 0:
                self.errors.append('CACHE_TTL_SECONDS must be positive')
            elif ttl > 3600:
                self.warnings.append('CACHE_TTL_SECONDS seems very high')
        if hasattr(self.config, 'MAX_CONCURRENT_REQUESTS'):
            concurrent = self.config.MAX_CONCURRENT_REQUESTS
            if concurrent <= 0:
                self.errors.append('MAX_CONCURRENT_REQUESTS must be positive')
            elif concurrent > 10:
                self.warnings.append(
                    'MAX_CONCURRENT_REQUESTS seems high for single user')

    def _is_valid_bot_token(self, token: str) ->bool:
        """Basic validation of bot token format."""
        if not token:
            return False
        parts = token.split(':')
        if len(parts) != 2:
            return False
        if not parts[0].isdigit():
            return False
        if not parts[1].replace('-', '').replace('_', '').isalnum():
            return False
        return True

    def get_validation_report(self) ->Dict[str, Any]:
        """Generate a comprehensive validation report."""
        is_valid, errors, warnings = self.validate_all()
        return {'valid': is_valid, 'errors': errors, 'warnings': warnings,
            'error_count': len(errors), 'warning_count': len(warnings),
            'config_info': self._get_config_summary()}

    def _get_config_summary(self) ->Dict[str, Any]:
        """Get a summary of current configuration."""
        summary = {}
        summary['environment'] = getattr(self.config, 'ENVIRONMENT', 'unknown')
        summary['debug_enabled'] = getattr(self.config, 'DEBUG', False)
        if hasattr(self.config, 'TELEGRAM_BOT_TOKEN'):
            token = self.config.TELEGRAM_BOT_TOKEN
            summary['bot_token_configured'] = bool(token)
            if token:
                summary['bot_token_length'] = len(token)
        if hasattr(self.config, 'ALLOWED_TELEGRAM_USER_ID'):
            summary['user_id_configured'] = bool(self.config.
                ALLOWED_TELEGRAM_USER_ID)
        summary['rate_limit'] = getattr(self.config,
            'MAX_REQUESTS_PER_MINUTE', 'unknown')
        summary['cache_ttl'] = getattr(self.config, 'CACHE_TTL_SECONDS',
            'unknown')
        return summary


def validate_config(config) ->Tuple[bool, List[str], List[str]]:
    """Convenience function to validate configuration."""
    validator = ConfigValidator(config)
    return validator.validate_all()


def get_validation_report(config) ->Dict[str, Any]:
    """Convenience function to get validation report."""
    validator = ConfigValidator(config)
    return validator.get_validation_report()


def secure_config_files() ->None:
    """Set secure permissions on configuration files."""
    config_files = ['.env', '.env.production', '.env.local']
    for config_file in config_files:
        if os.path.exists(config_file):
            os.chmod(config_file, stat.S_IRUSR | stat.S_IWUSR)
            print(f'Set secure permissions on {config_file}')


def validate_environment() ->bool:
    """Validate the current environment for production deployment."""
    print('🔍 Validating environment for production deployment...')
    env_vars = ['TELEGRAM_BOT_TOKEN', 'ALLOWED_TELEGRAM_USER_ID']
    missing_vars = [var for var in env_vars if not os.getenv(var)]
    if missing_vars:
        print(
            f"❌ Missing required environment variables: {', '.join(missing_vars)}"
            )
        return False
    secure_config_files()
    print('✅ Environment validation completed')
    return True
