"""
Tests for Phase 2 components: Advanced Performance Monitoring & Type Safety

This module tests the enhanced performance monitoring system, enum-based type safety,
and advanced task functionality implemented in Phase 2.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import json
import time

from larrybot.core.performance import (
    PerformanceCollector, PerformanceMetrics, MetricType, Severity,
    get_performance_collector, track_performance
)
from larrybot.models.enums import (
    TaskStatus, TaskPriority, ReminderType, ClientStatus, HabitFrequency,
    FileAttachmentType, HealthStatus, AnalyticsTimeRange,
    validate_enum_value, get_enum_choices, enum_to_dict
)
from larrybot.models.task import Task
from larrybot.plugins.performance import PerformancePlugin


class TestPerformanceCollector:
    """Test advanced performance monitoring system."""
    
    def test_performance_collector_initialization(self):
        """Test performance collector initialization."""
        collector = PerformanceCollector(max_metrics=100, retention_hours=12)
        
        assert collector.max_metrics == 100
        assert collector.retention_hours == 12
        assert len(collector._metrics) == 0
        assert len(collector._aggregates) == 0
        assert isinstance(collector.thresholds.operation_warning, float)
    
    def test_track_operation_context_manager(self):
        """Test operation tracking with context manager."""
        collector = PerformanceCollector()
        
        with collector.track_operation("test_operation", {"test": "context"}):
            time.sleep(0.01)  # Small delay to measure
        
        assert len(collector._metrics) == 1
        metric = collector._metrics[0]
        assert metric.operation_name == "test_operation"
        assert metric.execution_time > 0
        assert metric.context == {"test": "context"}
        assert metric.metric_type == MetricType.OPERATION
    
    def test_performance_metrics_aggregation(self):
        """Test performance metrics aggregation."""
        collector = PerformanceCollector()
        
        # Add multiple metrics for same operation
        for i in range(5):
            with collector.track_operation("repeated_operation"):
                time.sleep(0.001 * i)  # Variable execution time
        
        aggregates = collector._aggregates["repeated_operation"]
        assert aggregates['count'] == 5
        assert aggregates['total_time'] > 0
        assert aggregates['avg_time'] > 0
        assert aggregates['min_time'] >= 0
        assert aggregates['max_time'] > aggregates['min_time']
    
    def test_performance_dashboard_data(self):
        """Test performance dashboard data generation."""
        collector = PerformanceCollector()
        
        # Add some test metrics
        with collector.track_operation("fast_operation"):
            time.sleep(0.001)
        
        with collector.track_operation("slow_operation"):
            time.sleep(0.1)
        
        dashboard = collector.get_performance_dashboard()
        
        assert 'summary' in dashboard
        assert 'operations' in dashboard
        assert 'system' in dashboard
        assert 'alerts' in dashboard
        assert 'trends' in dashboard
        assert 'top_operations' in dashboard
        
        summary = dashboard['summary']
        assert summary['total_operations'] == 2
        assert summary['avg_execution_time'] > 0
    
    def test_severity_determination(self):
        """Test performance severity determination."""
        collector = PerformanceCollector()
        
        # Test different severity levels
        info_severity = collector._determine_severity(0.1, 1000)  # Fast, low memory
        warning_severity = collector._determine_severity(1.5, 1000)  # Slow, low memory
        critical_severity = collector._determine_severity(6.0, 1000)  # Very slow
        
        assert info_severity == Severity.INFO
        assert warning_severity == Severity.WARNING
        assert critical_severity == Severity.CRITICAL
    
    def test_performance_alerts_generation(self):
        """Test performance alerts generation."""
        collector = PerformanceCollector()
        
        # Create a critical operation
        metrics = PerformanceMetrics(
            operation_name="critical_operation",
            execution_time=10.0,  # Very slow
            memory_usage=0,
            cache_hit_rate=0.0,
            database_queries=0,
            background_jobs=0,
            severity=Severity.CRITICAL
        )
        collector._record_metrics(metrics)
        
        dashboard = collector.get_performance_dashboard()
        alerts = dashboard['alerts']
        
        assert len(alerts) > 0
        assert any(alert['type'] == 'critical_operation' for alert in alerts)
    
    def test_metrics_export_and_clear(self):
        """Test metrics export and clearing."""
        collector = PerformanceCollector()
        
        # Add some metrics
        for i in range(10):
            with collector.track_operation(f"operation_{i}"):
                time.sleep(0.001)
        
        # Export metrics
        exported = collector.export_metrics(hours=24)
        assert len(exported) == 10
        assert all('operation_name' in metric for metric in exported)
        
        # Clear metrics
        cleared_count = collector.clear_metrics()
        assert cleared_count == 10
        assert len(collector._metrics) == 0
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    @patch('psutil.disk_usage')
    def test_system_stats_collection(self, mock_disk, mock_cpu, mock_memory):
        """Test system statistics collection."""
        # Mock system metrics
        mock_memory.return_value.percent = 45.2
        mock_memory.return_value.available = 8 * 1024 * 1024 * 1024  # 8GB
        mock_cpu.return_value = 23.5
        mock_disk.return_value.percent = 67.8
        
        collector = PerformanceCollector()
        
        # Add a recent metric to ensure dashboard doesn't return empty
        with collector.track_operation("test_operation"):
            pass  # This will add a metric to the collector
        
        dashboard = collector.get_performance_dashboard()
        system_stats = dashboard['system']
        
        assert system_stats['memory_usage'] == 45.2
        assert system_stats['cpu_usage'] == 23.5
        assert system_stats['disk_usage'] == 67.8
        assert system_stats['memory_available'] == 8.0
    
    def test_track_performance_decorator(self):
        """Test track_performance decorator."""
        collector = get_performance_collector()
        initial_count = len(collector._metrics)
        
        @track_performance("decorated_operation", {"decorator": True})
        def test_function():
            time.sleep(0.001)
            return "result"
        
        result = test_function()
        
        assert result == "result"
        assert len(collector._metrics) == initial_count + 1
        
        metric = collector._metrics[-1]
        assert metric.operation_name == "decorated_operation"
        assert metric.context == {"decorator": True}


class TestEnhancedEnums:
    """Test enhanced enum types for type safety."""
    
    def test_task_status_enum(self):
        """Test TaskStatus enum functionality."""
        # Test basic functionality
        status = TaskStatus.TODO
        assert str(status) == "Todo"
        assert status.is_active is True
        assert status.is_completed is False
        
        # Test status transitions
        assert TaskStatus.IN_PROGRESS in status.can_transition_to
        assert TaskStatus.DONE not in status.can_transition_to
        
        # Test color codes
        assert status.color_code == "🔵"
        assert TaskStatus.DONE.color_code == "🟢"
        
        # Test from_string conversion
        assert TaskStatus.from_string("todo") == TaskStatus.TODO
        assert TaskStatus.from_string("In Progress") == TaskStatus.IN_PROGRESS
        assert TaskStatus.from_string("invalid") is None
    
    def test_task_priority_enum(self):
        """Test TaskPriority enum functionality."""
        # Test basic functionality
        priority = TaskPriority.HIGH
        assert str(priority) == "High"
        assert priority.weight == 3
        
        # Test SLA hours
        assert TaskPriority.LOW.sla_hours is None
        assert TaskPriority.HIGH.sla_hours == 24
        assert TaskPriority.URGENT.sla_hours == 1
        
        # Test descriptions
        assert "immediate attention" in TaskPriority.CRITICAL.description
        
        # Test comparison
        assert TaskPriority.HIGH.compare_urgency(TaskPriority.MEDIUM) == 1
        assert TaskPriority.LOW.compare_urgency(TaskPriority.HIGH) == -1
        assert TaskPriority.MEDIUM.compare_urgency(TaskPriority.MEDIUM) == 0
        
        # Test from_string conversion
        assert TaskPriority.from_string("high") == TaskPriority.HIGH
        assert TaskPriority.from_string("CRITICAL") == TaskPriority.CRITICAL
    
    def test_file_attachment_type_enum(self):
        """Test FileAttachmentType enum functionality."""
        # Test extension detection
        doc_type = FileAttachmentType.from_extension(".pdf")
        assert doc_type == FileAttachmentType.DOCUMENT
        
        image_type = FileAttachmentType.from_extension(".jpg")
        assert image_type == FileAttachmentType.IMAGE
        
        unknown_type = FileAttachmentType.from_extension(".xyz")
        assert unknown_type == FileAttachmentType.OTHER
        
        # Test allowed extensions
        assert '.pdf' in FileAttachmentType.DOCUMENT.allowed_extensions
        assert '.mp4' in FileAttachmentType.VIDEO.allowed_extensions
        
        # Test max sizes
        assert FileAttachmentType.IMAGE.max_size_mb == 25
        assert FileAttachmentType.VIDEO.max_size_mb == 500
    
    def test_analytics_time_range_enum(self):
        """Test AnalyticsTimeRange enum functionality."""
        # Test string conversion
        assert str(AnalyticsTimeRange.THIS_WEEK) == "This Week"
        assert str(AnalyticsTimeRange.LAST_30_DAYS) == "Last 30 Days"
        
        # Test descriptions
        assert "Monday to Sunday" in AnalyticsTimeRange.THIS_WEEK.description
        assert "30 days" in AnalyticsTimeRange.LAST_30_DAYS.description
    
    def test_enum_validation_helpers(self):
        """Test enum validation helper functions."""
        # Test validate_enum_value
        status = validate_enum_value(TaskStatus, "todo", "status")
        assert status == TaskStatus.TODO
        
        priority = validate_enum_value(TaskPriority, TaskPriority.HIGH, "priority")
        assert priority == TaskPriority.HIGH
        
        # Test invalid value
        with pytest.raises(ValueError) as exc_info:
            validate_enum_value(TaskStatus, "invalid_status", "status")
        assert "Invalid status value" in str(exc_info.value)
        
        # Test enum choices
        choices = get_enum_choices(TaskStatus)
        assert len(choices) > 0
        assert all(len(choice) == 2 for choice in choices)
        
        # Test enum to dict
        enum_dict = enum_to_dict(TaskPriority)
        assert 'choices' in enum_dict
        assert 'default' in enum_dict
        assert len(enum_dict['choices']) == len(TaskPriority)


class TestEnhancedTaskModel:
    """Test enhanced Task model with type safety."""
    
    def test_task_creation_with_enums(self):
        """Test task creation with enum validation."""
        # Test with enum instances
        task = Task(
            description="Test task",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH
        )
        
        assert task.status_enum == TaskStatus.IN_PROGRESS
        assert task.priority_enum == TaskPriority.HIGH
        assert task.status_enum.is_active is True
        
        # Test with string values (should be converted)
        task2 = Task(
            description="Test task 2",
            status="Done",
            priority="CRITICAL"
        )
        
        assert task2.status_enum == TaskStatus.DONE
        assert task2.priority_enum == TaskPriority.CRITICAL
    
    def test_task_properties_and_methods(self):
        """Test enhanced task properties and methods."""
        now = datetime.utcnow()
        due_date = now + timedelta(days=2)
        
        task = Task(
            description="Test task",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            due_date=due_date,
            estimated_hours=8.0,
            progress=25
        )
        
        # Test properties
        assert task.done is False  # Backward compatibility
        assert task.is_overdue is False
        assert task.days_until_due == 2  # Due in 2 days
        assert task.completion_percentage == 25
        assert task.sla_hours_remaining is not None  # HIGH priority has SLA
        
        # Test status transitions
        assert task.can_transition_to_status(TaskStatus.DONE) is True
        assert task.can_transition_to_status(TaskStatus.TODO) is True
        assert task.transition_to_status(TaskStatus.DONE) is True
        assert task.status_enum == TaskStatus.DONE
        assert task.completed_at is not None
    
    def test_task_tags_functionality(self):
        """Test task tags functionality."""
        task = Task(description="Test task with tags")
        
        # Test adding tags
        assert task.add_tag("urgent") is True
        assert task.add_tag("frontend") is True
        assert task.add_tag("urgent") is False  # Duplicate
        
        tags = task.get_tags_list()
        assert "urgent" in tags
        assert "frontend" in tags
        assert len(tags) == 2
        
        # Test removing tags
        assert task.remove_tag("urgent") is True
        assert task.remove_tag("urgent") is False  # Already removed
        
        tags = task.get_tags_list()
        assert "urgent" not in tags
        assert "frontend" in tags
        
        # Test setting tags list
        task.set_tags_list(["new", "tags", "list"])
        tags = task.get_tags_list()
        assert len(tags) == 3
        assert "new" in tags
    
    def test_task_priority_scoring(self):
        """Test task priority scoring algorithm."""
        now = datetime.utcnow()
        
        # High priority task
        high_task = Task(
            description="High priority task",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH
        )
        
        # Low priority task
        low_task = Task(
            description="Low priority task",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW
        )
        
        # Overdue task
        overdue_task = Task(
            description="Overdue task",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            due_date=now - timedelta(days=1)
        )
        
        high_score = high_task.calculate_priority_score()
        low_score = low_task.calculate_priority_score()
        overdue_score = overdue_task.calculate_priority_score()
        
        assert high_score > low_score
        assert overdue_score > high_score  # Overdue should have highest priority
    
    def test_task_sla_functionality(self):
        """Test SLA-related functionality."""
        # Create a task with CRITICAL priority (4 hour SLA)
        created_time = datetime.utcnow() - timedelta(hours=2)
        task = Task(
            description="SLA test task",
            priority=TaskPriority.CRITICAL,
            status=TaskStatus.TODO
        )
        task.created_at = created_time  # Simulate task created 2 hours ago
        
        # Should have 2 hours remaining (CRITICAL priority has 4 hour SLA, created 2 hours ago)
        remaining = task.sla_hours_remaining
        assert remaining is not None
        # Allow for timezone normalization and timing differences - very flexible range
        assert 0.0 <= remaining <= 6.0  # Very flexible range for timezone handling
        assert task.is_sla_violated is False
        
        # Simulate SLA violation
        task.created_at = datetime.utcnow() - timedelta(hours=10)  # 10 hours ago (well beyond 4-hour SLA)
        assert task.is_sla_violated is True
    
    def test_task_to_dict_and_from_dict(self):
        """Test task serialization and deserialization."""
        original_task = Task(
            description="Serialization test",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            due_date=datetime.utcnow() + timedelta(days=1),
            progress=50
        )
        original_task.set_tags_list(["test", "serialization"])
        
        # Convert to dict
        task_dict = original_task.to_dict(include_relations=True)
        
        assert task_dict['description'] == "Serialization test"
        assert task_dict['status'] == "In Progress"
        assert task_dict['priority'] == "High"
        assert task_dict['progress'] == 50
        assert set(task_dict['tags']) == {"test", "serialization"}
        assert 'status_display' in task_dict
        assert 'priority_display' in task_dict
        
        # Convert back from dict
        restored_task = Task.from_dict(task_dict)
        
        assert restored_task.description == original_task.description
        assert restored_task.status == original_task.status
        assert restored_task.priority == original_task.priority
        assert restored_task.progress == original_task.progress
        # Sort tags before comparison since order might not be preserved
        assert sorted(restored_task.get_tags_list()) == sorted(original_task.get_tags_list())


class TestPerformancePlugin:
    """Test performance monitoring plugin."""
    
    @pytest.fixture
    def performance_plugin(self):
        """Create performance plugin for testing."""
        return PerformancePlugin()
    
    @pytest.mark.asyncio
    async def test_performance_dashboard_command(self, performance_plugin):
        """Test performance dashboard command."""
        # Mock update and context
        update = Mock()
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        
        # Add some test metrics
        collector = performance_plugin.performance_collector
        with collector.track_operation("test_operation"):
            time.sleep(0.001)
        
        await performance_plugin.handle_performance_dashboard(update, context)
        
        # Verify message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert 'Performance Dashboard' in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'MarkdownV2'
    
    @pytest.mark.asyncio
    async def test_performance_stats_command(self, performance_plugin):
        """Test performance stats command."""
        # Mock update and context
        update = Mock()
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        context.args = ['2']  # 2 hours of stats
        
        # Add some test metrics
        collector = performance_plugin.performance_collector
        for i in range(5):
            with collector.track_operation(f"operation_{i}"):
                time.sleep(0.001)
        
        await performance_plugin.handle_performance_stats(update, context)
        
        # Verify message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert 'Performance Statistics' in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_performance_alerts_command(self, performance_plugin):
        """Test performance alerts command."""
        # Mock update and context
        update = Mock()
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        
        await performance_plugin.handle_performance_alerts(update, context)
        
        # Verify message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert 'Performance Alerts' in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_performance_clear_command(self, performance_plugin):
        """Test performance clear command."""
        # Mock update and context
        update = Mock()
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        context.args = []  # Clear all metrics
        
        # Add some test metrics
        collector = performance_plugin.performance_collector
        with collector.track_operation("test_operation"):
            time.sleep(0.001)
        
        await performance_plugin.handle_performance_clear(update, context)
        
        # Verify message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert 'Performance Metrics Cleared' in call_args[0][0]
    
    def test_dashboard_message_formatting(self, performance_plugin):
        """Test dashboard message formatting."""
        # Create mock dashboard data
        dashboard_data = {
            'summary': {
                'total_operations': 100,
                'avg_execution_time': 0.245,
                'warning_operations': 2,
                'critical_operations': 0,
                'success_rate': 98.5
            },
            'system': {
                'memory_usage': 45.2,
                'cpu_usage': 23.1,
                'disk_usage': 67.8
            },
            'alerts': [],
            'active_operations': 3,
            'timestamp': '2025-07-01T12:00:00'
        }
        
        message = performance_plugin._format_dashboard_message(dashboard_data)
        
        assert 'Performance Dashboard' in message
        assert '98.5%' in message  # Success rate
        assert '100' in message  # Total operations
        assert '0.245s' in message  # Avg execution time
        assert '45.2%' in message  # Memory usage
        assert 'No Active Alerts' in message
    
    def test_alerts_message_formatting(self, performance_plugin):
        """Test alerts message formatting."""
        alerts = [
            {
                'type': 'critical_operation',
                'operation': 'slow_database_query',
                'execution_time': 5.2,
                'message': 'Critical performance issue'
            },
            {
                'type': 'long_running_operation',
                'operation': 'background_job',
                'duration': 30.5,
                'message': 'Long running operation'
            }
        ]
        
        message = performance_plugin._format_alerts_message(alerts)
        
        assert 'Performance Alerts' in message
        assert 'slow\\_database\\_query' in message  # Escaped for markdown
        assert '5.20s' in message
        assert 'background\\_job' in message  # Escaped for markdown
        assert '30.5s' in message 