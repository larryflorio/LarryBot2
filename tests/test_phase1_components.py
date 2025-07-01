"""
Tests for Phase 1 components: Performance & Monitoring.

This module tests the metrics collection system, health service, and health plugin.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import psutil
import sqlite3
import os

from larrybot.core.metrics import MetricsCollector, CommandMetrics, SystemMetrics
from larrybot.services.health_service import HealthService
from larrybot.core.dependency_injection import DependencyContainer, ServiceLocator
from larrybot.models.metrics import CommandMetric, SystemMetric, UserActivityMetric
from larrybot.storage.db import get_session
from sqlalchemy.orm import Session


class TestMetricsCollection:
    """Test metrics collection functionality."""
    
    def test_record_command_metrics(self):
        """Test recording command metrics."""
        collector = MetricsCollector()
        
        # Record a command
        collector.record_command(
            command="/test",
            execution_time=1.5,
            success=True
        )
        
        assert len(collector.command_metrics) == 1
        metric = collector.command_metrics[0]
        assert metric.command == "/test"
        assert metric.execution_time == 1.5
        assert metric.success is True
        assert metric.error_message is None
    
    def test_record_failed_command_metrics(self):
        """Test recording failed command metrics."""
        collector = MetricsCollector()
        
        # Record a failed command
        collector.record_command(
            command="/test",
            execution_time=0.5,
            success=False,
            error_message="Test error"
        )
        
        assert len(collector.command_metrics) == 1
        metric = collector.command_metrics[0]
        assert metric.command == "/test"
        assert metric.execution_time == 0.5
        assert metric.success is False
        assert metric.error_message == "Test error"
    
    def test_record_system_metrics(self):
        """Test recording system metrics."""
        collector = MetricsCollector()
        
        # Record system metrics
        collector.record_system_metrics()
        
        assert len(collector.system_metrics) == 1
        metric = collector.system_metrics[0]
        assert isinstance(metric.memory_usage, float)
        assert isinstance(metric.cpu_usage, float)
        assert isinstance(metric.active_connections, int)
        assert isinstance(metric.timestamp, datetime)
    
    def test_get_command_stats(self):
        """Test getting command statistics."""
        collector = MetricsCollector()
        
        # Add some test metrics
        collector.record_command("/test1", 1.0, True)
        collector.record_command("/test2", 2.0, True)
        collector.record_command("/test1", 0.5, False, "Error")
        
        stats = collector.get_command_stats(hours=24)
        
        assert stats["total_commands"] == 3
        assert stats["successful_commands"] == 2
        assert stats["failed_commands"] == 1
        assert stats["commands_by_type"]["/test1"] == 2
        assert stats["commands_by_type"]["/test2"] == 1
        assert stats["error_rate"] == 33.33
    
    def test_get_user_activity(self):
        """Test getting user activity statistics."""
        collector = MetricsCollector()
        
        # Add some test metrics
        collector.record_command("/test1", 1.0, True)
        collector.record_command("/test2", 2.0, True)
        collector.record_command("/test1", 0.5, False, "Error")
        
        activity = collector.get_user_activity(hours=24)
        
        assert activity["total_commands"] == 3
        assert activity["successful_commands"] == 2
        assert activity["failed_commands"] == 1
        assert "3 commands in last 24h" in activity["activity_summary"]
    
    def test_clear_old_metrics(self):
        """Test clearing old metrics."""
        collector = MetricsCollector()
        
        # Add some metrics
        collector.record_command("/test", 1.0, True)
        collector.record_system_metrics()
        
        assert len(collector.command_metrics) == 1
        assert len(collector.system_metrics) == 1
        
        # Clear old metrics
        collector.clear_old_metrics(hours=0)  # Clear all
        
        assert len(collector.command_metrics) == 0
        assert len(collector.system_metrics) == 0


class TestHealthService:
    """Test cases for HealthService."""
    
    @pytest.fixture
    def health_service(self):
        """Create a HealthService instance for testing."""
        return HealthService(":memory:", plugin_manager=None)
    
    @pytest.mark.asyncio
    async def test_get_system_health(self, health_service):
        """Test getting comprehensive system health."""
        health = await health_service.get_system_health()
        
        assert "database" in health
        assert "memory" in health
        assert "cpu" in health
        assert "disk" in health
        assert "plugins" in health
        assert "overall_status" in health
        assert "timestamp" in health
    
    @pytest.mark.asyncio
    async def test_check_database_health_memory_db(self, health_service):
        """Test database health check with in-memory database."""
        db_health = await health_service._check_database_health()
        
        # In-memory database should be healthy but may not have tables
        assert db_health["status"] in ["healthy", "critical"]
        assert "connection" in db_health
    
    @pytest.mark.asyncio
    async def test_check_database_health_missing_file(self, health_service):
        """Test database health check with missing file."""
        health_service.database_path = "/nonexistent/path/db.sqlite"
        db_health = await health_service._check_database_health()
        
        assert db_health["status"] == "critical"
        assert db_health["connection"] == "failed"
        assert (
            "Database file not found" in db_health["error"]
            or "unable to open database file" in db_health["error"]
        )
    
    @patch('psutil.virtual_memory')
    def test_check_memory_health(self, mock_virtual_memory, health_service):
        """Test memory health check."""
        # Mock memory usage
        mock_memory = Mock()
        mock_memory.percent = 75.5
        mock_memory.available = 4 * 1024**3  # 4 GB
        mock_memory.total = 16 * 1024**3     # 16 GB
        mock_memory.used = 12 * 1024**3      # 12 GB
        mock_virtual_memory.return_value = mock_memory
        
        memory_health = health_service._check_memory_health()
        
        assert memory_health["status"] == "healthy"
        assert memory_health["usage_percent"] == 75.5
        assert memory_health["available_gb"] == 4.0
        assert memory_health["total_gb"] == 16.0
        assert memory_health["used_gb"] == 12.0
    
    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_count')
    def test_check_cpu_health(self, mock_cpu_count, mock_cpu_percent, health_service):
        """Test CPU health check."""
        # Mock CPU usage
        mock_cpu_percent.return_value = 45.2
        mock_cpu_count.return_value = 8
        
        cpu_health = health_service._check_cpu_health()
        
        assert cpu_health["status"] == "healthy"  # 45.2% < 80% threshold
        assert cpu_health["usage_percent"] == 45.2
        assert cpu_health["cpu_count"] == 8
    
    @patch('psutil.disk_usage')
    def test_check_disk_health(self, mock_disk_usage, health_service):
        """Test disk health check."""
        # Mock disk usage
        mock_disk = Mock()
        mock_disk.percent = 70.0
        mock_disk.free = 100 * 1024**3  # 100 GB
        mock_disk.total = 500 * 1024**3 # 500 GB
        mock_disk.used = 400 * 1024**3  # 400 GB
        mock_disk_usage.return_value = mock_disk
        
        disk_health = health_service._check_disk_health()
        
        assert disk_health["status"] == "healthy"  # 70% < 85% threshold
        assert disk_health["usage_percent"] == 70.0
        assert disk_health["free_gb"] == 100.0
        assert disk_health["total_gb"] == 500.0
        assert disk_health["used_gb"] == 400.0
    
    @pytest.mark.asyncio
    async def test_check_plugins_health_no_manager(self, health_service):
        """Test plugin health check without plugin manager."""
        plugins_health = await health_service._check_plugins_health()
        
        assert plugins_health["status"] == "warning"
        assert plugins_health["loaded_plugins"] == 5
        assert plugins_health["enabled_plugins"] == 5
        assert "Plugin manager not available" in plugins_health["note"]
    
    @pytest.mark.asyncio
    async def test_check_plugins_health_with_manager(self, health_service):
        """Test plugin health check with plugin manager."""
        # Mock plugin manager
        mock_plugin_manager = Mock()
        mock_plugin_manager.get_loaded_plugins.return_value = [
            {"name": "tasks", "enabled": True},
            {"name": "client", "enabled": True},
            {"name": "habit", "enabled": False},
        ]
        
        health_service.plugin_manager = mock_plugin_manager
        plugins_health = await health_service._check_plugins_health()
        
        assert plugins_health["status"] == "healthy"
        assert plugins_health["loaded_plugins"] == 3
        assert plugins_health["enabled_plugins"] == 2
        assert "tasks" in plugins_health["plugin_names"]
    
    def test_determine_overall_status(self, health_service):
        """Test overall status determination."""
        # Test healthy status
        health_checks = {
            "database": {"status": "healthy"},
            "memory": {"status": "healthy"},
            "cpu": {"status": "healthy"},
        }
        status = health_service._determine_overall_status(health_checks)
        assert status == "healthy"
        
        # Test warning status
        health_checks["memory"]["status"] = "warning"
        status = health_service._determine_overall_status(health_checks)
        assert status == "warning"
        
        # Test critical status
        health_checks["database"]["status"] = "critical"
        status = health_service._determine_overall_status(health_checks)
        assert status == "critical"
    
    @pytest.mark.asyncio
    async def test_get_quick_health(self, health_service):
        """Test quick health check."""
        quick_health = await health_service.get_quick_health()
        
        assert "database" in quick_health
        assert "memory" in quick_health
        assert "timestamp" in quick_health
        assert "cpu" not in quick_health  # Not included in quick health
        assert "disk" not in quick_health  # Not included in quick health


class TestHealthPlugin:
    """Test cases for health plugin commands."""
    
    @pytest.fixture
    def mock_health_service(self):
        """Create a mock health service."""
        service = AsyncMock()
        service.get_system_health.return_value = {
            "overall_status": "healthy",
            "database": {
                "status": "healthy",
                "task_count": 10,
                "client_count": 3,
                "habit_count": 5,
                "database_size_mb": 2.5,
                "connection": "ok"
            },
            "memory": {
                "status": "healthy",
                "usage_percent": 65.5,
                "available_gb": 8.5,
                "total_gb": 16.0,
                "used_gb": 7.5
            },
            "cpu": {
                "status": "healthy",
                "usage_percent": 45.2,
                "cpu_count": 8
            },
            "disk": {
                "status": "healthy",
                "usage_percent": 70.0,
                "free_gb": 100.0,
                "total_gb": 500.0,
                "used_gb": 400.0
            },
            "plugins": {
                "status": "healthy",
                "loaded_plugins": 5,
                "enabled_plugins": 5,
                "plugin_names": ["tasks", "client", "habit", "reminder", "calendar"]
            }
        }
        return service
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock update object."""
        update = Mock()
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock context object."""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_health_check_command(self, mock_health_service, mock_update, mock_context):
        """Test /health command."""
        from larrybot.plugins.health import health_check
        
        # Mock ServiceLocator
        with patch('larrybot.plugins.health.ServiceLocator') as mock_service_locator:
            mock_service_locator.get.return_value = mock_health_service
            
            await health_check(mock_update, mock_context)
            
            # Verify service was called
            mock_health_service.get_system_health.assert_called_once()
            
            # Verify message was sent
            mock_update.message.reply_text.assert_called_once()
            message = mock_update.message.reply_text.call_args[0][0]
            
            # Check that the message contains expected content
            assert "System Health Status" in message
            assert "🟢" in message  # Healthy status emoji
            assert "Database" in message
            assert "Memory" in message
            assert "CPU" in message
            assert "Disk" in message
            assert "Plugins" in message
    
    @pytest.mark.asyncio
    async def test_health_check_command_error(self, mock_update, mock_context):
        """Test /health command with error."""
        from larrybot.plugins.health import health_check
        
        # Mock ServiceLocator to raise exception
        with patch('larrybot.plugins.health.ServiceLocator') as mock_service_locator:
            mock_service_locator.get.side_effect = Exception("Service not found")
            
            await health_check(mock_update, mock_context)
            
            # Verify error message was sent
            mock_update.message.reply_text.assert_called_once()
            message = mock_update.message.reply_text.call_args[0][0]
            assert "Health Check Failed" in message
            assert "Service not found" in message
    
    @pytest.mark.asyncio
    async def test_quick_health_check_command(self, mock_health_service, mock_update, mock_context):
        """Test /health_quick command."""
        from larrybot.plugins.health import quick_health_check
        
        # Mock quick health response
        mock_health_service.get_quick_health.return_value = {
            "database": {
                "status": "healthy",
                "task_count": 10
            },
            "memory": {
                "status": "healthy",
                "usage_percent": 65.5
            }
        }
        
        # Mock ServiceLocator
        with patch('larrybot.plugins.health.ServiceLocator') as mock_service_locator:
            mock_service_locator.get.return_value = mock_health_service
            
            await quick_health_check(mock_update, mock_context)
            
            # Verify service was called
            mock_health_service.get_quick_health.assert_called_once()
            
            # Verify message was sent
            mock_update.message.reply_text.assert_called_once()
            message = mock_update.message.reply_text.call_args[0][0]
            
            assert "Quick Health Status" in message
            assert "Database" in message
            assert "Memory" in message


class TestIntegration:
    """Integration tests for Phase 1 components."""
    
    @pytest.mark.asyncio
    async def test_metrics_collector_integration(self):
        """Test metrics collector integration with dependency injection."""
        # Set up dependency injection
        container = DependencyContainer()
        metrics_collector = MetricsCollector()
        container.register_singleton("metrics_collector", metrics_collector)
        ServiceLocator.set_container(container)
        
        # Test metrics collection
        metrics_collector.record_command("/test", 0.5, True)
        
        # Mock system metrics to avoid permission issues
        with patch('psutil.net_connections') as mock_net_connections:
            mock_net_connections.return_value = []
            metrics_collector.record_system_metrics()
        
        # Verify metrics were recorded
        assert len(metrics_collector.command_metrics) == 1
        assert len(metrics_collector.system_metrics) == 1
        
        # Test statistics
        command_stats = metrics_collector.get_command_stats()
        assert command_stats["total_commands"] == 1
        assert command_stats["successful_commands"] == 1
    
    @pytest.mark.asyncio
    async def test_health_service_integration(self):
        """Test health service integration."""
        # Create health service with in-memory database
        health_service = HealthService(":memory:")
        
        # Test health check
        health = await health_service.get_system_health()
        
        # Verify all components are present
        required_components = ["database", "memory", "cpu", "disk", "plugins", "overall_status"]
        for component in required_components:
            assert component in health
        
        # Verify overall status is determined
        assert health["overall_status"] in ["healthy", "warning", "critical"] 