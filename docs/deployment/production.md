---
title: Production Deployment
description: Production deployment guide for LarryBot2
last_updated: 2025-06-28
---

# Production Deployment 🌐

> **Breadcrumbs:** [Home](../../README.md) > [Deployment](README.md) > Production

This guide covers deploying LarryBot2 in production environments with best practices for security, performance, and reliability.

## 🚀 Production Setup

### 1. Environment Configuration
```bash
# Production environment variables
ENVIRONMENT=production
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///larrybot.db
TELEGRAM_TOKEN=your_production_token
ALLOWED_TELEGRAM_USER_ID=your_user_id
```

### 2. Database Setup
```bash
# Run migrations
alembic upgrade head

# Backup existing data
cp larrybot.db larrybot.db.backup

# Verify database optimization settings
python -c "
from larrybot.storage.db import engine
with engine.connect() as conn:
    result = conn.execute('PRAGMA journal_mode')
    print(f'Journal mode: {result.fetchone()[0]}')
    result = conn.execute('PRAGMA cache_size')
    print(f'Cache size: {result.fetchone()[0]}')
"
```

### Database Performance Configuration
The bot automatically applies optimized SQLite settings:
- **WAL Mode**: Better concurrency for read/write operations
- **64MB Cache**: Improved query performance
- **30s Busy Timeout**: Reduced lock contention
- **Connection Pooling**: Efficient connection management

### 3. Process Management
Use a process manager to keep the bot running:

**Systemd (Linux):**
```ini
[Unit]
Description=LarryBot2
After=network.target

[Service]
Type=simple
User=larrybot
WorkingDirectory=/opt/larrybot2
Environment=PATH=/opt/larrybot2/venv/bin
ExecStart=/opt/larrybot2/venv/bin/python -m larrybot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Supervisord:**
```ini
[program:larrybot2]
command=/opt/larrybot2/venv/bin/python -m larrybot
directory=/opt/larrybot2
user=larrybot
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/larrybot2.log
```

## 🔒 Security Best Practices

### 1. File Permissions
```bash
# Secure file permissions
chmod 600 .env
chmod 600 larrybot.db
chmod 600 client_secret.json
```

### 2. Firewall Configuration
```bash
# Only allow necessary ports
ufw allow ssh
ufw allow 443
ufw enable
```

### 3. Regular Updates
- Keep dependencies updated
- Monitor for security patches
- Regular backups

## 📊 Monitoring & Logging

### 1. Health Checks
```bash
# Set up health check endpoint
curl http://localhost:8000/health

# Check scheduler performance
python -c "
import time
from larrybot.scheduler import check_due_reminders
start = time.time()
check_due_reminders()
print(f'Reminder check took: {time.time() - start:.3f}s')
"
```

### 2. Log Management
```bash
# Configure log rotation
logrotate /etc/logrotate.d/larrybot2

# Monitor for performance warnings
tail -f /var/log/larrybot2.log | grep "potential performance issue"
```

### 3. Performance Monitoring
- **Response Times**: Monitor command response times (<100ms target)
- **Scheduler Performance**: Watch for >1 second execution warnings
- **Database Queries**: Monitor query execution times
- **Memory Usage**: Track memory usage with caching optimizations
- **Connection Pool**: Monitor database connection efficiency

### 4. Performance Metrics to Watch
```bash
# Key performance indicators
echo "Performance Monitoring Checklist:"
echo "✓ Scheduler operations complete in <1 second"
echo "✓ Database queries complete in <100ms"
echo "✓ Command responses in <100ms"
echo "✓ No 'potential performance issue' warnings"
echo "✓ WAL mode enabled (journal_mode=WAL)"
echo "✓ Cache size properly configured (-64000)"
```

### 5. Performance Troubleshooting
```bash
# Check database performance
python -c "
from larrybot.storage.db import engine
import time
with engine.connect() as conn:
    start = time.time()
    conn.execute('SELECT COUNT(*) FROM tasks')
    print(f'Query time: {time.time() - start:.3f}s')
"

# Monitor scheduler timing
grep "potential performance issue" /var/log/larrybot2.log
```

## 🛠️ Best Practices
- Use environment-specific configurations
- Implement proper logging and monitoring
- Set up automated backups
- Use process managers for reliability
- Monitor system resources

## 🚨 Troubleshooting
- **Bot not starting**: Check logs and environment variables
- **Database errors**: Verify permissions and run migrations
- **Performance issues**: Monitor resources and optimize queries

---

**Related Guides:** [Docker Deployment](docker.md) | [Monitoring](monitoring.md) 