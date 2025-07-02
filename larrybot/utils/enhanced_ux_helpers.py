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
from larrybot.utils.ux_helpers import MessageFormatter


class MessageLayoutBuilder:
    """Enhanced message layout builder with improved visual hierarchy."""
    
    @staticmethod
    def build_section_header(title: str, icon: str = "📋", subtitle: str = None) -> str:
        """
        Create consistent section headers with visual separation.
        
        Args:
            title: Section title
            icon: Icon for the section
            subtitle: Optional subtitle
            
        Returns:
            Formatted section header
        """
        header = f"{icon} **{MessageFormatter.escape_markdown(title)}**"
        if subtitle:
            header += f"\n_{MessageFormatter.escape_markdown(subtitle)}_"
        header += "\n" + "─" * 30 + "\n"
        return header
    
    @staticmethod
    def build_info_card(title: str, content: dict, style: str = "default") -> str:
        """
        Create structured information cards with consistent styling.
        
        Args:
            title: Card title
            content: Dictionary of key-value pairs
            style: Card style (default, success, warning, error)
            
        Returns:
            Formatted info card
        """
        # Style-specific formatting
        style_configs = {
            "default": {"icon": "ℹ️", "separator": "│"},
            "success": {"icon": "✅", "separator": "│"},
            "warning": {"icon": "⚠️", "separator": "│"},
            "error": {"icon": "❌", "separator": "│"}
        }
        
        config = style_configs.get(style, style_configs["default"])
        
        card = f"{config['icon']} **{MessageFormatter.escape_markdown(title)}**\n"
        card += "┌" + "─" * 28 + "┐\n"
        
        for key, value in content.items():
            safe_key = MessageFormatter.escape_markdown(str(key))
            safe_value = MessageFormatter.escape_markdown(str(value))
            card += f"{config['separator']} {safe_key}: {safe_value}\n"
        
        card += "└" + "─" * 28 + "┘\n"
        return card
    
    @staticmethod
    def build_progressive_list(items: list, max_visible: int = 5, title: str = "Items") -> str:
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
            return f"📋 **{title}**\n\nNo items found."
        
        total_items = len(items)
        visible_items = items[:max_visible]
        
        message = f"📋 **{title}** \\({total_items} total\\)\n\n"
        
        for i, item in enumerate(visible_items, 1):
            if hasattr(item, 'description'):
                description = item.description
            elif isinstance(item, dict):
                description = item.get('description', str(item))
            else:
                description = str(item)
            
            safe_desc = MessageFormatter.escape_markdown(description[:50])
            if len(description) > 50:
                safe_desc += "..."
            
            message += f"{i}\\. {safe_desc}\n"
        
        if total_items > max_visible:
            remaining = total_items - max_visible
            message += f"\n\\.\\.\\. and {remaining} more items"
        
        return message
    
    @staticmethod
    def build_status_indicator(status: str, priority: str = None, due_date: str = None) -> str:
        """
        Create visual status indicators with color coding.
        
        Args:
            status: Task status
            priority: Task priority
            due_date: Due date string
            
        Returns:
            Formatted status indicator
        """
        # Status emojis
        status_emojis = {
            "Todo": "⏳",
            "In Progress": "🔄",
            "Review": "👀",
            "Done": "✅",
            "Overdue": "⚠️"
        }
        
        # Priority emojis
        priority_emojis = {
            "Low": "🟢",
            "Medium": "🟡",
            "High": "🟠",
            "Critical": "🔴"
        }
        
        indicator = f"{status_emojis.get(status, '❓')} **{status}**"
        
        if priority:
            indicator += f" {priority_emojis.get(priority, '⚪')} {priority}"
        
        if due_date:
            indicator += f" 📅 {MessageFormatter.escape_markdown(due_date)}"
        
        return indicator
    
    @staticmethod
    def build_summary_card(title: str, metrics: dict, show_percentages: bool = True) -> str:
        """
        Create summary cards with key metrics.
        
        Args:
            title: Card title
            metrics: Dictionary of metric name and value
            show_percentages: Whether to show percentages for numeric values
            
        Returns:
            Formatted summary card
        """
        card = f"📊 **{MessageFormatter.escape_markdown(title)}**\n\n"
        
        for metric_name, value in metrics.items():
            safe_name = MessageFormatter.escape_markdown(str(metric_name))
            
            if isinstance(value, (int, float)) and show_percentages:
                card += f"• {safe_name}: {value}%\n"
            else:
                safe_value = MessageFormatter.escape_markdown(str(value))
                card += f"• {safe_name}: {safe_value}\n"
        
        return card.strip()


class SmartNavigationHelper:
    """Enhanced navigation helper with context awareness."""
    
    @staticmethod
    def build_contextual_keyboard(
        current_context: str,
        available_actions: list,
        user_history: list = None
    ) -> InlineKeyboardMarkup:
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
        
        # Group actions by type
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
        
        # Add primary actions
        if primary_actions:
            primary_row = []
            for action in primary_actions[:3]:  # Max 3 per row
                primary_row.append(InlineKeyboardButton(
                    action['text'], 
                    callback_data=action['callback_data']
                ))
            buttons.append(primary_row)
        
        # Add secondary actions
        if secondary_actions:
            for action in secondary_actions:
                buttons.append([InlineKeyboardButton(
                    action['text'], 
                    callback_data=action['callback_data']
                )])
        
        # Add navigation actions
        if navigation_actions:
            nav_row = []
            for action in navigation_actions[:2]:  # Max 2 per row
                nav_row.append(InlineKeyboardButton(
                    action['text'], 
                    callback_data=action['callback_data']
                ))
            buttons.append(nav_row)
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def add_breadcrumb_navigation(message: str, navigation_path: list) -> str:
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
        
        breadcrumb = "📍 **Navigation:** "
        breadcrumb_parts = []
        
        for i, step in enumerate(navigation_path):
            if i == len(navigation_path) - 1:
                # Current step
                breadcrumb_parts.append(f"**{MessageFormatter.escape_markdown(step)}**")
            else:
                # Previous steps
                breadcrumb_parts.append(MessageFormatter.escape_markdown(step))
        
        breadcrumb += " > ".join(breadcrumb_parts)
        breadcrumb += "\n\n"
        
        return breadcrumb + message
    
    @staticmethod
    def suggest_next_actions(current_action: str, user_patterns: dict) -> list:
        """
        Suggest next actions based on user behavior patterns.
        
        Args:
            current_action: Current user action
            user_patterns: User's behavior patterns
            
        Returns:
            List of suggested next actions
        """
        # Common action patterns
        action_patterns = {
            "task_list": ["add_task", "filter_tasks", "analytics"],
            "task_view": ["edit_task", "complete_task", "delete_task"],
            "client_list": ["add_client", "view_client", "client_analytics"],
            "habit_list": ["add_habit", "complete_habit", "habit_stats"],
            "analytics": ["export_report", "filter_analytics", "compare_periods"]
        }
        
        return action_patterns.get(current_action, [])
    
    @staticmethod
    def build_quick_actions_keyboard(entity_type: str, entity_id: int) -> InlineKeyboardMarkup:
        """
        Build quick action keyboard for specific entity types.
        
        Args:
            entity_type: Type of entity (task, client, habit, etc.)
            entity_id: Entity ID
            
        Returns:
            Quick actions keyboard
        """
        quick_actions = {
            "task": [
                ("✅ Done", f"task_done:{entity_id}"),
                ("✏️ Edit", f"task_edit:{entity_id}"),
                ("👁️ View", f"task_view:{entity_id}"),
                ("🗑️ Delete", f"task_delete:{entity_id}")
            ],
            "client": [
                ("📋 Tasks", f"client_tasks:{entity_id}"),
                ("📊 Analytics", f"client_analytics:{entity_id}"),
                ("✏️ Edit", f"client_edit:{entity_id}"),
                ("🗑️ Delete", f"client_delete:{entity_id}")
            ],
            "habit": [
                ("✅ Complete", f"habit_done:{entity_id}"),
                ("📊 Progress", f"habit_progress:{entity_id}"),
                ("🗑️ Delete", f"habit_delete:{entity_id}")
            ]
        }
        
        actions = quick_actions.get(entity_type, [])
        buttons = []
        
        # Group buttons in rows of 2
        for i in range(0, len(actions), 2):
            row = []
            row.append(InlineKeyboardButton(actions[i][0], callback_data=actions[i][1]))
            if i + 1 < len(actions):
                row.append(InlineKeyboardButton(actions[i + 1][0], callback_data=actions[i + 1][1]))
            buttons.append(row)
        
        return InlineKeyboardMarkup(buttons)


class ErrorRecoveryHelper:
    """Enhanced error handling with recovery options."""
    
    @staticmethod
    def build_error_recovery_keyboard(error_type: str, context: dict) -> InlineKeyboardMarkup:
        """
        Build recovery options based on error type.
        
        Args:
            error_type: Type of error that occurred
            context: Error context information
            
        Returns:
            Error recovery keyboard
        """
        # Error-specific recovery actions
        recovery_actions = {
            "validation_error": [
                ("🔄 Try Again", "retry_action"),
                ("📝 Edit Input", "edit_input"),
                ("❓ Help", "show_help")
            ],
            "not_found_error": [
                ("🔍 Search", "search_similar"),
                ("📋 List All", "list_all"),
                ("➕ Create New", "create_new")
            ],
            "permission_error": [
                ("🔐 Check Permissions", "check_permissions"),
                ("📞 Contact Admin", "contact_admin")
            ],
            "network_error": [
                ("🔄 Retry", "retry_network"),
                ("📡 Check Connection", "check_connection"),
                ("⏰ Try Later", "try_later")
            ]
        }
        
        actions = recovery_actions.get(error_type, [
            ("🔄 Retry", "retry_action"),
            ("🏠 Main Menu", "nav_main"),
            ("❓ Help", "show_help")
        ])
        
        buttons = []
        for action_text, callback_data in actions:
            buttons.append([InlineKeyboardButton(action_text, callback_data=callback_data)])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def suggest_alternatives(failed_command: str, user_context: dict) -> list:
        """
        Suggest alternative commands or approaches.
        
        Args:
            failed_command: Command that failed
            user_context: User context information
            
        Returns:
            List of alternative suggestions
        """
        # Command alternatives mapping
        command_alternatives = {
            "add_task": ["/add", "/task_add", "/new_task"],
            "edit_task": ["/edit", "/modify_task", "/update_task"],
            "delete_task": ["/remove", "/del_task", "/rm_task"],
            "list_tasks": ["/tasks", "/list", "/show_tasks"],
            "add_client": ["/client_add", "/new_client", "/create_client"],
            "list_clients": ["/clients", "/allclients", "/show_clients"]
        }
        
        return command_alternatives.get(failed_command, [])
    
    @staticmethod
    def provide_contextual_help(error_context: dict) -> str:
        """
        Provide contextual help based on error situation.
        
        Args:
            error_context: Error context information
            
        Returns:
            Contextual help message
        """
        error_type = error_context.get('type', 'unknown')
        error_message = error_context.get('message', 'An error occurred')
        
        help_messages = {
            "validation_error": f"💡 **Help**: {MessageFormatter.escape_markdown(error_message)}\n\n"
                               f"Please check your input format and try again\\.",
            "not_found_error": f"💡 **Help**: The requested item was not found\\.\n\n"
                              f"Try searching for similar items or create a new one\\.",
            "permission_error": f"💡 **Help**: You don't have permission for this action\\.\n\n"
                               f"Contact an administrator if you believe this is an error\\.",
            "network_error": f"💡 **Help**: Network connection issue detected\\.\n\n"
                            f"Please check your internet connection and try again\\."
        }
        
        return help_messages.get(error_type, f"💡 **Help**: {MessageFormatter.escape_markdown(error_message)}")


class VisualFeedbackSystem:
    """Comprehensive visual feedback system."""
    
    @staticmethod
    def show_loading_state(operation: str, estimated_time: float = None) -> str:
        """
        Show loading state with progress indicators.
        
        Args:
            operation: Operation being performed
            estimated_time: Estimated time in seconds
            
        Returns:
            Loading state message
        """
        loading_message = f"⏳ **{MessageFormatter.escape_markdown(operation)}**\n\n"
        loading_message += "🔄 Processing\\.\\.\\."
        
        if estimated_time:
            loading_message += f"\n⏱️ Estimated time: {estimated_time:.1f}s"
        
        return loading_message
    
    @staticmethod
    def show_success_animation(action: str, details: dict) -> str:
        """
        Show success feedback with visual elements.
        
        Args:
            action: Action that was completed
            details: Success details
            
        Returns:
            Success message with visual elements
        """
        success_message = f"✅ **{MessageFormatter.escape_markdown(action)}**\n\n"
        success_message += "🎉 Successfully completed!\n\n"
        
        if details:
            success_message += "📋 **Details:**\n"
            for key, value in details.items():
                safe_key = MessageFormatter.escape_markdown(str(key))
                safe_value = MessageFormatter.escape_markdown(str(value))
                success_message += f"   • {safe_key}: {safe_value}\n"
        
        return success_message
    
    @staticmethod
    def show_progress_bar(current: int, total: int, label: str, width: int = 20) -> str:
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
            return f"📊 **{MessageFormatter.escape_markdown(label)}**\n\nNo progress data available."
        
        percentage = (current / total) * 100
        filled_width = int((current / total) * width)
        
        progress_bar = "█" * filled_width + "░" * (width - filled_width)
        
        message = f"📊 **{MessageFormatter.escape_markdown(label)}**\n\n"
        message += f"`{progress_bar}` {percentage:.1f}%\n"
        message += f"Progress: {current}/{total}"
        
        return message
    
    @staticmethod
    def show_confirmation_dialog(
        action: str, 
        details: dict, 
        risk_level: str = "low"
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Show enhanced confirmation dialogs.
        
        Args:
            action: Action to confirm
            details: Action details
            risk_level: Risk level (low, medium, high)
            
        Returns:
            Tuple of (message, keyboard)
        """
        # Risk level indicators
        risk_indicators = {
            "low": {"icon": "ℹ️", "color": "blue"},
            "medium": {"icon": "⚠️", "color": "yellow"},
            "high": {"icon": "🚨", "color": "red"}
        }
        
        indicator = risk_indicators.get(risk_level, risk_indicators["low"])
        
        message = f"{indicator['icon']} **Confirm {MessageFormatter.escape_markdown(action)}**\n\n"
        
        if details:
            message += "📋 **Details:**\n"
            for key, value in details.items():
                safe_key = MessageFormatter.escape_markdown(str(key))
                safe_value = MessageFormatter.escape_markdown(str(value))
                message += f"   • {safe_key}: {safe_value}\n"
            message += "\n"
        
        message += "Are you sure you want to proceed?"
        
        # Confirmation keyboard
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{action}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
            ]
        ])
        
        return message, keyboard


class EnhancedUXSystem:
    """Main enhanced UX system that coordinates all components."""
    
    def __init__(self):
        self.layout_builder = MessageLayoutBuilder()
        self.navigation_helper = SmartNavigationHelper()
        self.error_recovery_helper = ErrorRecoveryHelper()
        self.feedback_system = VisualFeedbackSystem()
    
    def enhance_message(
        self, 
        message: str, 
        context: dict, 
        user_id: int = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
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
        
        # Add breadcrumb navigation if enabled
        if context.get('navigation_path'):
            enhanced_message = self.navigation_helper.add_breadcrumb_navigation(
                enhanced_message, context['navigation_path']
            )
        
        # Build contextual keyboard
        available_actions = context.get('available_actions', [])
        keyboard = self.navigation_helper.build_contextual_keyboard(
            context.get('current_context', ''),
            available_actions,
            context.get('user_history', [])
        )
        
        return enhanced_message, keyboard
    
    def create_error_response(
        self, 
        error_type: str, 
        error_message: str, 
        context: dict
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Create enhanced error response with recovery options.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Error context
            
        Returns:
            Tuple of (error_message, recovery_keyboard)
        """
        # Format error message
        formatted_error = MessageFormatter.format_error_message(error_message)
        
        # Add contextual help
        help_message = self.error_recovery_helper.provide_contextual_help({
            'type': error_type,
            'message': error_message
        })
        
        full_message = formatted_error + "\n\n" + help_message
        
        # Build recovery keyboard
        keyboard = self.error_recovery_helper.build_error_recovery_keyboard(
            error_type, context
        )
        
        return full_message, keyboard 