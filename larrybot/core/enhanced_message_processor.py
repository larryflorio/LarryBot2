"""
Enhanced Message Processor for LarryBot2

This module provides enhanced message processing with UX improvements
including better layouts, smart navigation, and error recovery.
"""
from typing import Dict, Any, Tuple, Optional
from telegram import InlineKeyboardMarkup
from larrybot.utils.enhanced_ux_helpers import EnhancedUXSystem
from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
from larrybot.config.ux_config import UXConfig
from larrybot.utils.ux_helpers import MessageFormatter
import logging
logger = logging.getLogger(__name__)


class EnhancedMessageProcessor:
    """Enhanced message processing with UX improvements."""

    def __init__(self):
        self.ux_system = EnhancedUXSystem()
        self._navigation_cache = {}

    async def process_message(self, message: str, context: Dict[str, Any],
        user_id: Optional[int]=None) ->Tuple[str, InlineKeyboardMarkup]:
        """
        Process message with UX enhancements.
        
        Args:
            message: Original message
            context: Message context
            user_id: User ID for personalization
            
        Returns:
            Tuple of (enhanced_message, keyboard)
        """
        try:
            enhanced_message = message
            if UXConfig.is_feature_enabled('enhanced_layouts'):
                enhanced_message = self._apply_enhanced_layout(enhanced_message
                    , context)
            if UXConfig.is_feature_enabled('breadcrumbs') and context.get(
                'navigation_path'):
                enhanced_message = (self.ux_system.navigation_helper.
                    add_breadcrumb_navigation(enhanced_message, context[
                    'navigation_path']))
            keyboard = self._build_smart_keyboard(context, user_id)
            return enhanced_message, keyboard
        except Exception as e:
            logger.error(f'Error in enhanced message processing: {e}')
            return message, self._build_fallback_keyboard(context)

    def _apply_enhanced_layout(self, message: str, context: Dict[str, Any]
        ) ->str:
        """
        Apply enhanced layout improvements to the message.
        
        Args:
            message: Original message
            context: Message context
            
        Returns:
            Enhanced message
        """
        if 'tasks' in context or 'task' in context:
            return self._enhance_task_message(message, context)
        if 'clients' in context or 'client' in context:
            return self._enhance_client_message(message, context)
        if 'habits' in context or 'habit' in context:
            return self._enhance_habit_message(message, context)
        if 'analytics' in context or 'statistics' in context:
            return self._enhance_analytics_message(message, context)
        return message

    def _enhance_task_message(self, message: str, context: Dict[str, Any]
        ) ->str:
        """Enhance task-related messages with better formatting."""
        if 'tasks' in context and isinstance(context['tasks'], list):
            tasks = context['tasks']
            if UXConfig.is_feature_enabled('progressive_lists'):
                return self.ux_system.layout_builder.build_progressive_list(
                    tasks, UXConfig.MAX_ITEMS_PER_PAGE, 'Tasks')
        return message

    def _enhance_client_message(self, message: str, context: Dict[str, Any]
        ) ->str:
        """Enhance client-related messages with better formatting."""
        if 'clients' in context and isinstance(context['clients'], list):
            clients = context['clients']
            if UXConfig.is_feature_enabled('progressive_lists'):
                return self.ux_system.layout_builder.build_progressive_list(
                    clients, UXConfig.MAX_ITEMS_PER_PAGE, 'Clients')
        return message

    def _enhance_habit_message(self, message: str, context: Dict[str, Any]
        ) ->str:
        """Enhance habit-related messages with better formatting."""
        if 'habits' in context and isinstance(context['habits'], list):
            habits = context['habits']
            if UXConfig.is_feature_enabled('progressive_lists'):
                return self.ux_system.layout_builder.build_progressive_list(
                    habits, UXConfig.MAX_ITEMS_PER_PAGE, 'Habits')
        return message

    def _enhance_analytics_message(self, message: str, context: Dict[str, Any]
        ) ->str:
        """Enhance analytics messages with better formatting."""
        if 'analytics' in context and isinstance(context['analytics'], dict):
            analytics = context['analytics']
            if UXConfig.is_feature_enabled('info_cards'):
                return self.ux_system.layout_builder.build_summary_card(
                    'Analytics Summary', analytics)
        return message

    def _build_smart_keyboard(self, context: Dict[str, Any], user_id:
        Optional[int]=None) ->InlineKeyboardMarkup:
        """
        Build smart navigation keyboard based on context.
        
        Args:
            context: Message context
            user_id: User ID for personalization
            
        Returns:
            Smart navigation keyboard
        """
        if not UXConfig.is_feature_enabled('contextual_keyboards'):
            return self._build_fallback_keyboard(context)
        current_context = context.get('current_context', 'main')
        available_actions = self._get_available_actions(current_context,
            context)
        return self.ux_system.navigation_helper.build_contextual_keyboard(
            current_context, available_actions, context.get('user_history', [])
            )

    def _get_available_actions(self, current_context: str, context: Dict[
        str, Any]) ->list:
        """
        Get available actions based on current context.
        
        Args:
            current_context: Current user context
            context: Full context information
            
        Returns:
            List of available actions
        """
        actions = []
        if current_context == 'main':
            actions = [{'text': '📋 Tasks', 'callback_data': 'menu_tasks',
                'type': 'primary'}, {'text': '👥 Clients', 'callback_data':
                'menu_clients', 'type': 'primary'}, {'text': '🔄 Habits',
                'callback_data': 'menu_habits', 'type': 'primary'}, {'text':
                '📊 Analytics', 'callback_data': 'menu_analytics', 'type':
                'secondary'}, {'text': '⏰ Reminders', 'callback_data':
                'menu_reminders', 'type': 'secondary'}]
        elif current_context == 'tasks':
            actions = [{'text': '➕ Add Task', 'callback_data': 'add_task',
                'type': 'primary'}, {'text': '🔄 Refresh', 'callback_data':
                'tasks_refresh', 'type': 'primary'}, {'text': '🔍 Search',
                'callback_data': 'tasks_search', 'type': 'secondary'}, {
                'text': '📊 Analytics', 'callback_data': 'tasks_analytics',
                'type': 'secondary'}, {'text': '🏠 Main Menu',
                'callback_data': 'nav_main', 'type': 'navigation'}]
        elif current_context == 'clients':
            actions = [{'text': '➕ Add Client', 'callback_data':
                'add_client', 'type': 'primary'}, {'text': '🔄 Refresh',
                'callback_data': 'clients_refresh', 'type': 'primary'}, {
                'text': '📊 Analytics', 'callback_data': 'clients_analytics',
                'type': 'secondary'}, {'text': '🏠 Main Menu',
                'callback_data': 'nav_main', 'type': 'navigation'}]
        elif current_context == 'habits':
            actions = [{'text': '➕ Add Habit', 'callback_data': 'add_habit',
                'type': 'primary'}, {'text': '🔄 Refresh', 'callback_data':
                'habit_refresh', 'type': 'primary'}, {'text':
                '📊 Statistics', 'callback_data': 'habit_stats', 'type':
                'secondary'}, {'text': '🏠 Main Menu', 'callback_data':
                'nav_main', 'type': 'navigation'}]
        elif current_context == 'analytics':
            actions = [{'text': '📊 Basic', 'callback_data':
                'analytics_basic', 'type': 'primary'}, {'text':
                '📈 Detailed', 'callback_data': 'analytics_detailed', 'type':
                'primary'}, {'text': '🚀 Advanced', 'callback_data':
                'analytics_advanced', 'type': 'secondary'}, {'text':
                '🏠 Main Menu', 'callback_data': 'nav_main', 'type':
                'navigation'}]
        if 'entity_type' in context and 'entity_id' in context:
            quick_actions = self._get_quick_actions(context['entity_type'],
                context['entity_id'])
            actions.extend(quick_actions)
        return actions

    def _get_quick_actions(self, entity_type: str, entity_id: int) ->list:
        """
        Get quick actions for specific entity types.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            
        Returns:
            List of quick actions
        """
        quick_actions = {'task': [{'text': '✅ Done', 'callback_data':
            f'task_done:{entity_id}', 'type': 'primary'}, {'text':
            '✏️ Edit', 'callback_data': f'task_edit:{entity_id}', 'type':
            'secondary'}, {'text': '🗑️ Delete', 'callback_data':
            f'task_delete:{entity_id}', 'type': 'secondary'}], 'client': [{
            'text': '📋 Tasks', 'callback_data': f'client_tasks:{entity_id}',
            'type': 'primary'}, {'text': '📊 Analytics', 'callback_data':
            f'client_analytics:{entity_id}', 'type': 'secondary'}, {'text':
            '🗑️ Delete', 'callback_data': f'client_delete:{entity_id}',
            'type': 'secondary'}], 'habit': [{'text': '✅ Complete',
            'callback_data': f'habit_done:{entity_id}', 'type': 'primary'},
            {'text': '📊 Progress', 'callback_data':
            f'habit_progress:{entity_id}', 'type': 'secondary'}, {'text':
            '🗑️ Delete', 'callback_data': f'habit_delete:{entity_id}',
            'type': 'secondary'}]}
        return quick_actions.get(entity_type, [])

    def _build_fallback_keyboard(self, context: Dict[str, Any]
        ) ->InlineKeyboardMarkup:
        """
        Build fallback keyboard when enhanced features are disabled.
        
        Args:
            context: Message context
            
        Returns:
            Fallback keyboard
        """
        from larrybot.utils.ux_helpers import NavigationHelper
        return NavigationHelper.get_main_menu_keyboard()

    def create_error_response(self, error_type: str, error_message: str,
        context: Dict[str, Any]) ->Tuple[str, InlineKeyboardMarkup]:
        """
        Create enhanced error response with recovery options.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Error context
            
        Returns:
            Tuple of (error_message, recovery_keyboard)
        """
        if not UXConfig.is_feature_enabled('error_recovery'):
            formatted_error = MessageFormatter.format_error_message(
                error_message)
            return formatted_error, self._build_fallback_keyboard(context)
        return self.ux_system.create_error_response(error_type,
            error_message, context)

    def create_loading_message(self, operation: str, estimated_time: float=None
        ) ->str:
        """
        Create enhanced loading message.
        
        Args:
            operation: Operation being performed
            estimated_time: Estimated time in seconds
            
        Returns:
            Loading message
        """
        if not UXConfig.is_feature_enabled('loading_indicators'):
            return f'⏳ {operation}...'
        return self.ux_system.feedback_system.show_loading_state(operation,
            estimated_time)

    def create_success_message(self, action: str, details: Dict[str, Any]
        ) ->str:
        """
        Create enhanced success message.
        
        Args:
            action: Action that was completed
            details: Success details
            
        Returns:
            Success message
        """
        if not UXConfig.is_feature_enabled('success_animations'):
            return MessageFormatter.format_success_message(action, details)
        return self.ux_system.feedback_system.show_success_animation(action,
            details)

    def create_confirmation_dialog(self, action: str, details: Dict[str,
        Any], risk_level: str='low') ->Tuple[str, InlineKeyboardMarkup]:
        """
        Create enhanced confirmation dialog.
        
        Args:
            action: Action to confirm
            details: Action details
            risk_level: Risk level
            
        Returns:
            Tuple of (message, keyboard)
        """
        if not UXConfig.is_feature_enabled('enhanced_confirmations'):
            message = f'Are you sure you want to {action}?'
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([[UnifiedButtonBuilder.
                create_button(text='✅ Yes', callback_data=
                f'confirm_{action}', button_type=ButtonType.INFO),
                UnifiedButtonBuilder.create_button(text='❌ No',
                callback_data='cancel_action', button_type=ButtonType.INFO)]])
            return message, keyboard
        return self.ux_system.feedback_system.show_confirmation_dialog(action,
            details, risk_level)
