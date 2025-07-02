# LarryBot2 Testing Guide

## Overview

LarryBot2 maintains **enterprise-grade testing quality** with **959 passing tests** and **0% failure rate**. This guide provides comprehensive information about our testing procedures, best practices, and contribution guidelines.

## Current Test Status

### ✅ Test Suite Statistics
- **Total Tests**: 986 (100% passing)
- **Execution Time**: ~40 seconds
- **Async Tests**: 434 (45% of suite)
- **Coverage**: 73% overall
- **Critical Services**: Task Service (86%), Database Layer (92%)

### ✅ Quality Achievements
- **Zero regression policy** maintained
- **Edge case resolution** complete (19 tests fixed)
- **Enterprise-grade reliability** achieved
- **All 75+ bot commands** fully functional

## Running Tests

### Basic Test Execution

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run with short traceback for quick feedback
python -m pytest --tb=short

# Run specific test file
python -m pytest tests/test_services_task_service.py

# Run specific test method
python -m pytest tests/test_plugins_tasks.py::TestTasksPlugin::test_add_task_success
```

### Coverage Testing

```bash
# Generate coverage report
python -m pytest --cov=larrybot --cov-report=term

# Generate HTML coverage report
python -m pytest --cov=larrybot --cov-report=html

# Coverage for specific service
python -m pytest --cov=larrybot.services.task_service --cov-report=term

# Coverage with missing lines
python -m pytest --cov=larrybot --cov-report=term-missing
```

### Performance Testing

```bash
# Show slowest test durations
python -m pytest --durations=10

# Time individual test categories
python -m pytest tests/test_core_* --durations=5
python -m pytest tests/test_services_* --durations=5
python -m pytest tests/test_plugins_* --durations=5
```

### Advanced Test Options

```bash
# Run only failed tests from last run
python -m pytest --lf

# Run failed tests first, then remaining
python -m pytest --ff

# Stop on first failure
python -m pytest -x

# Run tests in parallel (if pytest-xdist installed)
python -m pytest -n auto

# Run with warnings displayed
python -m pytest -W error::UserWarning
```

## Test Organization

### Directory Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── factories.py                # Test data factories
├── utils.py                    # Test utilities
├── test_*.py                   # Individual test modules
└── README.md                   # This guide
```

### Test Categories

#### Core System Tests
- `test_core_command_registry.py` - Command registration and discovery
- `test_core_event_bus.py` - Event system functionality
- `test_core_plugin_loader.py` - Plugin loading and management
- `test_core_task_manager.py` - Task management core logic

#### Service Layer Tests
- `test_services_task_service.py` - Task business logic (86% coverage)
- `test_services_task_attachment_service.py` - File attachment handling (97% coverage)
- `test_services_health_service.py` - System health monitoring

#### Storage Layer Tests
- `test_storage_db.py` - Database operations (92% coverage)
- `test_storage_repositories.py` - Repository pattern implementation
- `test_storage_*_repository.py` - Individual repository tests

#### Plugin Tests
- `test_plugins_tasks.py` - Core task management plugin
- `test_plugins_advanced_tasks.py` - Advanced task features
- `test_plugins_calendar.py` - Calendar integration
- `test_plugins_file_attachments.py` - File attachment functionality
- `test_plugins_habit.py` - Habit tracking features
- `test_plugins_reminder.py` - Reminder management

#### Integration Tests
- `test_handlers_bot.py` - Telegram bot handlers
- `test_enhanced_architecture.py` - System integration
- `test_plugins_integration.py` - Cross-plugin functionality

## Test Writing Guidelines

### Python Testing Best Practices

#### Async Test Pattern
```python
import pytest

@pytest.mark.asyncio
async def test_async_service_method(self):
    """Test async service operations with proper await handling."""
    # Arrange
    service = self.get_service_instance()
    test_data = await self.create_test_data()
    
    # Act
    result = await service.process_data(test_data)
    
    # Assert
    assert result['success'] is True
    assert 'data' in result
```

#### Error Response Testing
```python
@pytest.mark.asyncio
async def test_service_error_handling(self):
    """Test service error responses follow standard structure."""
    # Arrange
    service = self.get_service_instance()
    invalid_input = "invalid_data"
    
    # Act
    result = await service.process_input(invalid_input)
    
    # Assert
    assert result['success'] is False
    assert 'error' in result  # Use 'error', not 'message'
    assert isinstance(result['error'], str)
    assert len(result['error']) > 0
    
    # Optional context validation
    if 'context' in result:
        assert isinstance(result['context'], str)
```

#### Factory Usage
```python
from tests.factories import TaskFactory, ClientFactory

@pytest.mark.asyncio
async def test_task_creation_with_client(self):
    """Test task creation using factory-generated data."""
    # Arrange
    client = await ClientFactory.create()
    task_data = TaskFactory.build(client_id=client.id)
    
    # Act
    task = await self.service.create_task(task_data)
    
    # Assert
    assert task['success'] is True
    assert task['data']['client_id'] == client.id
```

### Service Response Standards

All service methods must return consistent response structures:

#### Success Response
```python
{
    "success": True,
    "data": {...},           # Actual response data
    "count": 5,             # Optional: item count
    "total": 10             # Optional: total available
}
```

#### Error Response
```python
{
    "success": False,
    "error": "User-friendly error message",     # Direct error description
    "context": "Technical context or details"  # Additional debugging info
}
```

### Test Fixtures and Factories

#### Using Shared Fixtures
```python
# Available in conftest.py
@pytest.fixture
async def db_session():
    """Provide clean database session for tests."""
    # Setup and cleanup handled automatically

@pytest.fixture
async def sample_task():
    """Provide sample task for testing."""
    return await TaskFactory.create()
```

#### Factory Pattern
```python
# Using factories for consistent test data
from tests.factories import TaskFactory

# Create in-memory object (not saved to DB)
task_data = TaskFactory.build(title="Test Task")

# Create and save to database
task = await TaskFactory.create(title="Test Task", priority="high")

# Create multiple instances
tasks = await TaskFactory.create_batch(5, client_id=client.id)
```

## Debugging Test Failures

### Common Issues and Solutions

#### 1. Response Structure Errors
**Problem**: `KeyError: 'message'` in test assertions
```python
# ❌ Incorrect
assert "error" in result['message']

# ✅ Correct
assert "error" in result['error']
```

#### 2. Async/Await Issues
**Problem**: `RuntimeWarning: coroutine was never awaited`
```python
# ❌ Incorrect
result = service.async_method()

# ✅ Correct
result = await service.async_method()
```

#### 3. Database State Issues
**Problem**: Tests failing due to previous test data
```python
# ✅ Use proper cleanup in fixtures
@pytest.fixture
async def clean_db():
    await clear_database()
    yield
    await clear_database()
```

### Debugging Commands

```bash
# Run with detailed output and stop on first failure
python -m pytest -vvv -x --tb=long

# Run specific failing test with maximum detail
python -m pytest tests/test_file.py::test_method -vvv --tb=long

# Show print statements and logging
python -m pytest -s tests/test_file.py

# Run with pdb debugger on failures
python -m pytest --pdb tests/test_file.py
```

## Contributing New Tests

### Before Adding Tests

1. **Understand existing patterns** - Review similar test files
2. **Use consistent naming** - Follow `test_module_component_scenario` pattern
3. **Leverage factories** - Use existing factories for test data
4. **Check coverage** - Ensure your tests add meaningful coverage

### Test Development Workflow

```bash
# 1. Create test file following naming convention
touch tests/test_new_feature.py

# 2. Write tests following established patterns
# 3. Run your new tests
python -m pytest tests/test_new_feature.py -v

# 4. Check coverage impact
python -m pytest tests/test_new_feature.py --cov=larrybot.new_feature --cov-report=term

# 5. Run full suite to ensure no regressions
python -m pytest

# 6. Update documentation if needed
```

### Quality Checklist

- [ ] All tests pass consistently
- [ ] Tests follow async/await patterns correctly
- [ ] Error responses use `result['error']` not `result['message']`
- [ ] Tests use factories for data generation
- [ ] Coverage is improved by new tests
- [ ] No regression in existing functionality
- [ ] Tests are well-documented with docstrings

## Performance Considerations

### Test Execution Optimization

- **Use factories** instead of creating real database records when possible
- **Mock external dependencies** to avoid network calls
- **Clean up properly** to prevent test pollution
- **Group related tests** in classes for better organization

### Monitoring Test Performance

```bash
# Identify slow tests
python -m pytest --durations=20

# Profile specific test categories
python -m pytest tests/test_services_* --durations=10
python -m pytest tests/test_plugins_* --durations=10
```

## Continuous Integration

### CI Requirements

All tests must pass in CI environment:
- **Zero failures** required for merge
- **Coverage thresholds** must be maintained
- **Performance benchmarks** must not regress
- **No new warnings** introduced

### Local Validation

Before pushing changes:
```bash
# Full test suite
python -m pytest

# Coverage check
python -m pytest --cov=larrybot --cov-report=term

# Performance check
python -m pytest --durations=10

# Verify no regressions
python -m pytest --lf
```

## Support and Resources

### Getting Help

- **Review existing tests** for patterns and examples
- **Check conftest.py** for available fixtures
- **Use factories.py** for consistent test data
- **Consult TESTING_SUMMARY.md** for recent improvements

### Documentation

- **[Testing Quality Report](../TESTING_SUMMARY.md)** - Executive overview
- **[Edge Case Resolution](../EDGE_CASE_RESOLUTION.md)** - Technical deep dive
- **[Metrics Collection Guide](../TESTING_METRICS_COLLECTION.md)** - Data collection procedures

---

**Last Updated**: July 1, 2025  
**Test Suite Status**: 959 passing, 0 failing  
**Quality Standard**: ✅ Enterprise Grade 