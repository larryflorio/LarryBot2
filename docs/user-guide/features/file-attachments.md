---
title: File Attachments
description: Attach files to tasks for better project management
last_updated: 2025-06-28
---

# File Attachments 📎

> **Breadcrumbs:** [Home](../../README.md) > [User Guide](../README.md) > [Features](README.md) > File Attachments

LarryBot2 supports file attachments for tasks, allowing you to store documents, images, and other files directly with your tasks for better project management and organization.

## 🚀 Overview

File attachments enable you to:
- **Store project documents** (PDFs, Word docs, etc.)
- **Attach design mockups** (images, screenshots)
- **Keep reference materials** (text files, spreadsheets)
- **Organize project assets** (archives, compressed files)

## 📋 Supported File Types

### Documents
- **PDF** (`.pdf`) - Portable Document Format
- **Word Documents** (`.doc`, `.docx`) - Microsoft Word files
- **Text Files** (`.txt`) - Plain text documents

### Images
- **JPEG** (`.jpg`, `.jpeg`) - Photographic images
- **PNG** (`.png`) - Graphics and screenshots
- **GIF** (`.gif`) - Animated images

### Archives
- **ZIP** (`.zip`) - Compressed archives
- **RAR** (`.rar`) - WinRAR archives

## 📏 File Size Limits

- **Maximum file size**: 10MB per file
- **Storage**: Files are stored locally on the server
- **Security**: Files are stored with hash-based naming for security

## 🎯 Commands

### `/attach` - Attach File to Task
Attach a file to a specific task.

**Usage**: `/attach <task_id> [description]`

**Steps**:
1. Send a file (document, image, etc.) to the bot
2. Reply with: `/attach <task_id> [description]`

**Examples**:
```
/attach 123
/attach 124 "Project requirements document"
/attach 125 "Design mockup v2"
```

**Response**:
```
✅ File attached successfully!

📎 File: project_requirements.pdf
📋 Task: #124
📏 Size: 2,456 bytes
📄 Type: application/pdf
🆔 Attachment ID: 5
```

### `/attachments` - List Task Attachments
View all attachments for a specific task.

**Usage**: `/attachments <task_id>`

**Examples**:
```
/attachments 123
/attachments 124
```

**Response**:
```
📎 Attachments for Task #124

📊 Summary: 3 files, 15,234 bytes

🆔 ID: 5
📄 File: project_requirements.pdf
📏 Size: 2,456 bytes
📅 Added: 2025-06-28 11:15:00
📝 Description: Project requirements document

🆔 ID: 6
📄 File: design_mockup.png
📏 Size: 8,456 bytes
📅 Added: 2025-06-28 11:20:00

🆔 ID: 7
📄 File: meeting_notes.txt
📏 Size: 4,322 bytes
📅 Added: 2025-06-28 11:25:00
📝 Description: Team meeting discussion points
```

### `/remove_attachment` - Remove Attachment
Delete an attachment from a task.

**Usage**: `/remove_attachment <attachment_id>`

**Examples**:
```
/remove_attachment 5
/remove_attachment 6
```

**Response**:
```
🗑️ Attachment removed successfully!

📄 File: project_requirements.pdf
🆔 ID: 5
```

### `/attachment_description` - Update Attachment Description
Update the description of an attachment.

**Usage**: `/attachment_description <attachment_id> <description>`

**Examples**:
```
/attachment_description 5 "Updated project requirements v2"
/attachment_description 6 "Final design mockup"
```

**Response**:
```
✅ Description updated successfully!

📄 File: project_requirements.pdf
📝 Description: Updated project requirements v2
🆔 ID: 5
```

## 🔧 Technical Details

### File Storage
- Files are stored in a configurable local directory
- Each file is renamed using an MD5 hash for security
- Original filenames are preserved in the database
- File paths are stored for efficient retrieval

### Security Features
- **Hash-based naming**: Prevents filename conflicts and improves security
- **File type validation**: Only allowed file types can be uploaded
- **Size limits**: Prevents storage abuse
- **Access control**: Files are associated with specific tasks

### Database Schema
```sql
CREATE TABLE task_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_url VARCHAR(500),
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

## 📊 Best Practices

### File Organization
- **Use descriptive filenames**: Make it easy to identify files
- **Add descriptions**: Provide context for each attachment
- **Group related files**: Attach multiple files to the same task
- **Regular cleanup**: Remove outdated attachments

### File Management
- **Backup important files**: Don't rely solely on attachments for critical documents
- **Monitor storage**: Keep track of attachment sizes
- **Use appropriate formats**: Choose the right file type for your content
- **Compress when possible**: Reduce file sizes for better performance

### Security Considerations
- **Validate file contents**: Ensure files are what they claim to be
- **Limit access**: Only share attachments with authorized users
- **Regular audits**: Review and clean up old attachments
- **Backup strategy**: Implement proper backup procedures

## 🚨 Troubleshooting

### Common Issues

**File too large**
```
❌ Error: File too large. Maximum size: 10MB
```
**Solution**: Compress the file or split it into smaller parts.

**Unsupported file type**
```
❌ Error: File type not allowed: .exe. Allowed: .pdf, .doc, .docx, .txt, .jpg, .jpeg, .png, .gif, .zip, .rar
```
**Solution**: Convert the file to a supported format.

**Task not found**
```
❌ Error: Task 999 not found
```
**Solution**: Verify the task ID exists using `/list`.

**Attachment not found**
```
❌ Error: Attachment 999 not found
```
**Solution**: Use `/attachments <task_id>` to see available attachments.

### Performance Tips
- **Optimize images**: Compress images before uploading
- **Use appropriate formats**: Choose efficient file formats
- **Regular cleanup**: Remove unused attachments
- **Monitor storage**: Keep track of total attachment size

## 🔄 Integration

### Event System
File attachment operations emit events for integration:
- `file_attached` - When a file is successfully attached
- `file_removed` - When a file is removed
- `file_updated` - When file description is updated

### API Access
File attachments are accessible through the service layer:
```python
from larrybot.services.task_attachment_service import TaskAttachmentService

# Attach a file
result = await service.attach_file(task_id, file_data, filename)

# Get attachments
attachments = await service.get_task_attachments(task_id)

# Remove attachment
await service.remove_attachment(attachment_id)
```

## 📈 Future Enhancements

### Planned Features
- **Cloud storage integration**: Support for external storage providers
- **File preview**: Inline preview of common file types
- **Version control**: Track file versions and changes
- **Sharing**: Share attachments with external users
- **Search**: Full-text search within file contents
- **OCR**: Extract text from images and PDFs

### Roadmap
- **Q3 2025**: Cloud storage integration
- **Q4 2025**: File preview and search
- **Q1 2026**: Version control and sharing
- **Q2 2026**: OCR and advanced features 