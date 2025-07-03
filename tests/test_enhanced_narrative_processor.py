"""
Comprehensive tests for the Enhanced Narrative Input Processor.

Tests cover intent recognition, entity extraction, smart defaults,
conversation management, and response generation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from larrybot.nlp.enhanced_narrative_processor import (
    EnhancedNarrativeProcessor,
    IntentType,
    ContextType,
    NarrativeContext,
    ProcessedInput,
    SmartDefaults,
    ConversationManager
)


class TestSmartDefaults:
    """Test smart default suggestions."""
    
    def setup_method(self):
        self.smart_defaults = SmartDefaults()
    
    def test_suggest_priority_urgent(self):
        """Test priority suggestion for urgent tasks."""
        text = "This is an urgent task that needs immediate attention"
        priority = self.smart_defaults.suggest_priority(text)
        assert priority == "Urgent"
    
    def test_suggest_priority_high(self):
        """Test priority suggestion for high priority tasks."""
        text = "This is an important project that needs high priority"
        priority = self.smart_defaults.suggest_priority(text)
        assert priority == "High"
    
    def test_suggest_priority_medium(self):
        """Test priority suggestion for medium priority tasks."""
        text = "This is a normal task with standard priority"
        priority = self.smart_defaults.suggest_priority(text)
        assert priority == "Medium"
    
    def test_suggest_priority_low(self):
        """Test priority suggestion for low priority tasks."""
        text = "This is a minor task that can be done when possible"
        priority = self.smart_defaults.suggest_priority(text)
        assert priority == "Low"
    
    def test_suggest_priority_default(self):
        """Test default priority when no keywords found."""
        text = "This is a regular task without priority indicators"
        priority = self.smart_defaults.suggest_priority(text)
        assert priority == "Medium"
    
    def test_suggest_category_work(self):
        """Test category suggestion for work tasks."""
        text = "I need to work on this project for the office"
        category = self.smart_defaults.suggest_category(text)
        assert category == "Work"
    
    def test_suggest_category_personal(self):
        """Test category suggestion for personal tasks."""
        text = "This is a personal matter for my home life"
        category = self.smart_defaults.suggest_category(text)
        assert category == "Personal"
    
    def test_suggest_category_health(self):
        """Test category suggestion for health tasks."""
        text = "I need to exercise and see the doctor"
        category = self.smart_defaults.suggest_category(text)
        assert category == "Health"
    
    def test_suggest_category_learning(self):
        """Test category suggestion for learning tasks."""
        text = "I need to study and learn this course"
        category = self.smart_defaults.suggest_category(text)
        assert category == "Learning"
    
    def test_suggest_category_finance(self):
        """Test category suggestion for finance tasks."""
        text = "I need to pay bills and manage my budget"
        category = self.smart_defaults.suggest_category(text)
        assert category == "Finance"
    
    def test_suggest_category_none(self):
        """Test category suggestion when no keywords found."""
        text = "This is a generic task without category indicators"
        category = self.smart_defaults.suggest_category(text)
        assert category is None
    
    def test_suggest_due_date_today(self):
        """Test due date suggestion for today."""
        text = "I need to do this today"
        entities = {}
        date = self.smart_defaults.suggest_due_date(text, entities)
        assert date == datetime.now().strftime("%Y-%m-%d")
    
    def test_suggest_due_date_tomorrow(self):
        """Test due date suggestion for tomorrow."""
        text = "I need to do this tomorrow"
        entities = {}
        date = self.smart_defaults.suggest_due_date(text, entities)
        expected_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert date == expected_date
    
    def test_suggest_due_date_next_week(self):
        """Test due date suggestion for next week."""
        text = "I need to do this next week"
        entities = {}
        date = self.smart_defaults.suggest_due_date(text, entities)
        expected_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        assert date == expected_date
    
    def test_suggest_due_date_with_existing_date(self):
        """Test due date suggestion when date already exists in entities."""
        text = "I need to do this"
        entities = {'date': '2024-01-15'}
        date = self.smart_defaults.suggest_due_date(text, entities)
        assert date == '2024-01-15'


class TestConversationManager:
    """Test conversation flow and context management."""
    
    def setup_method(self):
        self.conversation_manager = ConversationManager()
        self.user_id = 12345
    
    def test_get_context_new_user(self):
        """Test getting context for new user."""
        context = self.conversation_manager.get_context(self.user_id)
        assert context.current_intent == IntentType.UNKNOWN
        assert context.context_type == ContextType.GENERAL
        assert context.sentiment == "neutral"
        assert context.confidence == 0.0
    
    def test_update_context(self):
        """Test updating conversation context."""
        context = NarrativeContext(
            current_intent=IntentType.CREATE_TASK,
            context_type=ContextType.TASK_CREATION,
            entities={'task_name': 'test task'},
            sentiment="positive",
            confidence=0.8,
            suggested_actions=[],
            follow_up_questions=[],
            user_history=[],
            conversation_state={}
        )
        
        self.conversation_manager.update_context(self.user_id, context)
        updated_context = self.conversation_manager.get_context(self.user_id)
        
        assert updated_context.current_intent == IntentType.CREATE_TASK
        assert updated_context.context_type == ContextType.TASK_CREATION
        assert updated_context.entities['task_name'] == 'test task'
        assert updated_context.sentiment == "positive"
        assert updated_context.confidence == 0.8
    
    def test_add_to_history(self):
        """Test adding interactions to user history."""
        interaction = {
            'intent': 'create_task',
            'entities': {'task_name': 'test task'},
            'sentiment': 'positive'
        }
        
        self.conversation_manager.add_to_history(self.user_id, interaction)
        
        # Check that history was added
        context = self.conversation_manager.get_context(self.user_id)
        assert len(context.user_history) == 1
        assert context.user_history[0]['intent'] == 'create_task'
        assert 'timestamp' in context.user_history[0]
    
    def test_history_limit(self):
        """Test that history is limited to prevent memory issues."""
        # Add more than 20 interactions
        for i in range(25):
            interaction = {
                'intent': f'task_{i}',
                'entities': {},
                'sentiment': 'neutral'
            }
            self.conversation_manager.add_to_history(self.user_id, interaction)
        
        # Check that only last 20 are kept
        context = self.conversation_manager.get_context(self.user_id)
        assert len(context.user_history) == 20
        assert context.user_history[-1]['intent'] == 'task_24'


class TestEnhancedNarrativeProcessor:
    """Test the main narrative processor functionality."""
    
    def setup_method(self):
        self.processor = EnhancedNarrativeProcessor()
    
    def test_process_input_create_task(self):
        """Test processing input for task creation."""
        text = "Add a task to review the quarterly report"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.CREATE_TASK
        assert result.confidence > 0.7
        assert result.suggested_command == "/add"
        assert "review the quarterly report" in result.suggested_parameters['description']
        assert "I'll create a task" in result.response_message
    
    def test_process_input_complete_task(self):
        """Test processing input for task completion."""
        text = "Mark the project review as done"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.COMPLETE_TASK
        assert result.confidence > 0.7
        assert result.suggested_command == "/done"
        assert "project review" in result.suggested_parameters['task_description']
        assert "mark" in result.response_message.lower()
    
    def test_process_input_list_tasks(self):
        """Test processing input for task listing."""
        text = "Show me my tasks"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.LIST_TASKS
        assert result.confidence > 0.7
        assert result.suggested_command == "/list"
        assert "show you your tasks" in result.response_message
    
    def test_process_input_search_tasks(self):
        """Test processing input for task search."""
        text = "Search for project tasks"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.SEARCH_TASKS
        assert result.confidence > 0.7
        assert result.suggested_command == "/search"
        assert "project tasks" in result.suggested_parameters['query']
        assert "search for tasks" in result.response_message
    
    def test_process_input_add_habit(self):
        """Test processing input for habit creation."""
        text = "Add a habit to exercise daily"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.ADD_HABIT
        assert result.confidence > 0.7
        assert result.suggested_command == "/habit_add"
        assert "exercise daily" in result.suggested_parameters['name']
        assert "create a habit" in result.response_message
    
    def test_process_input_unknown(self):
        """Test processing input with unknown intent."""
        text = "Hello there, how are you?"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.UNKNOWN
        assert result.confidence < 0.5
        assert result.suggested_command is None
        assert "I'm not sure what you'd like to do" in result.response_message
    
    def test_process_input_empty(self):
        """Test processing empty input."""
        result = self.processor.process_input("")
        
        assert result.intent == IntentType.UNKNOWN
        assert result.confidence == 0.0
        assert "Empty input" in result.response_message
    
    def test_process_input_with_priority_keywords(self):
        """Test processing input with priority keywords."""
        text = "Add an urgent task to fix the critical bug"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.CREATE_TASK
        assert 'suggested_priority' in result.entities
        assert result.entities['suggested_priority'] == "Urgent"
        assert "priority: Urgent" in result.response_message
    
    def test_process_input_with_category_keywords(self):
        """Test processing input with category keywords."""
        text = "Add a work task for the office project"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.CREATE_TASK
        assert 'suggested_category' in result.entities
        assert result.entities['suggested_category'] == "Work"
        assert "category: Work" in result.response_message
    
    def test_process_input_with_date_keywords(self):
        """Test processing input with date keywords."""
        text = "Add a task to call the client tomorrow"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.CREATE_TASK
        assert 'suggested_date' in result.entities
        expected_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert result.entities['suggested_date'] == expected_date
        assert "due:" in result.response_message
    
    def test_process_input_with_user_context(self):
        """Test processing input with user context management."""
        user_id = 12345
        text = "Add another task like the previous one"
        
        # First interaction
        result1 = self.processor.process_input("Add a task to review documents", user_id)
        assert result1.intent == IntentType.CREATE_TASK
        
        # Second interaction with context
        result2 = self.processor.process_input(text, user_id)
        assert result2.intent == IntentType.CREATE_TASK
        
        # Check that context was updated
        context = self.processor.conversation_manager.get_context(user_id)
        assert context.current_intent == IntentType.CREATE_TASK
        assert len(context.user_history) == 2
    
    def test_process_input_reminder_intent(self):
        """Test processing input for reminder creation."""
        text = "Remind me to call the client tomorrow"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.SET_REMINDER
        assert result.confidence > 0.5
        assert "remind" in result.response_message.lower()
    
    def test_process_input_analytics_intent(self):
        """Test processing input for analytics request."""
        text = "Show me my analytics and stats"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.GET_ANALYTICS
        assert result.confidence > 0.5
        assert "analytics" in result.response_message.lower()
    
    def test_process_input_edit_task(self):
        """Test processing input for task editing."""
        text = "Edit the project review task"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.EDIT_TASK
        assert result.confidence > 0.7
        assert result.suggested_command == "/edit"
        assert "project review" in result.suggested_parameters['task_description']
    
    def test_process_input_delete_task(self):
        """Test processing input for task deletion."""
        text = "Delete the old task"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.DELETE_TASK
        assert result.confidence > 0.7
        assert result.suggested_command == "/done"  # Using /done for deletion
        assert "old task" in result.suggested_parameters['task_description']
    
    def test_process_input_complete_habit(self):
        """Test processing input for habit completion."""
        text = "I did my daily exercise habit"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.COMPLETE_HABIT
        assert result.confidence > 0.7
        assert result.suggested_command == "/habit_done"
        assert "daily exercise" in result.suggested_parameters['name']
    
    def test_process_input_with_sentiment(self):
        """Test processing input with sentiment analysis."""
        text = "I'm so happy to complete this great task!"
        result = self.processor.process_input(text)
        
        # Should detect positive sentiment
        assert result.context.sentiment == "positive"
    
    def test_process_input_with_negative_sentiment(self):
        """Test processing input with negative sentiment."""
        text = "I'm frustrated with this terrible bug"
        result = self.processor.process_input(text)
        
        # Should detect negative sentiment
        assert result.context.sentiment == "negative"
    
    def test_process_input_complex_task_creation(self):
        """Test processing complex task creation with multiple entities."""
        text = "Add an urgent work task to fix the critical bug by tomorrow"
        result = self.processor.process_input(text)
        
        assert result.intent == IntentType.CREATE_TASK
        assert result.entities['suggested_priority'] == "Urgent"
        assert result.entities['suggested_category'] == "Work"
        assert 'suggested_date' in result.entities
        
        # Check response includes all suggestions
        response = result.response_message
        assert "priority: Urgent" in response
        assert "category: Work" in response
        assert "due:" in response
    
    def test_process_input_natural_language_patterns(self):
        """Test various natural language patterns."""
        patterns = [
            ("I need to review the quarterly report", IntentType.CREATE_TASK),
            ("I should call the client", IntentType.CREATE_TASK),
            ("I want to exercise daily", IntentType.CREATE_TASK),
            ("Review the quarterly report is a task", IntentType.CREATE_TASK),
            ("Done with the project review", IntentType.COMPLETE_TASK),
            ("Completed the bug fix", IntentType.COMPLETE_TASK),
            ("What are my tasks?", IntentType.LIST_TASKS),
            ("My tasks list", IntentType.LIST_TASKS),
            ("Find tasks about project", IntentType.SEARCH_TASKS),
            ("Look for bug fixes", IntentType.SEARCH_TASKS),
        ]
        
        for text, expected_intent in patterns:
            result = self.processor.process_input(text)
            assert result.intent == expected_intent, f"Failed for: {text}"
            assert result.confidence > 0.5, f"Low confidence for: {text}"


class TestEnhancedNarrativeProcessorIntegration:
    """Integration tests for the enhanced narrative processor."""
    
    def setup_method(self):
        self.processor = EnhancedNarrativeProcessor()
    
    def test_full_conversation_flow(self):
        """Test a complete conversation flow with context management."""
        user_id = 12345
        
        # Step 1: User creates a task
        result1 = self.processor.process_input(
            "Add an urgent work task to fix the critical bug", 
            user_id
        )
        assert result1.intent == IntentType.CREATE_TASK
        assert result1.entities['suggested_priority'] == "Urgent"
        assert result1.entities['suggested_category'] == "Work"
        
        # Step 2: User completes the task
        result2 = self.processor.process_input(
            "Done with the bug fix", 
            user_id
        )
        assert result2.intent == IntentType.COMPLETE_TASK
        
        # Step 3: User asks for task list
        result3 = self.processor.process_input(
            "Show me my tasks", 
            user_id
        )
        assert result3.intent == IntentType.LIST_TASKS
        
        # Check conversation history
        context = self.processor.conversation_manager.get_context(user_id)
        assert len(context.user_history) == 3
        assert context.user_history[0]['intent'] == 'create_task'
        assert context.user_history[1]['intent'] == 'complete_task'
        assert context.user_history[2]['intent'] == 'list_tasks'
    
    def test_smart_defaults_integration(self):
        """Test integration of smart defaults with intent recognition."""
        text = "Add an urgent work task to fix the critical bug by tomorrow"
        result = self.processor.process_input(text)
        
        # Check that smart defaults were applied
        assert result.entities['suggested_priority'] == "Urgent"
        assert result.entities['suggested_category'] == "Work"
        assert 'suggested_date' in result.entities
        
        # Check that suggestions are included in response
        response = result.response_message
        assert "priority: Urgent" in response
        assert "category: Work" in response
        assert "due:" in response
    
    def test_error_handling(self):
        """Test error handling in the processor."""
        # Test with None input
        result = self.processor.process_input(None)
        assert result.intent == IntentType.UNKNOWN
        assert "Empty input" in result.response_message
        
        # Test with very long input
        long_text = "x" * 1000
        result = self.processor.process_input(long_text)
        assert result.intent == IntentType.UNKNOWN  # Should not match any patterns
    
    def test_performance_with_large_input(self):
        """Test performance with large input text."""
        large_text = "Add a task to " + "review " * 100 + "the quarterly report"
        result = self.processor.process_input(large_text)
        
        # Should still process correctly
        assert result.intent == IntentType.CREATE_TASK
        assert "quarterly report" in result.suggested_parameters['description']


if __name__ == "__main__":
    pytest.main([__file__]) 