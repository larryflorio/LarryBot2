from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from larrybot.core.command_registry import CommandRegistry
from larrybot.core.event_bus import EventBus
from larrybot.storage.db import get_session
from larrybot.storage.habit_repository import HabitRepository
from larrybot.utils.ux_helpers import KeyboardBuilder, MessageFormatter
from larrybot.utils.datetime_utils import get_current_datetime
from typing import Optional

_habit_event_bus = None

def register(event_bus: EventBus, command_registry: CommandRegistry) -> None:
    """Register habit tracking commands with enhanced UX."""
    global _habit_event_bus
    _habit_event_bus = event_bus
    
    command_registry.register("/habit_add", habit_add_handler)
    command_registry.register("/habit_done", habit_done_handler)
    command_registry.register("/habit_list", habit_list_handler)
    command_registry.register("/habit_delete", habit_delete_handler)
    command_registry.register("/habit_progress", habit_progress_handler)
    command_registry.register("/habit_stats", habit_stats_handler)

async def habit_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a new habit with enhanced UX."""
    if not context.args:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Missing habit name",
                "Usage: /habit_add <name>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    name = " ".join(context.args).strip()
    if not name:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Habit name cannot be empty",
                "Please provide a valid habit name."
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    with next(get_session()) as session:
        repo = HabitRepository(session)
        if repo.get_habit_by_name(name):
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"Habit '{name}' already exists",
                    "Use a different name or check existing habits with /habit_list"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        habit = repo.add_habit(name)
        
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"Habit '{name}' created successfully!",
                {
                    "Habit ID": habit.id,
                    "Habit Name": habit.name,
                    "Current Streak": habit.streak,
                    "Created At": habit.created_at.strftime("%Y-%m-%d %H:%M") if habit.created_at else "N/A"
                }
            ),
            parse_mode='MarkdownV2'
        )

async def habit_done_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark a habit as done with enhanced UX."""
    if not context.args:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Missing habit name",
                "Usage: /habit_done <name>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    name = " ".join(context.args).strip()
    
    with next(get_session()) as session:
        repo = HabitRepository(session)
        habit = repo.mark_habit_done(name)
        
        if not habit:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"Habit '{name}' not found",
                    "Check the habit name or use /habit_list to see available habits"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Calculate streak emoji
        streak_emoji = "🔥" if habit.streak >= 7 else "📈" if habit.streak >= 3 else "✅"
        
        # Check if this is a milestone
        milestone_message = ""
        if habit.streak == 7:
            milestone_message = "\n🎉 **7-day streak milestone!**"
        elif habit.streak == 30:
            milestone_message = "\n🏆 **30-day streak milestone!**"
        elif habit.streak == 100:
            milestone_message = "\n👑 **100-day streak milestone!**"
        
        await update.message.reply_text(
            MessageFormatter.format_success_message(
                f"Habit completed for today! {streak_emoji}",
                {
                    "Habit": habit.name,
                    "Current Streak": f"{habit.streak} days {streak_emoji}",
                    "Last Completed": habit.last_completed.strftime("%Y-%m-%d %H:%M") if habit.last_completed else "N/A"
                }
            ) + milestone_message,
            parse_mode='MarkdownV2'
        )

async def habit_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all habits with enhanced formatting and per-habit action buttons."""
    with next(get_session()) as session:
        repo = HabitRepository(session)
        habits = repo.list_habits()
        
        if not habits:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "No habits found",
                    "Use /habit_add to create your first habit"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Calculate today's date for streak calculations
        today = get_current_datetime().date()
        
        # Format habit list with rich formatting and action buttons
        message = f"🔄 **All Habits** \\({len(habits)} found\\)\n\n"
        
        # Create inline keyboard with per-habit action buttons
        keyboard = []
        
        for i, habit in enumerate(habits, 1):
            # Calculate streak status
            if habit.last_completed:
                # Handle both datetime and date objects
                if hasattr(habit.last_completed, 'date'):
                    last_completed_date = habit.last_completed.date()
                else:
                    last_completed_date = habit.last_completed
                days_since_last = (today - last_completed_date).days
                
                if days_since_last == 0:
                    status_emoji = "✅"  # Done today
                    status_text = "Completed today"
                    completed_today = True
                elif days_since_last == 1:
                    status_emoji = "⚠️"  # Missed yesterday
                    status_text = "Missed yesterday"
                    completed_today = False
                else:
                    status_emoji = "❌"  # Missed multiple days
                    status_text = f"Missed {days_since_last} days"
                    completed_today = False
            else:
                status_emoji = "⏳"  # Never completed
                status_text = "Never completed"
                completed_today = False
            
            # Streak emoji based on length
            if habit.streak >= 30:
                streak_emoji = "👑"
            elif habit.streak >= 7:
                streak_emoji = "🔥"
            elif habit.streak >= 3:
                streak_emoji = "📈"
            else:
                streak_emoji = "✅"
            
            message += f"{i}\\. {status_emoji} **{MessageFormatter.escape_markdown(habit.name)}**\n"
            message += f"   {streak_emoji} Streak: {habit.streak} days\n"
            message += f"   📅 {status_text}\n"
            
            if habit.last_completed:
                message += f"   🕐 Last: {habit.last_completed.strftime('%Y-%m-%d')}\n"
            
            if habit.created_at:
                message += f"   📅 Created: {habit.created_at.strftime('%Y-%m-%d')}\n"
            message += "\n"
            
            # Add per-habit action buttons
            habit_buttons = []
            
            # Show complete button only if not completed today
            if not completed_today:
                habit_buttons.append(InlineKeyboardButton(
                    "✅ Complete", 
                    callback_data=f"habit_done:{habit.id}"
                ))
            
            habit_buttons.extend([
                InlineKeyboardButton(
                    "📊 Progress", 
                    callback_data=f"habit_progress:{habit.id}"
                ),
                InlineKeyboardButton(
                    "🗑️ Delete", 
                    callback_data=f"habit_delete:{habit.id}"
                )
            ])
            
            keyboard.append(habit_buttons)
        
        # Add navigation buttons at the bottom
        keyboard.append([
            InlineKeyboardButton("➕ Add Habit", callback_data="habit_add"),
            InlineKeyboardButton("📊 Statistics", callback_data="habit_stats")
        ])
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="habit_refresh"),
            InlineKeyboardButton("⬅️ Back", callback_data="nav_main")
        ])
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )

async def habit_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a habit with confirmation dialog."""
    if not context.args:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Missing habit name",
                "Usage: /habit_delete <name>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    name = " ".join(context.args).strip()
    
    with next(get_session()) as session:
        repo = HabitRepository(session)
        habit = repo.get_habit_by_name(name)
        
        if not habit:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"Habit '{name}' not found",
                    "Check the habit name or use /habit_list to see available habits"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Show confirmation dialog with inline keyboard
        keyboard = KeyboardBuilder.build_confirmation_keyboard("habit_delete", habit.id)
        
        await update.message.reply_text(
            f"🗑️ **Confirm Habit Deletion**\n\n"
            f"**Habit**: {MessageFormatter.escape_markdown(name)}\n"
            f"**Current Streak**: {habit.streak} days\n"
            f"**Created**: {habit.created_at.strftime('%Y-%m-%d') if habit.created_at else 'N/A'}\n\n"
            f"⚠️ **Warning**: This will permanently delete the habit and all progress data\\.\n\n"
            f"Are you sure you want to delete this habit?",
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )

async def habit_progress_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed habit progress with visual indicators."""
    if not context.args:
        await update.message.reply_text(
            MessageFormatter.format_error_message(
                "Missing habit name",
                "Usage: /habit_progress <name>"
            ),
            parse_mode='MarkdownV2'
        )
        return
    
    name = " ".join(context.args).strip()
    
    with next(get_session()) as session:
        repo = HabitRepository(session)
        habit = repo.get_habit_by_name(name)
        
        if not habit:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    f"Habit '{name}' not found",
                    "Check the habit name or use /habit_list to see available habits"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Calculate progress metrics
        today = get_current_datetime().date()
        days_since_creation = (today - habit.created_at.date()).days + 1 if habit.created_at else 0
        completion_rate = (habit.streak / days_since_creation * 100) if days_since_creation > 0 else 0
        
        # Visual progress bar (30 characters)
        progress_length = int((habit.streak / max(days_since_creation, 1)) * 30)
        progress_bar = "█" * progress_length + "░" * (30 - progress_length)
        
        # Streak milestone
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
        
        # Format progress details
        message = f"📊 **Habit Progress Report**\n\n"
        message += f"**Habit**: {MessageFormatter.escape_markdown(habit.name)}\n"
        message += f"**Current Streak**: {habit.streak} days\n"
        message += f"**Days Tracked**: {days_since_creation} days\n"
        message += f"**Completion Rate**: {completion_rate:.1f}%\n\n"
        
        message += f"📈 **Progress Bar**\n"
        message += f"`{progress_bar}`\n"
        message += f"`{habit.streak:>3} / {days_since_creation:>3} days`\n\n"
        
        if next_milestone:
            message += f"🎯 **Next Milestone**\n"
            message += f"• Target: {next_milestone} days\n"
            message += f"• Days needed: {days_to_milestone}\n\n"
        
        if habit.last_completed:
            # Handle both datetime and date objects
            if hasattr(habit.last_completed, 'date'):
                last_completed_date = habit.last_completed.date()
            else:
                last_completed_date = habit.last_completed
            days_since_last = (today - last_completed_date).days
            
            message += f"📅 **Recent Activity**\n"
            # Format the date display based on the type
            if hasattr(habit.last_completed, 'strftime'):
                last_completed_str = habit.last_completed.strftime('%Y-%m-%d %H:%M')
            else:
                last_completed_str = str(habit.last_completed)
            message += f"• Last completed: {last_completed_str}\n"
            
            if days_since_last == 0:
                message += f"• Status: ✅ Completed today\n"
            elif days_since_last == 1:
                message += f"• Status: ⚠️ Missed yesterday\n"
            else:
                message += f"• Status: ❌ Missed {days_since_last} days\n"
        
        # Create action keyboard for this habit
        keyboard = KeyboardBuilder.build_habit_detail_keyboard(habit.id, habit.name)
        
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )

async def habit_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show comprehensive habit statistics and insights."""
    with next(get_session()) as session:
        repo = HabitRepository(session)
        habits = repo.list_habits()
        
        if not habits:
            await update.message.reply_text(
                MessageFormatter.format_error_message(
                    "No habits to analyze",
                    "Add some habits first with /habit_add"
                ),
                parse_mode='MarkdownV2'
            )
            return
        
        # Calculate overall statistics
        total_habits = len(habits)
        total_streaks = sum(h.streak for h in habits)
        active_habits = sum(1 for h in habits if h.streak > 0)
        
        # Find top performers
        habits_by_streak = sorted(habits, key=lambda h: h.streak, reverse=True)
        best_habit = habits_by_streak[0] if habits_by_streak else None
        
        # Calculate average streak
        avg_streak = total_streaks / total_habits if total_habits > 0 else 0
        
        message = f"📊 **Habit Statistics Report**\n\n"
        
        message += f"📈 **Overall Statistics**\n"
        message += f"• Total Habits: {total_habits}\n"
        message += f"• Active Habits: {active_habits}\n"
        message += f"• Total Streak Days: {total_streaks}\n"
        message += f"• Average Streak: {avg_streak:.1f} days\n\n"
        
        message += f"🏆 **Top Performers**\n"
        for i, habit in enumerate(habits_by_streak[:3], 1):
            if habit.streak > 0:
                # Performance indicator
                if habit.streak >= 30:
                    performance = "👑"
                elif habit.streak >= 7:
                    performance = "🔥"
                else:
                    performance = "📈"
                
                message += f"{i}\\. {performance} **{MessageFormatter.escape_markdown(habit.name)}**\n"
                message += f"   📊 {habit.streak} day streak\n"
                
                if habit.last_completed:
                    message += f"   📅 Last: {habit.last_completed.strftime('%Y-%m-%d')}\n"
                message += "\n"
        
        # Insights and recommendations
        message += f"💡 **Insights**\n"
        
        if best_habit and best_habit.streak >= 7:
            message += f"• 🏆 **Best Habit**: {MessageFormatter.escape_markdown(best_habit.name)} \\({best_habit.streak} days\\)\n"
        
        if avg_streak < 3:
            message += f"• 📉 **Low average streak** \\({avg_streak:.1f} days\\) - Consider smaller, more achievable goals\n"
        elif avg_streak >= 7:
            message += f"• 🎉 **Excellent consistency!** Average streak: {avg_streak:.1f} days\n"
        
        inactive_count = total_habits - active_habits
        if inactive_count > 0:
            message += f"• ⚠️ **{inactive_count} inactive habits** - Consider reviewing or removing them\n"
        
        # Motivational message
        if total_streaks > 0:
            message += f"\n🎯 **Keep going!** You've maintained {total_streaks} total streak days across all habits\\."
        
        await update.message.reply_text(
            message,
            parse_mode='MarkdownV2'
        ) 