# Quick Start Guide

Get LarryBot2 up and running in minutes with this quick start guide.

## 🚀 Prerequisites

- **Python 3.9+** - Download from [python.org](https://python.org)
- **Telegram Bot Token** - Get from [@BotFather](https://t.me/BotFather)
- **Git** - For cloning the repository

## ⚡ 5-Minute Setup

### 1. Clone and Setup
```bash
git clone <repository-url>
cd LarryBot2
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Create environment file
cp .env.example .env

# Edit .env with your bot token
echo "TELEGRAM_TOKEN=your_bot_token_here" > .env
```

### 3. Initialize Database
```bash
# Run database migrations
alembic upgrade head
```

### 4. Start the Bot
```bash
python -m larrybot
```

### 5. Test Basic Commands
In Telegram, send these commands to your bot:
- `/health` - Check if bot is running
- `/add "Buy groceries"` - Create your first task
- `/list` - See your tasks

## 🎯 First Tasks

Try these commands to get familiar with LarryBot2:

```bash
# Create tasks
/add "Complete project proposal"
/addtask "Review code" High 2025-07-01 "Work"

# List and manage
/list
/done 1

# Check system
/health
```

## 🔧 Next Steps

- **Calendar Integration**: See [Calendar Integration Guide](../user-guide/calendar-integration.md)
- **Advanced Features**: Explore [Advanced Features](../user-guide/advanced-features.md)
- **Plugin Development**: Learn [Plugin Development](../developer-guide/plugin-development.md)

## 🆘 Troubleshooting

### Common Issues

**Bot not responding?**
- Check your `TELEGRAM_TOKEN` in `.env`
- Ensure the bot is running: `python -m larrybot`
- Verify bot permissions with @BotFather

**Database errors?**
- Run migrations: `alembic upgrade head`
- Check database file permissions

**Import errors?**
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

### Getting Help

- Check the [Health Command](../user-guide/basic-commands.md#health-commands) for system status
- Review [Basic Commands](../user-guide/basic-commands.md) for usage
- See [Architecture Guide](../developer-guide/architecture.md) for technical details

---

*Ready to get started? Jump to [Basic Commands](../user-guide/basic-commands.md) to learn more!* 