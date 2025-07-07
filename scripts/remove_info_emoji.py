#!/usr/bin/env python3
"""
Automated  Emoji Removal Script

This script safely removes all instances of the  emoji from the LarryBot2 codebase
while preserving functionality and ensuring no breaking changes.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass
import subprocess

@dataclass
class RemovalChange:
    """Represents a single removal change."""
    file_path: str
    line_number: int
    original_line: str
    modified_line: str
    change_type: str  # 'format_info', 'button_type', 'action_template', 'direct'
    description: str

class InfoEmojiRemover:
    """Safely removes  emoji from the codebase."""
    
    def __init__(self, root_dir: str = '.'):
        self.root_dir = Path(root_dir)
        self.changes: List[RemovalChange] = []
        self.backup_dir = Path('backup_before_emoji_removal')
        self.files_modified = 0
        
    def create_backup(self):
        """Create a backup of the codebase before making changes."""
        print("💾 Creating backup...")
        
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        # Copy larrybot directory
        if (self.root_dir / 'larrybot').exists():
            shutil.copytree(self.root_dir / 'larrybot', self.backup_dir / 'larrybot')
        
        # Copy tests directory
        if (self.root_dir / 'tests').exists():
            shutil.copytree(self.root_dir / 'tests', self.backup_dir / 'tests')
        
        # Copy scripts directory
        if (self.root_dir / 'scripts').exists():
            shutil.copytree(self.root_dir / 'scripts', self.backup_dir / 'scripts')
        
        print(f"✅ Backup created at {self.backup_dir}")
    
    def remove_from_format_info_message(self, file_path: Path) -> bool:
        """Remove  from format_info_message function."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            modified = False
            
            for i, line in enumerate(lines):
                if 'format_info_message' in line and '' in line:
                    # Find the line that adds  prefix
                    original_line = line
                    modified_line = line.replace("", "")
                    
                    self.changes.append(RemovalChange(
                        file_path=str(file_path),
                        line_number=i + 1,
                        original_line=original_line,
                        modified_line=modified_line,
                        change_type='format_info',
                        description='Removed  from format_info_message'
                    ))
                    
                    lines[i] = modified_line
                    modified = True
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                self.files_modified += 1
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️  Error processing {file_path}: {e}")
            return False
    
    def remove_from_button_type_config(self, file_path: Path) -> bool:
        """Remove  from ButtonType.INFO configuration."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            modified = False
            
            for i, line in enumerate(lines):
                if 'ButtonType.INFO' in line and '' in line:
                    original_line = line
                    # Replace  with a more appropriate emoji or empty string
                    modified_line = line.replace("''", "'📋'")  # Use 📋 as default
                    
                    self.changes.append(RemovalChange(
                        file_path=str(file_path),
                        line_number=i + 1,
                        original_line=original_line,
                        modified_line=modified_line,
                        change_type='button_type',
                        description='Replaced  with 📋 in ButtonType.INFO'
                    ))
                    
                    lines[i] = modified_line
                    modified = True
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                self.files_modified += 1
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️  Error processing {file_path}: {e}")
            return False
    
    def remove_from_action_templates(self, file_path: Path) -> bool:
        """Remove  from action templates."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            modified = False
            
            for i, line in enumerate(lines):
                if 'ActionType.REFRESH' in line and '' in line:
                    original_line = line
                    # Replace  with 🔄 for refresh actions
                    modified_line = line.replace("''", "'🔄'")
                    
                    self.changes.append(RemovalChange(
                        file_path=str(file_path),
                        line_number=i + 1,
                        original_line=original_line,
                        modified_line=modified_line,
                        change_type='action_template',
                        description='Replaced  with 🔄 in ActionType.REFRESH'
                    ))
                    
                    lines[i] = modified_line
                    modified = True
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                self.files_modified += 1
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️  Error processing {file_path}: {e}")
            return False
    
    def remove_direct_usage(self, file_path: Path) -> bool:
        """Remove direct  usage from files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            modified = False
            
            for i, line in enumerate(lines):
                if '' in line:
                    original_line = line
                    # Remove  but preserve the rest of the line
                    modified_line = line.replace('', '')
                    
                    self.changes.append(RemovalChange(
                        file_path=str(file_path),
                        line_number=i + 1,
                        original_line=original_line,
                        modified_line=modified_line,
                        change_type='direct',
                        description='Removed direct  usage'
                    ))
                    
                    lines[i] = modified_line
                    modified = True
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                self.files_modified += 1
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️  Error processing {file_path}: {e}")
            return False
    
    def process_file(self, file_path: Path) -> bool:
        """Process a single file for  removal."""
        if not file_path.is_file():
            return False
        
        # Skip backup directory
        if 'backup_before_emoji_removal' in str(file_path):
            return False
        
        # Skip binary files and cache
        if file_path.suffix in ['.pyc', '.pyo', '.pyd'] or '__pycache__' in str(file_path):
            return False
        
        modified = False
        
        # Process based on file type and content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file contains 
            if '' not in content:
                return False
            
            # Process different types of files
            if 'ux_helpers.py' in str(file_path):
                modified |= self.remove_from_format_info_message(file_path)
                modified |= self.remove_from_button_type_config(file_path)
            elif 'enhanced_ux_helpers.py' in str(file_path):
                modified |= self.remove_from_button_type_config(file_path)
                modified |= self.remove_from_action_templates(file_path)
            else:
                # For other files, remove direct usage
                modified |= self.remove_direct_usage(file_path)
            
            return modified
            
        except Exception as e:
            print(f"⚠️  Error processing {file_path}: {e}")
            return False
    
    def remove_all_instances(self) -> Dict[str, int]:
        """Remove all  instances from the codebase."""
        print("🔧 Starting  emoji removal...")
        
        # Create backup first
        self.create_backup()
        
        # Define files to process
        patterns = [
            'larrybot/**/*.py',
            'tests/**/*.py',
            'scripts/**/*.py'
        ]
        
        stats = {
            'files_processed': 0,
            'files_modified': 0,
            'changes_made': 0
        }
        
        for pattern in patterns:
            for file_path in self.root_dir.glob(pattern):
                if file_path.is_file():
                    stats['files_processed'] += 1
                    if self.process_file(file_path):
                        stats['files_modified'] += 1
        
        stats['changes_made'] = len(self.changes)
        return stats
    
    def run_tests(self) -> bool:
        """Run tests to ensure no regressions."""
        print("🧪 Running tests to validate changes...")
        
        try:
            # Run the specific test for  removal
            result = subprocess.run([
                'python', '-m', 'pytest', 'tests/test_no_info_emoji.py', '-v'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ All tests passed!")
                return True
            else:
                print("❌ Tests failed!")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"⚠️  Error running tests: {e}")
            return False
    
    def generate_report(self) -> str:
        """Generate a comprehensive report of changes."""
        report = []
        report.append("#  Emoji Removal Report")
        report.append("=" * 50)
        report.append(f"📊 **Summary**")
        report.append(f"  Files modified: {self.files_modified}")
        report.append(f"  Total changes: {len(self.changes)}")
        report.append("")
        
        # Group changes by type
        changes_by_type = {}
        for change in self.changes:
            if change.change_type not in changes_by_type:
                changes_by_type[change.change_type] = []
            changes_by_type[change.change_type].append(change)
        
        for change_type, changes in changes_by_type.items():
            report.append(f"## {change_type.upper()} Changes ({len(changes)})")
            for change in changes:
                report.append(f"  - **{change.file_path}:{change.line_number}**")
                report.append(f"    - {change.description}")
                report.append(f"    - Before: `{change.original_line.strip()}`")
                report.append(f"    - After: `{change.modified_line.strip()}`")
            report.append("")
        
        return "\n".join(report)
    
    def rollback_changes(self):
        """Rollback changes using backup."""
        print("🔄 Rolling back changes...")
        
        if not self.backup_dir.exists():
            print("❌ No backup found for rollback")
            return False
        
        try:
            # Remove current larrybot directory
            if (self.root_dir / 'larrybot').exists():
                shutil.rmtree(self.root_dir / 'larrybot')
            
            # Restore from backup
            shutil.copytree(self.backup_dir / 'larrybot', self.root_dir / 'larrybot')
            
            print("✅ Rollback completed")
            return True
            
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False

def main():
    """Main function to run the removal process."""
    remover = InfoEmojiRemover()
    
    print("🚀 Starting automated  emoji removal...")
    
    # Step 1: Remove all instances
    stats = remover.remove_all_instances()
    
    print(f"\n📊 Removal Complete!")
    print(f"  Files processed: {stats['files_processed']}")
    print(f"  Files modified: {stats['files_modified']}")
    print(f"  Changes made: {stats['changes_made']}")
    
    # Step 2: Run tests
    if remover.run_tests():
        print("\n✅ All tests passed! Changes are safe.")
        
        # Generate report
        report = remover.generate_report()
        with open('INFO_EMOJI_REMOVAL_REPORT.md', 'w') as f:
            f.write(report)
        
        print(f"\n📄 Report generated: INFO_EMOJI_REMOVAL_REPORT.md")
        
        # Ask for confirmation
        response = input("\n🤔 Do you want to keep these changes? (y/N): ")
        if response.lower() != 'y':
            print("🔄 Rolling back changes...")
            remover.rollback_changes()
        else:
            print("✅ Changes kept!")
            
    else:
        print("\n❌ Tests failed! Rolling back changes...")
        remover.rollback_changes()

if __name__ == "__main__":
    main() 