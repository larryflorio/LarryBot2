---
title: Reminders Commands
description: Set, list, and delete reminders in LarryBot2 with enhanced action buttons
last_updated: 2025-06-29
---

# Reminders Commands ⏰

LarryBot2 allows you to set, list, and delete reminders for your tasks with enhanced action buttons for quick interactions. This guide covers all reminder commands and interactive features.

## ⏰ Reminder Commands

### `/addreminder` - Add Reminder
Add a reminder for a specific task.

**Usage**: `/addreminder <task_id> <YYYY-MM-DD HH:MM>`

**Examples**:
```
/addreminder 124 2025-06-30 09:00
/addreminder 125 2025-07-01 14:30
```

**Response**:
```
✅ Reminder set for Task #124 at 2025-06-30 09:00.

📋 **Details:**
   • Task: Complete project proposal
   • ID: 124
   • Reminder: 2025-06-30 09:00
   • Status: Active
   • Created: 2025-06-29 10:30
```

### `/reminders` - List Reminders
List all reminders for your tasks with action buttons for quick management.

**Usage**: `/reminders`

**Features**:
- **Per-reminder action buttons**: Complete, Snooze, Edit, Delete for each reminder
- **Task information**: Shows associated task details
- **Time indicators**: Visual indicators for upcoming vs overdue reminders
- **Navigation buttons**: Add Reminder, Refresh, Back to Main
- **Status tracking**: Shows active vs completed reminders

**Response**:
```
⏰ **All Reminders** (3 found)

1. 🔴 **Overdue** - Task #124
   📝 Complete project proposal
   ⏰ Due: 2025-06-29 09:00 (2 hours ago)
   📅 Created: 2025-06-28 10:30

2. 🟡 **Today** - Task #125
   📝 Call client about project
   ⏰ Due: 2025-06-29 14:30 (in 2 hours)
   📅 Created: 2025-06-28 11:00

3. 🟢 **Upcoming** - Task #126
   📝 Review quarterly reports
   ⏰ Due: 2025-06-30 10:00 (tomorrow)
   📅 Created: 2025-06-28 15:00

[✅ Complete] [⏰ Snooze 1h] [✏️ Edit] [🗑️ Delete]
[✅ Complete] [⏰ Snooze 1h] [✏️ Edit] [🗑️ Delete]
[✅ Complete] [⏰ Snooze 1h] [✏️ Edit] [🗑️ Delete]

[➕ Add Reminder] [🔄 Refresh]
[⬅️ Back]
```

### `/delreminder` - Delete Reminder
Delete a reminder by its ID with confirmation dialog.

**Usage**: `/delreminder <reminder_id>`

**Examples**:
```
/delreminder 1
/delreminder 2
```

**Response (confirmation dialog)**:
```
🗑️ **Confirm Reminder Deletion**

**Reminder**: Task #124 - Complete project proposal
**ID**: 1
**Due**: 2025-06-29 09:00
**Status**: Overdue

⚠️ **Warning**: This will permanently delete the reminder.

Are you sure you want to delete this reminder?

[Inline keyboard: Confirm Delete | Cancel]
```

**Response (after confirmation)**:
```
🗑️ Reminder #1 deleted successfully!

📋 **Details:**
   • Task: Complete project proposal
   • ID: 1
   • Status: Deleted
   • Action: Reminder removed from database
```

## 🎮 Action Buttons

### Reminder List Actions
When you use `/reminders`, each reminder displays action buttons:

- **✅ Complete**: Mark the associated task as complete
- **⏰ Snooze 1h**: Snooze the reminder for 1 hour
- **⏰ Snooze 1d**: Snooze the reminder for 1 day
- **✏️ Edit**: Edit reminder time (placeholder - shows "not implemented")
- **🗑️ Delete**: Delete the reminder with confirmation dialog
- **👁️ View Task**: View the associated task details

### Reminder Response Actions
When a reminder triggers, you can:

- **✅ Mark Done**: Mark the task as complete
- **⏰ Snooze 1h**: Snooze the reminder for 1 hour
- **⏰ Snooze 1d**: Snooze the reminder for 1 day
- **🗑️ Delete Reminder**: Delete the reminder permanently
- **👁️ View Task**: View the task details
- **❌ Dismiss**: Dismiss the reminder without action

### Navigation Actions
- **➕ Add Reminder**: Shows instructions for adding a new reminder
- **🔄 Refresh**: Reload the reminder list with current data
- **⬅️ Back**: Return to main menu

## 🎯 Reminder Response Example

When a reminder triggers, you'll receive a message like this:

```
⏰ **Reminder**

📝 **Task**: Complete project proposal
🆔 **ID**: 124
⏰ **Due**: 2025-06-29 09:00
📅 **Created**: 2025-06-28 10:30

This task is due now!

[✅ Mark Done] [⏰ Snooze 1h]
[⏰ Snooze 1d] [🗑️ Delete Reminder]
[👁️ View Task] [❌ Dismiss]
```

## 🔄 Snooze Functionality

### Snooze Options
- **1 Hour**: Snooze reminder for 1 hour
- **1 Day**: Snooze reminder for 24 hours
- **Custom**: Set custom snooze time (future feature)

### Snooze Example
When you click **⏰ Snooze 1h**:

```
⏰ **Reminder Snoozed**

📝 **Task**: Complete project proposal
⏰ **New Due**: 2025-06-29 10:00 (in 1 hour)
📅 **Snoozed**: 2025-06-29 09:00

The reminder has been snoozed for 1 hour.

[✅ Mark Done] [⏰ Snooze Again]
[👁️ View Task] [🗑️ Delete Reminder]
```

## 🎯 Reminder Management

### Reminder Status Indicators
- **🔴 Overdue**: Reminder is past due time
- **🟡 Today**: Reminder is due today
- **🟢 Upcoming**: Reminder is due in the future
- **✅ Completed**: Associated task is completed

### Reminder Information Display
Each reminder shows:

- **Task Details**: Description and ID of associated task
- **Due Time**: When the reminder is scheduled
- **Status**: Current status (active, overdue, completed)
- **Created Date**: When the reminder was created
- **Snooze History**: Previous snooze actions (if any)

## 🛠️ Best Practices
- **Set reminders for important deadlines** to stay on track
- **Use snooze functionality** when you need more time
- **Regularly review reminders** to keep them current
- **Delete completed reminders** to maintain a clean list
- **Use action buttons** for quick interactions without typing commands
- **Check reminder status** to prioritize urgent items

## 🚨 Troubleshooting
- **Reminder not set**: Ensure the date/time format is correct (YYYY-MM-DD HH:MM)
- **Reminder not found**: Check the reminder ID or use the reminder list
- **Action buttons not working**: Refresh the list or use command alternatives
- **Snooze not working**: Check if the reminder is still active
- **Edit functionality**: Reminder editing is currently a placeholder - use command alternatives

## 🔄 Integration
- **Event-driven updates**: Reminder actions emit events for other plugins
- **Database persistence**: All reminder data is stored securely
- **Real-time feedback**: Immediate updates and visual confirmation
- **Task integration**: Seamless task completion from reminders

## 🌍 Timezone Handling

All reminder times in LarryBot2 are displayed in your configured or automatically detected local timezone. Internally, all times are stored in UTC for reliability and consistency. Daylight Saving Time (DST) is handled automatically for all supported timezones.

- **Local Display**: Reminders, due dates, and snooze times are always shown in your local time.
- **UTC Storage**: All reminder times are stored in UTC in the database.
- **Manual Override**: Use `/timezone` to set your timezone, or `/autotimezone` to reset to automatic detection.
- **DST Support**: DST changes are handled automatically.
- **Fallback**: If timezone detection fails, UTC is used as a safe default.

> **Tip:** If your reminders appear at the wrong time, check your timezone setting with `/timezone`.

---

**Related Commands**: [Task Management](task-management.md) → [Calendar Integration](calendar-integration.md) → [Habits](habits.md) 