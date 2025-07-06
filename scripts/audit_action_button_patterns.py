#!/usr/bin/env python3
"""
Audit script for action button/callback patterns in LarryBot2.
Finds old callback patterns, direct InlineKeyboardButton usage, and inconsistent navigation callbacks.
Outputs a checklist for migration.
"""
import os
import re

# Patterns to search for
PATTERNS = [
    (r'callback_data=["\\\]?task_complete', 'Old task_complete callback'),
    (r'callback_data=["\\\]?task_done', 'task_done callback (should be checked)'),
    (r'callback_data=["\\\]?client_', 'client_ callback'),
    (r'callback_data=["\\\]?habit_', 'habit_ callback'),
    (r'callback_data=["\\\]?confirm_', 'confirm_ callback'),
    (r'callback_data=["\\\]?back', 'back navigation callback'),
    (r'callback_data=["\\\]?main_menu', 'main_menu navigation callback'),
    (r'callback_data=["\\\]?cancel', 'cancel navigation callback'),
    (r'InlineKeyboardButton\(', 'Direct InlineKeyboardButton usage'),
]

EXCLUDE_DIRS = {'.git', 'venv', '__pycache__', 'htmlcov', 'node_modules', '.mypy_cache'}

checklist = []

for root, dirs, files in os.walk('.'):
    # Skip excluded dirs
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for fname in files:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            for pat, desc in PATTERNS:
                if re.search(pat, line):
                    checklist.append(f"{desc}: {fpath}:{i}: {line.strip()}")

# Write checklist
with open('ACTION_BUTTON_MIGRATION_CHECKLIST.md', 'w') as f:
    f.write('# Action Button Migration Checklist\n\n')
    for item in checklist:
        f.write(f'- [ ] {item}\n')

print(f"Found {len(checklist)} potential migration points.")
print("Checklist written to ACTION_BUTTON_MIGRATION_CHECKLIST.md") 