---
title: Event System
description: Event-driven architecture and event bus in LarryBot2
last_updated: 2025-06-28
---

# Event System 🔄

LarryBot2 uses an event-driven architecture to enable loose coupling and extensibility.

## 🚌 Event Bus
- Central hub for emitting and listening to events
- Plugins and core services communicate via events
- Supports custom and built-in event types

## 🏷️ Event Types
- `task_created`, `task_updated`, `task_completed`
- `client_added`, `client_removed`, `client_assigned`
- `reminder_set`, `reminder_triggered`, `reminder_deleted`
- `calendar_event_added`, `calendar_event_updated`
- Custom events can be defined by plugins

## 📝 Usage Example
```python
from larrybot.core.event_utils import emit_task_event, safe_event_handler

# Emit a task created event
emit_task_event(event_bus, "task_created", task_data)

# Listen for an event
@event_listener("task_created")
@safe_event_handler
def handle_task_created(task):
    print(f"Task created: {task.description}")
```

## 🛠️ Best Practices
- Use standardized event names and payloads
- Handle events asynchronously when possible
- Use `safe_event_handler` to catch and log exceptions
- Document custom events in plugin docs

## 🚨 Troubleshooting
- **Event not received**: Check event name and registration
- **Handler errors**: Use `safe_event_handler` for debugging

## Event Data Format (Best Practice)

> **Note:** All events emitted by plugins (e.g., `task_completed`, `client_created`) now use a standardized dictionary format for event data, not ORM objects. This ensures compatibility and decoupling between plugins and the core system. See `larrybot/core/event_utils.py` for formatting details.

---

**Related Guides**: [Plugin System](plugin-system.md) | [Architecture Overview](overview.md) 