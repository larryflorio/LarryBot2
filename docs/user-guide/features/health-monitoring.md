---
title: Health Monitoring Feature Guide
description: System health checks and monitoring in LarryBot2
last_updated: 2025-06-28
---

# Health Monitoring Feature Guide 🏥

LarryBot2 includes robust health monitoring features to ensure reliability and performance.

## 🩺 Health Monitoring Commands

### `/health` - System Health Status
Provides a comprehensive overview of the system's health status.

**Usage**: `/health`

### `/health_quick` - Quick Health Check
Performs a rapid health check for immediate status verification.

**Usage**: `/health_quick`

### `/health_detailed` - Detailed System Information
Provides in-depth system information including performance metrics, configuration, and diagnostic data.

**Usage**: `/health_detailed`

## 🔍 Health Check Components
- **Database Health**: Connection, query performance, table integrity
- **Service Health**: Task, calendar, plugin, and event bus status
- **Performance Metrics**: Response time, memory, CPU, disk usage
- **Plugin Status**: Loaded plugins and their health

## 🛠️ Best Practices
- Schedule regular health checks (manual or automated)
- Monitor performance metrics for bottlenecks
- Use `/health_detailed` for diagnostics
- Enable debug logging for troubleshooting

## 🚨 Troubleshooting
- **Database connection failed**: Check file permissions and path
- **Plugin loading error**: Verify plugin files and dependencies
- **High response time**: Optimize queries and review plugin performance

## 📊 Health Metrics Dashboard
- Integrate with Prometheus and Grafana for advanced monitoring
- Set up alerting for health issues

---

**Related Guides**: [System Commands](../commands/system-commands.md) → [Deployment Monitoring](../../deployment/monitoring.md) 