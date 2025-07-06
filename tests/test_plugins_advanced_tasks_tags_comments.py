"""
Tests for the Advanced Tasks Tags and Comments module.

This module tests the tags and comments functionality including:
- Tag management
- Comment management
"""

import pytest
from unittest.mock import Mock, AsyncMock
from larrybot.plugins.advanced_tasks.tags_comments import (
    _tags_handler_internal,
    _comment_handler_internal,
    register
)


class TestAdvancedTasksTagsComments:
    """Test cases for the Advanced Tasks Tags and Comments module."""

    @pytest.fixture
    def mock_event_bus(self):
        return Mock()

    @pytest.fixture
    def mock_command_registry(self):
        return Mock()

    @pytest.fixture
    def mock_update(self):
        update = Mock()
        update.message.reply_text = AsyncMock()
        update.effective_user.id = 12345
        return update

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.args = []
        return context

    @pytest.fixture
    def mock_task_service(self):
        service = Mock()
        service.add_tag = AsyncMock()
        service.remove_tag = AsyncMock()
        service.add_comment = AsyncMock()
        return service

    def test_register_tags_comments_commands(self, mock_event_bus, mock_command_registry):
        """Test tags and comments module registration with command registry."""
        # Act
        register(mock_event_bus, mock_command_registry)

        # Assert
        assert mock_command_registry.register.call_count == 3  # 3 tags/comments commands
        registered_commands = [call[0][0] for call in mock_command_registry.register.call_args_list]
        assert "/tags" in registered_commands
        assert "/comment" in registered_commands
        assert "/comments" in registered_commands

    @pytest.mark.asyncio
    async def test_tag_handler_add_success(self, mock_update, mock_context, mock_task_service):
        """Test successful tag addition."""
        # Arrange
        mock_context.args = ["1", "add", "urgent"]
        mock_task_service.add_tags = AsyncMock(return_value={
            'success': True,
            'message': 'Tag added successfully'
        })
        
        # Act
        await _tags_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.add_tags.assert_called_once_with(1, ['urgent'], 'add')
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Tag added successfully" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_tag_handler_remove_success(self, mock_update, mock_context, mock_task_service):
        """Test successful tag removal."""
        # Arrange
        mock_context.args = ["1", "remove", "urgent"]
        mock_task_service.add_tags = AsyncMock(return_value={
            'success': True,
            'message': 'Tag removed successfully'
        })
        
        # Act
        await _tags_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.add_tags.assert_called_once_with(1, ['urgent'], 'remove')
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Tag removed successfully" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_tag_handler_invalid_task_id(self, mock_update, mock_context, mock_task_service):
        """Test tag operation with invalid task ID."""
        # Arrange
        mock_context.args = ["invalid", "add", "urgent"]
        
        # Act
        await _tags_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_tag_handler_invalid_operation(self, mock_update, mock_context, mock_task_service):
        """Test tag operation with invalid operation."""
        # Arrange
        mock_context.args = ["1", "invalid", "urgent"]
        
        # Act
        await _tags_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Invalid action" in response_text or "Invalid operation" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_tag_handler_missing_tag(self, mock_update, mock_context, mock_task_service):
        """Test tag operation with missing tag."""
        # Arrange: Provide three args, but the third is empty to simulate missing tag
        mock_context.args = ["1", "add", ""]
        
        # Act
        await _tags_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "No tags provided" in response_text or "Tag name is required" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_tag_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test tag operation when service returns error."""
        # Arrange
        mock_context.args = ["1", "add", "urgent"]
        mock_task_service.add_tags = AsyncMock(return_value={
            'success': False,
            'message': 'Task not found'
        })
        
        # Act
        await _tags_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task not found" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_comment_handler_success(self, mock_update, mock_context, mock_task_service):
        """Test successful comment addition."""
        # Arrange
        mock_context.args = ["1", "This is a test comment"]
        mock_task_service.add_comment = AsyncMock(return_value={
            'success': True,
            'message': 'Comment added successfully',
            'data': {'id': 42, 'content': 'This is a test comment'}
        })
        
        # Act
        await _comment_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.add_comment.assert_called_once_with(1, "This is a test comment")
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Comment added successfully" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_comment_handler_invalid_task_id(self, mock_update, mock_context, mock_task_service):
        """Test comment addition with invalid task ID."""
        # Arrange
        mock_context.args = ["invalid", "This is a test comment"]
        
        # Act
        await _comment_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task ID must be a number" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_comment_handler_missing_comment(self, mock_update, mock_context, mock_task_service):
        """Test comment operation with missing comment."""
        # Arrange: Provide two args, but the second is empty to simulate missing comment
        mock_context.args = ["1", ""]
        
        # Act
        await _comment_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Comment" in response_text or "required" in response_text or "Usage" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_comment_handler_service_error(self, mock_update, mock_context, mock_task_service):
        """Test comment addition when service returns error."""
        # Arrange
        mock_context.args = ["1", "This is a test comment"]
        mock_task_service.add_comment.return_value = {
            'success': False,
            'message': 'Task not found'
        }
        
        # Act
        await _comment_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Task not found" in response_text
        assert parse_mode == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_comment_handler_long_comment(self, mock_update, mock_context, mock_task_service):
        """Test comment operation with a long comment."""
        # Arrange
        long_comment = "A" * 100
        mock_context.args = ["1", long_comment]
        mock_task_service.add_comment = AsyncMock(return_value={
            'success': True,
            'message': 'Comment added successfully',
            'data': {'id': 99, 'content': long_comment}
        })
        
        # Act
        await _comment_handler_internal(mock_update, mock_context, mock_task_service)
        
        # Assert
        mock_task_service.add_comment.assert_called_once_with(1, long_comment)
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        parse_mode = call_args[1].get('parse_mode')
        
        assert "Comment added successfully" in response_text
        assert parse_mode == 'MarkdownV2' 