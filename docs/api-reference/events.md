---
title: Events API Reference
description: Event system reference for LarryBot2
last_updated: 2025-06-28
---

# Events API Reference 📡

> **Breadcrumbs:** [Home](../../README.md) > [API Reference](README.md) > Events

This document provides a complete reference for LarryBot2's event-driven architecture and all available events.

## 🎯 Event System Overview

LarryBot2 uses an event-driven architecture where components communicate through events. This provides loose coupling, extensibility, and asynchronous processing.

### Core Components
- **Event Bus**: Central event dispatcher
- **Event Listeners**: Components that respond to events
- **Event Emitters**: Components that trigger events
- **Event Data**: Standardized data format for all events

## 📡 Event Types

### Task Events
- `task_created` - New task created
- `task_updated` - Task modified
- `task_deleted` - Task removed
- `task_completed` - Task marked as done
- `task_priority_changed` - Task priority updated
- `task_status_changed` - Task status updated
- `task_due_date_set` - Task due date assigned
- `subtask_added` - Subtask created
- `dependency_added` - Task dependency created
- `comment_added` - Comment added to task
- `time_tracking_started` - Time tracking started
- `time_tracking_stopped` - Time tracking stopped
- `time_entry_added` - Time entry recorded

### Client Events
- `client_created` - New client added
- `client_updated` - Client information modified
- `client_deleted` - Client removed

### Reminder Events
- `reminder_created` - New reminder set
- `reminder_updated` - Reminder modified
- `reminder_deleted` - Reminder removed
- `reminder_triggered` - Reminder fired

### Habit Events
- `habit_created` - New habit added
- `habit_updated` - Habit modified
- `habit_deleted` - Habit removed
- `habit_tracked` - Habit completion recorded

### Calendar Events
- `calendar_event_created` - Calendar event added
- `calendar_event_updated` - Calendar event modified
- `calendar_event_deleted` - Calendar event removed
- `calendar_sync_completed` - Calendar synchronization finished

### System Events
- `command_executed` - Command processed
- `error_occurred` - System error
- `health_check` - Health monitoring
- `plugin_loaded` - Plugin loaded
- `plugin_unloaded` - Plugin unloaded

## 📊 Event Data Format

### Standard Event Structure
```python
{
    "event_type": "task_created",
    "timestamp": "2025-06-28T10:30:00Z",
    "data": {
        "task_id": 1,
        "description": "Complete project documentation",
        "client_id": None,
        "priority": "medium",
        "status": "todo",
        "created_at": "2025-06-28T10:30:00Z"
    },
    "metadata": {
        "user_id": 123456789,
        "command": "/add_task",
        "session_id": "abc123"
    }
}
```

### Task Event Data
```python
# task_created, task_updated
{
    "task_id": 1,
    "description": "Task description",
    "done": False,
    "client_id": 1,
    "priority": "medium",
    "due_date": "2025-07-15",
    "category": "Development",
    "status": "todo",
    "estimated_hours": 4.0,
    "actual_hours": 0.0,
    "started_at": None,
    "parent_id": None,
    "tags": ["urgent", "bugfix"],
    "description_rich": "Rich text description",
    "created_at": "2025-06-28T10:30:00Z",
    "updated_at": "2025-06-28T10:30:00Z"
}

# task_completed
{
    "task_id": 1,
    "completed_at": "2025-06-28T15:45:00Z",
    "completion_time": 315  # minutes
}

# subtask_added
{
    "parent_task_id": 1,
    "subtask_id": 2,
    "description": "Subtask description"
}

# dependency_added
{
    "task_id": 1,
    "dependency_id": 2,
    "dependency_type": "blocks"
}

# comment_added
{
    "task_id": 1,
    "comment_id": 1,
    "comment": "Comment text",
    "user_id": 123456789,
    "created_at": "2025-06-28T10:30:00Z"
}

# time_tracking_started
{
    "task_id": 1,
    "started_at": "2025-06-28T10:30:00Z"
}

# time_tracking_stopped
{
    "task_id": 1,
    "stopped_at": "2025-06-28T12:30:00Z",
    "duration_minutes": 120
}

# time_entry_added
{
    "task_id": 1,
    "time_entry_id": 1,
    "started_at": "2025-06-28T10:30:00Z",
    "ended_at": "2025-06-28T12:30:00Z",
    "duration_minutes": 120,
    "description": "Time entry description"
}
```

### Client Event Data
```python
# client_created, client_updated
{
    "client_id": 1,
    "name": "Acme Corporation",
    "created_at": "2025-06-28T10:30:00Z",
    "updated_at": "2025-06-28T10:30:00Z"
}
```

### Reminder Event Data
```python
# reminder_created, reminder_updated
{
    "reminder_id": 1,
    "message": "Call client",
    "scheduled_time": "2025-07-15T10:00:00Z",
    "created_at": "2025-06-28T10:30:00Z",
    "updated_at": "2025-06-28T10:30:00Z"
}

# reminder_triggered
{
    "reminder_id": 1,
    "triggered_at": "2025-07-15T10:00:00Z",
    "message": "Call client"
}
```

### Habit Event Data
```python
# habit_created, habit_updated
{
    "habit_id": 1,
    "name": "Daily exercise",
    "frequency": "daily",
    "created_at": "2025-06-28T10:30:00Z",
    "updated_at": "2025-06-28T10:30:00Z"
}

# habit_tracked
{
    "habit_id": 1,
    "tracked_at": "2025-06-28T10:30:00Z",
    "streak_count": 5
}
```

### System Event Data
```python
# command_executed
{
    "command": "/add_task",
    "user_id": 123456789,
    "execution_time_ms": 150,
    "success": True,
    "error_message": None
}

# error_occurred
{
    "error_type": "ValidationError",
    "error_message": "Invalid task ID",
    "command": "/done",
    "user_id": 123456789,
    "timestamp": "2025-06-28T10:30:00Z"
}

# health_check
{
    "database_status": "healthy",
    "memory_usage_mb": 45.2,
    "cpu_usage_percent": 12.5,
    "disk_usage_percent": 23.1,
    "active_plugins": 8,
    "timestamp": "2025-06-28T10:30:00Z"
}
```

## 🔧 Event Handling

### Registering Event Listeners
```python
from larrybot.core.event_bus import EventBus
from larrybot.utils.decorators import event_listener

# Using decorator
@event_listener("task_created")
def handle_task_created(task_data):
    print(f"New task created: {task_data['description']}")

# Manual registration
def handle_task_updated(task_data):
    print(f"Task updated: {task_data['description']}")

event_bus = EventBus()
event_bus.subscribe("task_updated", handle_task_updated)
```

### Emitting Events
```python
from larrybot.core.event_bus import EventBus

event_bus = EventBus()

# Emit task created event
event_bus.emit("task_created", {
    "task_id": 1,
    "description": "New task",
    "created_at": "2025-06-28T10:30:00Z"
})
```

### Event Listener Best Practices
```python
@event_listener("task_created")
def handle_task_created(task_data):
    """Handle task creation events."""
    try:
        # Process the event
        process_new_task(task_data)
        
        # Emit follow-up events if needed
        event_bus.emit("task_processed", {"task_id": task_data["task_id"]})
        
    except Exception as e:
        # Log error and emit error event
        logger.error(f"Error processing task_created event: {e}")
        event_bus.emit("error_occurred", {
            "error_type": "TaskProcessingError",
            "error_message": str(e),
            "task_id": task_data.get("task_id")
        })
```

## 🛡️ Error Handling

### Event Processing Errors
- Events are processed asynchronously
- Errors in event handlers don't affect the main command flow
- Failed events are logged and can trigger error events
- Event handlers should be idempotent

### Event Data Validation
```python
def validate_task_event_data(data):
    """Validate task event data structure."""
    required_fields = ["task_id", "description"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    if not isinstance(data["task_id"], int):
        raise ValueError("task_id must be an integer")
    
    if not data["description"].strip():
        raise ValueError("description cannot be empty")
```

## 📈 Event Analytics

### Event Metrics
- **Event Volume**: Number of events per type per day
- **Processing Time**: Average time to process events
- **Error Rate**: Percentage of events that fail processing
- **Event Patterns**: Common event sequences

### Event Monitoring
```python
@event_listener("command_executed")
def track_command_metrics(event_data):
    """Track command execution metrics."""
    metrics_collector.record_command(
        command=event_data["command"],
        execution_time=event_data["execution_time_ms"],
        success=event_data["success"]
    )
```

## 🔄 Event Flow Examples

### Task Creation Flow
1. User sends `/add_task "New task"`
2. Command handler processes request
3. Task service creates task in database
4. `task_created` event emitted
5. Analytics plugin records task creation
6. Notification plugin sends confirmation
7. Calendar plugin checks for due date conflicts

### Task Completion Flow
1. User sends `/done 1`
2. Command handler processes request
3. Task service marks task as done
4. `task_completed` event emitted
5. Analytics plugin updates statistics
6. Habit plugin checks for related habits
7. Client plugin updates client statistics

## 📚 Related References

- [Commands API](commands.md) - Command reference
- [Models API](models.md) - Data model reference
- [Architecture Overview](../../developer-guide/architecture/overview.md) - System architecture
- [Event System Guide](../../developer-guide/architecture/event-system.md) - Detailed event system documentation

---

**Last Updated**: June 28, 2025 