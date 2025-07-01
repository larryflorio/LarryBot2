---
title: Analytics Feature Guide
description: Task and client analytics in LarryBot2
last_updated: 2025-06-28
---

# Analytics Feature Guide 📊

LarryBot2 provides powerful analytics to help you understand your productivity, task completion, and client engagement.

## 📈 Analytics Commands

### `/analytics` - Task Analytics
View comprehensive analytics about your tasks.

**Usage**: `/analytics`

**Response**:
```
📊 Task Analytics

📈 Overview:
• Total Tasks: 45
• Completed: 32
• Pending: 13
• Completion Rate: 71%

⏰ Time Tracking:
• Total Time Tracked: 127h 30m
• Average Task Duration: 2h 15m
• Most Productive Day: Wednesday

📊 Priority Distribution:
• Critical: 8 (18%)
• High: 15 (33%)
• Medium: 18 (40%)
• Low: 4 (9%)

🏷️ Category Breakdown:
• Work: 28 (62%)
• Personal: 12 (27%)
• Urgent: 5 (11%)

📅 Weekly Progress:
• This Week: 12 tasks completed
• Last Week: 8 tasks completed
• Trend: +50% improvement
```

### `/clientanalytics` - Client Analytics
Show analytics for all clients.

**Usage**: `/clientanalytics`

**Response**:
```
📊 Client Analytics
• Total Clients: 12
• Tasks Assigned: 45
• Most Active Client: Acme Corp
• Least Active Client: Beta LLC
```

## 🛠️ Best Practices
- Review analytics weekly to track progress
- Use category and priority breakdowns to identify focus areas
- Monitor client analytics for engagement

## 🚨 Troubleshooting
- **No data**: Ensure you have created tasks and assigned clients
- **Analytics not updating**: Try `/analytics` after adding new data

---

**Related Guides**: [Task Management](../commands/task-management.md) → [Client Management](../commands/client-management.md) 