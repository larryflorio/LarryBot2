"""
Performance Monitoring Plugin for LarryBot2 Phase 2

This plugin provides commands to view performance metrics, monitoring dashboard,
and system health information for enterprise-grade performance analysis.
"""

import asyncio
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from larrybot.core.performance import get_performance_collector, track_performance
from larrybot.core.dependency_injection import ServiceLocator
from larrybot.utils.ux_helpers import performance_monitor

def escape_markdown_v2(text: str) -> str:
    """Escape MarkdownV2 special characters."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_standardized_error(error_type: str, message: str, details: str = "") -> str:
    """Format a standardized error message for Telegram."""
    return f"❌ *Error*: {escape_markdown_v2(message)}"
import logging

logger = logging.getLogger(__name__)


class PerformancePlugin:
    """Performance monitoring and dashboard plugin."""
    
    def __init__(self):
        self.performance_collector = get_performance_collector()
    
    async def handle_performance_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Display comprehensive performance dashboard."""
        async with performance_monitor("performance_dashboard_command"):
            try:
                dashboard_data = self.performance_collector.get_performance_dashboard()
                
                # Format dashboard message
                message = self._format_dashboard_message(dashboard_data)
                
                # Create navigation keyboard
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="perf_refresh"),
                        InlineKeyboardButton("📊 Details", callback_data="perf_details")
                    ],
                    [
                        InlineKeyboardButton("⚠️ Alerts", callback_data="perf_alerts"),
                        InlineKeyboardButton("📈 Trends", callback_data="perf_trends")
                    ],
                    [
                        InlineKeyboardButton("🧹 Clear Metrics", callback_data="perf_clear"),
                        InlineKeyboardButton("📤 Export", callback_data="perf_export")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    message,
                    parse_mode='MarkdownV2',
                    reply_markup=reply_markup
                )
                
            except Exception as e:
                logger.error(f"Error in performance dashboard: {e}")
                error_msg = format_standardized_error(
                    "performance_error",
                    "Failed to load performance dashboard",
                    str(e)
                )
                await update.message.reply_text(error_msg, parse_mode='MarkdownV2')
    
    async def handle_performance_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Display detailed performance statistics."""
        async with performance_monitor("performance_stats_command"):
            try:
                # Get time range from arguments (default: 1 hour)
                hours = 1
                if context.args and len(context.args) > 0:
                    try:
                        hours = int(context.args[0])
                        hours = max(1, min(hours, 168))  # 1 hour to 1 week
                    except ValueError:
                        pass
                
                # Get metrics for specified time range
                metrics = self.performance_collector.export_metrics(hours=hours)
                
                if not metrics:
                    await update.message.reply_text(
                        f"📊 *Performance Statistics*\n\n"
                        f"No performance data available for the last {hours} hour(s)\\.",
                        parse_mode='MarkdownV2'
                    )
                    return
                
                # Calculate statistics
                stats = self._calculate_detailed_stats(metrics)
                message = self._format_stats_message(stats, hours)
                
                await update.message.reply_text(message, parse_mode='MarkdownV2')
                
            except Exception as e:
                logger.error(f"Error in performance stats: {e}")
                error_msg = format_standardized_error(
                    "performance_error",
                    "Failed to load performance statistics",
                    str(e)
                )
                await update.message.reply_text(error_msg, parse_mode='MarkdownV2')
    
    async def handle_performance_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Display current performance alerts."""
        async with performance_monitor("performance_alerts_command"):
            try:
                dashboard_data = self.performance_collector.get_performance_dashboard()
                alerts = dashboard_data.get('alerts', [])
                
                if not alerts:
                    await update.message.reply_text(
                        "🟢 *Performance Alerts*\n\n"
                        "No active performance alerts\\. System is running normally\\.",
                        parse_mode='MarkdownV2'
                    )
                    return
                
                message = self._format_alerts_message(alerts)
                
                # Add action buttons for alerts
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="perf_alerts_refresh"),
                        InlineKeyboardButton("📊 Dashboard", callback_data="perf_dashboard")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    message,
                    parse_mode='MarkdownV2',
                    reply_markup=reply_markup
                )
                
            except Exception as e:
                logger.error(f"Error in performance alerts: {e}")
                error_msg = format_standardized_error(
                    "performance_error",
                    "Failed to load performance alerts",
                    str(e)
                )
                await update.message.reply_text(error_msg, parse_mode='MarkdownV2')
    
    async def handle_performance_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clear performance metrics."""
        async with performance_monitor("performance_clear_command"):
            try:
                # Get hours from arguments (default: clear all)
                hours = None
                if context.args and len(context.args) > 0:
                    try:
                        hours = int(context.args[0])
                        hours = max(1, hours)
                    except ValueError:
                        pass
                
                cleared_count = self.performance_collector.clear_metrics(hours=hours)
                
                if hours is None:
                    message = f"🧹 *Performance Metrics Cleared*\n\n" \
                             f"Cleared all {cleared_count} performance metrics\\."
                else:
                    message = f"🧹 *Performance Metrics Cleared*\n\n" \
                             f"Cleared {cleared_count} metrics older than {hours} hour(s)\\."
                
                await update.message.reply_text(message, parse_mode='MarkdownV2')
                
            except Exception as e:
                logger.error(f"Error clearing performance metrics: {e}")
                error_msg = format_standardized_error(
                    "performance_error",
                    "Failed to clear performance metrics",
                    str(e)
                )
                await update.message.reply_text(error_msg, parse_mode='MarkdownV2')
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle performance-related callback queries."""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        try:
            if callback_data == "perf_refresh" or callback_data == "perf_dashboard":
                dashboard_data = self.performance_collector.get_performance_dashboard()
                message = self._format_dashboard_message(dashboard_data)
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="perf_refresh"),
                        InlineKeyboardButton("📊 Details", callback_data="perf_details")
                    ],
                    [
                        InlineKeyboardButton("⚠️ Alerts", callback_data="perf_alerts"),
                        InlineKeyboardButton("📈 Trends", callback_data="perf_trends")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    message,
                    parse_mode='MarkdownV2',
                    reply_markup=reply_markup
                )
            
            elif callback_data == "perf_alerts" or callback_data == "perf_alerts_refresh":
                dashboard_data = self.performance_collector.get_performance_dashboard()
                alerts = dashboard_data.get('alerts', [])
                
                if not alerts:
                    message = "🟢 *Performance Alerts*\n\n" \
                             "No active performance alerts\\. System is running normally\\."
                else:
                    message = self._format_alerts_message(alerts)
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="perf_alerts_refresh"),
                        InlineKeyboardButton("📊 Dashboard", callback_data="perf_dashboard")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    message,
                    parse_mode='MarkdownV2',
                    reply_markup=reply_markup
                )
            
            elif callback_data == "perf_trends":
                dashboard_data = self.performance_collector.get_performance_dashboard()
                trends = dashboard_data.get('trends', {})
                message = self._format_trends_message(trends)
                
                keyboard = [
                    [
                        InlineKeyboardButton("📊 Dashboard", callback_data="perf_dashboard"),
                        InlineKeyboardButton("🔄 Refresh", callback_data="perf_trends")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    message,
                    parse_mode='MarkdownV2',
                    reply_markup=reply_markup
                )
            
            elif callback_data == "perf_details":
                dashboard_data = self.performance_collector.get_performance_dashboard()
                message = self._format_detailed_dashboard(dashboard_data)
                
                keyboard = [
                    [
                        InlineKeyboardButton("📊 Summary", callback_data="perf_dashboard"),
                        InlineKeyboardButton("🔄 Refresh", callback_data="perf_details")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    message,
                    parse_mode='MarkdownV2',
                    reply_markup=reply_markup
                )
            
        except Exception as e:
            logger.error(f"Error handling performance callback: {e}")
            await query.message.reply_text(
                f"❌ Error handling performance action: {escape_markdown_v2(str(e))}",
                parse_mode='MarkdownV2'
            )
    
    def _format_dashboard_message(self, dashboard_data: Dict[str, Any]) -> str:
        """Format the main dashboard message."""
        summary = dashboard_data.get('summary', {})
        system = dashboard_data.get('system', {})
        alerts = dashboard_data.get('alerts', [])
        
        # Performance status indicator
        success_rate = summary.get('success_rate', 100.0)
        if success_rate >= 95.0:
            status_icon = "🟢"
            status_text = "Excellent"
        elif success_rate >= 85.0:
            status_icon = "🟡"
            status_text = "Good"
        else:
            status_icon = "🔴"
            status_text = "Needs Attention"
        
        message = f"📊 *Performance Dashboard*\n\n"
        
        # Overall status
        message += f"*System Status:* {status_icon} {status_text}\n"
        message += f"*Success Rate:* {success_rate:.1f}%\n\n"
        
        # Summary metrics
        message += f"*Recent Activity \\(1h\\):*\n"
        message += f"• Operations: {summary.get('total_operations', 0)}\n"
        message += f"• Avg Response: {summary.get('avg_execution_time', 0.0):.3f}s\n"
        message += f"• Warnings: {summary.get('warning_operations', 0)}\n"
        message += f"• Critical: {summary.get('critical_operations', 0)}\n\n"
        
        # System resources
        message += f"*System Resources:*\n"
        message += f"• Memory: {system.get('memory_usage', 0.0):.1f}%\n"
        message += f"• CPU: {system.get('cpu_usage', 0.0):.1f}%\n"
        message += f"• Active Ops: {dashboard_data.get('active_operations', 0)}\n\n"
        
        # Alert summary
        if alerts:
            message += f"⚠️ *{len(alerts)} Active Alert(s)*\n"
            message += "Use 'Alerts' button for details\\.\n\n"
        else:
            message += "✅ *No Active Alerts*\n\n"
        
        message += f"*Last Updated:* {escape_markdown_v2(dashboard_data.get('timestamp', 'Unknown'))}"
        
        return message
    
    def _format_alerts_message(self, alerts: List[Dict[str, Any]]) -> str:
        """Format alerts message."""
        message = f"⚠️ *Performance Alerts*\n\n"
        
        for i, alert in enumerate(alerts[:10], 1):  # Limit to 10 alerts
            alert_type = alert.get('type', 'unknown')
            operation = alert.get('operation', 'unknown')
            alert_message = alert.get('message', 'No details available')
            
            if alert_type == 'critical_operation':
                icon = "🔴"
                execution_time = alert.get('execution_time', 0)
                message += f"{icon} *Critical Performance*\n"
                message += f"Operation: `{escape_markdown_v2(operation)}`\n"
                message += f"Time: {execution_time:.2f}s\n\n"
            
            elif alert_type == 'long_running_operation':
                icon = "🟡"
                duration = alert.get('duration', 0)
                message += f"{icon} *Long\\-Running Operation*\n"
                message += f"Operation: `{escape_markdown_v2(operation)}`\n"
                message += f"Duration: {duration:.1f}s\n\n"
        
        if len(alerts) > 10:
            message += f"\\.\\.\\. and {len(alerts) - 10} more alerts\\."
        
        return message
    
    def _format_trends_message(self, trends: Dict[str, Any]) -> str:
        """Format trends message."""
        execution_times = trends.get('execution_times', [])
        memory_usage = trends.get('memory_usage', [])
        cache_hit_rates = trends.get('cache_hit_rates', [])
        
        message = f"📈 *Performance Trends*\n\n"
        
        if not execution_times:
            message += "No trend data available\\."
            return message
        
        # Calculate trend direction
        if len(execution_times) >= 2:
            recent_avg = sum(execution_times[-3:]) / min(3, len(execution_times))
            older_avg = sum(execution_times[:3]) / min(3, len(execution_times))
            
            if recent_avg > older_avg * 1.1:
                trend_icon = "📈"
                trend_text = "Increasing"
            elif recent_avg < older_avg * 0.9:
                trend_icon = "📉"
                trend_text = "Decreasing"
            else:
                trend_icon = "➡️"
                trend_text = "Stable"
        else:
            trend_icon = "➡️"
            trend_text = "Insufficient data"
        
        message += f"*Response Time Trend:* {trend_icon} {trend_text}\n"
        
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            min_time = min(execution_times)
            max_time = max(execution_times)
            
            message += f"• Average: {avg_time:.3f}s\n"
            message += f"• Range: {min_time:.3f}s \\- {max_time:.3f}s\n\n"
        
        if memory_usage:
            avg_memory = sum(memory_usage) / len(memory_usage)
            message += f"*Memory Usage:*\n"
            message += f"• Average: {avg_memory:.1f}MB\n"
            message += f"• Peak: {max(memory_usage):.1f}MB\n\n"
        
        if cache_hit_rates:
            avg_hit_rate = sum(cache_hit_rates) / len(cache_hit_rates)
            message += f"*Cache Performance:*\n"
            message += f"• Hit Rate: {avg_hit_rate:.1%}\n"
        
        return message
    
    def _format_detailed_dashboard(self, dashboard_data: Dict[str, Any]) -> str:
        """Format detailed dashboard with operation breakdown."""
        operations = dashboard_data.get('operations', {})
        top_operations = dashboard_data.get('top_operations', {})
        
        message = f"📊 *Detailed Performance Dashboard*\n\n"
        
        # Top slowest operations
        slowest = top_operations.get('slowest_operations', [])
        if slowest:
            message += f"*Slowest Operations:*\n"
            for i, op in enumerate(slowest[:5], 1):
                operation = op.get('operation', 'unknown')
                avg_time = op.get('avg_time', 0)
                message += f"{i}\\. `{escape_markdown_v2(operation)}`: {avg_time:.3f}s\n"
            message += "\n"
        
        # Most frequent operations
        frequent = top_operations.get('most_frequent', [])
        if frequent:
            message += f"*Most Frequent Operations:*\n"
            for i, op in enumerate(frequent[:5], 1):
                operation = op.get('operation', 'unknown')
                count = op.get('count', 0)
                message += f"{i}\\. `{escape_markdown_v2(operation)}`: {count} calls\n"
            message += "\n"
        
        # Operation details
        if operations:
            message += f"*All Operations:*\n"
            for op_name, stats in list(operations.items())[:10]:  # Limit to 10
                count = stats.get('count', 0)
                avg_time = stats.get('avg_time', 0)
                message += f"• `{escape_markdown_v2(op_name)}`: {count} calls, {avg_time:.3f}s avg\n"
            
            if len(operations) > 10:
                message += f"\\.\\.\\. and {len(operations) - 10} more operations\\."
        
        return message
    
    def _calculate_detailed_stats(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate detailed statistics from metrics."""
        if not metrics:
            return {}
        
        execution_times = [m.get('execution_time', 0) for m in metrics]
        memory_usages = [m.get('memory_usage', 0) for m in metrics]
        
        return {
            'total_operations': len(metrics),
            'avg_execution_time': sum(execution_times) / len(execution_times),
            'min_execution_time': min(execution_times),
            'max_execution_time': max(execution_times),
            'avg_memory_usage': sum(memory_usages) / len(memory_usages),
            'total_memory_usage': sum(memory_usages),
            'operations_by_type': self._group_operations_by_type(metrics)
        }
    
    def _group_operations_by_type(self, metrics: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group operations by type."""
        operation_counts = {}
        for metric in metrics:
            op_name = metric.get('operation_name', 'unknown')
            operation_counts[op_name] = operation_counts.get(op_name, 0) + 1
        return operation_counts
    
    def _format_stats_message(self, stats: Dict[str, Any], hours: int) -> str:
        """Format detailed statistics message."""
        message = f"📊 *Performance Statistics \\({hours}h\\)*\n\n"
        
        if not stats:
            message += "No performance data available\\."
            return message
        
        # Overall statistics
        message += f"*Overall Performance:*\n"
        message += f"• Total Operations: {stats.get('total_operations', 0)}\n"
        message += f"• Average Time: {stats.get('avg_execution_time', 0):.3f}s\n"
        message += f"• Fastest: {stats.get('min_execution_time', 0):.3f}s\n"
        message += f"• Slowest: {stats.get('max_execution_time', 0):.3f}s\n\n"
        
        # Memory statistics
        avg_memory = stats.get('avg_memory_usage', 0) / 1024 / 1024  # Convert to MB
        total_memory = stats.get('total_memory_usage', 0) / 1024 / 1024
        
        message += f"*Memory Usage:*\n"
        message += f"• Average per Operation: {avg_memory:.1f}MB\n"
        message += f"• Total Memory Delta: {total_memory:.1f}MB\n\n"
        
        # Operations breakdown
        operations = stats.get('operations_by_type', {})
        if operations:
            message += f"*Operations Breakdown:*\n"
            # Sort by count descending
            sorted_ops = sorted(operations.items(), key=lambda x: x[1], reverse=True)
            for op_name, count in sorted_ops[:10]:  # Top 10
                percentage = (count / stats['total_operations']) * 100
                message += f"• `{escape_markdown_v2(op_name)}`: {count} \\({percentage:.1f}%\\)\n"
            
            if len(operations) > 10:
                message += f"\\.\\.\\. and {len(operations) - 10} more operation types\\."
        
        return message


def register(event_bus, command_registry, **kwargs):
    """Register the performance monitoring plugin."""
    plugin = PerformancePlugin()
    
    # Register commands
    command_registry.register(
        command="performance",
        handler=plugin.handle_performance_dashboard,
        description="📊 View performance monitoring dashboard"
    )
    
    command_registry.register(
        command="perfstats",
        handler=plugin.handle_performance_stats,
        description="📈 View detailed performance statistics [hours]"
    )
    
    command_registry.register(
        command="perfalerts",
        handler=plugin.handle_performance_alerts,
        description="⚠️ View active performance alerts"
    )
    
    command_registry.register(
        command="perfclear",
        handler=plugin.handle_performance_clear,
        description="🧹 Clear performance metrics [hours]"
    )
    
    # Register callback handler for performance-related callbacks
    command_registry.register_callback_handler(
        pattern=r"^perf_",
        handler=plugin.handle_callback_query
    )
    
    logger.info("Performance monitoring plugin registered successfully") 