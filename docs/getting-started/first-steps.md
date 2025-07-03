---
title: First Steps with LarryBot2
description: Learn your first commands and start using LarryBot2 effectively
last_updated: 2025-07-02
---

# First Steps with LarryBot2 🚀

> **Breadcrumbs:** [Home](../../README.md) > [Getting Started](README.md) > First Steps

Welcome! This guide will help you get started with LarryBot2 and learn your first commands. You'll be managing tasks like a pro in no time.

## 🎯 What You'll Learn

By the end of this guide, you'll know how to:
- Create and manage tasks
- Set up reminders
- Track habits
- Use interactive buttons
- Find your tasks quickly

## 📋 Your First Task

Let's start with the basics - creating your first task.

### Step 1: Create a Simple Task

Send this message to your bot:
```
/add Buy groceries
```

You should see a response like:
```
✅ Task added successfully!

📋 Details:
   • Task: Buy groceries
   • ID: 123
   • Status: Todo
   • Created: 2025-07-02 10:30

[👁️ View] [✅ Done] [✏️ Edit] [🗑️ Delete]
```

### Step 2: View Your Tasks

Send this command to see all your tasks:
```
/list
```

This shows all your incomplete tasks with interactive buttons for quick actions.

### Step 3: Mark a Task Complete

Click the **✅ Done** button next to your task, or send:
```
/done 123
```

## ⏰ Setting Up Reminders

Never miss important deadlines with smart reminders.

### Create a Reminder

```
/addreminder "Team meeting" 2025-07-03 14:00
```

This creates a reminder for a team meeting on July 3rd at 2:00 PM.

### View Your Reminders

```
/reminders
```

See all your active reminders with options to snooze or complete them.

## 📈 Building Habits

Track daily habits to build better routines.

### Start a New Habit

```
/habit_add "Daily exercise" "Exercise for 30 minutes"
```

This creates a habit called "Daily exercise" with a description.

### Mark a Habit Complete

```
/habit_done 1
```

Or click the **✅ Complete** button next to your habit.

### Check Your Progress

```
/habit_progress 1
```

See your habit streak and progress over time.

## 🎮 Using Interactive Buttons

LarryBot2 makes task management effortless with interactive buttons.

### Task Buttons
- **👁️ View** - See detailed task information
- **✅ Done** - Mark task complete
- **✏️ Edit** - Update task details
- **🗑️ Delete** - Remove task

### Navigation Buttons
- **➕ Add Task** - Create a new task
- **🔄 Refresh** - Update your list
- **⬅️ Back** - Go back to previous view

## 🔍 Finding Your Tasks

### Basic Search

```
/search groceries
```

Find tasks containing "groceries" in the description.

### Filter by Priority

```
/list high
```

Show only high-priority tasks.

### Filter by Category

```
/list work
```

Show only work-related tasks.

## 📅 Calendar Integration

Connect your Google Calendar for seamless scheduling.

### Connect Your Calendar

```
/connect_google
```

Follow the instructions to link your Google Calendar.

### View Your Schedule

```
/agenda
```

See your upcoming calendar events.

## 📊 Productivity Insights

Get insights into your productivity patterns.

### Basic Analytics

```
/analytics
```

See your task completion rates and productivity trends.

### Detailed Report

```
/productivity_report
```

Get a comprehensive productivity report.

## 🎯 Pro Tips

### Use Natural Language

LarryBot2 understands natural language:
```
/add "Call client about project proposal" high 2025-07-05 work
```

This creates a high-priority work task due July 5th.

### Quick Reminders

```
/reminder_quick "Pick up dry cleaning"
```

Creates a reminder for today.

### Bulk Operations

Manage multiple tasks at once:
```
/bulk_status 1,2,3 done
```

Mark tasks 1, 2, and 3 as complete.

## 🆘 Getting Help

### Check System Status

```
/health
```

See if everything is working properly.

### Get Command Help

```
/help
```

See all available commands.

### Quick Health Check

```
/health_quick
```

Get a quick system status.

## 🎉 Congratulations!

You've learned the basics of LarryBot2! Here's what you can do next:

### Explore More Features
- **[Advanced Task Features](../user-guide/features/advanced-tasks.md)** - Learn about subtasks, dependencies, and file attachments
- **[Client Management](../user-guide/commands/client-management.md)** - Organize work by clients
- **[File Attachments](../user-guide/features/file-attachments.md)** - Keep files organized with your tasks

### Real-World Examples
- **[Command Examples](../user-guide/examples.md)** - See how others use LarryBot2
- **[Use Cases](../user-guide/examples.md)** - Common productivity scenarios

### When You Need Help
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions
- **[Getting Help](../troubleshooting/getting-help.md)** - How to get support

---

**Ready to boost your productivity?** Try creating a few more tasks and explore the interactive features. LarryBot2 is designed to grow with you as your productivity needs evolve!

---

**Next Steps:**
- [Task Management Commands](../user-guide/commands/task-management.md)
- [Reminders Guide](../user-guide/commands/reminders.md)
- [Habits Guide](../user-guide/commands/habits.md) 