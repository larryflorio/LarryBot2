"""
Error Handling Decorators and Utilities for LarryBot2

This module provides decorators and utilities for standardized error handling
across different layers of the application (repositories, services, handlers).
"""

import asyncio
import functools
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type, Union
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

from larrybot.core.exceptions import (
    LarryBotException, DatabaseError, ValidationError, NetworkError,
    ServiceError, ErrorCode, ErrorSeverity, log_exception, wrap_exception
)
from larrybot.utils.datetime_utils import get_utc_now

logger = logging.getLogger(__name__)


def handle_database_errors(
    operation_name: Optional[str] = None,
    auto_rollback: bool = True,
    reraise: bool = True
):
    """
    Decorator for handling database operations with automatic transaction management.
    
    Args:
        operation_name: Name of the operation for logging
        auto_rollback: Whether to automatically rollback on error
        reraise: Whether to reraise exceptions after handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                return result
                
            except IntegrityError as e:
                if auto_rollback and hasattr(args[0], 'session') and hasattr(args[0].session, 'rollback'):
                    args[0].session.rollback()
                
                db_error = DatabaseError(
                    message=f"Database constraint violation in {op_name}",
                    error_code=ErrorCode.DATABASE_CONSTRAINT_ERROR,
                    operation=op_name,
                    context={'constraint_error': str(e)},
                    original_exception=e
                )
                log_exception(db_error)
                
                if reraise:
                    raise db_error
                return None
                
            except OperationalError as e:
                if auto_rollback and hasattr(args[0], 'session') and hasattr(args[0].session, 'rollback'):
                    args[0].session.rollback()
                
                # Check for specific operational errors
                error_code = ErrorCode.DATABASE_ERROR
                if 'timeout' in str(e).lower():
                    error_code = ErrorCode.DATABASE_TIMEOUT
                elif 'connection' in str(e).lower():
                    error_code = ErrorCode.DATABASE_CONNECTION_ERROR
                
                db_error = DatabaseError(
                    message=f"Database operational error in {op_name}",
                    error_code=error_code,
                    operation=op_name,
                    context={'operational_error': str(e)},
                    original_exception=e
                )
                log_exception(db_error)
                
                if reraise:
                    raise db_error
                return None
                
            except SQLAlchemyError as e:
                if auto_rollback and hasattr(args[0], 'session') and hasattr(args[0].session, 'rollback'):
                    args[0].session.rollback()
                
                db_error = DatabaseError(
                    message=f"Database error in {op_name}",
                    operation=op_name,
                    context={'sqlalchemy_error': str(e)},
                    original_exception=e
                )
                log_exception(db_error)
                
                if reraise:
                    raise db_error
                return None
                
            except Exception as e:
                if auto_rollback and hasattr(args[0], 'session') and hasattr(args[0].session, 'rollback'):
                    args[0].session.rollback()
                
                wrapped = wrap_exception(
                    e,
                    context={'operation': op_name}
                )
                log_exception(wrapped)
                
                if reraise:
                    raise wrapped
                return None
                
        return wrapper
    return decorator


def handle_service_errors(
    service_name: Optional[str] = None,
    return_error_response: bool = True
):
    """
    Decorator for handling service-level operations.
    
    Args:
        service_name: Name of the service for logging
        return_error_response: Whether to return structured error response
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            svc_name = service_name or getattr(args[0], '__class__', {}).get('__name__', 'Unknown')
            op_name = f"{svc_name}.{func.__name__}"
            
            try:
                result = await func(*args, **kwargs)
                return result
                
            except ValidationError as e:
                log_exception(e)
                if return_error_response:
                    return {
                        "success": False,
                        "error_code": e.error_code.value,
                        "message": e.user_message,
                        "details": e.message,
                        "suggested_action": e.suggested_action,
                        "context": e.context
                    }
                raise
                
            except LarryBotException as e:
                log_exception(e)
                if return_error_response:
                    return {
                        "success": False,
                        "error_code": e.error_code.value,
                        "message": e.user_message,
                        "details": e.message,
                        "suggested_action": e.suggested_action,
                        "context": e.context
                    }
                raise
                
            except Exception as e:
                service_error = ServiceError(
                    message=f"Service error in {op_name}",
                    service_name=svc_name,
                    operation=func.__name__,
                    original_exception=e
                )
                log_exception(service_error)
                
                if return_error_response:
                    return {
                        "success": False,
                        "error_code": service_error.error_code.value,
                        "message": service_error.user_message,
                        "details": service_error.message,
                        "suggested_action": service_error.suggested_action
                    }
                raise service_error
                
        return wrapper
    return decorator


def with_timeout(timeout_seconds: float = 30.0, operation_name: Optional[str] = None):
    """
    Decorator for adding timeout handling to async operations.
    
    Args:
        timeout_seconds: Timeout in seconds
        operation_name: Name of the operation for logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__name__}"
            
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                timeout_error = NetworkError(
                    message=f"Operation '{op_name}' timed out after {timeout_seconds} seconds",
                    error_code=ErrorCode.API_TIMEOUT,
                    context={
                        'operation': op_name,
                        'timeout_seconds': timeout_seconds
                    }
                )
                log_exception(timeout_error)
                raise timeout_error
                
        return wrapper
    return decorator


class ErrorResponseBuilder:
    """Builder for creating standardized error responses."""
    
    @staticmethod
    def build_error_response(
        exception: Union[Exception, LarryBotException],
        include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Build a standardized error response from an exception.
        
        Args:
            exception: Exception to build response from
            include_details: Whether to include detailed error information
            
        Returns:
            Standardized error response dictionary
        """
        if isinstance(exception, LarryBotException):
            response = {
                "success": False,
                "error_code": exception.error_code.value,
                "message": exception.user_message,
                "error": exception.message,  # Backward compatibility
                "suggested_action": exception.suggested_action,
                "timestamp": get_utc_now().isoformat()
            }
            
            if include_details:
                response.update({
                    "details": exception.message,
                    "context": exception.context,
                    "severity": exception.severity.value
                })
        else:
            wrapped = wrap_exception(exception)
            response = {
                "success": False,
                "error_code": wrapped.error_code.value,
                "message": wrapped.user_message,
                "error": wrapped.message,  # Backward compatibility
                "suggested_action": wrapped.suggested_action,
                "timestamp": get_utc_now().isoformat()
            }
            
            if include_details:
                response.update({
                    "details": wrapped.message,
                    "original_error": str(exception)
                })
        
        return response
    
    @staticmethod
    def build_success_response(
        data: Any = None,
        message: str = "Operation completed successfully"
    ) -> Dict[str, Any]:
        """
        Build a standardized success response.
        
        Args:
            data: Response data
            message: Success message
            
        Returns:
            Standardized success response dictionary
        """
        response = {
            "success": True,
            "message": message,
            "timestamp": get_utc_now().isoformat()
        }
        
        if data is not None:
            response["data"] = data
        
        return response 