---
title: System Commands
description: Health checks and system status commands for LarryBot2
last_updated: 2025-06-28
---

# System Commands 🏥

System commands provide health monitoring and status information for LarryBot2. These commands help you monitor the bot's performance and diagnose any issues.

## 📊 Available Commands

### `/health` - System Health Status
Provides a comprehensive overview of the system's health status.

**Usage**: `/health`

**Response**:
```
🏥 LarryBot2 Health Status

✅ Database: Connected
✅ Event Bus: Active
✅ Plugin Manager: Running
✅ Task Service: Operational
✅ Calendar Service: Connected

📊 Performance Metrics:
• Response Time: 45ms
• Memory Usage: 12.5MB
• Active Connections: 3
• Uptime: 2h 15m 30s

🎯 System Status: HEALTHY
```

### `/health_quick` - Quick Health Check
Performs a rapid health check for immediate status verification.

**Usage**: `/health_quick`

**Response**:
```
⚡ Quick Health Check

✅ Database: OK
✅ Services: OK
✅ Plugins: OK

Status: HEALTHY
```

### `/health_detailed` - Detailed System Information
Provides in-depth system information including performance metrics, configuration, and diagnostic data.

**Usage**: `/health_detailed`

**Response**:
```
🔍 Detailed System Information

📋 System Overview:
• Version: LarryBot2 v2.0.0
• Environment: production
• Python Version: 3.9.18
• Platform: macOS-14.5.0

🗄️ Database Information:
• Type: SQLite
• Path: /path/to/larrybot.db
• Size: 1.2MB
• Tables: 8
• Active Connections: 2

⚙️ Configuration:
• Log Level: INFO
• Timezone: UTC
• Max Concurrent Tasks: 10
• Cache Timeout: 300s

📊 Performance Metrics:
• Average Response Time: 45ms
• Peak Response Time: 120ms
• Memory Usage: 12.5MB
• CPU Usage: 2.3%
• Disk Usage: 15.2MB

🔌 Active Plugins:
• advanced_tasks (v1.0.0)
• calendar (v1.0.0)
• reminders (v1.0.0)
• habits (v1.0.0)
• analytics (v1.0.0)

📈 Recent Activity:
• Commands Processed: 1,247
• Tasks Created: 89
• Events Emitted: 2,156
• Errors: 0

🎯 System Status: HEALTHY
```

## 🔍 Health Check Components

### Database Health
- **Connection Status**: Verifies database connectivity
- **Query Performance**: Tests basic database operations
- **Table Integrity**: Checks for corrupted tables
- **Connection Pool**: Monitors active connections

### Service Health
- **Task Service**: Verifies task management functionality
- **Calendar Service**: Checks Google Calendar integration
- **Plugin Manager**: Ensures plugin system is operational
- **Event Bus**: Validates event-driven communication

### Performance Metrics
- **Response Time**: Average command processing time
- **Memory Usage**: Current memory consumption
- **CPU Usage**: System resource utilization
- **Disk Usage**: Storage space consumption

### Plugin Status
- **Active Plugins**: List of loaded and running plugins
- **Plugin Versions**: Version information for each plugin
- **Plugin Health**: Individual plugin status checks

## 🚨 Troubleshooting

### Common Health Issues

#### Database Connection Failed
```
❌ Database: Connection Failed
Error: Unable to connect to database
```

**Solutions**:
1. Check database file permissions
2. Verify database path in configuration
3. Ensure sufficient disk space
4. Restart the application

#### Plugin Loading Error
```
❌ Plugin Manager: Error
Error: Failed to load plugin 'calendar'
```

**Solutions**:
1. Check plugin file permissions
2. Verify plugin dependencies
3. Review plugin configuration
4. Check application logs

#### High Response Time
```
⚠️ Performance: Slow Response
Average Response Time: 500ms (High)
```

**Solutions**:
1. Check system resources
2. Optimize database queries
3. Review plugin performance
4. Consider scaling resources

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Set log level to DEBUG
LOG_LEVEL=DEBUG

# Restart the application
python -m larrybot
```

### Health Check Automation

You can automate health checks using external monitoring tools:

```bash
# Example: Cron job for health monitoring
*/5 * * * * curl -X POST "https://your-bot-url/health" > /dev/null 2>&1
```

## 📊 Health Metrics Dashboard

For production deployments, consider implementing a metrics dashboard:

- **Prometheus**: Collect and store metrics
- **Grafana**: Visualize health data
- **Alerting**: Set up notifications for health issues

## 🔧 Configuration

### Health Check Settings

Configure health check behavior in your environment:

```bash
# Enable/disable health checks
ENABLE_HEALTH_CHECKS=true

# Health check interval (seconds)
HEALTH_CHECK_INTERVAL=60

# Performance thresholds
MAX_RESPONSE_TIME=200
MAX_MEMORY_USAGE=100
```

### Custom Health Checks

Add custom health checks for your specific needs:

```python
@health_check("custom_service")
def check_custom_service():
    # Your custom health check logic
    return HealthStatus.HEALTHY
```

## 📞 Support

If you encounter persistent health issues:

1. Check the [Troubleshooting Guide](../troubleshooting.md)
2. Review the [Architecture Documentation](../../developer-guide/architecture/overview.md)
3. Report issues on GitHub with health check output

---

**Related Commands**: [Task Management](task-management.md) → [Analytics](../features/analytics.md) 