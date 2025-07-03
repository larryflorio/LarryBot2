---
title: Calendar Integration Commands
description: Sync with Google Calendar for seamless scheduling
last_updated: 2025-07-02
---

# Calendar Integration Commands 📅

Keep your schedule organized by connecting LarryBot2 with your Google Calendar. View upcoming events, sync your schedule, and never miss important meetings or appointments.

## 🎯 What You Can Do

- **Connect to Google Calendar** for seamless integration
- **View your agenda** and upcoming events
- **Sync calendar events** with your task management
- **Stay on top of meetings** and appointments
- **Plan your day** with calendar context

## 🔗 Connecting Your Calendar

### Connect to Google Calendar

Link your Google Calendar account:

```
/connect_google
```

This starts the connection process. Follow the instructions to authorize LarryBot2 to access your calendar.

### What Happens When You Connect

After connecting, LarryBot2 can:
- Read your calendar events
- Show your upcoming schedule
- Help you plan around existing commitments
- Sync event information with your tasks

### Security and Privacy

- LarryBot2 only reads your calendar (doesn't create or modify events)
- Your calendar data stays private and secure
- You can disconnect at any time
- No calendar data is stored permanently

## 📅 Viewing Your Schedule

### See Today's Agenda

View your upcoming events for today:

```
/agenda
```

This shows all your scheduled events for the day.

### Calendar Overview

Get a broader view of your schedule:

```
/calendar
```

This provides an overview of your calendar with upcoming events.

### List Calendar Events

See all your upcoming events:

```
/calendar_events
```

This lists all events in your calendar with details.

## 🔄 Syncing Your Calendar

### Sync Calendar Data

Update your calendar information:

```
/calendar_sync
```

This refreshes your calendar data to show the latest events.

### Automatic Syncing

LarryBot2 automatically syncs your calendar:
- When you first connect
- When you view your agenda
- Periodically to keep data current

## 📊 Calendar Features

### Event Information

Each calendar event shows:
- **Event title** and description
- **Date and time** (start and end)
- **Location** (if specified)
- **Attendees** (if it's a meeting)
- **Recurring status** (if it repeats)

### Time Zone Support

All times are displayed in your local timezone:
- Events are shown in your local time
- Timezone changes are handled automatically
- Daylight saving time is supported

## 🎯 Pro Tips

### Plan Around Your Calendar

**Check your schedule before adding tasks:**
```
/agenda
/add "Prepare for team meeting" high 2025-07-03 08:00
```

**Use calendar context for task planning:**
```
/calendar
/add "Review project proposal" high 2025-07-03 16:00
```

### Combine with Reminders

**Set reminders for calendar events:**
```
/agenda
/addreminder "Team meeting" 2025-07-03 09:00
```

**Create task reminders for preparation:**
```
/addreminder "Prepare meeting notes" 2025-07-03 08:30
```

### Daily Planning

**Morning routine with calendar check:**
```
/agenda
/add "Review today's meetings" high
/add "Prepare for client call" high
```

**End-of-day planning:**
```
/calendar
/add "Prepare for tomorrow's presentation" high
```

## 🔌 Managing Your Connection

### Disconnect Your Calendar

Remove the calendar connection:

```
/disconnect
```

This disconnects LarryBot2 from your Google Calendar.

### When to Disconnect

Consider disconnecting when:
- You're not using calendar features
- You want to limit data access
- You're troubleshooting connection issues
- You're switching Google accounts

### Reconnecting

To reconnect after disconnecting:
```
/connect_google
```

Follow the authorization process again.

## 🆘 Getting Help

### Calendar Help

```
/help calendar
```

Get help with calendar commands.

### Check Connection Status

```
/agenda
```

If connected, this shows your events. If not, you'll see connection instructions.

### Troubleshooting

**Connection issues:**
- Check your internet connection
- Verify your Google account credentials
- Try disconnecting and reconnecting
- Check Google Calendar permissions

**No events showing:**
- Ensure your calendar has upcoming events
- Check your calendar sharing settings
- Try syncing manually with `/calendar_sync`

## 🎯 Common Use Cases

### Work Schedule Management

**Daily standup preparation:**
```
/agenda
/add "Prepare standup updates" high
```

**Meeting preparation:**
```
/calendar
/add "Review meeting agenda" high
/add "Prepare presentation slides" high
```

**Project planning:**
```
/calendar
/add "Schedule project review" high
/add "Book team meeting" high
```

### Personal Schedule

**Appointment reminders:**
```
/agenda
/addreminder "Dentist appointment" 2025-07-15 14:00
```

**Social events:**
```
/calendar
/add "Buy birthday gift" high
/add "Prepare for dinner party" high
```

### Travel Planning

**Trip preparation:**
```
/calendar
/add "Book flight" high
/add "Pack luggage" high
/add "Arrange airport pickup" high
```

**Meeting scheduling:**
```
/calendar
/add "Schedule client meetings" high
/add "Book hotel" high
```

## 🔄 Integration with Other Features

### Calendar + Tasks

**Create tasks from calendar events:**
```
/agenda
/add "Prepare for team meeting" high
/add "Review quarterly reports" high
```

### Calendar + Reminders

**Set reminders for calendar events:**
```
/calendar
/addreminder "Team meeting" 2025-07-03 09:00
/addreminder "Client presentation" 2025-07-03 14:00
```

### Calendar + Habits

**Build calendar-checking habits:**
```
/habit_add "Check calendar"
/habit_add "Review daily schedule"
```

## 📱 Mobile Usage

### Quick Calendar Check

On mobile, quickly check your schedule:
```
/agenda
```

### Voice Commands

Use natural language:
```
"Show my calendar"
"What's on my agenda today?"
"Sync my calendar"
```

---

**Keep your schedule organized!** Connect your Google Calendar with `/connect_google` and start planning your day with context.

---

**Next Steps:**
- [Task Management](task-management.md) - Create and manage tasks
- [Reminders](reminders.md) - Set up smart reminders
- [Habits](habits.md) - Build productive habits
- [Examples](../examples.md) - See real-world calendar integration examples 