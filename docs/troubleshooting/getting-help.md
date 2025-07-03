---
title: Getting Help
description: How to get help when you need it
last_updated: 2025-07-02
---

# Getting Help 🆘

> **Breadcrumbs:** [Home](../../README.md) > [Troubleshooting](README.md) > Getting Help

Need help with LarryBot2? We're here to help you get back to being productive quickly.

## 🚨 Quick Fixes

### Bot Not Responding?

**Try these steps in order:**

1. **Check if the bot is running**
   - Look at your terminal/command prompt
   - You should see "Bot started" or similar message
   - If not, restart the bot: `python -m larrybot`

2. **Check your connection**
   - Make sure you have internet access
   - Try sending a simple message to your bot

3. **Verify your setup**
   - Check your `.env` file has the correct token and user ID
   - Make sure you're using the right bot (check the username)

### Commands Not Working?

**Common issues and solutions:**

1. **"Command not found"**
   - Make sure you're typing the command correctly
   - Try `/help` to see all available commands
   - Check that you're sending the message to your bot, not a chat

2. **"Permission denied"**
   - Verify your user ID is correct in the `.env` file
   - Make sure you're the only user configured to use the bot

3. **"Database error"**
   - Try restarting the bot
   - Check that the database file exists and is readable

## 🔍 Self-Help Resources

### Check System Status

```
/health
```

This tells you if everything is working properly.

### Get Command Help

```
/help
```

See all available commands and their descriptions.

### Quick Health Check

```
/health_quick
```

Get a fast system status report.

## 📚 Documentation

### Setup and Installation
- **[Quick Start Guide](../getting-started/quick-start.md)** - Get up and running in 5 minutes
- **[Installation Guide](../getting-started/installation.md)** - Detailed setup instructions
- **[First Steps](../getting-started/first-steps.md)** - Learn your first commands

### Using LarryBot2
- **[Task Management](../user-guide/commands/task-management.md)** - Create and manage tasks
- **[Reminders](../user-guide/commands/reminders.md)** - Set up smart reminders
- **[Habits](../user-guide/commands/habits.md)** - Build productive habits
- **[Examples](../user-guide/examples.md)** - Real-world use cases

### Common Issues
- **[Troubleshooting Guide](../getting-started/troubleshooting.md)** - Common problems and solutions

## 🐛 Reporting Bugs

### Before You Report

1. **Check if it's already known**
   - Look through existing GitHub issues
   - Search for similar problems

2. **Gather information**
   - What command were you trying to use?
   - What error message did you see?
   - What were you expecting to happen?
   - What operating system are you using?

3. **Try to reproduce**
   - Can you make the problem happen again?
   - What steps lead to the issue?

### How to Report

**Option 1: GitHub Issues (Recommended)**
1. Go to the [GitHub repository](https://github.com/your-repo/issues)
2. Click "New Issue"
3. Choose "Bug Report"
4. Fill out the template with your information

**Option 2: Simple Report**
Send a message with:
- What you were trying to do
- What went wrong
- Any error messages you saw

## 💡 Feature Requests

Have an idea for improving LarryBot2? We'd love to hear it!

### Before Suggesting

1. **Check existing features**
   - Look through the documentation
   - Try different commands
   - See if there's already a way to do what you want

2. **Think about the use case**
   - How would this help you be more productive?
   - Would other users benefit from this?
   - Is it something you'd use regularly?

### How to Suggest

**Option 1: GitHub Issues**
1. Go to the [GitHub repository](https://github.com/your-repo/issues)
2. Click "New Issue"
3. Choose "Feature Request"
4. Describe your idea and why it would be helpful

**Option 2: Simple Suggestion**
Send a message with:
- What feature you'd like to see
- How it would help you
- Any ideas for how it might work

## 🤝 Community Support

### Ask Other Users

- **GitHub Discussions** - Ask questions and share tips
- **Community Chat** - Get help from other users
- **Documentation Comments** - Suggest improvements to guides

### Share Your Experience

- **Success Stories** - Tell us how LarryBot2 helps you
- **Tips and Tricks** - Share your productivity hacks
- **Use Cases** - Show how you use LarryBot2

## 📞 Direct Support

### When to Contact Directly

- **Critical bugs** that prevent you from using LarryBot2
- **Setup issues** that aren't covered in the documentation
- **Security concerns** that need immediate attention

### How to Contact

**For urgent issues:**
- Create a GitHub issue with "URGENT" in the title
- Include all relevant information
- Be patient - we'll respond as quickly as possible

**For general questions:**
- Use GitHub Discussions
- Check the documentation first
- Try the self-help resources above

## 🎯 Getting Back to Productivity

### Quick Recovery Steps

1. **Restart the bot** - Often fixes temporary issues
2. **Check your setup** - Verify configuration is correct
3. **Try a simple command** - `/health` or `/help`
4. **Check the logs** - Look for error messages in the terminal

### Prevention Tips

1. **Keep backups** - Regularly backup your task data
2. **Update regularly** - Get the latest features and fixes
3. **Test new features** - Try them in a safe environment first
4. **Document your workflow** - Write down how you use LarryBot2

---

**Remember:** Most issues can be solved quickly with the right information. Start with the self-help resources, and don't hesitate to ask for help when you need it!

---

**Related Guides:**
- [Troubleshooting Guide](../getting-started/troubleshooting.md)
- [Quick Start Guide](../getting-started/quick-start.md)
- [First Steps](../getting-started/first-steps.md) 