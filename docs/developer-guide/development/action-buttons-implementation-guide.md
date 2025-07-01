---
title: Action Buttons Implementation Guide
description: Detailed guide for implementing action button handlers in LarryBot2
last_updated: 2025-06-29
version: 1.0
---

# Action Buttons Implementation Guide 🎯

> **Breadcrumbs:** [Home](../../README.md) > [Developer Guide](../README.md) > [Development](README.md) > Action Buttons Implementation Guide

This guide provides detailed implementation patterns, code examples, and best practices for completing all missing action button handlers in LarryBot2.

## 🎯 Overview

This guide follows the [Action Buttons Completion Project Plan](../../project/action-buttons-completion-plan.md) and provides specific implementation details for each phase.

### Implementation Principles
- **Consistency**: Follow existing patterns and conventions
- **Modularity**: Keep handlers focused and single-purpose
- **Error Handling**: Robust error handling for all scenarios
- **Testing**: Comprehensive testing for all handlers
- **Performance**: Optimized for fast response times
- **Security**: Secure handling of user input

---

## 🛠️ Phase 1: Critical Fixes Implementation

### 1.1 Bulk Operations Handlers

#### 1.1.1 Add Missing Bulk Status Handlers

**File**: `larrybot/handlers/bot.py`

**Add to `_handle_bulk_operations_callback()` method**:

```python
async def _handle_bulk_operations_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle bulk operations callback queries."""
    callback_data = query.data
    
    # Existing handlers...
    if callback_data == "bulk_status_menu":
        await self._show_bulk_status_menu(query, context)
    elif callback_data == "bulk_priority_menu":
        await self._show_bulk_priority_menu(query, context)
    # ... other existing handlers
    
    # NEW: Add these handlers
    elif callback_data.startswith("bulk_status:"):
        status = callback_data.split(":")[1]
        await self._handle_bulk_status_update(query, context, status)
    elif callback_data.startswith("bulk_priority:"):
        priority = callback_data.split(":")[1]
        await self._handle_bulk_priority_update(query, context, priority)
    elif callback_data == "bulk_operations_back":
        await self._handle_bulk_operations_back(query, context)
```

#### 1.1.2 Implement Bulk Status Update Handler

```python
async def _handle_bulk_status_update(self, query, context: ContextTypes.DEFAULT_TYPE, status: str) -> None:
    """Handle bulk status update for selected tasks."""
    from larrybot.services.task_service import TaskService
    from larrybot.utils.ux_helpers import MessageFormatter
    
    try:
        # Get selected task IDs from context
        selected_task_ids = context.user_data.get('bulk_selected_tasks', [])
        
        if not selected_task_ids:
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    "No tasks selected",
                    "Please select tasks for bulk status update first."
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Update tasks via service
        task_service = TaskService()
        result = await task_service.bulk_update_status(selected_task_ids, status)
        
        if result['success']:
            updated_count = result.get('updated_count', 0)
            await query.edit_message_text(
                MessageFormatter.format_success_message(
                    f"✅ Bulk Status Update Complete!",
                    {
                        "Status": status,
                        "Tasks Updated": updated_count,
                        "Total Selected": len(selected_task_ids),
                        "Details": result.get('details', 'Status updated successfully')
                    }
                ),
                parse_mode='MarkdownV2'
            )
        else:
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Please check the task IDs and try again."
                ),
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        logger.error(f"Error in bulk status update: {e}")
        await query.edit_message_text(
            MessageFormatter.format_error_message(
                "Error during bulk status update",
                "Please try again or contact support."
            ),
            parse_mode='MarkdownV2'
        )
```

#### 1.1.3 Implement Bulk Priority Update Handler

```python
async def _handle_bulk_priority_update(self, query, context: ContextTypes.DEFAULT_TYPE, priority: str) -> None:
    """Handle bulk priority update for selected tasks."""
    from larrybot.services.task_service import TaskService
    from larrybot.utils.ux_helpers import MessageFormatter
    
    try:
        # Get selected task IDs from context
        selected_task_ids = context.user_data.get('bulk_selected_tasks', [])
        
        if not selected_task_ids:
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    "No tasks selected",
                    "Please select tasks for bulk priority update first."
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Update tasks via service
        task_service = TaskService()
        result = await task_service.bulk_update_priority(selected_task_ids, priority)
        
        if result['success']:
            updated_count = result.get('updated_count', 0)
            await query.edit_message_text(
                MessageFormatter.format_success_message(
                    f"✅ Bulk Priority Update Complete!",
                    {
                        "Priority": priority,
                        "Tasks Updated": updated_count,
                        "Total Selected": len(selected_task_ids),
                        "Details": result.get('details', 'Priority updated successfully')
                    }
                ),
                parse_mode='MarkdownV2'
            )
        else:
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Please check the task IDs and try again."
                ),
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        logger.error(f"Error in bulk priority update: {e}")
        await query.edit_message_text(
            MessageFormatter.format_error_message(
                "Error during bulk priority update",
                "Please try again or contact support."
            ),
            parse_mode='MarkdownV2'
        )
```

#### 1.1.4 Implement Bulk Operations Back Handler

```python
async def _handle_bulk_operations_back(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle navigation back to bulk operations menu."""
    from larrybot.utils.ux_helpers import KeyboardBuilder
    
    keyboard = KeyboardBuilder.build_bulk_operations_keyboard()
    
    await query.edit_message_text(
        "🔄 **Bulk Operations**\n\nSelect an operation to perform on your selected tasks:",
        reply_markup=keyboard,
        parse_mode='MarkdownV2'
    )
```

### 1.2 Task Menu Handlers

#### 1.2.1 Add Missing Task Menu Handlers

**Add to `_handle_task_callback()` method**:

```python
async def _handle_task_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle task-related callback queries."""
    callback_data = query.data
    
    # Existing handlers...
    if callback_data.startswith("task_done:"):
        task_id = int(callback_data.split(":")[1])
        await self._handle_task_done(query, context, task_id)
    # ... other existing handlers
    
    # NEW: Add these handlers
    elif callback_data == "tasks_list":
        await self._handle_tasks_list(query, context)
    elif callback_data == "task_add":
        await self._handle_task_add(query, context)
    elif callback_data == "tasks_search":
        await self._handle_tasks_search(query, context)
    elif callback_data == "tasks_analytics":
        await self._handle_tasks_analytics(query, context)
    elif callback_data == "tasks_overdue":
        await self._handle_tasks_overdue(query, context)
    elif callback_data == "tasks_today":
        await self._handle_tasks_today(query, context)
```

#### 1.2.2 Implement Task List Handler

```python
async def _handle_tasks_list(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle tasks list view."""
    from larrybot.storage.db import get_session
    from larrybot.storage.task_repository import TaskRepository
    from larrybot.utils.ux_helpers import MessageFormatter
    
    try:
        with next(get_session()) as session:
            repo = TaskRepository(session)
            tasks = repo.list_incomplete_tasks()
            
            if not tasks:
                await query.edit_message_text(
                    MessageFormatter.format_info_message(
                        "📋 No Tasks Found",
                        {
                            "Status": "No incomplete tasks",
                            "Action": "Use /add to create your first task"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
                return
            
            # Format task list
            message = MessageFormatter.format_task_list(tasks, "Incomplete Tasks")
            
            # Create action buttons for each task
            keyboard_buttons = []
            for task in tasks:
                task_row = [
                    InlineKeyboardButton(f"👁️ {task.id}", callback_data=f"task_view:{task.id}"),
                    InlineKeyboardButton(f"✅ {task.id}", callback_data=f"task_done:{task.id}"),
                    InlineKeyboardButton(f"✏️ {task.id}", callback_data=f"task_edit:{task.id}"),
                    InlineKeyboardButton(f"🗑️ {task.id}", callback_data=f"task_delete:{task.id}")
                ]
                keyboard_buttons.append(task_row)
            
            # Add navigation buttons
            keyboard_buttons.append([
                InlineKeyboardButton("🔄 Refresh", callback_data="tasks_refresh"),
                InlineKeyboardButton("⬅️ Back", callback_data="menu_tasks")
            ])
            
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
            
            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        logger.error(f"Error showing tasks list: {e}")
        await query.edit_message_text(
            MessageFormatter.format_error_message(
                "Error loading tasks",
                "Please try again or use /list command."
            ),
            parse_mode='MarkdownV2'
        )
```

#### 1.2.3 Implement Task Add Handler

```python
async def _handle_task_add(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle task add button click."""
    from larrybot.utils.ux_helpers import MessageFormatter
    
    await query.edit_message_text(
        MessageFormatter.format_info_message(
            "Add New Task",
            {
                "Command": "/add <description>",
                "Advanced": "/addtask <description> [priority] [due_date] [category]",
                "Example": "/add Buy groceries",
                "Description": "Create a new task to track"
            }
        ),
        parse_mode='MarkdownV2'
    )
```

#### 1.2.4 Implement Task Search Handler

```python
async def _handle_tasks_search(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle task search functionality."""
    from larrybot.utils.ux_helpers import MessageFormatter
    
    # Store search mode in context
    context.user_data['search_mode'] = 'tasks'
    
    await query.edit_message_text(
        "🔍 **Task Search**\n\n"
        "Please reply with your search terms.\n"
        "You can search by:\n"
        "• Description keywords\n"
        "• Task ID\n"
        "• Status (Todo, In Progress, Done)\n"
        "• Priority (Low, Medium, High, Critical)\n"
        "• Category\n\n"
        "Example: `high priority work`",
        parse_mode='MarkdownV2'
    )
```

### 1.3 Placeholder Implementations

#### 1.3.1 Implement Client Tasks Handler

```python
async def _handle_client_tasks(self, query, context: ContextTypes.DEFAULT_TYPE, client_id: int) -> None:
    """Handle client tasks view with full functionality."""
    from larrybot.storage.db import get_session
    from larrybot.storage.client_repository import ClientRepository
    from larrybot.storage.task_repository import TaskRepository
    from larrybot.utils.ux_helpers import MessageFormatter
    
    try:
        with next(get_session()) as session:
            client_repo = ClientRepository(session)
            task_repo = TaskRepository(session)
            
            client = client_repo.get_client_by_id(client_id)
            if not client:
                await query.edit_message_text(
                    MessageFormatter.format_error_message(
                        f"Client ID {client_id} not found",
                        "The client may have been deleted or doesn't exist."
                    ),
                    parse_mode='MarkdownV2'
                )
                return
            
            # Get tasks for this client
            tasks = task_repo.get_tasks_by_client(client.name)
            
            if not tasks:
                await query.edit_message_text(
                    MessageFormatter.format_info_message(
                        f"No Tasks for {client.name}",
                        {
                            "Client": client.name,
                            "Status": "No tasks assigned",
                            "Action": f"Use /addtask to create tasks for {client.name}"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
                return
            
            # Format task list
            message = f"📋 **Tasks for {MessageFormatter.escape_markdown(client.name)}**\n\n"
            
            for task in tasks:
                status_emoji = "✅" if task.done else "📝"
                priority_emoji = {
                    "Low": "🟢", "Medium": "🟡", 
                    "High": "🟠", "Critical": "🔴"
                }.get(getattr(task, 'priority', 'Medium'), '🟡')
                
                message += f"{status_emoji} **{task.id}**: {MessageFormatter.escape_markdown(task.description)}\n"
                message += f"   {priority_emoji} {getattr(task, 'priority', 'Medium')}\n"
                if hasattr(task, 'due_date') and task.due_date:
                    message += f"   📅 Due: {task.due_date.strftime('%Y-%m-%d')}\n"
                message += "\n"
            
            # Create action buttons
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"client_tasks:{client_id}")],
                [InlineKeyboardButton("⬅️ Back to Client", callback_data=f"client_view:{client_id}")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        logger.error(f"Error showing client tasks for {client_id}: {e}")
        await query.edit_message_text(
            MessageFormatter.format_error_message(
                "Error loading client tasks",
                "Please try again or use /client command."
            ),
            parse_mode='MarkdownV2'
        )
```

---

## 🛠️ Phase 2: Core Feature Implementation

### 2.1 Reminder Management Handlers

#### 2.1.1 Add Reminder Callback Handler

**Add to main callback router in `_handle_callback_query()`**:

```python
async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    # ... existing code ...
    
    try:
        callback_data = query.data
        
        # ... existing handlers ...
        
        # NEW: Add reminder handler
        elif callback_data.startswith("reminder_"):
            await self._handle_reminder_callback(query, context)
        
        # ... rest of existing code ...
```

#### 2.1.2 Implement Reminder Callback Handler

```python
async def _handle_reminder_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle reminder-related callback queries."""
    callback_data = query.data
    
    if callback_data == "reminder_add":
        await self._handle_reminder_add(query, context)
    elif callback_data == "reminder_stats":
        await self._handle_reminder_stats(query, context)
    elif callback_data == "reminder_refresh":
        await self._handle_reminder_refresh(query, context)
    elif callback_data.startswith("reminder_complete:"):
        reminder_id = int(callback_data.split(":")[1])
        await self._handle_reminder_complete(query, context, reminder_id)
    elif callback_data.startswith("reminder_snooze:"):
        parts = callback_data.split(":")
        reminder_id = int(parts[1])
        duration = parts[2] if len(parts) > 2 else "1h"
        await self._handle_reminder_snooze(query, context, reminder_id, duration)
    elif callback_data.startswith("reminder_edit:"):
        reminder_id = int(callback_data.split(":")[1])
        await self._handle_reminder_edit(query, context, reminder_id)
    elif callback_data.startswith("reminder_delete:"):
        reminder_id = int(callback_data.split(":")[1])
        await self._handle_reminder_delete(query, context, reminder_id)
    elif callback_data.startswith("reminder_reactivate:"):
        reminder_id = int(callback_data.split(":")[1])
        await self._handle_reminder_reactivate(query, context, reminder_id)
    elif callback_data == "reminder_dismiss":
        await self._handle_reminder_dismiss(query, context)
```

#### 2.1.3 Implement Individual Reminder Handlers

```python
async def _handle_reminder_add(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle reminder add button click."""
    from larrybot.utils.ux_helpers import MessageFormatter
    
    await query.edit_message_text(
        MessageFormatter.format_info_message(
            "Add New Reminder",
            {
                "Command": "/addreminder <task_id> <time>",
                "Example": "/addreminder 123 2h",
                "Time Formats": "1h, 2d, 1w, 2025-07-01 14:30",
                "Description": "Create a reminder for a specific task"
            }
        ),
        parse_mode='MarkdownV2'
    )

async def _handle_reminder_complete(self, query, context: ContextTypes.DEFAULT_TYPE, reminder_id: int) -> None:
    """Handle reminder completion."""
    from larrybot.storage.db import get_session
    from larrybot.storage.reminder_repository import ReminderRepository
    from larrybot.utils.ux_helpers import MessageFormatter
    
    try:
        with next(get_session()) as session:
            repo = ReminderRepository(session)
            reminder = repo.get_reminder_by_id(reminder_id)
            
            if not reminder:
                await query.edit_message_text(
                    MessageFormatter.format_error_message(
                        f"Reminder ID {reminder_id} not found",
                        "The reminder may have been deleted."
                    ),
                    parse_mode='MarkdownV2'
                )
                return
            
            # Mark reminder as completed
            repo.mark_reminder_completed(reminder_id)
            
            await query.edit_message_text(
                MessageFormatter.format_success_message(
                    "✅ Reminder Completed!",
                    {
                        "Reminder": reminder.description,
                        "ID": reminder_id,
                        "Status": "Completed",
                        "Completed": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                ),
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        logger.error(f"Error completing reminder {reminder_id}: {e}")
        await query.edit_message_text(
            MessageFormatter.format_error_message(
                "Error completing reminder",
                "Please try again or contact support."
            ),
            parse_mode='MarkdownV2'
        )
```

### 2.2 File Attachment Handlers

#### 2.2.1 Add Attachment Callback Handler

**Add to main callback router**:

```python
# NEW: Add attachment handler
elif callback_data.startswith("attachment_"):
    await self._handle_attachment_callback(query, context)
```

#### 2.2.2 Implement Attachment Callback Handler

```python
async def _handle_attachment_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle attachment-related callback queries."""
    callback_data = query.data
    
    if callback_data.startswith("attachment_edit_desc:"):
        attachment_id = int(callback_data.split(":")[1])
        await self._handle_attachment_edit_desc(query, context, attachment_id)
    elif callback_data.startswith("attachment_details:"):
        attachment_id = int(callback_data.split(":")[1])
        await self._handle_attachment_details(query, context, attachment_id)
    elif callback_data.startswith("attachment_remove:"):
        attachment_id = int(callback_data.split(":")[1])
        await self._handle_attachment_remove(query, context, attachment_id)
    elif callback_data.startswith("attachment_stats:"):
        task_id = int(callback_data.split(":")[1])
        await self._handle_attachment_stats(query, context, task_id)
    elif callback_data.startswith("attachment_add_desc:"):
        task_id = int(callback_data.split(":")[1])
        await self._handle_attachment_add_desc(query, context, task_id)
    elif callback_data.startswith("attachment_bulk_remove:"):
        task_id = int(callback_data.split(":")[1])
        await self._handle_attachment_bulk_remove(query, context, task_id)
    elif callback_data.startswith("attachment_export:"):
        task_id = int(callback_data.split(":")[1])
        await self._handle_attachment_export(query, context, task_id)
    elif callback_data.startswith("attachment_add:"):
        task_id = int(callback_data.split(":")[1])
        await self._handle_attachment_add(query, context, task_id)
```

---

## 🧪 Testing Implementation

### Test Structure

```python
# tests/test_action_buttons_comprehensive.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from larrybot.handlers.bot import TelegramBotHandler

class TestActionButtonsComprehensive:
    """Comprehensive testing for all action button handlers."""
    
    @pytest.fixture
    def mock_callback_query(self):
        """Create a mock callback query for testing."""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.data = "test_callback_data"
        return query
    
    @pytest.mark.asyncio
    async def test_bulk_status_update_success(self, bot_handler, mock_callback_query, mock_context):
        """Test successful bulk status update."""
        mock_callback_query.data = "bulk_status:Todo"
        mock_context.user_data = {'bulk_selected_tasks': [1, 2, 3]}
        
        with patch('larrybot.services.task_service.TaskService') as mock_service:
            mock_service.return_value.bulk_update_status.return_value = {
                'success': True,
                'updated_count': 3,
                'details': 'All tasks updated successfully'
            }
            
            await bot_handler._handle_bulk_status_update(mock_callback_query, mock_context, "Todo")
            
            mock_callback_query.edit_message_text.assert_called_once()
            call_args = mock_callback_query.edit_message_text.call_args
            assert "Bulk Status Update Complete" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_bulk_status_update_no_tasks_selected(self, bot_handler, mock_callback_query, mock_context):
        """Test bulk status update with no tasks selected."""
        mock_callback_query.data = "bulk_status:Todo"
        mock_context.user_data = {'bulk_selected_tasks': []}
        
        await bot_handler._handle_bulk_status_update(mock_callback_query, mock_context, "Todo")
        
        mock_callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query.edit_message_text.call_args
        assert "No tasks selected" in call_args[0][0]
```

---

## 🔧 Service Layer Implementation

### Task Service Bulk Operations

```python
# larrybot/services/task_service.py
class TaskService:
    async def bulk_update_status(self, task_ids: List[int], status: str) -> Dict[str, Any]:
        """Update status for multiple tasks."""
        try:
            with next(get_session()) as session:
                repo = TaskRepository(session)
                updated_count = 0
                
                for task_id in task_ids:
                    task = repo.get_task_by_id(task_id)
                    if task:
                        task.status = status
                        updated_count += 1
                
                session.commit()
                
                return {
                    'success': True,
                    'updated_count': updated_count,
                    'details': f'Updated {updated_count} tasks to {status}'
                }
                
        except Exception as e:
            logger.error(f"Error in bulk status update: {e}")
            return {
                'success': False,
                'message': f'Error updating tasks: {str(e)}'
            }
    
    async def bulk_update_priority(self, task_ids: List[int], priority: str) -> Dict[str, Any]:
        """Update priority for multiple tasks."""
        try:
            with next(get_session()) as session:
                repo = TaskRepository(session)
                updated_count = 0
                
                for task_id in task_ids:
                    task = repo.get_task_by_id(task_id)
                    if task:
                        task.priority = priority
                        updated_count += 1
                
                session.commit()
                
                return {
                    'success': True,
                    'updated_count': updated_count,
                    'details': f'Updated {updated_count} tasks to {priority} priority'
                }
                
        except Exception as e:
            logger.error(f"Error in bulk priority update: {e}")
            return {
                'success': False,
                'message': f'Error updating tasks: {str(e)}'
            }
```

---

## 📊 Performance Optimization

### Database Query Optimization

```python
# Optimized bulk operations
async def bulk_update_status_optimized(self, task_ids: List[int], status: str) -> Dict[str, Any]:
    """Optimized bulk status update using single query."""
    try:
        with next(get_session()) as session:
            # Use single UPDATE query for better performance
            result = session.query(Task).filter(Task.id.in_(task_ids)).update(
                {Task.status: status}, 
                synchronize_session=False
            )
            session.commit()
            
            return {
                'success': True,
                'updated_count': result,
                'details': f'Updated {result} tasks to {status}'
            }
            
    except Exception as e:
        logger.error(f"Error in optimized bulk status update: {e}")
        return {
            'success': False,
            'message': f'Error updating tasks: {str(e)}'
        }
```

---

## 🚨 Error Handling Best Practices

### Comprehensive Error Handling Pattern

```python
async def _handle_action_with_error_handling(self, query, context: ContextTypes.DEFAULT_TYPE, action_func, *args) -> None:
    """Generic error handling wrapper for action handlers."""
    from larrybot.utils.ux_helpers import MessageFormatter
    
    try:
        # Validate input
        if not self._validate_input(*args):
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    "Invalid input",
                    "Please check your input and try again."
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Perform action
        result = await action_func(*args)
        
        if result['success']:
            await query.edit_message_text(
                MessageFormatter.format_success_message(
                    result['title'],
                    result['details']
                ),
                parse_mode='MarkdownV2'
            )
        else:
            await query.edit_message_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    result.get('suggestion', 'Please try again.')
                ),
                parse_mode='MarkdownV2'
            )
            
    except ValueError as e:
        logger.warning(f"Validation error in action handler: {e}")
        await query.edit_message_text(
            MessageFormatter.format_error_message(
                "Invalid input",
                str(e)
            ),
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Unexpected error in action handler: {e}")
        await query.edit_message_text(
            MessageFormatter.format_error_message(
                "An unexpected error occurred",
                "Please try again or contact support."
            ),
            parse_mode='MarkdownV2'
        )
```

---

## 📚 References

- [Action Buttons Completion Project Plan](../../project/action-buttons-completion-plan.md)
- [Adding Commands Guide](adding-commands.md)
- [UX Implementation Plan](../../project/ux-implementation-plan.md)
- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [Telegram Bot UX Best Practices](https://core.telegram.org/bots/2-0-intro)

---

**Last Updated**: June 29, 2025  
**Version**: 1.0  
**Status**: Implementation Guide 