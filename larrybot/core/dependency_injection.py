from typing import Dict, Any, Type, Optional, Callable, Union
from larrybot.core.interfaces import PluginInterface, EventListener, CommandHandler
from larrybot.nlp.intent_recognizer import IntentRecognizer
from larrybot.nlp.entity_extractor import EntityExtractor
from larrybot.nlp.sentiment_analyzer import SentimentAnalyzer


class DependencyContainer:
    """
    Simple dependency injection container for managing component dependencies.
    Supports singleton and factory patterns.
    """

    def __init__(self):
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._types: Dict[str, Type] = {}

    def register(self, key: Union[str, Type], value: Any=None) ->None:
        """
        Convenient method for registering dependencies.
        
        Usage patterns:
        - register("service_name", instance) - Register singleton by name
        - register(MyClass, instance) - Register singleton by type
        - register(MyClass) - Register type for auto-instantiation
        """
        if isinstance(key, str):
            self.register_singleton(key, value)
        elif isinstance(key, type):
            if value is not None:
                type_name = key.__name__.lower()
                self.register_singleton(type_name, value)
            else:
                type_name = key.__name__.lower()
                self.register_type(type_name, key)
        else:
            raise ValueError(
                f'Invalid key type: {type(key)}. Expected str or type.')

    def register_singleton(self, name: str, instance: Any) ->None:
        """Register a singleton instance."""
        self._singletons[name] = instance

    def register_factory(self, name: str, factory: Callable) ->None:
        """Register a factory function for creating instances."""
        self._factories[name] = factory

    def register_type(self, name: str, type_class: Type) ->None:
        """Register a type for automatic instantiation."""
        self._types[name] = type_class

    def get(self, name: str) ->Any:
        """Get a dependency by name."""
        if name in self._singletons:
            return self._singletons[name]
        if name in self._factories:
            instance = self._factories[name]()
            self._singletons[name] = instance
            return instance
        if name in self._types:
            instance = self._types[name]()
            self._singletons[name] = instance
            return instance
        raise KeyError(f"Dependency '{name}' not found")

    def has(self, name: str) ->bool:
        """Check if a dependency is registered."""
        return (name in self._singletons or name in self._factories or name in
            self._types)


class ServiceLocator:
    """
    Global service locator for accessing dependencies throughout the application.
    """
    _container: Optional[DependencyContainer] = None

    @classmethod
    def set_container(cls, container: DependencyContainer) ->None:
        """Set the global dependency container."""
        cls._container = container

    @classmethod
    def get(cls, name: str) ->Any:
        """Get a dependency from the global container."""
        if cls._container is None:
            raise RuntimeError(
                'ServiceLocator not initialized. Call set_container() first.')
        return cls._container.get(name)

    @classmethod
    def has(cls, name: str) ->bool:
        """Check if a dependency is available."""
        if cls._container is None:
            return False
        return cls._container.has(name)


def register_nlp_services(container: DependencyContainer):
    """Register NLP services for intent, entity, and sentiment analysis."""
    container.register_singleton('intent_recognizer', IntentRecognizer())
    container.register_singleton('entity_extractor', EntityExtractor())
    container.register_singleton('sentiment_analyzer', SentimentAnalyzer())
