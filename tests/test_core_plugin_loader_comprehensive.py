"""
Comprehensive Plugin Loader Testing Suite

This test suite provides thorough testing for the PluginLoader component,
focusing on actual functionality: plugin discovery and registration.
Tests real implementation methods only.
"""

import pytest
import sys
import os
import tempfile
import importlib
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from larrybot.core.plugin_loader import PluginLoader
from larrybot.core.event_bus import EventBus
from larrybot.core.command_registry import CommandRegistry


class TestPluginLoaderDiscovery:
    """Test plugin discovery functionality - testing actual discover_and_load() method."""

    @pytest.fixture
    def plugin_loader(self):
        """Create a fresh plugin loader for each test."""
        return PluginLoader()

    @pytest.fixture
    def temp_plugin_dir(self):
        """Create a temporary directory with test plugins."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create __init__.py to make it a package
            (temp_path / "__init__.py").write_text("")
            
            # Create a valid plugin
            valid_plugin = '''
def register(event_bus, command_registry):
    """Register plugin commands and events."""
    def test_handler(update, context):
        return "test response"
    
    command_registry.register("/test_plugin", test_handler)
'''
            (temp_path / "valid_plugin.py").write_text(valid_plugin)
            
            # Create an invalid plugin (syntax error)
            invalid_plugin = '''
def register(event_bus, command_registry):
    """Invalid plugin with syntax error."""
    invalid syntax here
'''
            (temp_path / "invalid_plugin.py").write_text(invalid_plugin)
            
            # Create a plugin without register function
            no_register_plugin = '''
def some_function():
    pass
'''
            (temp_path / "no_register_plugin.py").write_text(no_register_plugin)
            
            yield temp_path

    def test_discover_plugins_in_default_directory(self, plugin_loader):
        """Test discovering plugins in the default larrybot.plugins directory."""
        plugin_loader.discover_and_load()
        
        # Should discover real plugins from larrybot.plugins
        assert len(plugin_loader.plugins) > 0
        
        # Check that known plugins are discovered
        plugin_names = [p.__name__ for p in plugin_loader.plugins]
        assert "larrybot.plugins.tasks" in plugin_names
        assert "larrybot.plugins.hello" in plugin_names

    def test_discover_plugins_in_custom_directory(self, plugin_loader, temp_plugin_dir):
        """Test discovering plugins in a custom directory."""
        # Add temp directory to Python path
        sys.path.insert(0, str(temp_plugin_dir.parent))
        
        try:
            # Create new loader with custom package
            custom_loader = PluginLoader(temp_plugin_dir.name)
            custom_loader.discover_and_load()
            
            # Should discover the valid plugin only (import errors are silent)
            assert len(custom_loader.plugins) >= 1
            plugin_names = [p.__name__ for p in custom_loader.plugins]
            assert any("valid_plugin" in name for name in plugin_names)
        finally:
            sys.path.remove(str(temp_plugin_dir.parent))

    def test_discover_plugins_handles_import_errors(self, plugin_loader, temp_plugin_dir):
        """Test that plugin discovery handles import errors gracefully."""
        sys.path.insert(0, str(temp_plugin_dir.parent))
        
        try:
            custom_loader = PluginLoader(temp_plugin_dir.name)
            
            # Should not raise exception despite invalid plugins
            custom_loader.discover_and_load()
            
            # Should have loaded at least the valid plugin
            assert len(custom_loader.plugins) >= 1
        finally:
            sys.path.remove(str(temp_plugin_dir.parent))

    def test_discover_plugins_nonexistent_directory(self, plugin_loader):
        """Test discovering plugins when directory doesn't exist."""
        nonexistent_loader = PluginLoader('nonexistent_package')
        
        # Should raise ModuleNotFoundError for nonexistent package (actual behavior)
        with pytest.raises(ModuleNotFoundError):
            nonexistent_loader.discover_and_load()

    def test_plugin_loading_order(self, plugin_loader):
        """Test that plugins are loaded in a consistent order."""
        # Load plugins twice
        plugin_loader.discover_and_load()
        first_load_names = [p.__name__ for p in plugin_loader.plugins]
        
        plugin_loader.plugins = []  # Reset
        plugin_loader.discover_and_load()
        second_load_names = [p.__name__ for p in plugin_loader.plugins]
        
        # Order should be consistent
        assert first_load_names == second_load_names


class TestPluginLoaderRegistration:
    """Test plugin registration functionality - testing actual register_plugins() method."""

    @pytest.fixture
    def plugin_loader(self):
        """Create a plugin loader with mock plugins."""
        loader = PluginLoader()
        
        # Create mock plugins - but make register() not raise by default
        valid_plugin = MagicMock()
        valid_plugin.__name__ = "test.valid_plugin"
        valid_plugin.register = MagicMock()
        
        plugin_without_register = MagicMock()
        plugin_without_register.__name__ = "test.no_register"
        # This plugin simply doesn't have a register attribute
        if hasattr(plugin_without_register, 'register'):
            delattr(plugin_without_register, 'register')
        
        loader.plugins = [valid_plugin, plugin_without_register]
        return loader

    @pytest.fixture
    def plugin_loader_with_failing_plugin(self):
        """Create a plugin loader with a failing plugin for specific tests."""
        loader = PluginLoader()
        
        valid_plugin = MagicMock()
        valid_plugin.__name__ = "test.valid_plugin"
        valid_plugin.register = MagicMock()
        
        failing_plugin = MagicMock()
        failing_plugin.__name__ = "test.failing_plugin"
        failing_plugin.register = MagicMock(side_effect=Exception("Registration failed"))
        
        loader.plugins = [valid_plugin, failing_plugin]
        return loader

    @pytest.fixture
    def event_bus(self):
        """Create a mock event bus."""
        return Mock(spec=EventBus)

    @pytest.fixture
    def command_registry(self):
        """Create a mock command registry."""
        return Mock(spec=CommandRegistry)

    def test_register_valid_plugins(self, plugin_loader, event_bus, command_registry):
        """Test registering valid plugins with real register_plugins() method."""
        plugin_loader.register_plugins(event_bus, command_registry)
        
        # Valid plugin should have register called
        valid_plugin = plugin_loader.plugins[0]
        valid_plugin.register.assert_called_once_with(event_bus, command_registry)

    def test_skip_plugins_without_register_function(self, plugin_loader, event_bus, command_registry):
        """Test that plugins without register function are skipped."""
        plugin_loader.register_plugins(event_bus, command_registry)
        
        # Should not raise exception for plugin without register
        # Only valid plugin should have register called
        valid_plugin = plugin_loader.plugins[0]
        valid_plugin.register.assert_called_once()

    def test_handle_plugin_registration_failures(self, plugin_loader_with_failing_plugin, event_bus, command_registry):
        """Test handling of plugin registration failures."""
        # The implementation now handles exceptions gracefully and logs them
        # Should not raise exception but should continue with other plugins
        plugin_loader_with_failing_plugin.register_plugins(event_bus, command_registry)
        
        # Valid plugin should still be registered despite failing plugin
        valid_plugin = plugin_loader_with_failing_plugin.plugins[0]
        valid_plugin.register.assert_called_once_with(event_bus, command_registry)

    def test_register_plugins_with_none_event_bus(self, plugin_loader, command_registry):
        """Test registration with None event_bus."""
        plugin_loader.register_plugins(None, command_registry)
        
        valid_plugin = plugin_loader.plugins[0]
        valid_plugin.register.assert_called_once_with(None, command_registry)

    def test_register_plugins_with_none_command_registry(self, plugin_loader, event_bus):
        """Test registration with None command_registry."""
        plugin_loader.register_plugins(event_bus, None)
        
        valid_plugin = plugin_loader.plugins[0]
        valid_plugin.register.assert_called_once_with(event_bus, None)

    def test_register_plugins_empty_plugin_list(self, event_bus, command_registry):
        """Test registration with empty plugin list."""
        empty_loader = PluginLoader()
        empty_loader.plugins = []
        
        # Should not raise exception
        empty_loader.register_plugins(event_bus, command_registry)


class TestPluginLoaderIntegration:
    """Test integration with real plugins."""

    def test_integration_with_real_plugins(self):
        """Test plugin loader works with actual plugins from codebase."""
        loader = PluginLoader('larrybot.plugins')
        loader.discover_and_load()
        
        # Should find real plugins
        assert len(loader.plugins) > 0
        
        # Create mock registry for testing registration
        mock_registry = Mock()
        mock_event_bus = Mock()
        
        # Should not raise exception when registering real plugins
        loader.register_plugins(mock_event_bus, mock_registry)
        
        # At least one plugin should have register function
        real_plugins_with_register = [
            p for p in loader.plugins 
            if hasattr(p, 'register')
        ]
        assert len(real_plugins_with_register) > 0

    def test_plugin_discovery_performance(self):
        """Test that plugin discovery is reasonably fast."""
        import time
        
        loader = PluginLoader('larrybot.plugins')
        
        start_time = time.time()
        loader.discover_and_load()
        end_time = time.time()
        
        discovery_time = end_time - start_time
        
        # Should discover plugins in reasonable time (less than 1 second)
        assert discovery_time < 1.0
        
        # Should have discovered plugins
        assert len(loader.plugins) > 0 