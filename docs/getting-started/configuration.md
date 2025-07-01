---
title: Configuration Guide
description: Complete configuration guide for LarryBot2
last_updated: 2025-06-28
---

# Configuration Guide ⚙️

> **Breadcrumbs:** [Home](../../README.md) > [Getting Started](../README.md) > Configuration

This guide covers all configuration options for LarryBot2, including environment variables, security settings, and troubleshooting.

## 🚀 Quick Setup

### 1. Create Environment File
```bash
# Copy the example configuration
cp .env.example .env

# Edit with your settings
nano .env  # or use your preferred editor
```

### 2. Required Configuration
You must set these values for LarryBot2 to work:

```bash
# Your Telegram bot token from @BotFather
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Your Telegram user ID (get from @userinfobot)
ALLOWED_TELEGRAM_USER_ID=123456789
```

## 📋 Configuration Options

### Required Environment Variables

#### `TELEGRAM_BOT_TOKEN`
Your Telegram bot token from @BotFather.

**How to get it:**
1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the token provided

**Example:**
```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

#### `ALLOWED_TELEGRAM_USER_ID`
Your Telegram user ID (the only user who can access this bot).

**How to get it:**
1. Open Telegram and search for [@userinfobot](https://t.me/userinfobot)
2. Send any message to the bot
3. Copy your user ID from the response

**Example:**
```bash
ALLOWED_TELEGRAM_USER_ID=987654321
```

### Optional Environment Variables

#### `DATABASE_PATH`
Path to the SQLite database file (default: `larrybot.db`).

```bash
DATABASE_PATH=larrybot.db
```

#### `GOOGLE_CLIENT_SECRET_PATH`
Path to Google Calendar client secret file (default: `client_secret.json`).

```bash
GOOGLE_CLIENT_SECRET_PATH=client_secret.json
```

#### `LOG_LEVEL`
Logging level for the application (default: `INFO`).

**Options:**
- `DEBUG` - Detailed debug information
- `INFO` - General information (recommended)
- `WARNING` - Warning messages only
- `ERROR` - Error messages only
- `CRITICAL` - Critical errors only

```bash
LOG_LEVEL=INFO
```

#### `MAX_REQUESTS_PER_MINUTE`
Rate limiting for bot commands (default: `60`).

```bash
MAX_REQUESTS_PER_MINUTE=60
```

#### `HEALTH_CHECK_INTERVAL`
Health check interval in seconds (default: `60`).

```bash
HEALTH_CHECK_INTERVAL=60
```

#### `ENABLE_METRICS`
Enable metrics collection (default: `true`).

```bash
ENABLE_METRICS=true
```

### Google Calendar Integration (Optional)

#### `GOOGLE_CLIENT_ID`
Google OAuth client ID for calendar integration.

#### `GOOGLE_CLIENT_SECRET`
Google OAuth client secret for calendar integration.

**How to get these:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials
5. Download the client secret file

## 🔒 Security Configuration

### File Permissions
Set secure permissions for your configuration files:

```bash
# Secure environment file
chmod 600 .env

# Secure database file
chmod 600 larrybot.db

# Secure Google client secret
chmod 600 client_secret.json
```

### Environment File Security
- **Never commit `.env` to version control**
- Keep your bot token and user ID secure
- Use strong, unique values for all secrets
- Regularly rotate your tokens and secrets

### Single-User Security Model
LarryBot2 is designed for single-user use:
- Only the configured user can access the bot
- All data is stored locally
- No shared user accounts or permissions

## 🛠️ Configuration Validation

### Automatic Validation
LarryBot2 automatically validates configuration on startup:

```bash
python -m larrybot
```

### Manual Validation
You can validate configuration manually:

```python
from larrybot.config.loader import Config

try:
    config = Config()
    config.validate()
    print("✅ Configuration is valid")
except ValueError as e:
    print(f"❌ Configuration error: {e}")
```

### Common Validation Errors

#### "TELEGRAM_BOT_TOKEN is required"
- Make sure you've set the `TELEGRAM_BOT_TOKEN` environment variable
- Verify the token is correct and not empty

#### "ALLOWED_TELEGRAM_USER_ID is required"
- Make sure you've set the `ALLOWED_TELEGRAM_USER_ID` environment variable
- Verify it's a positive integer

#### "ALLOWED_TELEGRAM_USER_ID must be a positive integer"
- Make sure the user ID is a valid positive number
- Get your correct user ID from @userinfobot

#### "MAX_REQUESTS_PER_MINUTE must be a positive integer"
- Make sure the rate limit is a positive number
- Default is 60 commands per minute

## 🔧 Platform-Specific Configuration

### Windows
```cmd
# Set environment variables
set TELEGRAM_BOT_TOKEN=your_token_here
set ALLOWED_TELEGRAM_USER_ID=123456789

# Or use .env file (recommended)
copy .env.example .env
notepad .env
```

### macOS/Linux
```bash
# Set environment variables
export TELEGRAM_BOT_TOKEN=your_token_here
export ALLOWED_TELEGRAM_USER_ID=123456789

# Or use .env file (recommended)
cp .env.example .env
nano .env
```

### Docker
```bash
# Use environment variables
docker run -e TELEGRAM_BOT_TOKEN=your_token_here \
           -e ALLOWED_TELEGRAM_USER_ID=123456789 \
           larrybot2

# Or use .env file
docker run --env-file .env larrybot2
```

## 🚨 Troubleshooting

### Configuration Issues

#### Bot Token Issues
**Problem:** "Invalid bot token" or "Bot not found"
**Solution:**
1. Verify your bot token is correct
2. Make sure the bot is still active
3. Check with @BotFather that the bot exists

#### User ID Issues
**Problem:** "Unauthorized access"
**Solution:**
1. Get your correct user ID from @userinfobot
2. Make sure `ALLOWED_TELEGRAM_USER_ID` is set correctly
3. Verify you're using the same Telegram account

#### Database Issues
**Problem:** "Database error" or "Permission denied"
**Solution:**
1. Check file permissions on `larrybot.db`
2. Make sure the directory is writable
3. Try deleting the database file to recreate it

#### Calendar Integration Issues
**Problem:** "Calendar not connected" or "OAuth error"
**Solution:**
1. Verify `client_secret.json` exists and is valid
2. Check that Google Calendar API is enabled
3. Make sure OAuth credentials are correct

### Environment Variable Issues

#### Variables Not Loading
**Problem:** Environment variables not being read
**Solution:**
1. Make sure `.env` file is in the project root
2. Verify the file format is correct (no spaces around `=`)
3. Restart the application after changes

#### Wrong Values
**Problem:** Configuration has wrong values
**Solution:**
1. Check the `.env` file format
2. Verify no extra spaces or quotes
3. Use the validation script to check

## 📊 Configuration Examples

### Minimal Configuration
```bash
# .env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ALLOWED_TELEGRAM_USER_ID=987654321
```

### Full Configuration
```bash
# .env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ALLOWED_TELEGRAM_USER_ID=987654321
DATABASE_PATH=larrybot.db
GOOGLE_CLIENT_SECRET_PATH=client_secret.json
LOG_LEVEL=INFO
MAX_REQUESTS_PER_MINUTE=60
HEALTH_CHECK_INTERVAL=60
ENABLE_METRICS=true
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
```

### Development Configuration
```bash
# .env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ALLOWED_TELEGRAM_USER_ID=987654321
LOG_LEVEL=DEBUG
MAX_REQUESTS_PER_MINUTE=1000
ENABLE_METRICS=false
```

### Production Configuration
```bash
# .env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ALLOWED_TELEGRAM_USER_ID=987654321
DATABASE_PATH=/var/lib/larrybot/larrybot.db
LOG_LEVEL=WARNING
MAX_REQUESTS_PER_MINUTE=30
HEALTH_CHECK_INTERVAL=30
ENABLE_METRICS=true
```

## 🔄 Configuration Updates

### Adding New Configuration
When adding new configuration options:

1. **Update the Config class** in `larrybot/config/loader.py`
2. **Add validation** in the `validate()` method
3. **Update this documentation**
4. **Add to `.env.example`**
5. **Test the configuration**

### Migration Guide
When configuration changes between versions:

1. **Check the changelog** for breaking changes
2. **Update your `.env` file** with new variables
3. **Test the configuration** before deploying
4. **Backup your data** before major changes

---

**Related Guides:** [Installation](installation.md) | [Troubleshooting](troubleshooting.md)

**Last Updated**: June 28, 2025 