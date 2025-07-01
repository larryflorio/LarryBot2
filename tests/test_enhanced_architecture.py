"""
Tests for the enhanced architectural components.
Demonstrates testing best practices for the extensible design.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, User
from telegram.ext import ContextTypes

from larrybot.core.interfaces import PluginInterface, EventListener, CommandHandler
from larrybot.core.dependency_injection import DependencyContainer, ServiceLocator
from larrybot.core.plugin_manager import PluginManager, PluginMetadata
from larrybot.core.command_registry import CommandRegistry, CommandMetadata
from larrybot.core.event_bus import EventBus
from larrybot.core.middleware import Middleware, LoggingMiddleware, AuthorizationMiddleware, RateLimitingMiddleware
from larrybot.services.base_service import BaseService
from larrybot.utils.decorators import command_handler, event_listener, require_args, validate_user_id, async_retry, cache_result

# Concrete test implementation of BaseService
class ConcreteTestService(BaseService):
    """Concrete implementation of BaseService for testing."""
    
    async def execute(self, operation: str, data: dict) -> dict:
        """Test implementation of execute method."""
        if operation == "test":
            return self._create_success_response(data, "Test successful")
        else:
            return self._handle_error(ValueError(f"Unknown operation: {operation}"))

# Test fixtures
@pytest.fixture
def mock_update():
    """Create a mock Telegram Update."""
    update = Mock(spec=Update)
    update.message = Mock()
    update.message.reply_text = AsyncMock()
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 123456789
    return update

@pytest.fixture
def mock_context():
    """Create a mock Telegram Context."""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    return context

@pytest.fixture
def dependency_container():
    """Create a dependency container for testing."""
    container = DependencyContainer()
    container.register_singleton("event_bus", EventBus())
    container.register_singleton("command_registry", CommandRegistry())
    ServiceLocator.set_container(container)
    return container

@pytest.fixture
def event_bus():
    """Create an event bus for testing."""
    return EventBus()

@pytest.fixture
def command_registry():
    """Create a command registry for testing."""
    return CommandRegistry()

class TestDependencyInjection:
    """Test dependency injection functionality."""
    
    def test_register_and_get_singleton(self, dependency_container):
        """Test registering and retrieving singletons."""
        test_instance = {"test": "data"}
        dependency_container.register_singleton("test_service", test_instance)
        
        retrieved = dependency_container.get("test_service")
        assert retrieved == test_instance
    
    def test_register_and_get_factory(self, dependency_container):
        """Test registering and retrieving factory functions."""
        def create_test_instance():
            return {"created": "by_factory"}
        
        dependency_container.register_factory("test_factory", create_test_instance)
        
        retrieved = dependency_container.get("test_factory")
        assert retrieved == {"created": "by_factory"}
    
    def test_service_locator(self, dependency_container):
        """Test global service locator."""
        test_instance = {"test": "data"}
        dependency_container.register_singleton("test_service", test_instance)
        
        retrieved = ServiceLocator.get("test_service")
        assert retrieved == test_instance
    
    def test_service_locator_has(self, dependency_container):
        """Test checking if service exists."""
        dependency_container.register_singleton("test_service", {"test": "data"})
        
        assert ServiceLocator.has("test_service") is True
        assert ServiceLocator.has("nonexistent") is False

class TestPluginManager:
    """Test plugin manager functionality."""
    
    def test_register_plugin_metadata(self, dependency_container):
        """Test registering plugin metadata."""
        plugin_manager = PluginManager(dependency_container)
        
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Tester",
            dependencies=["event_bus"],
            enabled=True
        )
        
        plugin_manager.register_plugin_metadata("test_plugin", metadata)
        assert "test_plugin" in plugin_manager.metadata
    
    def test_check_dependencies(self, dependency_container):
        """Test dependency checking."""
        plugin_manager = PluginManager(dependency_container)
        
        # Test with satisfied dependencies
        assert plugin_manager._check_dependencies(["event_bus"]) is True
        
        # Test with unsatisfied dependencies
        assert plugin_manager._check_dependencies(["nonexistent"]) is False
    
    def test_enable_disable_plugin(self, dependency_container):
        """Test enabling and disabling plugins."""
        plugin_manager = PluginManager(dependency_container)
        
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Tester",
            dependencies=[],
            enabled=True
        )
        
        plugin_manager.register_plugin_metadata("test_plugin", metadata)
        
        # Test disable
        plugin_manager.disable_plugin("test_plugin")
        assert plugin_manager.metadata["test_plugin"].enabled is False
        
        # Test enable
        plugin_manager.enable_plugin("test_plugin")
        assert plugin_manager.metadata["test_plugin"].enabled is True

class TestCommandRegistry:
    """Test enhanced command registry functionality."""
    
    def test_register_with_metadata(self, command_registry):
        """Test registering commands with metadata."""
        async def test_handler(update, context):
            return "test"
        
        metadata = CommandMetadata(
            name="/test",
            description="Test command",
            usage="/test",
            category="test"
        )
        
        command_registry.register("/test", test_handler, metadata)
        
        assert command_registry.has_command("/test")
        assert command_registry.get_command_metadata("/test") == metadata
    
    def test_get_commands_by_category(self, command_registry):
        """Test getting commands by category."""
        async def test_handler(update, context):
            return "test"
        
        metadata1 = CommandMetadata(
            name="/test1",
            description="Test command 1",
            usage="/test1",
            category="test"
        )
        
        metadata2 = CommandMetadata(
            name="/test2",
            description="Test command 2",
            usage="/test2",
            category="other"
        )
        
        command_registry.register("/test1", test_handler, metadata1)
        command_registry.register("/test2", test_handler, metadata2)
        
        test_commands = command_registry.get_commands_by_category("test")
        assert "/test1" in test_commands
        assert "/test2" not in test_commands

class TestMiddleware:
    """Test middleware functionality."""
    
    @pytest.mark.asyncio
    async def test_logging_middleware(self, mock_update, mock_context):
        """Test logging middleware."""
        middleware = LoggingMiddleware()
        
        async def test_handler(update, context):
            return "success"
        
        result = await middleware.process(mock_update, mock_context, test_handler)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_authorization_middleware_success(self, mock_update, mock_context):
        """Test authorization middleware with authorized user."""
        middleware = AuthorizationMiddleware(allowed_user_id=123456789)
        
        async def test_handler(update, context):
            return "success"
        
        result = await middleware.process(mock_update, mock_context, test_handler)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_authorization_middleware_failure(self, mock_update, mock_context):
        """Test authorization middleware with unauthorized user."""
        middleware = AuthorizationMiddleware(allowed_user_id=999999999)
        
        async def test_handler(update, context):
            return "success"
        
        await middleware.process(mock_update, mock_context, test_handler)
        mock_update.message.reply_text.assert_called_with("You are not authorized to use this bot.")
    
    @pytest.mark.asyncio
    async def test_rate_limiting_middleware(self, mock_update, mock_context):
        """Test rate limiting middleware."""
        middleware = RateLimitingMiddleware(max_requests_per_minute=2)
        
        async def test_handler(update, context):
            return "success"
        
        # First two requests should succeed
        result1 = await middleware.process(mock_update, mock_context, test_handler)
        result2 = await middleware.process(mock_update, mock_context, test_handler)
        
        assert result1 == "success"
        assert result2 == "success"
        
        # Third request should be rate limited
        await middleware.process(mock_update, mock_context, test_handler)
        mock_update.message.reply_text.assert_called_with("Rate limit exceeded. Please wait before sending more commands.")

class TestBaseService:
    """Test base service functionality."""
    
    def test_create_success_response(self):
        """Test creating success responses."""
        service = ConcreteTestService()
        response = service._create_success_response({"data": "test"}, "Success message")
        
        assert response["success"] is True
        assert response["data"] == {"data": "test"}
        assert response["message"] == "Success message"
    
    def test_handle_error(self):
        """Test error handling."""
        service = ConcreteTestService()
        error = ValueError("Test error")
        response = service._handle_error(error, "Test context")
        
        assert response["success"] is False
        assert response["error"] == "Test error"
        assert response["context"] == "Test context"
    
    def test_validate_input(self):
        """Test input validation with enhanced error handling."""
        from larrybot.core.exceptions import ValidationError
        import pytest
        
        service = ConcreteTestService()
        
        # Valid input
        valid_data = {"field1": "value1", "field2": "value2"}
        assert service._validate_input(valid_data, ["field1", "field2"]) is True
        
        # Invalid input - missing field (should raise ValidationError)
        invalid_data = {"field1": "value1"}
        with pytest.raises(ValidationError) as exc_info:
            service._validate_input(invalid_data, ["field1", "field2"])
        assert "Missing required fields: field2" in str(exc_info.value)
        
        # Invalid input - not a dict (should raise ValidationError)
        with pytest.raises(ValidationError) as exc_info:
            service._validate_input("not a dict", ["field1"])
        assert "Input data must be a dictionary" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_method(self):
        """Test the execute method implementation."""
        service = ConcreteTestService()
        
        # Test successful operation
        result = await service.execute("test", {"test": "data"})
        assert result["success"] is True
        assert result["data"] == {"test": "data"}
        assert result["message"] == "Test successful"
        
        # Test error operation
        result = await service.execute("unknown", {"test": "data"})
        assert result["success"] is False
        assert "Unknown operation" in result["error"]

class TestDecorators:
    """Test utility decorators."""
    
    @pytest.mark.asyncio
    async def test_command_handler_decorator(self, mock_update, mock_context):
        """Test command handler decorator."""
        @command_handler("/test", "Test command", "Usage: /test", "test")
        async def test_handler(update, context):
            return "decorated"
        
        result = await test_handler(mock_update, mock_context)
        assert result == "decorated"
        assert hasattr(test_handler, '_command_metadata')
    
    @pytest.mark.asyncio
    async def test_require_args_decorator_success(self, mock_update, mock_context):
        """Test require args decorator with valid arguments."""
        @require_args(1, 3)
        async def test_handler(update, context):
            return "success"
        
        mock_context.args = ["arg1", "arg2"]
        result = await test_handler(mock_update, mock_context)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_require_args_decorator_failure(self, mock_update, mock_context):
        """Test require args decorator with insufficient arguments."""
        @require_args(2, 3)
        async def test_handler(update, context):
            return "success"
        
        mock_context.args = ["arg1"]
        await test_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_with("Usage: test_handler requires at least 2 argument(s)")
    
    @pytest.mark.asyncio
    async def test_validate_user_id_decorator_success(self, mock_update, mock_context):
        """Test user validation decorator with authorized user."""
        @validate_user_id(123456789)
        async def test_handler(update, context):
            return "success"
        
        result = await test_handler(mock_update, mock_context)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_validate_user_id_decorator_failure(self, mock_update, mock_context):
        """Test user validation decorator with unauthorized user."""
        @validate_user_id(999999999)
        async def test_handler(update, context):
            return "success"
        
        await test_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_with("You are not authorized to use this command.")
    
    @pytest.mark.asyncio
    async def test_async_retry_decorator_success(self):
        """Test async retry decorator with successful operation."""
        call_count = 0
        
        @async_retry(max_attempts=3, delay=0.1)
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_function()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_async_retry_decorator_retry(self):
        """Test async retry decorator with retries."""
        call_count = 0
        
        @async_retry(max_attempts=3, delay=0.1)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = await test_function()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_cache_result_decorator(self):
        """Test cache result decorator."""
        call_count = 0
        
        @cache_result(ttl_seconds=300)
        async def test_function(arg):
            nonlocal call_count
            call_count += 1
            return f"result_{arg}"
        
        # First call should execute the function
        result1 = await test_function("test")
        assert result1 == "result_test"
        assert call_count == 1
        
        # Second call should use cache
        result2 = await test_function("test")
        assert result2 == "result_test"
        assert call_count == 1  # Should not increment

class TestEventSystem:
    """Test event-driven communication."""
    
    def test_event_listener_decorator(self, event_bus):
        """Test event listener decorator."""
        events_received = []
        
        @event_listener("test_event")
        def test_listener(data):
            events_received.append(data)
        
        # Register the listener
        event_bus.subscribe("test_event", test_listener)
        
        # Emit event
        event_bus.emit("test_event", {"test": "data"})
        
        assert len(events_received) == 1
        assert events_received[0] == {"test": "data"}
        assert hasattr(test_listener, '_event_name')
        assert test_listener._event_name == "test_event"

class TestIntegration:
    """Integration tests for the enhanced architecture."""
    
    @pytest.mark.asyncio
    async def test_full_command_execution_flow(self, mock_update, mock_context, dependency_container):
        """Test complete command execution flow with middleware."""
        command_registry = dependency_container.get("command_registry")
        event_bus = dependency_container.get("event_bus")
        
        # Add middleware
        command_registry.add_middleware(LoggingMiddleware())
        command_registry.add_middleware(AuthorizationMiddleware(allowed_user_id=123456789))
        
        # Register command
        async def test_handler(update, context):
            await update.message.reply_text("Command executed successfully")
            return "success"
        
        command_registry.register("/test", test_handler)
        
        # Execute command
        result = await command_registry.dispatch("/test", mock_update, mock_context)
        
        assert result == "success"
        mock_update.message.reply_text.assert_called_with("Command executed successfully")
    
    def test_plugin_metadata_integration(self, dependency_container):
        """Test plugin metadata integration."""
        plugin_manager = PluginManager(dependency_container)
        
        # Register plugin metadata
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Tester",
            dependencies=["event_bus"],
            enabled=True
        )
        
        plugin_manager.register_plugin_metadata("test_plugin", metadata)
        
        # Get plugin info
        plugin_info = plugin_manager.get_plugin_info()
        assert len(plugin_info) == 1
        assert plugin_info[0].name == "test_plugin"
        
        # Get enabled plugins
        enabled_plugins = plugin_manager.get_enabled_plugins()
        assert "test_plugin" in enabled_plugins

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 