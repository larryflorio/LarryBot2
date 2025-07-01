from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict, Type
from larrybot.core.interfaces import ServiceInterface

class BaseService(ServiceInterface):
    """
    Base service class providing common functionality for all services.
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
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
    
    def _validate_input(self, data: Any, required_fields: List[str]) -> bool:
        """Validate input data has required fields."""
        if not isinstance(data, dict):
            return False
        
        for field in required_fields:
            if field not in data:
                return False
        
        return True
    
    def _handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """Handle errors consistently across services."""
        return {
            "success": False,
            "error": str(error),
            "context": context
        }
    
    def _create_success_response(self, data: Any, message: str = "") -> Dict[str, Any]:
        """Create a consistent success response."""
        return {
            "success": True,
            "data": data,
            "message": message
        }

class ServiceFactory:
    """
    Factory for creating service instances with dependency injection.
    """
    
    def __init__(self):
        self._services: Dict[str, Type[BaseService]] = {}
    
    def register_service(self, name: str, service_class: Type[BaseService]) -> None:
        """Register a service class."""
        self._services[name] = service_class
    
    def create_service(self, name: str, *args, **kwargs) -> BaseService:
        """Create a service instance."""
        if name not in self._services:
            raise ValueError(f"Service '{name}' not registered")
        
        return self._services[name](*args, **kwargs)
    
    def get_registered_services(self) -> List[str]:
        """Get list of registered service names."""
        return list(self._services.keys()) 