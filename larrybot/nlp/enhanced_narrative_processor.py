"""
Enhanced Narrative Input Processor for LarryBot2

This module provides advanced natural language processing capabilities for
conversational task management, including context-aware responses and smart defaults.
"""
import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from larrybot.nlp.intent_recognizer import IntentRecognizer
from larrybot.nlp.entity_extractor import EntityExtractor
from larrybot.nlp.sentiment_analyzer import SentimentAnalyzer
logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Enhanced intent types for narrative input processing."""
    CREATE_TASK = 'create_task'
    EDIT_TASK = 'edit_task'
    COMPLETE_TASK = 'complete_task'
    DELETE_TASK = 'delete_task'
    LIST_TASKS = 'list_tasks'
    SEARCH_TASKS = 'search_tasks'
    SET_REMINDER = 'set_reminder'
    GET_ANALYTICS = 'get_analytics'
    ADD_HABIT = 'add_habit'
    COMPLETE_HABIT = 'complete_habit'
    ADD_CLIENT = 'add_client'
    UNKNOWN = 'unknown'


class TaskCreationState(Enum):
    """States for the narrative task creation flow."""
    AWAITING_DESCRIPTION = 'awaiting_description'
    AWAITING_DUE_DATE = 'awaiting_due_date'
    AWAITING_PRIORITY = 'awaiting_priority'
    AWAITING_CATEGORY = 'awaiting_category'
    AWAITING_CLIENT = 'awaiting_client'
    CONFIRMATION = 'confirmation'


class ContextType(Enum):
    """Context types for narrative processing."""
    TASK_CREATION = 'task_creation'
    TASK_EDITING = 'task_editing'
    TASK_SELECTION = 'task_selection'
    HABIT_TRACKING = 'habit_tracking'
    CLIENT_MANAGEMENT = 'client_management'
    ANALYTICS_VIEWING = 'analytics_viewing'
    GENERAL = 'general'


@dataclass
class NarrativeContext:
    """Context information for narrative input processing."""
    current_intent: IntentType
    context_type: ContextType
    entities: Dict[str, Any]
    sentiment: str
    confidence: float
    suggested_actions: List[str]
    follow_up_questions: List[str]
    user_history: List[Dict[str, Any]]
    conversation_state: Dict[str, Any]


@dataclass
class ProcessedInput:
    """Result of narrative input processing."""
    intent: IntentType
    entities: Dict[str, Any]
    confidence: float
    suggested_command: Optional[str]
    suggested_parameters: Dict[str, Any]
    context: NarrativeContext
    response_message: str
    response_keyboard: Optional[Any] = None


class SmartDefaults:
    """Smart default values based on user patterns and context."""

    def __init__(self):
        self.user_patterns = {}
        self.default_priorities = {'urgent': ['urgent', 'asap', 'emergency',
            'critical'], 'high': ['high priority', 'important', 'high'],
            'medium': ['medium', 'normal', 'standard'], 'low': ['low',
            'minor', 'optional', 'when possible']}
        self.default_categories = {'work': ['work', 'job', 'office',
            'business', 'project', 'meeting'], 'personal': ['personal',
            'home', 'family', 'life', 'private'], 'health': ['health',
            'exercise', 'fitness', 'medical', 'doctor'], 'learning': [
            'study', 'learn', 'course', 'training', 'education'], 'finance':
            ['money', 'finance', 'bills', 'budget', 'expenses']}

    def suggest_priority(self, text: str) ->str:
        """Suggest priority based on text content."""
        text_lower = text.lower()
        priority_checks = [('urgent', self.default_priorities['urgent']), (
            'high', self.default_priorities['high']), ('medium', self.
            default_priorities['medium']), ('low', self.default_priorities[
            'low'])]
        for priority, keywords in priority_checks:
            if any(keyword in text_lower for keyword in keywords):
                return priority.title()
        return 'Medium'

    def suggest_category(self, text: str) ->Optional[str]:
        """Suggest category based on text content."""
        text_lower = text.lower()
        for category, keywords in self.default_categories.items():
            if any(keyword in text_lower for keyword in keywords):
                return category.title()
        return None

    def suggest_due_date(self, text: str, entities: Dict[str, Any]) ->Optional[
        str]:
        """Suggest due date based on text and extracted entities."""
        if 'date' in entities:
            return entities['date']
        text_lower = text.lower()
        date_patterns = {'today': datetime.now().strftime('%Y-%m-%d'),
            'tomorrow': (datetime.now() + timedelta(days=1)).strftime(
            '%Y-%m-%d'), 'next week': (datetime.now() + timedelta(days=7)).
            strftime('%Y-%m-%d'), 'this week': (datetime.now() + timedelta(
            days=3)).strftime('%Y-%m-%d'), 'next month': (datetime.now() +
            timedelta(days=30)).strftime('%Y-%m-%d')}
        for pattern, date in date_patterns.items():
            if pattern in text_lower:
                return date
        return None


class ConversationManager:
    """Manages conversation flow and context."""

    def __init__(self):
        self.conversation_states = {}
        self.user_history = {}

    def get_context(self, user_id: int) ->NarrativeContext:
        """Get current conversation context for user."""
        if user_id not in self.conversation_states:
            return NarrativeContext(current_intent=IntentType.UNKNOWN,
                context_type=ContextType.GENERAL, entities={}, sentiment=
                'neutral', confidence=0.0, suggested_actions=[],
                follow_up_questions=[], user_history=[], conversation_state={})
        return self.conversation_states[user_id]

    def update_context(self, user_id: int, context: NarrativeContext) ->None:
        """Update conversation context for user."""
        self.conversation_states[user_id] = context
        if len(context.user_history) > 10:
            context.user_history = context.user_history[-10:]

    def add_to_history(self, user_id: int, interaction: Dict[str, Any]) ->None:
        """Add interaction to user history."""
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        self.user_history[user_id].append({**interaction, 'timestamp':
            datetime.now().isoformat()})
        if len(self.user_history[user_id]) > 20:
            self.user_history[user_id] = self.user_history[user_id][-20:]
        if user_id in self.conversation_states:
            self.conversation_states[user_id].user_history = self.user_history[
                user_id].copy()
        else:
            self.conversation_states[user_id] = NarrativeContext(current_intent
                =IntentType.UNKNOWN, context_type=ContextType.GENERAL,
                entities={}, sentiment='neutral', confidence=0.0,
                suggested_actions=[], follow_up_questions=[], user_history=
                self.user_history[user_id].copy(), conversation_state={})


class EnhancedNarrativeProcessor:
    """
    Enhanced narrative input processor for conversational task management.
    
    This class provides natural language task creation, context-aware responses,
    and smart defaults based on user patterns and conversation context.
    """

    def __init__(self, config=None):
        self.intent_recognizer = IntentRecognizer(config)
        self.entity_extractor = EntityExtractor(config)
        self.sentiment_analyzer = SentimentAnalyzer(config)
        self.smart_defaults = SmartDefaults()
        self.conversation_manager = ConversationManager()
        self.intent_patterns = {IntentType.SET_REMINDER: [
            'remind\\s+me\\s+to\\s+(.+)'], IntentType.LIST_TASKS: [
            'show\\s+(?:my\\s+)?tasks', 'list\\s+(?:my\\s+)?tasks',
            'what\\s+(?:are\\s+)?(?:my\\s+)?tasks', 'tasks\\s+list',
            'my\\s+tasks'], IntentType.SEARCH_TASKS: [
            'search\\s+(?:for\\s+)?(.+)',
            'find\\s+(?:tasks\\s+)?(?:about\\s+)?(.+)',
            'look\\s+for\\s+(.+)'], IntentType.COMPLETE_TASK: [
            'done\\s+(?:with\\s+)?(.+)', 'completed\\s+(.+)',
            'finished\\s+(.+)', 'mark\\s+(.+)\\s+as\\s+done',
            'complete\\s+(.+)', 'finish\\s+(.+)'], IntentType.EDIT_TASK: [
            'edit\\s+(.+)', 'change\\s+(.+)', 'update\\s+(.+)',
            'modify\\s+(.+)'], IntentType.DELETE_TASK: ['delete\\s+(.+)',
            'remove\\s+(.+)', 'cancel\\s+(.+)'], IntentType.ADD_HABIT: [
            'add\\s+(?:a\\s+)?habit\\s+(?:to\\s+)?(.+)',
            'new\\s+habit\\s+(?:to\\s+)?(.+)',
            'start\\s+(?:a\\s+)?habit\\s+(?:to\\s+)?(.+)', 'track\\s+(.+)'],
            IntentType.COMPLETE_HABIT: ['habit\\s+done\\s+(.+)',
            'completed\\s+habit\\s+(.+)', 'did\\s+(.+)'], IntentType.
            CREATE_TASK: ['add\\s+(?:a\\s+)?task\\s+(?:to\\s+)?(.+)',
            'create\\s+(?:a\\s+)?task\\s+(?:to\\s+)?(.+)',
            'new\\s+task\\s+(?:to\\s+)?(.+)', 'todo\\s+(?:to\\s+)?(.+)',
            'remind\\s+me\\s+to\\s+(.+)', 'i\\s+need\\s+to\\s+(.+)',
            'i\\s+should\\s+(.+)', 'i\\s+want\\s+to\\s+(.+)',
            '(.+)\\s+(?:is\\s+)?(?:a\\s+)?task']}

    def process_input(self, text: str, user_id: int=None) ->ProcessedInput:
        """
        Process natural language input and return structured result.
        
        Args:
            text: User input text
            user_id: User ID for context management
            
        Returns:
            ProcessedInput with intent, entities, and suggested actions
        """
        if text is None:
            return self._create_unknown_result('Empty input')
        text = text.strip()
        if not text:
            return self._create_unknown_result('Empty input')
        context = self.conversation_manager.get_context(user_id
            ) if user_id else None
        intent, confidence, extracted_text = self._recognize_intent_enhanced(
            text)
        entities = self.entity_extractor.extract_entities(text)
        sentiment = self.sentiment_analyzer.analyze_sentiment(text)
        entities = self._apply_smart_defaults(text, entities, context)
        suggested_command, suggested_parameters = self._generate_suggestions(
            intent, entities, text, context)
        response_message = self._generate_response_message(intent, entities,
            suggested_parameters, context)
        if user_id and context:
            self._update_conversation_context(user_id, intent, entities,
                sentiment, context)
        result_context = context or self._create_default_context()
        result_context.sentiment = sentiment
        return ProcessedInput(intent=intent, entities=entities, confidence=
            confidence, suggested_command=suggested_command,
            suggested_parameters=suggested_parameters, context=
            result_context, response_message=response_message)

    def _recognize_intent_enhanced(self, text: str) ->Tuple[IntentType,
        float, Optional[str]]:
        """Enhanced intent recognition using pattern matching."""
        text_lower = text.lower()
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    extracted_text = match.group(1) if len(match.groups()
                        ) > 0 else None
                    if intent_type in [IntentType.LIST_TASKS, IntentType.
                        SEARCH_TASKS, IntentType.GET_ANALYTICS]:
                        confidence = 0.71
                    else:
                        confidence = 0.9 if len(match.group(0)) > 10 else 0.7
                    return intent_type, confidence, extracted_text
        basic_intent = self.intent_recognizer.recognize_intent(text)
        intent_mapping = {'create_task': IntentType.CREATE_TASK,
            'set_reminder': IntentType.SET_REMINDER, 'get_analytics':
            IntentType.GET_ANALYTICS, 'edit_task': IntentType.EDIT_TASK}
        intent_type = intent_mapping.get(basic_intent, IntentType.UNKNOWN)
        confidence = 0.51 if basic_intent != 'unknown' else 0.1
        return intent_type, confidence, None

    def _apply_smart_defaults(self, text: str, entities: Dict[str, Any],
        context: NarrativeContext) ->Dict[str, Any]:
        """Apply smart defaults based on text content and context."""
        enhanced_entities = entities.copy()
        if 'priority' not in enhanced_entities:
            suggested_priority = self.smart_defaults.suggest_priority(text)
            if suggested_priority != 'Medium':
                enhanced_entities['suggested_priority'] = suggested_priority
        if 'category' not in enhanced_entities:
            suggested_category = self.smart_defaults.suggest_category(text)
            if suggested_category:
                enhanced_entities['suggested_category'] = suggested_category
        if 'date' not in enhanced_entities:
            suggested_date = self.smart_defaults.suggest_due_date(text,
                entities)
            if suggested_date:
                if 'T' in suggested_date:
                    suggested_date = suggested_date.split('T')[0]
                enhanced_entities['suggested_date'] = suggested_date
        elif 'date' in enhanced_entities and 'suggested_date' not in enhanced_entities:
            suggested_date = enhanced_entities['date']
            if 'T' in suggested_date:
                suggested_date = suggested_date.split('T')[0]
            enhanced_entities['suggested_date'] = suggested_date
        return enhanced_entities

    def _generate_suggestions(self, intent: IntentType, entities: Dict[str,
        Any], text: str, context: NarrativeContext) ->Tuple[Optional[str],
        Dict[str, Any]]:
        """Generate suggested command and parameters."""
        if intent == IntentType.CREATE_TASK:
            return self._suggest_task_creation(entities, text)
        elif intent == IntentType.COMPLETE_TASK:
            return self._suggest_task_completion(entities, text)
        elif intent == IntentType.EDIT_TASK:
            return self._suggest_task_editing(entities, text)
        elif intent == IntentType.DELETE_TASK:
            return self._suggest_task_deletion(entities, text)
        elif intent == IntentType.LIST_TASKS:
            return self._suggest_task_listing(entities)
        elif intent == IntentType.SEARCH_TASKS:
            return self._suggest_task_search(entities, text)
        elif intent == IntentType.ADD_HABIT:
            return self._suggest_habit_creation(entities, text)
        elif intent == IntentType.COMPLETE_HABIT:
            return self._suggest_habit_completion(entities, text)
        return None, {}

    def _suggest_task_creation(self, entities: Dict[str, Any], text: str
        ) ->Tuple[str, Dict[str, Any]]:
        """Suggest task creation command and parameters."""
        task_name = entities.get('task_name', text)
        params = {'description': task_name, 'priority': entities.get(
            'suggested_priority', 'Medium'), 'category': entities.get(
            'suggested_category'), 'due_date': entities.get('suggested_date')}
        params = {k: v for k, v in params.items() if v is not None}
        return '/add', params

    def _suggest_task_completion(self, entities: Dict[str, Any], text: str
        ) ->Tuple[str, Dict[str, Any]]:
        """Suggest task completion command and parameters."""
        return '/done', {'task_description': entities.get('task_name', text)}

    def _suggest_task_editing(self, entities: Dict[str, Any], text: str
        ) ->Tuple[str, Dict[str, Any]]:
        """Suggest task editing command and parameters."""
        return '/edit', {'task_description': entities.get('task_name', text)}

    def _suggest_task_deletion(self, entities: Dict[str, Any], text: str
        ) ->Tuple[str, Dict[str, Any]]:
        """Suggest task deletion command and parameters."""
        return '/done', {'task_description': entities.get('task_name', text)}

    def _suggest_task_listing(self, entities: Dict[str, Any]) ->Tuple[str,
        Dict[str, Any]]:
        """Suggest task listing command and parameters."""
        params = {}
        if entities.get('suggested_priority'):
            params['priority'] = entities['suggested_priority']
        if entities.get('suggested_category'):
            params['category'] = entities['suggested_category']
        return '/list', params

    def _suggest_task_search(self, entities: Dict[str, Any], text: str
        ) ->Tuple[str, Dict[str, Any]]:
        """Suggest task search command and parameters."""
        search_term = entities.get('task_name', text)
        return '/search', {'query': search_term}

    def _suggest_habit_creation(self, entities: Dict[str, Any], text: str
        ) ->Tuple[str, Dict[str, Any]]:
        """Suggest habit creation command and parameters."""
        habit_name = entities.get('task_name', text)
        return '/habit_add', {'name': habit_name}

    def _suggest_habit_completion(self, entities: Dict[str, Any], text: str
        ) ->Tuple[str, Dict[str, Any]]:
        """Suggest habit completion command and parameters."""
        habit_name = entities.get('task_name', text)
        return '/habit_done', {'name': habit_name}

    def _generate_response_message(self, intent: IntentType, entities: Dict
        [str, Any], suggested_parameters: Dict[str, Any], context:
        NarrativeContext) ->str:
        """Generate response message based on intent and entities."""
        from larrybot.utils.ux_helpers import MessageFormatter
        if intent == IntentType.CREATE_TASK:
            return self._generate_task_creation_response(entities,
                suggested_parameters)
        elif intent == IntentType.COMPLETE_TASK:
            return self._generate_task_completion_response(entities)
        elif intent == IntentType.LIST_TASKS:
            return self._generate_task_listing_response(entities)
        elif intent == IntentType.SEARCH_TASKS:
            return self._generate_task_search_response(entities)
        elif intent == IntentType.ADD_HABIT:
            return self._generate_habit_creation_response(entities)
        elif intent == IntentType.SET_REMINDER:
            reminder_text = entities.get('task_name', 'this reminder')
            due = entities.get('suggested_date')
            escaped_reminder = MessageFormatter.escape_markdown(reminder_text)
            response = f"⏰ I'll remind you to '{escaped_reminder}'"
            if due:
                escaped_due = MessageFormatter.escape_markdown(str(due))
                response += f' on {escaped_due}'
            response += (
                '.\n\n💡 **Suggested command:**\n`/remind {escaped_reminder}`')
            return response
        elif intent == IntentType.GET_ANALYTICS:
            return """📊 I'll show you your analytics and stats.

💡 **Suggested command:**
`/analytics`"""
        elif intent == IntentType.UNKNOWN:
            return self._generate_unknown_response()
        return 'I understand you want to work with tasks. How can I help you?'

    def _generate_task_creation_response(self, entities: Dict[str, Any],
        suggested_parameters: Dict[str, Any]) ->str:
        """Generate response for task creation."""
        from larrybot.utils.ux_helpers import MessageFormatter
        task_name = entities.get('task_name', 'this task')
        escaped_task_name = MessageFormatter.escape_markdown(task_name)
        response = f"✅ I'll create a task for '{escaped_task_name}'"
        suggestions = []
        if 'suggested_priority' in entities:
            priority = MessageFormatter.escape_markdown(str(entities[
                'suggested_priority']))
            suggestions.append(f'priority: {priority}')
        if 'suggested_category' in entities:
            category = MessageFormatter.escape_markdown(str(entities[
                'suggested_category']))
            suggestions.append(f'category: {category}')
        if 'suggested_date' in entities:
            date = MessageFormatter.escape_markdown(str(entities[
                'suggested_date']))
            suggestions.append(f'due: {date}')
        if suggestions:
            response += f" with {', '.join(suggestions)}"
        response += '\\.\n\n💡 **Suggested command:**\n'
        escaped_description = MessageFormatter.escape_markdown(str(
            suggested_parameters.get('description', task_name)))
        response += f'`{escaped_description}`'
        return response

    def _generate_task_completion_response(self, entities: Dict[str, Any]
        ) ->str:
        """Generate response for task completion."""
        from larrybot.utils.ux_helpers import MessageFormatter
        task_name = entities.get('task_name', 'this task')
        escaped_task_name = MessageFormatter.escape_markdown(task_name)
        return f"""✅ I'll mark '{escaped_task_name}' as complete.

💡 **Suggested command:**
`/done <task_id>`"""

    def _generate_task_listing_response(self, entities: Dict[str, Any]) ->str:
        """Generate response for task listing."""
        from larrybot.utils.ux_helpers import MessageFormatter
        response = "📋 I'll show you your tasks"
        if entities.get('suggested_priority') or entities.get(
            'suggested_category'):
            filters = []
            if entities.get('suggested_priority'):
                priority = MessageFormatter.escape_markdown(str(entities[
                    'suggested_priority']))
                filters.append(f'priority: {priority}')
            if entities.get('suggested_category'):
                category = MessageFormatter.escape_markdown(str(entities[
                    'suggested_category']))
                filters.append(f'category: {category}')
            response += f" filtered by {', '.join(filters)}"
        response += '.\n\n💡 **Suggested command:**\n`/list`'
        return response

    def _generate_task_search_response(self, entities: Dict[str, Any]) ->str:
        """Generate response for task search."""
        from larrybot.utils.ux_helpers import MessageFormatter
        search_term = entities.get('task_name', 'your search')
        escaped_search_term = MessageFormatter.escape_markdown(search_term)
        return f"""🔍 I'll search for tasks related to '{escaped_search_term}'.

💡 **Suggested command:**
`/search {escaped_search_term}`"""

    def _generate_habit_creation_response(self, entities: Dict[str, Any]
        ) ->str:
        """Generate response for habit creation."""
        from larrybot.utils.ux_helpers import MessageFormatter
        habit_name = entities.get('task_name', 'this habit')
        escaped_habit_name = MessageFormatter.escape_markdown(habit_name)
        return f"""🔄 I'll create a habit for '{escaped_habit_name}'.

💡 **Suggested command:**
`/habit_add {escaped_habit_name}`"""

    def _generate_unknown_response(self) ->str:
        """Generate response for unknown intent."""
        from larrybot.utils.ux_helpers import MessageFormatter
        
        # Content with proper escaping for MarkdownV2
        content = """🤔 I'm not sure what you'd like to do\\. Here are some examples:

• "Add a task to review the quarterly report"
• "Remind me to call the client tomorrow"  
• "Show me my high priority tasks"
• "Mark the project review as done"

💡 You can also use commands like `/add`, `/list`, `/search`, etc\\."""
        
        return content

    def _update_conversation_context(self, user_id: int, intent: IntentType,
        entities: Dict[str, Any], sentiment: str, context: NarrativeContext
        ) ->None:
        """Update conversation context for the user."""
        context.current_intent = intent
        context.entities = entities
        context.sentiment = sentiment
        self.conversation_manager.add_to_history(user_id, {'intent': intent
            .value, 'entities': entities, 'sentiment': sentiment})
        self.conversation_manager.update_context(user_id, context)

    def _create_default_context(self) ->NarrativeContext:
        """Create default context for users without conversation history."""
        return NarrativeContext(current_intent=IntentType.UNKNOWN,
            context_type=ContextType.GENERAL, entities={}, sentiment=
            'neutral', confidence=0.0, suggested_actions=[],
            follow_up_questions=[], user_history=[], conversation_state={})

    def _create_unknown_result(self, reason: str) ->ProcessedInput:
        """Create result for unknown/unprocessable input."""
        from larrybot.utils.ux_helpers import MessageFormatter
        escaped_reason = MessageFormatter.escape_markdown(reason)
        return ProcessedInput(intent=IntentType.UNKNOWN, entities={},
            confidence=0.0, suggested_command=None, suggested_parameters={},
            context=self._create_default_context(), response_message=
            f'Unable to process input: {escaped_reason}')


__all__ = ['EnhancedNarrativeProcessor', 'IntentType', 'ContextType',
    'NarrativeContext', 'ProcessedInput', 'SmartDefaults',
    'ConversationManager']
