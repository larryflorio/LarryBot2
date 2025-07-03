---
title: File Attachments
description: Attach files to tasks for better project management
last_updated: 2025-07-02
---

# File Attachments 📎

> **Breadcrumbs:** [Home](../../README.md) > [User Guide](../README.md) > [Features](README.md) > File Attachments

Keep all your project files organized by attaching them directly to tasks. Whether you're working on design projects, client deliverables, or personal projects, file attachments help you keep everything in one place.

## 🎯 What You Can Do

- **Attach project documents** (PDFs, Word docs, spreadsheets)
- **Store design files** (images, mockups, screenshots)
- **Keep reference materials** (text files, notes)
- **Organize project assets** (archives, compressed files)
- **Add descriptions** to files for better organization
- **Manage multiple files** per task

## 📋 Supported File Types

### Documents
- **PDF** (`.pdf`) - Reports, contracts, specifications
- **Word Documents** (`.doc`, `.docx`) - Proposals, documentation
- **Text Files** (`.txt`) - Notes, instructions, logs

### Images
- **JPEG** (`.jpg`, `.jpeg`) - Photos, screenshots
- **PNG** (`.png`) - Graphics, mockups, diagrams
- **GIF** (`.gif`) - Animated graphics, demos

### Archives
- **ZIP** (`.zip`) - Compressed project files
- **RAR** (`.rar`) - Compressed archives

## 📏 File Limits

- **Maximum file size**: 10MB per file
- **Storage**: Files are stored securely on your system
- **Security**: Files are protected with secure naming

## 📎 Attaching Files

### Basic File Attachment

Attach a file to a task:

1. **Send the file** to your bot (document, image, etc.)
2. **Reply with the command**:
   ```
   /attach 123
   ```

This attaches the file to task #123.

### Adding Descriptions

Include a description for better organization:

```
/attach 123 "Project requirements document"
/attach 124 "Design mockup v2"
/attach 125 "Client feedback notes"
```

### Multiple Files

You can attach multiple files to the same task:

1. Send first file → `/attach 123 "Requirements"`
2. Send second file → `/attach 123 "Design mockup"`
3. Send third file → `/attach 123 "Meeting notes"`

## 📋 Managing Attachments

### View Task Attachments

See all files attached to a task:

```
/attachments 123
```

This shows:
- **File names** and types
- **File sizes** and dates
- **Descriptions** (if added)
- **Attachment IDs** for management

### Update File Descriptions

Change the description of an attachment:

```
/attachment_description 5 "Updated project requirements v2"
/attachment_description 6 "Final design mockup"
```

### Remove Attachments

Delete files you no longer need:

```
/remove_attachment 5
/remove_attachment 6
```

## 🎯 Pro Tips

### File Organization

**Use descriptive names:**
```
/attach 123 "Q1_2025_Project_Requirements.pdf"
/attach 124 "Homepage_Design_Mockup_v2.png"
/attach 125 "Client_Meeting_Notes_2025-07-02.txt"
```

**Add helpful descriptions:**
```
/attach 123 "Project requirements document"
/attach 124 "Design mockup for homepage redesign"
/attach 125 "Meeting notes from client discussion"
```

### Project Management

**Organize by project phase:**
```
# Planning phase
/attach 123 "Requirements_Document.pdf"
/attach 123 "Project_Timeline.xlsx"

# Design phase
/attach 124 "Wireframes.png"
/attach 124 "Design_Specs.pdf"

# Development phase
/attach 125 "Code_Review_Notes.txt"
/attach 125 "Test_Results.pdf"
```

**Client project organization:**
```
/attach 123 "Client_Acme_Requirements.pdf"
/attach 123 "Acme_Project_Proposal.docx"
/attach 123 "Acme_Design_Mockups.zip"
```

### File Management

**Regular cleanup:**
- Remove outdated files
- Update descriptions as projects evolve
- Keep only relevant attachments

**Backup important files:**
- Don't rely solely on attachments for critical documents
- Keep local copies of important files
- Use attachments for convenience, not as primary storage

## 🆘 Getting Help

### File Attachment Help

```
/help attachments
```

Get help with file attachment commands.

### Common Issues

**File too large:**
- Compress the file if possible
- Split large files into smaller parts
- Use cloud storage for very large files

**File type not supported:**
- Convert to a supported format
- Use alternative file types
- Contact support for format requests

**Can't attach file:**
- Check file size (max 10MB)
- Verify file type is supported
- Try sending the file again

### Command Reference

**Attaching Files:**
- `/attach <task_id> [description]` - Attach file to task
- `/attachments <task_id>` - View task attachments
- `/attachment_description <id> <description>` - Update description
- `/remove_attachment <id>` - Remove attachment

## 🎯 Common Use Cases

### Design Projects

**Store design assets:**
```
/attach 123 "Logo_Design_Sketch.png"
/attach 123 "Color_Palette.pdf"
/attach 123 "Typography_Specs.pdf"
/attach 123 "Final_Logo_Files.zip"
```

**Track design iterations:**
```
/attach 124 "Design_v1_Initial.png"
/attach 124 "Design_v2_Client_Feedback.png"
/attach 124 "Design_v3_Final.png"
```

### Client Work

**Project documentation:**
```
/attach 125 "Client_Brief.pdf"
/attach 125 "Project_Proposal.docx"
/attach 125 "Contract_Agreement.pdf"
/attach 125 "Invoice_Template.xlsx"
```

**Client communications:**
```
/attach 126 "Client_Email_Thread.txt"
/attach 126 "Meeting_Recording.mp3"
/attach 126 "Feedback_Summary.pdf"
```

### Personal Projects

**Learning materials:**
```
/attach 127 "Course_Notes.txt"
/attach 127 "Practice_Exercises.pdf"
/attach 127 "Reference_Materials.zip"
```

**Personal planning:**
```
/attach 128 "Goals_2025.pdf"
/attach 128 "Budget_Spreadsheet.xlsx"
/attach 128 "Travel_Plans.txt"
```

### Development Projects

**Code and documentation:**
```
/attach 129 "API_Documentation.pdf"
/attach 129 "Database_Schema.sql"
/attach 129 "Test_Results.txt"
/attach 129 "Deployment_Notes.txt"
```

**Project assets:**
```
/attach 130 "Project_Logo.png"
/attach 130 "Brand_Guidelines.pdf"
/attach 130 "Assets_Package.zip"
```

## 📊 Best Practices

### File Naming

**Use consistent naming:**
```
ProjectName_Type_Version.ext
Example: Website_Design_Mockup_v2.png
```

**Include dates when relevant:**
```
Meeting_Notes_2025-07-02.txt
Client_Feedback_2025-06-15.pdf
```

### Organization

**Group related files:**
- Attach multiple files to the same task
- Use consistent descriptions
- Keep files organized by project phase

**Regular maintenance:**
- Review attachments periodically
- Remove outdated files
- Update descriptions as needed

### Security

**File management:**
- Only attach files you own or have permission to share
- Be careful with sensitive information
- Use appropriate file types for your content

---

**Keep your projects organized!** Start by attaching a file to a task: send a file to your bot, then reply with `/attach 123` to attach it to task #123.

---

**Next Steps:**
- [Advanced Tasks](advanced-tasks.md) - Powerful task management features
- [Analytics](analytics.md) - Understand your productivity patterns
- [Calendar Integration](../commands/calendar-integration.md) - Sync with your schedule
- [Examples](../examples.md) - See real-world file attachment scenarios 