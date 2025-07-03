---
title: Reminders Commands
description: Set up smart reminders to never miss important deadlines
last_updated: 2025-07-02
---

# Reminders Commands ⏰

Never miss important deadlines again! LarryBot2's smart reminder system helps you stay on top of your tasks with timely notifications and flexible snooze options.

## 🎯 What You Can Do

- **Set reminders** for any task with specific times
- **Get notified** when tasks are due
- **Snooze reminders** when you need more time
- **Track overdue items** to stay accountable
- **Manage multiple reminders** with ease

## ⏰ Setting Up Reminders

### Basic Reminder Creation

Set a reminder for a specific task:

```
/addreminder 124 2025-07-03 14:00
```

This creates a reminder for task #124 on July 3rd at 2:00 PM.

### Quick Reminder Creation

Create a reminder for today:

```
/reminder_quick "Pick up dry cleaning"
```

This creates a reminder for today with a simple description.

### Reminder with Task Description

```
/addreminder "Team meeting" 2025-07-03 14:00
```

This creates a reminder with a description and specific time.

## 📋 Managing Your Reminders

### View All Reminders

See all your active reminders:

```
/reminders
```

This shows all reminders with interactive buttons for quick actions.

### Reminder Status

Your reminders are color-coded for easy identification:

- **🔴 Overdue** - Past due time
- **🟡 Today** - Due today
- **🟢 Upcoming** - Due in the future
- **✅ Completed** - Task is done

### Reminder Actions

Each reminder comes with interactive buttons:

- **✅ Complete** - Mark the task as done
- **⏰ Snooze 1h** - Snooze for 1 hour
- **⏰ Snooze 1d** - Snooze for 1 day
- **✏️ Edit** - Change the reminder time
- **🗑️ Delete** - Remove the reminder

## 🔄 Snoozing Reminders

### When You Need More Time

Sometimes you need a little extra time. Use snooze options:

**Snooze for 1 hour:**
- Click **⏰ Snooze 1h** button
- Reminder will trigger again in 1 hour

**Snooze for 1 day:**
- Click **⏰ Snooze 1d** button
- Reminder will trigger again tomorrow

### Snooze Example

When you snooze a reminder, you'll see:

```
⏰ Reminder Snoozed

📝 Task: Complete project proposal
⏰ New Due: 2025-07-03 15:00 (in 1 hour)
📅 Snoozed: 2025-07-03 14:00

The reminder has been snoozed for 1 hour.

[✅ Mark Done] [⏰ Snooze Again]
[👁️ View Task] [🗑️ Delete Reminder]
```

## 📅 Reminder Notifications

### When Reminders Trigger

You'll receive a notification like this:

```
⏰ Reminder

📝 Task: Complete project proposal
🆔 ID: 124
⏰ Due: 2025-07-03 14:00
📅 Created: 2025-07-02 10:30

This task is due now!

[✅ Mark Done] [⏰ Snooze 1h]
[⏰ Snooze 1d] [🗑️ Delete Reminder]
[👁️ View Task] [❌ Dismiss]
```

### Taking Action

When you receive a reminder, you can:

- **✅ Mark Done** - Complete the task immediately
- **⏰ Snooze 1h** - Get reminded again in 1 hour
- **⏰ Snooze 1d** - Get reminded again tomorrow
- **🗑️ Delete Reminder** - Remove the reminder permanently
- **👁️ View Task** - See full task details
- **❌ Dismiss** - Ignore for now

## 🗑️ Removing Reminders

### Delete a Reminder

Remove a reminder you no longer need:

```
/delreminder 1
```

This deletes reminder #1 with a confirmation dialog.

### Bulk Reminder Management

Use interactive buttons to manage multiple reminders:

- Click **🗑️ Delete** next to any reminder
- Confirm deletion in the dialog
- Reminder is permanently removed

## 📊 Reminder Statistics

### Track Your Reminder Usage

Get insights into your reminder patterns:

```
/reminder_stats
```

This shows:
- Total reminders created
- Completion rates
- Average response time
- Most common reminder times

## 🎯 Pro Tips

### Set Effective Reminders

**For important deadlines:**
```
/addreminder "Submit quarterly report" 2025-07-15 17:00
```

**For daily tasks:**
```
/reminder_quick "Take medication"
/reminder_quick "Check email"
```

**For meetings:**
```
/addreminder "Team standup" 2025-07-03 09:00
/addreminder "Client call with Sarah" 2025-07-03 14:00
```

### Use Snooze Wisely

- **Snooze 1h** when you need a short delay
- **Snooze 1d** when you need to reschedule for tomorrow
- **Complete immediately** when you can do it now

### Organize Your Reminders

**Work reminders:**
```
/addreminder "Review project timeline" 2025-07-03 10:00 work
/addreminder "Follow up on client proposal" 2025-07-04 15:00 work
```

**Personal reminders:**
```
/addreminder "Call mom" 2025-07-03 19:00 personal
/addreminder "Pick up groceries" 2025-07-03 18:00 personal
```

### Morning Routine Reminders

Set up reminders for your daily routine:

```
/reminder_quick "Morning workout"
/reminder_quick "Review today's priorities"
/reminder_quick "Check calendar"
```

### End-of-Day Reminders

Plan for tomorrow:

```
/addreminder "Prepare for tomorrow's meeting" 2025-07-02 17:00
/addreminder "Pack lunch for tomorrow" 2025-07-02 20:00
```

## 🆘 Getting Help

### Reminder Help

```
/help reminders
```

Get help with reminder commands.

### Check Reminder Status

```
/reminders
```

See all your active reminders.

### Reminder Statistics

```
/reminder_stats
```

View your reminder usage patterns.

## 🎯 Common Use Cases

### Work Deadlines

**Project deadlines:**
```
/addreminder "Submit project proposal" 2025-07-10 17:00
/addreminder "Review team feedback" 2025-07-08 14:00
/addreminder "Schedule client meeting" 2025-07-05 16:00
```

### Personal Tasks

**Daily tasks:**
```
/reminder_quick "Take vitamins"
/reminder_quick "Water plants"
/reminder_quick "Check mail"
```

**Appointments:**
```
/addreminder "Dentist appointment" 2025-07-15 14:00
/addreminder "Hair appointment" 2025-07-12 10:00
```

### Health and Wellness

**Exercise reminders:**
```
/reminder_quick "Go for a walk"
/reminder_quick "Stretch break"
/reminder_quick "Drink water"
```

**Health appointments:**
```
/addreminder "Annual checkup" 2025-07-20 09:00
/addreminder "Eye exam" 2025-07-25 15:00
```

---

**Never miss another deadline!** Start with a simple reminder: `/reminder_quick "Test reminder"` and see how LarryBot2 keeps you on track.

---

**Next Steps:**
- [Habits](habits.md) - Build productive habits
- [Calendar Integration](calendar-integration.md) - Sync with Google Calendar
- [Task Management](task-management.md) - Master task creation and management
- [Examples](../examples.md) - See real-world reminder use cases 