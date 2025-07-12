---
title: Task Management Commands
description: Create, edit, and manage tasks with LarryBot2's powerful task management system
last_updated: 2025-07-07
---

# Task Management Commands 📋

LarryBot2 makes task management effortless with powerful commands that help you stay organized and productive. Whether you're managing work projects, personal tasks, or daily routines, these commands will help you get things done.

## 🎯 What You Can Do

- **Create tasks** with natural language
- **Organize tasks** by priority, due date, and category
- **Track progress** with status updates
- **Find tasks quickly** with powerful search
- **Manage multiple tasks** with bulk operations
- **Get insights** into your productivity

## 📝 Creating Tasks

### Basic Task Creation

The simplest way to create a task:

```
/add Buy groceries
```

This creates a basic task with default settings.

### Advanced Task Creation

Add more details to your tasks:

```
/add "Complete project proposal" high 2025-07-05 work
```

This creates a high-priority work task due July 5th.

**Format:** `/add "description" [priority] [due_date] [category]`

### Guided Task Creation

Use the interactive narrative flow for step-by-step task creation:

```
/addtask
```

This starts a guided conversation where LarryBot2 asks you:
1. **Task description** - What needs to be done?
2. **Due date** - When is it due? (supports natural language like "Monday", "next week")
3. **Priority** - How urgent is it?
4. **Category** - What type of task is it?
5. **Client** (optional) - Who is this for?

**Natural Language Due Dates in Guided Flow:**
- "Monday", "Friday", "next Monday"
- "today", "tomorrow", "next week"
- "this weekend", "in 3 days", "next month"

**Examples:**
```
/add "Call client about project" high 2025-07-01 work
/add "Buy birthday gift" medium 2025-07-01 personal
/add "Schedule team meeting" critical 2025-06-30 work
```

### Task Priorities

Set task priorities to focus on what matters most:

- **`low`** - Not urgent, can wait
- **`medium`** - Normal priority
- **`high`** - Important, needs attention
- **`critical`** - Urgent, must be done soon

### Due Dates

Set due dates using natural language or YYYY-MM-DD format:

**Natural Language Examples:**
```
/add "Review quarterly reports" "next Monday"
/add "Submit expense report" "tomorrow"
/add "Buy groceries" "this weekend"
/add "Call client" "next week"
/add "Schedule meeting" "Friday"
```

**Structured Format:**
```
/add "Review quarterly reports" 2025-07-15
/add "Submit expense report" 2025-07-01
```

**Supported Natural Language:**
- Day names: "Monday", "Friday", "next Monday"
- Relative dates: "today", "tomorrow", "next week", "this weekend"
- Time periods: "in 3 days", "next month", "end of month"

### Categories

Organize tasks by category:

```
/add "Buy groceries" personal
/add "Complete project proposal" work
/add "Exercise" health
```

## 📋 Managing Your Tasks

### View Your Tasks

See all your incomplete tasks:

```
/list
```

This shows your tasks with interactive buttons for quick actions.

### Filter Your Tasks

Find specific tasks quickly:

```
/list todo          # Show only todo tasks
/list high          # Show only high-priority tasks
/list work          # Show only work tasks
/list todo high     # Show high-priority todo tasks
```

### Search Your Tasks

Find tasks by description:

```
/search groceries
/search project
/search meeting
```

### Advanced Search

Use powerful search filters:

```
/search_advanced "project proposal" high work
```

## ✅ Completing Tasks

### Mark Tasks Complete

Click the **✅ Done** button next to a task, or use:

```
/done 123
```

### Bulk Completion

Complete multiple tasks at once:

```
/bulk_status 1,2,3 done
```

This marks tasks 1, 2, and 3 as complete.

## ✏️ Editing Tasks

### Update Task Details

Click the **✏️ Edit** button next to a task, or use:

```
/edit 123 "Updated task description"
```

### Change Task Priority

```
/priority 123 high
```

### Set Due Date

```
/due 123 2025-07-15
```

### Change Category

```
/category 123 work
```

## 🗑️ Removing Tasks

### Delete a Task

Click the **🗑️ Delete** button next to a task, or use:

```
/remove 123
```

### Bulk Deletion

Delete multiple tasks:

```
/bulk_delete 1,2,3
```

## 📊 Task Organization

### Task Status

Track your progress with task status:

- **`todo`** - Not started yet
- **`in_progress`** - Currently working on it
- **`review`** - Ready for review
- **`done`** - Completed

### Change Task Status

```
/status 123 in_progress
```

### Bulk Status Updates

```
/bulk_status 1,2,3 in_progress
```

## 🔍 Finding Tasks

### Filter by Status

```
/tasks todo
/tasks done
/tasks in_progress
```

### Filter by Priority

```
/tasks high
/tasks critical
/tasks medium
```

### Filter by Category

```
/tasks work
/tasks personal
/tasks health
```

### Advanced Filtering

Combine multiple filters:

```
/filter_advanced status=todo priority=high category=work
```

### Time-Based Filtering

Find tasks by time:

```
/today          # Tasks due today
/week           # Tasks due this week
/overdue        # Overdue tasks
/time_range 2025-07-01 2025-07-31  # Tasks in date range
```

## 📈 Productivity Insights

### Basic Analytics

Get insights into your productivity:

```
/analytics
```

See your task completion rates and trends.

### Detailed Analytics

```
/analytics_detailed
```

Get comprehensive productivity insights.

### Productivity Report

```
/productivity_report
```

Generate a detailed productivity report.

### Smart Suggestions

Get intelligent task suggestions:

```
/suggest
```

LarryBot2 analyzes your patterns and suggests what to work on next.

## 🎮 Interactive Features

### Action Buttons

Every task comes with interactive buttons:

- **👁️ View** - See detailed task information
- **✅ Done** - Mark task complete
- **✏️ Edit** - Update task details
- **🗑️ Delete** - Remove task

### Navigation Buttons

- **➕ Add Task** - Create a new task
- **🔄 Refresh** - Update your task list
- **⬅️ Back** - Go back to previous view

## 🎯 Pro Tips

### Use Natural Language

LarryBot2 understands natural language:

```
/add "Call Sarah about the Johnson project tomorrow at 2pm" high work
```

### Quick Task Creation

For simple tasks, just describe what you need to do:

```
/add "Pick up dry cleaning"
/add "Send follow-up email"
/add "Review meeting notes"
```

### Organize by Project

Use categories to organize by project:

```
/add "Design homepage mockup" high 2025-07-10 website-project
/add "Write content for about page" medium 2025-07-12 website-project
```

### Track Progress

Update task status as you work:

```
/status 123 in_progress    # Start working
/status 123 review         # Ready for review
/done 123                  # Complete the task
```

### Use Bulk Operations

Save time with bulk operations:

```
/bulk_status 1,2,3,4,5 in_progress  # Start multiple tasks
/bulk_priority 1,2,3 high           # Set priority for multiple tasks
/bulk_delete 10,11,12               # Remove multiple tasks
```

## 🆘 Getting Help

### Command Help

```
/help
```

See all available commands.

### Task Help

```
/help tasks
```

Get help with task management commands.

### System Status

```
/health
```

Check if everything is working properly.

---

**Ready to get organized?** Start with a simple task: `/add "Learn LarryBot2 commands"` and explore the interactive features!

---

**Next Steps:**
- [Reminders](../reminders.md) - Set up smart reminders
- [Habits](../habits.md) - Build productive habits
- [Calendar Integration](../calendar-integration.md) - Sync with Google Calendar
- [Advanced Features](../features/advanced-tasks.md) - Learn advanced task capabilities