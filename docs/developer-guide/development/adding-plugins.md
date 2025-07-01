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

---

**Related Guides**: [Plugin System](../architecture/plugin-system.md) | [Testing](testing.md) 