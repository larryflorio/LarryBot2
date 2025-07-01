"""
LarryBot2 Exception Hierarchy and Error Handling System

This module provides a comprehensive, enterprise-grade exception hierarchy
and error handling utilities for consistent error management across the application.
"""

import logging
import traceback
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCode(Enum):
    """Standardized error codes for consistent error identification."""
    # General errors
    UNKNOWN_ERROR = "E001"
    INTERNAL_ERROR = "E002"
    CONFIGURATION_ERROR = "E003"
    
    # Validation errors
    VALIDATION_ERROR = "V001"
    INVALID_INPUT = "V002"
    MISSING_REQUIRED_FIELD = "V003"
    INVALID_FORMAT = "V004"
    VALUE_OUT_OF_RANGE = "V005"
    
    # Database errors
    DATABASE_ERROR = "D001"
    DATABASE_CONNECTION_ERROR = "D002"
    DATABASE_TIMEOUT = "D003"
    DATABASE_CONSTRAINT_ERROR = "D004"
    TRANSACTION_ERROR = "D005"
    
    # Network/API errors
    NETWORK_ERROR = "N001"
    API_TIMEOUT = "N002"
    API_RATE_LIMIT = "N003"
    API_UNAUTHORIZED = "N004"
    API_NOT_FOUND = "N005"
    API_SERVER_ERROR = "N006"
    
    # Authentication/Authorization errors
    AUTH_ERROR = "A001"
    UNAUTHORIZED = "A002"
    FORBIDDEN = "A003"
    TOKEN_EXPIRED = "A004"
    
    # File/Resource errors
    FILE_ERROR = "F001"
    FILE_NOT_FOUND = "F002"
    FILE_PERMISSION_ERROR = "F003"
    FILE_SIZE_ERROR = "F004"
    
    # Plugin errors
    PLUGIN_ERROR = "P001"
    PLUGIN_LOAD_ERROR = "P002"
    PLUGIN_EXECUTION_ERROR = "P003"
    
    # Service errors
    SERVICE_ERROR = "S001"
    SERVICE_UNAVAILABLE = "S002"
    SERVICE_TIMEOUT = "S003"


class LarryBotException(Exception):
    """
    Base exception class for all LarryBot2 errors.
    
    Provides comprehensive error information including:
    - Error code and message
    - Severity level
    - User-friendly message
    - Additional context
    - Suggested actions
    """
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        suggested_action: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.user_message = user_message or self._generate_user_message()
        self.context = context or {}
        self.suggested_action = suggested_action or self._generate_suggested_action()
        self.original_exception = original_exception
        self.timestamp = datetime.utcnow()
        self.traceback_info = traceback.format_exc() if original_exception else None
        
    def _generate_user_message(self) -> str:
        """Generate user-friendly message based on error code."""
        user_messages = {
            ErrorCode.VALIDATION_ERROR: "The provided information is invalid. Please check your input and try again.",
            ErrorCode.DATABASE_ERROR: "We're experiencing database issues. Please try again in a moment.",
            ErrorCode.NETWORK_ERROR: "Network connection problem. Please check your connection and try again.",
            ErrorCode.AUTH_ERROR: "Authentication failed. Please verify your credentials.",
            ErrorCode.FILE_ERROR: "File operation failed. Please check the file and try again.",
            ErrorCode.PLUGIN_ERROR: "Plugin error occurred. The system will continue operating.",
            ErrorCode.SERVICE_ERROR: "Service temporarily unavailable. Please try again later.",
        }
        return user_messages.get(self.error_code, "An unexpected error occurred. Please try again.")
        
    def _generate_suggested_action(self) -> str:
        """Generate suggested action based on error code."""
        suggestions = {
            ErrorCode.VALIDATION_ERROR: "Verify your input format and required fields.",
            ErrorCode.DATABASE_ERROR: "Wait a moment and try again. Contact support if the issue persists.",
            ErrorCode.NETWORK_ERROR: "Check your internet connection and try again.",
            ErrorCode.AUTH_ERROR: "Re-authenticate or contact an administrator.",
            ErrorCode.FILE_ERROR: "Check file permissions and try again.",
            ErrorCode.PLUGIN_ERROR: "The system will recover automatically. Report if issues persist.",
            ErrorCode.SERVICE_ERROR: "Try again in a few minutes. Check system status if problems continue.",
        }
        return suggestions.get(self.error_code, "Try again later or contact support if the issue persists.")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for structured logging and API responses."""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "user_message": self.user_message,
            "severity": self.severity.value,
            "context": self.context,
            "suggested_action": self.suggested_action,
            "timestamp": self.timestamp.isoformat(),
            "original_exception": str(self.original_exception) if self.original_exception else None
        }
    
    def to_json(self) -> str:
        """Convert exception to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class ValidationError(LarryBotException):
    """Exception for validation errors."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        invalid_value: Any = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if field_name:
            context['field_name'] = field_name
        if invalid_value is not None:
            context['invalid_value'] = str(invalid_value)
        
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', ErrorCode.VALIDATION_ERROR)
        kwargs['severity'] = kwargs.get('severity', ErrorSeverity.WARNING)
        
        super().__init__(message, **kwargs)


class DatabaseError(LarryBotException):
    """Exception for database-related errors."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table_name: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if operation:
            context['operation'] = operation
        if table_name:
            context['table_name'] = table_name
        
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', ErrorCode.DATABASE_ERROR)
        kwargs['severity'] = kwargs.get('severity', ErrorSeverity.ERROR)
        
        super().__init__(message, **kwargs)


class NetworkError(LarryBotException):
    """Exception for network-related errors."""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if url:
            context['url'] = url
        if status_code:
            context['status_code'] = status_code
        
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', ErrorCode.NETWORK_ERROR)
        kwargs['severity'] = kwargs.get('severity', ErrorSeverity.ERROR)
        
        super().__init__(message, **kwargs)


class AuthenticationError(LarryBotException):
    """Exception for authentication/authorization errors."""
    
    def __init__(
        self,
        message: str,
        user_id: Optional[str] = None,
        required_permission: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if user_id:
            context['user_id'] = user_id
        if required_permission:
            context['required_permission'] = required_permission
        
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', ErrorCode.AUTH_ERROR)
        kwargs['severity'] = kwargs.get('severity', ErrorSeverity.WARNING)
        
        super().__init__(message, **kwargs)


class FileError(LarryBotException):
    """Exception for file operation errors."""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if file_path:
            context['file_path'] = file_path
        if operation:
            context['operation'] = operation
        
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', ErrorCode.FILE_ERROR)
        kwargs['severity'] = kwargs.get('severity', ErrorSeverity.ERROR)
        
        super().__init__(message, **kwargs)


class PluginError(LarryBotException):
    """Exception for plugin-related errors."""
    
    def __init__(
        self,
        message: str,
        plugin_name: Optional[str] = None,
        plugin_operation: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if plugin_name:
            context['plugin_name'] = plugin_name
        if plugin_operation:
            context['plugin_operation'] = plugin_operation
        
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', ErrorCode.PLUGIN_ERROR)
        kwargs['severity'] = kwargs.get('severity', ErrorSeverity.WARNING)
        
        super().__init__(message, **kwargs)


class ServiceError(LarryBotException):
    """Exception for service-level errors."""
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if service_name:
            context['service_name'] = service_name
        if operation:
            context['operation'] = operation
        
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', ErrorCode.SERVICE_ERROR)
        kwargs['severity'] = kwargs.get('severity', ErrorSeverity.ERROR)
        
        super().__init__(message, **kwargs)


# Utility functions for error handling

def wrap_exception(
    exception: Exception,
    error_code: Optional[ErrorCode] = None,
    user_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> LarryBotException:
    """
    Wrap a standard exception into a LarryBotException.
    
    Args:
        exception: Original exception to wrap
        error_code: Error code to assign
        user_message: User-friendly message
        context: Additional context information
        
    Returns:
        LarryBotException instance
    """
    # Auto-detect error code based on exception type
    if error_code is None:
        if isinstance(exception, (ValueError, TypeError)):
            error_code = ErrorCode.VALIDATION_ERROR
        elif isinstance(exception, (ConnectionError, TimeoutError)):
            error_code = ErrorCode.NETWORK_ERROR
        elif isinstance(exception, (FileNotFoundError, PermissionError, OSError)):
            error_code = ErrorCode.FILE_ERROR
        elif isinstance(exception, (ImportError, ModuleNotFoundError)):
            error_code = ErrorCode.PLUGIN_ERROR
        else:
            error_code = ErrorCode.UNKNOWN_ERROR
    
    return LarryBotException(
        message=str(exception),
        error_code=error_code,
        user_message=user_message,
        context=context,
        original_exception=exception
    )


def log_exception(
    exception: Union[Exception, LarryBotException],
    logger_instance: Optional[logging.Logger] = None,
    extra_context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log exception with appropriate level and structured information.
    
    Args:
        exception: Exception to log
        logger_instance: Logger to use (defaults to module logger)
        extra_context: Additional context to include
    """
    log = logger_instance or logger
    
    if isinstance(exception, LarryBotException):
        context = {**exception.context}
        if extra_context:
            context.update(extra_context)
        
        log_level = {
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(exception.severity, logging.ERROR)
        
        log.log(
            log_level,
            f"[{exception.error_code.value}] {exception.message}",
            extra={
                'error_code': exception.error_code.value,
                'severity': exception.severity.value,
                'context': context,
                'user_message': exception.user_message,
                'suggested_action': exception.suggested_action,
                'timestamp': exception.timestamp.isoformat()
            }
        )
    else:
        log.error(f"Unhandled exception: {str(exception)}", exc_info=True)


class ErrorContext:
    """Context manager for enhanced error handling and logging."""
    
    def __init__(
        self,
        operation_name: str,
        logger_instance: Optional[logging.Logger] = None,
        auto_log: bool = True,
        reraise: bool = True
    ):
        self.operation_name = operation_name
        self.logger = logger_instance or logger
        self.auto_log = auto_log
        self.reraise = reraise
        self.context: Dict[str, Any] = {}
    
    def add_context(self, **kwargs) -> 'ErrorContext':
        """Add context information."""
        self.context.update(kwargs)
        return self
    
    def __enter__(self) -> 'ErrorContext':
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self.auto_log:
                if isinstance(exc_val, LarryBotException):
                    # Add operation context to existing exception
                    exc_val.context.update({
                        'operation': self.operation_name,
                        **self.context
                    })
                    log_exception(exc_val, self.logger)
                else:
                    # Wrap and log standard exception
                    wrapped = wrap_exception(
                        exc_val,
                        context={
                            'operation': self.operation_name,
                            **self.context
                        }
                    )
                    log_exception(wrapped, self.logger)
            
            return not self.reraise
        return False 