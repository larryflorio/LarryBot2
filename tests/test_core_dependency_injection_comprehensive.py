"""
Comprehensive Dependency Injection Testing Suite

This test suite provides thorough testing for the DependencyContainer and ServiceLocator
components that currently have 67% coverage. It covers factory patterns, type resolution,
circular dependencies, and advanced scenarios critical for production deployment.
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, Optional

from larrybot.core.dependency_injection import DependencyContainer, ServiceLocator
from larrybot.core.interfaces import PluginInterface, EventListener, CommandHandler


class TestDependencyContainerRegistration:
    """Test dependency registration functionality."""

    @pytest.fixture
    def container(self):
        """Create a fresh dependency container for each test."""
        return DependencyContainer()

    def test_register_singleton_by_name(self, container):
        """Test registering singleton instances by name."""
        test_instance = Mock()
        
        container.register("test_service", test_instance)
        
        # Should retrieve the same instance
        retrieved = container.get("test_service")
        assert retrieved is test_instance

    def test_register_singleton_by_type(self, container):
        """Test registering singleton instances by type."""
        class TestService:
            def __init__(self):
                self.value = "test"
        
        test_instance = TestService()
        container.register(TestService, test_instance)
        
        # Should retrieve by lowercase type name
        retrieved = container.get("testservice")
        assert retrieved is test_instance
        assert retrieved.value == "test"

    def test_register_type_for_auto_instantiation(self, container):
        """Test registering types for automatic instantiation."""
        class AutoService:
            def __init__(self):
                self.initialized = True
        
        container.register(AutoService)
        
        # Should auto-instantiate when requested
        instance = container.get("autoservice")
        assert isinstance(instance, AutoService)
        assert instance.initialized is True

    def test_register_invalid_key_type(self, container):
        """Test that invalid key types raise ValueError."""
        with pytest.raises(ValueError, match="Invalid key type"):
            container.register(123, "invalid")

    def test_register_factory_function(self, container):
        """Test registering factory functions."""
        def create_service():
            service = Mock()
            service.factory_created = True
            return service
        
        container.register_factory("factory_service", create_service)
        
        # Should create instance using factory
        instance = container.get("factory_service")
        assert instance.factory_created is True

    def test_register_type_explicitly(self, container):
        """Test explicit type registration."""
        class ExplicitService:
            def __init__(self):
                self.explicit = True
        
        container.register_type("explicit", ExplicitService)
        
        instance = container.get("explicit")
        assert isinstance(instance, ExplicitService)
        assert instance.explicit is True


class TestDependencyContainerRetrieval:
    """Test dependency retrieval functionality."""

    @pytest.fixture
    def populated_container(self):
        """Create a container with various registered dependencies."""
        container = DependencyContainer()
        
        # Singleton
        singleton_service = Mock()
        singleton_service.type = "singleton"
        container.register_singleton("singleton", singleton_service)
        
        # Factory
        def factory_function():
            factory_service = Mock()
            factory_service.type = "factory"
            factory_service.call_count = getattr(factory_function, 'call_count', 0) + 1
            factory_function.call_count = factory_service.call_count
            return factory_service
        
        container.register_factory("factory", factory_function)
        
        # Type
        class TypeService:
            def __init__(self):
                self.type = "type"
        
        container.register_type("type_service", TypeService)
        
        return container

    def test_get_singleton_always_returns_same_instance(self, populated_container):
        """Test that singletons always return the same instance."""
        instance1 = populated_container.get("singleton")
        instance2 = populated_container.get("singleton")
        
        assert instance1 is instance2
        assert instance1.type == "singleton"

    def test_get_factory_creates_and_caches_instance(self, populated_container):
        """Test that factories create instances and cache them as singletons."""
        instance1 = populated_container.get("factory")
        instance2 = populated_container.get("factory")
        
        # Should be the same instance (cached after first creation)
        assert instance1 is instance2
        assert instance1.type == "factory"
        assert instance1.call_count == 1  # Factory called only once

    def test_get_type_creates_and_caches_instance(self, populated_container):
        """Test that types are instantiated and cached."""
        instance1 = populated_container.get("type_service")
        instance2 = populated_container.get("type_service")
        
        # Should be the same instance (cached after first creation)
        assert instance1 is instance2
        assert instance1.type == "type"

    def test_get_nonexistent_dependency_raises_keyerror(self, populated_container):
        """Test that requesting nonexistent dependency raises KeyError."""
        with pytest.raises(KeyError, match="Dependency 'nonexistent' not found"):
            populated_container.get("nonexistent")

    def test_has_dependency_detection(self, populated_container):
        """Test dependency existence detection."""
        assert populated_container.has("singleton") is True
        assert populated_container.has("factory") is True
        assert populated_container.has("type_service") is True
        assert populated_container.has("nonexistent") is False


class TestDependencyContainerAdvancedScenarios:
    """Test advanced dependency injection scenarios."""

    @pytest.fixture
    def container(self):
        """Create a fresh dependency container."""
        return DependencyContainer()

    def test_overriding_dependencies(self, container):
        """Test that dependencies can be overridden."""
        # Register initial dependency
        initial_service = Mock()
        initial_service.version = "v1"
        container.register_singleton("service", initial_service)
        
        # Override with new dependency
        updated_service = Mock()
        updated_service.version = "v2"
        container.register_singleton("service", updated_service)
        
        # Should return the updated version
        retrieved = container.get("service")
        assert retrieved.version == "v2"

    def test_factory_with_dependencies(self, container):
        """Test factory functions that depend on other services."""
        # Register base dependency
        base_service = Mock()
        base_service.name = "base"
        container.register_singleton("base", base_service)
        
        # Register factory that uses base service
        def create_dependent_service():
            base = container.get("base")
            dependent = Mock()
            dependent.base = base
            return dependent
        
        container.register_factory("dependent", create_dependent_service)
        
        # Factory should access base service
        dependent = container.get("dependent")
        assert dependent.base is base_service

    def test_type_with_constructor_parameters(self, container):
        """Test types that require constructor parameters."""
        class ParameterizedService:
            def __init__(self, config=None):
                self.config = config or {"default": True}
        
        # Register without parameters (should use defaults)
        container.register_type("parameterized", ParameterizedService)
        
        instance = container.get("parameterized")
        assert isinstance(instance, ParameterizedService)
        assert instance.config["default"] is True

    def test_complex_dependency_chain(self, container):
        """Test complex dependency chains."""
        # Register chain: A -> B -> C
        class ServiceC:
            def __init__(self):
                self.level = "C"
        
        class ServiceB:
            def __init__(self):
                self.level = "B"
                self.c = None
        
        class ServiceA:
            def __init__(self):
                self.level = "A"
                self.b = None
        
        # Register services
        container.register_type("service_c", ServiceC)
        
        def create_service_b():
            b = ServiceB()
            b.c = container.get("service_c")
            return b
        container.register_factory("service_b", create_service_b)
        
        def create_service_a():
            a = ServiceA()
            a.b = container.get("service_b")
            return a
        container.register_factory("service_a", create_service_a)
        
        # Resolve chain
        service_a = container.get("service_a")
        assert service_a.level == "A"
        assert service_a.b.level == "B"
        assert service_a.b.c.level == "C"


class TestDependencyContainerErrorHandling:
    """Test error handling in dependency injection."""

    @pytest.fixture
    def container(self):
        """Create a dependency container for error testing."""
        return DependencyContainer()

    def test_factory_function_exception(self, container):
        """Test handling of exceptions in factory functions."""
        def failing_factory():
            raise ValueError("Factory failed")
        
        container.register_factory("failing", failing_factory)
        
        # Should propagate the exception
        with pytest.raises(ValueError, match="Factory failed"):
            container.get("failing")

    def test_type_instantiation_exception(self, container):
        """Test handling of exceptions during type instantiation."""
        class FailingService:
            def __init__(self):
                raise RuntimeError("Instantiation failed")
        
        container.register_type("failing", FailingService)
        
        # Should propagate the exception
        with pytest.raises(RuntimeError, match="Instantiation failed"):
            container.get("failing")

    def test_circular_dependency_detection(self, container):
        """Test detection of circular dependencies."""
        def create_service_a():
            return container.get("service_b")  # Circular reference
        
        def create_service_b():
            return container.get("service_a")  # Circular reference
        
        container.register_factory("service_a", create_service_a)
        container.register_factory("service_b", create_service_b)
        
        # Should eventually hit recursion limit or timeout
        with pytest.raises(RecursionError):
            container.get("service_a")

    def test_none_value_registration(self, container):
        """Test registration and retrieval of None values."""
        container.register_singleton("none_service", None)
        
        # Should be able to retrieve None
        assert container.get("none_service") is None
        assert container.has("none_service") is True

    def test_registration_with_none_key(self, container):
        """Test that None keys are handled appropriately."""
        with pytest.raises((ValueError, TypeError)):
            container.register(None, "value")


class TestServiceLocator:
    """Test ServiceLocator global service access."""

    def test_service_locator_initialization(self):
        """Test ServiceLocator initialization."""
        # Should start with no container
        assert ServiceLocator._container is None

    def test_set_and_get_container(self):
        """Test setting and using container in ServiceLocator."""
        container = DependencyContainer()
        test_service = Mock()
        container.register_singleton("test", test_service)
        
        ServiceLocator.set_container(container)
        
        # Should be able to access service through locator
        retrieved = ServiceLocator.get("test")
        assert retrieved is test_service

    def test_service_locator_without_container(self):
        """Test ServiceLocator behavior without initialized container."""
        # Reset container
        ServiceLocator._container = None
        
        with pytest.raises(RuntimeError, match="ServiceLocator not initialized"):
            ServiceLocator.get("any_service")

    def test_service_locator_has_without_container(self):
        """Test ServiceLocator.has() without initialized container."""
        # Reset container
        ServiceLocator._container = None
        
        assert ServiceLocator.has("any_service") is False

    def test_service_locator_multiple_containers(self):
        """Test switching between different containers."""
        # First container
        container1 = DependencyContainer()
        service1 = Mock()
        service1.name = "service1"
        container1.register_singleton("service", service1)
        
        # Second container
        container2 = DependencyContainer()
        service2 = Mock()
        service2.name = "service2"
        container2.register_singleton("service", service2)
        
        # Switch containers
        ServiceLocator.set_container(container1)
        assert ServiceLocator.get("service").name == "service1"
        
        ServiceLocator.set_container(container2)
        assert ServiceLocator.get("service").name == "service2"


class TestDependencyInjectionIntegration:
    """Test integration scenarios with actual LarryBot components."""

    @pytest.fixture
    def integration_container(self):
        """Create a container with typical LarryBot services."""
        container = DependencyContainer()
        
        # Mock typical services
        mock_config = Mock()
        mock_config.DATABASE_PATH = ":memory:"
        mock_config.TELEGRAM_BOT_TOKEN = "test_token"
        container.register_singleton("config", mock_config)
        
        mock_event_bus = Mock()
        container.register_singleton("event_bus", mock_event_bus)
        
        mock_command_registry = Mock()
        container.register_singleton("command_registry", mock_command_registry)
        
        return container

    def test_typical_service_resolution(self, integration_container):
        """Test resolving typical LarryBot services."""
        config = integration_container.get("config")
        event_bus = integration_container.get("event_bus")
        command_registry = integration_container.get("command_registry")
        
        assert config.DATABASE_PATH == ":memory:"
        assert event_bus is not None
        assert command_registry is not None

    def test_service_composition(self, integration_container):
        """Test composing services that depend on each other."""
        # Add a service that depends on config
        def create_database_service():
            config = integration_container.get("config")
            db_service = Mock()
            db_service.database_path = config.DATABASE_PATH
            return db_service
        
        integration_container.register_factory("database", create_database_service)
        
        db_service = integration_container.get("database")
        assert db_service.database_path == ":memory:"

    def test_plugin_manager_integration(self, integration_container):
        """Test integration with plugin manager pattern."""
        # Mock plugin manager that uses other services
        def create_plugin_manager():
            event_bus = integration_container.get("event_bus")
            command_registry = integration_container.get("command_registry")
            
            plugin_manager = Mock()
            plugin_manager.event_bus = event_bus
            plugin_manager.command_registry = command_registry
            plugin_manager.plugins = []
            return plugin_manager
        
        integration_container.register_factory("plugin_manager", create_plugin_manager)
        
        plugin_manager = integration_container.get("plugin_manager")
        assert plugin_manager.event_bus is integration_container.get("event_bus")
        assert plugin_manager.command_registry is integration_container.get("command_registry")


class TestDependencyInjectionPerformance:
    """Test performance characteristics of dependency injection."""

    def test_service_resolution_performance(self):
        """Test service resolution performance under load."""
        import time
        
        container = DependencyContainer()
        
        # Register many services
        for i in range(100):
            service = Mock()
            service.id = i
            container.register_singleton(f"service_{i}", service)
        
        # Time service resolution
        start_time = time.time()
        for i in range(100):
            for j in range(10):  # 10 resolutions per service
                container.get(f"service_{i}")
        end_time = time.time()
        
        # Should complete 1000 resolutions quickly (under 1 second)
        resolution_time = end_time - start_time
        assert resolution_time < 1.0

    def test_factory_caching_performance(self):
        """Test that factory caching improves performance."""
        import time
        
        container = DependencyContainer()
        
        # Expensive factory function
        def expensive_factory():
            time.sleep(0.01)  # Simulate expensive creation
            return Mock()
        
        container.register_factory("expensive", expensive_factory)
        
        # First call should be slow
        start_time = time.time()
        first_instance = container.get("expensive")
        first_call_time = time.time() - start_time
        
        # Subsequent calls should be fast (cached)
        start_time = time.time()
        second_instance = container.get("expensive")
        second_call_time = time.time() - start_time
        
        assert first_instance is second_instance  # Same instance
        assert second_call_time < first_call_time / 2  # Much faster

    def test_memory_usage_efficiency(self):
        """Test memory efficiency of dependency container."""
        import gc
        
        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Create container with many dependencies
        container = DependencyContainer()
        for i in range(1000):
            container.register_singleton(f"service_{i}", Mock())
        
        # Resolve all dependencies
        for i in range(1000):
            container.get(f"service_{i}")
        
        # Check memory usage
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be reasonable
        growth_ratio = final_objects / initial_objects
        assert growth_ratio < 2.0  # Less than 100% increase


class TestDependencyInjectionEdgeCases:
    """Test edge cases and corner scenarios."""

    @pytest.fixture
    def container(self):
        """Create a dependency container for edge case testing."""
        return DependencyContainer()

    def test_empty_string_keys(self, container):
        """Test handling of empty string keys."""
        test_service = Mock()
        container.register_singleton("", test_service)
        
        # Should be able to register and retrieve empty string key
        assert container.get("") is test_service
        assert container.has("") is True

    def test_unicode_keys(self, container):
        """Test handling of unicode keys."""
        test_service = Mock()
        unicode_key = "тест_сервис_🚀"
        
        container.register_singleton(unicode_key, test_service)
        
        assert container.get(unicode_key) is test_service
        assert container.has(unicode_key) is True

    def test_case_sensitivity(self, container):
        """Test case sensitivity of keys."""
        service1 = Mock()
        service2 = Mock()
        
        container.register_singleton("Service", service1)
        container.register_singleton("service", service2)
        
        # Should maintain case sensitivity
        assert container.get("Service") is service1
        assert container.get("service") is service2

    def test_type_registration_edge_cases(self, container):
        """Test edge cases in type registration."""
        # Abstract class
        from abc import ABC, abstractmethod
        
        class AbstractService(ABC):
            @abstractmethod
            def method(self):
                pass
        
        # Should register but fail on instantiation
        container.register_type("abstract", AbstractService)
        
        with pytest.raises(TypeError):
            container.get("abstract")

    def test_factory_returning_none(self, container):
        """Test factory functions that return None."""
        def none_factory():
            return None
        
        container.register_factory("none_factory", none_factory)
        
        # Should cache and return None
        assert container.get("none_factory") is None
        assert container.has("none_factory") is True

    def test_very_long_keys(self, container):
        """Test handling of very long keys."""
        long_key = "a" * 10000  # Very long key
        test_service = Mock()
        
        container.register_singleton(long_key, test_service)
        
        assert container.get(long_key) is test_service 