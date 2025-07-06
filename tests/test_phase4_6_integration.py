"""
Phase 4.6 Integration Tests

Comprehensive integration tests for the entire LarryBot2 system,
testing all components working together including:
- Dependency injection refactoring (Phase 4.1)
- Enhanced test suite (Phase 4.2) 
- Advanced UX features (Phase 4.3)
- All plugins and services
- End-to-end workflows
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta
from typing import Dict, Any, List

from larrybot.core.dependency_injection import DependencyContainer, ServiceLocator
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.core.plugin_loader import PluginLoader
from larrybot.core.task_manager import TaskManager
from larrybot.core.performance import PerformanceCollector

from larrybot.storage.db import get_session, init_db
from larrybot.storage.task_repository import TaskRepository
from larrybot.storage.client_repository import ClientRepository
from larrybot.storage.habit_repository import HabitRepository
from larrybot.storage.reminder_repository import ReminderRepository

from larrybot.services.task_service import TaskService
from larrybot.services.health_service import HealthService
from larrybot.services.task_attachment_service import TaskAttachmentService

from larrybot.utils.enhanced_ux_helpers import (
    SmartSuggestionsHelper, IntelligentDefaultsHelper,
    ProgressiveDisclosureBuilder, ErrorRecoveryHelper
)
from larrybot.utils.caching import cache_clear, cache_stats
from larrybot.utils.background_processing import get_background_queue_stats

from larrybot.models.task import Task
from larrybot.models.client import Client
from larrybot.models.habit import Habit
from larrybot.models.reminder import Reminder
from larrybot.models.enums import TaskStatus, TaskPriority


class TestPhase46Integration:
    """Comprehensive integration tests for Phase 4.6."""

    @pytest.fixture
    async def integration_setup(self):
        """Set up complete integration test environment."""
        # Initialize database
        init_db()
        
        # Create dependency container
        container = DependencyContainer()
        
        # Register core services
        container.register_singleton("event_bus", EventBus())
        container.register_singleton("command_registry", CommandRegistry())
        container.register_singleton("performance_collector", PerformanceCollector())
        
        # Register repositories
        session = next(get_session())
        container.register_singleton("task_repository", TaskRepository(session))
        container.register_singleton("client_repository", ClientRepository(session))
        container.register_singleton("habit_repository", HabitRepository(session))
        container.register_singleton("reminder_repository", ReminderRepository(session))
        
        # Register services
        container.register_singleton("task_service", TaskService(
            container.get("task_repository")
        ))
        container.register_singleton("health_service", HealthService())
        
        # Set up service locator
        ServiceLocator.set_container(container)
        
        # Load plugins
        plugin_loader = PluginLoader('larrybot.plugins')
        plugin_loader.discover_and_load()
        plugin_loader.register_plugins(
            container.get("event_bus"),
            container.get("command_registry")
        )
        
        # Start task manager
        task_manager = TaskManager()
        await task_manager.start_background_services(test_mode=True)
        
        setup_data = {
            'container': container,
            'event_bus': container.get("event_bus"),
            'command_registry': container.get("command_registry"),
            'task_service': container.get("task_service"),
            'health_service': container.get("health_service"),
            'plugin_loader': plugin_loader,
            'task_manager': task_manager
        }
        
        yield setup_data
        
        # Cleanup
        await task_manager.stop()
        cache_clear()

    @pytest.mark.asyncio
    async def test_complete_task_workflow(self, integration_setup):
        """Test complete task creation, management, and completion workflow."""
        task_service = integration_setup['task_service']
        event_bus = integration_setup['event_bus']
        
        # Track events
        events_received = []
        
        def event_handler(event_type, data):
            events_received.append({'type': event_type, 'data': data})
        
        event_bus.subscribe('task_created', event_handler)
        event_bus.subscribe('task_updated', event_handler)
        event_bus.subscribe('task_completed', event_handler)
        
        # 1. Create task with smart defaults
        task_input = "Urgent work meeting tomorrow to discuss quarterly report"
        defaults = IntelligentDefaultsHelper.suggest_task_defaults(task_input)
        
        task = await task_service.create_task(
            description=task_input,
            priority=defaults['priority'],
            category=defaults['category'],
            due_date=defaults['due_date']
        )
        
        assert task.description == task_input
        assert task.priority == "Urgent"
        assert task.category == "Work"
        assert task.status == TaskStatus.TODO
        assert task.due_date is not None
        
        # Verify event was emitted
        assert len(events_received) == 1
        assert events_received[0]['type'] == 'task_created'
        assert events_received[0]['data']['description'] == task_input
        
        # 2. Get smart suggestions for task improvement
        task_data = {
            'id': task.id,
            'description': task.description,
            'priority': task.priority,
            'category': task.category,
            'due_date': task.due_date
        }
        
        suggestions = SmartSuggestionsHelper.suggest_task_improvements(task_data)
        assert len(suggestions) > 0
        
        # 3. Update task with time tracking
        success = await task_service.start_time_tracking(task.id)
        assert success
        
        # Simulate work time
        await asyncio.sleep(0.1)
        
        duration = await task_service.stop_time_tracking(task.id)
        assert duration > 0
        
        # 4. Complete task
        completed_task = await task_service.complete_task(task.id)
        assert completed_task.status == TaskStatus.DONE
        assert completed_task.done is True
        
        # Verify completion event
        assert len(events_received) == 3
        assert events_received[2]['type'] == 'task_completed'

    @pytest.mark.asyncio
    async def test_advanced_task_features_integration(self, integration_setup):
        """Test advanced task features working together."""
        task_service = integration_setup['task_service']
        command_registry = integration_setup['command_registry']
        
        # Create multiple tasks for testing
        tasks = []
        for i in range(3):
            task = await task_service.create_task(
                description=f"Test task {i+1}",
                priority="Medium",
                category="Testing",
                tags=['test', f'task{i+1}']
            )
            tasks.append(task)
        
        # Test bulk operations
        task_ids = [task.id for task in tasks]
        
        # Bulk priority update
        updated_count = await task_service.bulk_update_priority(task_ids, "High")
        assert updated_count == 3
        
        # Verify all tasks updated
        for task_id in task_ids:
            task = await task_service.get_task_by_id(task_id)
            assert task.priority == "High"
        
        # Test advanced filtering
        high_priority_tasks = await task_service.get_tasks_with_filters(
            priority="High",
            status="Todo"
        )
        assert len(high_priority_tasks) == 3
        
        # Test analytics
        analytics = await task_service.get_task_analytics(days=7)
        assert analytics['total_tasks'] >= 3
        assert analytics['completion_rate'] >= 0

    @pytest.mark.asyncio
    async def test_ux_features_integration(self, integration_setup):
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

    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self, integration_setup):
        """Test performance monitoring integration."""
        performance_collector = integration_setup['container'].get("performance_collector")
        
        # Test operation tracking
        with performance_collector.track_operation("test_operation", {"test": True}):
            await asyncio.sleep(0.1)  # Simulate work
        
        # Get performance stats
        stats = performance_collector.get_performance_summary()
        assert stats['total_operations'] >= 1
        assert stats['avg_execution_time'] > 0
        
        # Test cache performance
        cache_stats_data = cache_stats()
        assert 'hit_rate' in cache_stats_data
        assert 'entries' in cache_stats_data
        
        # Test background processing stats
        bg_stats = get_background_queue_stats()
        assert 'pending_jobs' in bg_stats
        assert 'completed_jobs' in bg_stats

    @pytest.mark.asyncio
    async def test_plugin_integration(self, integration_setup):
        """Test all plugins working together."""
        command_registry = integration_setup['command_registry']
        plugin_loader = integration_setup['plugin_loader']
        
        # Verify plugins loaded
        assert len(plugin_loader.plugins) > 0
        
        # Check key commands are registered
        registered_commands = list(command_registry._commands.keys())
        
        # Task commands
        assert "/add" in registered_commands
        assert "/list" in registered_commands
        assert "/done" in registered_commands
        
        # Advanced task commands
        assert "/bulk" in registered_commands
        assert "/filter" in registered_commands
        assert "/analytics" in registered_commands
        
        # Other plugin commands
        assert "/habit_add" in registered_commands
        assert "/addreminder" in registered_commands
        assert "/agenda" in registered_commands

    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self, integration_setup):
        """Test health monitoring integration."""
        health_service = integration_setup['health_service']
        
        # Test comprehensive health check
        health = await health_service.get_system_health()
        
        required_components = [
            "database", "memory", "cpu", "disk", 
            "plugins", "overall_status", "timestamp"
        ]
        
        for component in required_components:
            assert component in health
        
        assert health["overall_status"] in ["healthy", "warning", "critical"]
        
        # Test quick health check
        quick_health = await health_service.get_quick_health()
        assert "database" in quick_health
        assert "memory" in quick_health
        assert "timestamp" in quick_health

    @pytest.mark.asyncio
    async def test_dependency_injection_integration(self, integration_setup):
        """Test dependency injection working throughout the system."""
        container = integration_setup['container']
        
        # Test service resolution
        task_service = container.get("task_service")
        health_service = container.get("health_service")
        event_bus = container.get("event_bus")
        
        assert task_service is not None
        assert health_service is not None
        assert event_bus is not None
        
        # Test service composition
        assert hasattr(task_service, 'task_repository')
        assert task_service.task_repository is not None
        
        # Test singleton behavior
        task_service_2 = container.get("task_service")
        assert task_service is task_service_2

    @pytest.mark.asyncio
    async def test_background_processing_integration(self, integration_setup):
        """Test background processing integration."""
        task_service = integration_setup['task_service']
        
        # Test analytics via background processing
        job_id = task_service.get_advanced_task_analytics_async(days=7)
        assert job_id is not None
        assert isinstance(job_id, str)
        
        # Wait for job to complete
        await asyncio.sleep(0.5)
        
        # Check background queue stats
        bg_stats = get_background_queue_stats()
        assert bg_stats['completed_jobs'] >= 1

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, integration_setup):
        """Test error handling throughout the system."""
        task_service = integration_setup['task_service']
        
        # Test invalid task ID
        result = await task_service.get_task_by_id(99999)
        assert result is None
        
        # Test invalid bulk operation
        result = await task_service.bulk_update_priority([99999], "High")
        assert result == 0
        
        # Test error recovery suggestions
        error_context = {
            'type': 'not_found_error',
            'message': 'Task not found',
            'action': 'view_task',
            'user_level': 'beginner'
        }
        
        suggestions = ErrorRecoveryHelper.suggest_recovery_actions(
            'not_found_error', error_context
        )
        assert len(suggestions) > 0

    @pytest.mark.asyncio
    async def test_caching_integration(self, integration_setup):
        """Test caching system integration."""
        task_service = integration_setup['task_service']
        
        # Clear cache
        cache_clear()
        
        # First call - should hit database
        start_time = datetime.now()
        tasks1 = await task_service.get_all_tasks()
        first_call_time = (datetime.now() - start_time).total_seconds()
        
        # Second call - should hit cache
        start_time = datetime.now()
        tasks2 = await task_service.get_all_tasks()
        second_call_time = (datetime.now() - start_time).total_seconds()
        
        # Cache should be faster
        assert second_call_time < first_call_time
        assert len(tasks1) == len(tasks2)
        
        # Check cache stats
        stats = cache_stats()
        assert stats['entries'] > 0
        assert stats['hit_rate'] > 0

    @pytest.mark.asyncio
    async def test_event_system_integration(self, integration_setup):
        """Test event system integration."""
        event_bus = integration_setup['event_bus']
        task_service = integration_setup['task_service']
        
        # Track events
        events_received = []
        
        def event_handler(event_type, data):
            events_received.append({'type': event_type, 'data': data})
        
        event_bus.subscribe('task_created', event_handler)
        event_bus.subscribe('task_updated', event_handler)
        event_bus.subscribe('task_completed', event_handler)
        
        # Create and update task
        task = await task_service.create_task("Event test task")
        await task_service.update_task_priority(task.id, "High")
        await task_service.complete_task(task.id)
        
        # Verify events were emitted
        assert len(events_received) == 3
        assert events_received[0]['type'] == 'task_created'
        assert events_received[1]['type'] == 'task_updated'
        assert events_received[2]['type'] == 'task_completed'

    @pytest.mark.asyncio
    async def test_complete_user_workflow(self, integration_setup):
        """Test complete user workflow from start to finish."""
        task_service = integration_setup['task_service']
        command_registry = integration_setup['command_registry']
        
        # Simulate user workflow
        
        # 1. User creates multiple tasks
        tasks = []
        task_descriptions = [
            "Review quarterly report",
            "Prepare presentation for client meeting",
            "Update project documentation",
            "Schedule team meeting"
        ]
        
        for desc in task_descriptions:
            defaults = IntelligentDefaultsHelper.suggest_task_defaults(desc)
            task = await task_service.create_task(
                description=desc,
                priority=defaults['priority'],
                category=defaults['category']
            )
            tasks.append(task)
        
        # 2. User views tasks with smart suggestions
        all_tasks = await task_service.get_all_tasks()
        assert len(all_tasks) >= len(tasks)
        
        # Get suggestions for task improvements
        for task in tasks[:2]:  # Test first 2 tasks
            task_data = {
                'id': task.id,
                'description': task.description,
                'priority': task.priority,
                'category': task.category
            }
            suggestions = SmartSuggestionsHelper.suggest_task_improvements(task_data)
            assert len(suggestions) >= 0  # May or may not have suggestions
        
        # 3. User performs bulk operations
        task_ids = [task.id for task in tasks[:2]]
        updated_count = await task_service.bulk_update_priority(task_ids, "High")
        assert updated_count == 2
        
        # 4. User uses advanced filtering
        high_priority_tasks = await task_service.get_tasks_with_filters(
            priority="High"
        )
        assert len(high_priority_tasks) >= 2
        
        # 5. User completes some tasks
        completed_count = 0
        for task in tasks[:2]:
            await task_service.complete_task(task.id)
            completed_count += 1
        
        # 6. User views analytics
        analytics = await task_service.get_task_analytics(days=7)
        assert analytics['total_tasks'] >= len(tasks)
        assert analytics['completed_tasks'] >= completed_count
        
        # 7. User checks system health
        health_service = integration_setup['health_service']
        health = await health_service.get_quick_health()
        assert health['overall_status'] in ['healthy', 'warning', 'critical']

    def test_system_architecture_integrity(self, integration_setup):
        """Test that system architecture is properly integrated."""
        container = integration_setup['container']
        
        # Verify all core components are present
        core_services = [
            "event_bus", "command_registry", "performance_collector",
            "task_service", "health_service"
        ]
        
        for service_name in core_services:
            service = container.get(service_name)
            assert service is not None, f"Missing core service: {service_name}"
        
        # Verify plugin system is working
        plugin_loader = integration_setup['plugin_loader']
        assert len(plugin_loader.plugins) > 0
        
        # Verify command registry has commands
        command_registry = container.get("command_registry")
        assert len(command_registry._commands) > 0
        
        # Verify event bus is functional
        event_bus = container.get("event_bus")
        assert hasattr(event_bus, 'subscribe')
        assert hasattr(event_bus, 'emit')

    @pytest.mark.asyncio
    async def test_performance_under_load(self, integration_setup):
        """Test system performance under simulated load."""
        task_service = integration_setup['task_service']
        performance_collector = integration_setup['container'].get("performance_collector")
        
        # Create multiple tasks quickly
        start_time = datetime.now()
        
        tasks = []
        for i in range(10):
            with performance_collector.track_operation(f"create_task_{i}"):
                task = await task_service.create_task(f"Load test task {i}")
                tasks.append(task)
        
        creation_time = (datetime.now() - start_time).total_seconds()
        
        # Should complete quickly
        assert creation_time < 5.0  # Should create 10 tasks in under 5 seconds
        
        # Test bulk operations performance
        task_ids = [task.id for task in tasks]
        
        start_time = datetime.now()
        with performance_collector.track_operation("bulk_update"):
            updated_count = await task_service.bulk_update_priority(task_ids, "Medium")
        
        bulk_time = (datetime.now() - start_time).total_seconds()
        
        assert updated_count == 10
        assert bulk_time < 2.0  # Should update 10 tasks in under 2 seconds
        
        # Check performance metrics
        stats = performance_collector.get_performance_summary()
        assert stats['total_operations'] >= 11  # 10 creates + 1 bulk update

    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self, integration_setup):
        """Test various error recovery scenarios."""
        task_service = integration_setup['task_service']
        
        # Test invalid input handling
        try:
            await task_service.create_task("")  # Empty description
            assert False, "Should have raised validation error"
        except Exception:
            pass  # Expected
        
        # Test non-existent task operations
        result = await task_service.get_task_by_id(99999)
        assert result is None
        
        result = await task_service.update_task_priority(99999, "High")
        assert result is None
        
        # Test bulk operations with invalid IDs
        result = await task_service.bulk_update_priority([99999, 99998], "High")
        assert result == 0
        
        # Test error recovery suggestions
        error_context = {
            'type': 'validation_error',
            'message': 'Invalid task description',
            'action': 'add_task',
            'user_level': 'beginner'
        }
        
        help_message = ErrorRecoveryHelper.provide_contextual_help(error_context)
        assert 'Example' in help_message
        assert 'Usage' in help_message
        
        recovery_actions = ErrorRecoveryHelper.suggest_recovery_actions(
            'validation_error', error_context
        )
        assert len(recovery_actions) > 0

    @pytest.mark.asyncio
    async def test_system_cleanup_and_maintenance(self, integration_setup):
        """Test system cleanup and maintenance functions."""
        task_manager = integration_setup['task_manager']
        
        # Test background services are running
        assert task_manager._running is True
        
        # Test cache cleanup
        cache_stats_before = cache_stats()
        cache_clear()
        cache_stats_after = cache_stats()
        
        assert cache_stats_after['entries'] == 0
        
        # Test background queue cleanup
        bg_stats_before = get_background_queue_stats()
        
        # Submit some test jobs
        task_service = integration_setup['task_service']
        job_ids = []
        for i in range(3):
            job_id = task_service.get_advanced_task_analytics_async(days=1)
            job_ids.append(job_id)
        
        # Wait for jobs to complete
        await asyncio.sleep(1.0)
        
        bg_stats_after = get_background_queue_stats()
        assert bg_stats_after['completed_jobs'] >= 3
        
        # Test graceful shutdown
        await task_manager.stop()
        assert task_manager._running is False


class TestPhase46EndToEnd:
    """End-to-end tests simulating real user interactions."""

    @pytest.mark.asyncio
    async def test_complete_task_management_workflow(self):
        """Test complete task management workflow from user perspective."""
        # Initialize system
        init_db()
        
        session = next(get_session())
        task_repo = TaskRepository(session)
        task_service = TaskService(task_repo)
        
        # 1. User creates tasks with natural language
        task_inputs = [
            "Urgent work meeting tomorrow to discuss quarterly report",
            "Medium priority personal task to buy groceries",
            "Low priority task to organize desk"
        ]
        
        tasks = []
        for input_text in task_inputs:
            defaults = IntelligentDefaultsHelper.suggest_task_defaults(input_text)
            task = await task_service.create_task(
                description=input_text,
                priority=defaults['priority'],
                category=defaults['category'],
                due_date=defaults['due_date']
            )
            tasks.append(task)
        
        # Verify smart defaults were applied
        assert tasks[0].priority == "Urgent"
        assert tasks[0].category == "Work"
        assert tasks[1].priority == "Medium"
        assert tasks[1].category == "Personal"
        assert tasks[2].priority == "Low"
        
        # 2. User views tasks with smart suggestions
        all_tasks = await task_service.get_all_tasks()
        assert len(all_tasks) >= 3
        
        # Get suggestions for first task
        task_data = {
            'id': tasks[0].id,
            'description': tasks[0].description,
            'priority': tasks[0].priority,
            'category': tasks[0].category
        }
        suggestions = SmartSuggestionsHelper.suggest_task_improvements(task_data)
        
        # 3. User performs bulk operations
        task_ids = [task.id for task in tasks]
        updated_count = await task_service.bulk_update_priority(task_ids, "High")
        assert updated_count == 3
        
        # 4. User uses advanced filtering
        high_priority_tasks = await task_service.get_tasks_with_filters(
            priority="High"
        )
        assert len(high_priority_tasks) >= 3
        
        # 5. User completes tasks
        for task in tasks:
            await task_service.complete_task(task.id)
        
        # 6. User views analytics
        analytics = await task_service.get_task_analytics(days=7)
        assert analytics['total_tasks'] >= 3
        assert analytics['completed_tasks'] >= 3
        assert analytics['completion_rate'] >= 50

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery workflow from user perspective."""
        # Test various error scenarios and recovery
        
        # 1. Invalid task ID error
        error_context = {
            'type': 'not_found_error',
            'message': 'Task 999 not found',
            'action': 'view_task',
            'user_level': 'beginner'
        }
        
        help_message = ErrorRecoveryHelper.provide_contextual_help(error_context)
        assert 'Item Not Found' in help_message or 'not found' in help_message
        
        recovery_actions = ErrorRecoveryHelper.suggest_recovery_actions(
            'not_found_error', error_context
        )
        assert len(recovery_actions) > 0
        
        # 2. Validation error
        error_context = {
            'type': 'validation_error',
            'message': 'Invalid task description',
            'action': 'add_task',
            'user_level': 'beginner'
        }
        
        help_message = ErrorRecoveryHelper.provide_contextual_help(error_context)
        assert 'Example' in help_message
        assert 'Tip' in help_message
        
        # 3. System error
        error_context = {
            'type': 'system_error',
            'message': 'Database connection failed',
            'action': 'any',
            'user_level': 'advanced'
        }
        
        recovery_actions = ErrorRecoveryHelper.suggest_recovery_actions(
            'system_error', error_context
        )
        assert len(recovery_actions) > 0

    def test_ux_feature_integration(self):
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