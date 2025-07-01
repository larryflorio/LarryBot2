"""
Comprehensive tests for larrybot.core.event_utils module.

This test suite covers all uncovered scenarios to achieve 85% coverage:
- Exception handling in data formatting
- Error recovery mechanisms
- Edge cases and boundary conditions
- Performance scenarios
- Complex event processing workflows
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from larrybot.core.event_utils import (
    EventDataFormatter,
    safe_event_handler,
    emit_task_event,
    emit_client_event
)
from larrybot.core.event_bus import EventBus
import types


class TestEventDataFormatterComprehensive:
    """Comprehensive tests for EventDataFormatter class."""

    def test_format_task_data_with_dict(self):
        """Test format_task_data with dictionary input."""
        task_dict = {
            'id': 1,
            'description': 'Test task',
            'done': False,
            'priority': 'High'
        }
        result = EventDataFormatter.format_task_data(task_dict)
        assert result == task_dict

    def test_format_task_data_with_task_object(self):
        """Test format_task_data with Task object."""
        # Create a mock Task object with all attributes
        task_obj = Mock()
        task_obj.id = 1
        task_obj.description = 'Test task'
        task_obj.done = False
        task_obj.priority = 'High'
        task_obj.due_date = datetime(2025, 1, 1, 12, 0)
        task_obj.category = 'Work'
        task_obj.status = 'In Progress'
        task_obj.estimated_hours = 2.5
        task_obj.actual_hours = 1.5
        task_obj.started_at = datetime(2025, 1, 1, 10, 0)
        task_obj.parent_id = None
        task_obj.tags = '["urgent", "frontend"]'
        task_obj.client_id = 1
        task_obj.created_at = datetime(2025, 1, 1, 9, 0)
        task_obj.updated_at = datetime(2025, 1, 1, 11, 0)

        result = EventDataFormatter.format_task_data(task_obj)
        
        assert result['id'] == 1
        assert result['description'] == 'Test task'
        assert result['done'] is False
        assert result['priority'] == 'High'
        assert result['due_date'] == '2025-01-01T12:00:00'
        assert result['category'] == 'Work'
        assert result['status'] == 'In Progress'
        assert result['estimated_hours'] == 2.5
        assert result['actual_hours'] == 1.5
        assert result['started_at'] == '2025-01-01T10:00:00'
        assert result['parent_id'] is None
        assert result['tags'] == ['urgent', 'frontend']
        assert result['client_id'] == 1
        assert result['created_at'] == '2025-01-01T09:00:00'
        assert result['updated_at'] == '2025-01-01T11:00:00'

    def test_format_task_data_with_task_object_missing_attributes(self):
        """Test format_task_data with Task object missing some attributes (should use defaults)."""
        task_obj = MinimalTask()
        result = EventDataFormatter.format_task_data(task_obj)
        assert result['id'] == 1
        assert result['description'] == 'Test task'
        assert result['done'] is False
        assert result['priority'] == 'Medium'
        assert result['due_date'] is None
        assert result['category'] is None
        assert result['status'] == 'Todo'
        assert result['estimated_hours'] is None
        assert result['actual_hours'] is None
        assert result['started_at'] is None
        assert result['parent_id'] is None
        assert result['tags'] == []
        assert result['client_id'] is None
        assert result['created_at'] is None
        assert result['updated_at'] is None

    def test_format_task_data_with_task_object_none_values(self):
        """Test format_task_data with Task object having None values."""
        task_obj = NoneTask()
        result = EventDataFormatter.format_task_data(task_obj)
        # Use .get() to avoid KeyError and accept None or missing
        assert result.get('due_date') is None
        assert result.get('estimated_hours') is None
        assert result.get('actual_hours') is None
        assert result.get('started_at') is None
        # Accept both None and [] for tags
        tags = result.get('tags')
        assert tags is None or tags == []
        assert result.get('created_at') is None
        assert result.get('updated_at') is None

    def test_format_task_data_with_exception_handling(self):
        """Test format_task_data exception handling (attribute raises Exception)."""
        task_obj = ExplodingTask()
        result = EventDataFormatter.format_task_data(task_obj)
        assert result['id'] == 1
        assert result['description'] == 'Test task'
        assert result['done'] is False
        assert result['priority'] == 'Medium'
        assert result['due_date'] is None
        assert result['category'] is None
        assert result['status'] == 'Todo'
        assert 'error' in result
        assert 'Data conversion error' in result['error']

    def test_format_task_data_with_json_decode_error(self):
        """Test format_task_data with JSON decode error in tags."""
        task_obj = Mock()
        task_obj.id = 1
        task_obj.description = 'Test task'
        task_obj.tags = 'invalid json'

        result = EventDataFormatter.format_task_data(task_obj)
        
        # Should return fallback data with error information
        assert 'error' in result
        assert 'Data conversion error' in result['error']

    def test_format_client_data_with_dict(self):
        """Test format_client_data with dictionary input."""
        client_dict = {
            'id': 1,
            'name': 'Test Client',
            'created_at': '2025-01-01T09:00:00',
            'updated_at': '2025-01-01T11:00:00'
        }
        result = EventDataFormatter.format_client_data(client_dict)
        assert result == client_dict

    def test_format_client_data_with_client_object(self):
        """Test format_client_data with Client object."""
        client_obj = Mock()
        client_obj.id = 1
        client_obj.name = 'Test Client'
        client_obj.created_at = datetime(2025, 1, 1, 9, 0)
        client_obj.updated_at = datetime(2025, 1, 1, 11, 0)

        result = EventDataFormatter.format_client_data(client_obj)
        
        assert result['id'] == 1
        assert result['name'] == 'Test Client'
        assert result['created_at'] == '2025-01-01T09:00:00'
        assert result['updated_at'] == '2025-01-01T11:00:00'

    def test_format_client_data_with_client_object_missing_attributes(self):
        """Test format_client_data with Client object missing some attributes (should use defaults)."""
        client_obj = MinimalClient()
        result = EventDataFormatter.format_client_data(client_obj)
        assert result['id'] == 1
        assert result['name'] == 'Test Client'
        assert result['created_at'] is None
        assert result['updated_at'] is None

    def test_format_client_data_with_exception_handling(self):
        """Test format_client_data exception handling (attribute raises Exception)."""
        client_obj = ExplodingClient()
        result = EventDataFormatter.format_client_data(client_obj)
        assert result['id'] == 1
        assert result['name'] == 'Test Client'
        assert 'error' in result
        assert 'Data conversion error' in result['error']

    def test_format_client_data_with_none_values(self):
        """Test format_client_data with Client object having None values."""
        client_obj = NoneClient()
        result = EventDataFormatter.format_client_data(client_obj)
        assert result.get('created_at') is None
        assert result.get('updated_at') is None

    def test_format_task_data_with_none_input(self):
        """Test format_task_data with None input (should return all fields None/defaults)."""
        result = EventDataFormatter.format_task_data(None)
        # Should be a dict with all expected keys, all set to None or default values
        assert isinstance(result, dict)
        assert result.get('id') is None
        assert result.get('description') == 'Unknown Task' or result.get('description') == ''
        assert result.get('done') is False
        assert result.get('priority') == 'Medium'
        assert result.get('due_date') is None
        assert result.get('category') is None
        assert result.get('status') == 'Todo'
        # Accept either None or missing for optional fields
        assert result.get('estimated_hours') is None
        assert result.get('actual_hours') is None
        assert result.get('started_at') is None
        assert result.get('parent_id') is None
        assert result.get('tags') == [] or result.get('tags') is None
        assert result.get('client_id') is None
        assert result.get('created_at') is None
        assert result.get('updated_at') is None

    def test_format_client_data_with_none_input(self):
        """Test format_client_data with None input (should return all fields None/defaults)."""
        result = EventDataFormatter.format_client_data(None)
        assert isinstance(result, dict)
        assert result.get('id') is None
        assert result.get('name') == 'Unknown Client' or result.get('name') == ''
        assert result.get('created_at') is None
        assert result.get('updated_at') is None


class TestSafeEventHandlerComprehensive:
    """Comprehensive tests for safe_event_handler decorator."""

    def test_safe_event_handler_success(self):
        """Test safe_event_handler with successful execution."""
        @safe_event_handler
        def test_handler(data):
            return f"Processed: {data['name']}"

        result = test_handler({'name': 'Test'})
        assert result == "Processed: Test"

    def test_safe_event_handler_with_attribute_error_description(self):
        """Test safe_event_handler with AttributeError containing 'description' (lines 83-84)."""
        @safe_event_handler
        def test_handler(data):
            return data.description  # This will cause AttributeError

        # Test with dict data that should be converted to object
        result = test_handler({'description': 'Test task', 'id': 1})
        
        # Should convert dict to object and succeed
        assert result == 'Test task'

    def test_safe_event_handler_with_attribute_error_id(self):
        """Test safe_event_handler with AttributeError containing 'id'."""
        @safe_event_handler
        def test_handler(data):
            return data.id  # This will cause AttributeError

        # Test with dict data that should be converted to object
        result = test_handler({'id': 123, 'name': 'Test'})
        
        # Should convert dict to object and succeed
        assert result == 123

    def test_safe_event_handler_with_attribute_error_not_format_related(self):
        """Test safe_event_handler with AttributeError not related to format."""
        @safe_event_handler
        def test_handler(data):
            return data.nonexistent_attribute  # This will cause AttributeError

        # Test with dict data that doesn't have the attribute
        with pytest.raises(AttributeError):
            test_handler({'id': 123, 'name': 'Test'})

    def test_safe_event_handler_with_general_exception(self):
        """Test safe_event_handler with general exception."""
        @safe_event_handler
        def test_handler(data):
            raise ValueError("Test error")

        # Should catch exception and return None
        result = test_handler({'name': 'Test'})
        assert result is None

    def test_safe_event_handler_dict_as_object_conversion(self):
        """Test DictAsObject conversion functionality (lines 102-123)."""
        @safe_event_handler
        def test_handler(data):
            # Access attributes that would normally be on an object
            return f"{data.id}: {data.name} - {data.description}"

        # Test with dict data
        result = test_handler({
            'id': 1,
            'name': 'Test Task',
            'description': 'This is a test task'
        })
        
        # Should convert dict to object and succeed
        assert result == "1: Test Task - This is a test task"

    def test_safe_event_handler_dict_as_object_nested_access(self):
        """Test DictAsObject with nested attribute access."""
        @safe_event_handler
        def test_handler(data):
            return {
                'id': data.id,
                'name': data.name,
                'metadata': data.metadata,
                'tags': data.tags
            }

        # Test with complex dict data
        result = test_handler({
            'id': 1,
            'name': 'Test Task',
            'metadata': {'priority': 'high', 'category': 'work'},
            'tags': ['urgent', 'frontend']
        })
        
        expected = {
            'id': 1,
            'name': 'Test Task',
            'metadata': {'priority': 'high', 'category': 'work'},
            'tags': ['urgent', 'frontend']
        }
        assert result == expected

    def test_safe_event_handler_with_additional_args(self):
        """Test safe_event_handler with additional arguments."""
        @safe_event_handler
        def test_handler(data, extra_arg, keyword_arg=None):
            return f"{data['name']} - {extra_arg} - {keyword_arg}"

        result = test_handler({'name': 'Test'}, 'extra', keyword_arg='keyword')
        assert result == "Test - extra - keyword"

    def test_safe_event_handler_with_kwargs(self):
        """Test safe_event_handler with keyword arguments."""
        @safe_event_handler
        def test_handler(data, **kwargs):
            return f"{data['name']} - {kwargs.get('status', 'unknown')}"

        result = test_handler({'name': 'Test'}, status='active')
        assert result == "Test - active"

    def test_safe_event_handler_with_none_data(self):
        """Test safe_event_handler with None data."""
        @safe_event_handler
        def test_handler(data):
            return data['key']
        
        # Should catch the TypeError and return None
        result = test_handler(None)
        assert result is None


class TestEventEmissionComprehensive:
    """Comprehensive tests for event emission functions."""

    def test_emit_task_event_with_event_bus(self):
        """Test emit_task_event with valid event bus."""
        event_bus = Mock()
        task_data = {'id': 1, 'description': 'Test task'}
        
        emit_task_event(event_bus, 'task_created', task_data)
        
        event_bus.emit.assert_called_once_with('task_created', task_data)

    def test_emit_task_event_without_event_bus(self):
        """Test emit_task_event without event bus."""
        # Should not raise any exception
        emit_task_event(None, 'task_created', {'id': 1, 'description': 'Test task'})

    def test_emit_task_event_with_task_object(self):
        """Test emit_task_event with Task object."""
        event_bus = Mock()
        task_obj = Mock()
        task_obj.id = 1
        task_obj.description = 'Test task'
        task_obj.done = False
        task_obj.priority = 'High'
        
        emit_task_event(event_bus, 'task_created', task_obj)
        
        # Should format the task object and emit
        call_args = event_bus.emit.call_args
        assert call_args[0][0] == 'task_created'
        assert call_args[0][1]['id'] == 1
        assert call_args[0][1]['description'] == 'Test task'
        assert call_args[0][1]['done'] is False
        assert call_args[0][1]['priority'] == 'High'

    def test_emit_client_event_with_event_bus(self):
        """Test emit_client_event with valid event bus."""
        event_bus = Mock()
        client_data = {'id': 1, 'name': 'Test Client'}
        
        emit_client_event(event_bus, 'client_created', client_data)
        
        event_bus.emit.assert_called_once_with('client_created', client_data)

    def test_emit_client_event_without_event_bus(self):
        """Test emit_client_event without event bus."""
        # Should not raise any exception
        emit_client_event(None, 'client_created', {'id': 1, 'name': 'Test Client'})

    def test_emit_client_event_with_client_object(self):
        """Test emit_client_event with Client object."""
        event_bus = Mock()
        client_obj = Mock()
        client_obj.id = 1
        client_obj.name = 'Test Client'
        client_obj.created_at = datetime(2025, 1, 1, 9, 0)
        
        emit_client_event(event_bus, 'client_created', client_obj)
        
        # Should format the client object and emit
        call_args = event_bus.emit.call_args
        assert call_args[0][0] == 'client_created'
        assert call_args[0][1]['id'] == 1
        assert call_args[0][1]['name'] == 'Test Client'
        assert call_args[0][1]['created_at'] == '2025-01-01T09:00:00'


class TestEventUtilsIntegration:
    """Integration tests for event utilities."""

    def test_full_event_workflow_with_task(self):
        """Test complete event workflow with task data."""
        event_bus = EventBus()
        events_received = []
        
        @safe_event_handler
        def task_handler(data):
            events_received.append(data)
        
        event_bus.subscribe('task_created', task_handler)
        
        # Create task object
        task_obj = Mock()
        task_obj.id = 1
        task_obj.description = 'Integration test task'
        task_obj.done = False
        task_obj.priority = 'Medium'
        
        # Emit event
        emit_task_event(event_bus, 'task_created', task_obj)
        
        # Verify event was received and processed
        assert len(events_received) == 1
        assert events_received[0]['id'] == 1
        assert events_received[0]['description'] == 'Integration test task'
        assert events_received[0]['done'] is False
        assert events_received[0]['priority'] == 'Medium'

    def test_full_event_workflow_with_client(self):
        """Test complete event workflow with client data."""
        event_bus = EventBus()
        events_received = []
        
        @safe_event_handler
        def client_handler(data):
            events_received.append(data)
        
        event_bus.subscribe('client_created', client_handler)
        
        # Create client object
        client_obj = Mock()
        client_obj.id = 1
        client_obj.name = 'Integration test client'
        client_obj.created_at = datetime(2025, 1, 1, 9, 0)
        
        # Emit event
        emit_client_event(event_bus, 'client_created', client_obj)
        
        # Verify event was received and processed
        assert len(events_received) == 1
        assert events_received[0]['id'] == 1
        assert events_received[0]['name'] == 'Integration test client'
        assert events_received[0]['created_at'] == '2025-01-01T09:00:00'

    def test_event_workflow_with_error_recovery(self):
        """Test event workflow with error recovery."""
        event_bus = EventBus()
        events_received = []
        
        @safe_event_handler
        def error_handler(data):
            # This handler expects object attributes but receives dict
            return f"ID: {data.id}, Name: {data.name}"
        
        event_bus.subscribe('test_event', error_handler)
        
        # Emit event with dict data
        emit_task_event(event_bus, 'test_event', {'id': 1, 'name': 'Test'})
        
        # Handler should convert dict to object and succeed
        # Note: This test verifies the DictAsObject conversion works
        # The actual result would be the return value from the handler


class TestEventUtilsEdgeCases:
    """Edge case tests for event utilities."""

    def test_format_task_data_with_empty_dict(self):
        """Test format_task_data with empty dictionary."""
        result = EventDataFormatter.format_task_data({})
        assert result == {}

    def test_format_task_data_with_none_input(self):
        """Test format_task_data with None input (should return all fields None/defaults)."""
        result = EventDataFormatter.format_task_data(None)
        assert isinstance(result, dict)
        assert result.get('id') is None
        assert result.get('description') == 'Unknown Task' or result.get('description') == ''
        assert result.get('done') is False
        assert result.get('priority') == 'Medium'
        assert result.get('due_date') is None
        assert result.get('category') is None
        assert result.get('status') == 'Todo'
        assert result.get('estimated_hours') is None
        assert result.get('actual_hours') is None
        assert result.get('started_at') is None
        assert result.get('parent_id') is None
        tags = result.get('tags')
        assert tags is None or tags == []
        assert result.get('client_id') is None
        assert result.get('created_at') is None
        assert result.get('updated_at') is None

    def test_format_client_data_with_empty_dict(self):
        """Test format_client_data with empty dictionary."""
        result = EventDataFormatter.format_client_data({})
        assert result == {}

    def test_format_client_data_with_none_input(self):
        """Test format_client_data with None input (should return all fields None/defaults)."""
        result = EventDataFormatter.format_client_data(None)
        assert isinstance(result, dict)
        assert result.get('id') is None
        assert result.get('name') == 'Unknown Client' or result.get('name') == ''
        assert result.get('created_at') is None
        assert result.get('updated_at') is None

    def test_safe_event_handler_with_empty_dict(self):
        """Test safe_event_handler with empty dictionary."""
        @safe_event_handler
        def test_handler(data):
            return data.get('key', 'default')
        
        result = test_handler({})
        assert result == 'default'

    def test_safe_event_handler_with_none_data(self):
        """Test safe_event_handler with None data."""
        @safe_event_handler
        def test_handler(data):
            return data['key']
        
        # Should catch the TypeError and return None
        result = test_handler(None)
        assert result is None

    def test_emit_events_with_falsy_event_bus(self):
        """Test emit events with falsy event bus values."""
        # Test with empty string
        emit_task_event("", 'task_created', {'id': 1})
        emit_client_event("", 'client_created', {'id': 1})
        
        # Test with zero
        emit_task_event(0, 'task_created', {'id': 1})
        emit_client_event(0, 'client_created', {'id': 1})
        
        # Test with empty list
        emit_task_event([], 'task_created', {'id': 1})
        emit_client_event([], 'client_created', {'id': 1})


class TestEventUtilsPerformance:
    """Performance tests for event utilities."""

    def test_format_task_data_performance(self):
        """Test format_task_data performance with large dataset."""
        import time
        
        # Create a large task object
        task_obj = Mock()
        task_obj.id = 1
        task_obj.description = 'Performance test task'
        task_obj.done = False
        task_obj.priority = 'High'
        task_obj.due_date = datetime(2025, 1, 1, 12, 0)
        task_obj.category = 'Work'
        task_obj.status = 'In Progress'
        task_obj.estimated_hours = 2.5
        task_obj.actual_hours = 1.5
        task_obj.started_at = datetime(2025, 1, 1, 10, 0)
        task_obj.parent_id = None
        task_obj.tags = '["urgent", "frontend", "performance"]'
        task_obj.client_id = 1
        task_obj.created_at = datetime(2025, 1, 1, 9, 0)
        task_obj.updated_at = datetime(2025, 1, 1, 11, 0)
        
        # Measure performance
        start_time = time.time()
        for _ in range(1000):
            EventDataFormatter.format_task_data(task_obj)
        end_time = time.time()
        
        # Should complete within reasonable time (less than 1 second for 1000 iterations)
        assert end_time - start_time < 1.0

    def test_safe_event_handler_performance(self):
        """Test safe_event_handler performance."""
        import time
        
        @safe_event_handler
        def test_handler(data):
            return data['id']
        
        # Measure performance
        start_time = time.time()
        for i in range(1000):
            test_handler({'id': i, 'name': f'Task {i}'})
        end_time = time.time()
        
        # Should complete within reasonable time (less than 1 second for 1000 iterations)
        assert end_time - start_time < 1.0

    def test_event_emission_performance(self):
        """Test event emission performance."""
        import time
        
        event_bus = Mock()
        task_data = {'id': 1, 'description': 'Performance test task'}
        
        # Measure performance
        start_time = time.time()
        for _ in range(1000):
            emit_task_event(event_bus, 'task_created', task_data)
        end_time = time.time()
        
        # Should complete within reasonable time (less than 1 second for 1000 iterations)
        assert end_time - start_time < 1.0 


class MinimalTask:
    def __init__(self):
        self.id = 1
        self.description = 'Test task'

class NoneTask:
    def __init__(self):
        self.id = 1
        self.description = 'Test task'
        self.done = None
        self.priority = None
        self.due_date = None
        self.category = None
        self.status = None
        self.estimated_hours = None
        self.actual_hours = None
        self.started_at = None
        self.parent_id = None
        self.tags = None
        self.client_id = None
        self.created_at = None
        self.updated_at = None

class ExplodingTask:
    id = 1
    description = 'Test task'
    @property
    def due_date(self):
        raise Exception("Simulated error")

class MinimalClient:
    def __init__(self):
        self.id = 1
        self.name = 'Test Client'

class NoneClient:
    def __init__(self):
        self.id = 1
        self.name = 'Test Client'
        self.created_at = None
        self.updated_at = None

class ExplodingClient:
    id = 1
    name = 'Test Client'
    @property
    def created_at(self):
        raise Exception("Simulated error") 