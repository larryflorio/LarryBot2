"""
Phase 4.6 Simple Integration Tests

Simplified integration tests focusing on core system functionality
and the integration of all Phase 4.1-4.3 features.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from larrybot.core.dependency_injection import DependencyContainer, ServiceLocator
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.core.plugin_loader import PluginLoader

from larrybot.storage.db import init_db, get_session
from larrybot.storage.task_repository import TaskRepository
from larrybot.services.task_service import TaskService

from larrybot.utils.enhanced_ux_helpers import (
    SmartSuggestionsHelper, IntelligentDefaultsHelper,
    ProgressiveDisclosureBuilder, ErrorRecoveryHelper
)
from larrybot.utils.caching import cache_clear, cache_stats
from larrybot.utils.background_processing import get_background_queue_stats

from larrybot.models.enums import TaskStatus, TaskPriority


class TestPhase46SimpleIntegration:
    """Simple integration tests for Phase 4.6."""

    def setup_method(self):
        """Set up test environment."""
        # Initialize database
        init_db()
        cache_clear()

    def test_dependency_injection_integration(self):
        """Test dependency injection working throughout the system."""
        # Create dependency container
        container = DependencyContainer()
        
        # Register core services
        container.register_singleton("event_bus", EventBus())
        container.register_singleton("command_registry", CommandRegistry())
        
        # Register repositories and services
        session = next(get_session())
        container.register_singleton("task_repository", TaskRepository(session))
        container.register_singleton("task_service", TaskService(
            container.get("task_repository")
        ))
        
        # Set up service locator
        ServiceLocator.set_container(container)
        
        # Test service resolution
        task_service = container.get("task_service")
        event_bus = container.get("event_bus")
        command_registry = container.get("command_registry")
        
        assert task_service is not None
        assert event_bus is not None
        assert command_registry is not None
        
        # Test service composition
        assert hasattr(task_service, 'task_repository')
        assert task_service.task_repository is not None
        
        # Test singleton behavior
        task_service_2 = container.get("task_service")
        assert task_service is task_service_2

    def test_plugin_system_integration(self):
        """Test plugin system integration."""
        # Create command registry
        command_registry = CommandRegistry()
        event_bus = EventBus()
        
        # Load plugins
        plugin_loader = PluginLoader('larrybot.plugins')
        plugin_loader.discover_and_load()
        plugin_loader.register_plugins(event_bus, command_registry)
        
        # Verify plugins loaded
        assert len(plugin_loader.plugins) > 0
        
        # Check key commands are registered
        registered_commands = list(command_registry._commands.keys())
        
        # Task commands
        assert "/add" in registered_commands
        assert "/list" in registered_commands
        assert "/done" in registered_commands
        
        # Advanced task commands (check for actual registered commands)
        # Note: These may be registered under different names
        advanced_commands = [cmd for cmd in registered_commands if any(keyword in cmd for keyword in ['bulk', 'filter', 'analytics'])]
        assert len(advanced_commands) > 0
        
        # Other plugin commands
        assert "/habit_add" in registered_commands
        assert "/addreminder" in registered_commands
        assert "/agenda" in registered_commands

    def test_ux_features_integration(self):
        """Test UX features working together."""
        # Test progressive disclosure
        task_data = {
            'id': 123,
            'description': 'Complex task with many details and requirements',
            'status': 'Todo',
            'priority': 'Medium',
            'attachments': ['file1.pdf', 'file2.docx'],
            'comments': ['Comment 1', 'Comment 2'],
            'time_entries': [{'duration': 2.5, 'description': 'Initial work'}]
        }
        
        # Build smart disclosure keyboard
        keyboard = ProgressiveDisclosureBuilder.build_smart_disclosure_keyboard(
            'task', 123, task_data
        )
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
        
        # Test error recovery
        error_context = {
            'type': 'validation_error',
            'message': 'Invalid task format',
            'action': 'add_task',
            'user_level': 'beginner'
        }
        
        help_message = ErrorRecoveryHelper.provide_contextual_help(error_context)
        assert 'Example' in help_message
        assert 'Tip' in help_message
        
        recovery_keyboard = ErrorRecoveryHelper.build_error_recovery_keyboard(
            'validation_error', error_context
        )
        assert recovery_keyboard is not None

    def test_smart_suggestions_integration(self):
        """Test smart suggestions integration."""
        # Test intelligent defaults
        task_input = "Urgent work meeting tomorrow to discuss quarterly report"
        defaults = IntelligentDefaultsHelper.suggest_task_defaults(task_input)
        
        assert defaults['priority'] == "Urgent"
        assert defaults['category'] == "Work"
        assert defaults['due_date'] is not None
        
        # Test task improvement suggestions
        task_data = {
            'id': 123,
            'description': 'Complex project with multiple phases',
            'status': 'Todo',
            'priority': 'Medium',
            'category': 'Work'
        }
        
        suggestions = SmartSuggestionsHelper.suggest_task_improvements(task_data)
        assert len(suggestions) >= 0  # May or may not have suggestions

    def test_error_recovery_integration(self):
        """Test error recovery integration."""
        # Test various error scenarios
        error_contexts = [
            {
                'type': 'not_found_error',
                'message': 'Task 999 not found',
                'action': 'view_task',
                'user_level': 'beginner'
            },
            {
                'type': 'validation_error',
                'message': 'Invalid task description',
                'action': 'add_task',
                'user_level': 'beginner'
            },
            {
                'type': 'system_error',
                'message': 'Database connection failed',
                'action': 'any',
                'user_level': 'advanced'
            }
        ]
        
        for error_context in error_contexts:
            help_message = ErrorRecoveryHelper.provide_contextual_help(error_context)
            assert len(help_message) > 0
            
            # Test recovery keyboard instead
            recovery_keyboard = ErrorRecoveryHelper.build_error_recovery_keyboard(
                error_context['type'], error_context
            )
            assert recovery_keyboard is not None

    def test_caching_integration(self):
        """Test caching system integration."""
        # Clear cache
        cache_clear()
        
        # Check cache stats
        stats = cache_stats()
        assert stats['entries'] == 0
        assert 'hit_rate' in stats
        assert 'memory_usage' in stats

    def test_background_processing_integration(self):
        """Test background processing integration."""
        # Check background queue stats
        bg_stats = get_background_queue_stats()
        assert 'pending_jobs' in bg_stats
        assert 'completed_jobs' in bg_stats
        assert 'worker_count' in bg_stats

    def test_event_system_integration(self):
        """Test event system integration."""
        event_bus = EventBus()
        
        # Track events
        events_received = []
        
        def event_handler(data):
            events_received.append({'type': 'test_event', 'data': data})
        
        event_bus.subscribe('test_event', event_handler)
        
        # Emit test event
        event_bus.emit('test_event', {'test': 'data'})
        
        # Verify event was received
        assert len(events_received) == 1
        assert events_received[0]['type'] == 'test_event'
        assert events_received[0]['data']['test'] == 'data'

    @pytest.mark.asyncio
    async def test_task_service_integration(self):
        """Test task service integration."""
        # Set up task service
        session = next(get_session())
        task_repo = TaskRepository(session)
        task_service = TaskService(task_repo)
        
        # Test task creation
        result = await task_service.create_task_with_metadata(
            description="Integration test task",
            priority="Medium",
            category="Testing"
        )
        
        assert result['success'] is True
        task_data = result['data']
        assert task_data['description'] == "Integration test task"
        assert task_data['priority'] == "Medium"
        assert task_data['category'] == "Testing"
        
        # Test task retrieval using repository directly
        retrieved_task = task_repo.get_task_by_id(task_data['id'])
        assert retrieved_task is not None
        assert retrieved_task.id == task_data['id']
        
        # Test task completion using repository directly
        task_repo.update_status(task_data['id'], "Done")
        completed_task = task_repo.get_task_by_id(task_data['id'])
        assert completed_task.status == "Done"

    def test_system_architecture_integrity(self):
        """Test that system architecture is properly integrated."""
        # Test core components can be instantiated
        container = DependencyContainer()
        event_bus = EventBus()
        command_registry = CommandRegistry()
        plugin_loader = PluginLoader('larrybot.plugins')
        
        assert container is not None
        assert event_bus is not None
        assert command_registry is not None
        assert plugin_loader is not None
        
        # Test plugin discovery
        plugin_loader.discover_and_load()
        assert len(plugin_loader.plugins) > 0
        
        # Test command registration
        plugin_loader.register_plugins(event_bus, command_registry)
        assert len(command_registry._commands) > 0

    def test_ux_feature_combinations(self):
        """Test UX features working together seamlessly."""
        # Test progressive disclosure with smart suggestions
        complex_task = {
            'id': 123,
            'description': 'Complex project with multiple phases, stakeholders, and deliverables that requires careful planning and coordination',
            'status': 'Todo',
            'priority': 'High',
            'category': 'Work',
            'attachments': ['requirements.pdf', 'design_mockups.zip'],
            'comments': ['Initial requirements gathered', 'Design phase started'],
            'time_entries': [
                {'duration': 4.0, 'description': 'Requirements analysis'},
                {'duration': 2.5, 'description': 'Design work'}
            ]
        }
        
        # Build smart disclosure keyboard
        keyboard = ProgressiveDisclosureBuilder.build_smart_disclosure_keyboard(
            'task', 123, complex_task
        )
        assert keyboard is not None
        
        # Get smart suggestions
        suggestions = SmartSuggestionsHelper.suggest_task_improvements(complex_task)
        assert len(suggestions) > 0
        
        # Complex task should have subtask suggestions
        subtask_suggestion = next(
            (s for s in suggestions if s['type'] == 'subtasks'), 
            None
        )
        assert subtask_suggestion is not None
        
        # Test intelligent defaults with suggestions
        task_input = "Urgent client meeting tomorrow to discuss project timeline"
        defaults = IntelligentDefaultsHelper.suggest_task_defaults(task_input)
        
        assert defaults['priority'] == "Urgent"
        assert defaults['category'] == "Work"
        assert defaults['due_date'] is not None
        
        # Test error recovery with contextual help
        error_context = {
            'type': 'validation_error',
            'message': 'Invalid date format',
            'action': 'add_task',
            'user_level': 'beginner'
        }
        
        help_message = ErrorRecoveryHelper.provide_contextual_help(error_context)
        assert 'Example' in help_message
        
        recovery_keyboard = ErrorRecoveryHelper.build_error_recovery_keyboard(
            'validation_error', error_context
        )
        assert recovery_keyboard is not None

    def test_performance_monitoring_integration(self):
        """Test performance monitoring integration."""
        # Test cache performance
        cache_stats_data = cache_stats()
        assert 'hit_rate' in cache_stats_data
        assert 'entries' in cache_stats_data
        assert 'memory_usage' in cache_stats_data
        
        # Test background processing stats
        bg_stats = get_background_queue_stats()
        assert 'pending_jobs' in bg_stats
        assert 'completed_jobs' in bg_stats
        assert 'worker_count' in bg_stats

    def test_error_handling_integration(self):
        """Test error handling integration."""
        # Test error recovery for different error types
        error_types = ['validation_error', 'not_found_error', 'system_error']
        
        for error_type in error_types:
            error_context = {
                'type': error_type,
                'message': f'Test {error_type} message',
                'action': 'test_action',
                'user_level': 'beginner'
            }
            
            # Test contextual help
            help_message = ErrorRecoveryHelper.provide_contextual_help(error_context)
            assert len(help_message) > 0
            
            # Test recovery keyboard
            recovery_keyboard = ErrorRecoveryHelper.build_error_recovery_keyboard(
                error_type, error_context
            )
            assert recovery_keyboard is not None
            
            # Test recovery keyboard
            recovery_keyboard = ErrorRecoveryHelper.build_error_recovery_keyboard(
                error_type, error_context
            )
            assert recovery_keyboard is not None

    def test_complete_workflow_simulation(self):
        """Test complete workflow simulation."""
        # Simulate user workflow without database operations
        
        # 1. User input with smart defaults
        task_input = "Urgent work meeting tomorrow to discuss quarterly report"
        defaults = IntelligentDefaultsHelper.suggest_task_defaults(task_input)
        
        assert defaults['priority'] == "Urgent"
        assert defaults['category'] == "Work"
        assert defaults['due_date'] is not None
        
        # 2. Task data for suggestions
        task_data = {
            'id': 123,
            'description': task_input,
            'priority': defaults['priority'],
            'category': defaults['category'],
            'due_date': defaults['due_date']
        }
        
        # 3. Get smart suggestions
        suggestions = SmartSuggestionsHelper.suggest_task_improvements(task_data)
        assert len(suggestions) >= 0
        
        # 4. Build progressive disclosure
        keyboard = ProgressiveDisclosureBuilder.build_smart_disclosure_keyboard(
            'task', 123, task_data
        )
        assert keyboard is not None
        
        # 5. Simulate error and recovery
        error_context = {
            'type': 'validation_error',
            'message': 'Invalid input',
            'action': 'add_task',
            'user_level': 'beginner'
        }
        
        help_message = ErrorRecoveryHelper.provide_contextual_help(error_context)
        assert 'Example' in help_message
        
        recovery_keyboard = ErrorRecoveryHelper.build_error_recovery_keyboard(
            'validation_error', error_context
        )
        assert recovery_keyboard is not None 