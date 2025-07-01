"""
UX Utilities for LarryBot2

This module provides utilities for creating inline keyboards, formatting messages,
and handling navigation following Telegram bot best practices.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any, Optional, Union, AsyncContextManager
import re
import time
import asyncio
from contextlib import asynccontextmanager
import logging

# Performance monitoring logger
perf_logger = logging.getLogger('performance')

@asynccontextmanager
async def performance_monitor(operation_name: str, warn_threshold: float = 2.0) -> AsyncContextManager[None]:
    """
    Context manager for monitoring operation performance.
    
    Args:
        operation_name: Name of the operation being monitored
        warn_threshold: Time in seconds after which to log a warning
    """
    start_time = time.time()
    try:
        yield
    finally:
        execution_time = time.time() - start_time
        if execution_time > warn_threshold:
            perf_logger.warning(f"{operation_name} took {execution_time:.2f}s (threshold: {warn_threshold}s)")
        elif execution_time > 0.5:  # Log info for operations over 0.5s
            perf_logger.info(f"{operation_name} completed in {execution_time:.2f}s")


class PerformanceHelper:
    """Helper class for performance monitoring and optimization."""
    
    @staticmethod
    async def with_timeout(coro, timeout_seconds: float = 10.0, operation_name: str = "operation"):
        """
        Execute a coroutine with timeout and performance monitoring.
        
        Args:
            coro: The coroutine to execute
            timeout_seconds: Timeout in seconds
            operation_name: Name for logging
            
        Returns:
            The result of the coroutine
            
        Raises:
            asyncio.TimeoutError: If operation times out
        """
        async with performance_monitor(operation_name, warn_threshold=timeout_seconds * 0.8):
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
    
    @staticmethod
    def log_slow_operation(operation_name: str, execution_time: float, threshold: float = 1.0):
        """Log slow operations for analysis."""
        if execution_time > threshold:
            perf_logger.warning(f"Slow operation detected: {operation_name} took {execution_time:.2f}s")


class KeyboardBuilder:
    """Build inline keyboards following Telegram best practices."""
    
    @staticmethod
    def build_task_keyboard(task_id: int, status: str, show_edit: bool = True) -> InlineKeyboardMarkup:
        """
        Build keyboard for task actions.
        
        Args:
            task_id: Task ID
            status: Current task status
            show_edit: Whether to show edit button
            
        Returns:
            InlineKeyboardMarkup with task action buttons
        """
        buttons = []
        
        # Only show "Done" for incomplete tasks
        if status != "Done":
            buttons.append(InlineKeyboardButton(
                "✅ Done", 
                callback_data=f"task_done:{task_id}"
            ))
        
        # Show edit button if requested and task is not done
        if show_edit and status != "Done":
            buttons.append(InlineKeyboardButton(
                "✏️ Edit", 
                callback_data=f"task_edit:{task_id}"
            ))
        
        # Always show delete button
        buttons.append(InlineKeyboardButton(
            "🗑️ Delete", 
            callback_data=f"task_delete:{task_id}"
        ))
        
        return InlineKeyboardMarkup([buttons])
    
    @staticmethod
    def build_task_list_keyboard(tasks: list) -> InlineKeyboardMarkup:
        """
        Build keyboard for task list with refresh and navigation buttons.
        
        Args:
            tasks: List of task objects or dictionaries
            
        Returns:
            InlineKeyboardMarkup with task list navigation buttons
        """
        buttons = []
        
        # If we have tasks, add some quick action buttons
        if tasks:
            # Add a button to view first few tasks
            task_buttons = []
            for i, task in enumerate(tasks[:3]):  # Show first 3 tasks
                if hasattr(task, 'id'):
                    task_id = task.id
                    description = task.description[:15] + "..." if len(task.description) > 15 else task.description
                else:
                    task_id = task.get('id')
                    desc = task.get('description', 'Unknown')
                    description = desc[:15] + "..." if len(desc) > 15 else desc
                
                task_buttons.append(InlineKeyboardButton(
                    f"📋 {description}",
                    callback_data=f"task_view:{task_id}"
                ))
            
            # Add task buttons in rows of 1
            for button in task_buttons:
                buttons.append([button])
        
        # Add navigation buttons
        nav_buttons = [
            InlineKeyboardButton("🔄 Refresh", callback_data="tasks_refresh"),
            InlineKeyboardButton("➕ Add Task", callback_data="add_task")
        ]
        buttons.append(nav_buttons)
        
        # Add back to main menu button
        buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def build_add_task_keyboard() -> InlineKeyboardMarkup:
        """Build keyboard for when no tasks are found."""
        buttons = [
            [InlineKeyboardButton("➕ Add New Task", callback_data="add_task")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="tasks_refresh")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def build_client_keyboard(client_id: int, client_name: str) -> InlineKeyboardMarkup:
        """
        Build keyboard for client actions.
        
        Args:
            client_id: Client ID
            client_name: Client name
            
        Returns:
            InlineKeyboardMarkup with client action buttons
        """
        buttons = []
        
        buttons.extend([
            InlineKeyboardButton(
                "📋 View Tasks", 
                callback_data=f"client_tasks:{client_id}"
            ),
            InlineKeyboardButton(
                "📊 Analytics", 
                callback_data=f"client_analytics:{client_id}"
            ),
            InlineKeyboardButton(
                "🗑️ Delete", 
                callback_data=f"client_delete:{client_id}"
            )
        ])
        
        return InlineKeyboardMarkup([buttons])
    
    @staticmethod
    def build_habit_keyboard(habit_id: int, habit_name: str, completed_today: bool = False) -> InlineKeyboardMarkup:
        """
        Build keyboard for habit actions.
        
        Args:
            habit_id: Habit ID
            habit_name: Habit name
            completed_today: Whether habit was completed today
            
        Returns:
            InlineKeyboardMarkup with habit action buttons
        """
        buttons = []
        
        # Show complete button only if not completed today
        if not completed_today:
            buttons.append(InlineKeyboardButton(
                "✅ Complete", 
                callback_data=f"habit_done:{habit_id}"
            ))
        
        buttons.extend([
            InlineKeyboardButton(
                "📊 Progress", 
                callback_data=f"habit_progress:{habit_id}"
            ),
            InlineKeyboardButton(
                "🗑️ Delete", 
                callback_data=f"habit_delete:{habit_id}"
            )
        ])
        
        return InlineKeyboardMarkup([buttons])
    
    @staticmethod
    def build_navigation_keyboard(
        show_back: bool = True, 
        show_main_menu: bool = True,
        custom_buttons: Optional[List[Dict[str, str]]] = None
    ) -> InlineKeyboardMarkup:
        """
        Build navigation keyboard.
        
        Args:
            show_back: Whether to show back button
            show_main_menu: Whether to show main menu button
            custom_buttons: List of custom buttons with 'text' and 'callback_data'
            
        Returns:
            InlineKeyboardMarkup with navigation buttons
        """
        buttons = []
        
        if custom_buttons:
            for button in custom_buttons:
                buttons.append([InlineKeyboardButton(
                    button['text'], 
                    callback_data=button['callback_data']
                )])
        
        # Add navigation buttons
        nav_buttons = []
        if show_back:
            nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data="nav_back"))
        if show_main_menu:
            nav_buttons.append(InlineKeyboardButton("🏠 Main Menu", callback_data="nav_main"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def build_pagination_keyboard(
        current_page: int, 
        total_pages: int, 
        base_callback: str,
        show_nav: bool = True
    ) -> InlineKeyboardMarkup:
        """
        Build pagination keyboard.
        
        Args:
            current_page: Current page number (1-based)
            total_pages: Total number of pages
            base_callback: Base callback data for pagination
            show_nav: Whether to show navigation buttons
            
        Returns:
            InlineKeyboardMarkup with pagination buttons
        """
        buttons = []
        
        # Pagination buttons
        pagination_buttons = []
        
        if current_page > 1:
            pagination_buttons.append(InlineKeyboardButton(
                "⬅️", 
                callback_data=f"{base_callback}:page:{current_page - 1}"
            ))
        
        pagination_buttons.append(InlineKeyboardButton(
            f"{current_page}/{total_pages}", 
            callback_data="no_action"
        ))
        
        if current_page < total_pages:
            pagination_buttons.append(InlineKeyboardButton(
                "➡️", 
                callback_data=f"{base_callback}:page:{current_page + 1}"
            ))
        
        if pagination_buttons:
            buttons.append(pagination_buttons)
        
        # Navigation buttons
        if show_nav:
            nav_buttons = [
                InlineKeyboardButton("⬅️ Back", callback_data="nav_back"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="nav_main")
            ]
            buttons.append(nav_buttons)
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def build_confirmation_keyboard(
        action: str, 
        item_id: int, 
        item_name: str = ""
    ) -> InlineKeyboardMarkup:
        """
        Build confirmation keyboard for destructive actions.
        
        Args:
            action: Action type (delete, bulk_delete, etc.)
            item_id: Item ID
            item_name: Item name for display
            
        Returns:
            InlineKeyboardMarkup with confirmation buttons
        """
        buttons = [
            [
                InlineKeyboardButton(
                    "✅ Confirm", 
                    callback_data=f"confirm_{action}:{item_id}"
                ),
                InlineKeyboardButton(
                    "❌ Cancel", 
                    callback_data="cancel_action"
                )
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="nav_back")]
        ]
        
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_client_list_keyboard() -> InlineKeyboardMarkup:
        """
        Build keyboard for client list actions.
        
        Returns:
            InlineKeyboardMarkup for client list actions
        """
        keyboard = [
            [
                InlineKeyboardButton("➕ Add Client", callback_data="client_add"),
                InlineKeyboardButton("📊 Analytics", callback_data="client_analytics")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="client_refresh"),
                InlineKeyboardButton("⬅️ Back", callback_data="nav_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_client_detail_keyboard(client_id: int, client_name: str) -> InlineKeyboardMarkup:
        """
        Build keyboard for client detail actions.
        
        Args:
            client_id: ID of the client
            client_name: Name of the client
            
        Returns:
            InlineKeyboardMarkup for client detail actions
        """
        keyboard = [
            [
                InlineKeyboardButton("📋 View Tasks", callback_data=f"client_tasks:{client_id}"),
                InlineKeyboardButton("📊 Analytics", callback_data=f"client_analytics:{client_id}")
            ],
            [
                InlineKeyboardButton("✏️ Edit", callback_data=f"client_edit:{client_id}"),
                InlineKeyboardButton("🗑️ Delete", callback_data=f"client_delete:{client_id}")
            ],
            [
                InlineKeyboardButton("⬅️ Back to Clients", callback_data="client_list"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="nav_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_habit_list_keyboard() -> InlineKeyboardMarkup:
        """
        Build keyboard for habit list actions.
        
        Returns:
            InlineKeyboardMarkup for habit list actions
        """
        keyboard = [
            [
                InlineKeyboardButton("➕ Add Habit", callback_data="habit_add"),
                InlineKeyboardButton("📊 Statistics", callback_data="habit_stats")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="habit_refresh"),
                InlineKeyboardButton("⬅️ Back", callback_data="nav_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_habit_detail_keyboard(habit_id: int, habit_name: str) -> InlineKeyboardMarkup:
        """
        Build keyboard for habit detail actions.
        
        Args:
            habit_id: ID of the habit
            habit_name: Name of the habit
            
        Returns:
            InlineKeyboardMarkup for habit detail actions
        """
        keyboard = [
            [
                InlineKeyboardButton("✅ Mark Done", callback_data=f"habit_done:{habit_id}"),
                InlineKeyboardButton("📊 Progress", callback_data=f"habit_progress:{habit_id}")
            ],
            [
                InlineKeyboardButton("✏️ Edit", callback_data=f"habit_edit:{habit_id}"),
                InlineKeyboardButton("🗑️ Delete", callback_data=f"habit_delete:{habit_id}")
            ],
            [
                InlineKeyboardButton("⬅️ Back to Habits", callback_data="habit_list"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="nav_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_reminder_list_keyboard() -> InlineKeyboardMarkup:
        """
        Build keyboard for reminder list actions.
        
        Returns:
            InlineKeyboardMarkup for reminder list actions
        """
        keyboard = [
            [
                InlineKeyboardButton("➕ Add Reminder", callback_data="reminder_add"),
                InlineKeyboardButton("📊 Statistics", callback_data="reminder_stats")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="reminder_refresh"),
                InlineKeyboardButton("⬅️ Back", callback_data="nav_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_reminder_action_keyboard(task_id: int, reminder_id: int) -> InlineKeyboardMarkup:
        """
        Build keyboard for reminder action responses.
        
        Args:
            task_id: ID of the task
            reminder_id: ID of the reminder
            
        Returns:
            InlineKeyboardMarkup for reminder actions
        """
        keyboard = [
            [
                InlineKeyboardButton("✅ Mark Done", callback_data=f"task_done:{task_id}"),
                InlineKeyboardButton("⏰ Snooze 1h", callback_data=f"reminder_snooze:{reminder_id}:1h")
            ],
            [
                InlineKeyboardButton("⏰ Snooze 1d", callback_data=f"reminder_snooze:{reminder_id}:1d"),
                InlineKeyboardButton("🗑️ Delete Reminder", callback_data=f"reminder_delete:{reminder_id}")
            ],
            [
                InlineKeyboardButton("📋 View Task", callback_data=f"task_view:{task_id}"),
                InlineKeyboardButton("❌ Dismiss", callback_data="reminder_dismiss")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_reminder_keyboard(reminder_id: int, is_active: bool = True) -> InlineKeyboardMarkup:
        """Build keyboard for reminder actions."""
        buttons = []
        
        if is_active:
            buttons.append([
                InlineKeyboardButton("✅ Complete", callback_data=f"reminder_complete:{reminder_id}"),
                InlineKeyboardButton("⏰ Snooze", callback_data=f"reminder_snooze:{reminder_id}")
            ])
            buttons.append([
                InlineKeyboardButton("📝 Edit", callback_data=f"reminder_edit:{reminder_id}"),
                InlineKeyboardButton("🗑️ Delete", callback_data=f"reminder_delete:{reminder_id}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton("🔄 Reactivate", callback_data=f"reminder_reactivate:{reminder_id}"),
                InlineKeyboardButton("🗑️ Delete", callback_data=f"reminder_delete:{reminder_id}")
            ])
        
        buttons.append([InlineKeyboardButton("📊 Statistics", callback_data=f"reminder_stats:{reminder_id}")])
        buttons.append([InlineKeyboardButton("🔙 Back to Reminders", callback_data="reminders_list")])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def build_analytics_keyboard() -> InlineKeyboardMarkup:
        """Build keyboard for analytics navigation."""
        buttons = [
            [
                InlineKeyboardButton("📈 Detailed", callback_data="analytics_detailed"),
                InlineKeyboardButton("📊 Productivity", callback_data="analytics_productivity")
            ],
            [
                InlineKeyboardButton("⏰ Time Tracking", callback_data="analytics_time"),
                InlineKeyboardButton("🎯 Performance", callback_data="analytics_performance")
            ],
            [
                InlineKeyboardButton("📅 Trends", callback_data="analytics_trends"),
                InlineKeyboardButton("📋 Reports", callback_data="analytics_reports")
            ],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
        ]
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def build_filter_keyboard() -> InlineKeyboardMarkup:
        """Build keyboard for advanced filtering options."""
        buttons = [
            [
                InlineKeyboardButton("📅 Date Range", callback_data="filter_date_range"),
                InlineKeyboardButton("🎯 Priority", callback_data="filter_priority")
            ],
            [
                InlineKeyboardButton("📋 Status", callback_data="filter_status"),
                InlineKeyboardButton("🏷️ Tags", callback_data="filter_tags")
            ],
            [
                InlineKeyboardButton("📂 Category", callback_data="filter_category"),
                InlineKeyboardButton("⏰ Time Tracking", callback_data="filter_time")
            ],
            [
                InlineKeyboardButton("🔍 Advanced Search", callback_data="filter_advanced_search"),
                InlineKeyboardButton("💾 Save Filter", callback_data="filter_save")
            ],
            [InlineKeyboardButton("🔙 Back to Tasks", callback_data="tasks_list")]
        ]
        
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_attachment_keyboard(attachment_id: int, task_id: int) -> InlineKeyboardMarkup:
        """Build keyboard for individual attachment actions."""
        buttons = [
            [
                InlineKeyboardButton("📝 Edit Description", callback_data=f"attachment_edit_desc:{attachment_id}"),
                InlineKeyboardButton("📊 View Details", callback_data=f"attachment_details:{attachment_id}")
            ],
            [
                InlineKeyboardButton("🗑️ Remove", callback_data=f"attachment_remove:{attachment_id}"),
                InlineKeyboardButton("📋 Task Details", callback_data=f"task_details:{task_id}")
            ],
            [InlineKeyboardButton("🔙 Back to Attachments", callback_data=f"attachments_list:{task_id}")]
        ]
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def build_attachments_list_keyboard(task_id: int, attachment_count: int) -> InlineKeyboardMarkup:
        """Build keyboard for attachments list management."""
        buttons = []
        
        if attachment_count > 0:
            buttons.append([
                InlineKeyboardButton("📊 Statistics", callback_data=f"attachment_stats:{task_id}"),
                InlineKeyboardButton("📝 Add Description", callback_data=f"attachment_add_desc:{task_id}")
            ])
            buttons.append([
                InlineKeyboardButton("🗑️ Bulk Remove", callback_data=f"attachment_bulk_remove:{task_id}"),
                InlineKeyboardButton("📋 Export List", callback_data=f"attachment_export:{task_id}")
            ])
        
        buttons.append([InlineKeyboardButton("📎 Add New File", callback_data=f"attachment_add:{task_id}")])
        buttons.append([InlineKeyboardButton("🔙 Back to Task", callback_data=f"task_details:{task_id}")])
        
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_calendar_keyboard() -> InlineKeyboardMarkup:
        """Build keyboard for calendar navigation."""
        buttons = [
            [
                InlineKeyboardButton("📅 Today", callback_data="calendar_today"),
                InlineKeyboardButton("📅 Week", callback_data="calendar_week")
            ],
            [
                InlineKeyboardButton("📅 Month", callback_data="calendar_month"),
                InlineKeyboardButton("📅 Upcoming", callback_data="calendar_upcoming")
            ],
            [
                InlineKeyboardButton("🔄 Sync", callback_data="calendar_sync"),
                InlineKeyboardButton("⚙️ Settings", callback_data="calendar_settings")
            ],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
        ]
        
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_bulk_operations_keyboard() -> InlineKeyboardMarkup:
        """Build keyboard for bulk operations menu."""
        buttons = [
            [
                InlineKeyboardButton("📋 Status", callback_data="bulk_status_menu"),
                InlineKeyboardButton("🎯 Priority", callback_data="bulk_priority_menu")
            ],
            [
                InlineKeyboardButton("👥 Assign", callback_data="bulk_assign_menu"),
                InlineKeyboardButton("🗑️ Delete", callback_data="bulk_delete_menu")
            ],
            [
                InlineKeyboardButton("📊 Preview", callback_data="bulk_preview"),
                InlineKeyboardButton("💾 Save Selection", callback_data="bulk_save_selection")
            ],
            [InlineKeyboardButton("🔙 Back to Tasks", callback_data="tasks_list")]
        ]
        
        return InlineKeyboardMarkup(buttons)


class MessageFormatter:
    """Format messages following Telegram best practices."""
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Escape text for MarkdownV2 format.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for MarkdownV2
        """
        if not text:
            return text
        
        # Characters that need escaping in MarkdownV2
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    @staticmethod
    def format_task_list(tasks: list, title: str = "Tasks") -> str:
        """
        Format a list of tasks with rich formatting.
        
        Args:
            tasks: List of task objects or dictionaries
            title: Title for the task list
            
        Returns:
            Formatted task list string
        """
        if not tasks:
            return f"📋 **{title}**\n\nNo tasks found."
        
        message = f"📋 **{title}** \\({len(tasks)} found\\)\n\n"
        
        for i, task in enumerate(tasks, 1):
            # Handle both Task objects and dictionaries
            if hasattr(task, 'priority'):
                # Task object
                task_id = task.id
                description = task.description
                priority = getattr(task, 'priority', 'Medium')
                status = getattr(task, 'status', 'Todo')
                category = getattr(task, 'category', None)
                due_date = getattr(task, 'due_date', None)
                tags = getattr(task, 'tags', None)
            else:
                # Dictionary
                task_id = task.get('id')
                description = task.get('description', '')
                priority = task.get('priority', 'Medium')
                status = task.get('status', 'Todo')
                category = task.get('category')
                due_date = task.get('due_date')
                tags = task.get('tags')
            
            # Task header with priority indicator
            priority_emoji = {
                'Low': '🟢',
                'Medium': '🟡', 
                'High': '🟠',
                'Critical': '🔴'
            }.get(priority, '⚪')
            
            status_emoji = {
                'Todo': '📝',
                'In Progress': '🔄',
                'Review': '👀',
                'Done': '✅'
            }.get(status, '📝')
            
            message += f"{i}\\. {priority_emoji} **{MessageFormatter.escape_markdown(description)}** \\(ID: {task_id}\\)\n"
            message += f"   {status_emoji} {status} \\| {priority}\n"
            
            # Add category if present
            if category:
                message += f"   📂 {MessageFormatter.escape_markdown(category)}\n"
            
            # Add due date if present
            if due_date:
                if isinstance(due_date, str):
                    message += f"   📅 Due: {due_date}\n"
                else:
                    message += f"   📅 Due: {due_date.strftime('%Y-%m-%d')}\n"
            
            # Add tags if present
            if tags:
                if isinstance(tags, str):
                    # Handle JSON string or comma-separated string
                    import json
                    try:
                        tags_list = json.loads(tags)
                    except (json.JSONDecodeError, TypeError):
                        tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
                elif isinstance(tags, list):
                    tags_list = tags
                else:
                    tags_list = []
                
                if tags_list:
                    message += f"   🏷️ {', '.join([MessageFormatter.escape_markdown(str(tag)) for tag in tags_list])}\n"
            
            message += "\n"
        
        return message
    
    @staticmethod
    def format_client_list(clients: List[Dict]) -> str:
        """
        Format client list with proper MarkdownV2 escaping.
        
        Args:
            clients: List of client dictionaries
            
        Returns:
            Formatted client list message
        """
        if not clients:
            return "👥 **Clients**\n\nNo clients found."
        
        message = f"👥 **Clients** \\({len(clients)} found\\)\n\n"
        
        for client in clients:
            name = MessageFormatter.escape_markdown(client.get('name', 'Unknown'))
            client_id = client.get('id', 'N/A')
            task_count = client.get('task_count', 0)
            
            message += f"🏢 **{name}** \\(ID: {client_id}\\)\n"
            message += f"   📋 Tasks: {task_count}\n\n"
        
        return message.strip()
    
    @staticmethod
    def format_habit_list(habits: List[Dict]) -> str:
        """
        Format habit list with progress visualization.
        
        Args:
            habits: List of habit dictionaries
            
        Returns:
            Formatted habit list message
        """
        if not habits:
            return "🔄 **Habits**\n\nNo habits found."
        
        message = f"🔄 **Habits** \\({len(habits)} found\\)\n\n"
        
        for habit in habits:
            name = MessageFormatter.escape_markdown(habit.get('name', 'Unknown'))
            habit_id = habit.get('id', 'N/A')
            streak = habit.get('streak', 0)
            last_completed = habit.get('last_completed', None)
            
            # Streak emoji based on length
            if streak >= 7:
                streak_emoji = "🔥"
            elif streak >= 3:
                streak_emoji = "⚡"
            else:
                streak_emoji = "📈"
            
            message += f"{streak_emoji} **{name}** \\(ID: {habit_id}\\)\n"
            message += f"   🔥 Streak: {streak} days\n"
            
            if last_completed:
                if isinstance(last_completed, str):
                    message += f"   📅 Last: {MessageFormatter.escape_markdown(last_completed)}\n"
            
            message += "\n"
        
        return message.strip()
    
    @staticmethod
    def format_error_message(error: str, suggestion: str = "") -> str:
        """
        Format error message with helpful suggestions.
        
        Args:
            error: Error message
            suggestion: Helpful suggestion for user
            
        Returns:
            Formatted error message
        """
        message = f"❌ **Error**\n\n{MessageFormatter.escape_markdown(error)}"
        
        if suggestion:
            message += f"\n\n💡 **Suggestion:**\n{MessageFormatter.escape_markdown(suggestion)}"
        
        return message
    
    @staticmethod
    def format_success_message(message: str, details: Optional[Dict] = None) -> str:
        """
        Format success message with optional details.
        
        Args:
            message: Success message
            details: Optional details to include
            
        Returns:
            Formatted success message
        """
        formatted_message = f"✅ **Success**\n\n{MessageFormatter.escape_markdown(message)}"
        
        if details:
            formatted_message += "\n\n📋 **Details:**\n"
            for key, value in details.items():
                formatted_message += f"   • {MessageFormatter.escape_markdown(str(key))}: {MessageFormatter.escape_markdown(str(value))}\n"
        
        return formatted_message
    
    @staticmethod
    def format_analytics(analytics: Dict) -> str:
        """
        Format analytics data with visual indicators.
        
        Args:
            analytics: Analytics data dictionary
            
        Returns:
            Formatted analytics message
        """
        message = "📊 **Analytics**\n\n"
        
        # Basic stats
        total_tasks = analytics.get('total_tasks', 0)
        completed_tasks = analytics.get('completed_tasks', 0)
        incomplete_tasks = analytics.get('incomplete_tasks', 0)
        overdue_tasks = analytics.get('overdue_tasks', 0)
        completion_rate = analytics.get('completion_rate', 0)
        
        message += f"📈 Total Tasks: {total_tasks}\n"
        message += f"✅ Completed: {completed_tasks}\n"
        message += f"⏳ Incomplete: {incomplete_tasks}\n"
        message += f"⚠️ Overdue: {overdue_tasks}\n"
        message += f"📊 Completion Rate: {completion_rate:.1f}%\n\n"
        
        # Priority distribution
        priority_dist = analytics.get('priority_distribution', {})
        if priority_dist:
            message += "🎯 **Priority Distribution:**\n"
            for priority, count in priority_dist.items():
                priority_emoji = {
                    'Low': '🟢',
                    'Medium': '🟡',
                    'High': '🟠',
                    'Critical': '🔴'
                }.get(priority, '⚪')
                message += f"   {priority_emoji} {priority}: {count}\n"
            message += "\n"
        
        # Status distribution
        status_dist = analytics.get('status_distribution', {})
        if status_dist:
            message += "📋 **Status Distribution:**\n"
            for status, count in status_dist.items():
                status_emoji = {
                    'Todo': '⏳',
                    'In Progress': '🔄',
                    'Review': '👀',
                    'Done': '✅'
                }.get(status, '❓')
                message += f"   {status_emoji} {status}: {count}\n"
        
        return message.strip()

    @staticmethod
    def format_warning_message(title: str, details: dict) -> str:
        """
        Format a warning message with rich formatting.
        
        Args:
            title: Warning title
            details: Dictionary of details to display
            
        Returns:
            Formatted warning message string
        """
        message = f"⚠️ **{title}**\n\n"
        
        for key, value in details.items():
            safe_key = MessageFormatter.escape_markdown(str(key))
            safe_value = MessageFormatter.escape_markdown(str(value))
            message += f"• **{safe_key}**: {safe_value}\n"
        
        return message
    
    @staticmethod
    def format_info_message(title: str, details: dict) -> str:
        """
        Format an info message with rich formatting.
        
        Args:
            title: Info title
            details: Dictionary of details to display
            
        Returns:
            Formatted info message string
        """
        message = f"ℹ️ **{title}**\n\n"
        
        for key, value in details.items():
            safe_key = MessageFormatter.escape_markdown(str(key))
            safe_value = MessageFormatter.escape_markdown(str(value))
            message += f"• **{safe_key}**: {safe_value}\n"
        
        return message


class NavigationHelper:
    """Helper for navigation and menu management."""
    
    @staticmethod
    def get_main_menu_keyboard() -> InlineKeyboardMarkup:
        """
        Get main menu keyboard.
        
        Returns:
            InlineKeyboardMarkup with main menu options
        """
        buttons = [
            [
                InlineKeyboardButton("📋 Tasks", callback_data="menu_tasks"),
                InlineKeyboardButton("👥 Clients", callback_data="menu_clients")
            ],
            [
                InlineKeyboardButton("🔄 Habits", callback_data="menu_habits"),
                InlineKeyboardButton("⏰ Reminders", callback_data="menu_reminders")
            ],
            [
                InlineKeyboardButton("📊 Analytics", callback_data="menu_analytics"),
                InlineKeyboardButton("📎 Files", callback_data="menu_files")
            ],
            [
                InlineKeyboardButton("📅 Calendar", callback_data="menu_calendar"),
                InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")
            ]
        ]
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def get_task_menu_keyboard() -> InlineKeyboardMarkup:
        """
        Get task management menu keyboard.
        
        Returns:
            InlineKeyboardMarkup with task menu options
        """
        buttons = [
            [
                InlineKeyboardButton("📋 View Tasks", callback_data="tasks_list"),
                InlineKeyboardButton("➕ Add Task", callback_data="task_add")
            ],
            [
                InlineKeyboardButton("🔍 Search", callback_data="tasks_search"),
                InlineKeyboardButton("📊 Analytics", callback_data="tasks_analytics")
            ],
            [
                InlineKeyboardButton("⚠️ Overdue", callback_data="tasks_overdue"),
                InlineKeyboardButton("📅 Today", callback_data="tasks_today")
            ],
            [
                InlineKeyboardButton("⬅️ Back", callback_data="nav_main")
            ]
        ]
        
        return InlineKeyboardMarkup(buttons)


class ChartBuilder:
    """Build visual charts and graphs using Unicode characters and ASCII art."""
    
    @staticmethod
    def build_bar_chart(data: dict, title: str = "Chart", max_width: int = 20) -> str:
        """
        Build a horizontal bar chart using Unicode characters.
        
        Args:
            data: Dictionary with label: value pairs
            title: Chart title
            max_width: Maximum width of bars in characters
            
        Returns:
            Formatted bar chart string
        """
        if not data:
            return f"📊 **{title}**\n\nNo data available."
        
        # Find maximum value for scaling
        max_value = max(data.values()) if data.values() else 1
        
        chart = f"📊 **{title}**\n\n"
        
        for label, value in data.items():
            # Calculate bar length
            bar_length = int((value / max_value) * max_width) if max_value > 0 else 0
            bar = "█" * bar_length + "░" * (max_width - bar_length)
            
            # Format label and value
            safe_label = MessageFormatter.escape_markdown(str(label))
            percentage = (value / max_value * 100) if max_value > 0 else 0
            
            chart += f"`{bar}` {safe_label} \\({value}\\) \\- {percentage:.1f}%\n"
        
        return chart
    
    @staticmethod
    def build_pie_chart(data: dict, title: str = "Distribution") -> str:
        """
        Build a pie chart representation using Unicode characters.
        
        Args:
            data: Dictionary with label: value pairs
            title: Chart title
            
        Returns:
            Formatted pie chart string
        """
        if not data:
            return f"🥧 **{title}**\n\nNo data available."
        
        total = sum(data.values())
        if total == 0:
            return f"🥧 **{title}**\n\nNo data available."
        
        # Pie chart characters (8 segments)
        pie_chars = ["🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "🟫", "⬛"]
        
        chart = f"🥧 **{title}**\n\n"
        
        # Calculate percentages and assign colors
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
        
        for i, (label, value) in enumerate(sorted_data):
            percentage = (value / total * 100)
            color = pie_chars[i % len(pie_chars)]
            safe_label = MessageFormatter.escape_markdown(str(label))
            
            chart += f"{color} {safe_label}: {value} \\({percentage:.1f}%\\)\n"
        
        return chart
    
    @staticmethod
    def build_progress_bar(current: int, total: int, width: int = 20, label: str = "Progress") -> str:
        """
        Build a progress bar with percentage.
        
        Args:
            current: Current value
            total: Total value
            width: Width of progress bar
            label: Label for the progress bar
            
        Returns:
            Formatted progress bar string
        """
        if total == 0:
            return f"📈 **{label}**: 0%"
        
        percentage = (current / total * 100)
        filled_width = int((current / total) * width)
        
        bar = "█" * filled_width + "░" * (width - filled_width)
        
        return f"📈 **{label}**: `{bar}` {percentage:.1f}% \\({current}/{total}\\)"
    
    @staticmethod
    def build_timeline_chart(data: list, title: str = "Timeline") -> str:
        """
        Build a timeline chart showing data over time.
        
        Args:
            data: List of tuples (date, value, label)
            title: Chart title
            
        Returns:
            Formatted timeline chart string
        """
        if not data:
            return f"📅 **{title}**\n\nNo data available."
        
        chart = f"📅 **{title}**\n\n"
        
        # Sort by date
        sorted_data = sorted(data, key=lambda x: x[0])
        
        for date, value, label in sorted_data:
            # Format date
            if hasattr(date, 'strftime'):
                date_str = date.strftime('%Y-%m-%d')
            else:
                date_str = str(date)
            
            safe_label = MessageFormatter.escape_markdown(str(label))
            chart += f"📅 **{date_str}**: {safe_label} \\({value}\\)\n"
        
        return chart
    
    @staticmethod
    def build_heatmap(data: dict, title: str = "Activity Heatmap") -> str:
        """
        Build a simple heatmap using Unicode characters.
        
        Args:
            data: Dictionary with key: value pairs
            title: Chart title
            
        Returns:
            Formatted heatmap string
        """
        if not data:
            return f"🔥 **{title}**\n\nNo data available."
        
        max_value = max(data.values()) if data.values() else 1
        
        chart = f"🔥 **{title}**\n\n"
        
        for key, value in data.items():
            # Determine intensity level
            intensity = value / max_value if max_value > 0 else 0
            
            if intensity >= 0.8:
                heat_char = "🔴"
            elif intensity >= 0.6:
                heat_char = "🟠"
            elif intensity >= 0.4:
                heat_char = "🟡"
            elif intensity >= 0.2:
                heat_char = "🟢"
            else:
                heat_char = "⚪"
            
            safe_key = MessageFormatter.escape_markdown(str(key))
            chart += f"{heat_char} {safe_key}: {value}\n"
        
        return chart


class AnalyticsFormatter:
    """Format analytics data with rich visualizations."""
    
    @staticmethod
    def format_task_analytics(analytics: dict) -> str:
        """
        Format comprehensive task analytics with visualizations.
        
        Args:
            analytics: Analytics data dictionary
            
        Returns:
            Formatted analytics string
        """
        message = f"📊 **Task Analytics Dashboard**\n\n"
        
        # Overview statistics
        total_tasks = analytics.get('total_tasks', 0)
        completed_tasks = analytics.get('completed_tasks', 0)
        incomplete_tasks = analytics.get('incomplete_tasks', 0)
        overdue_tasks = analytics.get('overdue_tasks', 0)
        completion_rate = analytics.get('completion_rate', 0)
        
        message += f"📈 **Overview**\n"
        message += f"• Total Tasks: {total_tasks}\n"
        message += f"• Completed: {completed_tasks} ✅\n"
        message += f"• Incomplete: {incomplete_tasks} ⏳\n"
        message += f"• Overdue: {overdue_tasks} ⚠️\n"
        message += f"• Completion Rate: {completion_rate:.1f}%\n\n"
        
        # Progress bar for completion rate
        message += ChartBuilder.build_progress_bar(completed_tasks, total_tasks, 20, "Completion Rate") + "\n\n"
        
        # Priority distribution chart
        if analytics.get('priority_distribution'):
            message += ChartBuilder.build_bar_chart(
                analytics['priority_distribution'], 
                "Priority Distribution"
            ) + "\n"
        
        # Status distribution chart
        if analytics.get('status_distribution'):
            message += ChartBuilder.build_pie_chart(
                analytics['status_distribution'], 
                "Status Distribution"
            ) + "\n"
        
        # Category distribution (if available)
        if analytics.get('category_distribution'):
            message += ChartBuilder.build_bar_chart(
                analytics['category_distribution'], 
                "Category Distribution"
            ) + "\n"
        
        # Insights
        message += f"💡 **Insights**\n"
        
        if completion_rate >= 80:
            message += f"• 🎉 **Excellent completion rate!** Keep up the great work\\.\n"
        elif completion_rate >= 60:
            message += f"• 📈 **Good progress!** You're on track\\.\n"
        elif completion_rate >= 40:
            message += f"• ⚠️ **Moderate completion rate** \\. Consider reviewing priorities\\.\n"
        else:
            message += f"• 📉 **Low completion rate** \\. Focus on high\\-priority tasks\\.\n"
        
        if overdue_tasks > 0:
            message += f"• ⚠️ **{overdue_tasks} overdue tasks** \\. Consider rescheduling or reprioritizing\\.\n"
        
        if incomplete_tasks > completed_tasks:
            message += f"• 📋 **More incomplete than complete tasks** \\. Consider breaking down large tasks\\.\n"
        
        return message
    
    @staticmethod
    def format_productivity_report(data: dict) -> str:
        """
        Format productivity report with visualizations.
        
        Args:
            data: Productivity data dictionary
            
        Returns:
            Formatted productivity report string
        """
        message = f"📈 **Productivity Report**\n\n"
        
        # Time tracking summary
        if 'time_tracking' in data:
            time_data = data['time_tracking']
            total_hours = time_data.get('total_hours', 0)
            avg_hours_per_day = time_data.get('avg_hours_per_day', 0)
            most_productive_day = time_data.get('most_productive_day', 'N/A')
            
            message += f"⏰ **Time Tracking**\n"
            message += f"• Total Hours: {total_hours:.1f}h\n"
            message += f"• Average per Day: {avg_hours_per_day:.1f}h\n"
            message += f"• Most Productive Day: {most_productive_day}\n\n"
        
        # Task completion trends
        if 'completion_trends' in data:
            trends = data['completion_trends']
            message += f"📊 **Completion Trends**\n"
            
            for period, count in trends.items():
                message += f"• {period}: {count} tasks\n"
            message += "\n"
        
        # Performance metrics
        if 'performance_metrics' in data:
            metrics = data['performance_metrics']
            efficiency = metrics.get('efficiency', 0)
            accuracy = metrics.get('accuracy', 0)
            
            message += f"🎯 **Performance Metrics**\n"
            message += ChartBuilder.build_progress_bar(efficiency, 100, 15, "Efficiency") + "\n"
            message += ChartBuilder.build_progress_bar(accuracy, 100, 15, "Accuracy") + "\n\n"
        
        return message 