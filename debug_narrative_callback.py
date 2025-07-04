#!/usr/bin/env python3
"""
Debug script to test narrative callback handling.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, CallbackQuery, User, Message, Chat
from telegram.ext import ContextTypes

# Import the bot handler and narrative functions
from larrybot.handlers.bot import TelegramBotHandler
from larrybot.config.loader import Config
from larrybot.core.command_registry import CommandRegistry
from larrybot.nlp.enhanced_narrative_processor import TaskCreationState
from larrybot.plugins.tasks import narrative_add_task_handler, _handle_description_step

async def debug_narrative_flow():
    """Debug the complete narrative flow."""
    
    # Create mock config and command registry
    config = MagicMock(spec=Config)
    config.TELEGRAM_BOT_TOKEN = "test_token"
    config.ALLOWED_TELEGRAM_USER_ID = 12345
    
    command_registry = MagicMock(spec=CommandRegistry)
    command_registry._commands = {}
    
    # Create bot handler
    bot_handler = TelegramBotHandler(config, command_registry)
    
    # Create mock user
    user = MagicMock(spec=User)
    user.id = 12345
    
    # Create mock message
    message = MagicMock(spec=Message)
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 12345
    message.reply_text = AsyncMock()
    
    # Create mock update for /addtask
    update = MagicMock(spec=Update)
    update.effective_user = user
    update.message = message
    
    # Create mock context
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    
    print("=== Testing /addtask initialization ===")
    
    # Test /addtask initialization
    try:
        await narrative_add_task_handler(update, context)
        print(f"✅ /addtask initialized successfully")
        print(f"State after /addtask: {context.user_data.get('task_creation_state')}")
        print(f"Expected state: {TaskCreationState.AWAITING_DESCRIPTION.value}")
    except Exception as e:
        print(f"❌ Error in /addtask: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n=== Testing description step ===")
    
    # Test description step
    try:
        await _handle_description_step(update, context, "Test task description")
        print(f"✅ Description step completed successfully")
        print(f"State after description: {context.user_data.get('task_creation_state')}")
        print(f"Expected state: {TaskCreationState.AWAITING_DUE_DATE.value}")
    except Exception as e:
        print(f"❌ Error in description step: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n=== Testing due date callback ===")
    
    # Create mock callback query for due date
    query = MagicMock(spec=CallbackQuery)
    query.data = "addtask_step:due_date:today"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    
    # Create mock update for callback
    callback_update = MagicMock(spec=Update)
    callback_update.callback_query = query
    callback_update.effective_user = user
    
    print(f"Current state before callback: {context.user_data.get('task_creation_state')}")
    print(f"Expected state: {TaskCreationState.AWAITING_DUE_DATE.value}")
    print(f"States match: {context.user_data.get('task_creation_state') == TaskCreationState.AWAITING_DUE_DATE.value}")
    
    # Test the callback handling
    try:
        await bot_handler._handle_narrative_task_callback(query, context)
        print("✅ Due date callback handled successfully")
        print(f"State after callback: {context.user_data.get('task_creation_state')}")
    except Exception as e:
        print(f"❌ Error handling callback: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_narrative_flow()) 