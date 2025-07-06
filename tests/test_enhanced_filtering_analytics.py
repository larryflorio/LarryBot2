import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, AsyncMock
from larrybot.storage.task_repository import TaskRepository
from larrybot.services.task_service import TaskService
from larrybot.models.task import Task
from larrybot.plugins.advanced_tasks import (
    search_advanced_handler, filter_advanced_handler, tags_multi_handler,
    time_range_handler, priority_range_handler, analytics_handler,
    productivity_report_handler
)

class TestEnhancedFiltering:
    """Test enhanced filtering functionality."""

    def test_search_tasks_by_text_repository(self, test_session, db_task_factory):
        """Test text search at repository level."""
        repo = TaskRepository(test_session)
        
        # Create tasks with different content
        task1 = db_task_factory(description="Code review for authentication module")
        task2 = db_task_factory(description="Update documentation for API")
        task3 = db_task_factory(description="Fix authentication bug")
        
        # Add tags to tasks
        repo.add_tags(task1.id, ["code", "review"])
        repo.add_tags(task2.id, ["documentation", "api"])
        repo.add_tags(task3.id, ["bug", "authentication"])
        
        # Test search
        results = repo.search_tasks_by_text("authentication")
        assert len(results) == 2  # task1 and task3
        
        results = repo.search_tasks_by_text("code")
        assert len(results) == 1  # task1
        
        results = repo.search_tasks_by_text("nonexistent")
        assert len(results) == 0

    def test_advanced_filters_repository(self, test_session, db_task_factory):
        """Test advanced filtering at repository level."""
        repo = TaskRepository(test_session)
        
        # Create tasks with different attributes
        task1 = db_task_factory(description="Task 1", priority="High", category="Development")
        task2 = db_task_factory(description="Task 2", priority="Medium", category="Testing")
        task3 = db_task_factory(description="Task 3", priority="Low", category="Development")
        
        # Test filtering by multiple criteria
        results = repo.get_tasks_with_advanced_filters(
            priority="High",
            category="Development"
        )
        assert len(results) == 1
        assert results[0].id == task1.id
        
        # Test sorting
        results = repo.get_tasks_with_advanced_filters(
            sort_by="priority",
            sort_order="desc"
        )
        assert len(results) == 3
        # Should be sorted by priority: High, Medium, Low

    def test_multiple_tags_repository(self, test_session, db_task_factory):
        """Test multiple tag filtering at repository level."""
        repo = TaskRepository(test_session)
        
        # Create tasks with different tags
        task1 = db_task_factory(description="Task 1")
        task2 = db_task_factory(description="Task 2")
        task3 = db_task_factory(description="Task 3")
        
        repo.add_tags(task1.id, ["urgent", "bug"])
        repo.add_tags(task2.id, ["urgent", "feature"])
        repo.add_tags(task3.id, ["bug", "feature"])
        
        # Test "any" matching
        results = repo.get_tasks_by_multiple_tags(["urgent", "bug"], match_all=False)
        assert len(results) == 3  # All tasks match at least one tag
        
        # Test "all" matching
        results = repo.get_tasks_by_multiple_tags(["urgent", "bug"], match_all=True)
        assert len(results) == 1  # Only task1 has both tags

    def test_time_range_repository(self, test_session, db_task_factory):
        """Test time range filtering at repository level."""
        repo = TaskRepository(test_session)
        
        # Create tasks with different dates
        now = datetime.utcnow()
        task1 = db_task_factory(description="Task 1", due_date=now - timedelta(days=5))
        task2 = db_task_factory(description="Task 2", due_date=now + timedelta(days=5))
        task3 = db_task_factory(description="Task 3", due_date=now + timedelta(days=10))
        
        # Test time range
        start_date = now - timedelta(days=10)
        end_date = now + timedelta(days=10)
        results = repo.get_tasks_by_time_range(start_date, end_date)
        assert len(results) == 3
        
        # Test excluding completed
        repo.update_status(task1.id, "Done")
        results = repo.get_tasks_by_time_range(start_date, end_date, include_completed=False)
        assert len(results) == 2

    def test_priority_range_repository(self, test_session, db_task_factory):
        """Test priority range filtering at repository level."""
        repo = TaskRepository(test_session)
        
        # Create tasks with different priorities
        task1 = db_task_factory(description="Task 1", priority="Low")
        task2 = db_task_factory(description="Task 2", priority="Medium")
        task3 = db_task_factory(description="Task 3", priority="High")
        task4 = db_task_factory(description="Task 4", priority="Critical")
        
        # Test priority range
        results = repo.get_tasks_by_priority_range("Medium", "High")
        assert len(results) == 2  # Medium and High
        assert any(task.priority_enum.name.title() == "Medium" for task in results)
        assert any(task.priority_enum.name.title() == "High" for task in results)

class TestEnhancedAnalytics:
    """Test enhanced analytics functionality."""

    def test_advanced_analytics_repository(self, test_session, db_task_factory):
        """Test advanced analytics at repository level."""
        repo = TaskRepository(test_session)
        
        # Create tasks for analytics
        task1 = db_task_factory(description="Task 1", priority="High", category="Development")
        task2 = db_task_factory(description="Task 2", priority="Medium", category="Testing")
        task3 = db_task_factory(description="Task 3", priority="Low", category="Development")
        
        # Mark some as completed
        repo.update_status(task1.id, "Done")
        repo.update_status(task2.id, "Done")
        
        # Get analytics
        analytics = repo.get_advanced_task_analytics(days=30)
        
        assert analytics['overall_stats']['total_tasks'] == 3
        assert analytics['overall_stats']['completed_tasks'] == 2
        assert abs(analytics['overall_stats']['completion_rate'] - 66.7) < 0.1  # Allow for floating point precision
        
        # Check priority analysis
        priority_analysis = analytics['priority_analysis']
        assert priority_analysis['High']['completed'] == 1
        assert priority_analysis['Medium']['completed'] == 1
        assert priority_analysis['Low']['completed'] == 0

    def test_productivity_report_repository(self, test_session, db_task_factory):
        """Test productivity report at repository level."""
        repo = TaskRepository(test_session)
        
        # Create tasks in a specific time period
        now = datetime.utcnow()
        start_date = now - timedelta(days=7)
        end_date = now + timedelta(days=7)
        
        task1 = db_task_factory(description="Task 1")
        task2 = db_task_factory(description="Task 2")
        task3 = db_task_factory(description="Task 3")
        
        # Mark some as completed
        repo.update_status(task1.id, "Done")
        repo.update_status(task2.id, "Done")
        
        # Get productivity report
        report = repo.get_productivity_report(start_date, end_date)
        
        assert report['summary']['tasks_created'] == 3
        assert report['summary']['tasks_completed'] == 2
        assert abs(report['summary']['completion_rate'] - 66.7) < 0.1  # Allow for floating point precision

class TestEnhancedFilteringService:
    """Test enhanced filtering at service level."""

    @pytest.mark.asyncio
    async def test_search_tasks_by_text_service(self, test_session, db_task_factory):
        """Test text search at service level."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Create task with specific content
        task = db_task_factory(description="Authentication module needs review")
        
        # Test search
        result = await service.search_tasks_by_text("authentication")
        
        assert result['success'] is True
        assert len(result['data']) == 1
        assert result['data'][0]['id'] == task.id

    @pytest.mark.asyncio
    async def test_advanced_filters_service(self, test_session, db_task_factory):
        """Test advanced filtering at service level."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Create tasks
        task1 = db_task_factory(description="Task 1", priority="High")
        task2 = db_task_factory(description="Task 2", priority="Medium")
        
        # Test filtering
        result = await service.get_tasks_with_advanced_filters(
            priority="High",
            sort_by="created_at",
            sort_order="desc"
        )
        
        assert result['success'] is True
        assert len(result['data']) == 1
        assert result['data'][0]['priority'] == "High"

    @pytest.mark.asyncio
    async def test_multiple_tags_service(self, test_session, db_task_factory):
        """Test multiple tags at service level."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Create task with tags
        task = db_task_factory(description="Task 1")
        repo.add_tags(task.id, ["urgent", "bug"])
        
        # Test matching
        result = await service.get_tasks_by_multiple_tags(["urgent", "bug"], match_all=True)
        
        assert result['success'] is True
        assert len(result['data']) == 1

    @pytest.mark.asyncio
    async def test_advanced_analytics_service(self, test_session, db_task_factory):
        """Test advanced analytics at service level."""
        repo = TaskRepository(test_session)
        service = TaskService(repo)
        
        # Create some tasks
        task1 = db_task_factory(description="Task 1")
        task2 = db_task_factory(description="Task 2")
        repo.update_status(task1.id, "Done")
        
        # Test analytics
        result = await service.get_advanced_task_analytics(days=30)
        
        assert result['success'] is True
        analytics = result['data']
        assert analytics['overall_stats']['total_tasks'] == 2
        assert analytics['overall_stats']['completed_tasks'] == 1

class TestEnhancedFilteringCommands:
    """Test enhanced filtering at command level."""

    @pytest.mark.asyncio
    async def test_search_advanced_command_success(self, mock_update, mock_context, mock_task_service):
        """Test successful advanced search command."""
        # Arrange
        mock_context.args = ["authentication"]
        mock_task_service.search_tasks_by_text.return_value = {
            'success': True,
            'data': [
                {'id': 1, 'description': 'Fix authentication bug', 'priority': 'High', 'status': 'Todo', 'category': 'Development'}
            ],
            'message': 'Found 1 tasks matching authentication'
        }
        
        with patch('larrybot.plugins.advanced_tasks.get_task_service', return_value=mock_task_service):
            # Act
            await search_advanced_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.search_tasks_by_text.assert_called_once_with("authentication", case_sensitive=False)
            assert mock_update.message.reply_text.call_count == 2
            # First call: deprecation notice, second call: search results
            call_args = mock_update.message.reply_text.call_args_list[1][0][0]
            assert "Search Results" in call_args
            assert "Fix authentication bug" in call_args

    @pytest.mark.asyncio
    async def test_filter_advanced_command_success(self, mock_update, mock_context, mock_task_service):
        """Test successful advanced filter command."""
        # Arrange
        mock_context.args = ["Todo", "High", "Development"]
        mock_task_service.get_tasks_with_filters = AsyncMock(return_value={
            'success': True,
            'data': [
                {'id': 1, 'description': 'Task 1', 'priority': 'High', 'status': 'Todo', 'category': 'Development', 'due_date': None}
            ],
            'message': 'Found 1 tasks with advanced filters'
        })
        
        with patch('larrybot.plugins.advanced_tasks.get_task_service', return_value=mock_task_service):
            # Act
            await filter_advanced_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.get_tasks_with_filters.assert_called_once()
            assert mock_update.message.reply_text.call_count == 1  # Not deprecated, so only 1 message
            call_args = mock_update.message.reply_text.call_args_list[0][0][0]
            assert "Advanced Filter Results" in call_args
            assert "Task 1" in call_args

    @pytest.mark.asyncio
    async def test_tags_multi_command_success(self, mock_update, mock_context, mock_task_service):
        """Test successful multi-tag command."""
        # Arrange
        mock_context.args = ["urgent,bug", "all"]
        mock_task_service.get_tasks_with_filters = AsyncMock(return_value={
            'success': True,
            'data': [
                {'id': 1, 'description': 'Task 1', 'priority': 'High', 'status': 'Todo', 'tags': ['urgent', 'bug']}
            ],
            'message': 'Found 1 tasks matching all of tags: urgent, bug'
        })
        
        with patch('larrybot.plugins.advanced_tasks.get_task_service', return_value=mock_task_service):
            # Act
            await tags_multi_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.get_tasks_with_filters.assert_called_once_with({
                'tags': ['urgent', 'bug'], 
                'tag_match_type': 'all'
            })
            assert mock_update.message.reply_text.call_count == 1  # Not deprecated, so only 1 message
            call_args = mock_update.message.reply_text.call_args_list[0][0][0]
            assert "Multi-Tag Filter" in call_args
            assert "Task 1" in call_args

    @pytest.mark.asyncio
    async def test_tags_multi_command_error(self, mock_update, mock_context, mock_task_service):
        """Test multi-tag command with error."""
        # Arrange
        mock_context.args = ["invalid,format"]
        mock_task_service.get_tasks_with_filters = AsyncMock(return_value={
            'success': False,
            'message': 'Invalid tag format'
        })
        
        with patch('larrybot.plugins.advanced_tasks.get_task_service', return_value=mock_task_service):
            # Act
            await tags_multi_handler(mock_update, mock_context)
            
            # Assert
            assert mock_update.message.reply_text.call_count == 1  # Not deprecated, so only 1 message
            call_args = mock_update.message.reply_text.call_args_list[0][0][0]
            assert "❌ **Error**" in call_args or "No tags provided" in call_args or "Invalid tag format" in call_args

    @pytest.mark.asyncio
    async def test_analytics_advanced_command_success(self, mock_update, mock_context, mock_task_service):
        """Test successful advanced analytics command."""
        # Arrange
        mock_context.args = ["30"]
        mock_task_service.get_advanced_task_analytics = AsyncMock(return_value={
            'success': True,
            'data': {
                'overall_stats': {
                    'total_tasks': 10,
                    'completed_tasks': 7,
                    'incomplete_tasks': 3,
                    'overdue_tasks': 1,
                    'completion_rate': 70.0
                },
                'recent_activity': {
                    'tasks_created': 5,
                    'tasks_completed': 3,
                    'completion_rate': 60.0
                },
                'time_tracking': {
                    'total_hours': 25.5,
                    'entries_count': 15,
                    'avg_hours_per_task': 1.7
                }
            },
            'message': 'Advanced analytics for the last 30 days'
        })
        
        with patch('larrybot.plugins.advanced_tasks.get_task_service', return_value=mock_task_service):
            # Act
            await analytics_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.get_advanced_task_analytics.assert_called_once_with(30)
            assert mock_update.message.reply_text.call_count == 1  # Not deprecated, so only 1 message
            call_args = mock_update.message.reply_text.call_args_list[0][0][0]
            assert "Analytics" in call_args
            assert "overall\\_stats" in call_args

    @pytest.mark.asyncio
    async def test_productivity_report_command_success(self, mock_update, mock_context, mock_task_service):
        """Test successful productivity report command."""
        # Arrange
        mock_context.args = ["2025-01-01", "2025-01-31"]
        mock_task_service.get_productivity_report = AsyncMock(return_value={
            'success': True,
            'data': {
                'time_tracking': {
                    'total_hours': 120.5,
                    'avg_hours_per_day': 3.9,
                    'most_productive_day': 'Monday'
                },
                'completion_trends': {
                    'Week 1': 5,
                    'Week 2': 8,
                    'Week 3': 7,
                    'Week 4': 10
                },
                'performance_metrics': {
                    'efficiency': 85,
                    'accuracy': 92
                }
            },
            'message': 'Productivity report from 2025-01-01 to 2025-01-31'
        })
        
        with patch('larrybot.plugins.advanced_tasks.get_task_service', return_value=mock_task_service):
            # Act
            await productivity_report_handler(mock_update, mock_context)
            
            # Assert
            mock_task_service.get_productivity_report.assert_called_once()
            assert mock_update.message.reply_text.call_count == 1  # Not deprecated, so only 1 message
            call_args = mock_update.message.reply_text.call_args_list[0][0][0]
            assert "Productivity Report" in call_args
            assert "time\\_tracking" in call_args
            assert "completion\\_trends" in call_args 