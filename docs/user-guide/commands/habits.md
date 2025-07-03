---
title: Habits Commands
description: Build productive habits and track your progress
last_updated: 2025-07-02
---

# Habits Commands 🎯

Build lasting habits and track your progress with LarryBot2's habit tracking system. Whether you want to exercise daily, read more, or develop any positive routine, LarryBot2 helps you stay consistent and motivated.

## 🎯 What You Can Do

- **Create habits** for any daily activity
- **Track your progress** with visual streaks
- **Stay motivated** with milestone celebrations
- **Monitor consistency** with detailed statistics
- **Build lasting routines** through daily tracking

## 📝 Creating Habits

### Start a New Habit

Create a habit to track:

```
/habit_add "Morning exercise"
```

This creates a new habit called "Morning exercise" that you can track daily.

### Add a Description

Include more details about your habit:

```
/habit_add "Read before bed" "Read for 20 minutes each night"
```

This creates a habit with a name and description.

### Examples of Good Habits

**Health and Fitness:**
```
/habit_add "Daily workout"
/habit_add "Drink water"
/habit_add "Take vitamins"
/habit_add "Morning stretch"
```

**Learning and Growth:**
```
/habit_add "Read daily"
/habit_add "Practice guitar"
/habit_add "Learn new skill"
/habit_add "Journal writing"
```

**Productivity:**
```
/habit_add "Review priorities"
/habit_add "Check email"
/habit_add "Plan tomorrow"
/habit_add "Declutter workspace"
```

## ✅ Completing Habits

### Mark a Habit Complete

When you complete your habit for the day:

```
/habit_done "Morning exercise"
```

This marks the habit as complete and updates your streak.

### Using Interactive Buttons

You can also click the **✅ Complete** button next to any habit in your list.

### Daily Completion

Each habit can only be completed once per day. If you try to complete it again, you'll see a message that it's already done for today.

## 📋 Managing Your Habits

### View All Habits

See all your tracked habits:

```
/habit_list
```

This shows all your habits with their current status and interactive buttons.

### Habit Status

Your habits are color-coded for easy identification:

- **✅ Completed today** - You've done this habit today
- **⚠️ Missed yesterday** - You didn't complete it yesterday
- **📅 Not done today** - Haven't completed it yet today

### Habit Actions

Each habit comes with interactive buttons:

- **✅ Complete** - Mark the habit as done for today
- **📊 Progress** - View detailed progress and statistics
- **🗑️ Delete** - Remove the habit from tracking

## 📊 Tracking Progress

### View Habit Progress

Get detailed insights into a specific habit:

```
/habit_progress "Morning exercise"
```

This shows:
- Current streak length
- Completion rate
- Days tracked
- Next milestone
- Recent activity

### Progress Visualization

See your progress with visual indicators:

```
📊 Habit Progress Report

Habit: Morning exercise
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
```

### Overall Statistics

View statistics for all your habits:

```
/habit_stats
```

This shows:
- Total habits you're tracking
- Overall completion rates
- Best performing habit
- Today's completion status

## 🔥 Streaks and Motivation

### Understanding Streaks

A streak is the number of consecutive days you've completed a habit. The longer your streak, the more motivated you'll be to keep going!

**Streak Examples:**
- **1 day** - Great start! Keep it up!
- **7 days** - One week! You're building momentum!
- **30 days** - One month! This is becoming a habit!
- **100 days** - Incredible! You're unstoppable!

### Milestone Celebrations

LarryBot2 celebrates your achievements:

```
✅ Habit completed for today! 🔥

Habit: Morning exercise
Current Streak: 7 days 🔥
Last Completed: 2025-07-02 10:30

🎉 7-day streak milestone!
```

### Breaking Streaks

If you miss a day, your streak resets to 0. Don't worry! Every day is a new opportunity to start fresh.

## 🗑️ Managing Habits

### Delete a Habit

Remove a habit you no longer want to track:

```
/habit_delete "Morning exercise"
```

This removes the habit and all its progress data.

### When to Delete Habits

Consider deleting a habit when:
- You've successfully built the habit and no longer need to track it
- The habit no longer fits your goals
- You want to focus on different habits
- You're overwhelmed with too many habits

## 🎯 Pro Tips

### Start Small

**Begin with 1-3 habits:**
```
/habit_add "Drink water"
/habit_add "Morning exercise"
/habit_add "Read before bed"
```

Don't try to change everything at once. Focus on building a few solid habits first.

### Be Specific

**Good habit names:**
```
/habit_add "30-minute workout"
/habit_add "Read 20 pages"
/habit_add "Meditate for 10 minutes"
```

**Vague habit names:**
```
/habit_add "Exercise"  # Too vague
/habit_add "Read"      # Not specific enough
/habit_add "Be healthy" # Too broad
```

### Track at the Right Time

**Morning habits:**
```
/habit_add "Morning workout"
/habit_add "Drink water"
/habit_add "Review daily goals"
```

**Evening habits:**
```
/habit_add "Read before bed"
/habit_add "Journal writing"
/habit_add "Plan tomorrow"
```

### Use Reminders

Combine habits with reminders for better consistency:

```
/habit_add "Take vitamins"
/addreminder "Take vitamins" 2025-07-02 09:00
```

### Celebrate Progress

Don't just focus on streaks. Celebrate:
- **First completion** - You started!
- **3-day streak** - Building momentum!
- **7-day streak** - One week!
- **30-day streak** - One month!
- **100-day streak** - Incredible!

## 🆘 Getting Help

### Habit Help

```
/help habits
```

Get help with habit commands.

### Check Habit Status

```
/habit_list
```

See all your habits and their current status.

### View Progress

```
/habit_progress "habit name"
```

Get detailed progress for a specific habit.

### Overall Statistics

```
/habit_stats
```

View comprehensive habit statistics.

## 🎯 Common Habit Examples

### Health and Wellness

**Exercise habits:**
```
/habit_add "Morning workout"
/habit_add "Evening walk"
/habit_add "Stretch break"
/habit_add "Take stairs instead of elevator"
```

**Nutrition habits:**
```
/habit_add "Drink 8 glasses of water"
/habit_add "Take vitamins"
/habit_add "Eat vegetables"
/habit_add "Pack healthy lunch"
```

**Mental health:**
```
/habit_add "Meditate for 10 minutes"
/habit_add "Practice gratitude"
/habit_add "Take deep breaths"
/habit_add "Journal writing"
```

### Learning and Growth

**Reading habits:**
```
/habit_add "Read 20 pages"
/habit_add "Read before bed"
/habit_add "Read during lunch"
/habit_add "Read on weekends"
```

**Skill development:**
```
/habit_add "Practice guitar"
/habit_add "Learn new language"
/habit_add "Write code"
/habit_add "Practice drawing"
```

### Productivity

**Work habits:**
```
/habit_add "Review daily priorities"
/habit_add "Check email twice daily"
/habit_add "Take breaks every hour"
/habit_add "Plan tomorrow"
```

**Organization habits:**
```
/habit_add "Declutter workspace"
/habit_add "File documents"
/habit_add "Update calendar"
/habit_add "Review weekly goals"
```

### Personal Development

**Relationship habits:**
```
/habit_add "Call family member"
/habit_add "Send thank you notes"
/habit_add "Connect with friends"
/habit_add "Practice active listening"
```

**Financial habits:**
```
/habit_add "Track expenses"
/habit_add "Review budget"
/habit_add "Save money"
/habit_add "Check bank account"
```

---

**Start building the habits that will change your life!** Begin with one simple habit: `/habit_add "Drink water"` and watch your consistency grow.

---

**Next Steps:**
- [Task Management](task-management.md) - Create and manage tasks
- [Reminders](reminders.md) - Set up smart reminders
- [Calendar Integration](calendar-integration.md) - Sync with Google Calendar
- [Examples](../examples.md) - See real-world habit-building examples 