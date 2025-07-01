---
title: Client Management Commands
description: Manage clients and assign tasks in LarryBot2 with enhanced action buttons
last_updated: 2025-06-29
---

# Client Management Commands 👥

LarryBot2 allows you to manage clients and assign tasks to them with enhanced action buttons for quick interactions. This guide covers all commands for client management and interactive features.

## 👤 Client Commands

### `/addclient` - Add Client
Add a new client to your system.

**Usage**: `/addclient <name>`

**Examples**:
```
/addclient Acme Corp
/addclient John Doe
```

**Response**:
```
✅ Client 'Acme Corp' added successfully!

📋 **Details:**
   • Client: Acme Corp
   • ID: 1
   • Created: 2025-06-29 10:30
```

### `/removeclient` - Remove Client
Remove a client from your system with confirmation dialog.

**Usage**: `/removeclient <name> [confirm]`

**Examples**:
```
/removeclient Acme Corp confirm
/removeclient John Doe confirm
```

**Response (confirmation dialog)**:
```
🗑️ **Confirm Client Deletion**

**Client**: Acme Corp
**ID**: 1
**Tasks Assigned**: 5
**Created**: 2025-06-20

⚠️ **Warning**: This will permanently delete the client and unassign all associated tasks.

Are you sure you want to delete this client?

[Inline keyboard: Confirm Delete | Cancel]
```

**Response (after confirmation)**:
```
🗑️ Client 'Acme Corp' deleted successfully!

📋 **Details:**
   • Client: Acme Corp
   • ID: 1
   • Tasks Unassigned: 5
   • Action: Client removed from database
```

### `/allclients` - List All Clients
Display a list of all clients with per-client action buttons for quick interactions.

**Usage**: `/allclients`

**Features**:
- **Per-client action buttons**: View, Edit, Delete, Analytics for each client
- **Task statistics**: Shows task count and completion rate for each client
- **Navigation buttons**: Add Client, Refresh, Back to Main
- **Visual indicators**: Shows client activity status with emojis

**Response**:
```
👥 **All Clients** (3 found)

1. 🟢 **Acme Corp** (ID: 1)
   📊 Tasks: 5 (3 completed, 2 pending)
   📈 Completion Rate: 60.0%
   📅 Last Activity: 2025-06-28

2. 🟡 **John Doe** (ID: 2)
   📊 Tasks: 3 (1 completed, 2 pending)
   📈 Completion Rate: 33.3%
   📅 Last Activity: 2025-06-27

3. 🔴 **Beta LLC** (ID: 3)
   📊 Tasks: 0 (no tasks assigned)
   📈 Completion Rate: N/A
   📅 Last Activity: Never

[👁️ View] [✏️ Edit] [🗑️ Delete] [📊 Analytics]
[👁️ View] [✏️ Edit] [🗑️ Delete] [📊 Analytics]
[👁️ View] [✏️ Edit] [🗑️ Delete] [📊 Analytics]

[➕ Add Client] [🔄 Refresh]
[⬅️ Back]
```

### `/assign` - Assign Task to Client
Assign a task to a client.

**Usage**: `/assign <task_id> <client_name>`

**Examples**:
```
/assign 124 Acme Corp
/assign 125 John Doe
```

**Response**:
```
✅ Task #124 assigned to client 'Acme Corp'.

📋 **Details:**
   • Task: Complete project proposal
   • ID: 124
   • Client: Acme Corp
   • Status: Assigned
   • Updated: 2025-06-29 10:35
```

### `/unassign` - Unassign Task
Remove a client assignment from a task.

**Usage**: `/unassign <task_id>`

**Examples**:
```
/unassign 124
/unassign 125
```

**Response**:
```
✅ Task #124 unassigned from client 'Acme Corp'.

📋 **Details:**
   • Task: Complete project proposal
   • ID: 124
   • Previous Client: Acme Corp
   • Status: Unassigned
   • Updated: 2025-06-29 10:40
```

### `/client` - Client Details
Show details for a specific client.

**Usage**: `/client <client_name>`

**Examples**:
```
/client Acme Corp
/client John Doe
```

**Response**:
```
👤 **Client Details**

📋 **Client Information:**
   • Name: Acme Corp
   • ID: 1
   • Created: 2025-06-20 09:15
   • Total Tasks: 5
   • Completed: 3
   • Pending: 2
   • Completion Rate: 60.0%

📊 **Recent Activity:**
   • Last Task Completed: 2025-06-28
   • Last Task Added: 2025-06-27
   • Average Task Duration: 3.2 days
```

### `/clientanalytics` - Client Analytics
Show comprehensive analytics for all clients.

**Usage**: `/clientanalytics`

**Features**:
- **Overall statistics**: Total clients, total tasks, average completion rate
- **Client rankings**: Best and worst performing clients
- **Visual charts**: Bar charts showing client performance
- **Navigation buttons**: Refresh, Back to Clients

**Response**:
```
📊 **Client Analytics**

📈 **Overall Statistics:**
   • Total Clients: 3
   • Total Tasks: 8
   • Average Completion Rate: 50.0%
   • Most Active Client: Acme Corp
   • Least Active Client: Beta LLC

🏆 **Performance Rankings:**
   1. Acme Corp - 60.0% completion (5 tasks)
   2. John Doe - 33.3% completion (3 tasks)
   3. Beta LLC - 0.0% completion (0 tasks)

📊 **Client Performance Chart:**
Acme Corp: ████████████████████ 60%
John Doe:  ████████ 33%
Beta LLC:  ░░░░░░░░ 0%

[🔄 Refresh] [⬅️ Back to Clients]
```

## 🎮 Action Buttons

### Client List Actions
When you use `/allclients`, each client displays action buttons:

- **👁️ View**: Show detailed client information with task statistics
- **✏️ Edit**: Edit client information (placeholder - shows "not implemented")
- **🗑️ Delete**: Delete the client with confirmation dialog
- **📊 Analytics**: View per-client analytics and performance metrics

### Client Detail Actions
When viewing a specific client, you can:

- **✏️ Edit**: Edit client information (placeholder)
- **🗑️ Delete**: Delete the client with confirmation
- **📊 Analytics**: View detailed client analytics
- **⬅️ Back to List**: Return to the client list

### Navigation Actions
- **➕ Add Client**: Shows instructions for adding a new client
- **🔄 Refresh**: Reload the client list with current data
- **⬅️ Back**: Return to main menu

## 🎯 Client View Details

### Client Information Display
The client view shows comprehensive information:

- **Basic Info**: Name, ID, creation date
- **Task Statistics**: Total, completed, pending tasks
- **Performance Metrics**: Completion rate, average task duration
- **Activity Timeline**: Last task completed, last task added

### Task Assignment Management
- **Current Assignments**: List of all tasks assigned to the client
- **Completion Status**: Visual indicators for task progress
- **Performance Trends**: Historical completion data

## 🛠️ Best Practices
- **Use clear, unique client names** for easy identification
- **Regularly review client assignments** to maintain organization
- **Use action buttons** for quick interactions without typing commands
- **Check client analytics** to monitor performance and engagement
- **Use confirmation dialogs** for destructive actions like client deletion
- **Review task completion rates** to identify high-performing clients

## 🚨 Troubleshooting
- **Client not found**: Ensure the client name is correct or check the client list
- **Assignment errors**: Check if the task and client exist
- **Action buttons not working**: Refresh the list or use command alternatives
- **Analytics not updating**: Use the refresh button to get latest data
- **Edit functionality**: Client editing is currently a placeholder - use command alternatives

## 🔄 Integration
- **Event-driven updates**: Client actions emit events for other plugins
- **Database persistence**: All client data is stored securely
- **Real-time feedback**: Immediate updates and visual confirmation
- **Task integration**: Seamless task assignment and management

---

**Related Commands**: [Task Management](task-management.md) → [Habits](habits.md) → [Analytics](../features/analytics.md) 