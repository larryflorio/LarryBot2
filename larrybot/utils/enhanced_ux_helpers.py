"""
Enhanced UX Helpers for LarryBot2

This module provides advanced UX utilities for creating better user experiences
including enhanced message layouts, smart navigation, error recovery, and visual feedback.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any, Optional, Union, Tuple
import json
import time
from datetime import datetime
# MessageFormatter is used but imported locally to avoid circular imports
from enum import Enum
import logging
logger = logging.getLogger(__name__)


def escape_markdown(text: str) -> str:
    """Escape markdown characters to prevent formatting issues."""
    if not text:
        return text
    # Escape special characters for MarkdownV2
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


class ButtonType(Enum):
    """Enumeration of button types for consistent styling."""
    PRIMARY = 'primary'
    SECONDARY = 'secondary'
    SUCCESS = 'success'
    DANGER = 'danger'
    WARNING = 'warning'
    INFO = 'info'
    TASK_ACTION = 'primary'
    NAVIGATION = 'secondary'
    CONFIRMATION = 'danger'


class ActionType(Enum):
    """Enumeration of action types for consistent callback data."""
    VIEW = 'view'
    EDIT = 'edit'
    DELETE = 'delete'
    COMPLETE = 'complete'
    START = 'start'
    STOP = 'stop'
    REFRESH = 'refresh'
    NAVIGATE = 'navigate'
    CONFIRM = 'confirm'
    CANCEL = 'cancel'


class MessageLayoutBuilder:
    """Enhanced message layout builder with improved visual hierarchy."""

    @staticmethod
    def build_section_header(title: str, icon: str='📋', subtitle: str=None
        ) ->str:
        """
        Create consistent section headers with visual separation.
        
        Args:
            title: Section title
            icon: Icon for the section
            subtitle: Optional subtitle
            
        Returns:
            Formatted section header
        """
        header = f'{icon} **{escape_markdown(title)}**'
        if subtitle:
            header += f'\n_{escape_markdown(subtitle)}_'
        header += '\n' + '─' * 30 + '\n'
        return header

    @staticmethod
    def build_info_card(title: str, content: dict, style: str='default') ->str:
        """
        Create structured information cards with consistent styling.
        
        Args:
            title: Card title
            content: Dictionary of key-value pairs
            style: Card style (default, success, warning, error)
            
        Returns:
            Formatted info card
        """
        style_configs = {'default': {'icon': '', 'separator': '│'},
            'success': {'icon': '✅', 'separator': '│'}, 'warning': {'icon':
            '⚠️', 'separator': '│'}, 'error': {'icon': '❌', 'separator': '│'}}
        config = style_configs.get(style, style_configs['default'])
        card = (
            f"{config['icon']} **{escape_markdown(title)}**\n"
            )
        card += '┌' + '─' * 28 + '┐\n'
        for key, value in content.items():
            safe_key = escape_markdown(str(key))
            safe_value = escape_markdown(str(value))
            card += f"{config['separator']} {safe_key}: {safe_value}\n"
        card += '└' + '─' * 28 + '┘\n'
        return card

    @staticmethod
    def build_progressive_list(items: list, max_visible: int=5, title: str=
        'Items') ->str:
        """
        Create expandable lists with "show more" functionality.
        
        Args:
            items: List of items to display
            max_visible: Maximum items to show initially
            title: List title
            
        Returns:
            Formatted progressive list
        """
        if not items:
            return f'📋 **{title}**\n\nNo items found.'
        total_items = len(items)
        visible_items = items[:max_visible]
        message = f'📋 **{title}** \\({total_items} total\\)\n\n'
        for i, item in enumerate(visible_items, 1):
            if hasattr(item, 'description'):
                description = item.description
            elif isinstance(item, dict):
                description = item.get('description', str(item))
            else:
                description = str(item)
            safe_desc = escape_markdown(description[:50])
            if len(description) > 50:
                safe_desc += '...'
            message += f'{i}\\. {safe_desc}\n'
        if total_items > max_visible:
            remaining = total_items - max_visible
            message += f'\n\\.\\.\\. and {remaining} more items'
        return message

    @staticmethod
    def build_status_indicator(status: str, priority: str=None, due_date:
        str=None) ->str:
        """
        Create visual status indicators with color coding.
        
        Args:
            status: Task status
            priority: Task priority
            due_date: Due date string
            
        Returns:
            Formatted status indicator
        """
        status_emojis = {'Todo': '⏳', 'In Progress': '🔄', 'Review': '👀',
            'Done': '✅', 'Overdue': '⚠️'}
        priority_emojis = {'Low': '🟢', 'Medium': '🟡', 'High': '🟠',
            'Critical': '🔴'}
        indicator = f"{status_emojis.get(status, '❓')} **{status}**"
        if priority:
            indicator += f" {priority_emojis.get(priority, '⚪')} {priority}"
        if due_date:
            indicator += f' 📅 {escape_markdown(due_date)}'
        return indicator

    @staticmethod
    def build_summary_card(title: str, metrics: dict, show_percentages:
        bool=True) ->str:
        """
        Create summary cards with key metrics.
        
        Args:
            title: Card title
            metrics: Dictionary of metric name and value
            show_percentages: Whether to show percentages for numeric values
            
        Returns:
            Formatted summary card
        """
        card = f'📊 **{escape_markdown(title)}**\n\n'
        for metric_name, value in metrics.items():
            safe_name = escape_markdown(str(metric_name))
            if isinstance(value, (int, float)) and show_percentages:
                card += f'• {safe_name}: {value}%\n'
            else:
                safe_value = escape_markdown(str(value))
                card += f'• {safe_name}: {safe_value}\n'
        return card.strip()


class SmartNavigationHelper:
    """Enhanced navigation helper with context awareness."""

    @staticmethod
    def build_contextual_keyboard(current_context: str, available_actions:
        list, user_history: list=None) ->InlineKeyboardMarkup:
        """
        Build navigation based on user context and available actions.
        
        Args:
            current_context: Current user context
            available_actions: List of available actions
            user_history: User's recent actions
            
        Returns:
            Contextual keyboard markup
        """
        buttons = []
        primary_actions = []
        secondary_actions = []
        navigation_actions = []
        for action in available_actions:
            if action.get('type') == 'primary':
                primary_actions.append(action)
            elif action.get('type') == 'navigation':
                navigation_actions.append(action)
            else:
                secondary_actions.append(action)
        if primary_actions:
            primary_row = []
            for action in primary_actions[:3]:
                primary_row.append(UnifiedButtonBuilder.create_button(text=
                    action['text'], callback_data=action['callback_data'],
                    button_type=ButtonType.INFO))
            buttons.append(primary_row)
        if secondary_actions:
            for action in secondary_actions:
                buttons.append([UnifiedButtonBuilder.create_button(text=
                    action['text'], callback_data=action['callback_data'],
                    button_type=ButtonType.INFO)])
        if navigation_actions:
            nav_row = []
            for action in navigation_actions[:2]:
                nav_row.append(UnifiedButtonBuilder.create_button(text=
                    action['text'], callback_data=action['callback_data'],
                    button_type=ButtonType.INFO))
            buttons.append(nav_row)
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def add_breadcrumb_navigation(message: str, navigation_path: list) ->str:
        """
        Add breadcrumb navigation to messages.
        
        Args:
            message: Original message
            navigation_path: List of navigation steps
            
        Returns:
            Message with breadcrumb navigation
        """
        if not navigation_path:
            return message
        breadcrumb = '📍 **Navigation:** '
        breadcrumb_parts = []
        for i, step in enumerate(navigation_path):
            if i == len(navigation_path) - 1:
                            breadcrumb_parts.append(
                f'**{escape_markdown(step)}**')
        else:
            breadcrumb_parts.append(escape_markdown(step))
        breadcrumb += ' > '.join(breadcrumb_parts)
        breadcrumb += '\n\n'
        return breadcrumb + message

    @staticmethod
    def suggest_next_actions(current_action: str, user_patterns: dict) ->list:
        """
        Suggest next actions based on user behavior patterns.
        
        Args:
            current_action: Current user action
            user_patterns: User's behavior patterns
            
        Returns:
            List of suggested next actions
        """
        action_patterns = {'task_list': ['add_task', 'filter_tasks',
            'analytics'], 'task_view': ['edit_task', 'complete_task',
            'delete_task'], 'client_list': ['add_client', 'view_client',
            'client_analytics'], 'habit_list': ['add_habit',
            'complete_habit', 'habit_stats'], 'analytics': ['export_report',
            'filter_analytics', 'compare_periods']}
        return action_patterns.get(current_action, [])

    @staticmethod
    def build_quick_actions_keyboard(entity_type: str, entity_id: int
        ) ->InlineKeyboardMarkup:
        """
        Build quick action keyboard for specific entity types.
        
        Args:
            entity_type: Type of entity (task, client, habit, etc.)
            entity_id: Entity ID
            
        Returns:
            Quick actions keyboard
        """
        quick_actions = {'task': [('✅ Done', f'task_done:{entity_id}'), (
            '✏️ Edit', f'task_edit:{entity_id}'), ('👁️ View',
            f'task_view:{entity_id}'), ('🗑️ Delete',
            f'task_delete:{entity_id}')], 'client': [('📋 Tasks',
            f'client_tasks:{entity_id}'), ('📊 Analytics',
            f'client_analytics:{entity_id}'), ('✏️ Edit',
            f'client_edit:{entity_id}'), ('🗑️ Delete',
            f'client_delete:{entity_id}')], 'habit': [('✅ Complete',
            f'habit_done:{entity_id}'), ('📊 Progress',
            f'habit_progress:{entity_id}'), ('🗑️ Delete',
            f'habit_delete:{entity_id}')]}
        actions = quick_actions.get(entity_type, [])
        buttons = []
        for i in range(0, len(actions), 2):
            row = []
            row.append(UnifiedButtonBuilder.create_button(text=actions[i][0
                ], callback_data=actions[i][1], button_type=ButtonType.INFO))
            if i + 1 < len(actions):
                row.append(UnifiedButtonBuilder.create_button(text=actions[
                    i + 1][0], callback_data=actions[i + 1][1], button_type
                    =ButtonType.INFO))
            buttons.append(row)
        return InlineKeyboardMarkup(buttons)


class ErrorRecoveryHelper:
    """Enhanced error handling with intelligent recovery options and contextual help."""

    @staticmethod
    def build_error_recovery_keyboard(error_type: str, context: dict
        ) ->InlineKeyboardMarkup:
        """
        Build intelligent recovery options based on error type and context.
        
        Args:
            error_type: Type of error that occurred
            context: Error context information
            
        Returns:
            Error recovery keyboard
        """
        recovery_actions = {'validation_error': [('🔄 Try Again',
            'retry_action'), ('📝 Edit Input', 'edit_input'), (
            '💡 Show Examples', 'show_examples'), ('❓ Help', 'show_help')],
            'not_found_error': [('🔍 Search Similar', 'search_similar'), (
            '📋 List All', 'list_all'), ('➕ Create New', 'create_new'), (
            '🔙 Go Back', 'go_back')], 'permission_error': [(
            '🔐 Check Permissions', 'check_permissions'), ('📞 Contact Admin',
            'contact_admin'), ('🔑 Re-authenticate', 'reauth')],
            'network_error': [('🔄 Retry Now', 'retry_network'), (
            '📡 Check Connection', 'check_connection'), ('⏰ Try Later',
            'try_later'), ('📊 Check Status', 'check_status')],
            'database_error': [('🔄 Retry', 'retry_db'), ('💾 Check Storage',
            'check_storage'), ('📊 System Status', 'system_status'), (
            '🆘 Emergency Mode', 'emergency_mode')], 'timeout_error': [(
            '⏱️ Quick Retry', 'quick_retry'), ('🔄 Full Retry', 'full_retry'
            ), ('📊 Check Performance', 'check_performance'), ('⚡ Optimize',
            'optimize')]}
        actions = recovery_actions.get(error_type, [('🔄 Retry',
            'retry_action'), ('🏠 Main Menu', 'nav_main'), ('❓ Help',
            'show_help')])
        context_actions = ErrorRecoveryHelper._get_context_specific_actions(
            context)
        actions.extend(context_actions)
        buttons = []
        for action_text, callback_data in actions:
            buttons.append([UnifiedButtonBuilder.create_button(text=
                action_text, callback_data=callback_data, button_type=
                ButtonType.INFO)])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def _get_context_specific_actions(context: dict) ->list:
        """Get context-specific recovery actions."""
        actions = []
        if context.get('action') == 'add_task':
            actions.append(('📝 Quick Add', 'quick_add_task'))
        elif context.get('action') == 'edit_task':
            actions.append(('📋 View Task', 'view_task'))
        elif context.get('action') == 'search':
            actions.append(('🔍 Advanced Search', 'advanced_search'))
        if context.get('user_level') == 'expert':
            actions.append(('🔧 Debug Mode', 'debug_mode'))
        elif context.get('user_level') == 'beginner':
            actions.append(('📚 Tutorial', 'show_tutorial'))
        return actions

    @staticmethod
    def suggest_alternatives(failed_command: str, user_context: dict) ->list:
        """
        Suggest alternative commands or approaches.
        
        Args:
            failed_command: Command that failed
            user_context: User context information
            
        Returns:
            List of alternative suggestions
        """
        command_alternatives = {'add_task': ['/add', '/task_add',
            '/new_task'], 'edit_task': ['/edit', '/modify_task',
            '/update_task'], 'delete_task': ['/remove', '/del_task',
            '/rm_task'], 'list_tasks': ['/tasks', '/list', '/show_tasks'],
            'add_client': ['/client_add', '/new_client', '/create_client'],
            'list_clients': ['/clients', '/allclients', '/show_clients']}
        return command_alternatives.get(failed_command, [])

    @staticmethod
    def provide_contextual_help(error_context: dict) ->str:
        """
        Provide intelligent contextual help based on error situation and user context.
        
        Args:
            error_context: Error context information
            
        Returns:
            Contextual help message with actionable suggestions
        """
        error_type = error_context.get('type', 'unknown')
        error_message = error_context.get('message', 'An error occurred')
        user_level = error_context.get('user_level', 'intermediate')
        action = error_context.get('action', '')
        help_messages = {'validation_error': ErrorRecoveryHelper.
            _get_validation_help(error_message, user_level, action),
            'not_found_error': ErrorRecoveryHelper._get_not_found_help(
            error_context), 'permission_error': ErrorRecoveryHelper.
            _get_permission_help(error_context), 'network_error':
            ErrorRecoveryHelper._get_network_help(error_context),
            'database_error': ErrorRecoveryHelper._get_database_help(
            error_context), 'timeout_error': ErrorRecoveryHelper.
            _get_timeout_help(error_context)}
        return help_messages.get(error_type,
            f'💡 **Help**: {escape_markdown(error_message)}')

    @staticmethod
    def _get_validation_help(error_message: str, user_level: str, action: str
        ) ->str:
        """Get validation error help with examples."""
        help_text = f"""💡 **Validation Error**

{escape_markdown(error_message)}

"""
        if action == 'add_task':
            help_text += (
                '**Example**: `/add Complete quarterly report by Friday`\n')
            help_text += (
                '**Example**: `/add Review code changes priority:High`\n')
        elif action == 'edit_task':
            help_text += (
                '**Example**: `/edit 123 New description priority:High`\n')
        elif action == 'search':
            help_text += '**Example**: `/search urgent tasks`\n'
            help_text += '**Example**: `/search priority:High status:Todo`\n'
        if user_level == 'beginner':
            help_text += (
                '\n💡 **Tip**: Start with simple commands and add complexity gradually\\.'
                )
        elif user_level == 'expert':
            help_text += (
                '\n💡 **Tip**: Use advanced filters and bulk operations for efficiency\\.'
                )
        return help_text

    @staticmethod
    def _get_not_found_help(error_context: dict) ->str:
        """Get not found error help with search suggestions."""
        entity_type = error_context.get('entity_type', 'item')
        search_term = error_context.get('search_term', '')
        help_text = f'💡 **{entity_type.title()} Not Found**\n\n'
        if search_term:
            help_text += f"""The search for "{escape_markdown(search_term)}" returned no results\\.

"""
        help_text += '**Try these alternatives:**\n'
        help_text += '• Use broader search terms\n'
        help_text += '• Check spelling and formatting\n'
        help_text += '• Use `/list` to see all available items\n'
        help_text += '• Create a new item if needed\n'
        return help_text

    @staticmethod
    def _get_permission_help(error_context: dict) ->str:
        """Get permission error help with resolution steps."""
        action = error_context.get('action', 'this action')
        help_text = f'💡 **Permission Denied**\n\n'
        help_text += f"You don't have permission to perform {action}\\.\n\n"
        help_text += '**Possible solutions:**\n'
        help_text += '• Contact your administrator\n'
        help_text += '• Check your user role and permissions\n'
        help_text += '• Try a different approach or action\n'
        return help_text

    @staticmethod
    def _get_network_help(error_context: dict) ->str:
        """Get network error help with troubleshooting steps."""
        help_text = '💡 **Network Connection Issue**\n\n'
        help_text += 'Unable to connect to the service\\.\n\n'
        help_text += '**Troubleshooting steps:**\n'
        help_text += '1\\. Check your internet connection\n'
        help_text += '2\\. Try again in a few moments\n'
        help_text += '3\\. Check if the service is available\n'
        help_text += '4\\. Contact support if the issue persists\n'
        return help_text

    @staticmethod
    def _get_database_help(error_context: dict) ->str:
        """Get database error help."""
        help_text = '💡 **Database Error**\n\n'
        help_text += 'A database operation failed\\.\n\n'
        help_text += '**What you can do:**\n'
        help_text += '• Try the operation again\n'
        help_text += '• Check if your data is still available\n'
        help_text += '• Contact support if the issue persists\n'
        return help_text

    @staticmethod
    def _get_timeout_help(error_context: dict) ->str:
        """Get timeout error help."""
        help_text = '💡 **Operation Timed Out**\n\n'
        help_text += 'The operation took too long to complete\\.\n\n'
        help_text += '**Solutions:**\n'
        help_text += '• Try again with a smaller dataset\n'
        help_text += '• Break the operation into smaller parts\n'
        return help_text

    @staticmethod
    def suggest_recovery_actions(error_type: str, context: dict) -> List[str]:
        """
        Suggest recovery actions based on error type and context.
        
        Args:
            error_type: Type of error that occurred
            context: Error context information
            
        Returns:
            List of suggested recovery actions
        """
        recovery_suggestions = {
            'validation_error': [
                'Check input format and try again',
                'Use the provided examples as a template',
                'Ensure all required fields are filled'
            ],
            'not_found_error': [
                'Verify the item ID or name is correct',
                'Use search to find similar items',
                'Create a new item if it doesn\'t exist'
            ],
            'permission_error': [
                'Contact your administrator for access',
                'Check your user role and permissions',
                'Try a different approach or action'
            ],
            'network_error': [
                'Check your internet connection',
                'Try again in a few moments',
                'Contact support if the issue persists'
            ],
            'database_error': [
                'Try the operation again',
                'Check if your data is still available',
                'Contact support if the issue persists'
            ],
            'timeout_error': [
                'Try again with a smaller dataset',
                'Break the operation into smaller parts',
                'Check system performance and try later'
            ],
            'system_error': [
                'Try the operation again',
                'Check system status',
                'Contact support if the issue persists'
            ]
        }
        
        suggestions = recovery_suggestions.get(error_type, [
            'Try the operation again',
            'Check your input and try again',
            'Contact support if the issue persists'
        ])
        
        # Add context-specific suggestions
        if context.get('action') == 'add_task':
            suggestions.append('Use /add command with a clear description')
        elif context.get('action') == 'edit_task':
            suggestions.append('Use /edit command with the correct task ID')
        elif context.get('user_level') == 'beginner':
            suggestions.append('Use /help for command examples')
        
        return suggestions
        help_text += '• Check your connection speed\n'
        help_text += '• Try again during off-peak hours\n'
        return help_text


class VisualFeedbackSystem:
    """Comprehensive visual feedback system."""

    @staticmethod
    def show_loading_state(operation: str, estimated_time: float=None) ->str:
        """
        Show loading state with progress indicators.
        
        Args:
            operation: Operation being performed
            estimated_time: Estimated time in seconds
            
        Returns:
            Loading state message
        """
        loading_message = (
            f'⏳ **{escape_markdown(operation)}**\n\n')
        loading_message += '🔄 Processing\\.\\.\\.'
        if estimated_time:
            loading_message += f'\n⏱️ Estimated time: {estimated_time:.1f}s'
        return loading_message

    @staticmethod
    def show_success_animation(action: str, details: dict) ->str:
        """
        Show success feedback with visual elements.
        
        Args:
            action: Action that was completed
            details: Success details
            
        Returns:
            Success message with visual elements
        """
        success_message = (
            f'✅ **{escape_markdown(action)}**\n\n')
        success_message += '🎉 Successfully completed!\n\n'
        if details:
            success_message += '📋 **Details:**\n'
            for key, value in details.items():
                safe_key = escape_markdown(str(key))
                safe_value = escape_markdown(str(value))
                success_message += f'   • {safe_key}: {safe_value}\n'
        return success_message

    @staticmethod
    def show_progress_bar(current: int, total: int, label: str, width: int=20
        ) ->str:
        """
        Show progress bars for long operations.
        
        Args:
            current: Current progress value
            total: Total value
            label: Progress label
            width: Progress bar width
            
        Returns:
            Progress bar message
        """
        if total == 0:
            return (
                f'📊 **{escape_markdown(label)}**\n\nNo progress data available.'
                )
        percentage = current / total * 100
        filled_width = int(current / total * width)
        progress_bar = '█' * filled_width + '░' * (width - filled_width)
        message = f'📊 **{escape_markdown(label)}**\n\n'
        message += f'`{progress_bar}` {percentage:.1f}%\n'
        message += f'Progress: {current}/{total}'
        return message

    @staticmethod
    def show_confirmation_dialog(action: str, details: dict, risk_level:
        str='low') ->Tuple[str, InlineKeyboardMarkup]:
        """
        Show enhanced confirmation dialogs.
        
        Args:
            action: Action to confirm
            details: Action details
            risk_level: Risk level (low, medium, high)
            
        Returns:
            Tuple of (message, keyboard)
        """
        risk_indicators = {'low': {'icon': '', 'color': 'blue'}, 'medium':
            {'icon': '⚠️', 'color': 'yellow'}, 'high': {'icon': '🚨',
            'color': 'red'}}
        indicator = risk_indicators.get(risk_level, risk_indicators['low'])
        message = (
            f"{indicator['icon']} **Confirm {escape_markdown(action)}**\n\n"
            )
        if details:
            message += '📋 **Details:**\n'
            for key, value in details.items():
                safe_key = escape_markdown(str(key))
                safe_value = escape_markdown(str(value))
                message += f'   • {safe_key}: {safe_value}\n'
            message += '\n'
        message += 'Are you sure you want to proceed?'
        keyboard = InlineKeyboardMarkup([[UnifiedButtonBuilder.
            create_button(text='✅ Confirm', callback_data=
            f'confirm_{action}', button_type=ButtonType.INFO),
            UnifiedButtonBuilder.create_button(text='❌ Cancel',
            callback_data='cancel_action', button_type=ButtonType.DANGER)]])
        return message, keyboard


class UnifiedButtonBuilder:
    """
    Unified button builder that consolidates repetitive keyboard building patterns.
    
    This class provides a consistent, maintainable approach to creating inline keyboards
    across the LarryBot2 codebase, reducing code duplication and improving UX consistency.
    """
    BUTTON_STYLES = {ButtonType.PRIMARY: {'emoji': '🔵', 'style': 'primary'},
        ButtonType.SECONDARY: {'emoji': '⚪', 'style': 'secondary'},
        ButtonType.SUCCESS: {'emoji': '✅', 'style': 'success'}, ButtonType.
        DANGER: {'emoji': '🗑️', 'style': 'danger'}, ButtonType.WARNING: {
        'emoji': '⚠️', 'style': 'warning'}, ButtonType.INFO: {'emoji': '📋',
        'style': 'info'}, 'TASK_ACTION': {'emoji': '🔵', 'style': 'primary'},
        'NAVIGATION': {'emoji': '⚪', 'style': 'secondary'}, 'CONFIRMATION':
        {'emoji': '🗑️', 'style': 'danger'}}
    ACTION_TEMPLATES = {ActionType.VIEW: {'emoji': '👁️', 'text': 'View',
        'style': ButtonType.INFO}, ActionType.EDIT: {'emoji': '✏️', 'text':
        'Edit', 'style': ButtonType.SECONDARY}, ActionType.DELETE: {'emoji':
        '🗑️', 'text': 'Delete', 'style': ButtonType.DANGER}, ActionType.
        COMPLETE: {'emoji': '✅', 'text': 'Done', 'style': ButtonType.
        SUCCESS}, ActionType.START: {'emoji': '▶️', 'text': 'Start',
        'style': ButtonType.SUCCESS}, ActionType.STOP: {'emoji': '⏹️',
        'text': 'Stop', 'style': ButtonType.WARNING}, ActionType.REFRESH: {
        'emoji': '🔄', 'text': 'Refresh', 'style': ButtonType.INFO},
        ActionType.NAVIGATE: {'emoji': '🏠', 'text': 'Main Menu', 'style':
        ButtonType.PRIMARY}, ActionType.CONFIRM: {'emoji': '✅', 'text':
        'Confirm', 'style': ButtonType.SUCCESS}, ActionType.CANCEL: {
        'emoji': '❌', 'text': 'Cancel', 'style': ButtonType.DANGER}}

    @staticmethod
    def create_button(text: str, callback_data: str, button_type:
        ButtonType=ButtonType.PRIMARY, custom_emoji: Optional[str]=None
        ) ->InlineKeyboardButton:
        """
        Create a single button with consistent styling.
        
        Args:
            text: Button text
            callback_data: Callback data for the button
            button_type: Type of button for styling
            custom_emoji: Custom emoji to override default
            
        Returns:
            InlineKeyboardButton with consistent styling
        """
        style = UnifiedButtonBuilder.BUTTON_STYLES[button_type]
        emoji = custom_emoji or style['emoji']
        if emoji and not any(text.startswith(e) for e in ['👁️', '✏️', '🗑️',
            '✅', '▶️', '⏹️', '🔄', '🏠', '⚠️', '❌', '📊', '⚙️', '🔍', '⏱️', '🔗',
            '➕', '📅']):
            display_text = f'{emoji} {text}'
        else:
            display_text = text
        return InlineKeyboardButton(text=display_text, callback_data=callback_data)

    @staticmethod
    def create_action_button(action_type: ActionType, entity_id: Union[int,
        str], entity_type: str='item', custom_text: Optional[str]=None
        ) ->InlineKeyboardButton:
        """
        Create an action button using predefined templates.
        
        Args:
            action_type: Type of action to perform
            entity_id: ID of the entity to act upon
            entity_type: Type of entity (e.g., 'task', 'client', 'habit')
            custom_text: Custom text to override template
            
        Returns:
            InlineKeyboardButton with action-specific styling
        """
        template = UnifiedButtonBuilder.ACTION_TEMPLATES[action_type]
        text = custom_text or template['text']
        style = template['style']
        emoji = template['emoji']
        if entity_type == 'task' and action_type == ActionType.COMPLETE:
            callback_data = f'task_complete:{entity_id}'
        else:
            callback_data = f'{entity_type}_{action_type.value}:{entity_id}'
        return UnifiedButtonBuilder.create_button(text=text, callback_data=
            callback_data, button_type=style, custom_emoji=emoji)

    @staticmethod
    def build_entity_keyboard(entity_id: int, entity_type: str,
        available_actions: List[ActionType], entity_status: Optional[str]=
        None, custom_actions: Optional[List[Dict[str, Any]]]=None
        ) ->InlineKeyboardMarkup:
        """
        Build a keyboard for entity actions with context-aware button visibility.
        
        Args:
            entity_id: ID of the entity
            entity_type: Type of entity (e.g., 'task', 'client', 'habit')
            available_actions: List of available actions for this entity
            entity_status: Current status of the entity (for conditional buttons)
            custom_actions: List of custom actions with 'text', 'callback_data', 'type'
            
        Returns:
            InlineKeyboardMarkup with context-aware buttons
        """
        buttons = []
        for action in available_actions:
            if action == ActionType.COMPLETE and entity_status == 'Done':
                continue
            elif action == ActionType.EDIT and entity_status == 'Done':
                continue
            button = UnifiedButtonBuilder.create_action_button(action_type=
                action, entity_id=entity_id, entity_type=entity_type)
            buttons.append(button)
        if custom_actions:
            for custom_action in custom_actions:
                button = UnifiedButtonBuilder.create_button(text=
                    custom_action['text'], callback_data=custom_action[
                    'callback_data'], button_type=custom_action.get('type',
                    ButtonType.SECONDARY), custom_emoji=custom_action.get(
                    'emoji'))
                buttons.append(button)
        return InlineKeyboardMarkup([buttons])

    @staticmethod
    def build_list_keyboard(items: List[Dict[str, Any]], item_type: str,
        max_items: int=5, show_navigation: bool=True, navigation_actions:
        Optional[List[ActionType]]=None) ->InlineKeyboardMarkup:
        """
        Build a keyboard for listing items with pagination and navigation.
        
        Args:
            items: List of items to display
            item_type: Type of items (e.g., 'task', 'client', 'habit')
            max_items: Maximum number of items to show
            show_navigation: Whether to show navigation buttons
            navigation_actions: List of navigation actions to include
            
        Returns:
            InlineKeyboardMarkup with item list and navigation
        """
        buttons = []
        for item in items[:max_items]:
            item_id = item.get('id', item.get('task_id'))
            item_name = item.get('name', item.get('description', 'Unknown'))
            display_name = item_name[:20] + '...' if len(item_name
                ) > 20 else item_name
            button = UnifiedButtonBuilder.create_action_button(action_type=
                ActionType.VIEW, entity_id=item_id, entity_type=item_type,
                custom_text=display_name)
            buttons.append([button])
        if show_navigation:
            nav_buttons = []
            if navigation_actions is None:
                navigation_actions = [ActionType.REFRESH, ActionType.NAVIGATE]
            for action in navigation_actions:
                if action == ActionType.NAVIGATE:
                    button = UnifiedButtonBuilder.create_button(text=
                        'Main Menu', callback_data='nav_main', button_type=
                        ButtonType.PRIMARY, custom_emoji='🏠')
                else:
                    button = UnifiedButtonBuilder.create_action_button(
                        action_type=action, entity_id='list', entity_type=
                        item_type)
                nav_buttons.append(button)
            buttons.append(nav_buttons)
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_task_keyboard(task_id: int, status: str='Todo', show_edit:
        bool=True, show_time_tracking: bool=False, is_time_tracking: bool=False
        ) ->InlineKeyboardMarkup:
        """
        Build a specialized keyboard for task actions.
        
        Args:
            task_id: Task ID
            status: Current task status
            show_edit: Whether to show edit button
            show_time_tracking: Whether to show time tracking buttons
            is_time_tracking: Whether time tracking is currently active
            
        Returns:
            InlineKeyboardMarkup with task-specific buttons
        """
        available_actions = [ActionType.VIEW, ActionType.DELETE]
        if status != 'Done':
            available_actions.append(ActionType.COMPLETE)
        if show_edit and status != 'Done':
            available_actions.append(ActionType.EDIT)
        custom_actions = []
        if show_time_tracking:
            if is_time_tracking:
                custom_actions.append({'text': '⏹️ Stop Timer',
                    'callback_data': f'task_time_stop:{task_id}', 'type':
                    ButtonType.WARNING, 'emoji': '⏹️'})
            else:
                custom_actions.append({'text': '▶️ Start Timer',
                    'callback_data': f'task_time_start:{task_id}', 'type':
                    ButtonType.SUCCESS, 'emoji': '▶️'})
        return UnifiedButtonBuilder.build_entity_keyboard(entity_id=task_id,
            entity_type='task', available_actions=available_actions,
            entity_status=status, custom_actions=custom_actions)

    @staticmethod
    def build_analytics_keyboard(complexity_levels: List[str]=None,
        show_custom: bool=True) ->InlineKeyboardMarkup:
        """
        Build a keyboard for analytics options.
        
        Args:
            complexity_levels: List of complexity levels to show
            show_custom: Whether to show custom analytics option
            
        Returns:
            InlineKeyboardMarkup with analytics options
        """
        if complexity_levels is None:
            complexity_levels = ['basic', 'detailed', 'advanced']
        buttons = []
        for level in complexity_levels:
            button = UnifiedButtonBuilder.create_button(text=level.title(),
                callback_data=f'analytics_{level}', button_type=ButtonType.
                INFO, custom_emoji='📊')
            buttons.append(button)
        if show_custom:
            custom_button = UnifiedButtonBuilder.create_button(text=
                'Custom Days', callback_data='analytics_custom',
                button_type=ButtonType.SECONDARY, custom_emoji='⚙️')
            buttons.append(custom_button)
        nav_button = UnifiedButtonBuilder.create_button(text='Main Menu',
            callback_data='nav_main', button_type=ButtonType.PRIMARY,
            custom_emoji='🏠')
        buttons.append(nav_button)
        keyboard_rows = []
        for i in range(0, len(buttons), 3):
            keyboard_rows.append(buttons[i:i + 3])
        return InlineKeyboardMarkup(keyboard_rows)

    @staticmethod
    def build_filter_keyboard(filter_types: List[str]=None, show_advanced:
        bool=True) ->InlineKeyboardMarkup:
        """
        Build a keyboard for filtering options.
        
        Args:
            filter_types: List of filter types to show
            show_advanced: Whether to show advanced filtering option
            
        Returns:
            InlineKeyboardMarkup with filter options
        """
        if filter_types is None:
            filter_types = ['status', 'priority', 'category', 'tags']
        buttons = []
        for filter_type in filter_types:
            button = UnifiedButtonBuilder.create_button(text=filter_type.
                title(), callback_data=f'filter_{filter_type}', button_type
                =ButtonType.SECONDARY, custom_emoji='🔍')
            buttons.append(button)
        if show_advanced:
            advanced_button = UnifiedButtonBuilder.create_button(text=
                'Advanced', callback_data='filter_advanced', button_type=
                ButtonType.INFO, custom_emoji='⚙️')
            buttons.append(advanced_button)
        clear_button = UnifiedButtonBuilder.create_button(text=
            'Clear Filters', callback_data='filter_clear', button_type=
            ButtonType.WARNING, custom_emoji='🗑️')
        buttons.append(clear_button)
        nav_button = UnifiedButtonBuilder.create_button(text='Main Menu',
            callback_data='nav_main', button_type=ButtonType.PRIMARY,
            custom_emoji='🏠')
        buttons.append(nav_button)
        keyboard_rows = []
        for i in range(0, len(buttons), 3):
            keyboard_rows.append(buttons[i:i + 3])
        return InlineKeyboardMarkup(keyboard_rows)

    @staticmethod
    def build_confirmation_keyboard(action: str, entity_id: int,
        entity_type: str='item', entity_name: str='') ->InlineKeyboardMarkup:
        """
        Build a confirmation keyboard for destructive actions.
        
        Args:
            action: Action to confirm (e.g., 'delete', 'remove')
            entity_id: ID of the entity
            entity_type: Type of entity
            entity_name: Name of the entity for display
            
        Returns:
            InlineKeyboardMarkup with confirmation buttons
        """
        confirm_button = UnifiedButtonBuilder.create_button(text=
            f'Confirm {action.title()}', callback_data=
            f'{entity_type}_{action}_confirm:{entity_id}', button_type=
            ButtonType.DANGER, custom_emoji='⚠️')
        cancel_button = UnifiedButtonBuilder.create_button(text='Cancel',
            callback_data=f'{entity_type}_{action}_cancel:{entity_id}',
            button_type=ButtonType.SECONDARY, custom_emoji='❌')
        return InlineKeyboardMarkup([[confirm_button, cancel_button]])


class ContextAwareButtonBuilder:
    """
    Context-aware button builder that adapts to user behavior and preferences.
    """

    @staticmethod
    def build_smart_task_keyboard(task_id: int, task_data: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]]=None
        ) ->InlineKeyboardMarkup:
        """
        Build a smart task keyboard that adapts to task context and user preferences.
        
        Args:
            task_id: Task ID
            task_data: Task data including status, priority, due_date, etc.
            user_preferences: User preferences for button layout
            
        Returns:
            InlineKeyboardMarkup with context-aware buttons
        """
        status = task_data.get('status', 'Todo')
        priority = task_data.get('priority', 'Medium')
        due_date = task_data.get('due_date')
        available_actions = [ActionType.VIEW, ActionType.DELETE]
        if status != 'Done':
            available_actions.append(ActionType.COMPLETE)
        if status not in ['Done', 'Archived']:
            available_actions.append(ActionType.EDIT)
        custom_actions = []
        if status in ['Todo', 'In Progress']:
            is_tracking = task_data.get('time_tracking_active', False)
            if is_tracking:
                custom_actions.append({'text': '⏹️ Stop Timer',
                    'callback_data': f'task_time_stop:{task_id}', 'type':
                    ButtonType.WARNING, 'emoji': '⏹️'})
            else:
                custom_actions.append({'text': '▶️ Start Timer',
                    'callback_data': f'task_time_start:{task_id}', 'type':
                    ButtonType.SUCCESS, 'emoji': '▶️'})
        if priority == 'High' or priority == 'Critical':
            custom_actions.append({'text': '📊 Time Summary',
                'callback_data': f'task_time_summary:{task_id}', 'type':
                ButtonType.INFO, 'emoji': '📊'})
        if due_date:
            custom_actions.append({'text': '📅 Extend Due Date',
                'callback_data': f'task_extend_due:{task_id}', 'type':
                ButtonType.WARNING, 'emoji': '📅'})
        return UnifiedButtonBuilder.build_entity_keyboard(entity_id=task_id,
            entity_type='task', available_actions=available_actions,
            entity_status=status, custom_actions=custom_actions)


class ProgressiveDisclosureBuilder:
    """
    Builder for progressive disclosure keyboards that show options based on user interaction.
    """

    @staticmethod
    def build_progressive_task_keyboard(task_id: int, task_data: Dict[str,
        Any], disclosure_level: int=1) ->InlineKeyboardMarkup:
        """
        Build a progressive disclosure keyboard for tasks.
        
        Args:
            task_id: Task ID
            task_data: Task data
            disclosure_level: Level of disclosure (1=basic, 2=advanced, 3=expert)
            
        Returns:
            InlineKeyboardMarkup with progressive disclosure
        """
        buttons = []
        basic_actions = [ActionType.VIEW, ActionType.COMPLETE, ActionType.
            DELETE]
        if disclosure_level >= 2:
            basic_actions.extend([ActionType.EDIT])
            if task_data.get('status') in ['Todo', 'In Progress']:
                buttons.append(UnifiedButtonBuilder.create_button(text=
                    'Time Tracking', callback_data=
                    f'task_time_menu:{task_id}', button_type=ButtonType.
                    INFO, custom_emoji='⏱️'))
        if disclosure_level >= 3:
            buttons.append(UnifiedButtonBuilder.create_button(text=
                '📊 Analytics', callback_data=f'task_analytics:{task_id}',
                button_type=ButtonType.SECONDARY))
            buttons.append(UnifiedButtonBuilder.create_button(text=
                '🔗 Dependencies', callback_data=
                f'task_dependencies:{task_id}', button_type=ButtonType.
                SECONDARY))
        for action in basic_actions:
            button = UnifiedButtonBuilder.create_action_button(action_type=
                action, entity_id=task_id, entity_type='task')
            buttons.append(button)
        if disclosure_level < 3:
            buttons.append(UnifiedButtonBuilder.create_button(text=
                'More Options', callback_data=
                f'task_disclose:{task_id}:{disclosure_level + 1}',
                button_type=ButtonType.SECONDARY, custom_emoji='➕'))
        return InlineKeyboardMarkup([buttons])

    @staticmethod
    def build_smart_disclosure_keyboard(entity_type: str, entity_id: int,
        entity_data: Dict[str, Any], user_preferences: Dict[str, Any]=None
        ) ->InlineKeyboardMarkup:
        """
        Build smart disclosure keyboard that adapts to user preferences and entity type.
        
        Args:
            entity_type: Type of entity (task, client, habit, etc.)
            entity_id: Entity ID
            entity_data: Entity data
            user_preferences: User preferences for disclosure
            
        Returns:
            Smart disclosure keyboard
        """
        default_level = user_preferences.get('preferred_disclosure_level', 2
            ) if user_preferences else 2
        complexity_score = (ProgressiveDisclosureBuilder.
            _calculate_entity_complexity(entity_data))
        if complexity_score > 0.7:
            default_level = min(default_level + 1, 3)
        elif complexity_score < 0.3:
            default_level = max(default_level - 1, 1)
        if entity_type == 'task':
            return (ProgressiveDisclosureBuilder.
                build_progressive_task_keyboard(entity_id, entity_data,
                default_level))
        elif entity_type == 'client':
            return (ProgressiveDisclosureBuilder.
                _build_client_disclosure_keyboard(entity_id, entity_data,
                default_level))
        elif entity_type == 'habit':
            return (ProgressiveDisclosureBuilder.
                _build_habit_disclosure_keyboard(entity_id, entity_data,
                default_level))
        else:
            return (ProgressiveDisclosureBuilder.
                _build_generic_disclosure_keyboard(entity_type, entity_id,
                entity_data, default_level))

    @staticmethod
    def _calculate_entity_complexity(entity_data: Dict[str, Any]) ->float:
        """Calculate complexity score for an entity (0.0 to 1.0)."""
        complexity_factors = {'has_subtasks': 0.2, 'has_attachments': 0.15,
            'has_comments': 0.1, 'has_dependencies': 0.2,
            'has_time_tracking': 0.15, 'has_reminders': 0.1,
            'description_length': 0.1}
        score = 0.0
        if entity_data.get('subtasks'):
            score += complexity_factors['has_subtasks']
        if entity_data.get('attachments'):
            score += complexity_factors['has_attachments']
        if entity_data.get('comments'):
            score += complexity_factors['has_comments']
        if entity_data.get('dependencies'):
            score += complexity_factors['has_dependencies']
        if entity_data.get('time_entries'):
            score += complexity_factors['has_time_tracking']
        if entity_data.get('reminders'):
            score += complexity_factors['has_reminders']
        description = entity_data.get('description', '')
        if len(description) > 100:
            score += complexity_factors['description_length']
        elif len(description) > 50:
            score += complexity_factors['description_length'] * 0.5
        return min(score, 1.0)

    @staticmethod
    def _build_client_disclosure_keyboard(client_id: int, client_data: Dict
        [str, Any], level: int) ->InlineKeyboardMarkup:
        """Build progressive disclosure keyboard for clients."""
        buttons = []
        if level >= 1:
            buttons.extend([[UnifiedButtonBuilder.create_button(text=
                '📋 View Tasks', callback_data=f'client_tasks:{client_id}',
                button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.
                create_button(text='📊 Analytics', callback_data=
                f'client_analytics:{client_id}', button_type=ButtonType.INFO)]]
                )
        if level >= 2:
            buttons.extend([[UnifiedButtonBuilder.create_button(text=
                '✏️ Edit Client', callback_data=f'client_edit:{client_id}',
                button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.
                create_button(text='📅 Schedule', callback_data=
                f'client_schedule:{client_id}', button_type=ButtonType.INFO)]])
        if level >= 3:
            buttons.extend([[UnifiedButtonBuilder.create_button(text=
                '📤 Export Data', callback_data=f'client_export:{client_id}',
                button_type=ButtonType.INFO)], [UnifiedButtonBuilder.
                create_button(text='🗑️ Delete Client', callback_data=
                f'client_delete:{client_id}', button_type=ButtonType.INFO)]])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def _build_habit_disclosure_keyboard(habit_id: int, habit_data: Dict[
        str, Any], level: int) ->InlineKeyboardMarkup:
        """Build progressive disclosure keyboard for habits."""
        buttons = []
        if level >= 1:
            buttons.extend([[UnifiedButtonBuilder.create_button(text=
                '✅ Complete Today', callback_data=
                f'habit_complete:{habit_id}', button_type=ButtonType.PRIMARY)],
                [UnifiedButtonBuilder.create_button(text='📊 Progress',
                callback_data=f'habit_progress:{habit_id}', button_type=
                ButtonType.INFO)]])
        if level >= 2:
            buttons.extend([[UnifiedButtonBuilder.create_button(text=
                '✏️ Edit Habit', callback_data=f'habit_edit:{habit_id}',
                button_type=ButtonType.SECONDARY)], [UnifiedButtonBuilder.
                create_button(text='⏰ Reminders', callback_data=
                f'habit_reminders:{habit_id}', button_type=ButtonType.INFO)]])
        if level >= 3:
            buttons.extend([[UnifiedButtonBuilder.create_button(text=
                '📈 Analytics', callback_data=f'habit_analytics:{habit_id}',
                button_type=ButtonType.INFO)], [UnifiedButtonBuilder.
                create_button(text='🗑️ Delete Habit', callback_data=
                f'habit_delete:{habit_id}', button_type=ButtonType.INFO)]])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def _build_generic_disclosure_keyboard(entity_type: str, entity_id: int,
        entity_data: Dict[str, Any], level: int) ->InlineKeyboardMarkup:
        """Build generic progressive disclosure keyboard."""
        buttons = []
        if level >= 1:
            buttons.extend([[UnifiedButtonBuilder.create_button(text=
                '👁️ View', callback_data=f'{entity_type}_view:{entity_id}',
                button_type=ButtonType.INFO)], [UnifiedButtonBuilder.
                create_button(text='✏️ Edit', callback_data=
                f'{entity_type}_edit:{entity_id}', button_type=ButtonType.
                INFO)]])
        if level >= 2:
            buttons.extend([[UnifiedButtonBuilder.create_button(text=
                '📊 Details', callback_data=
                f'{entity_type}_details:{entity_id}', button_type=
                ButtonType.INFO)], [UnifiedButtonBuilder.create_button(text
                ='⚙️ Options', callback_data=
                f'{entity_type}_options:{entity_id}', button_type=
                ButtonType.INFO)]])
        if level >= 3:
            buttons.extend([[UnifiedButtonBuilder.create_button(text=
                '🗑️ Delete', callback_data=
                f'{entity_type}_delete:{entity_id}', button_type=ButtonType.DANGER)]])
        return InlineKeyboardMarkup(buttons)


class SmartSuggestionsHelper:
    """
    Enhanced smart suggestions system that provides context-aware recommendations
    based on user patterns, task history, and current context.
    """

    def __init__(self):
        self.user_patterns = {}
        self.suggestion_weights = {'recent_actions': 0.3,
            'task_completion_rate': 0.25, 'priority_patterns': 0.2,
            'time_patterns': 0.15, 'category_preferences': 0.1}

    @staticmethod
    def suggest_next_actions(current_context: str, user_data: dict,
        task_history: list=None) ->list:
        """
        Suggest next actions based on current context and user patterns.
        
        Args:
            current_context: Current user context (e.g., 'task_view', 'task_list')
            user_data: User data and preferences
            task_history: Recent task history
            
        Returns:
            List of suggested actions with confidence scores
        """
        suggestions = []
        if current_context == 'task_view':
            suggestions.extend([{'action': 'edit_task', 'confidence': 0.9,
                'reason': 'Currently viewing a task'}, {'action':
                'complete_task', 'confidence': 0.8, 'reason':
                'Quick completion option'}, {'action': 'add_subtask',
                'confidence': 0.7, 'reason': 'Break down complex task'}, {
                'action': 'set_reminder', 'confidence': 0.6, 'reason':
                'Stay on track'}])
        elif current_context == 'task_list':
            suggestions.extend([{'action': 'add_task', 'confidence': 0.9,
                'reason': 'Primary action in task list'}, {'action':
                'filter_tasks', 'confidence': 0.7, 'reason':
                'Organize view'}, {'action': 'bulk_operations',
                'confidence': 0.6, 'reason': 'Efficient management'}, {
                'action': 'analytics', 'confidence': 0.5, 'reason':
                'Track progress'}])
        elif current_context == 'analytics':
            suggestions.extend([{'action': 'productivity_report',
                'confidence': 0.8, 'reason': 'Detailed insights'}, {
                'action': 'export_data', 'confidence': 0.6, 'reason':
                'Data analysis'}, {'action': 'set_goals', 'confidence': 0.7,
                'reason': 'Improve performance'}])
        if task_history:
            suggestions.extend(SmartSuggestionsHelper.
                _analyze_task_patterns(task_history))
        if user_data:
            suggestions.extend(SmartSuggestionsHelper.
                _analyze_user_preferences(user_data))
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:5]

    @staticmethod
    def suggest_task_improvements(task_data: dict, user_patterns: dict=None
        ) ->list:
        """
        Suggest improvements for a specific task based on best practices and user patterns.
        
        Args:
            task_data: Current task data
            user_patterns: User's historical patterns
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        if task_data.get('priority') == 'Medium' and task_data.get('status'
            ) == 'Todo':
            suggestions.append({'type': 'priority', 'message':
                'Consider setting a higher priority for better organization',
                'confidence': 0.8, 'action': 'set_priority_high'})
        if not task_data.get('due_date') and task_data.get('status') == 'Todo':
            suggestions.append({'type': 'due_date', 'message':
                'Add a due date to track progress and avoid delays',
                'confidence': 0.9, 'action': 'set_due_date'})
        if not task_data.get('category'):
            suggested_category = (SmartSuggestionsHelper.
                _suggest_category_from_description(task_data.get(
                'description', '')))
            if suggested_category:
                suggestions.append({'type': 'category', 'message':
                    f'Consider categorizing as "{suggested_category}" for better organization'
                    , 'confidence': 0.7, 'action':
                    f'set_category_{suggested_category.lower()}'})
        if task_data.get('status') == 'In Progress' and not task_data.get(
            'time_entries'):
            suggestions.append({'type': 'time_tracking', 'message':
                'Start time tracking to monitor progress', 'confidence': 
                0.8, 'action': 'start_time_tracking'})
        description = task_data.get('description', '')
        if len(description) > 50 and not task_data.get('subtasks'):
            suggestions.append({'type': 'subtasks', 'message':
                'Consider breaking this complex task into subtasks',
                'confidence': 0.6, 'action': 'add_subtasks'})
        return suggestions

    @staticmethod
    def suggest_productivity_improvements(user_data: dict, task_history: list
        ) ->dict:
        """
        Suggest productivity improvements based on user patterns and task history.
        
        Args:
            user_data: User data and preferences
            task_history: Recent task history
            
        Returns:
            Dictionary of improvement suggestions with categories
        """
        suggestions = {'time_management': [], 'task_organization': [],
            'workflow_optimization': [], 'goal_setting': []}
        completion_rate = SmartSuggestionsHelper._calculate_completion_rate(
            task_history)
        if completion_rate < 0.7:
            suggestions['task_organization'].append({'title':
                'Improve Task Completion Rate', 'message':
                f'Your completion rate is {completion_rate:.1%}. Consider setting smaller, more achievable goals.'
                , 'priority': 'high'})
        priority_dist = SmartSuggestionsHelper._analyze_priority_distribution(
            task_history)
        if priority_dist.get('High', 0) > 0.5:
            suggestions['time_management'].append({'title':
                'High Priority Overload', 'message':
                'Too many high-priority tasks can reduce effectiveness. Consider prioritizing more carefully.'
                , 'priority': 'medium'})
        time_patterns = SmartSuggestionsHelper._analyze_time_patterns(
            task_history)
        if time_patterns.get('overdue_rate', 0) > 0.2:
            suggestions['time_management'].append({'title':
                'Reduce Overdue Tasks', 'message':
                f"{time_patterns['overdue_rate']:.1%} of tasks are overdue. Consider more realistic due dates."
                , 'priority': 'high'})
        return suggestions

    @staticmethod
    def _analyze_task_patterns(task_history: list) ->list:
        """Analyze task history to identify patterns and suggest actions."""
        suggestions = []
        if not task_history:
            return suggestions
        completion_times = [t.get('completion_time', 0) for t in
            task_history if t.get('completion_time')]
        if completion_times:
            avg_completion = sum(completion_times) / len(completion_times)
            if avg_completion > 24:
                suggestions.append({'action': 'time_tracking', 'confidence':
                    0.7, 'reason':
                    'Tasks take longer than expected - time tracking can help'}
                    )
        priorities = [t.get('priority', 'Medium') for t in task_history]
        high_priority_count = priorities.count('High') + priorities.count(
            'Critical')
        if high_priority_count > len(priorities) * 0.4:
            suggestions.append({'action': 'priority_review', 'confidence': 
                0.8, 'reason':
                'Many high-priority tasks - consider priority review'})
        return suggestions

    @staticmethod
    def _analyze_user_preferences(user_data: dict) ->list:
        """Analyze user preferences to suggest personalized actions."""
        suggestions = []
        if user_data.get('prefers_time_tracking', False):
            suggestions.append({'action': 'start_time_tracking',
                'confidence': 0.6, 'reason':
                'You prefer time tracking for tasks'})
        if user_data.get('views_analytics_frequently', False):
            suggestions.append({'action': 'view_analytics', 'confidence': 
                0.7, 'reason': 'You frequently check analytics'})
        return suggestions

    @staticmethod
    def _suggest_category_from_description(description: str) ->str:
        """Suggest category based on task description keywords."""
        description_lower = description.lower()
        category_keywords = {'Work': ['work', 'project', 'meeting',
            'client', 'business', 'office'], 'Personal': ['personal',
            'home', 'family', 'life', 'private'], 'Health': ['exercise',
            'fitness', 'health', 'medical', 'doctor', 'gym'], 'Learning': [
            'study', 'learn', 'course', 'training', 'education', 'read'],
            'Finance': ['money', 'finance', 'bills', 'budget', 'expenses',
            'pay'], 'Shopping': ['buy', 'purchase', 'shop', 'order',
            'shopping'], 'Travel': ['travel', 'trip', 'vacation', 'flight',
            'hotel', 'booking']}
        for category, keywords in category_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                return category
        return None

    @staticmethod
    def _calculate_completion_rate(task_history: list) ->float:
        """Calculate task completion rate from history."""
        if not task_history:
            return 0.0
        completed = sum(1 for task in task_history if task.get('status') ==
            'Done')
        return completed / len(task_history)

    @staticmethod
    def _analyze_priority_distribution(task_history: list) ->dict:
        """Analyze distribution of task priorities."""
        priorities = [task.get('priority', 'Medium') for task in task_history]
        distribution = {}
        for priority in priorities:
            distribution[priority] = distribution.get(priority, 0) + 1
        total = len(priorities)
        if total > 0:
            distribution = {k: (v / total) for k, v in distribution.items()}
        return distribution

    @staticmethod
    def _analyze_time_patterns(task_history: list) ->dict:
        """Analyze time-related patterns in task history."""
        patterns = {'overdue_rate': 0.0, 'avg_completion_time': 0.0,
            'on_time_rate': 0.0}
        if not task_history:
            return patterns
        overdue_count = 0
        completion_times = []
        on_time_count = 0
        for task in task_history:
            if task.get('status') == 'Done' and task.get('due_date'):
                if task.get('completed_at') and task.get('due_date'):
                    if task['completed_at'] > task['due_date']:
                        overdue_count += 1
                    else:
                        on_time_count += 1
            if task.get('completion_time'):
                completion_times.append(task['completion_time'])
        total_completed = sum(1 for t in task_history if t.get('status') ==
            'Done')
        if total_completed > 0:
            patterns['overdue_rate'] = overdue_count / total_completed
            patterns['on_time_rate'] = on_time_count / total_completed
        if completion_times:
            patterns['avg_completion_time'] = sum(completion_times) / len(
                completion_times)
        return patterns


class IntelligentDefaultsHelper:
    """
    Intelligent defaults system that provides smart default values based on
    user patterns, context, and best practices.
    """

    def __init__(self):
        self.user_patterns = {}
        self.default_weights = {'recent_usage': 0.4, 'user_preferences': 
            0.3, 'best_practices': 0.2, 'context': 0.1}

    @staticmethod
    def suggest_task_defaults(user_input: str, user_context: dict=None,
        task_history: list=None) ->dict:
        """
        Suggest intelligent defaults for task creation.
        
        Args:
            user_input: User's task description
            user_context: Current user context
            task_history: User's task history
            
        Returns:
            Dictionary of suggested defaults
        """
        defaults = {'priority': 'Medium', 'category': None, 'due_date':
            None, 'tags': [], 'reminder': None}
        priority_keywords = {'urgent': ['urgent', 'asap', 'emergency',
            'critical', 'immediate'], 'high': ['high', 'important',
            'priority', 'crucial', 'essential'], 'low': ['low', 'minor',
            'optional', 'when possible', 'someday']}
        input_lower = user_input.lower()
        for priority, keywords in priority_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                defaults['priority'] = priority.title()
                break
        category_keywords = {'Work': ['work', 'project', 'meeting',
            'client', 'business', 'office', 'report'], 'Personal': [
            'personal', 'home', 'family', 'life', 'private', 'household'],
            'Health': ['exercise', 'fitness', 'health', 'medical', 'gym',
            'workout'], 'Learning': ['study', 'learn', 'read', 'practice',
            'skill'], 'Finance': ['money', 'finance', 'bills', 'budget',
            'expenses', 'pay', 'banking'], 'Shopping': ['buy', 'purchase',
            'shop', 'order', 'shopping', 'grocery'], 'Travel': ['travel',
            'trip', 'vacation', 'flight', 'hotel', 'booking', 'reservation']}
        for category, keywords in category_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                defaults['category'] = category
                break
        due_date_keywords = {'today': 0, 'tomorrow': 1, 'next week': 7,
            'this week': 3, 'next month': 30, 'end of month': None}
        for keyword, days in due_date_keywords.items():
            if keyword in input_lower:
                if days is not None:
                    from datetime import datetime, timedelta
                    defaults['due_date'] = (datetime.now() + timedelta(days
                        =days)).strftime('%Y-%m-%d')
                else:
                    from datetime import datetime
                    today = datetime.now()
                    if today.month == 12:
                        end_of_month = datetime(today.year + 1, 1, 1
                            ) - timedelta(days=1)
                    else:
                        end_of_month = datetime(today.year, today.month + 1, 1
                            ) - timedelta(days=1)
                    defaults['due_date'] = end_of_month.strftime('%Y-%m-%d')
                break
        tag_suggestions = IntelligentDefaultsHelper._suggest_tags(user_input)
        if tag_suggestions:
            defaults['tags'] = tag_suggestions
        if defaults['priority'] == 'High' and defaults['due_date']:
            defaults['reminder'] = '1_day_before'
        elif defaults['due_date']:
            defaults['reminder'] = '2_days_before'
        if user_context and task_history:
            IntelligentDefaultsHelper._apply_user_patterns(defaults,
                user_context, task_history)
        return defaults

    @staticmethod
    def suggest_habit_defaults(user_input: str, user_context: dict=None
        ) ->dict:
        """
        Suggest intelligent defaults for habit creation.
        
        Args:
            user_input: User's habit description
            user_context: Current user context
            
        Returns:
            Dictionary of suggested defaults
        """
        defaults = {'frequency': 'daily', 'time_of_day': 'morning',
            'reminder': True, 'goal': 1, 'category': None}
        input_lower = user_input.lower()
        frequency_keywords = {'daily': ['daily', 'every day', 'each day',
            'morning', 'evening'], 'weekly': ['weekly', 'every week',
            'once a week'], 'monthly': ['monthly', 'every month',
            'once a month']}
        for frequency, keywords in frequency_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                defaults['frequency'] = frequency
                break
        time_keywords = {'morning': ['morning', 'breakfast', 'wake up',
            'start of day'], 'afternoon': ['afternoon', 'lunch', 'midday'],
            'evening': ['evening', 'dinner', 'night', 'before bed']}
        for time_of_day, keywords in time_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                defaults['time_of_day'] = time_of_day
                break
        category_keywords = {'Health': ['exercise', 'fitness', 'health',
            'medical', 'gym', 'workout'], 'Learning': ['study', 'learn',
            'read', 'practice', 'skill'], 'Personal': ['personal', 'home',
            'family', 'life'], 'Work': ['work', 'professional', 'career',
            'job']}
        for category, keywords in category_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                defaults['category'] = category
                break
        return defaults

    @staticmethod
    def suggest_reminder_defaults(task_data: dict, user_preferences: dict=None
        ) ->dict:
        """
        Suggest intelligent defaults for reminder creation.
        
        Args:
            task_data: Task data
            user_preferences: User preferences
            
        Returns:
            Dictionary of suggested defaults
        """
        defaults = {'timing': '1_day_before', 'method': 'notification',
            'message': None}
        priority = task_data.get('priority', 'Medium')
        due_date = task_data.get('due_date')
        if priority == 'High':
            defaults['timing'] = '2_hours_before'
        elif priority == 'Medium':
            defaults['timing'] = '1_day_before'
        else:
            defaults['timing'] = '2_days_before'
        if user_preferences:
            preferred_method = user_preferences.get('preferred_reminder_method'
                , 'notification')
            defaults['method'] = preferred_method
        task_description = task_data.get('description', '')
        if task_description:
            defaults['message'] = (
                f"Reminder: {task_description[:50]}{'...' if len(task_description) > 50 else ''}"
                )
        return defaults

    @staticmethod
    def suggest_filter_defaults(user_context: dict, task_history: list=None
        ) ->dict:
        """
        Suggest intelligent defaults for task filtering.
        
        Args:
            user_context: Current user context
            task_history: User's task history
            
        Returns:
            Dictionary of suggested defaults
        """
        defaults = {'status': 'all', 'priority': 'all', 'category': 'all',
            'sort_by': 'due_date', 'sort_order': 'asc'}
        if user_context.get('current_context') == 'overdue_tasks':
            defaults['status'] = 'overdue'
            defaults['sort_by'] = 'due_date'
            defaults['sort_order'] = 'asc'
        elif user_context.get('current_context') == 'high_priority':
            defaults['priority'] = 'high'
            defaults['sort_by'] = 'priority'
            defaults['sort_order'] = 'desc'
        if task_history:
            incomplete_tasks = [t for t in task_history if t.get('status') !=
                'Done']
            if incomplete_tasks:
                status_counts = {}
                for task in incomplete_tasks:
                    status = task.get('status', 'Todo')
                    status_counts[status] = status_counts.get(status, 0) + 1
                if status_counts:
                    most_common_status = max(status_counts, key=
                        status_counts.get)
                    defaults['status'] = most_common_status
        return defaults

    @staticmethod
    def _suggest_tags(text: str) ->list:
        """Suggest tags based on text content."""
        tags = []
        text_lower = text.lower()
        tag_patterns = {'urgent': ['urgent', 'asap', 'emergency'],
            'meeting': ['meeting', 'call', 'conference'], 'review': [
            'review', 'check', 'verify'], 'creative': ['design', 'creative',
            'art', 'write'], 'technical': ['code', 'debug', 'technical',
            'programming'], 'research': ['research', 'study', 'analyze',
            'investigate']}
        for tag, keywords in tag_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                tags.append(tag)
        return tags[:3]

    @staticmethod
    def _apply_user_patterns(defaults: dict, user_context: dict,
        task_history: list):
        """Apply user-specific patterns to defaults."""
        if not task_history:
            return
        priority_counts = {}
        for task in task_history[-20:]:
            priority = task.get('priority', 'Medium')
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        if priority_counts:
            most_common_priority = max(priority_counts, key=priority_counts.get
                )
            if priority_counts[most_common_priority] > len(task_history) * 0.5:
                defaults['priority'] = most_common_priority
        category_counts = {}
        for task in task_history[-20:]:
            category = task.get('category')
            if category:
                category_counts[category] = category_counts.get(category, 0
                    ) + 1
        if category_counts and not defaults.get('category'):
            most_common_category = max(category_counts, key=category_counts.get
                )
            if category_counts[most_common_category] > len(task_history) * 0.3:
                defaults['category'] = most_common_category


class EnhancedUXSystem:
    """Main enhanced UX system that coordinates all components."""

    def __init__(self):
        self.layout_builder = MessageLayoutBuilder()
        self.navigation_helper = SmartNavigationHelper()
        self.error_recovery_helper = ErrorRecoveryHelper()
        self.feedback_system = VisualFeedbackSystem()

    def enhance_message(self, message: str, context: dict, user_id: int=None
        ) ->Tuple[str, InlineKeyboardMarkup]:
        """
        Enhance a message with all UX improvements.
        
        Args:
            message: Original message
            context: Message context
            user_id: User ID for personalization
            
        Returns:
            Tuple of (enhanced_message, keyboard)
        """
        enhanced_message = message
        if context.get('navigation_path'):
            enhanced_message = (self.navigation_helper.
                add_breadcrumb_navigation(enhanced_message, context[
                'navigation_path']))
        available_actions = context.get('available_actions', [])
        keyboard = self.navigation_helper.build_contextual_keyboard(context
            .get('current_context', ''), available_actions, context.get(
            'user_history', []))
        return enhanced_message, keyboard

    def create_error_response(self, error_type: str, error_message: str,
        context: dict) ->Tuple[str, InlineKeyboardMarkup]:
        """
        Create enhanced error response with recovery options.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Error context
            
        Returns:
            Tuple of (error_message, recovery_keyboard)
        """
        formatted_error = f"❌ **Error**: {escape_markdown(error_message)}"
        help_message = self.error_recovery_helper.provide_contextual_help({
            'type': error_type, 'message': error_message})
        full_message = formatted_error + '\n\n' + help_message
        keyboard = self.error_recovery_helper.build_error_recovery_keyboard(
            error_type, context)
        return full_message, keyboard


def escape_markdown_v2(text: str) ->str:
    """Escape all special characters for Telegram MarkdownV2."""
    if not text:
        return text
    escape_chars = '_\\*\\[\\]\\(\\)~`>#+\\-=|{}.!'
    return ''.join(f'\\{c}' if c in escape_chars else c for c in text)


__all__ = ['UnifiedButtonBuilder', 'ContextAwareButtonBuilder',
    'ProgressiveDisclosureBuilder', 'ButtonType', 'ActionType']
