#!/usr/bin/env python3
"""
Quick test script to verify command registration and bot functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from larrybot.core.event_bus import EventBus
from larrybot.core.plugin_manager import PluginManager
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.dependency_injection import DependencyContainer
from larrybot.config.loader import Config
from larrybot.storage.db import init_db
from larrybot.handlers.bot import TelegramBotHandler

def test_command_registration():
    """Test that all commands are properly registered, including core commands."""
    print("🔍 Testing Command Registration...")
    
    # Initialize components
    config = Config()
    config.validate()
    init_db()
    
    container = DependencyContainer()
    plugin_manager = PluginManager(container)
    plugin_manager.discover_and_load()
    
    event_bus = EventBus()
    command_registry = CommandRegistry()
    
    # Register plugins
    plugin_manager.register_plugins(event_bus=event_bus, command_registry=command_registry)
    
    # Instantiate TelegramBotHandler to register core commands
    bot_handler = TelegramBotHandler(config, command_registry)
    
    # Get all registered commands
    commands = list(command_registry._commands.keys())
    metadata = command_registry._metadata
    
    print(f"\n✅ Found {len(commands)} registered commands:")
    
    # Group by category
    categories = {}
    for cmd in commands:
        meta = metadata.get(cmd)
        if meta:
            category = meta.category
            if category not in categories:
                categories[category] = []
            categories[category].append((cmd, meta))
    
    # Display commands by category
    for category, cmd_list in sorted(categories.items()):
        print(f"\n📂 {category.upper()}:")
        for cmd, meta in sorted(cmd_list):
            print(f"  • {cmd} - {meta.description}")
    
    # Check for any issues
    print(f"\n🔧 Command Registry Status:")
    print(f"  • Total Commands: {len(commands)}")
    print(f"  • Categories: {len(categories)}")
    print(f"  • Commands with Metadata: {len(metadata)}")
    
    # Verify core commands exist
    core_commands = ['/start', '/help', '/add', '/list', '/done', '/edit', '/remove']
    missing_commands = [cmd for cmd in core_commands if cmd not in commands]
    
    if missing_commands:
        print(f"\n❌ Missing Core Commands: {missing_commands}")
        assert False, f"Missing core commands: {missing_commands}"
    else:
        print(f"\n✅ All Core Commands Present")
        assert len(commands) > 0, "No commands registered"
    
    return True  # Explicitly return success status

def test_plugin_loading():
    """Test that all plugins are loaded properly."""
    print("\n🔌 Testing Plugin Loading...")
    
    container = DependencyContainer()
    plugin_manager = PluginManager(container)
    plugin_manager.discover_and_load()
    
    plugins = plugin_manager.get_loaded_plugins()
    enabled_plugins = plugin_manager.get_enabled_plugins()
    
    print(f"✅ Loaded {len(plugins)} plugins:")
    for plugin in plugins:
        status = "✅" if plugin['enabled'] else "❌"
        print(f"  {status} {plugin['name']} v{plugin['version']} - {plugin['description']}")
    
    print(f"\n🔧 Plugin Status:")
    print(f"  • Total Plugins: {len(plugins)}")
    print(f"  • Enabled Plugins: {len(enabled_plugins)}")
    
    assert len(plugins) > 0, "No plugins loaded"
    
    return True  # Explicitly return success status

if __name__ == "__main__":
    print("🚀 LarryBot2 Command Verification Test")
    print("=" * 50)
    
    try:
        cmd_success = test_command_registration()
        plugin_success = test_plugin_loading()
        
        print("\n" + "=" * 50)
        if cmd_success and plugin_success:
            print("✅ All tests passed! Commands are ready for UX improvements.")
        else:
            print("❌ Some tests failed. Please check the issues above.")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc() 