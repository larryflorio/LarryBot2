from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.storage.db import get_session
from larrybot.storage.task_repository import TaskRepository
from larrybot.core.event_utils import emit_task_event
from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
from larrybot.services.task_service import TaskService
from larrybot.utils.decorators import command_handler
from typing import Optional
from larrybot.utils.datetime_utils import get_current_datetime
from larrybot.nlp.enhanced_narrative_processor import TaskCreationState, ContextType
from larrybot.storage.client_repository import ClientRepository
from datetime import datetime, timedelta, timezone
import json

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
    command_registry.register("/addtask", narrative_add_task_handler)

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
                    f"Invalid priority: {MessageFormatter.escape_markdown(priority)}",
                    f"Valid priorities: {', '.join(valid_priorities)}"
                ),
                parse_mode='MarkdownV2'
            )
            return
    
    if len(args) > 2:
        try:
            due_date = get_current_datetime().strptime(args[2], "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Invalid date format",
                    MessageFormatter.escape_markdown("Please use YYYY-MM-DD format or select from the buttons.")
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
                        f"❌ Error: {MessageFormatter.escape_markdown(result['message'])}",
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
                    "Completed": get_current_datetime().strftime("%Y-%m-%d %H:%M")
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
                    "Modified": get_current_datetime().strftime("%Y-%m-%d %H:%M")
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

@command_handler("/addtask", "Create task with narrative flow", "Usage: /addtask", "tasks")
async def narrative_add_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the narrative task creation flow."""
    user_id = update.effective_user.id if update.effective_user else None
    
    # Initialize task creation state
    context.user_data['task_creation_state'] = TaskCreationState.AWAITING_DESCRIPTION.value
    context.user_data['partial_task'] = {
        'description': None,
        'due_date': None,
        'priority': 'Medium',
        'category': None,
        'client_id': None,
        'estimated_hours': None
    }
    context.user_data['step_history'] = []
    context.user_data['started_at'] = datetime.now().isoformat()
    
    # Ask for task description
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            "📝 Let's create a new task!",
            {"Action": "Please describe what you'd like to add."}
        ),
        parse_mode='MarkdownV2'
    )

async def handle_narrative_task_creation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str) -> None:
    """Handle the narrative task creation flow."""
    if 'task_creation_state' not in context.user_data:
        return
    
    current_state = context.user_data['task_creation_state']
    partial_task = context.user_data['partial_task']
    
    # Handle custom category input
    if current_state == TaskCreationState.AWAITING_CATEGORY.value and context.user_data.get('awaiting_custom_category'):
        del context.user_data['awaiting_custom_category']
        await _handle_category_step(update, context, user_input.strip())
        return
    
    # Handle new client input
    if current_state == TaskCreationState.AWAITING_CLIENT.value and context.user_data.get('awaiting_new_client'):
        del context.user_data['awaiting_new_client']
        # Create new client
        with next(get_session()) as session:
            client_repo = ClientRepository(session)
            new_client = client_repo.add_client(user_input.strip())
            await _handle_client_step(update, context, str(new_client.id))
        return
    
    if current_state == TaskCreationState.AWAITING_DESCRIPTION.value:
        await _handle_description_step(update, context, user_input)
    elif current_state == TaskCreationState.AWAITING_DUE_DATE.value:
        await _handle_due_date_step(update, context, user_input)
    elif current_state == TaskCreationState.AWAITING_PRIORITY.value:
        await _handle_priority_step(update, context, user_input)
    elif current_state == TaskCreationState.AWAITING_CATEGORY.value:
        await _handle_category_step(update, context, user_input)
    elif current_state == TaskCreationState.AWAITING_CLIENT.value:
        await _handle_client_step(update, context, user_input)
    elif current_state == TaskCreationState.CONFIRMATION.value:
        await _handle_confirmation_step(update, context, user_input)

async def _handle_description_step(update: Update, context: ContextTypes.DEFAULT_TYPE, description: str) -> None:
    if hasattr(update, 'answer'):
        await update.answer()
    if not description.strip():
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Description cannot be empty",
                "Please provide a task description."
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    # Store description and move to next step
    context.user_data['partial_task']['description'] = description.strip()
    context.user_data['task_creation_state'] = TaskCreationState.AWAITING_DUE_DATE.value
    context.user_data['step_history'].append({
        'step': 'description',
        'value': description.strip(),
        'timestamp': datetime.now().isoformat()
    })
    
    # Ask for due date with action buttons
    keyboard_buttons = [
        [
            InlineKeyboardButton("📅 Today", callback_data="addtask_step:due_date:today"),
            InlineKeyboardButton("📅 Tomorrow", callback_data="addtask_step:due_date:tomorrow")
        ],
        [
            InlineKeyboardButton("📅 This Week", callback_data="addtask_step:due_date:week"),
            InlineKeyboardButton("📅 Next Week", callback_data="addtask_step:due_date:next_week")
        ],
        [
            InlineKeyboardButton("⏭️ Skip", callback_data="addtask_step:due_date:skip"),
            InlineKeyboardButton("❌ Cancel", callback_data="addtask_step:cancel")
        ]
    ]
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    await update.message.reply_text(
        MessageFormatter.format_info_message(
            f"📝 Task: {MessageFormatter.escape_markdown(description.strip())}",
            {"Question": "When is this due?"}
        ),
        reply_markup=keyboard,
        parse_mode='MarkdownV2'
    )

async def _handle_due_date_step(update_or_query, context: ContextTypes.DEFAULT_TYPE, due_date_input: str) -> None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    due_date = None
    
    if due_date_input == "skip":
        due_date = None
    elif due_date_input == "today":
        due_date = datetime.now().date()
    elif due_date_input == "tomorrow":
        due_date = (datetime.now() + timedelta(days=1)).date()
    elif due_date_input == "week":
        # End of this week (Sunday)
        today = datetime.now().date()
        days_until_sunday = (6 - today.weekday()) % 7
        due_date = today + timedelta(days=days_until_sunday)
    elif due_date_input == "next_week":
        # End of next week (Sunday)
        today = datetime.now().date()
        days_until_next_sunday = (6 - today.weekday()) % 7 + 7
        due_date = today + timedelta(days=days_until_next_sunday)
    else:
        # Try to parse custom date
        try:
            due_date_obj = datetime.strptime(due_date_input, "%Y-%m-%d")
            # Make timezone-aware (UTC) to avoid naive/aware comparison issues
            due_date = due_date_obj.replace(tzinfo=timezone.utc)
        except ValueError:
            message = MessageFormatter.format_error_message(
                "Invalid date format",
                MessageFormatter.escape_markdown("Please use YYYY-MM-DD format or select from the buttons.")
            )
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(message, parse_mode='MarkdownV2')
            else:
                await update_or_query.message.reply_text(message, parse_mode='MarkdownV2')
            return
    
    # Store due date and move to next step
    context.user_data['partial_task']['due_date'] = due_date.isoformat() if due_date else None
    context.user_data['task_creation_state'] = TaskCreationState.AWAITING_PRIORITY.value
    context.user_data['step_history'].append({
        'step': 'due_date',
        'value': due_date.isoformat() if due_date else None,
        'timestamp': datetime.now().isoformat()
    })
    
    # Ask for priority with action buttons
    keyboard_buttons = [
        [
            InlineKeyboardButton("🟢 Low", callback_data="addtask_step:priority:Low"),
            InlineKeyboardButton("🟡 Medium", callback_data="addtask_step:priority:Medium")
        ],
        [
            InlineKeyboardButton("🟠 High", callback_data="addtask_step:priority:High"),
            InlineKeyboardButton("🔴 Critical", callback_data="addtask_step:priority:Critical")
        ],
        [
            InlineKeyboardButton("⏭️ Skip", callback_data="addtask_step:priority:skip"),
            InlineKeyboardButton("❌ Cancel", callback_data="addtask_step:cancel")
        ]
    ]
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    due_date_text = due_date.strftime("%Y-%m-%d") if due_date else "No due date"
    message = MessageFormatter.format_info_message(
        f"📅 Due: {due_date_text}",
        {"Question": "How urgent is this task?"}
    )

    print("[DEBUG] Due date message to Telegram:")
    print(repr(message))
    
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')
    else:
        await update_or_query.message.reply_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')

async def _handle_priority_step(update_or_query, context: ContextTypes.DEFAULT_TYPE, priority_input: str) -> None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    if priority_input == "skip":
        priority = "Medium"
    else:
        priority = priority_input
    
    # Store priority and move to next step
    context.user_data['partial_task']['priority'] = priority
    context.user_data['task_creation_state'] = TaskCreationState.AWAITING_CATEGORY.value
    context.user_data['step_history'].append({
        'step': 'priority',
        'value': priority,
        'timestamp': datetime.now().isoformat()
    })
    
    # Get available categories
    with next(get_session()) as session:
        task_repo = TaskRepository(session)
        available_categories = task_repo.get_all_categories()
    
    # Add common categories if not present
    common_categories = ["Work", "Personal", "Health", "Learning", "Finance", "Home"]
    for cat in common_categories:
        if cat not in available_categories:
            available_categories.append(cat)
    
    # Create category buttons (limit to 8 for UI performance)
    category_buttons = []
    for i in range(0, min(len(available_categories), 8), 2):
        row = []
        for j in range(2):
            if i + j < len(available_categories):
                cat = available_categories[i + j]
                row.append(InlineKeyboardButton(
                    f"📂 {cat}", 
                    callback_data=f"addtask_step:category:{cat}"
                ))
        category_buttons.append(row)
    
    # Add action buttons
    category_buttons.append([
        InlineKeyboardButton("➕ Custom", callback_data="addtask_step:category:custom"),
        InlineKeyboardButton("⏭️ Skip", callback_data="addtask_step:category:skip")
    ])
    category_buttons.append([
        InlineKeyboardButton("❌ Cancel", callback_data="addtask_step:cancel")
    ])
    
    keyboard = InlineKeyboardMarkup(category_buttons)
    
    priority_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}.get(priority, "⚪")
    message = MessageFormatter.format_info_message(
        f"{priority_emoji} Priority: {MessageFormatter.escape_markdown(priority)}",
        {"Question": "What category is this?"}
    )
    
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')
    else:
        await update_or_query.message.reply_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')

async def _handle_category_step(update_or_query, context: ContextTypes.DEFAULT_TYPE, category_input: str) -> None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    if category_input == "skip":
        category = None
        next_state = TaskCreationState.CONFIRMATION.value
    elif category_input == "custom":
        # Ask for custom category
        context.user_data['task_creation_state'] = TaskCreationState.AWAITING_CATEGORY.value
        context.user_data['awaiting_custom_category'] = True
        message = MessageFormatter.format_info_message(
            "📂 Custom Category",
            {"Action": "Please enter the category name:"}
        )
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(message, parse_mode='MarkdownV2')
        else:
            await update_or_query.message.reply_text(message, parse_mode='MarkdownV2')
        return
    else:
        category = category_input
        # If category is Work, ask for client
        if category.lower() == "work":
            next_state = TaskCreationState.AWAITING_CLIENT.value
        else:
            next_state = TaskCreationState.CONFIRMATION.value
    
    # Store category
    context.user_data['partial_task']['category'] = category
    context.user_data['step_history'].append({
        'step': 'category',
        'value': category,
        'timestamp': datetime.now().isoformat()
    })
    
    if next_state == TaskCreationState.AWAITING_CLIENT.value:
        context.user_data['task_creation_state'] = TaskCreationState.AWAITING_CLIENT.value
        await _handle_client_step(update_or_query, context, None)
    else:
        context.user_data['task_creation_state'] = TaskCreationState.CONFIRMATION.value
        await _show_confirmation(update_or_query, context)

async def _handle_client_step(update_or_query, context: ContextTypes.DEFAULT_TYPE, client_input: str) -> None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    if client_input == "skip":
        client_id = None
        next_state = TaskCreationState.CONFIRMATION.value
    elif client_input is None:
        # Show client selection buttons
        with next(get_session()) as session:
            client_repo = ClientRepository(session)
            clients = client_repo.list_clients()
        
        if not clients:
            # No clients available, skip to confirmation
            client_id = None
            next_state = TaskCreationState.CONFIRMATION.value
        else:
            # Show client selection buttons
            client_buttons = []
            for i in range(0, min(len(clients), 6), 2):  # Limit to 6 clients for UI
                row = []
                for j in range(2):
                    if i + j < len(clients):
                        client = clients[i + j]
                        # Get task count for this client
                        task_count = len(client.tasks) if hasattr(client, 'tasks') else 0
                        row.append(InlineKeyboardButton(
                            f"👤 {MessageFormatter.escape_markdown(client.name)} ({task_count})", 
                            callback_data=f"addtask_step:client:{client.id}"
                        ))
                client_buttons.append(row)
            
            # Add action buttons
            client_buttons.append([
                InlineKeyboardButton("➕ New Client", callback_data="addtask_step:client:new"),
                InlineKeyboardButton("⏭️ Skip", callback_data="addtask_step:client:skip")
            ])
            client_buttons.append([
                InlineKeyboardButton("❌ Cancel", callback_data="addtask_step:cancel")
            ])
            
            keyboard = InlineKeyboardMarkup(client_buttons)
            
            message = MessageFormatter.format_info_message(
                "💼 Category: Work",
                {"Question": "Which client is this for?"}
            )
            
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')
            else:
                await update_or_query.message.reply_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')
            return
    else:
        # Parse client ID from input
        try:
            client_id = int(client_input)
            next_state = TaskCreationState.CONFIRMATION.value
        except (ValueError, TypeError):
            if client_input == "new":
                # Handle new client creation
                context.user_data['task_creation_state'] = TaskCreationState.AWAITING_CLIENT.value
                context.user_data['awaiting_new_client'] = True
                message = MessageFormatter.format_info_message(
                    "➕ New Client",
                    {"Action": "Please enter the client name:"}
                )
                if hasattr(update_or_query, 'edit_message_text'):
                    await update_or_query.edit_message_text(message, parse_mode='MarkdownV2')
                else:
                    await update_or_query.message.reply_text(message, parse_mode='MarkdownV2')
                return
            else:
                client_id = None
                next_state = TaskCreationState.CONFIRMATION.value
    
    # Store client and move to confirmation
    context.user_data['partial_task']['client_id'] = client_id
    context.user_data['task_creation_state'] = TaskCreationState.CONFIRMATION.value
    context.user_data['step_history'].append({
        'step': 'client',
        'value': client_id,
        'timestamp': datetime.now().isoformat()
    })
    
    await _show_confirmation(update_or_query, context)

async def _show_confirmation(update_or_query, context: ContextTypes.DEFAULT_TYPE) -> None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    partial_task = context.user_data['partial_task']
    
    # Build summary message
    summary_lines = [
        f"📝 **{partial_task['description']}**"
    ]
    
    if partial_task['due_date']:
        summary_lines.append(f"📅 Due: {partial_task['due_date']}")
    
    priority_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}.get(partial_task['priority'], "⚪")
    summary_lines.append(f"{priority_emoji} Priority: {partial_task['priority']}")
    
    if partial_task['category']:
        summary_lines.append(f"📂 Category: {partial_task['category']}")
    
    if partial_task['client_id']:
        # Get client name
        with next(get_session()) as session:
            client_repo = ClientRepository(session)
            client = client_repo.get_client_by_id(partial_task['client_id'])
            if client:
                summary_lines.append(f"👤 Client: {client.name}")
    
    summary_text = "\n".join(summary_lines)
    
    # Create confirmation buttons
    keyboard_buttons = [
        [
            InlineKeyboardButton("✅ Create Task", callback_data="addtask_step:confirm"),
            InlineKeyboardButton("✏️ Edit", callback_data="addtask_step:edit")
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="addtask_step:cancel")
        ]
    ]
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    message = MessageFormatter.format_success_message(
        "✅ Task Summary",
        {"Summary": summary_text}
    )
    
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')
    else:
        await update_or_query.message.reply_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')

async def _handle_confirmation_step(update_or_query, context: ContextTypes.DEFAULT_TYPE, action: str) -> None:
    print(f"[DEBUG] Entered _handle_confirmation_step with action={action}")
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    if action == "confirm":
        await _create_final_task(update_or_query, context)
    elif action == "edit":
        await _show_edit_options(update_or_query, context)
    elif action == "cancel":
        await _cancel_task_creation(update_or_query, context)

async def _create_final_task(update_or_query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create the final task with all collected data."""
    partial_task = context.user_data['partial_task']
    
    # Convert due_date string back to datetime if present
    due_date = None
    if partial_task['due_date']:
        try:
            due_date_obj = datetime.strptime(partial_task['due_date'], "%Y-%m-%d")
            # Make timezone-aware (UTC) to avoid naive/aware comparison issues
            due_date = due_date_obj.replace(tzinfo=timezone.utc)
        except ValueError:
            due_date = None
    
    # Create task using existing service
    task_service = _get_task_service()
    result = await task_service.create_task_with_metadata(
        description=partial_task['description'],
        priority=partial_task['priority'],
        due_date=due_date,
        category=partial_task['category'],
        estimated_hours=partial_task['estimated_hours'],
        client_id=partial_task['client_id']
    )
    
    if result['success']:
        task_data = result['data']
        
        # Emit event
        emit_task_event(_task_event_bus, "task_created", task_data)
        
        message = MessageFormatter.format_success_message(
            "✅ Task created successfully!",
            {
                "ID": task_data['id'],
                "Description": task_data['description'],
                "Priority": task_data['priority'],
                "Due Date": task_data['due_date'] or 'None',
                "Category": task_data['category'] or 'None'
            }
        )
        print("[DEBUG] outgoing success message:\n", message)
        
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(message, parse_mode='MarkdownV2')
        else:
            await update_or_query.message.reply_text(message, parse_mode='MarkdownV2')
        
        # Clear task creation state
        _clear_task_creation_state(context)
    else:
        message = MessageFormatter.format_error_message(
            f"❌ Error creating task: {MessageFormatter.escape_markdown(result['message'])}",
            "Please try again or use /add for basic task creation."
        )
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(message, parse_mode='MarkdownV2')
        else:
            await update_or_query.message.reply_text(message, parse_mode='MarkdownV2')

async def _cancel_task_creation(update_or_query, context: ContextTypes.DEFAULT_TYPE) -> None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    _clear_task_creation_state(context)
    
    message = MessageFormatter.format_info_message(
        "❌ Task creation cancelled",
        {"Action": "Use /addtask to start over or /add for basic task creation."}
    )
    
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(message, parse_mode='MarkdownV2')
    else:
        await update_or_query.message.reply_text(message, parse_mode='MarkdownV2')

async def _show_edit_options(update_or_query, context: ContextTypes.DEFAULT_TYPE) -> None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    message = MessageFormatter.format_info_message(
        "✏️ Edit Options",
        {"Status": "Edit functionality coming soon. Please cancel and start over to make changes."}
    )
    
    keyboard_buttons = [
        [InlineKeyboardButton("❌ Cancel", callback_data="addtask_step:cancel")]
    ]
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')
    else:
        await update_or_query.message.reply_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')

def _clear_task_creation_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear task creation state from context."""
    keys_to_remove = [
        'task_creation_state', 'partial_task', 'step_history', 
        'started_at', 'awaiting_custom_category', 'awaiting_new_client'
    ]
    for key in keys_to_remove:
        if key in context.user_data:
            del context.user_data[key] 