# LarryBot2 🤖

> **Your Personal Productivity Powerhouse**  
> *Advanced task management, reminders, habits, and calendar integration—simple, fast, and private.*

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/Docs-Complete-blue.svg)](docs/)

## 🎯 What is LarryBot2?

LarryBot2 is a Telegram bot designed to help you organize your life, boost your productivity, and never miss a task or reminder. It's built for individuals who want powerful features without complexity or privacy worries. Everything runs locally—your data stays yours.

## ✨ Key Features

- **Natural Language Input** – Add tasks, reminders, and habits just by typing what you want to do
- **Advanced Task Management** – Organize, prioritize, and track tasks with ease
- **Interactive Action Buttons** – Instantly complete, edit, or delete items with a tap
- **Reminders & Habits** – Build routines and get notified so nothing slips through the cracks
- **Calendar Integration** – See your schedule and sync with Google Calendar
- **Analytics & Insights** – Visualize your productivity and spot trends
- **Bulk Operations** – Manage multiple tasks at once
- **Fast & Private** – Blazing-fast responses, no cloud required

## 🚀 Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/LarryBot2.git
   cd LarryBot2
   ```
2. **Set up your environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   alembic upgrade head
   cp .env.example .env
   # Edit .env with your Telegram bot token and user ID
   ```
3. **Start the bot:**
   ```bash
   python -m larrybot
   ```

## 📋 Most Useful Commands

- `/add` – Add a new task (e.g., `/add Buy groceries tomorrow`)
- `/list` – Show your current tasks
- `/done` – Mark a task as complete
- `/reminders` – List your reminders
- `/habit_add` – Add a new habit
- `/calendar` – View your calendar
- `/analytics` – See your productivity stats
- `/help` – Show all available commands

👉 **See the [User Guide](docs/user-guide/README.md) for the full list of commands and examples.**

## 🖱️ Action Button Examples

**Task List:**
```
1. 🟡 Buy groceries
   [👁️ View] [✅ Done] [✏️ Edit] [🗑️ Delete]
```
**Habit Progress:**
```
🏃‍♂️ Drink Water
   [✅ Complete] [📊 Progress] [🗑️ Delete]
```
**Analytics:**
```
📊 Productivity Report
   Tasks completed: 12
   Habits streak: 7 days
```

## 💡 Why LarryBot2?

- **Simple:** No complicated setup or learning curve
- **Fast:** Instant responses, even with lots of data
- **Private:** Runs locally—your data stays with you
- **Flexible:** Use natural language or classic commands
- **Visual:** Action buttons and analytics make productivity fun

## 🤝 For Developers

Want to contribute, customize, or self-host? See the [Developer Guide](docs/developer-guide/README.md) for architecture, testing, and advanced setup.

## 📚 More Help

- **[Installation Guide](docs/getting-started/installation.md)**
- **[User Guide](docs/user-guide/README.md)**
- **[Troubleshooting](docs/troubleshooting/README.md)**
- **[Changelog](CHANGELOG.md)** - Recent changes and improvements

---

**LarryBot2: Your productivity, your way.** 