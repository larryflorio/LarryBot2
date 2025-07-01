"""
Comprehensive file attachments plugin testing with edge cases and error scenarios.

This test suite targets the coverage gap in larrybot/plugins/file_attachments.py
to achieve 80%+ coverage through comprehensive testing of all attachment functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from larrybot.plugins import file_attachments

class TestFileAttachmentsPluginComprehensive:
    """Comprehensive file attachments plugin testing with edge cases."""

    @pytest.mark.asyncio
    async def test_attach_file_handler_no_file(self):
        update = MagicMock()
        update.message.document = None
        update.message.photo = None
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1"]
        await file_attachments.attach_file_handler(update, context)
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert "Please attach a file" in call_args[0][0]
        assert call_args[1].get('parse_mode') == 'MarkdownV2'

    @pytest.mark.asyncio
    async def test_attach_file_handler_invalid_args(self):
        update = MagicMock()
        update.message.document = MagicMock()
        update.message.photo = None
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = []
        await file_attachments.attach_file_handler(update, context)
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert "requires at least 1 argument" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    @patch("larrybot.plugins.file_attachments._extract_file_data")
    async def test_attach_file_handler_success(self, mock_extract, mock_service):
        update = MagicMock()
        update.message.document = MagicMock()
        update.message.photo = None
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1", "desc"]
        mock_extract.return_value = (b"data", "file.txt")
        mock_service.return_value.attach_file = AsyncMock(return_value={
            "success": True,
            "data": {"id": 1, "filename": "file.txt", "size": 10, "mime_type": "text/plain"}
        })
        with patch("larrybot.plugins.file_attachments.emit_task_event") as mock_emit:
            await file_attachments.attach_file_handler(update, context)
            update.message.reply_text.assert_called()
            call_args = update.message.reply_text.call_args
            assert "File attached successfully" in call_args[0][0]
            assert call_args[1].get('parse_mode') == 'MarkdownV2'
            mock_emit.assert_called_once()

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    @patch("larrybot.plugins.file_attachments._extract_file_data")
    async def test_attach_file_handler_service_error(self, mock_extract, mock_service):
        update = MagicMock()
        update.message.document = MagicMock()
        update.message.photo = None
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1"]
        mock_extract.return_value = (b"data", "file.txt")
        mock_service.return_value.attach_file = AsyncMock(return_value={
            "success": False,
            "error": "Attachment failed"
        })
        await file_attachments.attach_file_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Attachment failed" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_list_attachments_handler_success(self, mock_service):
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1"]
        mock_service.return_value.get_task_attachments = AsyncMock(return_value={
            "success": True,
            "data": {
                "attachments": [
                    {
                        "id": 1,
                        "filename": "file.txt",
                        "size": 10,
                        "mime_type": "text/plain",
                        "description": "desc",
                        "created_at": "2025-06-28T12:00:00",
                        "is_public": False
                    }
                ],
                "stats": {
                    "count": 1,
                    "total_size": 10,
                    "total_size_mb": 0.01,
                    "avg_size": 10,
                    "type_distribution": {"text/plain": 1}
                }
            }
        })
        await file_attachments.list_attachments_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "📎 **Attachments for Task #1**" in call_args[0][0]
        assert call_args[1].get('parse_mode') == 'MarkdownV2'

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_list_attachments_handler_no_attachments(self, mock_service):
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1"]
        mock_service.return_value.get_task_attachments = AsyncMock(return_value={
            "success": True,
            "data": {
                "attachments": [],
                "stats": {"count": 0, "total_size": 0, "total_size_mb": 0.0, "avg_size": 0, "type_distribution": {}}
            }
        })
        await file_attachments.list_attachments_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "No Attachments Found" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_list_attachments_handler_invalid_task_id(self, mock_service):
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["bad"]
        await file_attachments.list_attachments_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Invalid task ID" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_remove_attachment_handler_success(self, mock_service):
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1"]
        mock_service.return_value.remove_attachment = AsyncMock(return_value={
            "success": True,
            "data": {"filename": "file.txt", "size": 10}
        })
        await file_attachments.remove_attachment_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Attachment removed successfully" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_remove_attachment_handler_error(self, mock_service):
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1"]
        mock_service.return_value.remove_attachment = AsyncMock(return_value={
            "success": False,
            "error": "Not found"
        })
        await file_attachments.remove_attachment_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Not found" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_update_description_handler_success(self, mock_service):
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1", "desc"]
        mock_service.return_value.update_attachment_description = AsyncMock(return_value={
            "success": True,
            "data": {"filename": "file.txt", "description": "desc"}
        })
        await file_attachments.update_description_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Description updated successfully" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_update_description_handler_error(self, mock_service):
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1", "desc"]
        mock_service.return_value.update_attachment_description = AsyncMock(return_value={
            "success": False,
            "error": "Update failed"
        })
        await file_attachments.update_description_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Update failed" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_attachment_stats_handler_success_all_tasks(self, mock_service):
        """Test attachment_stats_handler for all tasks."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = []
        mock_service.return_value.get_attachment_statistics = AsyncMock(return_value={
            "success": True,
            "data": {
                "total_attachments": 5,
                "total_size": 1000,
                "total_size_mb": 0.001,
                "avg_size": 200,
                "largest_file_size": 500,
                "type_distribution": {"pdf": 2, "jpg": 3},
                "size_distribution": {"< 1MB": 4, "1-5MB": 1},
                "recent_activity": [
                    {"action": "Added", "filename": "file1.pdf", "date": "2025-06-28"}
                ]
            }
        })
        await file_attachments.attachment_stats_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        response_text = call_args[0][0]
        assert "📊 **Attachment Statistics**" in response_text
        assert "All Tasks" in response_text
        assert "Total Attachments: 5" in response_text
        assert call_args[1].get('parse_mode') == 'MarkdownV2'

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_attachment_stats_handler_success_specific_task(self, mock_service):
        """Test attachment_stats_handler for specific task."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1"]
        mock_service.return_value.get_attachment_statistics = AsyncMock(return_value={
            "success": True,
            "data": {
                "total_attachments": 2,
                "total_size": 500,
                "total_size_mb": 0.0005,
                "avg_size": 250,
                "largest_file_size": 300,
                "type_distribution": {"pdf": 1, "jpg": 1}
            }
        })
        await file_attachments.attachment_stats_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        response_text = call_args[0][0]
        assert "Task #1" in response_text
        assert "Total Attachments: 2" in response_text

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_attachment_stats_handler_invalid_task_id(self, mock_service):
        """Test attachment_stats_handler with invalid task ID."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["invalid"]
        
        # Mock service to return success for all tasks when task_id is None
        mock_service.return_value.get_attachment_statistics = AsyncMock(return_value={
            "success": True,
            "data": {
                "total_attachments": 0,
                "total_size": 0,
                "total_size_mb": 0.0,
                "avg_size": 0,
                "largest_file_size": 0
            }
        })
        
        await file_attachments.attachment_stats_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        response_text = call_args[0][0]
        assert "📊 **Attachment Statistics**" in response_text
        assert "All Tasks" in response_text  # Should default to all tasks when task_id is invalid

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_attachment_stats_handler_service_error(self, mock_service):
        """Test attachment_stats_handler when service returns error."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = []
        mock_service.return_value.get_attachment_statistics = AsyncMock(return_value={
            "success": False,
            "error": "Database error"
        })
        await file_attachments.attachment_stats_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Database error" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_extract_file_data_document(self):
        """Test _extract_file_data with document."""
        message = MagicMock()
        message.document = MagicMock()
        message.document.file_name = "test.pdf"
        message.photo = None
        
        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(return_value=b"file content")
        message.document.get_file = AsyncMock(return_value=mock_file)
        
        result = await file_attachments._extract_file_data(message)
        assert result[0] == b"file content"
        assert result[1] == "test.pdf"

    @pytest.mark.asyncio
    async def test_extract_file_data_photo(self):
        """Test _extract_file_data with photo."""
        message = MagicMock()
        message.document = None
        message.photo = [
            MagicMock(file_size=100, file_id="photo1"),
            MagicMock(file_size=200, file_id="photo2")  # Largest
        ]
        
        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(return_value=b"photo content")
        message.photo[1].get_file = AsyncMock(return_value=mock_file)
        
        result = await file_attachments._extract_file_data(message)
        assert result[0] == b"photo content"
        assert result[1] == "photo_photo2.jpg"

    @pytest.mark.asyncio
    async def test_extract_file_data_no_file(self):
        """Test _extract_file_data with no file."""
        message = MagicMock()
        message.document = None
        message.photo = None
        
        result = await file_attachments._extract_file_data(message)
        assert result[0] is None
        assert result[1] is None

    @pytest.mark.asyncio
    async def test_extract_file_data_exception(self):
        """Test _extract_file_data with exception."""
        message = MagicMock()
        message.document = MagicMock()
        message.document.get_file = AsyncMock(side_effect=Exception("Download failed"))
        message.photo = None
        
        result = await file_attachments._extract_file_data(message)
        assert result[0] is None
        assert result[1] is None

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    @patch("larrybot.plugins.file_attachments._extract_file_data")
    async def test_attach_file_handler_extract_failure(self, mock_extract, mock_service):
        """Test attach_file_handler when file extraction fails."""
        update = MagicMock()
        update.message.document = MagicMock()
        update.message.photo = None
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1"]
        mock_extract.return_value = (None, None)
        
        await file_attachments.attach_file_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Failed to extract file data" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_remove_attachment_handler_invalid_id(self, mock_service):
        """Test remove_attachment_handler with invalid attachment ID."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["invalid"]
        
        await file_attachments.remove_attachment_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Invalid attachment ID" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_update_description_handler_invalid_id(self, mock_service):
        """Test update_description_handler with invalid attachment ID."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["invalid", "description"]
        
        await file_attachments.update_description_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Invalid attachment ID" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_list_attachments_handler_service_error(self, mock_service):
        """Test list_attachments_handler when service returns error."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1"]
        mock_service.return_value.get_task_attachments = AsyncMock(return_value={
            "success": False,
            "error": "Task not found"
        })
        
        await file_attachments.list_attachments_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Task not found" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_list_attachments_handler_many_attachments(self, mock_service):
        """Test list_attachments_handler with many attachments (truncation)."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1"]
        
        # Create 10 attachments
        attachments = []
        for i in range(10):
            attachments.append({
                "id": i + 1,
                "filename": f"file{i+1}.txt",
                "size": 100,
                "mime_type": "text/plain",
                "description": f"Description {i+1}",
                "created_at": "2025-06-28T12:00:00",
                "is_public": False
            })
        
        mock_service.return_value.get_task_attachments = AsyncMock(return_value={
            "success": True,
            "data": {
                "attachments": attachments,
                "stats": {
                    "count": 10,
                    "total_size": 1000,
                    "total_size_mb": 0.001,
                    "avg_size": 100,
                    "type_distribution": {"text/plain": 10}
                }
            }
        })
        
        await file_attachments.list_attachments_handler(update, context)
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        response_text = call_args[0][0]
        assert "and 5 more files" in response_text  # Should show truncation message

    @pytest.mark.asyncio
    async def test_register_function(self):
        """Test register function sets up commands correctly."""
        event_bus = MagicMock()
        command_registry = MagicMock()
        
        file_attachments.register(event_bus, command_registry)
        
        # Verify commands were registered
        command_registry.register.assert_called()
        calls = command_registry.register.call_args_list
        
        # Check that all expected commands were registered
        registered_commands = [call[0][0] for call in calls]
        expected_commands = ["/attach", "/attachments", "/remove_attachment", 
                           "/attachment_description", "/attachment_stats"]
        
        for cmd in expected_commands:
            assert cmd in registered_commands

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    @patch("larrybot.plugins.file_attachments._extract_file_data")
    async def test_attach_file_handler_keyboard_generation(self, mock_extract, mock_service):
        """Test that attach_file_handler generates keyboard markup."""
        update = MagicMock()
        update.message.document = MagicMock()
        update.message.photo = None
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1"]
        mock_extract.return_value = (b"data", "file.txt")
        mock_service.return_value.attach_file = AsyncMock(return_value={
            "success": True,
            "data": {"id": 1, "filename": "file.txt", "size": 10, "mime_type": "text/plain"}
        })
        
        with patch("larrybot.plugins.file_attachments.emit_task_event"):
            await file_attachments.attach_file_handler(update, context)
            call_args = update.message.reply_text.call_args
            reply_markup = call_args[1].get('reply_markup')
            assert reply_markup is not None  # Should have keyboard

    @pytest.mark.asyncio
    @patch("larrybot.plugins.file_attachments._get_attachment_service")
    async def test_list_attachments_handler_keyboard_generation(self, mock_service):
        """Test that list_attachments_handler generates keyboard markup."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["1"]
        mock_service.return_value.get_task_attachments = AsyncMock(return_value={
            "success": True,
            "data": {
                "attachments": [{"id": 1, "filename": "file.txt", "size": 10, 
                               "mime_type": "text/plain", "description": "desc",
                               "created_at": "2025-06-28T12:00:00", "is_public": False}],
                "stats": {"count": 1, "total_size": 10, "total_size_mb": 0.01, 
                         "avg_size": 10, "type_distribution": {"text/plain": 1}}
            }
        })
        
        await file_attachments.list_attachments_handler(update, context)
        call_args = update.message.reply_text.call_args
        reply_markup = call_args[1].get('reply_markup')
        assert reply_markup is not None  # Should have keyboard 