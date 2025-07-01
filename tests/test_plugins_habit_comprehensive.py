"""
Comprehensive habit plugin testing with edge cases and error scenarios.

This test suite targets the 44% coverage gap in larrybot/plugins/habit.py
to achieve 80%+ coverage through comprehensive testing of all habit functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta
from larrybot.plugins.habit import (
    register,
    habit_add_handler,
    habit_done_handler,
    habit_list_handler,
    habit_delete_handler,
    habit_progress_handler,
    habit_stats_handler
)
from larrybot.storage.habit_repository import HabitRepository
from larrybot.models.habit import Habit


class TestHabitPluginComprehensive:
    """Comprehensive habit plugin testing with edge cases."""

    def test_register_commands_comprehensive(self, command_registry, event_bus):
        """Test that habit plugin registers all commands correctly."""
        register(event_bus, command_registry)
        
        registered_commands = list(command_registry._commands.keys())
        assert "/habit_add" in registered_commands
        assert "/habit_done" in registered_commands
        assert "/habit_list" in registered_commands
        assert "/habit_delete" in registered_commands
        assert "/habit_progress" in registered_commands
        assert "/habit_stats" in registered_commands

    # Habit Add Handler Tests

    @pytest.mark.asyncio
    async def test_habit_add_handler_no_args(self, test_session, mock_update, mock_context):
        """Test habit_add handler when no arguments are provided."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = []
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_add_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Missing habit name" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_habit_add_handler_empty_name(self, test_session, mock_update, mock_context):
        """Test habit_add handler with empty habit name."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["   "]  # Whitespace only
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_add_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Habit name cannot be empty" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_habit_add_handler_success(self, test_session, mock_update, mock_context):
        """Test habit_add handler with valid arguments."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_add_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Habit 'Exercise' created successfully" in response_text
            assert parse_mode == 'MarkdownV2'
            
            # Verify habit was created in database
            repo = HabitRepository(test_session)
            habit = repo.get_habit_by_name("Exercise")
            assert habit is not None
            assert habit.name == "Exercise"
            assert habit.streak == 0
            assert habit.last_completed is None

    @pytest.mark.asyncio
    async def test_habit_add_handler_multiple_words(self, test_session, mock_update, mock_context):
        """Test habit_add handler with multiple word habit name."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Drink", "water", "daily"]
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_add_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Habit 'Drink water daily' created successfully" in response_text
            assert parse_mode == 'MarkdownV2'
            
            # Verify habit was created with combined name
            repo = HabitRepository(test_session)
            habit = repo.get_habit_by_name("Drink water daily")
            assert habit is not None
            assert habit.name == "Drink water daily"

    @pytest.mark.asyncio
    async def test_habit_add_handler_already_exists(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_add handler when habit already exists."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        # Create a habit first
        db_habit_factory(name="Exercise")
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_add_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Habit 'Exercise' already exists" in response_text
            assert parse_mode == 'MarkdownV2'

    # Habit Done Handler Tests

    @pytest.mark.asyncio
    async def test_habit_done_handler_no_args(self, test_session, mock_update, mock_context):
        """Test habit_done handler when no arguments are provided."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = []
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_done_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Missing habit name" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_habit_done_handler_habit_not_found(self, test_session, mock_update, mock_context):
        """Test habit_done handler when habit doesn't exist."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Nonexistent"]
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_done_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Habit 'Nonexistent' not found" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_habit_done_handler_success_first_time(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_done handler when marking habit done for the first time."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        # Create a habit first
        db_habit_factory(name="Exercise")
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_done_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Habit completed for today" in response_text
            assert parse_mode == 'MarkdownV2'
            
            # Verify habit was updated
            repo = HabitRepository(test_session)
            updated_habit = repo.get_habit_by_name("Exercise")
            assert updated_habit.streak == 1
            assert updated_habit.last_completed == date.today()

    @pytest.mark.asyncio
    async def test_habit_done_handler_streak_increase(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_done handler when continuing a streak."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        # Create a habit and mark it done yesterday
        habit = db_habit_factory(name="Exercise")
        habit.last_completed = date.today() - timedelta(days=1)  # Yesterday
        habit.streak = 3
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_done_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Habit completed for today" in response_text
            assert parse_mode == 'MarkdownV2'
            
            # Verify streak increased
            repo = HabitRepository(test_session)
            updated_habit = repo.get_habit_by_name("Exercise")
            assert updated_habit.streak == 4
            assert updated_habit.last_completed == date.today()

    @pytest.mark.asyncio
    async def test_habit_done_handler_already_done_today(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_done handler when habit was already completed today."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        # Create a habit and mark it done today
        habit = db_habit_factory(name="Exercise")
        habit.last_completed = date.today()
        habit.streak = 5
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_done_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Habit completed for today" in response_text
            assert parse_mode == 'MarkdownV2'
            
            # Verify streak remains the same
            repo = HabitRepository(test_session)
            updated_habit = repo.get_habit_by_name("Exercise")
            assert updated_habit.streak == 5  # Should not increase

    @pytest.mark.asyncio
    async def test_habit_done_handler_milestone_7_days(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_done handler when reaching 7-day milestone."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        # Create a habit with 6-day streak
        habit = db_habit_factory(name="Exercise")
        habit.last_completed = date.today() - timedelta(days=1)
        habit.streak = 6
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_done_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "7-day streak milestone" in response_text
            assert "🔥" in response_text  # Streak emoji for 7+ days

    @pytest.mark.asyncio
    async def test_habit_done_handler_milestone_30_days(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_done handler when reaching 30-day milestone."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        # Create a habit with 29-day streak
        habit = db_habit_factory(name="Exercise")
        habit.last_completed = date.today() - timedelta(days=1)
        habit.streak = 29
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_done_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "30-day streak milestone" in response_text

    @pytest.mark.asyncio
    async def test_habit_done_handler_milestone_100_days(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_done handler when reaching 100-day milestone."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        # Create a habit with 99-day streak
        habit = db_habit_factory(name="Exercise")
        habit.last_completed = date.today() - timedelta(days=1)
        habit.streak = 99
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_done_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "100-day streak milestone" in response_text

    # Habit List Handler Tests

    @pytest.mark.asyncio
    async def test_habit_list_handler_no_habits(self, test_session, mock_update, mock_context):
        """Test habit_list handler when no habits exist."""
        mock_update.message.reply_text = AsyncMock()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_list_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "No habits found" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_habit_list_handler_with_habits(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_list handler with existing habits."""
        mock_update.message.reply_text = AsyncMock()
        
        # Create multiple habits
        habit1 = db_habit_factory(name="Exercise")
        habit2 = db_habit_factory(name="Read")
        habit3 = db_habit_factory(name="Meditate")
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_list_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            reply_markup = call_args[1].get('reply_markup')
            
            assert "All Habits" in response_text
            assert "Exercise" in response_text
            assert "Read" in response_text
            assert "Meditate" in response_text
            assert parse_mode == 'MarkdownV2'
            assert reply_markup is not None

    @pytest.mark.asyncio
    async def test_habit_list_handler_completed_today(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_list handler with habit completed today."""
        mock_update.message.reply_text = AsyncMock()
        
        # Create habit completed today
        habit = db_habit_factory(name="Exercise")
        habit.last_completed = datetime.now().date()  # Use date, not datetime
        habit.streak = 5
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_list_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "✅" in response_text  # Completed today emoji
            assert "Completed today" in response_text

    @pytest.mark.asyncio
    async def test_habit_list_handler_missed_yesterday(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_list handler with habit missed yesterday."""
        mock_update.message.reply_text = AsyncMock()
        
        # Create habit completed yesterday
        habit = db_habit_factory(name="Exercise")
        habit.last_completed = datetime.now().date() - timedelta(days=1)  # Use date, not datetime
        habit.streak = 5
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_list_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "⚠️" in response_text  # Missed yesterday emoji
            assert "Missed yesterday" in response_text

    @pytest.mark.asyncio
    async def test_habit_list_handler_missed_multiple_days(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_list handler with habit missed multiple days."""
        mock_update.message.reply_text = AsyncMock()
        
        # Create habit completed 3 days ago
        habit = db_habit_factory(name="Exercise")
        habit.last_completed = datetime.now().date() - timedelta(days=3)  # Use date, not datetime
        habit.streak = 5
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_list_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "❌" in response_text  # Missed multiple days emoji
            assert "Missed 3 days" in response_text

    # Habit Delete Handler Tests

    @pytest.mark.asyncio
    async def test_habit_delete_handler_no_args(self, test_session, mock_update, mock_context):
        """Test habit_delete handler when no arguments are provided."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = []
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_delete_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Missing habit name" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_habit_delete_handler_habit_not_found(self, test_session, mock_update, mock_context):
        """Test habit_delete handler when habit doesn't exist."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Nonexistent"]
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_delete_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Habit 'Nonexistent' not found" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_habit_delete_handler_success(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_delete handler with valid habit."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        # Create a habit first
        habit = db_habit_factory(name="Exercise")
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_delete_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            reply_markup = call_args[1].get('reply_markup')
            
            assert "Confirm Habit Deletion" in response_text
            assert "Exercise" in response_text
            assert parse_mode == 'MarkdownV2'
            assert reply_markup is not None

    # Habit Progress Handler Tests

    @pytest.mark.asyncio
    async def test_habit_progress_handler_no_args(self, test_session, mock_update, mock_context):
        """Test habit_progress handler when no arguments are provided."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = []
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_progress_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Missing habit name" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_habit_progress_handler_habit_not_found(self, test_session, mock_update, mock_context):
        """Test habit_progress handler when habit doesn't exist."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Nonexistent"]
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_progress_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Habit 'Nonexistent' not found" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_habit_progress_handler_success(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_progress handler with valid habit."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        # Create a habit with some progress
        habit = db_habit_factory(name="Exercise")
        habit.created_at = datetime.now() - timedelta(days=10)
        habit.streak = 7
        habit.last_completed = datetime.now().date()  # Use date, not datetime
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_progress_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            reply_markup = call_args[1].get('reply_markup')
            
            assert "Habit Progress Report" in response_text
            assert "Exercise" in response_text
            assert "**Current Streak**: 7 days" in response_text
            assert "Progress Bar" in response_text
            assert parse_mode == 'MarkdownV2'
            assert reply_markup is not None

    @pytest.mark.asyncio
    async def test_habit_progress_handler_milestone_calculation(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_progress handler milestone calculations."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        # Create a habit with 5-day streak (next milestone should be 7)
        habit = db_habit_factory(name="Exercise")
        habit.created_at = datetime.now() - timedelta(days=10)
        habit.streak = 5
        habit.last_completed = datetime.now().date()  # Use date, not datetime
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_progress_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "Next Milestone" in response_text
            assert "Target: 7 days" in response_text
            assert "Days needed: 2" in response_text

    # Habit Stats Handler Tests

    @pytest.mark.asyncio
    async def test_habit_stats_handler_no_habits(self, test_session, mock_update, mock_context):
        """Test habit_stats handler when no habits exist."""
        mock_update.message.reply_text = AsyncMock()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_stats_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "No habits to analyze" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_habit_stats_handler_with_habits(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_stats handler with existing habits."""
        mock_update.message.reply_text = AsyncMock()
        
        # Create multiple habits with different streaks
        habit1 = db_habit_factory(name="Exercise")
        habit1.streak = 10
        habit1.last_completed = date.today()
        
        habit2 = db_habit_factory(name="Read")
        habit2.streak = 5
        habit2.last_completed = date.today() - timedelta(days=1)
        
        habit3 = db_habit_factory(name="Meditate")
        habit3.streak = 0
        habit3.last_completed = None
        
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_stats_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            parse_mode = call_args[1].get('parse_mode')
            
            assert "Habit Statistics Report" in response_text
            assert "Total Habits: 3" in response_text
            assert "Active Habits: 2" in response_text
            assert "Average Streak: 5.0 days" in response_text
            assert "Top Performers" in response_text
            assert "Exercise" in response_text
            assert "Read" in response_text
            assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_habit_stats_handler_insights(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_stats handler insights and recommendations."""
        mock_update.message.reply_text = AsyncMock()
        
        # Create habits for different insight scenarios
        habit1 = db_habit_factory(name="Exercise")
        habit1.streak = 30  # High streak for best habit insight
        
        habit2 = db_habit_factory(name="Read")
        habit2.streak = 1  # Low streak for low average insight
        
        habit3 = db_habit_factory(name="Meditate")
        habit3.streak = 0  # Inactive habit for inactive insight
        
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_stats_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "Insights" in response_text
            assert "Best Habit" in response_text
            assert "Excellent consistency" in response_text
            assert "inactive habits" in response_text

    # Edge Cases and Error Scenarios

    @pytest.mark.asyncio
    async def test_habit_add_handler_special_characters(self, test_session, mock_update, mock_context):
        """Test habit_add handler with special characters in name."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise & Fitness!"]
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_add_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "Exercise & Fitness" in response_text
            assert "created successfully" in response_text

    @pytest.mark.asyncio
    async def test_habit_done_handler_streak_reset(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_done handler when streak should reset (missed more than 1 day)."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        # Create a habit completed 3 days ago
        habit = db_habit_factory(name="Exercise")
        habit.last_completed = date.today() - timedelta(days=3)
        habit.streak = 5
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_done_handler(mock_update, mock_context)
            
            # Verify streak was reset to 1
            repo = HabitRepository(test_session)
            updated_habit = repo.get_habit_by_name("Exercise")
            assert updated_habit.streak == 1  # Should reset to 1

    @pytest.mark.asyncio
    async def test_habit_progress_handler_zero_days_tracked(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_progress handler with habit created today."""
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["Exercise"]
        
        # Create a habit created today
        habit = db_habit_factory(name="Exercise")
        habit.created_at = datetime.now()
        habit.streak = 0
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_progress_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "**Days Tracked**: 1 days" in response_text
            assert "**Completion Rate**: 0.0%" in response_text

    @pytest.mark.asyncio
    async def test_habit_stats_handler_single_habit(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_stats handler with only one habit."""
        mock_update.message.reply_text = AsyncMock()
        
        # Create single habit
        habit = db_habit_factory(name="Exercise")
        habit.streak = 7
        habit.last_completed = date.today()
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_stats_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "Total Habits: 1" in response_text
            assert "Active Habits: 1" in response_text
            assert "Average Streak: 7.0 days" in response_text
            assert "Top Performers" in response_text
            assert "Exercise" in response_text

    # Performance and Large Dataset Tests

    @pytest.mark.asyncio
    async def test_habit_list_handler_many_habits(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_list handler with many habits."""
        mock_update.message.reply_text = AsyncMock()
        
        # Create 10 habits
        for i in range(10):
            db_habit_factory(name=f"Habit {i+1}")
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_list_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "All Habits" in response_text
            assert "10 found" in response_text
            assert "Habit 1" in response_text
            assert "Habit 10" in response_text

    @pytest.mark.asyncio
    async def test_habit_stats_handler_many_habits(self, test_session, mock_update, mock_context, db_habit_factory):
        """Test habit_stats handler with many habits."""
        mock_update.message.reply_text = AsyncMock()
        
        # Create 20 habits with varying streaks
        for i in range(20):
            habit = db_habit_factory(name=f"Habit {i+1}")
            habit.streak = i + 1  # Streaks from 1 to 20
            habit.last_completed = date.today() - timedelta(days=i % 3)
        
        test_session.commit()
        
        with patch("larrybot.plugins.habit.get_session", return_value=iter([test_session])):
            await habit_stats_handler(mock_update, mock_context)
            
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]
            
            assert "Total Habits: 20" in response_text
            assert "Active Habits: 20" in response_text
            assert "Average Streak: 10.5 days" in response_text
            assert "Top Performers" in response_text 