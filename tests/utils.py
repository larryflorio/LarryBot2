"""
Test Utilities for LarryBot2

This module provides utility functions and helper classes for common test operations,
performance testing, and standardized assertions.
"""

import time
from typing import Any, Dict, List, Callable
from datetime import datetime, timedelta


class TestUtils:
    """Utility functions for tests."""
    
    @staticmethod
    def assert_task_created(task: Any, **expected_attrs: Any) -> None:
        """Assert task was created with expected attributes."""
        assert task is not None
        for attr, value in expected_attrs.items():
            assert getattr(task, attr) == value
    
    @staticmethod
    def assert_client_has_tasks(client: Any, expected_count: int) -> None:
        """Assert client has expected number of tasks."""
        assert len(client.tasks) == expected_count
    
    @staticmethod
    def create_test_data_set(factories: Dict) -> Dict[str, Any]:
        """Create a complete test data set."""
        client = factories['client'].build()
        task = factories['task'].build(client_id=client.id)
        habit = factories['habit'].build()
        
        return {
            'client': client,
            'task': task,
            'habit': habit
        }
    
    @staticmethod
    def time_operation(operation: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Time an operation and return result and duration."""
        start_time = datetime.now()
        result = operation(*args, **kwargs)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        return {
            'result': result,
            'duration': duration,
            'success': True
        }


class PerformanceTest:
    """Base class for performance tests."""
    
    @staticmethod
    def benchmark_operation(operation: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Benchmark an operation and return metrics."""
        start_time = time.time()
        result = operation(*args, **kwargs)
        end_time = time.time()
        
        return {
            'result': result,
            'duration': end_time - start_time,
            'success': True
        }
    
    @staticmethod
    def assert_performance_threshold(duration: float, threshold: float, operation_name: str) -> None:
        """Assert operation meets performance threshold."""
        assert duration <= threshold, f"{operation_name} took {duration:.3f}s, expected <= {threshold:.3f}s"
    
    @staticmethod
    def benchmark_multiple_operations(operations: List[Callable], iterations: int = 100) -> Dict[str, float]:
        """Benchmark multiple operations and return average durations."""
        results = {}
        
        for operation in operations:
            durations = []
            for _ in range(iterations):
                start_time = time.time()
                operation()
                end_time = time.time()
                durations.append(end_time - start_time)
            
            results[operation.__name__] = sum(durations) / len(durations)
        
        return results


class MockUtils:
    """Utilities for creating and configuring mocks."""
    
    @staticmethod
    def create_mock_update(user_id: int = 123456789, text: str = "/test") -> Any:
        """Create consistent mock update objects."""
        from unittest.mock import MagicMock, AsyncMock
        
        update = MagicMock()
        update.effective_user.id = user_id
        update.message.text = text
        update.message.reply_text = AsyncMock()
        return update
    
    @staticmethod
    def create_mock_context() -> Any:
        """Create a mock Telegram context object."""
        from unittest.mock import MagicMock
        
        context = MagicMock()
        context.args = []
        context.bot_data = {}
        return context
    
    @staticmethod
    def create_mock_session() -> Any:
        """Create a mock database session."""
        from unittest.mock import MagicMock
        
        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        session.close = MagicMock()
        session.query = MagicMock()
        return session


class DataUtils:
    """Utilities for test data creation and manipulation."""
    
    @staticmethod
    def create_future_datetime(days: int = 1, seconds: int = 5) -> datetime:
        """Create a datetime in the future with buffer to avoid race conditions."""
        return datetime.now() + timedelta(days=days, seconds=seconds)
    
    @staticmethod
    def create_past_datetime(days: int = 1) -> datetime:
        """Create a datetime in the past."""
        return datetime.now() - timedelta(days=days)
    
    @staticmethod
    def create_unique_name(prefix: str = "Test") -> str:
        """Create a unique name for testing."""
        return f"{prefix}_{int(time.time())}"
    
    @staticmethod
    def create_test_tags(tag_count: int = 3) -> str:
        """Create test tags as JSON string."""
        import json
        tags = [f"tag_{i}" for i in range(tag_count)]
        return json.dumps(tags) 