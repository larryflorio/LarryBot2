---
title: Troubleshooting Guide
description: Common issues and solutions for LarryBot2
last_updated: 2025-06-28
---

# Troubleshooting Guide 🔧

> **Breadcrumbs:** [Home](../../README.md) > [Getting Started](../README.md) > Troubleshooting

This guide helps you resolve common issues with LarryBot2 installation, configuration, and usage.

## 🚨 Quick Diagnosis

### Check System Status
```bash
# Run health check
python -m larrybot --health

# Check configuration
python -c "from larrybot.config.loader import Config; Config().validate(); print('✅ Config OK')"

# Test command registration
python test_commands.py
```

### Common Error Patterns
- **"Configuration validation failed"** → Configuration issues
- **"Unauthorized access"** → User ID problems
- **"Task not found"** → Database issues
- **"Bot not found"** → Token problems

## 🔧 Installation Issues

### Python Version Problems

#### Problem: "Python 3.9+ required"
```bash
python --version
# Shows Python 3.8 or lower
```

**Solution:**
```bash
# Install Python 3.9+ (macOS)
brew install python@3.9

# Install Python 3.9+ (Ubuntu/Debian)
sudo apt update
sudo apt install python3.9 python3.9-venv

# Install Python 3.9+ (Windows)
# Download from python.org
```

#### Problem: "pip not found"
```bash
pip --version
# Command not found
```

**Solution:**
```bash
# Install pip
python -m ensurepip --upgrade

# Or use pip3
pip3 install -r requirements.txt
```

### Virtual Environment Issues

#### Problem: "Module not found"
```bash
python -m larrybot
# ModuleNotFoundError: No module named 'larrybot'
```

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### Problem: "Permission denied" creating venv
```bash
python -m venv venv
# Permission denied
```

**Solution:**
```bash
# Use sudo (not recommended)
sudo python -m venv venv

# Or change directory permissions
chmod 755 /path/to/project

# Or use user directory
python -m venv ~/larrybot-venv
```

### Dependency Installation Issues

#### Problem: "Failed to build wheel"
```bash
pip install -r requirements.txt
# Failed to build wheel for cryptography
```

**Solution:**
```bash
# Install build dependencies
# macOS
brew install openssl

# Ubuntu/Debian
sudo apt install build-essential libssl-dev libffi-dev

# Windows
# Install Visual Studio Build Tools

# Then retry
pip install -r requirements.txt
```

#### Problem: "SSL certificate verify failed"
```bash
pip install -r requirements.txt
# SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution:**
```bash
# Update pip and certificates
pip install --upgrade pip certifi

# Or use trusted host
pip install -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
```

## ⚙️ Configuration Issues

### Environment Variable Problems

#### Problem: "TELEGRAM_BOT_TOKEN is required"
```bash
python -m larrybot
# Configuration validation failed: TELEGRAM_BOT_TOKEN is required
```

**Solution:**
1. **Check .env file exists:**
   ```bash
   ls -la .env
   ```

2. **Create .env file:**
   ```bash
   cp .env.example .env
   nano .env
   ```

3. **Set token correctly:**
   ```bash
   # In .env file
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

4. **Verify token format:**
   - Should be like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
   - No extra spaces or quotes
   - Get from @BotFather

#### Problem: "ALLOWED_TELEGRAM_USER_ID is required"
```bash
python -m larrybot
# Configuration validation failed: ALLOWED_TELEGRAM_USER_ID is required
```

**Solution:**
1. **Get your user ID:**
   - Message @userinfobot on Telegram
   - Copy your user ID (number only)

2. **Set in .env file:**
   ```bash
   ALLOWED_TELEGRAM_USER_ID=987654321
   ```

3. **Verify format:**
   - Must be a positive integer
   - No quotes or spaces

#### Problem: "Invalid bot token"
```bash
python -m larrybot
# Error: Invalid bot token
```

**Solution:**
1. **Verify token format:**
   ```bash
   # Should be: NNNNNNNNNN:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   echo $TELEGRAM_BOT_TOKEN
   ```

2. **Get new token from BotFather:**
   - Message @BotFather on Telegram
   - Send `/newtoken`
   - Follow instructions

3. **Update .env file:**
   ```bash
   TELEGRAM_BOT_TOKEN=YOUR_NEW_TOKEN_HERE
   ```

## 🚀 Performance Issues

### Command Response Delays

#### Problem: "Telegram commands slow to respond"
```bash
# Commands take >5 seconds to respond
# Bot seems "laggy" or unresponsive
```

**Diagnosis:**
```bash
# Check for performance warnings
grep "potential performance issue" larrybot.log

# Test scheduler performance
python -c "
import time
from larrybot.scheduler import check_due_reminders
start = time.time()
check_due_reminders()
print(f'Scheduler time: {time.time() - start:.3f}s')
"

# Check database configuration
python -c "
from larrybot.storage.db import engine
with engine.connect() as conn:
    result = conn.execute('PRAGMA journal_mode')
    print(f'Journal mode: {result.fetchone()[0]}')
"
```

**Solutions:**
1. **Verify WAL mode enabled:**
   ```bash
   # Should show 'wal'
   python -c "
   from larrybot.storage.db import engine
   with engine.connect() as conn:
       result = conn.execute('PRAGMA journal_mode')
       print(result.fetchone()[0])
   "
   ```

2. **Check for database locks:**
   ```bash
   # Checkpoint WAL file
   python -c "
   from larrybot.storage.db import engine
   with engine.connect() as conn:
       conn.execute('PRAGMA wal_checkpoint(FULL)')
   "
   ```

3. **Monitor scheduler timing:**
   ```bash
   # Should complete in <1 second
   tail -f larrybot.log | grep "Reminder check took"
   ```

### Database Performance Issues

#### Problem: "Database queries slow"
```bash
# Database operations taking >1 second
# Lock timeout errors
```

**Diagnosis:**
```bash
# Check database settings
python -c "
from larrybot.storage.db import engine
with engine.connect() as conn:
    settings = ['journal_mode', 'cache_size', 'busy_timeout', 'synchronous']
    for setting in settings:
        result = conn.execute(f'PRAGMA {setting}')
        print(f'{setting}: {result.fetchone()[0]}')
"

# Test query performance
python -c "
from larrybot.storage.db import get_session
import time
with next(get_session()) as session:
    start = time.time()
    count = session.execute('SELECT COUNT(*) FROM tasks').scalar()
    print(f'Query time: {time.time() - start:.3f}s for {count} tasks')
"
```

**Solutions:**
1. **Verify optimized configuration:**
   - Journal mode should be 'wal'
   - Cache size should be '-64000' (64MB)
   - Busy timeout should be '30000' (30 seconds)

2. **Fix configuration if needed:**
   ```bash
   # Restart bot to apply settings
   pkill -f "python -m larrybot"
   python -m larrybot
   ```

3. **Monitor for lock contention:**
   ```bash
   # Check for lock errors
   grep -i "lock\|busy" larrybot.log
   ```

### Memory Usage Issues

#### Problem: "High memory usage"
```bash
# Bot consuming excessive memory
# System running out of RAM
```

**Diagnosis:**
```bash
# Check bot process memory
ps aux | grep "python -m larrybot"

# Monitor database cache
python -c "
from larrybot.storage.db import engine
with engine.connect() as conn:
    result = conn.execute('PRAGMA cache_size')
    cache_kb = abs(int(result.fetchone()[0])) * 1024 / 1024
    print(f'Database cache: {cache_kb:.1f}MB')
"
```

**Solutions:**
1. **Adjust cache size if needed:**
   ```python
   # In larrybot/storage/db.py
   # Reduce cache_size if memory constrained
   cursor.execute("PRAGMA cache_size=-32000")  # 32MB instead of 64MB
   ```

2. **Monitor connection pool:**
   ```bash
   # Check for connection leaks
   grep -i "connection" larrybot.log
   ```

## 📊 Performance Monitoring

### Regular Health Checks

```bash
# Performance health check script
echo "=== LarryBot2 Performance Check ==="

# 1. Scheduler performance
echo "1. Scheduler Performance:"
python -c "
import time
from larrybot.scheduler import check_due_reminders
start = time.time()
check_due_reminders()
exec_time = time.time() - start
print(f'   ✓ Execution time: {exec_time:.3f}s')
if exec_time > 1.0:
    print('   ⚠️  WARNING: Slow scheduler performance')
else:
    print('   ✓ Scheduler performance OK')
"

# 2. Database configuration
echo "2. Database Configuration:"
python -c "
from larrybot.storage.db import engine
with engine.connect() as conn:
    result = conn.execute('PRAGMA journal_mode')
    mode = result.fetchone()[0]
    print(f'   Journal mode: {mode}')
    if mode == 'wal':
        print('   ✓ WAL mode enabled')
    else:
        print('   ⚠️  WARNING: WAL mode not enabled')
"

# 3. Recent performance warnings
echo "3. Recent Performance Warnings:"
if [ -f larrybot.log ]; then
    warnings=$(grep "potential performance issue" larrybot.log | tail -5)
    if [ -z "$warnings" ]; then
        echo "   ✓ No recent performance warnings"
    else
        echo "   ⚠️  Recent warnings found:"
        echo "$warnings" | sed 's/^/   /'
    fi
else
    echo "     No log file found"
fi

echo "=== Performance Check Complete ==="
```

---

**Related Guides:** [Performance Guide](../../developer-guide/performance/README.md) | [Development Guide](../../developer-guide/development/deployment.md)

#### Problem: "Invalid bot token"
```bash
python -m larrybot
# Invalid bot token
```

**Solution:**
1. **Get new token from @BotFather:**
   - Message @BotFather
   - Use `/mybots` to see your bots
   - Select your bot
   - Use "API Token" to get new token

2. **Update .env file:**
   ```bash
   TELEGRAM_BOT_TOKEN=new_token_here
   ```

3. **Verify bot is active:**
   - Check with @BotFather that bot exists
   - Make sure bot hasn't been deleted

### File Permission Issues

#### Problem: "Permission denied" on database
```bash
python -m larrybot
# Permission denied: larrybot.db
```

**Solution:**
```bash
# Fix permissions
chmod 644 larrybot.db

# Or recreate database
rm larrybot.db
alembic upgrade head
```

#### Problem: "Permission denied" on .env
```bash
python -m larrybot
# Permission denied: .env
```

**Solution:**
```bash
# Fix permissions
chmod 600 .env

# Or recreate file
cp .env.example .env
chmod 600 .env
nano .env
```

## 🤖 Bot Issues

### Authorization Problems

#### Problem: "Unauthorized access"
```
🚫 Unauthorized Access

This is a single-user bot designed for personal use.
Only the configured user can access this bot.
```

**Solution:**
1. **Check user ID:**
   ```bash
   # Get your current user ID
   # Message @userinfobot on Telegram
   ```

2. **Update .env file:**
   ```bash
   ALLOWED_TELEGRAM_USER_ID=your_correct_user_id
   ```

3. **Restart bot:**
   ```bash
   python -m larrybot
   ```

4. **Verify Telegram account:**
   - Make sure you're using the same account
   - Check for typos in user ID

#### Problem: "Bot not responding"
- Bot doesn't respond to commands
- No error messages

**Solution:**
1. **Check bot is running:**
   ```bash
   ps aux | grep python
   # Should show larrybot process
   ```

2. **Check logs:**
   ```bash
   python -m larrybot
   # Look for error messages
   ```

3. **Test bot token:**
   ```bash
   curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
   # Should return bot info
   ```

4. **Restart bot:**
   ```bash
   # Stop current process
   pkill -f larrybot
   
   # Start again
   python -m larrybot
   ```

### Command Issues

#### Problem: "Command not found"
```
Command not found: /unknown_command
```

**Solution:**
1. **Check available commands:**
   ```
   /help
   ```

2. **Verify command spelling:**
   - Commands are case-sensitive
   - Use exact command names

3. **Check command registration:**
   ```bash
   python test_commands.py
   # Should show all 91 commands
   ```

#### Problem: "Task not found"
```
❌ Task not found
```

**Solution:**
1. **List tasks to see available IDs:**
   ```
   /list
   ```

2. **Check task ID format:**
   - Use numeric IDs only
   - No extra characters

3. **Verify task exists:**
   - Task might have been deleted
   - Check with `/list` command

## 🗄️ Database Issues

### Database Connection Problems

#### Problem: "Database locked"
```bash
python -m larrybot
# database is locked
```

**Solution:**
1. **Check for other processes:**
   ```bash
   ps aux | grep python
   # Kill other larrybot processes
   ```

2. **Recreate database:**
   ```bash
   rm larrybot.db
   alembic upgrade head
   ```

3. **Check file permissions:**
   ```bash
   chmod 644 larrybot.db
   ```

#### Problem: "Database schema error"
```bash
python -m larrybot
# no such table: tasks
```

**Solution:**
1. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

2. **Check migration status:**
   ```bash
   alembic current
   ```

3. **Recreate database:**
   ```bash
   rm larrybot.db
   alembic upgrade head
   ```

### Data Issues

#### Problem: "Data corruption"
- Strange behavior with tasks
- Missing data

**Solution:**
1. **Backup current data:**
   ```bash
   cp larrybot.db larrybot.db.backup
   ```

2. **Check database integrity:**
   ```bash
   sqlite3 larrybot.db "PRAGMA integrity_check;"
   ```

3. **Recreate if needed:**
   ```bash
   rm larrybot.db
   alembic upgrade head
   ```

## 📅 Calendar Integration Issues

### Google Calendar Problems

#### Problem: "Calendar not connected"
```
📅 Calendar Integration: Not Connected
```

**Solution:**
1. **Check client_secret.json:**
   ```bash
   ls -la client_secret.json
   # File should exist
   ```

2. **Connect calendar:**
   ```
   /connect_google
   ```

3. **Check Google Cloud Console:**
   - Enable Google Calendar API
   - Verify OAuth credentials
   - Check API quotas

#### Problem: "OAuth error"
```
❌ OAuth authentication failed
```

**Solution:**
1. **Check credentials file:**
   ```bash
   cat client_secret.json
   # Should be valid JSON
   ```

2. **Update credentials:**
   - Get new credentials from Google Cloud Console
   - Download and replace client_secret.json

3. **Check redirect URIs:**
   - Add localhost to authorized redirect URIs
   - Use correct OAuth 2.0 client type

## 🧪 Testing Issues

### Test Failures

#### Problem: "Tests failing"
```bash
python -m pytest
# Tests fail
```

**Solution:**
1. **Check test environment:**
   ```bash
   # Activate virtual environment
   source venv/bin/activate
   
   # Install test dependencies
   pip install -r requirements.txt
   ```

2. **Run specific test:**
   ```bash
   python -m pytest tests/test_handlers_bot.py -v
   ```

3. **Check test database:**
   ```bash
   # Tests use separate database
   # No need to worry about production data
   ```

#### Problem: "Coverage issues"
```bash
python -m pytest --cov=larrybot
# Coverage below 85%
```

**Solution:**
1. **This is normal for development:**
   - 85% coverage is excellent
   - Some code paths are hard to test
   - Focus on critical functionality

2. **Add missing tests:**
   - Look at coverage report
   - Add tests for uncovered lines

## 🔍 Debug Mode

### Enable Debug Logging

#### Set debug level:
```bash
# In .env file
LOG_LEVEL=DEBUG
```

#### Run with debug output:
```bash
python -m larrybot
# Will show detailed logs
```

### Common Debug Commands

#### Check system status:
```bash
# Health check
python -c "from larrybot.services.health_service import HealthService; h = HealthService(); print(h.get_health_status())"
```

#### Test configuration:
```bash
# Validate config
python -c "from larrybot.config.loader import Config; c = Config(); c.validate(); print('Config OK')"
```

#### Check database:
```bash
# Database info
sqlite3 larrybot.db ".tables"
sqlite3 larrybot.db "SELECT COUNT(*) FROM tasks;"
```

## 📞 Getting Help

### Before Asking for Help

1. **Check this troubleshooting guide**
2. **Enable debug logging** and check logs
3. **Try the solutions above**
4. **Gather error information**

### Information to Provide

When asking for help, include:

1. **Error message** (exact text)
2. **Your configuration** (without sensitive data)
3. **Steps to reproduce**
4. **System information** (OS, Python version)
5. **What you've already tried**

### Example Help Request

```
Error: Configuration validation failed: TELEGRAM_BOT_TOKEN is required

System: macOS 12.0, Python 3.9.6
Steps: 
1. Copied .env.example to .env
2. Set TELEGRAM_BOT_TOKEN=my_token
3. Run python -m larrybot

Tried:
- Checking file permissions
- Verifying token format
- Restarting terminal

Configuration (sanitized):
TELEGRAM_BOT_TOKEN=1234567890:ABC...
ALLOWED_TELEGRAM_USER_ID=987654321
```

## 🚀 Performance Issues

### Slow Response Times

#### Problem: Bot responds slowly
- Commands take >5 seconds
- Timeout errors

**Solution:**
1. **Check system resources:**
   ```bash
   top
   # Check CPU and memory usage
   ```

2. **Optimize database:**
   ```bash
   sqlite3 larrybot.db "VACUUM;"
   sqlite3 larrybot.db "ANALYZE;"
   ```

3. **Reduce log level:**
   ```bash
   # In .env file
   LOG_LEVEL=WARNING
   ```

### Memory Issues

#### Problem: High memory usage
- Bot uses >100MB RAM
- System becomes slow

**Solution:**
1. **Check memory usage:**
   ```bash
   ps aux | grep larrybot
   # Check memory column
   ```

2. **Restart bot periodically:**
   ```bash
   # Use process manager
   # Or cron job to restart
   ```

3. **Optimize queries:**
   - Use pagination for large lists
   - Limit search results

---

**Related Guides:** [Installation](installation.md) | [Configuration](configuration.md)

**Last Updated**: June 28, 2025 