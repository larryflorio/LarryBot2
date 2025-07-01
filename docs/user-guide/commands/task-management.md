---
title: Task Management Commands
description: Create, edit, and manage tasks with LarryBot2's enhanced task management system
last_updated: 2025-07-01
---

# Task Management Commands 📋

LarryBot2 provides a comprehensive task management system with **enhanced unified commands** that support both basic and advanced functionality through progressive enhancement. This guide covers all commands for creating, editing, and managing your tasks as of July 1, 2025.

> **🆕 New in v2.1.6:** Major command consolidation completed! Enhanced commands now provide both basic and advanced functionality through intelligent parameter handling. All deprecated commands redirect seamlessly to enhanced versions.

> **📋 Quick Reference**: 
> - **Basic Users**: Use `/add`, `/list`, `/done`, `/edit`, `/remove` 
> - **Advanced Users**: Add optional parameters for enhanced functionality
> - **Migration**: All old commands (`/addtask`, `/tasks`) automatically redirect with helpful guidance

---

## 🚀 **Enhanced Basic Commands**

### `/add` - **Enhanced Task Creation** ⭐
**Enhanced**: Now supports both basic AND advanced task creation with optional metadata.

**Usage**: 
- **Basic**: `/add <description>`
- **Advanced**: `/add <description> [priority] [due_date] [category]`

**Progressive Enhancement**: Start simple, add complexity when needed.

#### **Basic Usage** (unchanged for existing users)
```bash
/add Buy groceries
/add Call client about project  
/add Review quarterly reports
```

#### **Advanced Usage** (new capability!)
```bash
# With priority
/add Complete project proposal high

# With priority and due date
/add Complete project proposal high 2025-07-05

# Full advanced usage
/add Complete project proposal high 2025-07-05 work
/add Buy birthday gift medium 2025-07-01 personal
/add Schedule team meeting critical 2025-06-30 work
```

**Parameters**:
- `description` (required): Task description
- `priority` (optional): `low`, `medium`, `high`, `critical`
- `due_date` (optional): `YYYY-MM-DD` format
- `category` (optional): Any category name

#### **Response Examples**

**Basic Creation**:
```
✅ **Success**

✅ Task added successfully!

📋 **Details:**
   • Task: Buy groceries
   • ID: 123
   • Status: Todo
   • Created: 2025-06-30 10:30

[👁️ View] [✅ Done] [✏️ Edit] [🗑️ Delete]
```

**Advanced Creation**:
```
✅ **Success**

✅ Enhanced task created successfully!

📋 **Details:**
   • Task: Complete project proposal
   • ID: 124
   • Status: Todo
   • Priority: High 🔴
   • Due: 2025-07-05 📅
   • Category: work 🏷️
   • Created: 2025-06-30 10:30

[👁️ View] [✅ Done] [✏️ Edit] [🗑️ Delete]
```

#### **Migration from `/addtask`**
> **⚠️ Deprecated**: `/addtask` now redirects to enhanced `/add`
> 
> **Old**: `/addtask "Complete project" High 2025-07-05 work`  
> **New**: `/add "Complete project" high 2025-07-05 work`

---

### `/list` - **Enhanced Task Listing** ⭐
**Enhanced**: Now supports both basic listing AND advanced filtering with optional parameters.

**Usage**:
- **Basic**: `/list` (shows incomplete tasks)
- **Advanced**: `/list [status] [priority] [category]`

**Progressive Enhancement**: Start with simple listing, add filters when needed.

#### **Basic Usage** (unchanged for existing users)
```bash
/list
```

#### **Advanced Usage** (new filtering capability!)
```bash
# Filter by status
/list todo
/list done

# Filter by priority  
/list high
/list critical

# Filter by category
/list work
/list personal

# Combined filtering
/list todo high work
/list done medium personal
/list review critical
```

**Filter Parameters**:
- `status` (optional): `todo`, `in_progress`, `review`, `done`
- `priority` (optional): `low`, `medium`, `high`, `critical`  
- `category` (optional): Any category name

#### **Response Examples**

**Basic Listing**:
```
📋 **Incomplete Tasks** (3 found)

1. 🟡 **Buy groceries** (ID: 123)
   📝 Todo | Medium priority
   📅 Due: Today
   🏷️ Category: personal

2. 🔴 **Complete project proposal** (ID: 124)  
   📝 Todo | High priority
   📅 Due: 2025-07-05
   🏷️ Category: work

3. 🟡 **Call client about project** (ID: 125)
   📝 In Progress | Medium priority
   📅 Due: 2025-07-01
   🏷️ Category: work

[👁️ View] [✅ Done] [✏️ Edit] [🗑️ Delete]
[👁️ View] [✅ Done] [✏️ Edit] [🗑️ Delete]  
[👁️ View] [✅ Done] [✏️ Edit] [🗑️ Delete]

[➕ Add Task] [🔄 Refresh] [⬅️ Back]
```

**Advanced Filtering**:
```
📋 **Filtered Tasks: Todo + High + work** (1 found)

1. 🔴 **Complete project proposal** (ID: 124)
   📝 Todo | High priority  
   📅 Due: 2025-07-05
   🏷️ Category: work

[👁️ View] [✅ Done] [✏️ Edit] [🗑️ Delete]

[➕ Add Task] [🔄 Refresh] [⬅️ Back]
```

#### **Migration from `/tasks`**
> **⚠️ Deprecated**: `/tasks` now redirects to enhanced `/list`
> 
> **Old**: `/tasks High work`  
> **New**: `/list high work`

---

## 🎯 **Standard Task Commands**

### `/done` - Mark Task Complete
Mark a task as completed with confirmation and action buttons.

**Usage**: `/done <task_id>`

**Examples**:
```bash
/done 123
/done 124
```

**Response**:
```
✅ **Success**

✅ Task completed!

📋 **Details:**
   • Task: Buy groceries
   • ID: 123
   • Status: Done ✅
   • Completed: 2025-06-30 10:45
   • Duration: 2h 15m

[👁️ View] [↩️ Undo] [🗑️ Delete]
```

### `/edit` - Edit Task Description  
Update the description of an existing task with inline editing support.

**Usage**: `/edit <task_id> <new_description>`

**Examples**:
```bash
/edit 123 Buy groceries and household items
/edit 124 Complete project proposal for Q3
```

**Response**:
```
✅ **Success**

✏️ Task updated successfully!

📋 **Details:**
   • Task: Buy groceries and household items
   • ID: 123
   • Status: Updated ✏️
   • Modified: 2025-06-30 10:50

[👁️ View] [✅ Done] [✏️ Edit Again] [🗑️ Delete]
```

### `/remove` - Remove Task
Delete a task permanently with confirmation dialog and safety checks.

**Usage**: `/remove <task_id>`

**Examples**:
```bash
/remove 123
/remove 124
```

**Response (confirmation dialog)**:
```
🗑️ **Confirm Task Deletion**

**Task**: Buy groceries and household items
**ID**: 123
**Status**: 📝 Todo
**Priority**: Medium 🟡
**Category**: personal 🏷️

⚠️ **Warning**: This action cannot be undone.

Are you sure you want to delete this task?

[🗑️ Confirm Delete] [❌ Cancel]
```

**Response (after confirmation)**:
```
🗑️ **Task deleted successfully!**

📋 **Details:**
   • Task: Buy groceries and household items
   • ID: 123
   • Status: Deleted 🗑️
   • Action: Task removed from database

[↩️ Undo Delete] [⬅️ Back to List]
```

---

## 🎮 **Action Buttons System**

### **Per-Task Action Buttons**
Every task display includes intelligent action buttons:

- **👁️ View**: Show detailed task information with full metadata
- **✅ Done**: Mark task complete (only for incomplete tasks)
- **✏️ Edit**: Launch inline edit flow with text input
- **🗑️ Delete**: Delete task with confirmation dialog

### **Navigation Action Buttons**
All task lists include navigation options:

- **➕ Add Task**: Quick access to add new task
- **🔄 Refresh**: Reload current list with fresh data  
- **⬅️ Back**: Return to previous menu or main menu

### **Smart Button Behavior**
- **Context-Aware**: Buttons adapt based on task status
- **Confirmation Dialogs**: Destructive actions require confirmation
- **Inline Editing**: Edit operations use inline text input
- **Progress Feedback**: Visual feedback during operations

---

## 🔄 **Migration Guide**

### **Enhanced Commands Available**
| Old Command | New Enhanced Command | Migration |
|------------|---------------------|-----------|
| `/addtask` | `/add` | Automatic redirect with examples |
| `/tasks` | `/list` | Automatic redirect with filtering help |

### **Seamless Transition**
- **Zero Disruption**: Old commands continue working
- **Educational Redirects**: Helpful migration messages
- **Usage Examples**: Concrete examples for new syntax
- **Gradual Migration**: Users can transition at their own pace

### **Example Migration Messages**
When using deprecated commands, you'll see helpful guidance:

```
🔄 **Command Enhanced!**

The `/addtask` command has been enhanced and merged into `/add`.

**Your old command**: `/addtask "Complete project" High 2025-07-05 work`
**New enhanced syntax**: `/add "Complete project" high 2025-07-05 work`

✨ **Benefits**: 
• Single command for both basic and advanced task creation
• Simpler syntax with optional parameters
• Same powerful functionality with better user experience

**Try it now**: `/add Complete project high 2025-07-05 work`
```

---

## 📚 **Best Practices**

### **For New Users**
1. **Start Simple**: Use basic `/add` and `/list` commands
2. **Discover Gradually**: Add parameters as you need them
3. **Use Action Buttons**: Click buttons for quick task operations
4. **Explore Features**: Try advanced parameters when ready

### **For Existing Users**  
1. **Continue Current Usage**: Your existing commands still work
2. **Explore Enhancements**: Try optional parameters for more power
3. **Migrate Gradually**: Switch to enhanced syntax when convenient
4. **Benefit from Unification**: Fewer commands to remember

### **Command Efficiency Tips**
- **Progressive Enhancement**: `/add task` → `/add task high` → `/add task high 2025-07-01`
- **Smart Defaults**: Commands work intelligently with partial parameters
- **Consistent Patterns**: All enhanced commands follow similar parameter patterns
- **Action Buttons**: Use buttons for quick operations without typing commands

---

**📖 Related Documentation:**
- [Enhanced Filtering and Search](enhanced-filtering.md) - Enhanced `/search` command
- [Analytics and Reporting](analytics-reporting.md) - Unified `/analytics` command  
- [Bulk Operations](bulk-operations.md) - Bulk task operations
- [API Reference](../../api-reference/commands.md) - Complete command reference

---

**🎯 Quick Navigation:**
- [Basic Commands](#enhanced-basic-commands) - Start here for essential task management
- [Action Buttons](#action-buttons-system) - Interactive task operations  
- [Migration Guide](#migration-guide) - Transitioning from old commands
- [Best Practices](#best-practices) - Tips for efficient task management 
*Last updated: July 1, 2025* 