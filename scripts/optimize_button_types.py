#!/usr/bin/env python3
"""
Button Type Optimization Script

This script removes inappropriate ℹ️ prefixes from buttons by updating
ButtonType assignments to be semantically correct without redundant icons.
"""

import os
import re
import ast
from pathlib import Path

# Button type mapping rules - remove all prefixes, use semantic styling
BUTTON_TYPE_RULES = {
    # Navigation/Info buttons (no prefix, subtle styling)
    "⬅️ Back": "ButtonType.INFO",
    "🏠 Main Menu": "ButtonType.INFO", 
    "🔙 Back to": "ButtonType.INFO",
    "ℹ️ Info": "ButtonType.INFO",
    
    # Action buttons (no prefix, clear styling)
    "📋 View": "ButtonType.SECONDARY",
    "✏️ Edit": "ButtonType.SECONDARY",
    "🔄 Refresh": "ButtonType.SECONDARY",
    "📊 Analytics": "ButtonType.SECONDARY",
    "📈 Detailed": "ButtonType.SECONDARY",
    "⏰ Time Tracking": "ButtonType.SECONDARY",
    "🎯 Performance": "ButtonType.SECONDARY",
    "📋 Reports": "ButtonType.SECONDARY",
    "📝 Edit Description": "ButtonType.SECONDARY",
    "📝 Add Description": "ButtonType.SECONDARY",
    "📋 Export List": "ButtonType.SECONDARY",
    "📎 Add New File": "ButtonType.SECONDARY",
    "📋 Task Details": "ButtonType.SECONDARY",
    "🎯 Priority": "ButtonType.SECONDARY",
    "📋 Status": "ButtonType.SECONDARY",
    "🏷️ Tags": "ButtonType.SECONDARY",
    "📂 Category": "ButtonType.SECONDARY",
    "⏰ Time Tracking": "ButtonType.SECONDARY",
    "👥 Assign": "ButtonType.SECONDARY",
    "💾 Save Filter": "ButtonType.SECONDARY",
    "💾 Save Selection": "ButtonType.SECONDARY",
    "⏰ Snooze": "ButtonType.SECONDARY",
    "📋 View Tasks": "ButtonType.SECONDARY",
    "📋 Tasks": "ButtonType.SECONDARY",
    "👥 Clients": "ButtonType.SECONDARY",
    "⏰ Reminders": "ButtonType.SECONDARY",
    "📎 Files": "ButtonType.SECONDARY",
    "📋 View Tasks": "ButtonType.SECONDARY",
    
    # Primary actions (no prefix, prominent styling)
    "✅ Complete": "ButtonType.PRIMARY",
    "✅ Confirm": "ButtonType.PRIMARY",
    "✅ Mark Done": "ButtonType.PRIMARY",
    "➕ Add": "ButtonType.PRIMARY",
    "➕ Add Task": "ButtonType.PRIMARY",
    "💾 Save": "ButtonType.PRIMARY",
    
    # Danger actions (no prefix, warning styling)
    "🗑️ Delete": "ButtonType.DANGER",
    "❌ Cancel": "ButtonType.DANGER",
    "❌ Dismiss": "ButtonType.DANGER",
    "🗑️ Remove": "ButtonType.DANGER",
    "🗑️ Bulk Remove": "ButtonType.DANGER",
    "🗑️ Delete Reminder": "ButtonType.DANGER",
    
    # Special cases - keep as is
    "📅 Today": "ButtonType.SECONDARY",
    "📅 Week": "ButtonType.SECONDARY", 
    "📅 Month": "ButtonType.SECONDARY",
    "📅 Upcoming": "ButtonType.SECONDARY",
    "🔄 Sync": "ButtonType.SECONDARY",
    "⚙️ Settings": "ButtonType.SECONDARY",
    "📊 Statistics": "ButtonType.SECONDARY",
    "📊 Preview": "ButtonType.SECONDARY",
    "📊 Productivity": "ButtonType.SECONDARY",
    "📅 Trends": "ButtonType.SECONDARY",
    "📅 Date Range": "ButtonType.SECONDARY",
    "🔍 Advanced Search": "ButtonType.SECONDARY",
    "🔍 Search": "ButtonType.SECONDARY",
    "⚠️ Overdue": "ButtonType.SECONDARY",
    "📅 Today": "ButtonType.SECONDARY",
    "📅 Calendar": "ButtonType.SECONDARY",
}

def find_button_creations(file_path):
    """Find all UnifiedButtonBuilder.create_button calls in a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match create_button calls
    pattern = r'UnifiedButtonBuilder\.create_button\s*\(\s*([^,]+),\s*([^,]+)(?:,\s*button_type\s*=\s*([^,)]+))?'
    matches = re.finditer(pattern, content)
    
    changes = []
    for match in matches:
        text_arg = match.group(1).strip().strip('"\'')
        callback_arg = match.group(2).strip()
        current_button_type = match.group(3).strip() if match.group(3) else None
        
        # Check if this button text matches our rules
        for button_text, new_button_type in BUTTON_TYPE_RULES.items():
            if button_text in text_arg:
                changes.append({
                    'line': match.group(0),
                    'text': text_arg,
                    'current_type': current_button_type,
                    'new_type': new_button_type,
                    'start': match.start(),
                    'end': match.end()
                })
                break
    
    return changes

def update_button_types(file_path):
    """Update button types in a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes = find_button_creations(file_path)
    if not changes:
        return False
    
    # Sort changes by position (reverse order to avoid offset issues)
    changes.sort(key=lambda x: x['start'], reverse=True)
    
    modified_content = content
    for change in changes:
        old_call = change['line']
        
        # Create new call with updated button_type
        if 'button_type=' in old_call:
            # Replace existing button_type
            new_call = re.sub(
                r'button_type\s*=\s*[^,)]+',
                f'button_type={change["new_type"]}',
                old_call
            )
        else:
            # Add button_type parameter
            new_call = old_call.rstrip(')') + f', button_type={change["new_type"]})'
        
        modified_content = modified_content[:change['start']] + new_call + modified_content[change['end']:]
    
    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    return len(changes) > 0

def main():
    """Main function to optimize button types across the codebase."""
    # Files to process
    files_to_process = [
        'larrybot/plugins/tasks.py',
        'larrybot/plugins/client.py',
        'larrybot/plugins/calendar.py',
        'larrybot/plugins/habit.py',
        'larrybot/plugins/reminder.py',
        'larrybot/plugins/file_attachments.py',
        'larrybot/plugins/advanced_tasks/core.py',
        'larrybot/plugins/advanced_tasks/filtering.py',
        'larrybot/plugins/advanced_tasks/subtasks_dependencies.py',
        'larrybot/plugins/advanced_tasks/tags_comments.py',
        'larrybot/plugins/advanced_tasks/time_tracking.py',
        'larrybot/utils/ux_helpers.py',
        'larrybot/utils/enhanced_ux_helpers.py',
    ]
    
    total_changes = 0
    files_modified = 0
    
    print("🔧 Button Type Optimization")
    print("=" * 50)
    
    for file_path in files_to_process:
        if os.path.exists(file_path):
            print(f"Processing {file_path}...")
            try:
                if update_button_types(file_path):
                    files_modified += 1
                    changes = find_button_creations(file_path)
                    total_changes += len(changes)
                    print(f"  ✅ Modified {len(changes)} button(s)")
                else:
                    print(f"  ⏭️  No changes needed")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        else:
            print(f"  ⚠️  File not found: {file_path}")
    
    print("\n" + "=" * 50)
    print(f"📊 Summary:")
    print(f"  Files modified: {files_modified}")
    print(f"  Total button changes: {total_changes}")
    print(f"\n✅ Button type optimization complete!")
    print(f"   All inappropriate ℹ️ prefixes have been removed.")
    print(f"   Buttons now use semantic styling without redundant icons.")

if __name__ == "__main__":
    main() 