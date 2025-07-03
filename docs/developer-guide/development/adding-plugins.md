---
title: Adding Plugins
description: How to create and register plugins in LarryBot2
last_updated: 2025-06-28
---

# Adding Plugins 🧩

This guide explains how to create and register new plugins in LarryBot2.

## 🚀 Steps to Add a Plugin

1. **Create the Plugin Class**
   - Implement a `register` method for commands and event listeners.

```python
class MyPlugin:
    def register(self, event_bus, services):
        # Register commands and event listeners
        pass
```

2. **Register the Plugin**
   - Use `register_plugin` to add your plugin to the system.

```python
from larrybot.plugins import register_plugin
register_plugin(MyPlugin())
```

3. **Add Plugin to the Plugins Directory**
   - Place your plugin file in `larrybot/plugins/`.

4. **Document the Plugin**
   - List all commands and events in the plugin docstring and documentation.

5. **Test the Plugin**
   - Add unit and integration tests for all plugin features.
   - Testing framework (pytest, pytest-asyncio, pytest-cov) is included in requirements.txt.

## 🛠️ Best Practices
- Keep plugins modular and focused
- Use dependency injection for services
- Document all commands and events
- Handle errors gracefully

## 🚨 Troubleshooting
- **Plugin not loaded**: Check registration and file structure
- **Command/event not working**: Verify registration and event names

> **Tip:** When writing event handlers, remember that event data is always provided as a dictionary, not an ORM object. See the Event System guide for details.

## 🕒 Datetime Handling in Plugins

When developing plugins that involve dates and times, always use the timezone-safe datetime utilities:

### **Plugin Datetime Best Practices**
```python
from larrybot.utils.basic_datetime import get_utc_now, get_current_datetime
from larrybot.utils.datetime_utils import format_datetime_for_display

class MyPlugin(Plugin):
    """Example plugin with timezone-safe datetime handling."""
    
    async def on_task_created(self, task: Task):
        """Handle task creation with timezone-aware timestamps."""
        # Store creation time in UTC
        task.created_at = get_utc_now()
        
        # Display time in user's timezone
        display_time = format_datetime_for_display(task.created_at)
        await self.bot.send_message(f"Task created at: {display_time}")
    
    async def schedule_reminder(self, task: Task, reminder_time: str):
        """Schedule reminder with timezone-safe parsing."""
        from larrybot.utils.datetime_utils import parse_datetime_input
        
        # Parse user input with timezone awareness
        scheduled_time = parse_datetime_input(reminder_time)
        display_time = format_datetime_for_display(scheduled_time)
        
        # Store in UTC, display in local timezone
        task.reminder_time = scheduled_time
        await self.bot.send_message(f"Reminder scheduled for: {display_time}")
```

### **Timezone-Safe Plugin Patterns**
```python
# ✅ CORRECT: Use timezone-aware utilities in plugins
from larrybot.utils.basic_datetime import get_current_datetime
from larrybot.utils.datetime_utils import format_datetime_for_display

class TimePlugin(Plugin):
    async def get_current_time(self):
        """Get current time in user's timezone."""
        current_time = get_current_datetime()
        return format_datetime_for_display(current_time)

# ❌ INCORRECT: Direct datetime usage in plugins
import datetime
class BadTimePlugin(Plugin):
    async def get_current_time_bad(self):
        # This will cause timezone issues
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Banned
```

### **Plugin Configuration with Timezone**
```python
class ConfigurablePlugin(Plugin):
    def __init__(self):
        super().__init__()
        # Plugin can access timezone configuration
        self.timezone_service = self.get_service('timezone')
    
    async def handle_timezone_request(self):
        """Handle timezone-related plugin functionality."""
        current_timezone = self.timezone_service.get_current_timezone()
        current_time = get_current_datetime()
        display_time = format_datetime_for_display(current_time)
        
        return f"Current timezone: {current_timezone}\nCurrent time: {display_time}"
```

### **Testing Plugins with Datetime**
```python
# Test plugin with timezone-safe mocking
@patch('larrybot.utils.basic_datetime.get_current_datetime')
def test_time_plugin(mock_current_time):
    mock_current_time.return_value = create_future_datetime(hours=1)
    
    plugin = TimePlugin()
    result = await plugin.get_current_time()
    
    # Verify timezone-safe display
    assert "UTC" not in result
    assert result is not None
```

### **Plugin Event Handling with Datetime**
```python
class EventPlugin(Plugin):
    async def on_scheduled_event(self, event_time: datetime):
        """Handle scheduled events with timezone awareness."""
        # Event time is already timezone-aware
        display_time = format_datetime_for_display(event_time)
        
        # Process event with timezone-correct logic
        if event_time > get_current_datetime():
            await self.bot.send_message(f"Event scheduled for: {display_time}")
        else:
            await self.bot.send_message(f"Event occurred at: {display_time}")
```

### **Plugin Data Storage with UTC**
```python
class DataPlugin(Plugin):
    async def store_timestamped_data(self, data: dict):
        """Store data with timezone-safe timestamps."""
        # Always store timestamps in UTC
        data['created_at'] = get_utc_now()
        data['updated_at'] = get_utc_now()
        
        # Store in database
        await self.storage.save_data(data)
    
    async def retrieve_and_display_data(self, data_id: str):
        """Retrieve and display data with timezone conversion."""
        data = await self.storage.get_data(data_id)
        
        # Convert stored UTC times to local for display
        created_display = format_datetime_for_display(data['created_at'])
        updated_display = format_datetime_for_display(data['updated_at'])
        
        return f"Created: {created_display}\nUpdated: {updated_display}"
```

> **Plugin Development Note**: All plugins must use the timezone-safe datetime utilities to ensure consistent behavior across the entire system. The old `datetime.now()` and `datetime.utcnow()` patterns are no longer supported in plugin development.

---

**Related Guides**: [Plugin System](../architecture/plugin-system.md) | [Testing](testing.md) 