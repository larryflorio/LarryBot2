"""
Health monitoring plugin for LarryBot2.

This plugin provides system health monitoring and status reporting
through Telegram commands.
"""

from telegram import Update
from telegram.ext import ContextTypes
from larrybot.utils.decorators import command_handler
from larrybot.services.health_service import HealthService
from larrybot.core.dependency_injection import ServiceLocator
from larrybot.core.event_bus import EventBus
from larrybot.core.command_registry import CommandRegistry, CommandMetadata


@command_handler("/health", "System health status", "Usage: /health", "system")
async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display comprehensive system health status."""
    try:
        health_service = ServiceLocator.get("health_service")
        health_status = await health_service.get_system_health()
        
        # Format health status message
        message = "🏥 **System Health Status**\n\n"
        
        # Overall status
        overall_status = health_status["overall_status"]
        status_emoji = "🟢" if overall_status == "healthy" else "🟡" if overall_status == "warning" else "🔴"
        message += f"{status_emoji} **Overall Status**: {overall_status.upper()}\n\n"
        
        # Database
        db = health_status["database"]
        db_emoji = "🟢" if db["status"] == "healthy" else "🟡" if db["status"] == "warning" else "🔴"
        message += f"{db_emoji} **Database**: {db['status'].upper()}\n"
        message += f"   • Tasks: {db.get('task_count', 'N/A')}\n"
        message += f"   • Clients: {db.get('client_count', 'N/A')}\n"
        message += f"   • Habits: {db.get('habit_count', 'N/A')}\n"
        message += f"   • Size: {db.get('database_size_mb', 'N/A')} MB\n"
        message += f"   • Connection: {db['connection']}\n\n"
        
        # Memory
        memory = health_status["memory"]
        mem_emoji = "🟢" if memory["status"] == "healthy" else "🟡" if memory["status"] == "warning" else "🔴"
        message += f"{mem_emoji} **Memory**: {memory['status'].upper()}\n"
        message += f"   • Usage: {memory['usage_percent']:.1f}%\n"
        message += f"   • Available: {memory['available_gb']:.1f} GB\n"
        message += f"   • Total: {memory['total_gb']:.1f} GB\n\n"
        
        # CPU
        cpu = health_status["cpu"]
        cpu_emoji = "🟢" if cpu["status"] == "healthy" else "🟡" if cpu["status"] == "warning" else "🔴"
        message += f"{cpu_emoji} **CPU**: {cpu['status'].upper()}\n"
        message += f"   • Usage: {cpu['usage_percent']:.1f}%\n"
        message += f"   • Cores: {cpu['cpu_count']}\n\n"
        
        # Disk
        disk = health_status["disk"]
        disk_emoji = "🟢" if disk["status"] == "healthy" else "🟡" if disk["status"] == "warning" else "🔴"
        message += f"{disk_emoji} **Disk**: {disk['status'].upper()}\n"
        message += f"   • Usage: {disk['usage_percent']:.1f}%\n"
        message += f"   • Free: {disk['free_gb']:.1f} GB\n"
        message += f"   • Total: {disk['total_gb']:.1f} GB\n\n"
        
        # Plugins
        plugins = health_status["plugins"]
        plugins_emoji = "🟢" if plugins["status"] == "healthy" else "🟡" if plugins["status"] == "warning" else "🔴"
        message += f"{plugins_emoji} **Plugins**: {plugins['status'].upper()}\n"
        message += f"   • Loaded: {plugins['enabled_plugins']}/{plugins['loaded_plugins']}\n"
        if plugins.get('note'):
            message += f"   • Note: {plugins['note']}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error_message = f"❌ **Health Check Failed**\n\nError: {str(e)}"
        await update.message.reply_text(error_message, parse_mode='Markdown')


@command_handler("/health_quick", "Quick health status", "Usage: /health_quick", "system")
async def quick_health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display quick system health status."""
    try:
        health_service = ServiceLocator.get("health_service")
        health_status = await health_service.get_quick_health()
        
        message = "⚡ **Quick Health Status**\n\n"
        
        # Database
        db = health_status["database"]
        db_emoji = "🟢" if db["status"] == "healthy" else "🟡" if db["status"] == "warning" else "🔴"
        message += f"{db_emoji} **Database**: {db['status'].upper()}\n"
        message += f"   • Tasks: {db.get('task_count', 'N/A')}\n"
        
        # Memory
        memory = health_status["memory"]
        mem_emoji = "🟢" if memory["status"] == "healthy" else "🟡" if memory["status"] == "warning" else "🔴"
        message += f"{mem_emoji} **Memory**: {memory['usage_percent']:.1f}%\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error_message = f"❌ **Quick Health Check Failed**\n\nError: {str(e)}"
        await update.message.reply_text(error_message, parse_mode='Markdown')


@command_handler("/health_detailed", "Detailed health status", "Usage: /health_detailed", "system")
async def detailed_health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display detailed system health status."""
    try:
        health_service = ServiceLocator.get("health_service")
        health_status = await health_service.get_detailed_health()
        
        message = "📊 **Detailed Health Status**\n\n"
        
        # Overall status
        overall_status = health_status["overall_status"]
        status_emoji = "🟢" if overall_status == "healthy" else "🟡" if overall_status == "warning" else "🔴"
        message += f"{status_emoji} **Overall Status**: {overall_status.upper()}\n\n"
        
        # System info
        if "system_info" in health_status:
            sys_info = health_status["system_info"]
            message += "💻 **System Information**\n"
            message += f"   • Platform: {sys_info['platform']}\n"
            message += f"   • Python: {sys_info['python_version'].split()[0]}\n"
            message += f"   • Boot Time: {sys_info['boot_time'][:19]}\n"
            message += f"   • Uptime: {sys_info['uptime_seconds']/3600:.1f} hours\n\n"
        
        # Detailed component status
        for component, status in health_status.items():
            if component in ["overall_status", "timestamp", "system_info"]:
                continue
            
            emoji = "🟢" if status["status"] == "healthy" else "🟡" if status["status"] == "warning" else "🔴"
            message += f"{emoji} **{component.title()}**: {status['status'].upper()}\n"
            
            # Add component-specific details
            if component == "database":
                message += f"   • Connection: {status['connection']}\n"
                message += f"   • Size: {status.get('database_size_mb', 'N/A')} MB\n"
            elif component == "memory":
                message += f"   • Used: {status['used_gb']:.1f} GB\n"
                message += f"   • Available: {status['available_gb']:.1f} GB\n"
            elif component == "cpu":
                message += f"   • Cores: {status['cpu_count']}\n"
                if status.get('load_average'):
                    message += f"   • Load: {status['load_average'][0]:.2f}\n"
            elif component == "disk":
                message += f"   • Used: {status['used_gb']:.1f} GB\n"
                message += f"   • Free: {status['free_gb']:.1f} GB\n"
            elif component == "plugins":
                message += f"   • Active: {status['enabled_plugins']}/{status['loaded_plugins']}\n"
            
            message += "\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error_message = f"❌ **Detailed Health Check Failed**\n\nError: {str(e)}"
        await update.message.reply_text(error_message, parse_mode='Markdown')


def register(event_bus: EventBus, command_registry: CommandRegistry) -> None:
    """Register health monitoring commands and event handlers."""
    # Register commands with the command registry
    command_registry.register("/health", health_check)
    command_registry.register("/health_quick", quick_health_check)
    command_registry.register("/health_detailed", detailed_health_check)
    
    # Event handlers can be added here if needed
    # Example: Subscribe to system events for health monitoring
    # event_bus.subscribe("system_startup", handle_system_startup)
    # event_bus.subscribe("system_shutdown", handle_system_shutdown)


# Plugin metadata
PLUGIN_METADATA = {
    "name": "health",
    "version": "1.0.0",
    "description": "System health monitoring and status reporting",
    "author": "LarryBot2 Team",
    "dependencies": ["health_service"],
    "enabled": True
} 