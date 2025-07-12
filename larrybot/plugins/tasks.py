from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.storage.db import get_session
from larrybot.storage.task_repository import TaskRepository
from larrybot.core.event_utils import emit_task_event
from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
from larrybot.services.task_service import TaskService
from larrybot.utils.decorators import command_handler, callback_handler
from typing import Optional
from larrybot.utils.datetime_utils import get_current_datetime
from larrybot.nlp.enhanced_narrative_processor import TaskCreationState, ContextType
from larrybot.storage.client_repository import ClientRepository
from larrybot.services.datetime_service import DateTimeService
from larrybot.models.enums import TaskPriority
from datetime import datetime, timedelta, timezone
import json
from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ActionType, ButtonType
_task_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    """
    Register task management commands with the command registry.
    """
    global _task_event_bus
    _task_event_bus = event_bus
    command_registry.register('/list', list_tasks_handler)
    command_registry.register('/done', done_task_handler)
    command_registry.register('/edit', edit_task_handler)
    command_registry.register('/remove', remove_task_handler)
    command_registry.register('/addtask', narrative_add_task_handler)
    
    # Register callback handlers for narrative task flow
    command_registry.register_callback('addtask_step', handle_narrative_task_callback)


@callback_handler('addtask_step', 'Handle narrative task creation callbacks', 'tasks', True, 2)
async def handle_narrative_task_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Central handler for all addtask_step callbacks."""
    callback_data = query.data
    parts = callback_data.split(':')
    
    if len(parts) < 2:
        return
    
    step_type = parts[1]
    step_value = parts[2] if len(parts) > 2 else None
    
    # Route to appropriate step handler
    if step_type == 'due_date':
        await _handle_due_date_step(query, context, step_value)
    elif step_type == 'priority':
        await _handle_priority_step(query, context, step_value)
    elif step_type == 'category':
        await _handle_category_step(query, context, step_value)
    elif step_type == 'client':
        await _handle_client_step(query, context, step_value)
    elif step_type == 'confirm':
        await _handle_confirmation_step(query, context, 'confirm')
    elif step_type == 'cancel':
        await _cancel_task_creation(query, context)
    elif step_type == 'edit':
        await _handle_confirmation_step(query, context, 'edit')
    else:
        # Unknown step type - send error message
        from larrybot.utils.ux_helpers import MessageFormatter
        message = MessageFormatter.format_error_message(
            'Unknown step type',
            f'Step type "{step_type}" is not recognized. Please try again.'
        )
        await query.edit_message_text(message, parse_mode='MarkdownV2')


def _get_task_service() ->TaskService:
    """Get task service instance."""
    session = next(get_session())
    task_repository = TaskRepository(session)
    return TaskService(task_repository)


async def add_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """
    Enhanced task creation with optional metadata support.
    
    Usage:
    - Basic: /add <description>
    - Advanced: /add <description> [priority] [due_date] [category]
    
    This consolidates the functionality of both /add and /addtask commands.
    """
    if not context.args:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Missing task description',
            """Usage: /add <description> [priority] [due_date] [category]

Examples:
• Basic: /add "Complete project report"
• Advanced: /add "Complete project report" High 2025-07-15 work"""
            ), parse_mode='MarkdownV2')
        return
    args = context.args
    description = args[0]
    priority = 'Medium'
    due_date = None
    category = None
    if len(args) > 1:
        priority = args[1]
        valid_priorities = ['Low', 'Medium', 'High', 'Critical']
        if priority not in valid_priorities:
            await update.message.reply_text(MessageFormatter.
                format_error_message(
                f'Invalid priority: {MessageFormatter.escape_markdown(priority)}'
                , f"Valid priorities: {', '.join(valid_priorities)}"),
                parse_mode='MarkdownV2')
            return
    if len(args) > 2:
        due_date = DateTimeService.parse_user_date(args[2])
        if due_date is None:
            await update.message.reply_text(MessageFormatter.
                format_error_message('Invalid date format',
                MessageFormatter.escape_markdown(
                'Please use natural language (e.g., "Monday", "next week") or YYYY-MM-DD format.')
                ), parse_mode='MarkdownV2')
            return
    if len(args) > 3:
        category = args[3]
    if len(args) > 1:
        try:
            task_service = _get_task_service()
            result = await task_service.create_task_with_metadata(description
                =description, priority=priority, due_date=due_date,
                category=category)
            if result['success']:
                task_data = result['data']
                await update.message.reply_text(MessageFormatter.
                    format_success_message('✅ Task created with metadata!',
                    {'ID': task_data['id'], 'Description': task_data[
                    'description'], 'Priority': task_data['priority'],
                    'Due Date': task_data['due_date'] or 'None', 'Category':
                    task_data['category'] or 'None'}), parse_mode='MarkdownV2')
                emit_task_event(_task_event_bus, 'task_created', task_data)
            else:
                await update.message.reply_text(MessageFormatter.
                    format_error_message(
                    f"❌ Error: {MessageFormatter.escape_markdown(result['message'])}"
                    , 'Check your input format and try again.'), parse_mode
                    ='MarkdownV2')
        except Exception as e:
            await _create_basic_task(description, update)
    else:
        await _create_basic_task(description, update)


async def _create_basic_task(description: str, update: Update) ->None:
    """Create a basic task using the original /add logic."""
    with next(get_session()) as session:
        repo = TaskRepository(session)
        task = repo.add_task(description)
        emit_task_event(_task_event_bus, 'task_created', task)
        await update.message.reply_text(MessageFormatter.
            format_success_message('✅ Task added successfully!', {'Task':
            task.description, 'ID': task.id, 'Status': 'Todo', 'Created': 
            task.created_at.strftime('%Y-%m-%d %H:%M') if task.created_at else
            'N/A'}), parse_mode='MarkdownV2')


async def list_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """
    Enhanced task listing with optional filtering support.
    
    Usage:
    - Basic: /list (shows incomplete tasks)
    - Advanced: /list [status] [priority] [category]
    
    This consolidates the functionality of both /list and /tasks commands.
    """
    args = context.args
    status = None
    priority = None
    category = None
    if len(args) > 0:
        status = args[0]
    if len(args) > 1:
        priority = args[1]
    if len(args) > 2:
        category = args[2]
    if status or priority or category:
        await _list_tasks_with_filters(update, status, priority, category)
    else:
        await _list_incomplete_tasks_default(update)


async def _list_tasks_with_filters(update: Update, status: Optional[str],
    priority: Optional[str], category: Optional[str]) ->None:
    """List tasks with advanced filtering."""
    try:
        task_service = _get_task_service()
        result = await task_service.get_tasks_with_filters(status=status,
            priority=priority, category=category, done=False)
        if result['success']:
            tasks = result['data']
            if tasks:
                title = 'Tasks'
                if status or priority or category:
                    filters = []
                    if status:
                        filters.append(f'Status: {status}')
                    if priority:
                        filters.append(f'Priority: {priority}')
                    if category:
                        filters.append(f'Category: {category}')
                    title = f"Tasks ({', '.join(filters)})"
                message = MessageFormatter.format_task_list(tasks, title)
                keyboard_buttons = []
                for task in tasks[:10]:
                    task_row = [UnifiedButtonBuilder.create_action_button(
                        ActionType.VIEW, task['id'], 'task'),
                        UnifiedButtonBuilder.create_action_button(
                        ActionType.COMPLETE, task['id'], 'task'),
                        UnifiedButtonBuilder.create_action_button(
                        ActionType.EDIT, task['id'], 'task'),
                        UnifiedButtonBuilder.create_action_button(
                        ActionType.DELETE, task['id'], 'task')]
                    keyboard_buttons.append(task_row)
                keyboard_buttons.append([UnifiedButtonBuilder.create_button
                    (text='🏠 Main Menu', callback_data=
                    'nav_main', button_type=ButtonType.PRIMARY)])
                keyboard = InlineKeyboardMarkup(keyboard_buttons)
                await update.message.reply_text(message, reply_markup=
                    keyboard, parse_mode='MarkdownV2')
            else:
                await update.message.reply_text(MessageFormatter.
                    format_info_message('📋 No Tasks Found', {'Filters':
                    f"Status: {status or 'Any'}, Priority: {priority or 'Any'}, Category: {category or 'Any'}"
                    , 'Action':
                    'Try adjusting your filter criteria or use /add to create tasks'
                    }), parse_mode='MarkdownV2')
        else:
            await update.message.reply_text(MessageFormatter.
                format_error_message(result['message'],
                'Check your filter parameters.'), parse_mode='MarkdownV2')
    except Exception as e:
        await _list_incomplete_tasks_default(update)


async def _list_incomplete_tasks_default(update: Update) ->None:
    """Default task listing behavior (original /list functionality)."""
    with next(get_session()) as session:
        repo = TaskRepository(session)
        incomplete_tasks = repo.list_incomplete_tasks()
        # --- Begin sorting patch ---
        # Define priority order using enum values: Critical=4, High=3, Medium=2, Low=1
        priority_order = {4: 0, 3: 1, 2: 2, 1: 3}  # Map enum values to sort order
        def sort_key(task):
            # Handle due date sorting - None due dates go last
            if task.due_date is not None and hasattr(task.due_date, 'timestamp'):
                due_val = task.due_date.timestamp()
            else:
                # Use a very large timestamp for tasks without due dates
                due_val = float('inf')
            
            # Get priority as integer from enum, default to Medium (2)
            priority_enum = task.priority_enum or TaskPriority.MEDIUM
            priority_val = priority_order.get(priority_enum.value, 2)
            return (due_val, priority_val)
        incomplete_tasks = sorted(incomplete_tasks, key=sort_key)
        # --- End sorting patch ---
        if not incomplete_tasks:
            await update.message.reply_text(MessageFormatter.
                format_info_message('📋 No Tasks Found', {'Status':
                'No incomplete tasks', 'Action':
                'Use /add to create your first task'}), parse_mode='MarkdownV2'
                )
            return
        tasks_data = []
        for task in incomplete_tasks:
            # Use actual task data instead of static values
            task_data = {
                'id': task.id,
                'description': task.description,
                'priority': task.priority,  # Use actual priority from database
                'category': task.category,  # Include category if available
                'due_date': task.due_date,  # Include due date if available
                'client': task.client if (task.category and str(task.category).lower() == 'work') else None,
            }
            tasks_data.append(task_data)
        # --- Begin numbered list patch ---
        # Render the message as a numbered list (prefix each task with its number)
        message = MessageFormatter.format_task_list(tasks_data, 'Incomplete Tasks', numbered=True)
        # --- End numbered list patch ---
        keyboard_buttons = []
        # --- Begin 4-per-row button patch ---
        row = []
        for idx, task in enumerate(incomplete_tasks, 1):
            button = UnifiedButtonBuilder.create_button(
                text=str(idx),
                callback_data=f'task_view:{task.id}',
                button_type=ButtonType.INFO
            )
            row.append(button)
            if len(row) == 4:
                keyboard_buttons.append(row)
                row = []
        if row:
            keyboard_buttons.append(row)
        # --- End 4-per-row button patch ---
        keyboard_buttons.append([
            UnifiedButtonBuilder.create_button(text='🏠 Main Menu', callback_data='nav_main', button_type=ButtonType.INFO)
        ])
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')


async def done_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Mark a task as complete with enhanced UX."""
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(MessageFormatter.
            format_error_message('Missing or invalid task ID',
            'Usage: /done <task ID>'), parse_mode='MarkdownV2')
        return
    task_id = int(context.args[0])
    with next(get_session()) as session:
        repo = TaskRepository(session)
        task = repo.get_task_by_id(task_id)
        if not task:
            await update.message.reply_text(MessageFormatter.
                format_error_message(f'Task ID {task_id} not found',
                'Check the task ID or use /list to see available tasks'),
                parse_mode='MarkdownV2')
            return
        if task.done:
            await update.message.reply_text(MessageFormatter.
                format_info_message('✅ Task Already Complete', {'Task':
                task.description, 'ID': task_id, 'Status':
                'Already marked as done'}), parse_mode='MarkdownV2')
            return
        repo.mark_task_done(task_id)
        emit_task_event(_task_event_bus, 'task_completed', task)
        await update.message.reply_text(MessageFormatter.
            format_success_message('✅ Task completed!', {'Task': task.
            description, 'ID': task_id, 'Status': 'Done', 'Completed':
            get_current_datetime().strftime('%Y-%m-%d %H:%M')}), parse_mode
            ='MarkdownV2')


async def edit_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Edit a task with enhanced UX."""
    if len(context.args) < 2 or not context.args[0].isdigit():
        await update.message.reply_text(MessageFormatter.
            format_error_message('Invalid arguments',
            'Usage: /edit <task ID> <new description>'), parse_mode=
            'MarkdownV2')
        return
    task_id = int(context.args[0])
    new_desc = ' '.join(context.args[1:])
    if not new_desc:
        await update.message.reply_text(MessageFormatter.
            format_error_message('New description cannot be empty',
            'Please provide a valid task description'), parse_mode='MarkdownV2'
            )
        return
    with next(get_session()) as session:
        repo = TaskRepository(session)
        task = repo.edit_task(task_id, new_desc)
        if not task:
            await update.message.reply_text(MessageFormatter.
                format_error_message(f'Task ID {task_id} not found',
                'Check the task ID or use /list to see available tasks'),
                parse_mode='MarkdownV2')
            return
        emit_task_event(_task_event_bus, 'task_edited', task)
        await update.message.reply_text(MessageFormatter.
            format_success_message('✏️ Task updated successfully!', {'Task':
            task.description, 'ID': task_id, 'Status': 'Updated',
            'Modified': get_current_datetime().strftime('%Y-%m-%d %H:%M')}),
            parse_mode='MarkdownV2')


async def remove_task_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Remove a task with confirmation dialog."""
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(MessageFormatter.
            format_error_message('Missing or invalid task ID',
            'Usage: /remove <task ID>'), parse_mode='MarkdownV2')
        return
    task_id = int(context.args[0])
    with next(get_session()) as session:
        repo = TaskRepository(session)
        task = repo.get_task_by_id(task_id)
        if not task:
            await update.message.reply_text(MessageFormatter.
                format_error_message(f'Task ID {task_id} not found',
                'Check the task ID or use /list to see available tasks'),
                parse_mode='MarkdownV2')
            return
        keyboard = KeyboardBuilder.build_confirmation_keyboard('task_delete',
            task_id)
        await update.message.reply_text(
            f"""🗑️ **Confirm Task Deletion**

**Task**: {MessageFormatter.escape_markdown(task.description)}
**ID**: {task_id}
**Status**: {'✅ Done' if task.done else '📝 Todo'}

⚠️ **Warning**: This action cannot be undone\\.

Are you sure you want to delete this task?"""
            , reply_markup=keyboard, parse_mode='MarkdownV2')


@command_handler('/addtask', 'Create task with narrative flow',
    'Usage: /addtask', 'tasks')
async def narrative_add_task_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Start the narrative task creation flow."""
    user_id = update.effective_user.id if update.effective_user else None
    context.user_data['task_creation_state'
        ] = TaskCreationState.AWAITING_DESCRIPTION.value
    context.user_data['partial_task'] = {'description': None, 'due_date':
        None, 'priority': 'Medium', 'category': None, 'client_id': None,
        'estimated_hours': None}
    context.user_data['step_history'] = []
    context.user_data['started_at'] = datetime.now().isoformat()
    await update.message.reply_text(MessageFormatter.format_info_message(
        "📝 Let's create a new task!", {'Action':
        "Please describe what you'd like to add."}), parse_mode='MarkdownV2')


async def handle_narrative_task_creation(update: Update, context:
    ContextTypes.DEFAULT_TYPE, user_input: str) ->None:
    """Handle the narrative task creation flow."""
    if 'task_creation_state' not in context.user_data:
        return
    current_state = context.user_data['task_creation_state']
    partial_task = context.user_data['partial_task']
    if (current_state == TaskCreationState.AWAITING_CATEGORY.value and
        context.user_data.get('awaiting_custom_category')):
        del context.user_data['awaiting_custom_category']
        await _handle_category_step(update, context, user_input.strip())
        return
    if (current_state == TaskCreationState.AWAITING_CLIENT.value and
        context.user_data.get('awaiting_new_client')):
        del context.user_data['awaiting_new_client']
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


async def _handle_description_step(update: Update, context: ContextTypes.
    DEFAULT_TYPE, description: str) ->None:
    if hasattr(update, 'answer'):
        await update.answer()
    if not description.strip():
        await update.message.reply_text(MessageFormatter.
            format_error_message('Description cannot be empty',
            'Please provide a task description.'), parse_mode='MarkdownV2')
        return
    context.user_data['partial_task']['description'] = description.strip()
    context.user_data['task_creation_state'
        ] = TaskCreationState.AWAITING_DUE_DATE.value
    context.user_data['step_history'].append({'step': 'description',
        'value': description.strip(), 'timestamp': datetime.now().isoformat()})
    keyboard_buttons = [[UnifiedButtonBuilder.create_button(text='📅 Today',
        callback_data='addtask_step:due_date:today', button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.create_button(text='📅 Tomorrow',
        callback_data='addtask_step:due_date:tomorrow', button_type=
        ButtonType.INFO)], [UnifiedButtonBuilder.create_button(text=
        '📅 This Week', callback_data='addtask_step:due_date:week',
        button_type=ButtonType.INFO), UnifiedButtonBuilder.create_button(
        text='📅 Next Week', callback_data='addtask_step:due_date:next_week',
        button_type=ButtonType.INFO)], [UnifiedButtonBuilder.create_button(
        text='⏭️ Skip', callback_data='addtask_step:due_date:skip',
        button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.
        create_button(text='❌ Cancel', callback_data='addtask_step:cancel',
        button_type=ButtonType.DANGER)]]
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    await update.message.reply_text(MessageFormatter.format_info_message(
        f'📝 Task: {MessageFormatter.escape_markdown(description.strip())}',
        {'Question': 'When is this due?'}), reply_markup=keyboard,
        parse_mode='MarkdownV2')


async def _handle_due_date_step(update_or_query, context: ContextTypes.
    DEFAULT_TYPE, due_date_input: str) ->None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    due_date = None
    if due_date_input == 'skip':
        due_date = None
    elif due_date_input == 'today':
        due_date = DateTimeService.create_due_date_for_today()
    elif due_date_input == 'tomorrow':
        due_date = DateTimeService.create_due_date_for_tomorrow()
    elif due_date_input == 'week':
        due_date = DateTimeService.create_due_date_for_week()
    elif due_date_input == 'next_week':
        due_date = DateTimeService.create_due_date_for_next_week()
    else:
        due_date = DateTimeService.parse_user_date(due_date_input)
        if due_date is None:
            message = MessageFormatter.format_error_message(
                'Invalid date format', MessageFormatter.escape_markdown(
                'Please use natural language (e.g., "Monday", "next week") or YYYY-MM-DD format.'))
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(message, parse_mode
                    ='MarkdownV2')
            else:
                await update_or_query.message.reply_text(message,
                    parse_mode='MarkdownV2')
            return
    # Store datetime object directly instead of converting to string
    context.user_data['partial_task']['due_date'] = due_date if due_date else None
    context.user_data['task_creation_state'
        ] = TaskCreationState.AWAITING_PRIORITY.value
    context.user_data['step_history'].append({'step': 'due_date', 'value': 
        due_date.isoformat() if due_date else None, 'timestamp': datetime.
        now().isoformat()})
    keyboard_buttons = [[UnifiedButtonBuilder.create_button(text='🟢 Low',
        callback_data='addtask_step:priority:Low', button_type=ButtonType.
        SUCCESS), UnifiedButtonBuilder.create_button(text='🟡 Medium',
        callback_data='addtask_step:priority:Medium', button_type=
        ButtonType.WARNING)], [UnifiedButtonBuilder.create_button(text=
        '🟠 High', callback_data='addtask_step:priority:High', button_type=
        ButtonType.WARNING), UnifiedButtonBuilder.create_button(text=
        '🔴 Critical', callback_data='addtask_step:priority:Critical',
        button_type=ButtonType.DANGER)], [UnifiedButtonBuilder.
        create_button(text='⏭️ Skip', callback_data=
        'addtask_step:priority:skip', button_type=ButtonType.SECONDARY),
        UnifiedButtonBuilder.create_button(text='❌ Cancel', callback_data=
        'addtask_step:cancel', button_type=ButtonType.DANGER)]]
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    due_date_text = due_date.strftime('%Y-%m-%d'
        ) if due_date else 'No due date'
    message = MessageFormatter.format_info_message(f'📅 Due: {due_date_text}',
        {'Question': 'How urgent is this task?'})
    print('[DEBUG] Due date message to Telegram:')
    print(repr(message))
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(message, reply_markup=
            keyboard, parse_mode='MarkdownV2')
    else:
        await update_or_query.message.reply_text(message, reply_markup=
            keyboard, parse_mode='MarkdownV2')


async def _handle_priority_step(update_or_query, context: ContextTypes.
    DEFAULT_TYPE, priority_input: str) ->None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    if priority_input == 'skip':
        priority = 'Medium'
    else:
        priority = priority_input
    context.user_data['partial_task']['priority'] = priority
    context.user_data['task_creation_state'
        ] = TaskCreationState.AWAITING_CATEGORY.value
    context.user_data['step_history'].append({'step': 'priority', 'value':
        priority, 'timestamp': datetime.now().isoformat()})
    with next(get_session()) as session:
        task_repo = TaskRepository(session)
        available_categories = task_repo.get_all_categories()
    common_categories = ['Work', 'Personal', 'Health', 'Learning',
        'Finance', 'Home']
    for cat in common_categories:
        if cat not in available_categories:
            available_categories.append(cat)
    category_buttons = []
    for i in range(0, min(len(available_categories), 8), 2):
        row = []
        for j in range(2):
            if i + j < len(available_categories):
                cat = available_categories[i + j]
                row.append(UnifiedButtonBuilder.create_button(text=
                    f'📂 {cat}', callback_data=
                    f'addtask_step:category:{cat}', button_type=ButtonType.
                    INFO))
        category_buttons.append(row)
    category_buttons.append([UnifiedButtonBuilder.create_button(text=
        '➕ Custom', callback_data='addtask_step:category:custom',
        button_type=ButtonType.PRIMARY), UnifiedButtonBuilder.create_button
        (text='⏭️ Skip', callback_data='addtask_step:category:skip',
        button_type=ButtonType.SECONDARY)])
    category_buttons.append([UnifiedButtonBuilder.create_button(text=
        '❌ Cancel', callback_data='addtask_step:cancel', button_type=ButtonType.DANGER)])
    keyboard = InlineKeyboardMarkup(category_buttons)
    priority_emoji = {'Low': '🟢', 'Medium': '🟡', 'High': '🟠', 'Critical': '🔴'
        }.get(priority, '⚪')
    message = MessageFormatter.format_info_message(
        f'{priority_emoji} Priority: {MessageFormatter.escape_markdown(priority)}'
        , {'Question': 'What category is this?'})
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(message, reply_markup=
            keyboard, parse_mode='MarkdownV2')
    else:
        await update_or_query.message.reply_text(message, reply_markup=
            keyboard, parse_mode='MarkdownV2')


async def _handle_category_step(update_or_query, context: ContextTypes.
    DEFAULT_TYPE, category_input: str) ->None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    if category_input == 'skip':
        category = None
        next_state = TaskCreationState.CONFIRMATION.value
    elif category_input == 'custom':
        context.user_data['task_creation_state'
            ] = TaskCreationState.AWAITING_CATEGORY.value
        context.user_data['awaiting_custom_category'] = True
        message = MessageFormatter.format_info_message('📂 Custom Category',
            {'Action': 'Please enter the category name:'})
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(message, parse_mode=
                'MarkdownV2')
        else:
            await update_or_query.message.reply_text(message, parse_mode=
                'MarkdownV2')
        return
    else:
        category = category_input
        if category.lower() == 'work':
            next_state = TaskCreationState.AWAITING_CLIENT.value
        else:
            next_state = TaskCreationState.CONFIRMATION.value
    context.user_data['partial_task']['category'] = category
    context.user_data['step_history'].append({'step': 'category', 'value':
        category, 'timestamp': datetime.now().isoformat()})
    if next_state == TaskCreationState.AWAITING_CLIENT.value:
        context.user_data['task_creation_state'
            ] = TaskCreationState.AWAITING_CLIENT.value
        await _handle_client_step(update_or_query, context, None)
    else:
        context.user_data['task_creation_state'
            ] = TaskCreationState.CONFIRMATION.value
        await _show_confirmation(update_or_query, context)


async def _handle_client_step(update_or_query, context: ContextTypes.
    DEFAULT_TYPE, client_input: str) ->None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    if client_input == 'skip':
        client_id = None
        next_state = TaskCreationState.CONFIRMATION.value
    elif client_input is None:
        with next(get_session()) as session:
            client_repo = ClientRepository(session)
            clients = client_repo.get_clients_with_task_counts()
        if not clients:
            client_id = None
            next_state = TaskCreationState.CONFIRMATION.value
        else:
            client_buttons = []
            for i in range(0, min(len(clients), 6), 2):
                row = []
                for j in range(2):
                    if i + j < len(clients):
                        client = clients[i + j]
                        task_count = client['active_task_count'] or 0
                        row.append(UnifiedButtonBuilder.create_button(text=
                            f'👤 {MessageFormatter.escape_markdown(client["name"])} ({task_count})'
                            , callback_data=
                            f'addtask_step:client:{client["id"]}', button_type
                            =ButtonType.INFO))
                client_buttons.append(row)
            client_buttons.append([UnifiedButtonBuilder.create_button(text=
                '➕ New Client', callback_data='addtask_step:client:new',
                button_type=ButtonType.PRIMARY), UnifiedButtonBuilder.
                create_button(text='⏭️ Skip', callback_data=
                'addtask_step:client:skip', button_type=ButtonType.SECONDARY)])
            client_buttons.append([UnifiedButtonBuilder.create_button(text=
                '❌ Cancel', callback_data='addtask_step:cancel',
                button_type=ButtonType.DANGER)])
            keyboard = InlineKeyboardMarkup(client_buttons)
            message = MessageFormatter.format_info_message('💼 Category: Work',
                {'Question': 'Which client is this for?'})
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(message,
                    reply_markup=keyboard, parse_mode='MarkdownV2')
            else:
                await update_or_query.message.reply_text(message,
                    reply_markup=keyboard, parse_mode='MarkdownV2')
            return
    else:
        try:
            client_id = int(client_input)
            next_state = TaskCreationState.CONFIRMATION.value
        except (ValueError, TypeError):
            if client_input == 'new':
                context.user_data['task_creation_state'
                    ] = TaskCreationState.AWAITING_CLIENT.value
                context.user_data['awaiting_new_client'] = True
                message = MessageFormatter.format_info_message('➕ New Client',
                    {'Action': 'Please enter the client name:'})
                if hasattr(update_or_query, 'edit_message_text'):
                    await update_or_query.edit_message_text(message,
                        parse_mode='MarkdownV2')
                else:
                    await update_or_query.message.reply_text(message,
                        parse_mode='MarkdownV2')
                return
            else:
                client_id = None
                next_state = TaskCreationState.CONFIRMATION.value
    context.user_data['partial_task']['client_id'] = client_id
    context.user_data['task_creation_state'
        ] = TaskCreationState.CONFIRMATION.value
    context.user_data['step_history'].append({'step': 'client', 'value':
        client_id, 'timestamp': datetime.now().isoformat()})
    await _show_confirmation(update_or_query, context)


async def _show_confirmation(update_or_query, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    partial_task = context.user_data['partial_task']
    summary_lines = [f"📝 **{partial_task['description']}**"]
    if partial_task['due_date']:
        due_date_display = DateTimeService.format_for_display(partial_task['due_date'])
        summary_lines.append(f"📅 Due: {due_date_display}")
    priority_emoji = {'Low': '🟢', 'Medium': '🟡', 'High': '🟠', 'Critical': '🔴'
        }.get(partial_task['priority'], '⚪')
    summary_lines.append(
        f"{priority_emoji} Priority: {partial_task['priority']}")
    if partial_task['category']:
        summary_lines.append(f"📂 Category: {partial_task['category']}")
    if partial_task['client_id']:
        with next(get_session()) as session:
            client_repo = ClientRepository(session)
            client = client_repo.get_client_by_id(partial_task['client_id'])
            if client:
                summary_lines.append(f'👤 Client: {client.name}')
    summary_text = '\n'.join(summary_lines)
    keyboard_buttons = [[UnifiedButtonBuilder.create_button(text=
        '✅ Create Task', callback_data='addtask_step:confirm', button_type=
        ButtonType.SUCCESS), UnifiedButtonBuilder.create_button(text=
        '✏️ Edit', callback_data='addtask_step:edit', button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.create_button(text=
        '❌ Cancel', callback_data='addtask_step:cancel', button_type=ButtonType.DANGER)]]
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    message = MessageFormatter.format_success_message('✅ Task Summary', {
        'Summary': summary_text})
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(message, reply_markup=
            keyboard, parse_mode='MarkdownV2')
    else:
        await update_or_query.message.reply_text(message, reply_markup=
            keyboard, parse_mode='MarkdownV2')


async def _handle_confirmation_step(update_or_query, context: ContextTypes.
    DEFAULT_TYPE, action: str) ->None:
    print(f'[DEBUG] Entered _handle_confirmation_step with action={action}')
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    if action == 'confirm':
        await _create_final_task(update_or_query, context)
    elif action == 'edit':
        await _show_edit_options(update_or_query, context)
    elif action == 'cancel':
        await _cancel_task_creation(update_or_query, context)


async def _create_final_task(update_or_query, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Create the final task with all collected data."""
    partial_task = context.user_data['partial_task']
    due_date = None
    if partial_task['due_date']:
        # Convert to UTC for storage using DateTimeService
        due_date = DateTimeService.format_for_storage(partial_task['due_date'])
        # Validate the due date
        if not DateTimeService.validate_due_date(due_date):
            message = MessageFormatter.format_error_message(
                'Invalid due date', MessageFormatter.escape_markdown(
                'Due date cannot be in the past. Please select a future date.'))
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(message, parse_mode='MarkdownV2')
            else:
                await update_or_query.message.reply_text(message, parse_mode='MarkdownV2')
            return
    task_service = _get_task_service()
    result = await task_service.create_task_with_metadata(description=
        partial_task['description'], priority=partial_task['priority'],
        due_date=due_date, category=partial_task['category'],
        estimated_hours=partial_task['estimated_hours'], client_id=
        partial_task['client_id'])
    if result['success']:
        task_data = result['data']
        emit_task_event(_task_event_bus, 'task_created', task_data)
        message = MessageFormatter.format_success_message(
            '✅ Task created successfully!', {'ID': task_data['id'],
            'Description': task_data['description'], 'Priority': task_data[
            'priority'], 'Due Date': DateTimeService.format_for_display(task_data['due_date']),
            'Category': task_data['category'] or 'None'})
        print('[DEBUG] outgoing success message:\n', message)
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(message, parse_mode=
                'MarkdownV2')
        else:
            await update_or_query.message.reply_text(message, parse_mode=
                'MarkdownV2')
        _clear_task_creation_state(context)
    else:
        message = MessageFormatter.format_error_message(
            f"❌ Error creating task: {MessageFormatter.escape_markdown(result['message'])}"
            , 'Please try again or use /add for basic task creation.')
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(message, parse_mode=
                'MarkdownV2')
        else:
            await update_or_query.message.reply_text(message, parse_mode=
                'MarkdownV2')


async def _cancel_task_creation(update_or_query, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    _clear_task_creation_state(context)
    message = MessageFormatter.format_info_message('❌ Task creation cancelled',
        {'Action':
        'Use /addtask to start over or /add for basic task creation.'})
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(message, parse_mode=
            'MarkdownV2')
    else:
        await update_or_query.message.reply_text(message, parse_mode=
            'MarkdownV2')


async def _show_edit_options(update_or_query, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    if hasattr(update_or_query, 'answer'):
        await update_or_query.answer()
    message = MessageFormatter.format_info_message('✏️ Edit Options', {
        'Status':
        'Edit functionality coming soon. Please cancel and start over to make changes.'
        })
    keyboard_buttons = [[UnifiedButtonBuilder.create_button(text='❌ Cancel',
        callback_data='addtask_step:cancel', button_type=ButtonType.DANGER)]]
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(message, reply_markup=
            keyboard, parse_mode='MarkdownV2')
    else:
        await update_or_query.message.reply_text(message, reply_markup=
            keyboard, parse_mode='MarkdownV2')


def _clear_task_creation_state(context: ContextTypes.DEFAULT_TYPE) ->None:
    """Clear task creation state from context."""
    keys_to_remove = ['task_creation_state', 'partial_task', 'step_history',
        'started_at', 'awaiting_custom_category', 'awaiting_new_client']
    for key in keys_to_remove:
        if key in context.user_data:
            del context.user_data[key]
