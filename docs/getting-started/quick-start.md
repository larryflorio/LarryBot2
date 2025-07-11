# Quick Start Guide 🚀

Get LarryBot2 up and running in minutes with this simple guide.

## 🎯 What You Need

- **A Telegram account** - Download from [telegram.org](https://telegram.org)
- **Basic computer skills** - Ability to follow simple instructions
- **5 minutes of time** - That's it!

## ⚡ 5-Minute Setup

### Step 1: Get Your Bot Token

1. **Open Telegram** and search for [@BotFather](https://t.me/BotFather)
2. **Send `/newbot`** to create a new bot
3. **Choose a name** for your bot (e.g., "My Productivity Bot")
4. **Choose a username** (must end in 'bot', e.g., "myproductivitybot")
5. **Copy the token** - it looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### Step 2: Get Your User ID

1. **Search for [@userinfobot](https://t.me/userinfobot)** in Telegram
2. **Send any message** to the bot
3. **Copy your user ID** - it's just a number like `123456789`

### Step 3: Set Up LarryBot2

1. **Download LarryBot2** from the repository
2. **Open the folder** in your computer
3. **Create a file** called `.env` with this content:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ALLOWED_TELEGRAM_USER_ID=your_user_id_here
   ```
4. **Replace the values** with your actual token and user ID

### Step 4: Start Your Bot

1. **Open a terminal/command prompt** in the LarryBot2 folder
2. **Run these commands**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   alembic upgrade head
   python -m larrybot
   ```

### Step 5: Test Your Bot

1. **Open Telegram** and find your bot
2. **Send `/start`** to see the streamlined welcome
3. **Try creating a task**: `/add "Buy groceries"`
4. **You're ready!** 🎉

## 🎯 Your First Tasks

Try these commands to get familiar with LarryBot2:

### Create Tasks
```
/add "Complete project proposal"
/add "Call client about project" high 2025-07-01
```

### View Your Tasks
```
/list
```

### Mark Tasks Complete
```
/done 1
```

### Check System Status
```
/health
```

## 🔧 If Something Goes Wrong

### Bot Not Responding?
- Check your bot token in the `.env` file
- Make sure the bot is running (you should see "Bot started" in the terminal)
- Verify your user ID is correct

### Can't Find Your Bot?
- Search for your bot's username in Telegram
- Make sure you created the bot with @BotFather
- Check that the username ends in 'bot'

### Installation Errors?
- Make sure you have Python 3.9 or higher installed
- Try running the commands one by one
- Check that you're in the correct folder

## 🎉 What's Next?

Now that you're set up, learn how to use LarryBot2 effectively:

- **[First Steps](first-steps.md)** - Learn your first commands
- **[Task Management](../user-guide/commands/task-management.md)** - Master task creation and management
- **[Reminders](../user-guide/commands/reminders.md)** - Set up smart reminders
- **[Habits](../user-guide/commands/habits.md)** - Build productive habits

## 🆘 Need Help?

- **Check the [Troubleshooting Guide](troubleshooting.md)** for common issues
- **Review the [Installation Guide](installation.md)** for detailed setup instructions
- **Ask for help** on GitHub if you're still stuck

---

**Ready to boost your productivity?** Start with [First Steps](first-steps.md) to learn your first commands! 