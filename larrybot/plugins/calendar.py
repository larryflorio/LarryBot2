from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.storage.db import get_session
from larrybot.storage.calendar_token_repository import CalendarTokenRepository
from larrybot.utils.decorators import command_handler
from larrybot.utils.ux_helpers import MessageFormatter, KeyboardBuilder
from datetime import datetime, timezone, timedelta
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import asyncio
from functools import partial

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CLIENT_SECRET_FILE = "client_secret.json"


def register(event_bus: EventBus, command_registry: CommandRegistry) -> None:
    """Register calendar integration commands."""
    command_registry.register("/agenda", agenda_handler)
    command_registry.register("/calendar", calendar_handler)
    command_registry.register("/connect_google", connect_google_handler)
    command_registry.register("/disconnect", disconnect_handler)
    command_registry.register("/calendar_sync", calendar_sync_handler)
    command_registry.register("/calendar_events", calendar_events_handler)

@command_handler("/agenda", "Show today's agenda", "Usage: /agenda", "calendar")
async def agenda_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show today's calendar agenda with rich formatting."""
    try:
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            token = repo.get_token_by_provider("google")
            if not token:
                await update.message.reply_text(
                    MessageFormatter.format_info_message(
                        "📅 Calendar Not Connected",
                        {
                            "Status": "Google Calendar is not connected",
                            "Action": "Use /connect_google to connect your calendar",
                            "Features": "View agenda, sync events, and manage schedule"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
                return
            
            # Load client credentials
            try:
                with open(CLIENT_SECRET_FILE, "r") as f:
                    secrets = json.load(f)["installed"]
            except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        "Configuration Error",
                        f"Failed to load client configuration: {e}"
                    ),
                    parse_mode='MarkdownV2'
                )
                return
            
            creds = Credentials(
                token=token.access_token,
                refresh_token=token.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=secrets["client_id"],
                client_secret=secrets["client_secret"],
                expiry=token.expiry,
                scopes=SCOPES
            )
            
            # Refresh token if needed
            if creds.expired and creds.refresh_token:
                try:
                    await run_in_thread(creds.refresh, Request())
                    # Save updated token
                    repo.remove_token_by_provider("google")
                    repo.add_token(
                        provider="google",
                        access_token=creds.token,
                        refresh_token=creds.refresh_token,
                        expiry=creds.expiry
                    )
                except Exception as e:
                    await update.message.reply_text(
                        MessageFormatter.format_error_message(
                            "Token Refresh Failed",
                            f"Failed to refresh token: {e}"
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
            
            # Fetch events
            try:
                service = await run_in_thread(build, "calendar", "v3", credentials=creds)
                
                # Get today's events
                today = datetime.now(timezone.utc).date()
                start_of_day = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
                end_of_day = datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)
                
                events_result = await run_in_thread(
                    service.events().list,
                    calendarId="primary",
                    timeMin=start_of_day.isoformat(),
                    timeMax=end_of_day.isoformat(),
                    maxResults=10,
                    singleEvents=True,
                    orderBy="startTime"
                )
                events = await run_in_thread(events_result.execute)
                items = events.get("items", [])
                
                if not items:
                    await update.message.reply_text(
                        MessageFormatter.format_info_message(
                            "📅 Today's Agenda",
                            {
                                "Status": "No events scheduled for today",
                                "Date": today.strftime('%Y-%m-%d'),
                                "Suggestion": "Enjoy your free time or add some tasks!"
                            }
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                
                # Build rich agenda message
                message = f"📅 **Today's Agenda** \\({today.strftime('%B %d, %Y')}\\)\n\n"
                message += f"📋 **{len(items)} Events Scheduled**\n\n"
                
                for i, event in enumerate(items, 1):
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    summary = event.get("summary") or "(No title)"
                    location = event.get("location", "")
                    description = event.get("description", "")
                    
                    # Format time
                    if "T" in start:  # Has time
                        try:
                            event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                            time_str = event_time.strftime('%H:%M')
                        except:
                            time_str = start
                    else:  # All-day event
                        time_str = "All day"
                    
                    message += f"{i}\\. **{MessageFormatter.escape_markdown(summary)}**\n"
                    message += f"   🕐 {time_str}\n"
                    
                    if location:
                        message += f"   📍 {MessageFormatter.escape_markdown(location)}\n"
                    
                    if description:
                        # Truncate long descriptions
                        desc_preview = description[:100] + "..." if len(description) > 100 else description
                        message += f"   📝 {MessageFormatter.escape_markdown(desc_preview)}\n"
                    
                    message += "\n"
                
                # Create navigation keyboard
                keyboard = KeyboardBuilder.build_calendar_keyboard()
                
                await update.message.reply_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
                
            except Exception as e:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        "Failed to fetch events",
                        f"Error: {e}"
                    ),
                    parse_mode='MarkdownV2'
                )
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Unexpected error",
                f"An unexpected error occurred: {e}"
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/calendar", "Calendar overview", "Usage: /calendar [days]", "calendar")
async def calendar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show calendar overview for specified days."""
    try:
        days = 7  # Default to 7 days
        if context.args:
            try:
                days = int(context.args[0])
                if days <= 0 or days > 30:
                    await update.message.reply_text(
                        MessageFormatter.format_error_message(
                            "Invalid number of days",
                            "Please specify a number between 1 and 30."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
            except ValueError:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        "Invalid number format",
                        "Please specify a valid number of days."
                    ),
                    parse_mode='MarkdownV2'
                )
                return
        
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            token = repo.get_token_by_provider("google")
            if not token:
                await update.message.reply_text(
                    MessageFormatter.format_info_message(
                        "📅 Calendar Not Connected",
                        {
                            "Status": "Google Calendar is not connected",
                            "Action": "Use /connect_google to connect your calendar"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
                return
            
            # Load credentials and fetch events (similar to agenda_handler)
            # ... (implementation similar to agenda_handler but for multiple days)
            
            message = f"📅 **Calendar Overview** \\({days} days\\)\n\n"
            message += "Calendar integration is working! More features coming soon."
            
            keyboard = KeyboardBuilder.build_calendar_keyboard()
            
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Unexpected error",
                f"An unexpected error occurred: {e}"
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/connect_google", "Connect Google Calendar", "Usage: /connect_google", "calendar")
async def connect_google_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Connect Google Calendar with rich feedback."""
    try:
        if not os.path.exists(CLIENT_SECRET_FILE):
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Configuration Missing",
                    "client_secret.json not found in project root."
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            if repo.get_token_by_provider("google"):
                await update.message.reply_text(
                    MessageFormatter.format_info_message(
                        "📅 Already Connected",
                        {
                            "Status": "Google Calendar is already connected",
                            "Action": "Use /agenda to view your calendar",
                            "Disconnect": "Use /disconnect to remove connection"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
                return
        
        await update.message.reply_text(
            MessageFormatter.format_info_message(
                "🔗 Connecting Google Calendar",
                {
                    "Instructions": "A browser window will open for Google authentication",
                    "Steps": "1. Complete the authentication process\n2. Grant calendar access\n3. Return here when done",
                    "Security": "Your credentials are stored securely"
                }
            ),
            parse_mode='MarkdownV2'
        )
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = await run_in_thread(flow.run_local_server, port=0)
            
            with next(get_session()) as session:
                repo = CalendarTokenRepository(session)
                repo.remove_token_by_provider("google")
                repo.add_token(
                    provider="google",
                    access_token=creds.token,
                    refresh_token=creds.refresh_token,
                    expiry=creds.expiry
                )
            
            await update.message.reply_text(
                MessageFormatter.format_success_message(
                    "✅ Google Calendar Connected!",
                    {
                        "Status": "Successfully connected and token stored",
                        "Next Steps": "Use /agenda to view your calendar",
                        "Features": "View events, sync calendar, manage schedule"
                    }
                ),
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Authentication Failed",
                    f"Failed to authenticate: {e}"
                ),
                parse_mode='MarkdownV2'
            )
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Unexpected error",
                f"An unexpected error occurred: {e}"
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/disconnect", "Disconnect Google Calendar", "Usage: /disconnect", "calendar")
async def disconnect_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disconnect Google Calendar with confirmation."""
    try:
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            token = repo.remove_token_by_provider("google")
            if not token:
                await update.message.reply_text(
                    MessageFormatter.format_info_message(
                        "📅 No Connection Found",
                        {
                            "Status": "No Google Calendar connection found",
                            "Action": "Use /connect_google to connect your calendar"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
                return
            
            await update.message.reply_text(
                MessageFormatter.format_success_message(
                    "✅ Google Calendar Disconnected",
                    {
                        "Status": "Successfully disconnected and token removed",
                        "Security": "Your credentials have been securely removed",
                        "Reconnect": "Use /connect_google to reconnect anytime"
                    }
                ),
                parse_mode='MarkdownV2'
            )
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Unexpected error",
                f"An unexpected error occurred: {e}"
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/calendar_sync", "Sync calendar with tasks", "Usage: /calendar_sync", "calendar")
async def calendar_sync_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sync calendar events with task system."""
    try:
        await update.message.reply_text(
            MessageFormatter.format_info_message(
                "🔄 Calendar Sync",
                {
                    "Status": "Calendar sync feature coming soon",
                    "Features": "• Sync tasks with calendar events\n• Create events from tasks\n• Update task due dates from calendar",
                    "Progress": "Development in progress"
                }
            ),
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Unexpected error",
                f"An unexpected error occurred: {e}"
            ),
            parse_mode='MarkdownV2'
        )

@command_handler("/calendar_events", "Show upcoming events", "Usage: /calendar_events [count]", "calendar")
async def calendar_events_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show upcoming calendar events."""
    try:
        count = 5  # Default to 5 events
        if context.args:
            try:
                count = int(context.args[0])
                if count <= 0 or count > 20:
                    await update.message.reply_text(
                        MessageFormatter.format_error_message(
                            "Invalid event count",
                            "Please specify a number between 1 and 20."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
            except ValueError:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        "Invalid number format",
                        "Please specify a valid number of events."
                    ),
                    parse_mode='MarkdownV2'
                )
                return
        
        # Implementation similar to agenda_handler but for upcoming events
        await update.message.reply_text(
            MessageFormatter.format_info_message(
                "📅 Upcoming Events",
                {
                    "Status": "Feature coming soon",
                    "Count": f"Will show {count} upcoming events",
                    "Features": "• Event details\n• Time and location\n• Quick actions"
                }
            ),
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Unexpected error",
                f"An unexpected error occurred: {e}"
            ),
            parse_mode='MarkdownV2'
        )

# Helper to run blocking code in a thread (for run_local_server and Google API calls)
async def run_in_thread(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs)) 