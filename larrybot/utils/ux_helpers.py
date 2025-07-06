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
from telegram.helpers import escape_markdown as _tg_escape_md
from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
perf_logger = logging.getLogger('performance')


@asynccontextmanager
async def performance_monitor(operation_name: str, warn_threshold: float=2.0
    ) ->AsyncContextManager[None]:
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
            perf_logger.warning(
                f'{operation_name} took {execution_time:.2f}s (threshold: {warn_threshold}s)'
                )
        elif execution_time > 0.5:
            perf_logger.info(
                f'{operation_name} completed in {execution_time:.2f}s')


class PerformanceHelper:
    """Helper class for performance monitoring and optimization."""

    @staticmethod
    async def with_timeout(coro, timeout_seconds: float=10.0,
        operation_name: str='operation'):
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
        async with performance_monitor(operation_name, warn_threshold=
            timeout_seconds * 0.8):
            return await asyncio.wait_for(coro, timeout=timeout_seconds)

    @staticmethod
    def log_slow_operation(operation_name: str, execution_time: float,
        threshold: float=1.0):
        """Log slow operations for analysis."""
        if execution_time > threshold:
            perf_logger.warning(
                f'Slow operation detected: {operation_name} took {execution_time:.2f}s'
                )


class KeyboardBuilder:
    """Build inline keyboards following Telegram best practices."""

    @staticmethod
    def build_task_keyboard(task_id: int, status: str, show_edit: bool=True
        ) ->InlineKeyboardMarkup:
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
        if status != 'Done':
            buttons.append(UnifiedButtonBuilder.create_button(text='✅ Done',
                callback_data=f'task_done:{task_id}', button_type=
                ButtonType.INFO))
        if show_edit and status != 'Done':
            buttons.append(UnifiedButtonBuilder.create_button(text=
                '✏️ Edit', callback_data=f'task_edit:{task_id}',
                button_type=ButtonType.SECONDARY))
        buttons.append(UnifiedButtonBuilder.create_button(text='🗑️ Delete',
            callback_data=f'task_delete:{task_id}', button_type=ButtonType.DANGER))
        return InlineKeyboardMarkup([buttons])

    @staticmethod
    def build_task_list_keyboard(tasks: list) ->InlineKeyboardMarkup:
        """
        Build keyboard for task list with refresh and navigation buttons.
        
        Args:
            tasks: List of task objects or dictionaries
            
        Returns:
            InlineKeyboardMarkup with task list navigation buttons
        """
        buttons = []
        if tasks:
            task_buttons = []
            for i, task in enumerate(tasks[:3]):
                if hasattr(task, 'id'):
                    task_id = task.id
                    description = task.description[:15] + '...' if len(task
                        .description) > 15 else task.description
                else:
                    task_id = task.get('id')
                    desc = task.get('description', 'Unknown')
                    description = desc[:15] + '...' if len(desc) > 15 else desc
                task_buttons.append(UnifiedButtonBuilder.create_button(text
                    =f'📋 {description}', callback_data=
                    f'task_view:{task_id}', button_type=ButtonType.INFO))
            for button in task_buttons:
                buttons.append([button])
        nav_buttons = [UnifiedButtonBuilder.create_button(text='🔄 Refresh',
            callback_data='tasks_refresh', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='➕ Add Task',
            callback_data='add_task', button_type=ButtonType.PRIMARY)]
        buttons.append(nav_buttons)
        buttons.append([UnifiedButtonBuilder.create_button(text=
            '🏠 Main Menu', callback_data='main_menu', button_type=ButtonType.INFO)])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_add_task_keyboard() ->InlineKeyboardMarkup:
        """Build keyboard for when no tasks are found."""
        buttons = [[UnifiedButtonBuilder.create_button(text=
            '➕ Add New Task', callback_data='add_task', button_type=ButtonType.PRIMARY)], [UnifiedButtonBuilder.create_button(text=
            '🔄 Refresh', callback_data='tasks_refresh', button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.create_button(text=
            '🏠 Main Menu', callback_data='main_menu', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_client_keyboard(client_id: int, client_name: str
        ) ->InlineKeyboardMarkup:
        """
        Build keyboard for client actions.
        
        Args:
            client_id: Client ID
            client_name: Client name
            
        Returns:
            InlineKeyboardMarkup with client action buttons
        """
        buttons = []
        buttons.extend([UnifiedButtonBuilder.create_button(text=
            '📋 View Tasks', callback_data=f'client_tasks:{client_id}',
            button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.
            create_button(text='📊 Analytics', callback_data=
            f'client_analytics:{client_id}', button_type=ButtonType.INFO),
            UnifiedButtonBuilder.create_button(text='🗑️ Delete',
            callback_data=f'client_delete:{client_id}', button_type=ButtonType.DANGER)])
        return InlineKeyboardMarkup([buttons])

    @staticmethod
    def build_habit_keyboard(habit_id: int, habit_name: str,
        completed_today: bool=False) ->InlineKeyboardMarkup:
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
        if not completed_today:
            buttons.append(UnifiedButtonBuilder.create_button(text=
                '✅ Complete', callback_data=f'habit_done:{habit_id}',
                button_type=ButtonType.PRIMARY))
        buttons.extend([UnifiedButtonBuilder.create_button(text=
            '📊 Progress', callback_data=f'habit_progress:{habit_id}',
            button_type=ButtonType.INFO), UnifiedButtonBuilder.
            create_button(text='🗑️ Delete', callback_data=
            f'habit_delete:{habit_id}', button_type=ButtonType.INFO)])
        return InlineKeyboardMarkup([buttons])

    @staticmethod
    def build_navigation_keyboard(show_back: bool=True, show_main_menu:
        bool=True, custom_buttons: Optional[List[Dict[str, str]]]=None
        ) ->InlineKeyboardMarkup:
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
                buttons.append([UnifiedButtonBuilder.create_button(text=
                    button['text'], callback_data=button['callback_data'],
                    button_type=ButtonType.INFO)])
        nav_buttons = []
        if show_back:
            nav_buttons.append(UnifiedButtonBuilder.create_button(text=
                '⬅️ Back', callback_data='nav_back', button_type=ButtonType.INFO))
        if show_main_menu:
            nav_buttons.append(UnifiedButtonBuilder.create_button(text=
                '🏠 Main Menu', callback_data='nav_main', button_type=ButtonType.INFO))
        if nav_buttons:
            buttons.append(nav_buttons)
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_pagination_keyboard(current_page: int, total_pages: int,
        base_callback: str, show_nav: bool=True) ->InlineKeyboardMarkup:
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
        pagination_buttons = []
        if current_page > 1:
            pagination_buttons.append(UnifiedButtonBuilder.create_button(
                text='⬅️', callback_data=
                f'{base_callback}:page:{current_page - 1}', button_type=
                ButtonType.INFO))
        pagination_buttons.append(UnifiedButtonBuilder.create_button(text=
            f'{current_page}/{total_pages}', callback_data='no_action',
            button_type=ButtonType.INFO))
        if current_page < total_pages:
            pagination_buttons.append(UnifiedButtonBuilder.create_button(
                text='➡️', callback_data=
                f'{base_callback}:page:{current_page + 1}', button_type=
                ButtonType.INFO))
        if pagination_buttons:
            buttons.append(pagination_buttons)
        if show_nav:
            nav_buttons = [UnifiedButtonBuilder.create_button(text=
                '⬅️ Back', callback_data='nav_back', button_type=ButtonType.INFO), UnifiedButtonBuilder.create_button(text=
                '🏠 Main Menu', callback_data='nav_main', button_type=ButtonType.INFO)]
            buttons.append(nav_buttons)
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_confirmation_keyboard(action: str, item_id: int, item_name:
        str='') ->InlineKeyboardMarkup:
        """
        Build confirmation keyboard for destructive actions.
        
        Args:
            action: Action type (delete, bulk_delete, etc.)
            item_id: Item ID
            item_name: Item name for display
            
        Returns:
            InlineKeyboardMarkup with confirmation buttons
        """
        buttons = [[UnifiedButtonBuilder.create_button(text='✅ Confirm',
            callback_data=f'confirm_{action}:{item_id}', button_type=ButtonType.PRIMARY), UnifiedButtonBuilder.create_button(text=
            '❌ Cancel', callback_data='cancel_action', button_type=ButtonType.DANGER)], [UnifiedButtonBuilder.create_button(text=
            '⬅️ Back', callback_data='nav_back', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_client_list_keyboard() ->InlineKeyboardMarkup:
        """
        Build keyboard for client list actions.
        
        Returns:
            InlineKeyboardMarkup for client list actions
        """
        keyboard = [[UnifiedButtonBuilder.create_button(text='➕ Add Client',
            callback_data='client_add', button_type=ButtonType.PRIMARY),
            UnifiedButtonBuilder.create_button(text='📊 Analytics',
            callback_data='client_analytics', button_type=ButtonType.SECONDARY)],
            [UnifiedButtonBuilder.create_button(text='🔄 Refresh',
            callback_data='client_refresh', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='⬅️ Back',
            callback_data='nav_main', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_client_detail_keyboard(client_id: int, client_name: str
        ) ->InlineKeyboardMarkup:
        """
        Build keyboard for client detail actions.
        
        Args:
            client_id: ID of the client
            client_name: Name of the client
            
        Returns:
            InlineKeyboardMarkup for client detail actions
        """
        keyboard = [[UnifiedButtonBuilder.create_button(text='📋 View Tasks',
            callback_data=f'client_tasks:{client_id}', button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.create_button(text=
            '📊 Analytics', callback_data=f'client_analytics:{client_id}',
            button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.
            create_button(text='✏️ Edit', callback_data=
            f'client_edit:{client_id}', button_type=ButtonType.INFO),
            UnifiedButtonBuilder.create_button(text='🗑️ Delete',
            callback_data=f'client_delete:{client_id}', button_type=ButtonType.DANGER)], [UnifiedButtonBuilder.create_button(text=
            '⬅️ Back to Clients', callback_data='client_list', button_type=ButtonType.INFO), UnifiedButtonBuilder.create_button(text=
            '🏠 Main Menu', callback_data='nav_main', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_habit_list_keyboard() ->InlineKeyboardMarkup:
        """
        Build keyboard for habit list actions.
        
        Returns:
            InlineKeyboardMarkup for habit list actions
        """
        keyboard = [[UnifiedButtonBuilder.create_button(text='➕ Add Habit',
            callback_data='habit_add', button_type=ButtonType.PRIMARY),
            UnifiedButtonBuilder.create_button(text='📊 Statistics',
            callback_data='habit_stats', button_type=ButtonType.SECONDARY)], [
            UnifiedButtonBuilder.create_button(text='🔄 Refresh',
            callback_data='habit_refresh', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='⬅️ Back',
            callback_data='nav_main', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_habit_detail_keyboard(habit_id: int, habit_name: str
        ) ->InlineKeyboardMarkup:
        """
        Build keyboard for habit detail actions.
        
        Args:
            habit_id: ID of the habit
            habit_name: Name of the habit
            
        Returns:
            InlineKeyboardMarkup for habit detail actions
        """
        keyboard = [[UnifiedButtonBuilder.create_button(text='✅ Mark Done',
            callback_data=f'habit_done:{habit_id}', button_type=ButtonType.PRIMARY), UnifiedButtonBuilder.create_button(text='📊 Progress',
            callback_data=f'habit_progress:{habit_id}', button_type=
            ButtonType.INFO)], [UnifiedButtonBuilder.create_button(text=
            '✏️ Edit', callback_data=f'habit_edit:{habit_id}', button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.create_button(text=
            '🗑️ Delete', callback_data=f'habit_delete:{habit_id}',
            button_type=ButtonType.DANGER)], [UnifiedButtonBuilder.
            create_button(text='⬅️ Back to Habits', callback_data=
            'habit_list', button_type=ButtonType.INFO),
            UnifiedButtonBuilder.create_button(text='🏠 Main Menu',
            callback_data='nav_main', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_reminder_list_keyboard() ->InlineKeyboardMarkup:
        """
        Build keyboard for reminder list actions.
        
        Returns:
            InlineKeyboardMarkup for reminder list actions
        """
        keyboard = [[UnifiedButtonBuilder.create_button(text=
            '➕ Add Reminder', callback_data='reminder_add', button_type=ButtonType.PRIMARY), UnifiedButtonBuilder.create_button(text=
            '📊 Statistics', callback_data='reminder_stats', button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.create_button(text=
            '🔄 Refresh', callback_data='reminder_refresh', button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.create_button(text=
            '⬅️ Back', callback_data='nav_main', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_reminder_action_keyboard(task_id: int, reminder_id: int
        ) ->InlineKeyboardMarkup:
        """
        Build keyboard for reminder action responses.
        
        Args:
            task_id: ID of the task
            reminder_id: ID of the reminder
            
        Returns:
            InlineKeyboardMarkup for reminder actions
        """
        keyboard = [[UnifiedButtonBuilder.create_button(text='✅ Mark Done',
            callback_data=f'task_done:{task_id}', button_type=ButtonType.PRIMARY), UnifiedButtonBuilder.create_button(text='⏰ Snooze 1h',
            callback_data=f'reminder_snooze:{reminder_id}:1h', button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.create_button(text=
            '⏰ Snooze 1d', callback_data=
            f'reminder_snooze:{reminder_id}:1d', button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.create_button(text=
            '🗑️ Delete Reminder', callback_data=
            f'reminder_delete:{reminder_id}', button_type=ButtonType.DANGER)],
            [UnifiedButtonBuilder.create_button(text='📋 View Task',
            callback_data=f'task_view:{task_id}', button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.create_button(text='❌ Dismiss',
            callback_data='reminder_dismiss', button_type=ButtonType.DANGER)]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_reminder_keyboard(reminder_id: int, is_active: bool=True
        ) ->InlineKeyboardMarkup:
        """Build keyboard for reminder actions."""
        buttons = []
        if is_active:
            buttons.append([UnifiedButtonBuilder.create_button(text=
                '✅ Complete', callback_data=
                f'reminder_complete:{reminder_id}', button_type=ButtonType.PRIMARY), UnifiedButtonBuilder.create_button(text='⏰ Snooze',
                callback_data=f'reminder_snooze:{reminder_id}', button_type=ButtonType.SECONDARY)])
            buttons.append([UnifiedButtonBuilder.create_button(text=
                '📝 Edit', callback_data=f'reminder_edit:{reminder_id}',
                button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.
                create_button(text='🗑️ Delete', callback_data=
                f'reminder_delete:{reminder_id}', button_type=ButtonType.DANGER)])
        else:
            buttons.append([UnifiedButtonBuilder.create_button(text=
                '🔄 Reactivate', callback_data=
                f'reminder_reactivate:{reminder_id}', button_type=
                ButtonType.INFO), UnifiedButtonBuilder.create_button(text=
                '🗑️ Delete', callback_data=f'reminder_delete:{reminder_id}',
                button_type=ButtonType.DANGER)])
        buttons.append([UnifiedButtonBuilder.create_button(text=
            '📊 Statistics', callback_data=f'reminder_stats:{reminder_id}',
            button_type=ButtonType.SECONDARY)])
        buttons.append([UnifiedButtonBuilder.create_button(text=
            '🔙 Back to Reminders', callback_data='reminders_list',
            button_type=ButtonType.INFO)])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_analytics_keyboard() ->InlineKeyboardMarkup:
        """Build keyboard for analytics navigation."""
        buttons = [[UnifiedButtonBuilder.create_button(text='📈 Detailed',
            callback_data='analytics_detailed', button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.create_button(text='📊 Productivity',
            callback_data='analytics_productivity', button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.create_button(text=
            '⏰ Time Tracking', callback_data='analytics_time', button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.create_button(text=
            '🎯 Performance', callback_data='analytics_performance',
            button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.
            create_button(text='📅 Trends', callback_data='analytics_trends',
            button_type=ButtonType.INFO), UnifiedButtonBuilder.
            create_button(text='📋 Reports', callback_data=
            'analytics_reports', button_type=ButtonType.SECONDARY)], [
            UnifiedButtonBuilder.create_button(text='🔙 Back to Main',
            callback_data='main_menu', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_filter_keyboard() ->InlineKeyboardMarkup:
        """Build keyboard for advanced filtering options."""
        buttons = [[UnifiedButtonBuilder.create_button(text='📅 Date Range',
            callback_data='filter_date_range', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='🎯 Priority',
            callback_data='filter_priority', button_type=ButtonType.SECONDARY)],
            [UnifiedButtonBuilder.create_button(text='📋 Status',
            callback_data='filter_status', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='🏷️ Tags',
            callback_data='filter_tags', button_type=ButtonType.SECONDARY)], [
            UnifiedButtonBuilder.create_button(text='📂 Category',
            callback_data='filter_category', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='⏰ Time Tracking',
            callback_data='filter_time', button_type=ButtonType.SECONDARY)], [
            UnifiedButtonBuilder.create_button(text='🔍 Advanced Search',
            callback_data='filter_advanced_search', button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.create_button(text='💾 Save Filter',
            callback_data='filter_save', button_type=ButtonType.SECONDARY)], [
            UnifiedButtonBuilder.create_button(text='🔙 Back to Tasks',
            callback_data='tasks_list', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_attachment_keyboard(attachment_id: int, task_id: int
        ) ->InlineKeyboardMarkup:
        """Build keyboard for individual attachment actions."""
        buttons = [[UnifiedButtonBuilder.create_button(text=
            '📝 Edit Description', callback_data=
            f'attachment_edit_desc:{attachment_id}', button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.create_button(text=
            '📊 View Details', callback_data=
            f'attachment_details:{attachment_id}', button_type=ButtonType.
            INFO)], [UnifiedButtonBuilder.create_button(text='🗑️ Remove',
            callback_data=f'attachment_remove:{attachment_id}', button_type=ButtonType.DANGER), UnifiedButtonBuilder.create_button(text=
            '📋 Task Details', callback_data=f'task_details:{task_id}',
            button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.
            create_button(text='🔙 Back to Attachments', callback_data=
            f'attachments_list:{task_id}', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_attachments_list_keyboard(task_id: int, attachment_count: int
        ) ->InlineKeyboardMarkup:
        """Build keyboard for attachments list management."""
        buttons = []
        if attachment_count > 0:
            buttons.append([UnifiedButtonBuilder.create_button(text=
                '📊 Statistics', callback_data=f'attachment_stats:{task_id}',
                button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.
                create_button(text='📝 Add Description', callback_data=
                f'attachment_add_desc:{task_id}', button_type=ButtonType.SECONDARY)]
                )
            buttons.append([UnifiedButtonBuilder.create_button(text=
                '🗑️ Bulk Remove', callback_data=
                f'attachment_bulk_remove:{task_id}', button_type=ButtonType.DANGER), UnifiedButtonBuilder.create_button(text=
                '📋 Export List', callback_data=
                f'attachment_export:{task_id}', button_type=ButtonType.SECONDARY)])
        buttons.append([UnifiedButtonBuilder.create_button(text=
            '📎 Add New File', callback_data=f'attachment_add:{task_id}',
            button_type=ButtonType.SECONDARY)])
        buttons.append([UnifiedButtonBuilder.create_button(text=
            '🔙 Back to Task', callback_data=f'task_details:{task_id}',
            button_type=ButtonType.INFO)])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_calendar_keyboard() ->InlineKeyboardMarkup:
        """Build keyboard for calendar navigation."""
        buttons = [[UnifiedButtonBuilder.create_button(text='📅 Today',
            callback_data='calendar_today', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='📅 Week', callback_data
            ='calendar_week', button_type=ButtonType.SECONDARY)], [
            UnifiedButtonBuilder.create_button(text='📅 Month',
            callback_data='calendar_month', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='📅 Upcoming',
            callback_data='calendar_upcoming', button_type=ButtonType.SECONDARY)
            ], [UnifiedButtonBuilder.create_button(text='🔄 Sync',
            callback_data='calendar_sync', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='⚙️ Settings',
            callback_data='calendar_settings', button_type=ButtonType.SECONDARY)
            ], [UnifiedButtonBuilder.create_button(text='🔙 Back to Main',
            callback_data='main_menu', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_bulk_operations_keyboard() ->InlineKeyboardMarkup:
        """Build keyboard for bulk operations menu."""
        buttons = [[UnifiedButtonBuilder.create_button(text='📋 Status',
            callback_data='bulk_status_menu', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='🎯 Priority',
            callback_data='bulk_priority_menu', button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.create_button(text='👥 Assign',
            callback_data='bulk_assign_menu', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='🗑️ Delete',
            callback_data='bulk_delete_menu', button_type=ButtonType.DANGER)],
            [UnifiedButtonBuilder.create_button(text='📊 Preview',
            callback_data='bulk_preview', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='💾 Save Selection',
            callback_data='bulk_save_selection', button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.create_button(text=
            '🔙 Back to Tasks', callback_data='tasks_list', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_timezone_keyboard() ->InlineKeyboardMarkup:
        """Build timezone selection keyboard."""
        buttons = [[UnifiedButtonBuilder.create_button(text='🕐 UTC',
            callback_data='timezone_utc', button_type=ButtonType.INFO)], [
            UnifiedButtonBuilder.create_button(text='🕐 Local',
            callback_data='timezone_local', button_type=ButtonType.INFO)],
            [UnifiedButtonBuilder.create_button(text='🏠 Main Menu',
            callback_data='nav_main', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_progressive_task_keyboard(task_id: int, task_data: dict=None,
        disclosure_level: int=1) ->InlineKeyboardMarkup:
        """Legacy shim for build_progressive_task_keyboard with default task_data."""
        from larrybot.utils.enhanced_ux_helpers import ProgressiveDisclosureBuilder
        if task_data is None:
            task_data = {}
        return ProgressiveDisclosureBuilder.build_progressive_task_keyboard(
            task_id=task_id, task_data=task_data, disclosure_level=
            disclosure_level)

    @staticmethod
    def create_button(text: str, callback_data: str, button_type=None
        ) ->InlineKeyboardButton:
        """Legacy shim for create_button - delegates to UnifiedButtonBuilder."""
        from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
        if button_type == 'TASK_ACTION':
            button_type = ButtonType.PRIMARY
        elif button_type == 'NAVIGATION':
            button_type = ButtonType.SECONDARY
        elif button_type == 'CONFIRMATION':
            button_type = ButtonType.DANGER
        else:
            button_type = ButtonType.PRIMARY
        return UnifiedButtonBuilder.create_button(text, callback_data,
            button_type)

    @staticmethod
    def build_entity_keyboard(entities, action, available_actions=None
        ) ->InlineKeyboardMarkup:
        """Legacy shim for build_entity_keyboard with sensible defaults."""
        from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ActionType
        if isinstance(entities, list):
            entity_type = entities[0] if entities else 'item'
            entity_id = 1
        else:
            entity_type = 'item'
            entity_id = 1
        if action == 'entity_action':
            available_actions = [ActionType.VIEW, ActionType.EDIT,
                ActionType.DELETE]
        else:
            available_actions = available_actions or [ActionType.VIEW]
        return UnifiedButtonBuilder.build_entity_keyboard(entity_id=
            entity_id, entity_type=entity_type, available_actions=
            available_actions)


class MessageFormatter:
    """Format messages following Telegram best practices."""

    @staticmethod
    def escape_markdown(text: str) ->str:
        """Escape *any* text so it is safe in Markdown-V2 context.

        This now delegates to `telegram.helpers.escape_markdown`, which is kept
        up-to-date with Telegram's rules.  Using the official helper eliminates
        the risk of missing edge-cases (e.g. nested lists, reserved symbols
        introduced in future API versions).
        """
        if text is None:
            return None
        return _tg_escape_md(str(text), version=2)

    @staticmethod
    def obfuscate_url(url: str) ->str:
        """
        Obfuscate URL to prevent Telegram link embedding.
        
        Inserts zero-width Unicode characters between URL characters to break
        Telegram's automatic URL detection while keeping the URL visually identical
        and copyable.
        
        Args:
            url: URL to obfuscate
            
        Returns:
            Obfuscated URL string
        """
        if not url:
            return url
        return '\u200b'.join(url)

    @staticmethod
    def format_task_list(tasks: list, title: str='Tasks') ->str:
        """
        Format a list of tasks with rich formatting.
        
        Args:
            tasks: List of task objects or dictionaries
            title: Title for the task list
            
        Returns:
            Formatted task list string
        """
        if not tasks:
            return f'📋 **{title}**\n\nNo tasks found.'
        message = f'📋 **{title}** \\({len(tasks)} found\\)\n\n'
        for i, task in enumerate(tasks, 1):
            if hasattr(task, 'priority'):
                task_id = task.id
                description = task.description
                priority = getattr(task, 'priority', 'Medium')
                status = getattr(task, 'status', 'Todo')
                category = getattr(task, 'category', None)
                due_date = getattr(task, 'due_date', None)
                tags = getattr(task, 'tags', None)
            else:
                task_id = task.get('id')
                description = task.get('description', '')
                priority = task.get('priority', 'Medium')
                status = task.get('status', 'Todo')
                category = task.get('category')
                due_date = task.get('due_date')
                tags = task.get('tags')
            priority_emoji = {'Low': '🟢', 'Medium': '🟡', 'High': '🟠',
                'Critical': '🔴'}.get(priority, '⚪')
            status_emoji = {'Todo': '📝', 'In Progress': '🔄', 'Review': '👀',
                'Done': '✅'}.get(status, '📝')
            message += f"""• {priority_emoji} **{MessageFormatter.escape_markdown(description)}** \\(ID: {task_id}\\)
"""
            message += f'   {status_emoji} {status} \\| {priority}\n'
            if category:
                message += (
                    f'   📂 {MessageFormatter.escape_markdown(category)}\n')
            if due_date:
                if isinstance(due_date, str):
                    message += f'   📅 Due: {due_date}\n'
                else:
                    message += f"   📅 Due: {due_date.strftime('%Y-%m-%d')}\n"
            if tags:
                if isinstance(tags, str):
                    import json
                    try:
                        tags_list = json.loads(tags)
                    except (json.JSONDecodeError, TypeError):
                        tags_list = [tag.strip() for tag in tags.split(',') if
                            tag.strip()]
                elif isinstance(tags, list):
                    tags_list = tags
                else:
                    tags_list = []
                if tags_list:
                    message += f"""   🏷️ {', '.join([MessageFormatter.escape_markdown(str(tag)) for tag in tags_list])}
"""
            message += '\n'
        return message

    @staticmethod
    def format_client_list(clients: List[Dict]) ->str:
        """
        Format client list with proper MarkdownV2 escaping.
        
        Args:
            clients: List of client dictionaries
            
        Returns:
            Formatted client list message
        """
        if not clients:
            return '👥 **Clients**\n\nNo clients found.'
        message = f'👥 **Clients** \\({len(clients)} found\\)\n\n'
        for client in clients:
            name = MessageFormatter.escape_markdown(client.get('name',
                'Unknown'))
            client_id = client.get('id', 'N/A')
            task_count = client.get('task_count', 0)
            message += f'🏢 **{name}** \\(ID: {client_id}\\)\n'
            message += f'   📋 Tasks: {task_count}\n\n'
        return message.strip()

    @staticmethod
    def format_habit_list(habits: List[Dict]) ->str:
        """
        Format habit list with progress visualization.
        
        Args:
            habits: List of habit dictionaries
            
        Returns:
            Formatted habit list message
        """
        if not habits:
            return '🔄 **Habits**\n\nNo habits found.'
        message = f'🔄 **Habits** \\({len(habits)} found\\)\n\n'
        for habit in habits:
            name = MessageFormatter.escape_markdown(habit.get('name',
                'Unknown'))
            habit_id = habit.get('id', 'N/A')
            streak = habit.get('streak', 0)
            last_completed = habit.get('last_completed', None)
            if streak >= 7:
                streak_emoji = '🔥'
            elif streak >= 3:
                streak_emoji = '⚡'
            else:
                streak_emoji = '📈'
            message += f'{streak_emoji} **{name}** \\(ID: {habit_id}\\)\n'
            message += f'   🔥 Streak: {streak} days\n'
            if last_completed:
                if isinstance(last_completed, str):
                    message += (
                        f'   📅 Last: {MessageFormatter.escape_markdown(last_completed)}\n'
                        )
            message += '\n'
        return message.strip()

    @staticmethod
    def format_error_message(error: str, suggestion: str='') ->str:
        """
        Format error message with helpful suggestions.
        
        Args:
            error: Error message
            suggestion: Helpful suggestion for user
            
        Returns:
            Formatted error message
        """
        message = '❌ **Error**\n'
        safe_error = MessageFormatter.escape_markdown(str(error))
        message += f'_{safe_error}_\n'
        if suggestion:
            safe_suggestion = MessageFormatter.escape_markdown(str(suggestion))
            message += f'💡 **Suggestion:** {safe_suggestion}\n'
        return message

    @staticmethod
    def format_standardized_error(error_response: Dict[str, Any]) ->str:
        """
        Format standardized error response from our error handling system.
        
        Args:
            error_response: Standardized error response dictionary
            
        Returns:
            Formatted error message with MarkdownV2 escaping
        """
        error_code = error_response.get('error_code', 'E001')
        message = error_response.get('message', 'An error occurred')
        suggested_action = error_response.get('suggested_action', '')
        emoji = '❌'
        if error_code.startswith('V'):
            emoji = '⚠️'
        elif error_code.startswith('N'):
            emoji = '🌐'
        elif error_code.startswith('D'):
            emoji = '💾'
        formatted = (
            f'{emoji} **Error**\n\n{MessageFormatter.escape_markdown(message)}'
            )
        formatted += (
            f'\n\n🔍 _Code: {MessageFormatter.escape_markdown(error_code)}_')
        if suggested_action:
            formatted += f"""

💡 **Next Steps:**
{MessageFormatter.escape_markdown(suggested_action)}"""
        return formatted

    @staticmethod
    def format_success_message(message: str, details: Optional[Dict]=None
        ) ->str:
        """
        Format success message with optional details.
        
        Args:
            message: Success message
            details: Optional details to include
            
        Returns:
            Formatted success message
        """
        safe_msg = MessageFormatter.escape_markdown(str(message))
        formatted_message = f'✅ **Success**\n\n{safe_msg}'
        if details:
            formatted_message += '\n\n📋 **Details:**\n'
            for key, value in details.items():
                safe_key = MessageFormatter.escape_markdown(str(key))
                safe_val = MessageFormatter.escape_markdown(str(value))
                formatted_message += f'   • {safe_key}: {safe_val}\n'
        return formatted_message

    @staticmethod
    def format_analytics(analytics: Dict) ->str:
        """
        Format analytics data with visual indicators.
        
        Args:
            analytics: Analytics data dictionary
            
        Returns:
            Formatted analytics message
        """
        message = '📊 **Analytics**\n\n'
        total_tasks = analytics.get('total_tasks', 0)
        completed_tasks = analytics.get('completed_tasks', 0)
        incomplete_tasks = analytics.get('incomplete_tasks', 0)
        overdue_tasks = analytics.get('overdue_tasks', 0)
        completion_rate = analytics.get('completion_rate', 0)
        message += f'📈 Total Tasks: {total_tasks}\n'
        message += f'✅ Completed: {completed_tasks}\n'
        message += f'⏳ Incomplete: {incomplete_tasks}\n'
        message += f'⚠️ Overdue: {overdue_tasks}\n'
        message += f'📊 Completion Rate: {completion_rate:.1f}%\n\n'
        priority_dist = analytics.get('priority_distribution', {})
        if priority_dist:
            message += '🎯 **Priority Distribution:**\n'
            for priority, count in priority_dist.items():
                priority_emoji = {'Low': '🟢', 'Medium': '🟡', 'High': '🟠',
                    'Critical': '🔴'}.get(priority, '⚪')
                message += f'   {priority_emoji} {priority}: {count}\n'
            message += '\n'
        status_dist = analytics.get('status_distribution', {})
        if status_dist:
            message += '📋 **Status Distribution:**\n'
            for status, count in status_dist.items():
                status_emoji = {'Todo': '⏳', 'In Progress': '🔄', 'Review':
                    '👀', 'Done': '✅'}.get(status, '❓')
                message += f'   {status_emoji} {status}: {count}\n'
        return message.strip()

    @staticmethod
    def format_warning_message(title: str, details: dict) ->str:
        """
        Format a warning message with rich formatting.
        
        Args:
            title: Warning title
            details: Dictionary of details to display
            
        Returns:
            Formatted warning message string
        """
        safe_title = MessageFormatter.escape_markdown(str(title))
        message = f'⚠️ **{safe_title}**\n\n'
        for key, value in details.items():
            safe_key = MessageFormatter.escape_markdown(str(key))
            safe_value = MessageFormatter.escape_markdown(str(value))
            message += f'• **{safe_key}**: {safe_value}\n'
        return message

    @staticmethod
    def format_info_message(title: str, details: dict) ->str:
        """
        Format an info message with rich formatting.
        
        Args:
            title: Info title
            details: Dictionary of details to display
            
        Returns:
            Formatted info message string
        """
        safe_title = MessageFormatter.escape_markdown(str(title))
        message = f'ℹ️ **{safe_title}**\n\n'
        for key, value in details.items():
            safe_key = MessageFormatter.escape_markdown(str(key))
            safe_value = MessageFormatter.escape_markdown(str(value))
            message += f'• **{safe_key}**: {safe_value}\n'
        return message


class NavigationHelper:
    """Helper for navigation and menu management."""

    @staticmethod
    def get_main_menu_keyboard() ->InlineKeyboardMarkup:
        """
        Get main menu keyboard.
        
        Returns:
            InlineKeyboardMarkup with main menu options
        """
        buttons = [[UnifiedButtonBuilder.create_button(text='📋 Tasks',
            callback_data='menu_tasks', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='👥 Clients',
            callback_data='menu_clients', button_type=ButtonType.SECONDARY)], [
            UnifiedButtonBuilder.create_button(text='🔄 Habits',
            callback_data='menu_habits', button_type=ButtonType.INFO),
            UnifiedButtonBuilder.create_button(text='⏰ Reminders',
            callback_data='menu_reminders', button_type=ButtonType.SECONDARY)],
            [UnifiedButtonBuilder.create_button(text='📊 Analytics',
            callback_data='menu_analytics', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='📎 Files',
            callback_data='menu_files', button_type=ButtonType.SECONDARY)], [
            UnifiedButtonBuilder.create_button(text='📅 Calendar',
            callback_data='menu_calendar', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='⚙️ Settings',
            callback_data='menu_settings', button_type=ButtonType.SECONDARY)]]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_task_menu_keyboard() ->InlineKeyboardMarkup:
        """
        Get task management menu keyboard.
        
        Returns:
            InlineKeyboardMarkup with task menu options
        """
        buttons = [[UnifiedButtonBuilder.create_button(text='📋 View Tasks',
            callback_data='tasks_list', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='➕ Add Task',
            callback_data='task_add', button_type=ButtonType.PRIMARY)], [
            UnifiedButtonBuilder.create_button(text='🔍 Search',
            callback_data='tasks_search', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='📊 Analytics',
            callback_data='tasks_analytics', button_type=ButtonType.SECONDARY)],
            [UnifiedButtonBuilder.create_button(text='⚠️ Overdue',
            callback_data='tasks_overdue', button_type=ButtonType.SECONDARY),
            UnifiedButtonBuilder.create_button(text='📅 Today',
            callback_data='tasks_today', button_type=ButtonType.SECONDARY)], [
            UnifiedButtonBuilder.create_button(text='⬅️ Back',
            callback_data='nav_main', button_type=ButtonType.INFO)]]
        return InlineKeyboardMarkup(buttons)


class ChartBuilder:
    """Build visual charts and graphs using Unicode characters and ASCII art."""

    @staticmethod
    def build_bar_chart(data: dict, title: str='Chart', max_width: int=20
        ) ->str:
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
            return f'📊 **{title}**\n\nNo data available.'
        max_value = max(data.values()) if data.values() else 1
        chart = f'📊 **{title}**\n\n'
        for label, value in data.items():
            bar_length = int(value / max_value * max_width
                ) if max_value > 0 else 0
            bar = '█' * bar_length + '░' * (max_width - bar_length)
            safe_label = MessageFormatter.escape_markdown(str(label))
            percentage = value / max_value * 100 if max_value > 0 else 0
            chart += (
                f'`{bar}` {safe_label} \\({value}\\) \\- {percentage:.1f}%\n')
        return chart

    @staticmethod
    def build_pie_chart(data: dict, title: str='Distribution') ->str:
        """
        Build a pie chart representation using Unicode characters.
        
        Args:
            data: Dictionary with label: value pairs
            title: Chart title
            
        Returns:
            Formatted pie chart string
        """
        if not data:
            return f'🥧 **{title}**\n\nNo data available.'
        total = sum(data.values())
        if total == 0:
            return f'🥧 **{title}**\n\nNo data available.'
        pie_chars = ['🟥', '🟧', '🟨', '🟩', '🟦', '🟪', '🟫', '⬛']
        chart = f'🥧 **{title}**\n\n'
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
        for i, (label, value) in enumerate(sorted_data):
            percentage = value / total * 100
            color = pie_chars[i % len(pie_chars)]
            safe_label = MessageFormatter.escape_markdown(str(label))
            chart += f'{color} {safe_label}: {value} \\({percentage:.1f}%\\)\n'
        return chart

    @staticmethod
    def build_progress_bar(current: int, total: int, width: int=20, label:
        str='Progress') ->str:
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
            return f'📈 **{label}**: 0%'
        percentage = current / total * 100
        filled_width = int(current / total * width)
        bar = '█' * filled_width + '░' * (width - filled_width)
        return (
            f'📈 **{label}**: `{bar}` {percentage:.1f}% \\({current}/{total}\\)'
            )

    @staticmethod
    def build_timeline_chart(data: list, title: str='Timeline') ->str:
        """
        Build a timeline chart showing data over time.
        
        Args:
            data: List of tuples (date, value, label)
            title: Chart title
            
        Returns:
            Formatted timeline chart string
        """
        if not data:
            return f'📅 **{title}**\n\nNo data available.'
        chart = f'📅 **{title}**\n\n'
        sorted_data = sorted(data, key=lambda x: x[0])
        for date, value, label in sorted_data:
            if hasattr(date, 'strftime'):
                date_str = date.strftime('%Y-%m-%d')
            else:
                date_str = str(date)
            safe_label = MessageFormatter.escape_markdown(str(label))
            chart += f'📅 **{date_str}**: {safe_label} \\({value}\\)\n'
        return chart

    @staticmethod
    def build_heatmap(data: dict, title: str='Activity Heatmap') ->str:
        """
        Build a simple heatmap using Unicode characters.
        
        Args:
            data: Dictionary with key: value pairs
            title: Chart title
            
        Returns:
            Formatted heatmap string
        """
        if not data:
            return f'🔥 **{title}**\n\nNo data available.'
        max_value = max(data.values()) if data.values() else 1
        chart = f'🔥 **{title}**\n\n'
        for key, value in data.items():
            intensity = value / max_value if max_value > 0 else 0
            if intensity >= 0.8:
                heat_char = '🔴'
            elif intensity >= 0.6:
                heat_char = '🟠'
            elif intensity >= 0.4:
                heat_char = '🟡'
            elif intensity >= 0.2:
                heat_char = '🟢'
            else:
                heat_char = '⚪'
            safe_key = MessageFormatter.escape_markdown(str(key))
            chart += f'{heat_char} {safe_key}: {value}\n'
        return chart


class AnalyticsFormatter:
    """Format analytics data with rich visualizations."""

    @staticmethod
    def format_task_analytics(analytics: dict) ->str:
        """
        Format comprehensive task analytics with visualizations.
        
        Args:
            analytics: Analytics data dictionary
            
        Returns:
            Formatted analytics string
        """
        message = f'📊 **Task Analytics Dashboard**\n\n'
        total_tasks = analytics.get('total_tasks', 0)
        completed_tasks = analytics.get('completed_tasks', 0)
        incomplete_tasks = analytics.get('incomplete_tasks', 0)
        overdue_tasks = analytics.get('overdue_tasks', 0)
        completion_rate = analytics.get('completion_rate', 0)
        message += f'📈 **Overview**\n'
        message += f'• Total Tasks: {total_tasks}\n'
        message += f'• Completed: {completed_tasks} ✅\n'
        message += f'• Incomplete: {incomplete_tasks} ⏳\n'
        message += f'• Overdue: {overdue_tasks} ⚠️\n'
        message += f'• Completion Rate: {completion_rate:.1f}%\n\n'
        message += ChartBuilder.build_progress_bar(completed_tasks,
            total_tasks, 20, 'Completion Rate') + '\n\n'
        if analytics.get('priority_distribution'):
            message += ChartBuilder.build_bar_chart(analytics[
                'priority_distribution'], 'Priority Distribution') + '\n'
        if analytics.get('status_distribution'):
            message += ChartBuilder.build_pie_chart(analytics[
                'status_distribution'], 'Status Distribution') + '\n'
        if analytics.get('category_distribution'):
            message += ChartBuilder.build_bar_chart(analytics[
                'category_distribution'], 'Category Distribution') + '\n'
        message += f'💡 **Insights**\n'
        if completion_rate >= 80:
            message += (
                f'• 🎉 **Excellent completion rate!** Keep up the great work\\.\n'
                )
        elif completion_rate >= 60:
            message += f"• 📈 **Good progress!** You're on track\\.\n"
        elif completion_rate >= 40:
            message += (
                f'• ⚠️ **Moderate completion rate** \\. Consider reviewing priorities\\.\n'
                )
        else:
            message += (
                f'• 📉 **Low completion rate** \\. Focus on high\\-priority tasks\\.\n'
                )
        if overdue_tasks > 0:
            message += f"""• ⚠️ **{overdue_tasks} overdue tasks** \\. Consider rescheduling or reprioritizing\\.
"""
        if incomplete_tasks > completed_tasks:
            message += f"""• 📋 **More incomplete than complete tasks** \\. Consider breaking down large tasks\\.
"""
        return message

    @staticmethod
    def format_productivity_report(data: dict) ->str:
        """
        Format productivity report with visualizations.
        
        Args:
            data: Productivity data dictionary
            
        Returns:
            Formatted productivity report string
        """
        message = f'📈 **Productivity Report**\n\n'
        if 'time_tracking' in data:
            time_data = data['time_tracking']
            total_hours = time_data.get('total_hours', 0)
            avg_hours_per_day = time_data.get('avg_hours_per_day', 0)
            most_productive_day = time_data.get('most_productive_day', 'N/A')
            message += f'⏰ **Time Tracking**\n'
            message += f'• Total Hours: {total_hours:.1f}h\n'
            message += f'• Average per Day: {avg_hours_per_day:.1f}h\n'
            message += f'• Most Productive Day: {most_productive_day}\n\n'
        if 'completion_trends' in data:
            trends = data['completion_trends']
            message += f'📊 **Completion Trends**\n'
            for period, count in trends.items():
                message += f'• {period}: {count} tasks\n'
            message += '\n'
        if 'performance_metrics' in data:
            metrics = data['performance_metrics']
            efficiency = metrics.get('efficiency', 0)
            accuracy = metrics.get('accuracy', 0)
            message += f'🎯 **Performance Metrics**\n'
            message += ChartBuilder.build_progress_bar(efficiency, 100, 15,
                'Efficiency') + '\n'
            message += ChartBuilder.build_progress_bar(accuracy, 100, 15,
                'Accuracy') + '\n\n'
        return message


try:
    from larrybot.utils.enhanced_ux_helpers import ButtonType as _ButtonType, ActionType as _ActionType, UnifiedButtonBuilder as _UnifiedButtonBuilder
    ButtonType = _ButtonType
    ActionType = _ActionType


    class _LegacyKeyboardBridge:

        @staticmethod
        def build_progressive_task_keyboard(task_id: int, task_data: dict,
            disclosure_level: int=1):
            from larrybot.utils.enhanced_ux_helpers import ProgressiveDisclosureBuilder
            return (ProgressiveDisclosureBuilder.
                build_progressive_task_keyboard(task_id=task_id, task_data=
                task_data, disclosure_level=disclosure_level))

        @staticmethod
        def build_entity_keyboard(entity_id: int, entity_type: str,
            available_actions: list, entity_status: Optional[str]=None,
            custom_actions: Optional[list]=None):
            return _UnifiedButtonBuilder.build_entity_keyboard(entity_id=
                entity_id, entity_type=entity_type, available_actions=
                available_actions, entity_status=entity_status,
                custom_actions=custom_actions)
    setattr(KeyboardBuilder, 'build_progressive_task_keyboard',
        _LegacyKeyboardBridge.build_progressive_task_keyboard)
    setattr(KeyboardBuilder, 'build_entity_keyboard', _LegacyKeyboardBridge
        .build_entity_keyboard)
except ImportError:
    pass
