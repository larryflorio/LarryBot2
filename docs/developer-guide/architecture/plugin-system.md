---
title: Plugin System
description: Extensible plugin architecture in LarryBot2
last_updated: 2025-06-28
---

# Plugin System 🧩

LarryBot2 is built for extensibility using a robust plugin system.

## 🔌 Plugin Registration
- Plugins are registered with the event bus
- Each plugin implements a standard interface
- Plugins can emit and listen for events

## 🔄 Plugin Lifecycle
- **Load**: Plugin is discovered and loaded at startup
- **Register**: Plugin registers commands, event listeners, and services
- **Activate**: Plugin becomes active and can process events
- **Unload**: Plugin can be disabled or removed

## 🛠️ Extension Points
- **Commands**: Add new Telegram commands
- **Events**: Emit and handle custom events
- **Services**: Provide new business logic
- **Models**: Define new data structures

## 📝 Example: Registering a Plugin
```python
from larrybot.plugins import register_plugin

class MyPlugin:
    def register(self, event_bus, services):
        # Register commands and event listeners
        pass

register_plugin(MyPlugin())
```

## 🛠️ Best Practices
- Keep plugins modular and focused
- Document all commands and events
- Use dependency injection for services
- Handle errors gracefully

## 🚨 Troubleshooting
- **Plugin not loaded**: Check registration and file structure
- **Command/event not working**: Verify registration and event names

## Event Handler Best Practice

When subscribing to events, expect event data as a dictionary. For example:

```python
def on_task_completed(event_data):
    print(event_data['description'])  # event_data is a dict
```

---

**Related Guides**: [Event System](event-system.md) | [Architecture Overview](overview.md) 