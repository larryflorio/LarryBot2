import pytest
from unittest.mock import Mock, patch, AsyncMock
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes
from larrybot.plugins.performance import (
    handle_perf_refresh_callback, handle_perf_dashboard_callback,
    handle_perf_details_callback, handle_perf_alerts_callback,
    handle_perf_alerts_refresh_callback, handle_perf_trends_callback,
    handle_perf_clear_callback, handle_perf_export_callback,
    PerformancePlugin
)


class TestPerformanceCallbacks:
    """Test the performance callback handlers."""

    @pytest.fixture
    def mock_query(self):
        """Create a mock callback query."""
        query = Mock()
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.data = 'perf_refresh'
        return query

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    @pytest.fixture
    def mock_performance_collector(self):
        """Create a mock performance collector."""
        collector = Mock()
        collector.get_performance_dashboard.return_value = {
            'timestamp': '2025-01-01 12:00:00',
            'active_operations': 5,
            'alerts': [],
            'operations': {
                'test_operation': {'count': 10, 'avg_time': 0.1}
            },
            'top_operations': {
                'slowest_operations': [],
                'most_frequent': []
            }
        }
        collector.export_metrics.return_value = [
            {'operation_name': 'test', 'execution_time': 0.1, 'memory_usage': 1024}
        ]
        collector.clear_metrics.return_value = 10
        return collector

    @pytest.mark.asyncio
    @patch('larrybot.plugins.performance.get_performance_collector')
    async def test_perf_refresh_callback_success(self, mock_get_collector, mock_query, mock_context, mock_performance_collector):
        """Test successful performance refresh callback."""
        mock_get_collector.return_value = mock_performance_collector
        
        await handle_perf_refresh_callback(mock_query, mock_context)
        
        mock_query.answer.assert_called_once_with("Dashboard refreshed!")
        mock_query.edit_message_text.assert_called_once()
        # Verify the message contains dashboard content
        call_args = mock_query.edit_message_text.call_args
        assert 'MarkdownV2' in call_args[1]['parse_mode']

    @pytest.mark.asyncio
    @patch('larrybot.plugins.performance.get_performance_collector')
    @patch('larrybot.plugins.performance._performance_plugin', None)
    async def test_perf_refresh_callback_error(self, mock_get_collector, mock_query, mock_context):
        """Test performance refresh callback with error."""
        # Create a mock collector that raises an exception when get_performance_dashboard is called
        mock_collector = Mock()
        mock_collector.get_performance_dashboard.side_effect = Exception("Test error")
        mock_get_collector.return_value = mock_collector
        
        await handle_perf_refresh_callback(mock_query, mock_context)
        
        mock_query.answer.assert_called_once_with("Failed to refresh dashboard")
        mock_query.edit_message_text.assert_called_once()
        # Verify error message
        call_args = mock_query.edit_message_text.call_args
        assert 'Error' in call_args[0][0]

    @pytest.mark.asyncio
    @patch('larrybot.plugins.performance.get_performance_collector')
    async def test_perf_dashboard_callback_success(self, mock_get_collector, mock_query, mock_context, mock_performance_collector):
        """Test successful performance dashboard callback."""
        mock_query.data = 'perf_dashboard'
        mock_get_collector.return_value = mock_performance_collector
        
        await handle_perf_dashboard_callback(mock_query, mock_context)
        
        mock_query.answer.assert_called_once_with("Dashboard loaded!")
        mock_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    @patch('larrybot.plugins.performance.get_performance_collector')
    async def test_perf_details_callback_success(self, mock_get_collector, mock_query, mock_context, mock_performance_collector):
        """Test successful performance details callback."""
        mock_query.data = 'perf_details'
        mock_get_collector.return_value = mock_performance_collector
        
        await handle_perf_details_callback(mock_query, mock_context)
        
        mock_query.answer.assert_called_once_with("Details loaded!")
        mock_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    @patch('larrybot.plugins.performance.get_performance_collector')
    async def test_perf_alerts_callback_no_alerts(self, mock_get_collector, mock_query, mock_context, mock_performance_collector):
        """Test performance alerts callback with no alerts."""
        mock_query.data = 'perf_alerts'
        mock_get_collector.return_value = mock_performance_collector
        
        await handle_perf_alerts_callback(mock_query, mock_context)
        
        mock_query.answer.assert_called_once_with("Alerts loaded!")
        mock_query.edit_message_text.assert_called_once()
        # Verify no alerts message
        call_args = mock_query.edit_message_text.call_args
        assert 'No active performance alerts' in call_args[0][0]

    @pytest.mark.asyncio
    @patch('larrybot.plugins.performance.get_performance_collector')
    async def test_perf_alerts_callback_with_alerts(self, mock_get_collector, mock_query, mock_context):
        """Test performance alerts callback with alerts."""
        mock_query.data = 'perf_alerts'
        collector = Mock()
        collector.get_performance_dashboard.return_value = {
            'alerts': [
                {
                    'type': 'critical_operation',
                    'operation': 'test_op',
                    'message': 'Test alert',
                    'execution_time': 5.0
                }
            ]
        }
        mock_get_collector.return_value = collector
        
        await handle_perf_alerts_callback(mock_query, mock_context)
        
        mock_query.answer.assert_called_once_with("Alerts loaded!")
        mock_query.edit_message_text.assert_called_once()
        # Verify alerts message
        call_args = mock_query.edit_message_text.call_args
        assert 'Performance Alerts' in call_args[0][0]

    @pytest.mark.asyncio
    @patch('larrybot.plugins.performance.get_performance_collector')
    async def test_perf_clear_callback_success(self, mock_get_collector, mock_query, mock_context, mock_performance_collector):
        """Test successful performance clear callback."""
        mock_query.data = 'perf_clear'
        mock_get_collector.return_value = mock_performance_collector
        
        await handle_perf_clear_callback(mock_query, mock_context)
        
        mock_query.answer.assert_called_once_with("Cleared 10 metrics!")
        mock_query.edit_message_text.assert_called_once()
        # Verify clear message
        call_args = mock_query.edit_message_text.call_args
        assert 'Performance Metrics Cleared' in call_args[0][0]

    @pytest.mark.asyncio
    @patch('larrybot.plugins.performance.get_performance_collector')
    async def test_perf_export_callback_with_data(self, mock_get_collector, mock_query, mock_context, mock_performance_collector):
        """Test performance export callback with data."""
        mock_query.data = 'perf_export'
        mock_get_collector.return_value = mock_performance_collector
        
        await handle_perf_export_callback(mock_query, mock_context)
        
        mock_query.answer.assert_called_once_with("Exported 1 metrics!")
        mock_query.edit_message_text.assert_called_once()
        # Verify export message
        call_args = mock_query.edit_message_text.call_args
        assert 'Performance Export' in call_args[0][0]

    @pytest.mark.asyncio
    @patch('larrybot.plugins.performance.get_performance_collector')
    @patch('larrybot.plugins.performance._performance_plugin', None)
    async def test_perf_export_callback_no_data(self, mock_get_collector, mock_query, mock_context):
        """Test performance export callback with no data."""
        mock_query.data = 'perf_export'
        collector = Mock()
        collector.export_metrics.return_value = []
        mock_get_collector.return_value = collector
        
        await handle_perf_export_callback(mock_query, mock_context)
        
        mock_query.answer.assert_called_once_with("Exported 0 metrics!")
        mock_query.edit_message_text.assert_called_once()
        # Verify no data message
        call_args = mock_query.edit_message_text.call_args
        assert 'No performance data available' in call_args[0][0]

    def test_performance_plugin_initialization(self):
        """Test PerformancePlugin initialization."""
        plugin = PerformancePlugin()
        assert plugin.performance_collector is not None

    def test_performance_plugin_format_methods(self):
        """Test PerformancePlugin formatting methods."""
        plugin = PerformancePlugin()
        
        # Test dashboard message formatting
        dashboard_data = {
            'timestamp': '2025-01-01 12:00:00',
            'active_operations': 5,
            'alerts': [],
            'operations': {},
            'top_operations': {}
        }
        message = plugin._format_dashboard_message(dashboard_data)
        assert 'Performance Dashboard' in message
        
        # Test alerts message formatting
        alerts = [
            {
                'type': 'critical_operation',
                'operation': 'test_op',
                'message': 'Test alert',
                'execution_time': 5.0
            }
        ]
        message = plugin._format_alerts_message(alerts)
        assert 'Performance Alerts' in message
        
        # Test trends message formatting
        trends = {'execution_times': [0.1, 0.2], 'memory_usage': [100, 200], 'cache_hit_rates': [0.8, 0.9]}
        message = plugin._format_trends_message(trends)
        assert 'Performance Trends' in message 