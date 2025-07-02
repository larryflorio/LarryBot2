---
title: Commands API Reference
description: Complete command reference for LarryBot2 with enhanced consolidated commands
last_updated: 2025-07-01
---

# Commands API Reference 📋

> **🆕 New in v2.1.6:** Major command consolidation completed! This reference reflects the enhanced unified commands with progressive functionality and backward compatibility.

> **Breadcrumbs:** [Home](../../README.md) > [API Reference](README.md) > Commands

This document provides a complete reference for all available Telegram commands in LarryBot2 as of July 1, 2025, including the enhanced consolidated commands and deprecation information.

## 🎮 Action Buttons Overview

LarryBot2 implements comprehensive action button functionality across all major features:

### Task Action Buttons
- **👁️ View**: Show detailed task information with all metadata
- **✅ Done**: Mark task as complete (only for incomplete tasks)
- **✏️ Edit**: Launch inline edit flow with text input
- **🗑️ Delete**: Delete task with confirmation dialog

### Client Action Buttons
- **👁️ View**: Show detailed client information with task statistics
- **✏️ Edit**: Edit client information (placeholder)
- **🗑️ Delete**: Delete client with confirmation dialog
- **📊 Analytics**: View per-client analytics and performance metrics

### Habit Action Buttons
- **✅ Complete**: Mark habit as done for today
- **📊 Progress**: Show detailed habit progress with visual indicators
- **🗑️ Delete**: Delete habit with confirmation dialog

### Reminder Action Buttons
- **✅ Complete**: Mark associated task as complete
- **⏰ Snooze 1h**: Snooze reminder for 1 hour
- **⏰ Snooze 1d**: Snooze reminder for 1 day
- **✏️ Edit**: Edit reminder time (placeholder)
- **🗑️ Delete**: Delete reminder with confirmation dialog

### Navigation Action Buttons
- **➕ Add**: Add new item (task, client, habit, reminder)
- **🔄 Refresh**: Reload current list with fresh data
- **⬅️ Back**: Return to previous menu or main menu

## 🎯 Command Summary

**Total Commands**: 86 commands across 7 categories *(5 commands consolidated, 7 deprecation handlers added)*

> **📋 Command Consolidation Summary**: 5 major command mergers completed with full backward compatibility through 7 deprecation handlers.

### System Commands (5 commands)
- `/start` - Start the bot and show welcome message
- `/help` - Show available commands and their descriptions
- `/health` - System health status
- `/health_quick` - Quick health status
- `/health_detailed` - Detailed health status

### **Enhanced Task Management** (65 commands) ⭐
- **Enhanced Basic Tasks (5)**: 
  - `/add` **⭐ Enhanced** - Now supports both basic and advanced task creation
  - `/list` **⭐ Enhanced** - Now supports both basic listing and advanced filtering
  - `/done`, `/edit`, `/remove` - Standard task operations
- **Advanced Task Features (5)**: `/priority`, `/due`, `/category`, `/status`, `/assign`
- **File Attachments (5)**: `/attach`, `/attachments`, `/remove_attachment`, `/attachment_description`, `/attachment_stats`
- **Enhanced Time Tracking (4)**: `/time_start` **⭐ Renamed**, `/stop`, `/time_entry`, `/time_summary`
- **Task Organization (5)**: `/tags`, `/subtask`, `/depend`, `/comment`, `/comments`
- **Enhanced Search & Filtering (10)**: 
  - `/search` **⭐ Enhanced** - Now supports both basic and advanced search with flags
  - `/overdue`, `/today`, `/week`, `/filter_advanced`, `/tags_multi`, `/time_range`, `/priority_range`
- **Bulk Operations (5)**: `/bulk_status`, `/bulk_priority`, `/bulk_assign`, `/bulk_delete`, `/bulk_operations`
- **Enhanced Analytics (3)**: 
  - `/analytics` **⭐ Enhanced** - Unified command supporting basic/detailed/advanced levels
  - `/productivity_report`, `/suggest`

### **Deprecated Commands (7 deprecation handlers)** ⚠️
- `~~`/addtask`~~` → Redirects to enhanced `/add` with usage examples
- `~~`/tasks`~~` → Redirects to enhanced `/list` with filtering examples
- `~~`/search_advanced`~~` → Redirects to enhanced `/search` with flag examples
- `~~`/analytics_detailed`~~` → Redirects to unified `/analytics detailed`
- `~~`/analytics_advanced`~~` → Redirects to unified `/analytics advanced`
- `~~`/start` (time tracking)`~~` → Redirects to `/time_start` with clear explanation
- All deprecated commands provide helpful migration guidance and usage examples

### Client Management (7 commands)
- `/addclient` - Add a new client
- `/removeclient` - Remove a client
- `/allclients` - List all clients with action buttons
- `/assign` - Assign task to client
- `/unassign` - Unassign task from client
- `/client` - Show client details
- `/clientanalytics` - Client analytics

### Calendar Integration (6 commands)
- `/connect_google` - Connect Google Calendar
- `/disconnect` - Disconnect calendar
- `/agenda` - Show calendar agenda
- `/calendar` - Calendar overview
- `/calendar_sync` - Sync calendar events
- `/calendar_events` - List calendar events

### Reminders (5 commands)
- `/addreminder` - Add a reminder
- `/reminders` - List all reminders with action buttons
- `/delreminder` - Delete a reminder
- `/reminder_quick` - Quick reminder creation
- `/reminder_stats` - Reminder statistics

### Habits (6 commands)
- `/habit_add` - Add a new habit
- `/habit_done` - Mark habit complete
- `/habit_list` - List all habits with action buttons
- `/habit_delete` - Delete a habit
- `/habit_progress` - Show habit progress
- `/habit_stats` - Habit statistics

### Examples (3 commands)
- `/hello` - Hello command
- `/example` - Example command demonstrating features
- `/calculate` - Calculate sum of numbers
- `/help_examples` - Show help for example commands

## 🔄 Callback Query Patterns

### Task Callbacks
```
task_view:<task_id>          # View task details
task_done:<task_id>          # Mark task complete
task_edit:<task_id>          # Edit task description
task_delete:<task_id>        # Delete task
task_confirm_delete:<task_id> # Confirm task deletion
```

### Client Callbacks
```
client_view:<client_id>      # View client details
client_edit:<client_id>      # Edit client (placeholder)
client_delete:<client_id>    # Delete client
client_confirm_delete:<client_id> # Confirm client deletion
client_analytics:<client_id> # View client analytics
```

### Habit Callbacks
```
habit_done:<habit_id>        # Mark habit complete
habit_progress:<habit_id>    # Show habit progress
habit_delete:<habit_id>      # Delete habit
habit_confirm_delete:<habit_id> # Confirm habit deletion
```

### Reminder Callbacks
```
reminder_complete:<reminder_id> # Mark associated task complete
reminder_snooze_1h:<reminder_id> # Snooze reminder 1 hour
reminder_snooze_1d:<reminder_id> # Snooze reminder 1 day
reminder_delete:<reminder_id> # Delete reminder
reminder_confirm_delete:<reminder_id> # Confirm reminder deletion
```

### Navigation Callbacks
```
task_list                   # Return to task list
client_list                 # Return to client list
habit_list                  # Return to habit list
reminder_list               # Return to reminder list
main_menu                   # Return to main menu
```

## 📝 Command Parameters

### Task Parameters
- `task_id`: Numeric ID of the task
- `description`: Task description text
- `priority`: One of "Low", "Medium", "High", "Critical"
- `status`: One of "Todo", "In Progress", "Review", "Done"
- `category`: Task category name
- `tags`: Comma-separated list of tags
- `due_date`: Date in YYYY-MM-DD format (displayed in local timezone, stored as UTC)
- `duration_minutes`: Time duration in minutes

### File Attachment Parameters
- `attachment_id`: Numeric ID of the attachment
- `file_data`: Binary file data (for programmatic use)
- `original_filename`: Original filename of the uploaded file
- `description`: Optional description for the attachment
- `is_public`: Whether the attachment is publicly accessible (boolean)

### Advanced Filtering Parameters
- `search_text`: Text to search for in descriptions, comments, and tags
- `sort_by`: Field to sort by (created_at, due_date, priority, status, category)
- `sort_order`: Sort order (asc, desc)
- `match_all`: For multi-tag filtering, require all tags (true) or any tag (false)
- `include_completed`: Include completed tasks in time range (true/false)

### Bulk Operation Parameters
- `task_ids`: Comma-separated list of task IDs
- `confirm`: Confirmation for destructive operations

### Analytics Parameters
- `days`: Number of days for analytics (1-365)
- `start_date`: Start date for reports (YYYY-MM-DD)
- `end_date`: End date for reports (YYYY-MM-DD)

### Client Parameters
- `client_id`: Numeric ID of the client
- `name`: Client name

### Reminder Parameters
- `reminder_id`: Numeric ID of the reminder
- `message`: Reminder message text
- `date`: Date in YYYY-MM-DD format (displayed in local timezone, stored as UTC)
- `time`: Time in HH:MM format (displayed in local timezone, stored as UTC)

### Habit Parameters
- `habit_id`: Numeric ID of the habit
- `name`: Habit name
- `frequency`: Frequency (daily, weekly, monthly)

## 🔧 Command Examples

### Basic Task Management
```
/add Complete project documentation
/done 1
/edit 1 Update project documentation with new features
/remove 1
```

### Advanced Task Management
```
/addtask Complete project proposal High 2025-07-15 Development
/priority 1 Critical
/due 1 2025-07-10
/category 1 Development
/status 1 In Progress
```

### Time Tracking
```
/start 1
/stop 1
/time_entry 1 120 "Code review and testing"
/time_summary 1
```

### Task Organization
```
/tags 1 add urgent,bugfix
/subtask 1 Write unit tests
/depend 1 2
/comment 1 Need to review with team
/comments 1
```

### File Attachments
```
/attach 1 [attach file to message]
/attachments 1
/remove_attachment 5
/attachment_description 5 "Updated project requirements"
```

### Advanced Filtering and Search
```
/search_advanced authentication
/filter_advanced Todo High Development created_at desc
/tags_multi urgent,bug all
/time_range 2025-07-01 2025-07-31
/priority_range Medium High
```

### Bulk Operations
```
/bulk_status 1,2,3 In Progress
/bulk_priority 1,2,3 High
/bulk_assign 1,2,3 Acme Corp
/bulk_delete 1,2,3 confirm
```

### Analytics and Reporting
```
/analytics
/analytics_advanced 30
/productivity_report 2025-07-01 2025-07-31
/suggest Complete project documentation
```

### Client Management
```
/addclient Acme Corporation
/assign 1 Acme Corporation
/client 1
/clientanalytics 1
```

### Reminder Management
```
/addreminder 1 2025-07-01 09:00
/reminders
/delreminder 1
```

### Habit Management
```
/habit_add Morning Exercise
/habit_done 1
/habit_list
/habit_progress 1
```

## 🎮 Action Button Implementation

### Keyboard Builders
The following keyboard builder functions are available in `larrybot/utils/ux_helpers.py`:

```python
build_task_keyboard(task_id: int, is_completed: bool = False) -> InlineKeyboardMarkup
build_client_keyboard(client_id: int) -> InlineKeyboardMarkup
build_habit_keyboard(habit_id: int, is_done_today: bool = False) -> InlineKeyboardMarkup
build_reminder_keyboard(reminder_id: int) -> InlineKeyboardMarkup
build_navigation_keyboard(back_to: str = "main") -> InlineKeyboardMarkup
```

### Callback Handler Patterns
All callback handlers follow consistent patterns:

1. **Parse callback data** to extract entity ID and action
2. **Validate entity existence** in database
3. **Perform operation** with proper error handling
4. **Update message** with success/error feedback
5. **Emit events** for other plugins to respond to
6. **Provide navigation** back to relevant lists

### Error Handling
- **Entity not found**: Show error message with navigation
- **Permission denied**: Show appropriate error message
- **Database errors**: Log error and show user-friendly message
- **Invalid input**: Validate and show helpful error message

### Success Feedback
- **Immediate visual feedback** with emoji and clear messaging
- **Updated information** showing the result of the action
- **Navigation options** to continue workflow
- **Event emission** for real-time updates across plugins

## 🚨 Best Practices

### Action Button Design
- **Consistent naming**: Use clear, descriptive button labels
- **Visual hierarchy**: Group related actions together
- **State awareness**: Show/hide buttons based on current state
- **Confirmation dialogs**: Use for destructive actions
- **Navigation flow**: Provide clear paths back to lists

### Callback Implementation
- **Input validation**: Always validate callback data
- **Error handling**: Graceful handling of all error cases
- **Database transactions**: Use proper transaction management
- **Event emission**: Emit events for cross-plugin communication
- **User feedback**: Provide immediate and clear feedback

### Performance Considerations
- **Lazy loading**: Load data only when needed
- **Caching**: Cache frequently accessed data
- **Batch operations**: Use bulk operations when possible
- **Database optimization**: Use efficient queries and indexes

## 🎮 Timezone Handling

> **Timezone Handling:**
> - All datetimes/times in LarryBot2 are stored in UTC in the database for consistency and reliability.
> - All times shown to users (command input/output, reminders, due dates, analytics, etc.) are transparently converted to and from the user's configured/system timezone.
> - All datetimes are timezone-aware and DST is handled automatically.
> - **Best Practice:** Always use the provided timezone utilities for all datetime operations in plugins and integrations.

---

**Related Documentation**: [Events API](events.md) → [Models API](models.md) → [Developer Guide](../../developer-guide/README.md)

---

**Last Updated**: June 29, 2025  
**Total Commands**: 75  
**Categories**: 6

---

**Related References:**
- [Events API](events.md) - Event system reference
- [Models API](models.md) - Data model reference
- [User Guide](../../user-guide/README.md) - User documentation

---

**Last Updated**: June 29, 2025 