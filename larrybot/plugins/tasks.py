from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.storage.db import get_session
from larrybot.storage.task_repository import TaskRepository
from larrybot.core.event_utils import emit_task_event
from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
from larrybot.services.task_service import TaskService
from typing import Optional
from datetime import datetime

# Global reference to event bus for task events
_task_event_bus = None

def register(event_bus: EventBus, command_registry: CommandRegistry) -> None:
    """
    Register task management commands with the command registry.
    """
    global _task_event_bus
    _task_event_bus = event_bus
    
    command_registry.register("/add", add_task_handler)
    command_registry.register("/list", list_tasks_handler)
    command_registry.register("/done", done_task_handler)
    command_registry.register("/edit", edit_task_handler)
    command_registry.register("/remove", remove_task_handler)

def _get_task_service() -> TaskService:
    """Get task service instance."""
    session = next(get_session())
    task_repository = TaskRepository(session)
    return TaskService(task_repository)

async def add_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Enhanced task creation with optional metadata support.
    
    Usage:
    - Basic: /add <description>
    - Advanced: /add <description> [priority] [due_date] [category]
    
    This consolidates the functionality of both /add and /addtask commands.
    """
    if not context.args:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Missing task description",
                "Usage: /add <description> [priority] [due_date] [category]\n\n"
                "Examples:\n"
                "• Basic: /add \"Complete project report\"\n"
                "• Advanced: /add \"Complete project report\" High 2025-07-15 work"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    args = context.args
    description = args[0]
    
    # Parse optional arguments for advanced functionality
    priority = "Medium"  # Default priority
    due_date = None
    category = None
    
    # Enhanced argument parsing
    if len(args) > 1:
        priority = args[1]
        # Validate priority
        valid_priorities = ["Low", "Medium", "High", "Critical"]
        if priority not in valid_priorities:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"Invalid priority: {priority}",
                    f"Valid priorities: {', '.join(valid_priorities)}"
                ),
                parse_mode='MarkdownV2'
            )
            return
    
    if len(args) > 2:
        try:
            due_date = datetime.strptime(args[2], "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Invalid date format",
                    "Use YYYY-MM-DD format (e.g., 2025-07-15)"
                ),
                parse_mode='MarkdownV2'
            )
            return
    
    if len(args) > 3:
        category = args[3]
    
    # Use advanced task service if metadata provided, otherwise use basic repository
    if len(args) > 1:  # Advanced creation with metadata
        try:
            task_service = _get_task_service()
            result = await task_service.create_task_with_metadata(
                description=description,
                priority=priority,
                due_date=due_date,
                category=category
            )
            
            if result['success']:
                task_data = result['data']
                await update.message.reply_text(
                    MessageFormatter.format_success_message(
                        "✅ Task created with metadata!",
                        {
                            "ID": task_data['id'],
                            "Description": task_data['description'],
                            "Priority": task_data['priority'],
                            "Due Date": task_data['due_date'] or 'None',
                            "Category": task_data['category'] or 'None'
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
                
                # Emit event using standardized format
                emit_task_event(_task_event_bus, "task_created", task_data)
            else:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        f"❌ Error: {result['message']}",
                        "Check your input format and try again."
                    ),
                    parse_mode='MarkdownV2'
                )
        except Exception as e:
            # Fallback to basic creation if advanced service fails
            await _create_basic_task(description, update)
    
    else:  # Basic creation (original /add behavior)
        await _create_basic_task(description, update)

async def _create_basic_task(description: str, update: Update) -> None:
    """Create a basic task using the original /add logic."""
    with next(get_session()) as session:
        repo = TaskRepository(session)
        task = repo.add_task(description)
        # Emit event using standardized format
        emit_task_event(_task_event_bus, "task_created", task)
        
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                "✅ Task added successfully!",
                {
                    "Task": task.description,
                    "ID": task.id,
                    "Status": "Todo",
                    "Created": task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else "N/A"
                }
            ),
            parse_mode='MarkdownV2'
        )

async def list_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Enhanced task listing with optional filtering support.
    
    Usage:
    - Basic: /list (shows incomplete tasks)
    - Advanced: /list [status] [priority] [category]
    
    This consolidates the functionality of both /list and /tasks commands.
    """
    args = context.args
    
    # Parse optional filter arguments
    status = None
    priority = None
    category = None
    
    if len(args) > 0:
        status = args[0]
    if len(args) > 1:
        priority = args[1]
    if len(args) > 2:
        category = args[2]
    
    # Use advanced filtering if any filters provided
    if status or priority or category:
        await _list_tasks_with_filters(update, status, priority, category)
    else:
        # Default behavior - show incomplete tasks (original /list functionality)
        await _list_incomplete_tasks_default(update)

async def _list_tasks_with_filters(update: Update, status: Optional[str], priority: Optional[str], category: Optional[str]) -> None:
    """List tasks with advanced filtering."""
    try:
        task_service = _get_task_service()
        result = await task_service.get_tasks_with_filters(
            status=status,
            priority=priority,
            category=category,
            done=False
        )
        
        if result['success']:
            tasks = result['data']
            if tasks:
                # Build title with active filters
                title = "Tasks"
                if status or priority or category:
                    filters = []
                    if status:
                        filters.append(f"Status: {status}")
                    if priority:
                        filters.append(f"Priority: {priority}")
                    if category:
                        filters.append(f"Category: {category}")
                    title = f"Tasks ({', '.join(filters)})"
                
                message = MessageFormatter.format_task_list(tasks, title)
                
                # Create action buttons for filtered tasks
                keyboard_buttons = []
                for task in tasks[:10]:  # Limit to first 10 for UI performance
                    task_row = [
                        InlineKeyboardButton(f"👁️ {task['id']}", callback_data=f"task_view:{task['id']}"),
                        InlineKeyboardButton(f"✅ {task['id']}", callback_data=f"task_done:{task['id']}"),
                        InlineKeyboardButton(f"✏️ {task['id']}", callback_data=f"task_edit:{task['id']}"),
                        InlineKeyboardButton(f"🗑️ {task['id']}", callback_data=f"task_delete:{task['id']}")
                    ]
                    keyboard_buttons.append(task_row)
                
                # Add navigation buttons
                keyboard_buttons.append([
                    InlineKeyboardButton("🔄 Refresh", callback_data="tasks_refresh"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="nav_main")
                ])
                
                keyboard = InlineKeyboardMarkup(keyboard_buttons)
                
                await update.message.reply_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
            else:
                await update.message.reply_text(
                    MessageFormatter.format_info_message(
                        "📋 No Tasks Found",
                        {
                            "Filters": f"Status: {status or 'Any'}, Priority: {priority or 'Any'}, Category: {category or 'Any'}",
                            "Action": "Try adjusting your filter criteria or use /add to create tasks"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    result['message'],
                    "Check your filter parameters."
                ),
                parse_mode='MarkdownV2'
            )
    except Exception as e:
        # Fallback to default listing if advanced filtering fails
        await _list_incomplete_tasks_default(update)

async def _list_incomplete_tasks_default(update: Update) -> None:
    """Default task listing behavior (original /list functionality)."""
    with next(get_session()) as session:
        repo = TaskRepository(session)
        incomplete_tasks = repo.list_incomplete_tasks()
        
        if not incomplete_tasks:
            await update.message.reply_text(
                MessageFormatter.format_info_message(
                    "📋 No Tasks Found",
                    {
                        "Status": "No incomplete tasks",
                        "Action": "Use /add to create your first task"
                    }
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Convert tasks to dict format for MessageFormatter
        tasks_data = []
        for task in incomplete_tasks:
            tasks_data.append({
                'id': task.id,
                'description': task.description,
                'status': 'Todo',
                'priority': 'Medium',
                'created_at': task.created_at
            })
        
        message = MessageFormatter.format_task_list(tasks_data, "Incomplete Tasks")
        
        # Create action buttons for each task, now including a View button
        keyboard_buttons = []
        for task in incomplete_tasks:
            task_row = [
                InlineKeyboardButton(f"👁️ {task.id}", callback_data=f"task_view:{task.id}"),
                InlineKeyboardButton(f"✅ {task.id}", callback_data=f"task_done:{task.id}"),
                InlineKeyboardButton(f"✏️ {task.id}", callback_data=f"task_edit:{task.id}"),
                InlineKeyboardButton(f"🗑️ {task.id}", callback_data=f"task_delete:{task.id}")
            ]
            keyboard_buttons.append(task_row)
        
        # Add navigation buttons
        keyboard_buttons.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="tasks_refresh"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="nav_main")
        ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )

async def done_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark a task as complete with enhanced UX."""
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Missing or invalid task ID",
                "Usage: /done <task ID>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    with next(get_session()) as session:
        repo = TaskRepository(session)
        task = repo.get_task_by_id(task_id)
        
        if not task:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"Task ID {task_id} not found",
                    "Check the task ID or use /list to see available tasks"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        if task.done:
            await update.message.reply_text(
                MessageFormatter.format_info_message(
                    "✅ Task Already Complete",
                    {
                        "Task": task.description,
                        "ID": task_id,
                        "Status": "Already marked as done"
                    }
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        repo.mark_task_done(task_id)
        # Emit event using standardized format
        emit_task_event(_task_event_bus, "task_completed", task)
        
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                "✅ Task completed!",
                {
                    "Task": task.description,
                    "ID": task_id,
                    "Status": "Done",
                    "Completed": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
            ),
            parse_mode='MarkdownV2'
        )

async def edit_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Edit a task with enhanced UX."""
    if len(context.args) < 2 or not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Invalid arguments",
                "Usage: /edit <task ID> <new description>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    new_desc = " ".join(context.args[1:])
    
    if not new_desc:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "New description cannot be empty",
                "Please provide a valid task description"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    with next(get_session()) as session:
        repo = TaskRepository(session)
        task = repo.edit_task(task_id, new_desc)
        
        if not task:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"Task ID {task_id} not found",
                    "Check the task ID or use /list to see available tasks"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Emit event for task editing using standardized format
        emit_task_event(_task_event_bus, "task_edited", task)
        
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                "✏️ Task updated successfully!",
                {
                    "Task": task.description,
                    "ID": task_id,
                    "Status": "Updated",
                    "Modified": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
            ),
            parse_mode='MarkdownV2'
        )

async def remove_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a task with confirmation dialog."""
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Missing or invalid task ID",
                "Usage: /remove <task ID>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    task_id = int(context.args[0])
    with next(get_session()) as session:
        repo = TaskRepository(session)
        task = repo.get_task_by_id(task_id)
        
        if not task:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"Task ID {task_id} not found",
                    "Check the task ID or use /list to see available tasks"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Show confirmation dialog with inline keyboard
        keyboard = KeyboardBuilder.build_confirmation_keyboard("task_delete", task_id)
        
        await update.message.reply_text(
            f"🗑️ **Confirm Task Deletion**\n\n"
            f"**Task**: {MessageFormatter.escape_markdown(task.description)}\n"
            f"**ID**: {task_id}\n"
            f"**Status**: {'✅ Done' if task.done else '📝 Todo'}\n\n"
            f"⚠️ **Warning**: This action cannot be undone\\.\n\n"
            f"Are you sure you want to delete this task?",
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        ) 