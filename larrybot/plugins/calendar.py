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
import uuid
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import asyncio
from functools import partial
import re

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]
CLIENT_SECRET_FILE = "client_secret.json"


def register(event_bus: EventBus, command_registry: CommandRegistry) -> None:
    """Register calendar integration commands."""
    command_registry.register("/agenda", agenda_handler)
    command_registry.register("/calendar", calendar_handler)
    command_registry.register("/connect_google", connect_google_handler)
    command_registry.register("/disconnect", disconnect_handler)
    command_registry.register("/calendar_sync", calendar_sync_handler)
    command_registry.register("/calendar_events", calendar_events_handler)

    # New multi-account commands
    command_registry.register("/accounts", accounts_handler)
    command_registry.register("/account_primary", account_primary_handler)
    command_registry.register("/account_rename", account_rename_handler)
    command_registry.register("/account_deactivate", account_deactivate_handler)
    command_registry.register("/account_reactivate", account_reactivate_handler)
    command_registry.register("/account_delete", account_delete_handler)
    command_registry.register("/calendar_all", calendar_all_handler)


def extract_video_call_link(event):
    """Extract primary video call link from event."""
    video_platforms = {
        'meet.google.com': 'Google Meet',
        'zoom.us': 'Zoom',
        'teams.microsoft.com': 'Microsoft Teams',
        'webex.com': 'Cisco Webex',
        'bluejeans.com': 'BlueJeans',
        'gotomeeting.com': 'GoToMeeting',
        'join.skype.com': 'Skype',
        'discord.gg': 'Discord',
        'slack.com': 'Slack',
        'whereby.com': 'Whereby',
        'jitsi.org': 'Jitsi',
        'meet.jit.si': 'Jitsi',
        'bigbluebutton.org': 'BigBlueButton'
    }
    
    # Check conference data first (Google Meet, Zoom, etc.)
    conference_data = event.get('conferenceData', {})
    entry_points = conference_data.get('entryPoints', [])
    
    for entry_point in entry_points:
        if entry_point.get('entryPointType') == 'video':
            uri = entry_point.get('uri', '')
            for domain, platform in video_platforms.items():
                if domain in uri:
                    return {
                        'url': uri,
                        'platform': platform,
                        'label': entry_point.get('label', '')
                    }
    
    # Check description for video links
    description = event.get('description', '')
    if description:
        for domain, platform in video_platforms.items():
            if domain in description:
                # Extract URL using regex
                url_pattern = rf'https?://[^\s<>"]*{re.escape(domain)}[^\s<>"]*'
                match = re.search(url_pattern, description)
                if match:
                    return {
                        'url': match.group(0),
                        'platform': platform,
                        'label': 'Video Call'
                    }
    
    return None


@command_handler("/agenda", "Show today's agenda", "Usage: /agenda [account_id]", "calendar")
async def agenda_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show today's calendar agenda with rich formatting."""
    try:
        # Get account_id from args if provided
        account_id = context.args[0] if context.args else None
        
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            
            if account_id:
                # Show agenda for specific account
                token = repo.get_token_by_account("google", account_id)
                if not token:
                    await update.message.reply_text(
                        MessageFormatter.format_error_message(
                            "Account Not Found",
                            f"Account '{account_id}' not found. Use /accounts to see available accounts."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
                tokens = [token]  # Single account
            else:
                # Show agenda for all active accounts
                tokens = repo.get_active_tokens("google")
                if not tokens:
                    await update.message.reply_text(
                        MessageFormatter.format_info_message(
                            "📅 Calendar Not Connected",
                            {
                                "Status": "No Google Calendar accounts connected",
                                "Action": "Use /connect_google to connect your first calendar",
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
            
            all_events = []
            account_names = []
            
            # Fetch events from all accounts
            for token in tokens:
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
                        repo.update_token(
                            provider="google",
                            account_id=token.account_id,
                            access_token=creds.token,
                            refresh_token=creds.refresh_token,
                            expiry=creds.expiry
                        )
                    except Exception as e:
                        # Skip this account if token refresh fails
                        print(f"Warning: Token refresh failed for account {token.account_name}: {e}")
                        continue
                
                # Fetch events for this account
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
                        maxResults=20,  # Increased for multi-account
                        singleEvents=True,
                        orderBy="startTime"
                    )
                    events = await run_in_thread(events_result.execute)
                    items = events.get("items", [])
                    
                    # Add account info to each event
                    for event in items:
                        event['_account_name'] = token.account_name
                        event['_account_id'] = token.account_id
                        event['_account_email'] = token.account_email
                        all_events.append(event)
                    
                    account_names.append(token.account_name)
                    
                except Exception as e:
                    # Skip this account if event fetch fails
                    print(f"Warning: Failed to fetch events for account {token.account_name}: {e}")
                    continue
            
            if not all_events:
                account_info = f" \\({', '.join(account_names)}\\)" if account_id else ""
                await update.message.reply_text(
                    MessageFormatter.format_info_message(
                        f"📅 Today's Agenda{account_info}",
                        {
                            "Status": "No events scheduled for today",
                            "Date": today.strftime('%Y-%m-%d'),
                            "Accounts": ", ".join(account_names),
                            "Suggestion": "Enjoy your free time or add some tasks!"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
                return
            
            # Sort all events by start time
            all_events.sort(key=lambda x: x["start"].get("dateTime", x["start"].get("date")))
            
            # Build rich agenda message
            today = datetime.now(timezone.utc).date()
            message = f"📅 *Today's Agenda* \({MessageFormatter.escape_markdown(today.strftime('%B %d, %Y'))}\)\n\n"
            message += f"📋 *{len(all_events)} Events Scheduled*\n\n"
            
            # Find the next upcoming event (first event that hasn't started yet)
            now = datetime.now(timezone.utc)
            next_event_index = None
            for i, event in enumerate(all_events):
                start = event["start"].get("dateTime", event["start"].get("date"))
                if "T" in start:
                    try:
                        event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        if event_time > now:
                            next_event_index = i
                            break
                    except:
                        pass
            
            for i, event in enumerate(all_events, 1):
                # Horizontal line between events
                if i > 1:
                    message += "────────────\n"
                
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date")) if "end" in event else None
                summary = event.get("summary") or "(No title)"
                location = event.get("location", "")
                description = event.get("description", "")
                account_name = event.get("_account_name", "Unknown")
                account_email = event.get("_account_email", "")
                
                # Format time and duration
                if "T" in start:
                    try:
                        event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        time_str = event_time.strftime('%I:%M %p')
                    except:
                        time_str = start
                else:
                    time_str = "All day"
                duration_str = ""
                if end and "T" in start and "T" in end:
                    try:
                        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                        duration = end_dt - start_dt
                        total_minutes = int(duration.total_seconds() // 60)
                        hours = total_minutes // 60
                        minutes = total_minutes % 60
                        if hours and minutes:
                            duration_str = f" ({hours}h {minutes}m)"
                        elif hours:
                            duration_str = f" ({hours}h)"
                        elif minutes:
                            duration_str = f" ({minutes}m)"
                    except:
                        duration_str = ""
                
                # Highlight next event
                next_indicator = "⏭️ " if (i-1) == next_event_index else ""
                
                # Bold event name (MarkdownV2)
                safe_summary = MessageFormatter.escape_markdown(summary)
                message += f"{next_indicator}{i}\\. *{safe_summary}*\n"
                
                # Indented details
                message += f"   🕐 {MessageFormatter.escape_markdown(time_str + duration_str)}\n"
                if account_name and account_name != "Unknown":
                    message += f"   🗂️ {MessageFormatter.escape_markdown(account_name)}\n"
                elif account_email:
                    message += f"   🗂️ {MessageFormatter.escape_markdown(account_email)}\n"
                if location:
                    message += f"   📍 {MessageFormatter.escape_markdown(location)}\n"
                # Video link
                video_link = extract_video_call_link(event)
                if video_link:
                    message += f"   🎥 {MessageFormatter.escape_markdown(video_link['platform'])}: {MessageFormatter.escape_markdown(video_link['url'])}\n"
                elif description:
                    desc_preview = description[:50] + "..." if len(description) > 50 else description
                    message += f"   📝 {MessageFormatter.escape_markdown(desc_preview)}\n"
                message += "\n"
            
            await update.message.reply_text(
                message,
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


@command_handler("/accounts", "List connected calendar accounts", "Usage: /accounts", "calendar")
async def accounts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all connected calendar accounts."""
    try:
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            tokens = repo.get_all_tokens("google")
            
            if not tokens:
                await update.message.reply_text(
                    MessageFormatter.format_info_message(
                        "📅 No Calendar Accounts",
                        {
                            "Status": "No Google Calendar accounts connected",
                            "Action": "Use /connect_google to connect your first calendar",
                            "Features": "Support for multiple accounts"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
                return
            
            message = "📅 **Connected Calendar Accounts**\n\n"
            
            for i, token in enumerate(tokens, 1):
                status = "🟢 Active" if token.is_active else "🔴 Inactive"
                primary = " [PRIMARY]" if token.is_primary else ""
                email = f" \\({token.account_email}\\)" if token.account_email else ""
                
                message += f"{i}\\. **{MessageFormatter.escape_markdown(token.account_name)}**{primary}\n"
                message += f"   ID: `{token.account_id}`\n"
                message += f"   Status: {status}\n"
                if token.account_email:
                    message += f"   Email: {MessageFormatter.escape_markdown(token.account_email)}\n"
                message += "\n"
            
            message += "**Commands:**\n"
            message += "• `/agenda [account_id]` \\- Show agenda for specific account\n"
            message += "• `/account_primary [account_id]` \\- Set account as primary\n"
            message += "• `/account_rename [account_id] [name]` \\- Rename account\n"
            message += "• `/account_deactivate [account_id]` \\- Deactivate account\n"
            message += "• `/account_delete [account_id]` \\- Delete account\n"
            
            await update.message.reply_text(
                message,
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


@command_handler("/connect_google", "Connect Google Calendar", "Usage: /connect_google [account_name]", "calendar")
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
        
        # Get account name from args if provided
        account_name = " ".join(context.args) if context.args else None
        
        # No account limit check for single-user local bot
        await update.message.reply_text(
            MessageFormatter.format_info_message(
                "🔗 Connecting Google Calendar",
                {
                    "Account Name": account_name or "Will be set after connection",
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
            
            # Generate unique account ID
            account_id = str(uuid.uuid4())[:8]
            
            # Get user info to extract email (optional)
            account_email = None
            try:
                service = await run_in_thread(build, "oauth2", "v2", credentials=creds)
                user_info = await run_in_thread(service.userinfo().get().execute)
                account_email = user_info.get("email")
                if account_email is not None and not isinstance(account_email, str):
                    account_email = str(account_email)
            except Exception as e:
                # Email retrieval failed, but we can still proceed with calendar connection
                print(f"Warning: Could not retrieve user email: {e}")
                account_email = None
            
            with next(get_session()) as session:
                repo = CalendarTokenRepository(session)
                repo.add_token(
                    provider="google",
                    account_id=account_id,
                    account_name=account_name or "Unknown",  # Use "Unknown" if no name provided
                    access_token=creds.token,
                    refresh_token=creds.refresh_token,
                    expiry=creds.expiry,
                    account_email=account_email
                )
            
            # Success message
            success_message = MessageFormatter.format_success_message(
                "✅ Google Calendar Connected!",
                {
                    "Account ID": account_id,
                    "Email": account_email or "Not available",
                    "Status": "Successfully connected and token stored",
                    "Next Steps": f"Use `/agenda {account_id}` to view your calendar"
                }
            )
            
            # Add custom name prompt if no name was provided
            if not account_name:
                success_message += "\n\n💡 **Set a Custom Name:**\n"
                success_message += f"Use `/account_rename {account_id} [your_custom_name]` to set a friendly name for this calendar\\.\n"
                success_message += "Example: `/account_rename " + account_id + " Personal`"
            
            await update.message.reply_text(
                success_message,
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


@command_handler("/account_primary", "Set primary calendar account", "Usage: /account_primary [account_id]", "calendar")
async def account_primary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set an account as the primary calendar account."""
    try:
        if not context.args:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Missing Account ID",
                    "Please specify an account ID. Use /accounts to see available accounts."
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        account_id = context.args[0]
        
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            
            if repo.set_primary_account("google", account_id):
                token = repo.get_token_by_account("google", account_id)
                await update.message.reply_text(
                    MessageFormatter.format_success_message(
                        "✅ Primary Account Set",
                        {
                            "Account": token.account_name,
                            "Account ID": account_id,
                            "Status": "This account is now your primary calendar",
                            "Next Steps": "Use /agenda to view your primary calendar"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
            else:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        "Account Not Found",
                        f"Account '{account_id}' not found. Use /accounts to see available accounts."
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


@command_handler("/account_rename", "Rename calendar account", "Usage: /account_rename [account_id] [new_name]", "calendar")
async def account_rename_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Rename a calendar account."""
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Missing Parameters",
                    "Please specify account ID and new name. Usage: /account_rename [account_id] [new_name]"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        account_id = context.args[0]
        new_name = " ".join(context.args[1:])
        
        if len(new_name) > 50:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Name Too Long",
                    "Account name must be 50 characters or less."
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            
            token = repo.rename_account("google", account_id, new_name)
            if token:
                await update.message.reply_text(
                    MessageFormatter.format_success_message(
                        "✅ Account Renamed",
                        {
                            "Old Name": token.account_name,
                            "New Name": new_name,
                            "Account ID": account_id,
                            "Status": "Account renamed successfully"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
            else:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        "Account Not Found",
                        f"Account '{account_id}' not found. Use /accounts to see available accounts."
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


@command_handler("/account_deactivate", "Deactivate calendar account", "Usage: /account_deactivate [account_id]", "calendar")
async def account_deactivate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deactivate a calendar account."""
    try:
        if not context.args:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Missing Account ID",
                    "Please specify an account ID. Use /accounts to see available accounts."
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        account_id = context.args[0]
        
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            
            token = repo.deactivate_account("google", account_id)
            if token:
                await update.message.reply_text(
                    MessageFormatter.format_success_message(
                        "✅ Account Deactivated",
                        {
                            "Account": token.account_name,
                            "Account ID": account_id,
                            "Status": "Account deactivated successfully",
                            "Note": "Use /account_reactivate to reactivate this account"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
            else:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        "Account Not Found",
                        f"Account '{account_id}' not found. Use /accounts to see available accounts."
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


@command_handler("/account_reactivate", "Reactivate calendar account", "Usage: /account_reactivate [account_id]", "calendar")
async def account_reactivate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reactivate a deactivated calendar account."""
    try:
        if not context.args:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Missing Account ID",
                    "Please specify an account ID. Use /accounts to see available accounts."
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        account_id = context.args[0]
        
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            
            token = repo.reactivate_account("google", account_id)
            if token:
                await update.message.reply_text(
                    MessageFormatter.format_success_message(
                        "✅ Account Reactivated",
                        {
                            "Account": token.account_name,
                            "Account ID": account_id,
                            "Status": "Account reactivated successfully",
                            "Next Steps": f"Use `/agenda {account_id}` to view your calendar"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
            else:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        "Account Not Found",
                        f"Account '{account_id}' not found or already active. Use /accounts to see available accounts."
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


@command_handler("/account_delete", "Delete calendar account", "Usage: /account_delete [account_id]", "calendar")
async def account_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Permanently delete a calendar account."""
    try:
        if not context.args:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Missing Account ID",
                    "Please specify an account ID. Use /accounts to see available accounts."
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        account_id = context.args[0]
        
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            
            token = repo.remove_account("google", account_id)
            if token:
                await update.message.reply_text(
                    MessageFormatter.format_success_message(
                        "✅ Account Deleted",
                        {
                            "Account": token.account_name,
                            "Account ID": account_id,
                            "Status": "Account permanently deleted",
                            "Security": "All credentials have been removed"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
            else:
                await update.message.reply_text(
                    MessageFormatter.format_error_message(
                        "Account Not Found",
                        f"Account '{account_id}' not found. Use /accounts to see available accounts."
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


@command_handler("/calendar_all", "Show combined calendar view", "Usage: /calendar_all [days]", "calendar")
async def calendar_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show calendar overview from all active accounts."""
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
            tokens = repo.get_active_tokens("google")
            
            if not tokens:
                await update.message.reply_text(
                    MessageFormatter.format_info_message(
                        "📅 No Calendar Accounts",
                        {
                            "Status": "No active Google Calendar accounts found",
                            "Action": "Use /connect_google to connect your first calendar"
                        }
                    ),
                    parse_mode='MarkdownV2'
                )
                return
            
            message = f"📅 **Combined Calendar View** \\({days} days\\)\n\n"
            message += f"📋 **{len(tokens)} Active Accounts**\n\n"
            
            for token in tokens:
                primary = " [PRIMARY]" if token.is_primary else ""
                message += f"• **{MessageFormatter.escape_markdown(token.account_name)}**{primary}\n"
                if token.account_email:
                    message += f"  📧 {MessageFormatter.escape_markdown(token.account_email)}\n"
                message += f"  🆔 `{token.account_id}`\n\n"
            
            message += "**Commands:**\n"
            message += "• `/agenda [account_id]` \\- Show agenda for specific account\n"
            message += "• `/calendar [days] [account_id]` \\- Calendar overview for account\n"
            message += "• `/accounts` \\- Manage your accounts\n"
            
            await update.message.reply_text(
                message,
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


# Keep existing handlers for backward compatibility
@command_handler("/calendar", "Calendar overview", "Usage: /calendar [days] [account_id]", "calendar")
async def calendar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show calendar overview for specified days."""
    try:
        days = 7  # Default to 7 days
        account_id = None
        
        if context.args:
            # Check if first arg is a number (days) or account_id
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
                # If there's a second arg, it's the account_id
                if len(context.args) > 1:
                    account_id = context.args[1]
            except ValueError:
                # First arg is not a number, treat as account_id
                account_id = context.args[0]
        
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            
            if account_id:
                token = repo.get_token_by_account("google", account_id)
                if not token:
                    await update.message.reply_text(
                        MessageFormatter.format_error_message(
                            "Account Not Found",
                            f"Account '{account_id}' not found. Use /accounts to see available accounts."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
            else:
                token = repo.get_primary_token("google")
                if not token:
                    await update.message.reply_text(
                        MessageFormatter.format_info_message(
                            "📅 Calendar Not Connected",
                            {
                                "Status": "No Google Calendar accounts connected",
                                "Action": "Use /connect_google to connect your calendar"
                            }
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
        
            # Load credentials and fetch events (similar to agenda_handler)
            # ... (implementation similar to agenda_handler but for multiple days)
            
            account_info = f" \\({token.account_name}\\)" if account_id else ""
            message = f"📅 **Calendar Overview**{account_info} \\({days} days\\)\n\n"
            message += "Calendar integration is working\\! More features coming soon\\."
            
            await update.message.reply_text(
                message,
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


@command_handler("/disconnect", "Disconnect Google Calendar", "Usage: /disconnect [account_id]", "calendar")
async def disconnect_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disconnect Google Calendar with confirmation."""
    try:
        account_id = context.args[0] if context.args else None
        
        with next(get_session()) as session:
            repo = CalendarTokenRepository(session)
            
            if account_id:
                # Disconnect specific account
                token = repo.remove_account("google", account_id)
                if not token:
                    await update.message.reply_text(
                        MessageFormatter.format_error_message(
                            "Account Not Found",
                            f"Account '{account_id}' not found. Use /accounts to see available accounts."
                        ),
                        parse_mode='MarkdownV2'
                    )
                    return
            else:
                # Disconnect primary account (backward compatibility)
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
                        "Account": token.account_name,
                        "Account ID": token.account_id,
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


@command_handler("/calendar_events", "Show upcoming events", "Usage: /calendar_events [count] [account_id]", "calendar")
async def calendar_events_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show upcoming calendar events."""
    try:
        count = 5  # Default to 5 events
        account_id = None
        
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
                # If there's a second arg, it's the account_id
                if len(context.args) > 1:
                    account_id = context.args[1]
            except ValueError:
                # First arg is not a number, treat as account_id
                account_id = context.args[0]
        
        # Implementation similar to agenda_handler but for upcoming events
        await update.message.reply_text(
            MessageFormatter.format_info_message(
                "📅 Upcoming Events",
                {
                    "Status": "Feature coming soon",
                    "Count": f"Will show {count} upcoming events",
                    "Account": account_id or "Primary account",
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


async def run_in_thread(func, *args, **kwargs):
    """Run a function in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs)) 