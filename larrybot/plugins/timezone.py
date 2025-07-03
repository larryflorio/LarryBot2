"""
Timezone management plugin for LarryBot2.

This plugin provides commands for managing timezone settings,
including viewing current timezone, setting timezone manually,
and listing available timezones.
"""

from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from larrybot.utils.decorators import command_handler
from larrybot.core.timezone import get_timezone_service, initialize_timezone_service
from larrybot.utils.datetime_utils import get_timezone_info, set_timezone, reset_timezone_to_auto
from larrybot.utils.enhanced_ux_helpers import MessageFormatter, escape_markdown_v2
from larrybot.utils.ux_helpers import KeyboardBuilder


@command_handler("/timezone", "Show current timezone information", "Usage: /timezone", "system")
async def timezone_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current timezone information."""
    try:
        tz_service = get_timezone_service()
        tz_info = get_timezone_info()
        
        # Format timezone information
        message = "🌍 **Timezone Information**\n\n"
        
        # Current timezone
        message += f"📍 **Current Timezone**: `{tz_info['timezone_name']}`\n"
        
        # Detection method
        if tz_info['is_auto_detected']:
            message += "🔍 **Detection**: Auto-detected\n"
        else:
            message += "⚙️ **Detection**: Manually configured\n"
        
        # Current times
        message += f"🕐 **Local Time**: `{tz_info['current_local_time']}`\n"
        message += f"🌐 **UTC Time**: `{tz_info['current_utc_time']}`\n"
        
        # UTC offset
        offset_hours = tz_info['utc_offset']
        offset_sign = "+" if offset_hours >= 0 else ""
        message += f"⏰ **UTC Offset**: `{offset_sign}{offset_hours:.1f} hours`\n"
        
        # DST information
        if tz_info['is_dst']:
            dst_hours = tz_info['dst_offset']
            message += f"☀️ **DST**: Active \\(+{dst_hours:.1f} hours\\)\n"
        else:
            message += "🌙 **DST**: Inactive\n"
        
        # Detection details
        if tz_info['detected_timezone']:
            message += f"🔍 **Detected**: `{tz_info['detected_timezone']}`\n"
        
        if tz_info['manual_override']:
            message += f"⚙️ **Manual Override**: `{tz_info['manual_override']}`\n"
        
        # Create keyboard with timezone management options
        keyboard = KeyboardBuilder.build_timezone_keyboard()
        
        await update.message.reply_text(escape_markdown_v2(message), reply_markup=keyboard, parse_mode='MarkdownV2')
        
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Error retrieving timezone information",
                str(e)
            ),
            parse_mode='MarkdownV2'
        )


@command_handler("/settimezone", "Set timezone manually", "Usage: /settimezone <timezone_name>", "system")
async def set_timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set timezone manually."""
    if not context.args:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Missing timezone name",
                "Usage: /settimezone <timezone_name>\nExample: /settimezone America/New_York"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    timezone_name = " ".join(context.args)
    
    try:
        success = set_timezone(timezone_name)
        
        if success:
            tz_info = get_timezone_info()
            await update.message.reply_text(
                MessageFormatter.format_success_message(
                    "Timezone set successfully!",
                    {
                        "New Timezone": tz_info['timezone_name'],
                        "Local Time": tz_info['current_local_time'],
                        "UTC Offset": f"{tz_info['utc_offset']:+.1f} hours"
                    }
                ),
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Invalid timezone name",
                    f"'{timezone_name}' is not a valid timezone.\nUse /listtimezones to see available options."
                ),
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Error setting timezone",
                str(e)
            ),
            parse_mode='MarkdownV2'
        )


@command_handler("/listtimezones", "List available timezones", "Usage: /listtimezones [search_term]", "system")
async def list_timezones_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List available timezones, optionally filtered by search term."""
    try:
        search_term = " ".join(context.args) if context.args else None
        tz_service = get_timezone_service()
        
        timezones = tz_service.list_available_timezones(search_term)
        
        if not timezones:
            message = MessageFormatter.format_info_message(
                "No timezones found",
                f"No timezones match '{search_term}'" if search_term else "No timezones available"
            )
            await update.message.reply_text(message, parse_mode='MarkdownV2')
            return
        
        # Limit results to avoid message length issues
        max_results = 50
        if len(timezones) > max_results:
            timezones = timezones[:max_results]
            message = f"🌍 **Available Timezones** \\(showing first {max_results}\\)\n\n"
        else:
            message = f"🌍 **Available Timezones** \\({len(timezones)} total\\)\n\n"
        
        if search_term:
            message += f"🔍 **Search Term**: `{search_term}`\n\n"
        
        # Group timezones by region
        regions = {}
        for tz in timezones:
            parts = tz.split('/')
            if len(parts) >= 2:
                region = parts[0]
                if region not in regions:
                    regions[region] = []
                regions[region].append(tz)
            else:
                if 'Other' not in regions:
                    regions['Other'] = []
                regions['Other'].append(tz)
        
        # Display grouped timezones
        for region in sorted(regions.keys()):
            if region == 'Other':
                continue  # Skip Other for now
            
            message += f"**{region}**\n"
            for tz in regions[region][:10]:  # Limit per region
                message += f"• `{tz}`\n"
            
            if len(regions[region]) > 10:
                message += f"• ... and {len(regions[region]) - 10} more\n"
            message += "\n"
        
        # Add usage instructions
        message += "💡 **Usage**: `/settimezone <timezone_name>`\n"
        message += "Example: `/settimezone America/New_York`"
        
        await update.message.reply_text(escape_markdown_v2(message), parse_mode='MarkdownV2')
        
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Error listing timezones",
                str(e)
            ),
            parse_mode='MarkdownV2'
        )


@command_handler("/autotimezone", "Reset to automatic timezone detection", "Usage: /autotimezone", "system")
async def auto_timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset to automatic timezone detection."""
    try:
        success = reset_timezone_to_auto()
        
        if success:
            tz_info = get_timezone_info()
            await update.message.reply_text(
                MessageFormatter.format_success_message(
                    "Reset to automatic timezone detection!",
                    {
                        "Detected Timezone": tz_info['timezone_name'],
                        "Local Time": tz_info['current_local_time'],
                        "Detection Method": "Auto-detected"
                    }
                ),
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "Failed to reset timezone",
                    "No automatically detected timezone available. Manual configuration required."
                ),
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Error resetting timezone",
                str(e)
            ),
            parse_mode='MarkdownV2'
        )


@command_handler("/searchtimezone", "Search for timezones", "Usage: /searchtimezone <search_term>", "system")
async def search_timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for timezones by name."""
    if not context.args:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Missing search term",
                "Usage: /searchtimezone <search_term>\nExample: /searchtimezone New York"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    search_term = " ".join(context.args)
    
    try:
        tz_service = get_timezone_service()
        timezones = tz_service.list_available_timezones(search_term)
        
        if not timezones:
            await update.message.reply_text(
                MessageFormatter.format_info_message(
                    "No timezones found",
                    f"No timezones match '{search_term}'"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Limit results
        max_results = 20
        if len(timezones) > max_results:
            timezones = timezones[:max_results]
            message = f"🔍 **Search Results for '{search_term}'** \\(showing first {max_results}\\)\n\n"
        else:
            message = f"🔍 **Search Results for '{search_term}'** \\({len(timezones)} found\\)\n\n"
        
        for tz in timezones:
            message += f"• `{tz}`\n"
        
        message += "\n💡 **Usage**: `/settimezone <timezone_name>`"
        
        await update.message.reply_text(escape_markdown_v2(message), parse_mode='MarkdownV2')
        
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Error searching timezones",
                str(e)
            ),
            parse_mode='MarkdownV2'
        )


@command_handler("/currenttime", "Show current time in different formats", "Usage: /currenttime", "system")
async def current_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current time in different formats."""
    try:
        tz_info = get_timezone_info()
        
        message = "🕐 **Current Time**\n\n"
        message += f"📍 **Local**: `{tz_info['current_local_time']}`\n"
        message += f"🌐 **UTC**: `{tz_info['current_utc_time']}`\n"
        message += f"⏰ **Timezone**: `{tz_info['timezone_name']}`\n"
        
        # Format in different styles
        from larrybot.utils.datetime_utils import get_current_datetime, format_datetime_for_display
        
        now = get_current_datetime()
        message += f"📅 **Date**: `{format_datetime_for_display(now, '%Y-%m-%d')}`\n"
        message += f"🕐 **Time**: `{format_datetime_for_display(now, '%H:%M:%S')}`\n"
        message += f"📆 **Full**: `{format_datetime_for_display(now, '%A, %B %d, %Y at %I:%M %p')}`\n"
        
        await update.message.reply_text(escape_markdown_v2(message), parse_mode='MarkdownV2')
        
    except Exception as e:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Error getting current time",
                str(e)
            ),
            parse_mode='MarkdownV2'
        ) 