import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from larrybot.core.event_bus import EventBus
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.plugin_loader import PluginLoader
from larrybot.storage.db import get_session
from larrybot.models import Base
from typing import Generator
from larrybot.utils.datetime_utils import get_current_datetime


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_db_engine():
    """Create a test database engine."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_session(test_db_engine):
    """Create a test database session."""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def event_bus():
    """Create a fresh event bus for each test."""
    return EventBus()


@pytest.fixture
def command_registry():
    """Create a fresh command registry for each test."""
    return CommandRegistry()


@pytest.fixture
def plugin_loader():
    """Create a plugin loader for testing."""
    return PluginLoader()


@pytest.fixture
def mock_update():
    """Create a properly configured mock Telegram update object."""
    
    # Create the main update object
    update = MagicMock()
    
    # Create message with async reply_text method
    message = MagicMock()
    message.text = "/test"
    message.reply_text = AsyncMock()
    update.message = message
    
    # Create effective_user with sync attributes
    effective_user = MagicMock()
    effective_user.id = 123456789  # Default authorized user
    update.effective_user = effective_user
    
    return update


@pytest.fixture
def mock_context():
    """Create a mock Telegram context object."""
    class MockContext:
        def __init__(self):
            self.args = []
            self.bot_data = {}
    
    return MockContext()


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "description": "Test task",
        "done": False
    }


@pytest.fixture
def sample_habit_data():
    """Sample habit data for testing."""
    return {
        "name": "Test habit",
        "streak": 0,
        "last_completed": None
    }


@pytest.fixture
def sample_reminder_data():
    """Sample reminder data for testing."""
    from datetime import datetime, timedelta
    return {
        "task_id": 1,
        "remind_at": get_current_datetime() + timedelta(hours=1)
    }


# Week 1 Enhanced Fixtures for Comprehensive Testing

@pytest.fixture
def mock_psutil():
    """Mock psutil for system resource testing."""
    with patch('psutil.cpu_percent') as mock_cpu, \
         patch('psutil.virtual_memory') as mock_memory, \
         patch('psutil.disk_usage') as mock_disk:
        
        # Mock CPU usage
        mock_cpu.return_value = 25.0
        
        # Mock memory usage
        mock_memory.return_value = Mock(
            percent=45.0,
            available=1024*1024*1024,  # 1GB available
            total=4*1024*1024*1024,    # 4GB total
            used=2.2*1024*1024*1024    # 2.2GB used
        )
        
        # Mock disk usage
        mock_disk.return_value = Mock(
            percent=30.0,
            free=1024*1024*1024*10,    # 10GB free
            total=100*1024*1024*1024,  # 100GB total
            used=70*1024*1024*1024     # 70GB used
        )
        
        yield {
            'cpu': mock_cpu,
            'memory': mock_memory,
            'disk': mock_disk
        }


@pytest.fixture
def mock_google_calendar_api():
    """Mock Google Calendar API responses."""
    with patch('google.oauth2.credentials.Credentials') as mock_creds, \
         patch('googleapiclient.discovery.build') as mock_build, \
         patch('google.auth.transport.requests.Request') as mock_request:
        
        # Mock credentials
        mock_creds.return_value = Mock()
        mock_creds.return_value.expired = False
        mock_creds.return_value.valid = True
        
        # Mock service
        mock_service = Mock()
        mock_calendar_service = Mock()
        mock_events = Mock()
        
        # Mock events list response
        mock_events.list.return_value.execute.return_value = {
            'items': [
                {
                    'id': 'event1',
                    'summary': 'Test Event 1',
                    'start': {'dateTime': '2025-01-01T10:00:00Z'},
                    'end': {'dateTime': '2025-01-01T11:00:00Z'}
                },
                {
                    'id': 'event2',
                    'summary': 'Test Event 2',
                    'start': {'dateTime': '2025-01-01T14:00:00Z'},
                    'end': {'dateTime': '2025-01-01T15:00:00Z'}
                }
            ]
        }
        
        mock_calendar_service.events.return_value = mock_events
        mock_service.calendars.return_value = mock_calendar_service
        mock_build.return_value = mock_service
        
        # Mock request
        mock_request.return_value = Mock()
        
        yield {
            'credentials': mock_creds,
            'service': mock_build,
            'request': mock_request,
            'calendar_service': mock_calendar_service,
            'events': mock_events
        }


@pytest.fixture
def mock_telegram_api():
    """Mock Telegram API responses."""
    with patch('telegram.Bot') as mock_bot, \
         patch('telegram.ext.Application') as mock_app:
        
        # Mock bot
        mock_bot_instance = Mock()
        mock_bot_instance.get_me.return_value = Mock(
            id=123456789,
            username='test_bot',
            first_name='Test Bot'
        )
        mock_bot.return_value = mock_bot_instance
        
        # Mock application
        mock_app_instance = Mock()
        mock_app_instance.bot = mock_bot_instance
        mock_app_instance.add_handler = Mock()
        mock_app_instance.run_polling = Mock()
        mock_app.return_value = mock_app_instance
        
        yield {
            'bot': mock_bot,
            'application': mock_app,
            'bot_instance': mock_bot_instance,
            'app_instance': mock_app_instance
        }


@pytest.fixture
def sample_health_data():
    """Sample health monitoring data for testing."""
    return {
        'database': {
            'status': 'healthy',
            'response_time': 0.05,
            'connection_count': 5,
            'last_check': '2025-01-01T10:00:00Z'
        },
        'memory': {
            'status': 'healthy',
            'usage_percent': 45.0,
            'available_mb': 1024,
            'total_mb': 4096,
            'last_check': '2025-01-01T10:00:00Z'
        },
        'cpu': {
            'status': 'healthy',
            'usage_percent': 25.0,
            'load_average': [1.2, 1.1, 0.9],
            'last_check': '2025-01-01T10:00:00Z'
        },
        'disk': {
            'status': 'healthy',
            'usage_percent': 30.0,
            'free_gb': 10,
            'total_gb': 100,
            'last_check': '2025-01-01T10:00:00Z'
        },
        'plugins': {
            'status': 'healthy',
            'active_count': 5,
            'total_count': 6,
            'failed_plugins': [],
            'last_check': '2025-01-01T10:00:00Z'
        },
        'overall': {
            'status': 'healthy',
            'last_check': '2025-01-01T10:00:00Z',
            'response_time': 0.1
        }
    }


@pytest.fixture
def error_scenarios():
    """Common error scenarios for testing."""
    return {
        'database_connection_failed': Exception("Database connection failed: Connection refused"),
        'database_timeout': Exception("Database operation timed out after 30 seconds"),
        'database_locked': Exception("Database is locked: database is locked"),
        'api_timeout': TimeoutError("API request timed out after 30 seconds"),
        'api_rate_limit': Exception("Rate limit exceeded: 429 Too Many Requests"),
        'api_unauthorized': Exception("Unauthorized: 401 Unauthorized"),
        'api_server_error': Exception("Internal server error: 500 Internal Server Error"),
        'invalid_response': ValueError("Invalid API response format"),
        'authentication_failed': Exception("Authentication failed: Invalid credentials"),
        'file_not_found': FileNotFoundError("File not found: config.json"),
        'permission_denied': PermissionError("Permission denied: Cannot access file"),
        'memory_error': MemoryError("Out of memory: Cannot allocate memory"),
        'disk_full': OSError("No space left on device"),
        'network_unreachable': ConnectionError("Network is unreachable"),
        'plugin_load_failed': ImportError("Failed to load plugin: No module named 'invalid_plugin'"),
        'event_bus_failure': Exception("Event bus failure: Cannot emit event"),
        'command_registry_error': Exception("Command registry error: Invalid command format")
    }


@pytest.fixture
def mock_event_bus_with_failures():
    """Event bus that can simulate failures for testing error handling."""
    event_bus = EventBus()
    original_emit = event_bus.emit
    
    def emit_with_failures(event_type, data=None):
        """Emit events with optional failure simulation."""
        if data and data.get('simulate_failure'):
            failure_type = data.get('failure_type', 'generic')
            if failure_type == 'timeout':
                raise TimeoutError("Event emission timed out")
            elif failure_type == 'permission':
                raise PermissionError("Permission denied for event emission")
            elif failure_type == 'network':
                raise ConnectionError("Network error during event emission")
            else:
                raise Exception(f"Simulated event bus failure: {failure_type}")
        return original_emit(event_type, data)
    
    event_bus.emit = emit_with_failures
    return event_bus


@pytest.fixture
def mock_plugin_manager():
    """Create a mock plugin manager for testing."""
    manager = Mock()
    manager.load_plugins = Mock()
    manager.get_plugin = Mock()
    manager.list_plugins = Mock(return_value=['test_plugin'])
    return manager


@pytest.fixture
def mock_task_service():
    """Create a mock task service for testing."""
    service = Mock()
    
    # Mock all the bulk operation methods
    service.bulk_update_status = AsyncMock()
    service.bulk_update_priority = AsyncMock()
    service.bulk_assign_to_client = AsyncMock()
    service.bulk_delete_tasks = AsyncMock()
    
    # Mock time entry methods
    service.add_manual_time_entry = AsyncMock()
    service.get_task_time_summary = AsyncMock()
    
    # Mock enhanced filtering methods
    service.search_tasks_by_text = AsyncMock()
    service.get_tasks_with_advanced_filters = AsyncMock()
    service.get_tasks_by_multiple_tags = AsyncMock()
    service.get_tasks_by_time_range = AsyncMock()
    service.get_tasks_by_priority_range = AsyncMock()
    
    # Mock enhanced analytics methods
    service.get_advanced_task_analytics = AsyncMock()
    service.get_productivity_report = AsyncMock()
    
    # Mock other task methods
    service.create_task_with_metadata = AsyncMock()
    service.update_task_priority = AsyncMock()
    service.update_task_due_date = AsyncMock()
    service.update_task_category = AsyncMock()
    service.update_task_status = AsyncMock()
    service.start_time_tracking = AsyncMock()
    service.stop_time_tracking = AsyncMock()
    service.add_subtask = AsyncMock()
    service.get_subtasks = AsyncMock()
    service.add_task_dependency = AsyncMock()
    service.get_task_dependencies = AsyncMock()
    service.add_tags = AsyncMock()
    service.get_tasks_by_tag = AsyncMock()
    service.add_comment = AsyncMock()
    service.get_comments = AsyncMock()
    service.get_task_analytics = AsyncMock()
    service.suggest_priority = AsyncMock()
    
    return service


@pytest.fixture
def sample_command_metadata():
    """Sample command metadata for testing command registry and help functionality."""
    return {
        'start': {
            'description': 'Start the bot and show welcome message',
            'usage': '/start',
            'category': 'system',
            'admin_only': False
        },
        'help': {
            'description': 'Show help information and available commands',
            'usage': '/help [command]',
            'category': 'system',
            'admin_only': False
        },
        'add': {
            'description': 'Add a new task',
            'usage': '/add <description>',
            'category': 'tasks',
            'admin_only': False
        },
        'list': {
            'description': 'List all tasks',
            'usage': '/list [filter]',
            'category': 'tasks',
            'admin_only': False
        },
        'done': {
            'description': 'Mark a task as done',
            'usage': '/done <task_id>',
            'category': 'tasks',
            'admin_only': False
        },
        'habit_add': {
            'description': 'Add a new habit',
            'usage': '/habit_add <name>',
            'category': 'habits',
            'admin_only': False
        },
        'health': {
            'description': 'Check system health',
            'usage': '/health',
            'category': 'system',
            'admin_only': True
        }
    }


@pytest.fixture
def malformed_command_metadata():
    """Malformed command metadata for testing error handling."""
    return {
        'valid_command': {
            'description': 'Valid command',
            'usage': '/valid',
            'category': 'test'
        },
        'missing_description': {
            'usage': '/missing_desc',
            'category': 'test'
        },
        'missing_usage': {
            'description': 'Missing usage',
            'category': 'test'
        },
        'missing_category': {
            'description': 'Missing category',
            'usage': '/missing_cat'
        },
        'invalid_category': {
            'description': 'Invalid category',
            'usage': '/invalid_cat',
            'category': 'invalid_category'
        },
        'empty_description': {
            'description': '',
            'usage': '/empty_desc',
            'category': 'test'
        },
        'very_long_description': {
            'description': 'A' * 1000,  # Very long description
            'usage': '/long_desc',
            'category': 'test'
        }
    }


# Test Data Factory Fixtures (Week 1 Implementation)

@pytest.fixture
def task_factory():
    """Factory for creating test tasks."""
    from tests.factories import TaskFactory
    return TaskFactory()


@pytest.fixture
def client_factory():
    """Factory for creating test clients."""
    from tests.factories import ClientFactory
    return ClientFactory()


@pytest.fixture
def habit_factory():
    """Factory for creating test habits."""
    from tests.factories import HabitFactory
    return HabitFactory()


@pytest.fixture
def reminder_factory():
    """Factory for creating test reminders."""
    from tests.factories import ReminderFactory
    return ReminderFactory()


@pytest.fixture
def task_comment_factory():
    """Factory for creating test task comments."""
    from tests.factories import TaskCommentFactory
    return TaskCommentFactory()


@pytest.fixture
def task_dependency_factory():
    """Factory for creating test task dependencies."""
    from tests.factories import TaskDependencyFactory
    return TaskDependencyFactory()


@pytest.fixture
def factories():
    """Access to all factories."""
    from tests.factories import (
        TaskFactory, ClientFactory, HabitFactory, 
        ReminderFactory, TaskCommentFactory, TaskDependencyFactory
    )
    return {
        'task': TaskFactory(),
        'client': ClientFactory(),
        'habit': HabitFactory(),
        'reminder': ReminderFactory(),
        'task_comment': TaskCommentFactory(),
        'task_dependency': TaskDependencyFactory()
    }


@pytest.fixture
def db_task_factory(test_session):
    """Factory that creates and persists tasks to database."""
    from tests.factories import TaskFactory
    
    factory = TaskFactory()
    
    def create_task(**kwargs):
        task = factory.build(**kwargs)
        test_session.add(task)
        test_session.commit()
        return task
    
    return create_task


@pytest.fixture
def db_client_factory(test_session):
    """Factory that creates and persists clients to database."""
    from tests.factories import ClientFactory
    
    factory = ClientFactory()
    
    def create_client(**kwargs):
        client = factory.build(**kwargs)
        test_session.add(client)
        test_session.commit()
        return client
    
    return create_client


@pytest.fixture
def db_habit_factory(test_session):
    """Factory that creates and persists habits to database."""
    from tests.factories import HabitFactory
    
    factory = HabitFactory()
    
    def create_habit(**kwargs):
        habit = factory.build(**kwargs)
        test_session.add(habit)
        test_session.commit()
        return habit
    
    return create_habit


@pytest.fixture
def db_reminder_factory(test_session):
    """Factory that creates and persists reminders to database."""
    from tests.factories import ReminderFactory
    
    factory = ReminderFactory()
    
    def create_reminder(**kwargs):
        reminder = factory.build(**kwargs)
        test_session.add(reminder)
        test_session.commit()
        return reminder
    
    return create_reminder


@pytest.fixture
def db_task_comment_factory(test_session):
    """Factory that creates and persists task comments to database."""
    from tests.factories import TaskCommentFactory
    
    factory = TaskCommentFactory()
    
    def create_task_comment(**kwargs):
        task_comment = factory.build(**kwargs)
        test_session.add(task_comment)
        test_session.commit()
        return task_comment
    
    return create_task_comment


@pytest.fixture
def db_task_dependency_factory(test_session):
    """Factory that creates and persists task dependencies to database."""
    from tests.factories import TaskDependencyFactory
    
    factory = TaskDependencyFactory()
    
    def create_task_dependency(**kwargs):
        task_dependency = factory.build(**kwargs)
        test_session.add(task_dependency)
        test_session.commit()
        return task_dependency
    
    return create_task_dependency


# Background Processing Fixtures

@pytest_asyncio.fixture
async def job_queue():
    """Create a properly initialized background job queue for testing."""
    from larrybot.utils.background_processing import BackgroundJobQueue
    queue = BackgroundJobQueue(max_workers=2, max_queue_size=100)
    await queue.start()  # Initialize async queue
    yield queue
    await queue.stop()   # Clean shutdown


@pytest.fixture
def sync_job_queue():
    """Create a job queue for synchronous tests (without starting it)."""
    from larrybot.utils.background_processing import BackgroundJobQueue
    return BackgroundJobQueue(max_workers=2, max_queue_size=10) 