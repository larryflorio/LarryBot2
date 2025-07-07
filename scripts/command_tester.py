#!/usr/bin/env python3
"""
Simple Telegram Command Tester
Tests key commands for datetime-related issues after refactoring
"""

import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from larrybot.config.loader import Config
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.core.plugin_manager import PluginManager
from larrybot.core.dependency_injection import DependencyContainer
from larrybot.storage.db import init_db

async def test_command(command_name, args=None):
    """Test a single command and return results."""
    if args is None:
        args = []
    
    print(f"🧪 Testing: {command_name} {' '.join(args)}")
    
    try:
        # Setup
        config = Config()
        init_db()
        
        container = DependencyContainer()
        plugin_manager = PluginManager(container)
        plugin_manager.discover_and_load()
        
        event_bus = EventBus()
        registry = CommandRegistry()
        plugin_manager.register_plugins(event_bus=event_bus, command_registry=registry)
        
        # Create mock update and context
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = config.ALLOWED_TELEGRAM_USER_ID
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = MagicMock()
        mock_context.args = args
        
        # Get command handler
        command_func = registry._commands.get(command_name)
        if not command_func:
            print(f"❌ Command {command_name} not found")
            return False
        
        # Execute command
        if asyncio.iscoroutinefunction(command_func):
            await command_func(mock_update, mock_context)
        else:
            command_func(mock_update, mock_context)
        
        # Check if response was sent
        if mock_update.message.reply_text.called:
            response = mock_update.message.reply_text.call_args[0][0]
            print(f"✅ Success: {command_name}")
            print(f"   Response: {response[:100]}...")
            return True
        else:
            print(f"⚠️  No response from {command_name}")
            return False
            
    except Exception as e:
        print(f"❌ Error in {command_name}: {e}")
        return False

async def main():
    """Test key commands for datetime issues."""
    print("🤖 Testing Key Telegram Commands for Datetime Issues")
    print("=" * 60)
    
    # Test commands that are likely to use datetime
    test_commands = [
        ("/add", ["Test task with datetime"]),
        ("/addtask", ["Test advanced task", "high", "work", "tomorrow"]),
        ("/due", ["1", "next week"]),
        ("/today", []),
        ("/overdue", []),
        ("/week", []),
        ("/analytics", []),
        ("/time_start", ["1"]),
        ("/time_stop", ["1"]),
        ("/time_entry", ["1", "120", "Test entry"]),
        ("/time_summary", ["1"]),
        ("/addreminder", ["Test reminder", "tomorrow 9am"]),
        ("/reminders", []),
        ("/habit_add", ["Test habit"]),
        ("/habit_done", ["1"]),
        ("/health", []),
        ("performance", []),
        ("perfstats", []),
    ]
    
    results = []
    for command, args in test_commands:
        success = await test_command(command, args)
        results.append((command, success))
        print()
    
    # Summary
    print("📊 Test Results Summary")
    print("=" * 30)
    successful = sum(1 for _, success in results if success)
    total = len(results)
    
    for command, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {command}")
    
    print(f"\nOverall: {successful}/{total} commands working ({successful/total*100:.1f}%)")
    
    if successful == total:
        print("🎉 All commands working correctly!")
    else:
        print("⚠️  Some commands need attention")

if __name__ == "__main__":
    asyncio.run(main()) 