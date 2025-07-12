"""
Set Telegram bot menu button and main commands for LarryBot2.
Run this script after deployment to ensure users always see the main menu and commands.
"""
import os
import asyncio
from telegram import Bot, BotCommand
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()

async def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        return
    bot = Bot(token=token)
    commands = [
        BotCommand("start", "Show main menu"),
        BotCommand("addtask", "Create a new task (narrative flow)"),
        BotCommand("list", "View your tasks"),
    ]
    try:
        await bot.set_my_commands(commands)
        # Set the menu button to show commands (explicit, best practice)
        await bot.set_chat_menu_button(menu_button={"type": "commands"})
        print("✅ Bot menu and commands set successfully.")
    except TelegramError as e:
        print(f"Telegram API error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 