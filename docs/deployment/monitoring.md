---
title: Monitoring Guide
description: Monitoring and alerting for LarryBot2 in production
last_updated: 2025-06-28
---

# Monitoring Guide 📈

This guide explains how to monitor LarryBot2 in production for reliability and performance.

## 📊 Metrics Collection
- Expose health and metrics endpoints in the bot
- Use Prometheus to scrape metrics
- Example Prometheus config:

```yaml
scrape_configs:
  - job_name: 'larrybot2'
    static_configs:
      - targets: ['localhost:8000']
```

## 📉 Visualization with Grafana
- Connect Grafana to Prometheus
- Create dashboards for:
  - Command response times
  - Error rates
  - Database performance
  - Uptime and health checks

## 🚨 Alerting
- Set up alert rules in Prometheus or Grafana
- Example: Alert if health check fails or response time > 200ms
- Integrate with Slack, email, or PagerDuty for notifications

## 🛠️ Best Practices
- Monitor logs and metrics continuously
- Set up automated alerts for critical issues
- Regularly review dashboards and update alert rules

## 🚨 Troubleshooting
- **No metrics**: Check endpoint exposure and Prometheus config
- **No alerts**: Verify alert rules and notification channels
- **Performance issues**: Review logs and resource usage

---

**Related Guides**: [Health Monitoring](../user-guide/features/health-monitoring.md) | [Deployment Guide](deployment.md) 