from telegram import Update
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus

async def hello_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responds with a greeting message."""
    await update.message.reply_text("Hello from LarryBot plugin!")

def register(event_bus: EventBus, command_registry: CommandRegistry) -> None:
    """
    Register the /hello command with the command registry.
    """
    command_registry.register("/hello", hello_handler) 