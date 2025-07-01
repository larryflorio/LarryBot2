---
title: Habits Commands
description: Build and track habits in LarryBot2 with enhanced action buttons
last_updated: 2025-01-27
---

# Habits Commands 🎯

LarryBot2 helps you build and track productive habits with enhanced action buttons for quick interactions. This guide covers all habit commands and features.

## 🎯 Habit Commands

### `/habit_add` - Add Habit
Add a new habit to track.

**Usage**: `/habit_add <name>`

**Examples**:
```
/habit_add Morning Run
/habit_add Read 30 Minutes
```

**Response**:
```
✅ Habit 'Morning Run' created successfully!

Habit ID: 1
Habit Name: Morning Run
Current Streak: 0 days
Created At: 2025-01-27 10:30
```

### `/habit_done` - Mark Habit Complete
Mark a habit as completed for the day.

**Usage**: `/habit_done <name>`

**Examples**:
```
/habit_done Morning Run
/habit_done Read 30 Minutes
```

**Response**:
```
✅ Habit completed for today! 🔥

Habit: Morning Run
Current Streak: 7 days 🔥
Last Completed: 2025-01-27 10:30

🎉 7-day streak milestone!
```

### `/habit_list` - List Habits
List all your tracked habits with action buttons for quick interactions.

**Usage**: `/habit_list`

**Features**:
- **Per-habit action buttons**: Complete, Progress, Delete for each habit
- **Smart completion detection**: Only shows "Complete" button for habits not done today
- **Visual status indicators**: Shows completion status with emojis
- **Navigation buttons**: Add Habit, Statistics, Refresh, Back to Main

**Response**:
```
🔄 All Habits (3 found)

1. ✅ Morning Run
   🔥 Streak: 7 days
   📅 Completed today
   🕐 Last: 2025-01-27
   📅 Created: 2025-01-20

2. ⚠️ Read 30 Minutes
   📈 Streak: 3 days
   📅 Missed yesterday
   🕐 Last: 2025-01-25
   📅 Created: 2025-01-22

[✅ Complete] [📊 Progress] [🗑️ Delete]
[✅ Complete] [📊 Progress] [🗑️ Delete]

[➕ Add Habit] [📊 Statistics]
[🔄 Refresh] [⬅️ Back]
```

### `/habit_delete` - Delete Habit
Delete a habit from your list with confirmation dialog.

**Usage**: `/habit_delete <name>`

**Examples**:
```
/habit_delete Morning Run
/habit_delete Read 30 Minutes
```

**Response**:
```
🗑️ Confirm Habit Deletion

Habit: Morning Run
Current Streak: 7 days
Created: 2025-01-20

⚠️ Warning: This will permanently delete the habit and all progress data.

Are you sure you want to delete this habit?

[✅ Confirm Delete] [❌ Cancel]
```

### `/habit_progress` - View Habit Progress
View detailed progress and statistics for a specific habit.

**Usage**: `/habit_progress <name>`

**Features**:
- **Progress visualization**: Visual progress bar showing completion rate
- **Milestone tracking**: Shows next milestone and days needed
- **Recent activity**: Last completion status
- **Action buttons**: Complete Today, Back to Habits

**Response**:
```
📊 Habit Progress Report

Habit: Morning Run
Current Streak: 7 days
Days Tracked: 8 days
Completion Rate: 87.5%

📈 Progress Bar
██████████████████████████████░░
  7 /  8 days

🎯 Next Milestone
• Target: 30 days
• Days needed: 23

📅 Recent Activity
• Last completed: Today ✅

[✅ Complete Today] [⬅️ Back to Habits]
```

### `/habit_stats` - Habit Statistics
View comprehensive statistics for all your habits.

**Usage**: `/habit_stats`

**Features**:
- **Overall statistics**: Total habits, total streak days, average streak
- **Today's completion**: Shows completion rate for today
- **Best performer**: Highlights the habit with the longest streak
- **Visual charts**: Bar chart showing current streaks

**Response**:
```
📊 Habit Statistics

Total Habits: 3
Total Streak Days: 15
Average Streak: 5.0 days
Completed Today: 1/3
Today's Rate: 33.3%

🏆 Best Performer
• Morning Run
• Streak: 7 days

📈 Streak Overview
Morning Run: ████████████████ 7
Read 30 Min: ████████ 3
Meditation: █████ 2

[🔄 Refresh] [⬅️ Back to Habits]
```

## 🎮 Action Buttons

### Habit List Actions
When you use `/habit_list`, each habit displays action buttons:

- **✅ Complete**: Mark habit as done for today (only shown if not completed today)
- **📊 Progress**: View detailed progress report for the habit
- **🗑️ Delete**: Delete the habit with confirmation dialog

### Navigation Actions
- **➕ Add Habit**: Shows instructions for adding a new habit
- **📊 Statistics**: View comprehensive habit statistics
- **🔄 Refresh**: Reload the habit list with current data
- **⬅️ Back**: Return to main menu

### Progress View Actions
- **✅ Complete Today**: Mark the habit as done from the progress view
- **⬅️ Back to Habits**: Return to the habit list

## 🏆 Streak Milestones

LarryBot2 celebrates your habit streaks with special milestones:

- **7 days**: 🎉 7-day streak milestone!
- **30 days**: 🏆 30-day streak milestone!
- **100 days**: 👑 100-day streak milestone!

## 🛠️ Best Practices
- **Track habits daily** for consistency and accurate streak counting
- **Use clear, specific habit names** for better tracking
- **Review your streaks regularly** for motivation and progress
- **Use action buttons** for quick interactions without typing commands
- **Check progress views** to understand your completion patterns

## 🚨 Troubleshooting
- **Habit not found**: Ensure the habit name is correct or check the habit list
- **Completion not recorded**: Try again or check if already completed today
- **Action buttons not working**: Refresh the list or use command alternatives
- **Progress not updating**: Use the refresh button to get latest data

## 🔄 Integration
- **Event-driven updates**: Habit actions emit events for other plugins
- **Database persistence**: All habit data is stored securely
- **Real-time feedback**: Immediate updates and visual confirmation

---

**Related Commands**: [Task Management](task-management.md) → [Client Management](client-management.md) → [Analytics](../features/analytics.md) 