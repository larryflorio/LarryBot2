---
title: Adding Commands
description: Guide for adding new commands to LarryBot2
last_updated: 2025-06-28
---

# Adding Commands 🛠️

> **New in v2:** All commands now use rich MarkdownV2 formatting, emoji, and interactive inline keyboards. This guide covers the new UX helpers and best practices for creating world-class user experiences.

> **Breadcrumbs:** [Home](../../README.md) > [Developer Guide](../README.md) > [Development](README.md) > Adding Commands

This guide covers the process of adding new commands to LarryBot2, including best practices, patterns, and examples from recent implementations.

## 🎯 Overview

LarryBot2 uses a modular command system with clear separation of concerns:
- **Repository Layer**: Data access and persistence
- **Service Layer**: Business logic and validation
- **Plugin Layer**: Command handlers and user interface
- **Event System**: Asynchronous communication
- **UX Helpers**: Rich formatting and interactive elements

## 🎨 UX Standards & Helpers

### MessageFormatter
Provides consistent, rich formatting for all user-facing messages:

```python
from larrybot.utils.ux_helpers import MessageFormatter

# Success messages
await update.message.reply_text(
    MessageFormatter.format_success_message(
        "✅ Task created successfully!",
        {
            "Task": task.description,
            "ID": task.id,
            "Status": "Todo",
            "Created": task.created_at.strftime("%Y-%m-%d %H:%M")
        }
    ),
    parse_mode='MarkdownV2'
)

# Error messages
await update.message.reply_text(
    MessageFormatter.format_error_message(
        "Task not found",
        "Check the task ID or use /list to see available tasks"
    ),
    parse_mode='MarkdownV2'
)

# Info messages
await update.message.reply_text(
    MessageFormatter.format_info_message(
        "📋 No Tasks Found",
        {
            "Status": "No incomplete tasks",
            "Action": "Use /add to create your first task"
        }
    ),
    parse_mode='MarkdownV2'
)
```

### KeyboardBuilder
Creates interactive inline keyboards for actions and navigation:

```python
from larrybot.utils.ux_helpers import KeyboardBuilder

# Task action keyboard
keyboard = KeyboardBuilder.build_task_keyboard(task_id, status)

# Confirmation dialog
keyboard = KeyboardBuilder.build_confirmation_keyboard("task_delete", task_id)

# Navigation menu
keyboard = KeyboardBuilder.build_navigation_keyboard()

# Custom keyboard
keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Mark Done", callback_data=f"task_done:{task_id}"),
        InlineKeyboardButton("✏️ Edit", callback_data=f"task_edit:{task_id}")
    ],
    [
        InlineKeyboardButton("🗑️ Delete", callback_data=f"task_delete:{task_id}"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_main")
    ]
])
```

### Callback Query Handling
Handle interactive button clicks and confirmations:

```python
# In bot handler
async def _handle_task_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle task-related callback queries."""
    callback_data = query.data
    
    if callback_data.startswith("task_done:"):
        task_id = int(callback_data.split(":")[1])
        await self._handle_task_done(query, context, task_id)
    elif callback_data.startswith("task_edit:"):
        task_id = int(callback_data.split(":")[1])
        await self._handle_task_edit(query, context, task_id)
    elif callback_data.startswith("task_delete:"):
        task_id = int(callback_data.split(":")[1])
        await self._handle_task_delete(query, context, task_id)

async def _handle_task_done(self, query, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
    """Handle task completion via callback."""
    try:
        # Update task
        task_service = TaskService()
        result = await task_service.mark_task_done(task_id)
        
        if result['success']:
            await query.edit_message_text(
                MessageFormatter.format_success_message(
                    "✅ Task completed!",
                    {
                        "Task": result['data'].description,
                        "ID": task_id,
                        "Status": "Done",
                        "Completed": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                ),
                parse_mode='MarkdownV2'
            )
        else:
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Please try again or contact support."
                ),
                parse_mode='MarkdownV2'
            )
    except Exception as e:
        await query.edit_message_text(
            MessageFormatter.format_error_message(
                "Error completing task",
                str(e)
            ),
            parse_mode='MarkdownV2'
        )
```

## 📋 Command Categories

### Basic Commands
Simple CRUD operations with minimal business logic:
- Single task operations
- Basic data retrieval
- Simple updates

### Advanced Commands
Complex operations with business logic:
- Bulk operations
- Advanced filtering
- Analytics and reporting
- Multi-step processes

### System Commands
Infrastructure and utility commands:
- Health checks
- System diagnostics
- Help and documentation

## 🏗️ Implementation Patterns

### Pattern 1: Basic CRUD Command with Rich UX

#### Repository Layer
```python
# larrybot/storage/task_repository.py
class TaskRepository:
    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Get a single task by ID."""
        with self.get_session() as session:
            return session.query(Task).filter(Task.id == task_id).first()
    
    def update_task_status(self, task_id: int, status: str) -> bool:
        """Update task status."""
        with self.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = status
                session.commit()
                return True
            return False
```

#### Service Layer
```python
# larrybot/services/task_service.py
class TaskService:
    def __init__(self, task_repository: TaskRepository):
        self.task_repository = task_repository
    
    def update_task_status(self, task_id: int, status: str) -> Result[Task]:
        """Update task status with validation."""
        # Validate status
        if status not in ['Todo', 'In Progress', 'Review', 'Done']:
            return Result.error(f"Invalid status: {status}")
        
        # Update task
        success = self.task_repository.update_task_status(task_id, status)
        if not success:
            return Result.error(f"Task not found: {task_id}")
        
        # Get updated task
        task = self.task_repository.get_task_by_id(task_id)
        return Result.success(task)
```

#### Plugin Layer with Rich UX
```python
# larrybot/plugins/tasks.py
from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder

@command_handler("status")
def handle_status_command(update: Update, context: CallbackContext) -> None:
    """Handle /status command with rich UX."""
    try:
        # Parse arguments
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Missing arguments",
                    "Usage: /status <task_id> <status>"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        task_id = int(args[0])
        status = args[1]
        
        # Call service
        result = task_service.update_task_status(task_id, status)
        
        if result.is_success():
            task = result.value
            keyboard = KeyboardBuilder.build_task_keyboard(task.id, task.status)
            
            await update.message.reply_text(
                MessageFormatter.format_success_message(
                    "✅ Status updated successfully!",
                    {
                        "Task": task.description,
                        "ID": task.id,
                        "Status": task.status,
                        "Updated": task.updated_at.strftime("%Y-%m-%d %H:%M")
                    }
                ),
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    result.error,
                    "Check the task ID and status value."
                ),
                parse_mode='MarkdownV2'
            )
            
    except ValueError:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid task ID",
                "Please provide a valid numeric task ID."
            ),
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Unexpected error",
                str(e)
            ),
            parse_mode='MarkdownV2'
        )
```

### Pattern 2: Bulk Operations with Confirmation

#### Repository Layer
```python
# larrybot/storage/task_repository.py
class TaskRepository:
    def bulk_update_status(self, task_ids: List[int], status: str) -> BulkOperationResult:
        """Bulk update task status."""
        with self.get_session() as session:
            try:
                # Validate all tasks exist
                tasks = session.query(Task).filter(Task.id.in_(task_ids)).all()
                found_ids = {task.id for task in tasks}
                missing_ids = set(task_ids) - found_ids
                
                if missing_ids:
                    return BulkOperationResult(
                        success_count=len(found_ids),
                        failed_count=len(missing_ids),
                        errors=[f"Task not found: {id}" for id in missing_ids]
                    )
                
                # Update tasks
                for task in tasks:
                    task.status = status
                
                session.commit()
                
                return BulkOperationResult(
                    success_count=len(tasks),
                    failed_count=0,
                    errors=[]
                )
                
            except Exception as e:
                session.rollback()
                return BulkOperationResult(
                    success_count=0,
                    failed_count=len(task_ids),
                    errors=[f"Database error: {str(e)}"]
                )
```

#### Service Layer
```python
# larrybot/services/task_service.py
class TaskService:
    def bulk_update_status(self, task_ids: List[int], status: str) -> Result[BulkOperationResult]:
        """Bulk update task status with validation."""
        # Validate status
        if status not in ['Todo', 'In Progress', 'Review', 'Done']:
            return Result.error(f"Invalid status: {status}")
        
        # Validate task IDs
        if not task_ids:
            return Result.error("No task IDs provided")
        
        if len(task_ids) > 50:  # Limit bulk operations
            return Result.error("Too many tasks (max 50)")
        
        # Perform bulk update
        result = self.task_repository.bulk_update_status(task_ids, status)
        return Result.success(result)
```

#### Plugin Layer with Confirmation
```python
# larrybot/plugins/advanced_tasks.py
from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder

@command_handler("bulk_status")
def handle_bulk_status_command(update: Update, context: CallbackContext) -> None:
    """Handle /bulk_status command with confirmation."""
    try:
        # Parse arguments
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Missing arguments",
                    "Usage: /bulk_status <task_id1,task_id2,task_id3> <status>"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Parse task IDs
        try:
            task_ids = [int(id.strip()) for id in args[0].split(',')]
        except ValueError:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Invalid task IDs",
                    "Please provide comma-separated numeric task IDs."
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        status = args[1]
        
        # Show confirmation dialog
        keyboard = KeyboardBuilder.build_confirmation_keyboard("bulk_status", f"{','.join(map(str, task_ids))}:{status}")
        
        await update.message.reply_text(
            f"⚠️ **Confirm Bulk Status Update**\n\n"
            f"📊 **Tasks to update:** {len(task_ids)} tasks\n"
            f"🎯 **New status:** {status}\n"
            f"📋 **Task IDs:** {', '.join(map(str, task_ids))}\n\n"
            f"Are you sure you want to update these tasks?",
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Unexpected error",
                str(e)
            ),
            parse_mode='MarkdownV2'
        )
```

## 🧪 Testing with Rich UX

### Testing Message Formatting
```python
# tests/test_commands.py
@pytest.mark.asyncio
async def test_status_command_success(mock_update, mock_context, mock_task_service):
    """Test successful status command with rich UX."""
    # Arrange
    mock_context.args = ["1", "In Progress"]
    mock_task_service.update_task_status.return_value = Result.success(mock_task)
    
    # Act
    await handle_status_command(mock_update, mock_context)
    
    # Assert
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    
    # Check message content
    message_text = call_args[0][0]
    assert "✅ Status updated successfully!" in message_text
    assert "Task: Test task" in message_text
    
    # Check parse mode
    assert call_args[1]['parse_mode'] == 'MarkdownV2'
    
    # Check inline keyboard
    assert 'reply_markup' in call_args[1]
```

### Testing Error Handling
```python
@pytest.mark.asyncio
async def test_status_command_error(mock_update, mock_context, mock_task_service):
    """Test error handling in status command."""
    # Arrange
    mock_context.args = ["999", "Invalid"]
    mock_task_service.update_task_status.return_value = Result.error("Task not found")
    
    # Act
    await handle_status_command(mock_update, mock_context)
    
    # Assert
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    
    # Check error message
    message_text = call_args[0][0]
    assert "❌ Error" in message_text
    assert "Task not found" in message_text
    
    # Check parse mode
    assert call_args[1]['parse_mode'] == 'MarkdownV2'
```

## 🎯 Best Practices

### UX Design
- **Consistent Formatting**: Use MessageFormatter for all user-facing messages
- **Interactive Elements**: Provide inline keyboards for common actions
- **Progressive Disclosure**: Show advanced options only when needed
- **Error Handling**: Always provide actionable error messages
- **Mobile-First**: Ensure all flows work well on mobile devices

### Code Quality
- **Separation of Concerns**: Keep business logic in services, UI in plugins
- **Error Handling**: Use try-catch blocks and provide meaningful error messages
- **Validation**: Validate inputs at the service layer
- **Testing**: Write comprehensive tests for all command flows
- **Documentation**: Document complex commands and their usage

### Performance
- **Database Queries**: Optimize queries and use appropriate indexes
- **Rate Limiting**: Respect rate limits and provide feedback
- **Caching**: Cache frequently accessed data when appropriate
- **Async Operations**: Use async/await for I/O operations

## 🔗 Related Documentation
- [UX Helpers Reference](../architecture/ux-helpers.md) - Detailed UX helper documentation
- [Callback Query Handling](../architecture/callback-patterns.md) - Callback query patterns
- [Testing Guide](testing.md) - Testing best practices
- [Event System](../architecture/event-system.md) - Event-driven architecture

## 📝 Testing Guidelines

### Unit Tests
```