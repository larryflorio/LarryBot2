from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict, Type
import logging
from larrybot.core.interfaces import ServiceInterface
from larrybot.core.exceptions import (
    LarryBotException, ValidationError, ServiceError, ErrorCode, ErrorSeverity,
    log_exception, wrap_exception
)
from larrybot.core.error_handlers import (
    handle_service_errors, ErrorResponseBuilder
)

logger = logging.getLogger(__name__)


class BaseService(ServiceInterface):
    """
    Enhanced base service class with comprehensive error handling and validation.
    
    Provides standardized error handling, validation, caching, and response formatting
    for all services in the LarryBot2 system.
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the service operation."""
        pass
    
    def _cache_get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self._cache.get(key)
    
    def _cache_set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        self._cache[key] = value
    
    def _cache_clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
    
    def _cache_remove(self, key: str) -> bool:
        """Remove specific key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def _validate_input(self, data: Any, required_fields: List[str]) -> bool:
        """
        Validate input data has required fields.
        
        Args:
            data: Data to validate
            required_fields: List of required field names
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValidationError(
                "Input data must be a dictionary",
                error_code=ErrorCode.INVALID_FORMAT,
                context={'received_type': type(data).__name__}
            )
        
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing_fields)}",
                error_code=ErrorCode.MISSING_REQUIRED_FIELD,
                context={'missing_fields': missing_fields, 'provided_fields': list(data.keys())}
            )
        
        return True
    
    def _validate_field_types(self, data: Dict[str, Any], field_types: Dict[str, Type]) -> bool:
        """
        Validate field types in data.
        
        Args:
            data: Data to validate
            field_types: Dictionary mapping field names to expected types
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        for field_name, expected_type in field_types.items():
            if field_name in data and not isinstance(data[field_name], expected_type):
                raise ValidationError(
                    f"Field '{field_name}' must be of type {expected_type.__name__}",
                    field_name=field_name,
                    invalid_value=data[field_name],
                    error_code=ErrorCode.INVALID_FORMAT,
                    context={
                        'expected_type': expected_type.__name__,
                        'received_type': type(data[field_name]).__name__
                    }
                )
        return True
    
    def _validate_field_values(self, data: Dict[str, Any], value_constraints: Dict[str, Dict[str, Any]]) -> bool:
        """
        Validate field values against constraints.
        
        Args:
            data: Data to validate
            value_constraints: Dictionary mapping field names to constraint dictionaries
                             Example: {'age': {'min': 0, 'max': 150}, 'email': {'pattern': r'.*@.*'}}
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        import re
        
        for field_name, constraints in value_constraints.items():
            if field_name not in data:
                continue
                
            value = data[field_name]
            
            # Check minimum value
            if 'min' in constraints and value < constraints['min']:
                raise ValidationError(
                    f"Field '{field_name}' must be at least {constraints['min']}",
                    field_name=field_name,
                    invalid_value=value,
                    error_code=ErrorCode.VALUE_OUT_OF_RANGE
                )
            
            # Check maximum value
            if 'max' in constraints and value > constraints['max']:
                raise ValidationError(
                    f"Field '{field_name}' must be at most {constraints['max']}",
                    field_name=field_name,
                    invalid_value=value,
                    error_code=ErrorCode.VALUE_OUT_OF_RANGE
                )
            
            # Check pattern matching for strings
            if 'pattern' in constraints and isinstance(value, str):
                if not re.match(constraints['pattern'], value):
                    raise ValidationError(
                        f"Field '{field_name}' does not match required pattern",
                        field_name=field_name,
                        invalid_value=value,
                        error_code=ErrorCode.INVALID_FORMAT
                    )
            
            # Check allowed values
            if 'allowed' in constraints and value not in constraints['allowed']:
                raise ValidationError(
                    f"Field '{field_name}' must be one of: {', '.join(map(str, constraints['allowed']))}",
                    field_name=field_name,
                    invalid_value=value,
                    error_code=ErrorCode.INVALID_INPUT
                )
        
        return True
    
    def _handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Handle errors consistently across services using standardized error system.
        
        Args:
            error: Exception to handle
            context: Additional context information
            
        Returns:
            Standardized error response dictionary
        """
        if isinstance(error, LarryBotException):
            # Add service context to existing exception
            if context:
                error.context.update({'service_context': context})
            log_exception(error, self.logger)
            response = ErrorResponseBuilder.build_error_response(error)
        else:
            # Wrap standard exception
            wrapped = wrap_exception(
                error,
                context={'service': self.__class__.__name__, 'operation': context} if context else None
            )
            log_exception(wrapped, self.logger)
            response = ErrorResponseBuilder.build_error_response(wrapped)
        
        # Add context field for backward compatibility
        if context:
            response['context'] = context
        
        return response
    
    def _create_success_response(self, data: Any, message: str = "") -> Dict[str, Any]:
        """
        Create a standardized success response.
        
        Args:
            data: Response data
            message: Success message
            
        Returns:
            Standardized success response dictionary
        """
        return ErrorResponseBuilder.build_success_response(data, message)
    
    def _create_validation_error(self, message: str, field_name: Optional[str] = None, 
                               invalid_value: Any = None) -> ValidationError:
        """
        Create a validation error with service context.
        
        Args:
            message: Error message
            field_name: Name of the invalid field
            invalid_value: The invalid value
            
        Returns:
            ValidationError instance
        """
        return ValidationError(
            message=message,
            field_name=field_name,
            invalid_value=invalid_value,
            context={'service': self.__class__.__name__}
        )
    
    def _create_service_error(self, message: str, operation: Optional[str] = None, 
                            error_code: Optional[ErrorCode] = None) -> ServiceError:
        """
        Create a service error with context.
        
        Args:
            message: Error message
            operation: Operation that failed
            error_code: Specific error code
            
        Returns:
            ServiceError instance
        """
        return ServiceError(
            message=message,
            service_name=self.__class__.__name__,
            operation=operation,
            error_code=error_code or ErrorCode.SERVICE_ERROR
        )
    
    def _log_operation(self, operation: str, details: Optional[Dict[str, Any]] = None, 
                      level: int = logging.INFO) -> None:
        """
        Log service operations with structured information.
        
        Args:
            operation: Operation name
            details: Additional details to log
            level: Logging level
        """
        log_data = {
            'service': self.__class__.__name__,
            'operation': operation
        }
        if details:
            log_data.update(details)
        
        self.logger.log(level, f"Service operation: {operation}", extra=log_data)
    
    @handle_service_errors()
    async def safe_execute(self, operation: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute service operation with standardized error handling.
        
        Args:
            operation: Operation name
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Standardized response dictionary
        """
        self._log_operation(f"executing_{operation}", {'args_count': len(args), 'kwargs_keys': list(kwargs.keys())})
        
        try:
            result = await self.execute(operation, *args, **kwargs)
            
            if isinstance(result, dict) and 'success' in result:
                # Already formatted response
                return result
            else:
                # Wrap raw result in success response
                return self._create_success_response(result, f"{operation} completed successfully")
                
        except Exception as e:
            self._log_operation(f"error_in_{operation}", {'error': str(e)}, logging.ERROR)
            raise


class ServiceFactory:
    """
    Enhanced factory for creating service instances with dependency injection and error handling.
    """
    
    def __init__(self):
        self._services: Dict[str, Type[BaseService]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def register_service(self, name: str, service_class: Type[BaseService]) -> None:
        """
        Register a service class.
        
        Args:
            name: Service name
            service_class: Service class to register
            
        Raises:
            ValidationError: If service class is invalid
        """
        if not issubclass(service_class, BaseService):
            raise ValidationError(
                f"Service class must inherit from BaseService",
                context={'service_name': name, 'service_class': service_class.__name__}
            )
        
        self._services[name] = service_class
        self.logger.info(f"Registered service: {name}")
    
    def create_service(self, name: str, *args, **kwargs) -> BaseService:
        """
        Create a service instance with error handling.
        
        Args:
            name: Service name
            *args: Constructor arguments
            **kwargs: Constructor keyword arguments
            
        Returns:
            Service instance
            
        Raises:
            ValidationError: If service is not registered
            ServiceError: If service creation fails
        """
        if name not in self._services:
            raise ValidationError(
                f"Service '{name}' not registered",
                context={'registered_services': list(self._services.keys())}
            )
        
        try:
            service = self._services[name](*args, **kwargs)
            self.logger.info(f"Created service instance: {name}")
            return service
        except Exception as e:
            raise ServiceError(
                f"Failed to create service '{name}'",
                service_name=name,
                operation="create_instance",
                original_exception=e
            )
    
    def get_registered_services(self) -> List[str]:
        """Get list of registered service names."""
        return list(self._services.keys()) 