# Calendar Integration

LarryBot2 provides comprehensive Google Calendar integration to help you manage your schedule alongside your tasks.

## Features

### 📅 Daily Reports with Calendar Events
The `/daily` command now includes calendar events from all your connected Google Calendar accounts. When you run `/daily`, you'll see:
- **Today's Calendar Events**: All events scheduled for today across all connected calendars
- **Overdue Tasks**: Tasks that are past their due date
- **Due Today**: Tasks due today
- **Habits Due**: Habits that need to be completed today
- **Motivational Quote**: A daily motivational message

### 📋 Agenda View
Use `/agenda` to see a detailed view of today's calendar events with:
- Event times and durations
- Event locations and descriptions
- Account information for multi-calendar setups
- Video call links (automatically detected)

### 🔗 Multi-Account Support
Connect multiple Google Calendar accounts:
- `/accounts` - List all connected accounts
- `/connect_google [account_name]` - Connect a new account
- `/account_primary [account_id]` - Set your primary account
- `/account_rename [account_id] [new_name]` - Rename an account
- `/account_deactivate [account_id]` - Temporarily disable an account
- `/account_reactivate [account_id]` - Re-enable a deactivated account
- `/account_delete [account_id]` - Permanently remove an account

### 📊 Calendar Views
- `/calendar [days] [account_id]` - Calendar overview for specified days
- `/calendar_all [days]` - Combined view from all accounts
- `/calendar_events [count] [account_id]` - Show upcoming events

### 🔄 Calendar Sync
- `/calendar_sync` - Sync calendar events with tasks
- `/disconnect [account_id]` - Disconnect a calendar account

## Setup

1. **Get Google Calendar API Credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Calendar API
   - Create OAuth 2.0 credentials
   - Download the `client_secret.json` file

2. **Configure the Bot**:
   - Place `client_secret.json` in your bot's root directory
   - Ensure the file is named exactly `client_secret.json`

3. **Connect Your First Calendar**:
   ```
   /connect_google "My Personal Calendar"
   ```

4. **View Your Daily Schedule**:
   ```
   /daily
   ```

## Usage Examples

### Daily Planning
```
/daily
```
Shows a comprehensive view of your day including calendar events, tasks, and habits.

### Quick Agenda Check
```
/agenda
```
Get a detailed view of today's calendar events with times and descriptions.

### Multi-Account Management
```
/accounts
/connect_google "Work Calendar"
/agenda work_calendar_id
```

### Calendar Overview
```
/calendar 7
```
View the next 7 days of calendar events.

## Integration Benefits

- **Unified Daily View**: See everything in one place with `/daily`
- **Cross-Platform Sync**: Calendar events from multiple accounts
- **Smart Time Management**: Duration tracking and time conflicts
- **Seamless Workflow**: Calendar and task management in one bot

## Troubleshooting

### Connection Issues
- Ensure `client_secret.json` is in the correct location
- Check that Google Calendar API is enabled
- Verify OAuth redirect URIs are configured correctly

### Missing Events
- Check account activation status with `/accounts`
- Verify calendar permissions in Google Calendar
- Try refreshing tokens with `/calendar_sync`

### Multi-Account Problems
- Use `/account_primary` to set the main account
- Check account status with `/accounts`
- Reconnect problematic accounts with `/connect_google` 