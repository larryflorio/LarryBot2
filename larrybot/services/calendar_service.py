"""
Calendar Service for LarryBot2

This service provides calendar event fetching functionality
for integration with daily reports and other features.
"""
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from larrybot.storage.db import get_session
from larrybot.storage.calendar_token_repository import CalendarTokenRepository
from larrybot.utils.datetime_utils import get_current_datetime
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/userinfo.email', 'openid']
CLIENT_SECRET_FILE = 'client_secret.json'


async def run_in_thread(func, *args, **kwargs):
    """Run a function in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda : func(*args, **kwargs))


class CalendarService:
    """Service for fetching calendar events from all connected accounts."""

    def __init__(self):
        self.client_secrets = None
        self._load_client_secrets()

    def _load_client_secrets(self):
        """Load Google client secrets."""
        try:
            with open(CLIENT_SECRET_FILE, 'r') as f:
                self.client_secrets = json.load(f)['installed']
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            print(f'Warning: Failed to load client secrets: {e}')
            self.client_secrets = None

    async def get_todays_events(self) ->List[Dict[str, Any]]:
        """
        Fetch today's events from all connected Google Calendar accounts.
        
        Returns:
            List of event dictionaries with account information
        """
        if not self.client_secrets:
            return []
        try:
            with next(get_session()) as session:
                repo = CalendarTokenRepository(session)
                tokens = repo.get_active_tokens('google')
                if not tokens:
                    return []
                all_events = []
                for token in tokens:
                    try:
                        creds = Credentials(token=token.access_token,
                            refresh_token=token.refresh_token, token_uri=
                            'https://oauth2.googleapis.com/token',
                            client_id=self.client_secrets['client_id'],
                            client_secret=self.client_secrets[
                            'client_secret'], expiry=token.expiry, scopes=
                            SCOPES)
                        if creds.expired and creds.refresh_token:
                            try:
                                await run_in_thread(creds.refresh, Request())
                                repo.update_token(provider='google',
                                    account_id=token.account_id,
                                    access_token=creds.token, refresh_token
                                    =creds.refresh_token, expiry=creds.expiry)
                            except Exception as e:
                                print(
                                    f'Warning: Token refresh failed for account {token.account_name}: {e}'
                                    )
                                continue
                        service = await run_in_thread(build, 'calendar',
                            'v3', credentials=creds)
                        from larrybot.services.datetime_service import DateTimeService
                        start_of_day = DateTimeService.get_start_of_day()
                        end_of_day = DateTimeService.get_end_of_day()
                        events_result = await run_in_thread(service.events(
                            ).list, calendarId='primary', timeMin=
                            start_of_day.isoformat(), timeMax=end_of_day.
                            isoformat(), maxResults=20, singleEvents=True,
                            orderBy='startTime')
                        events = await run_in_thread(events_result.execute)
                        items = events.get('items', [])
                        for event in items:
                            event['_account_name'] = token.account_name
                            event['_account_id'] = token.account_id
                            event['_account_email'] = token.account_email
                            all_events.append(event)
                    except Exception as e:
                        print(
                            f'Warning: Failed to fetch events for account {token.account_name}: {e}'
                            )
                        continue
                all_events.sort(key=lambda x: x['start'].get('dateTime', x[
                    'start'].get('date')))
                return all_events
        except Exception as e:
            print(f'Error fetching calendar events: {e}')
            return []

    def format_event_for_daily_report(self, event: Dict[str, Any]) ->Dict[
        str, str]:
        """
        Format a calendar event for display in the daily report.
        
        Args:
            event: Calendar event dictionary from Google API
            
        Returns:
            Dictionary with formatted event information
        """
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date')
            ) if 'end' in event else None
        summary = event.get('summary') or '(No title)'
        account_name = event.get('_account_name', 'Unknown')
        if 'T' in start:
            try:
                event_time = datetime.fromisoformat(start.replace('Z',
                    '+00:00'))
                time_str = event_time.strftime('%I:%M %p')
            except:
                time_str = start
        else:
            time_str = 'All day'
        duration_str = ''
        if end and 'T' in start and 'T' in end:
            try:
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                duration = end_dt - start_dt
                total_minutes = int(duration.total_seconds() // 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                if hours and minutes:
                    duration_str = f' ({hours}h {minutes}m)'
                elif hours:
                    duration_str = f' ({hours}h)'
                elif minutes:
                    duration_str = f' ({minutes}m)'
            except:
                duration_str = ''
        return {'time': time_str, 'name': summary, 'duration': duration_str,
            'account': account_name}
