import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from larrybot.plugins import file_attachments

@pytest.mark.asyncio
async def test_attach_file_handler_no_file():
    update = MagicMock()
    update.message.document = None
    update.message.photo = None
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["1"]
    await file_attachments.attach_file_handler(update, context)
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    response_text = call_args[0][0]
    parse_mode = call_args[1].get('parse_mode')
    assert "Please attach a file" in response_text
    assert parse_mode == 'MarkdownV2'

@pytest.mark.asyncio
async def test_attach_file_handler_invalid_args():
    update = MagicMock()
    update.message.document = MagicMock()
    update.message.photo = None
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []
    await file_attachments.attach_file_handler(update, context)
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    response_text = call_args[0][0]
    parse_mode = call_args[1].get('parse_mode')
    assert "❌ This command requires at least 1 argument(s)." in response_text

@pytest.mark.asyncio
@patch("larrybot.plugins.file_attachments._get_attachment_service")
@patch("larrybot.plugins.file_attachments._extract_file_data")
async def test_attach_file_handler_success(mock_extract, mock_service):
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
    await file_attachments.attach_file_handler(update, context)
    update.message.reply_text.assert_called()
    call_args = update.message.reply_text.call_args
    response_text = call_args[0][0]
    parse_mode = call_args[1].get('parse_mode')
    assert "✅ **Success**" in response_text
    assert "File attached successfully" in response_text
    assert parse_mode == 'MarkdownV2'

@pytest.mark.asyncio
@patch("larrybot.plugins.file_attachments._get_attachment_service")
async def test_list_attachments_handler_success(mock_service):
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
    response_text = call_args[0][0]
    parse_mode = call_args[1].get('parse_mode')
    assert "📎 **Attachments for Task #1**" in response_text
    assert parse_mode == 'MarkdownV2'

@pytest.mark.asyncio
@patch("larrybot.plugins.file_attachments._get_attachment_service")
async def test_remove_attachment_handler_success(mock_service):
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
    response_text = call_args[0][0]
    parse_mode = call_args[1].get('parse_mode')
    assert "✅ **Success**" in response_text
    assert "Attachment removed successfully" in response_text
    assert parse_mode == 'MarkdownV2'

@pytest.mark.asyncio
@patch("larrybot.plugins.file_attachments._get_attachment_service")
async def test_update_description_handler_success(mock_service):
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
    response_text = call_args[0][0]
    parse_mode = call_args[1].get('parse_mode')
    assert "✅ **Success**" in response_text
    assert "Description updated successfully" in response_text
    assert parse_mode == 'MarkdownV2' 