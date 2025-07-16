from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.storage.db import get_session
from larrybot.storage.habit_repository import HabitRepository
from larrybot.utils.ux_helpers import KeyboardBuilder, MessageFormatter
from larrybot.utils.enhanced_ux_helpers import UnifiedButtonBuilder, ButtonType
from larrybot.utils.datetime_utils import get_current_datetime
from larrybot.utils.decorators import command_handler, callback_handler
from typing import Optional
_habit_event_bus = None


def register(event_bus: EventBus, command_registry: CommandRegistry) ->None:
    """Register habit tracking commands with enhanced UX."""
    global _habit_event_bus
    _habit_event_bus = event_bus
    command_registry.register('/habit_add', habit_add_handler)
    command_registry.register('/habit_done', habit_done_handler)
    command_registry.register('/habit_list', habit_list_handler)
    command_registry.register('/habit_delete', habit_delete_handler)
    command_registry.register('/habit_progress', habit_progress_handler)
    command_registry.register('/habit_stats', habit_stats_handler)
    
    # Register callback handlers
    command_registry.register_callback('habit_done', handle_habit_done_callback)
    command_registry.register_callback('habit_progress', handle_habit_progress_callback)
    command_registry.register_callback('habit_delete', handle_habit_delete_callback)
    command_registry.register_callback('habit_add', handle_habit_add_callback)
    command_registry.register_callback('habit_stats', handle_habit_stats_callback)
    command_registry.register_callback('habit_refresh', handle_habit_refresh_callback)


@callback_handler('habit_done', 'Mark habit as done', 'habit')
async def handle_habit_done_callback(query, context: ContextTypes.DEFAULT_TYPE) ->None:
    """Handle habit done callback."""
    try:
        habit_id = int(query.data.split(':')[1])
        with next(get_session()) as session:
            repo = HabitRepository(session)
            habit = repo.get_habit_by_id(habit_id)
            if not habit:
                await query.answer("Habit not found")
                return
            
            # Mark habit as done
            habit = repo.mark_habit_done(habit.name)
            if not habit:
                await query.answer("Failed to mark habit as done")
                return
            
            streak_emoji = ('🔥' if habit.streak >= 7 else '📈' if habit.streak >= 3 else '✅')
            milestone_message = ''
            if habit.streak == 7:
                milestone_message = '\n🎉 **7-day streak milestone!**'
            elif habit.streak == 30:
                milestone_message = '\n🏆 **30-day streak milestone!**'
            elif habit.streak == 100:
                milestone_message = '\n👑 **100-day streak milestone!**'
            
            await query.answer(f"Habit completed! {streak_emoji}")
            
            # Update the message to show completion
            await query.edit_message_text(
                MessageFormatter.format_success_message(
                    f'Habit completed for today! {streak_emoji}',
                    {
                        'Habit': habit.name,
                        'Current Streak': f'{habit.streak} days {streak_emoji}',
                        'Last Completed': habit.last_completed.strftime('%Y-%m-%d %H:%M') if habit.last_completed else 'N/A'
                    }
                ) + milestone_message,
                parse_mode='MarkdownV2'
            )
            
    except (ValueError, IndexError):
        await query.answer("Invalid habit ID")


@callback_handler('habit_progress', 'Show habit progress', 'habit')
async def handle_habit_progress_callback(query, context: ContextTypes.DEFAULT_TYPE) ->None:
    """Handle habit progress callback."""
    try:
        habit_id = int(query.data.split(':')[1])
        with next(get_session()) as session:
            repo = HabitRepository(session)
            habit = repo.get_habit_by_id(habit_id)
            if not habit:
                await query.answer("Habit not found")
                return
            
            # Calculate progress statistics
            today = get_current_datetime().date()
            if habit.last_completed:
                if hasattr(habit.last_completed, 'date'):
                    last_completed_date = habit.last_completed.date()
                else:
                    last_completed_date = habit.last_completed
                days_since_last = (today - last_completed_date).days
                completion_rate = "Today" if days_since_last == 0 else f"{days_since_last} days ago"
            else:
                completion_rate = "Never"
            
            message = f"""📊 **Habit Progress**

**Habit**: {MessageFormatter.escape_markdown(habit.name)}

**Current Status**:
• Streak: {habit.streak} days
• Last Completed: {completion_rate}
• Created: {habit.created_at.strftime('%Y-%m-%d') if habit.created_at else 'N/A'}

**Achievements**:
• {'🔥 7-day streak' if habit.streak >= 7 else '📈 Building momentum'}
• {'🏆 30-day streak' if habit.streak >= 30 else '🔥 Keep going!'}
• {'👑 100-day streak' if habit.streak >= 100 else '🏆 Long way to go!'}"""
            
            keyboard = InlineKeyboardMarkup([[
                UnifiedButtonBuilder.create_button(text='⬅️ Back', callback_data='habit_refresh', button_type=ButtonType.INFO)
            ]])
            
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')
            
    except (ValueError, IndexError):
        await query.answer("Invalid habit ID")


@callback_handler('habit_delete', 'Delete habit', 'habit')
async def handle_habit_delete_callback(query, context: ContextTypes.DEFAULT_TYPE) ->None:
    """Handle habit delete callback."""
    try:
        habit_id = int(query.data.split(':')[1])
        with next(get_session()) as session:
            repo = HabitRepository(session)
            habit = repo.get_habit_by_id(habit_id)
            if not habit:
                await query.answer("Habit not found")
                return
            
            # Delete the habit
            repo.delete_habit(habit.name)
            
            await query.answer(f"Habit '{habit.name}' deleted successfully!")
            await query.edit_message_text(
                MessageFormatter.format_success_message(f"Habit '{habit.name}' deleted successfully!", {
                    'Habit ID': habit.id,
                    'Streak Lost': f'{habit.streak} days'
                }),
                parse_mode='MarkdownV2'
            )
            
    except (ValueError, IndexError):
        await query.answer("Invalid habit ID")


@callback_handler('habit_add', 'Add new habit', 'habit')
async def handle_habit_add_callback(query, context: ContextTypes.DEFAULT_TYPE) ->None:
    """Handle habit add callback."""
    await query.answer("Use /habit_add <name> to add a new habit")


@callback_handler('habit_stats', 'Show habit statistics', 'habit')
async def handle_habit_stats_callback(query, context: ContextTypes.DEFAULT_TYPE) ->None:
    """Handle habit stats callback."""
    with next(get_session()) as session:
        repo = HabitRepository(session)
        habits = repo.list_habits()
        
        if not habits:
            await query.answer("No habits found")
            return
        
        # Calculate overall statistics
        total_habits = len(habits)
        total_streaks = sum(h.streak for h in habits)
        avg_streak = total_streaks / total_habits if total_habits > 0 else 0
        max_streak = max(h.streak for h in habits) if habits else 0
        
        today = get_current_datetime().date()
        completed_today = 0
        for habit in habits:
            if habit.last_completed:
                if hasattr(habit.last_completed, 'date'):
                    last_completed_date = habit.last_completed.date()
                else:
                    last_completed_date = habit.last_completed
                if (today - last_completed_date).days == 0:
                    completed_today += 1
        
        message = f"""📊 **Habit Statistics**

**Overall Progress**:
• Total Habits: {total_habits}
• Completed Today: {completed_today}/{total_habits}
• Average Streak: {avg_streak:.1f} days
• Best Streak: {max_streak} days

**Today's Completion Rate**: {round(completed_today/total_habits*100, 1) if total_habits > 0 else 0}%"""
        
        keyboard = InlineKeyboardMarkup([[
            UnifiedButtonBuilder.create_button(text='⬅️ Back', callback_data='habit_refresh', button_type=ButtonType.INFO)
        ]])
        
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')


@callback_handler('habit_refresh', 'Refresh habit list', 'habit')
async def handle_habit_refresh_callback(query, context: ContextTypes.DEFAULT_TYPE) ->None:
    """Handle habit refresh callback."""
    # Re-run the habit_list handler to refresh the list
    await habit_list_handler(query, context)


async def habit_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Add a new habit with enhanced UX."""
    if not context.args:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Missing habit name',
            'Usage: /habit_add <name>'), parse_mode='MarkdownV2')
        return
    name = ' '.join(context.args).strip()
    if not name:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Habit name cannot be empty',
            'Please provide a valid habit name.'), parse_mode='MarkdownV2')
        return
    with next(get_session()) as session:
        repo = HabitRepository(session)
        if repo.get_habit_by_name(name):
            await update.message.reply_text(MessageFormatter.
                format_error_message(f"Habit '{name}' already exists",
                'Use a different name or check existing habits with /habit_list'
                ), parse_mode='MarkdownV2')
            return
        habit = repo.add_habit(name)
        await update.message.reply_text(MessageFormatter.
            format_success_message(f"Habit '{name}' created successfully!",
            {'Habit ID': habit.id, 'Habit Name': habit.name,
            'Current Streak': habit.streak, 'Created At': habit.created_at.
            strftime('%Y-%m-%d %H:%M') if habit.created_at else 'N/A'}),
            parse_mode='MarkdownV2')


async def habit_done_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """Mark a habit as done with enhanced UX."""
    if not context.args:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Missing habit name',
            'Usage: /habit_done <name>'), parse_mode='MarkdownV2')
        return
    name = ' '.join(context.args).strip()
    with next(get_session()) as session:
        repo = HabitRepository(session)
        habit = repo.mark_habit_done(name)
        if not habit:
            await update.message.reply_text(MessageFormatter.
                format_error_message(f"Habit '{name}' not found",
                'Check the habit name or use /habit_list to see available habits'
                ), parse_mode='MarkdownV2')
            return
        streak_emoji = ('🔥' if habit.streak >= 7 else '📈' if habit.streak >=
            3 else '✅')
        milestone_message = ''
        if habit.streak == 7:
            milestone_message = '\n🎉 **7-day streak milestone!**'
        elif habit.streak == 30:
            milestone_message = '\n🏆 **30-day streak milestone!**'
        elif habit.streak == 100:
            milestone_message = '\n👑 **100-day streak milestone!**'
        await update.message.reply_text(MessageFormatter.
            format_success_message(
            f'Habit completed for today! {streak_emoji}', {'Habit': habit.
            name, 'Current Streak': f'{habit.streak} days {streak_emoji}',
            'Last Completed': habit.last_completed.strftime(
            '%Y-%m-%d %H:%M') if habit.last_completed else 'N/A'}) +
            milestone_message, parse_mode='MarkdownV2')


async def habit_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE
    ) ->None:
    """List all habits with enhanced formatting and per-habit action buttons."""
    with next(get_session()) as session:
        repo = HabitRepository(session)
        habits = repo.list_habits()
        if not habits:
            await update.message.reply_text(MessageFormatter.
                format_error_message('No habits found',
                'Use /habit_add to create your first habit'), parse_mode=
                'MarkdownV2')
            return
        today = get_current_datetime().date()
        message = f'🔄 **All Habits** \\({len(habits)} found\\)\n\n'
        keyboard = []
        for i, habit in enumerate(habits, 1):
            if habit.last_completed:
                if hasattr(habit.last_completed, 'date'):
                    last_completed_date = habit.last_completed.date()
                else:
                    last_completed_date = habit.last_completed
                days_since_last = (today - last_completed_date).days
                if days_since_last == 0:
                    status_emoji = '✅'
                    status_text = 'Completed today'
                    completed_today = True
                elif days_since_last == 1:
                    status_emoji = '⚠️'
                    status_text = 'Missed yesterday'
                    completed_today = False
                else:
                    status_emoji = '❌'
                    status_text = f'Missed {days_since_last} days'
                    completed_today = False
            else:
                status_emoji = '⏳'
                status_text = 'Never completed'
                completed_today = False
            if habit.streak >= 30:
                streak_emoji = '👑'
            elif habit.streak >= 7:
                streak_emoji = '🔥'
            elif habit.streak >= 3:
                streak_emoji = '📈'
            else:
                streak_emoji = '✅'
            message += (
                f'{i}\\. {status_emoji} **{MessageFormatter.escape_markdown(habit.name)}**\n'
                )
            message += f'   {streak_emoji} Streak: {habit.streak} days\n'
            message += f'   📅 {status_text}\n'
            if habit.last_completed:
                message += (
                    f"   🕐 Last: {MessageFormatter.escape_markdown(habit.last_completed.strftime('%Y-%m-%d'))}\n"
                    )
            if habit.created_at:
                message += (
                    f"   📅 Created: {MessageFormatter.escape_markdown(habit.created_at.strftime('%Y-%m-%d'))}\n")
            message += '\n'
            habit_buttons = []
            if not completed_today:
                habit_buttons.append(UnifiedButtonBuilder.create_button(
                    text='✅ Complete', callback_data=
                    f'habit_done:{habit.id}', button_type=ButtonType.PRIMARY))
            habit_buttons.extend([UnifiedButtonBuilder.create_button(text=
                '📊 Progress', callback_data=f'habit_progress:{habit.id}',
                button_type=ButtonType.INFO), UnifiedButtonBuilder.
                create_button(text='🗑️ Delete', callback_data=
                f'habit_delete:{habit.id}', button_type=ButtonType.DANGER)])
            keyboard.append(habit_buttons)
        keyboard.append([UnifiedButtonBuilder.create_button(text=
            '➕ Add Habit', callback_data='habit_add', button_type=ButtonType.PRIMARY), UnifiedButtonBuilder.create_button(text=
            '📊 Statistics', callback_data='habit_stats', button_type=ButtonType.SECONDARY)])
        keyboard.append([UnifiedButtonBuilder.create_button(text=
            '🔄 Refresh', callback_data='habit_refresh', button_type=ButtonType.SECONDARY), UnifiedButtonBuilder.create_button(text=
            '⬅️ Back', callback_data='nav_main', button_type=ButtonType.INFO)])
        await update.message.reply_text(message, reply_markup=
            InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')


async def habit_delete_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Delete a habit with confirmation dialog."""
    if not context.args:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Missing habit name',
            'Usage: /habit_delete <name>'), parse_mode='MarkdownV2')
        return
    name = ' '.join(context.args).strip()
    with next(get_session()) as session:
        repo = HabitRepository(session)
        habit = repo.get_habit_by_name(name)
        if not habit:
            await update.message.reply_text(MessageFormatter.
                format_error_message(f"Habit '{name}' not found",
                'Check the habit name or use /habit_list to see available habits'
                ), parse_mode='MarkdownV2')
            return
        keyboard = KeyboardBuilder.build_confirmation_keyboard('habit_delete',
            habit.id)
        await update.message.reply_text(
            f"""🗑️ **Confirm Habit Deletion**

**Habit**: {MessageFormatter.escape_markdown(name)}
**Current Streak**: {habit.streak} days
**Created**: {habit.created_at.strftime('%Y-%m-%d') if habit.created_at else 'N/A'}

⚠️ **Warning**: This will permanently delete the habit and all progress data\\.

Are you sure you want to delete this habit?"""
            , reply_markup=keyboard, parse_mode='MarkdownV2')


async def habit_progress_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Show detailed habit progress with visual indicators."""
    if not context.args:
        await update.message.reply_text(MessageFormatter.
            format_error_message('Missing habit name',
            'Usage: /habit_progress <name>'), parse_mode='MarkdownV2')
        return
    name = ' '.join(context.args).strip()
    with next(get_session()) as session:
        repo = HabitRepository(session)
        habit = repo.get_habit_by_name(name)
        if not habit:
            await update.message.reply_text(MessageFormatter.
                format_error_message(f"Habit '{name}' not found",
                'Check the habit name or use /habit_list to see available habits'
                ), parse_mode='MarkdownV2')
            return
        today = get_current_datetime().date()
        days_since_creation = (today - habit.created_at.date()
            ).days + 1 if habit.created_at else 0
        completion_rate = (habit.streak / days_since_creation * 100 if 
            days_since_creation > 0 else 0)
        progress_length = int(habit.streak / max(days_since_creation, 1) * 30)
        progress_bar = '█' * progress_length + '░' * (30 - progress_length)
        next_milestone = None
        if habit.streak < 7:
            next_milestone = 7
        elif habit.streak < 30:
            next_milestone = 30
        elif habit.streak < 100:
            next_milestone = 100
        else:
            next_milestone = habit.streak + 10
        days_to_milestone = next_milestone - habit.streak
        message = f'📊 **Habit Progress Report**\n\n'
        message += (
            f'**Habit**: {MessageFormatter.escape_markdown(habit.name)}\n')
        message += f'**Current Streak**: {habit.streak} days\n'
        message += f'**Days Tracked**: {days_since_creation} days\n'
        message += f'**Completion Rate**: {completion_rate:.1f}%\n\n'
        message += f'📈 **Progress Bar**\n'
        message += f'`{progress_bar}`\n'
        message += f'`{habit.streak:>3} / {days_since_creation:>3} days`\n\n'
        if next_milestone:
            message += f'🎯 **Next Milestone**\n'
            message += f'• Target: {next_milestone} days\n'
            message += f'• Days needed: {days_to_milestone}\n\n'
        if habit.last_completed:
            if hasattr(habit.last_completed, 'date'):
                last_completed_date = habit.last_completed.date()
            else:
                last_completed_date = habit.last_completed
            days_since_last = (today - last_completed_date).days
            message += f'📅 **Recent Activity**\n'
            if hasattr(habit.last_completed, 'strftime'):
                last_completed_str = habit.last_completed.strftime(
                    '%Y-%m-%d %H:%M')
            else:
                last_completed_str = str(habit.last_completed)
            message += f'• Last completed: {last_completed_str}\n'
            if days_since_last == 0:
                message += f'• Status: ✅ Completed today\n'
            elif days_since_last == 1:
                message += f'• Status: ⚠️ Missed yesterday\n'
            else:
                message += f'• Status: ❌ Missed {days_since_last} days\n'
        keyboard = KeyboardBuilder.build_habit_detail_keyboard(habit.id,
            habit.name)
        await update.message.reply_text(message, reply_markup=keyboard,
            parse_mode='MarkdownV2')


async def habit_stats_handler(update: Update, context: ContextTypes.
    DEFAULT_TYPE) ->None:
    """Show comprehensive habit statistics and insights."""
    with next(get_session()) as session:
        repo = HabitRepository(session)
        habits = repo.list_habits()
        if not habits:
            await update.message.reply_text(MessageFormatter.
                format_error_message('No habits to analyze',
                'Add some habits first with /habit_add'), parse_mode=
                'MarkdownV2')
            return
        total_habits = len(habits)
        total_streaks = sum(h.streak for h in habits)
        active_habits = sum(1 for h in habits if h.streak > 0)
        habits_by_streak = sorted(habits, key=lambda h: h.streak, reverse=True)
        best_habit = habits_by_streak[0] if habits_by_streak else None
        avg_streak = total_streaks / total_habits if total_habits > 0 else 0
        message = f'📊 **Habit Statistics Report**\n\n'
        message += f'📈 **Overall Statistics**\n'
        message += f'• Total Habits: {total_habits}\n'
        message += f'• Active Habits: {active_habits}\n'
        message += f'• Total Streak Days: {total_streaks}\n'
        message += f'• Average Streak: {avg_streak:.1f} days\n\n'
        message += f'🏆 **Top Performers**\n'
        for i, habit in enumerate(habits_by_streak[:3], 1):
            if habit.streak > 0:
                if habit.streak >= 30:
                    performance = '👑'
                elif habit.streak >= 7:
                    performance = '🔥'
                else:
                    performance = '📈'
                message += f"""{i}\\. {performance} **{MessageFormatter.escape_markdown(habit.name)}**
"""
                message += f'   📊 {habit.streak} day streak\n'
                if habit.last_completed:
                    message += (
                        f"   📅 Last: {habit.last_completed.strftime('%Y-%m-%d')}\n"
                        )
                message += '\n'
        message += f'💡 **Insights**\n'
        if best_habit and best_habit.streak >= 7:
            message += f"""• 🏆 **Best Habit**: {MessageFormatter.escape_markdown(best_habit.name)} \\({best_habit.streak} days\\)
"""
        if avg_streak < 3:
            message += f"""• 📉 **Low average streak** \\({avg_streak:.1f} days\\) - Consider smaller, more achievable goals
"""
        elif avg_streak >= 7:
            message += (
                f'• 🎉 **Excellent consistency!** Average streak: {avg_streak:.1f} days\n'
                )
        inactive_count = total_habits - active_habits
        if inactive_count > 0:
            message += f"""• ⚠️ **{inactive_count} inactive habits** - Consider reviewing or removing them
"""
        if total_streaks > 0:
            message += f"""
🎯 **Keep going!** You've maintained {total_streaks} total streak days across all habits\\."""
        await update.message.reply_text(message, parse_mode='MarkdownV2')
