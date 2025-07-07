#!/usr/bin/env python3
"""
Info Emoji Detection Script

This script comprehensively scans the LarryBot2 codebase to find all instances
of the  emoji usage, including direct usage, ButtonType.INFO usage, and
format_info_message calls that will generate  prefixes.
"""

import os
import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass

@dataclass
class EmojiUsage:
    """Represents a single  emoji usage instance."""
    file_path: str
    line_number: int
    line_content: str
    usage_type: str  # 'direct', 'button_type', 'format_info', 'action_template'
    context: str
    impact_level: str  # 'high', 'medium', 'low'

class InfoEmojiDetector:
    """Detects all  emoji usage in the codebase."""
    
    def __init__(self, root_dir: str = '.'):
        self.root_dir = Path(root_dir)
        self.usages: List[EmojiUsage] = []
        self.files_scanned = 0
        self.total_usages = 0
        
    def scan_codebase(self) -> Dict[str, List[EmojiUsage]]:
        """Scan the entire codebase for  usage."""
        print("🔍 Scanning codebase for  emoji usage...")
        
        # Define files to scan
        scan_patterns = [
            'larrybot/**/*.py',
            'tests/**/*.py',
            'scripts/**/*.py',
            '*.md',
            '*.txt'
        ]
        
        for pattern in scan_patterns:
            for file_path in self.root_dir.glob(pattern):
                if file_path.is_file() and not self._should_skip_file(file_path):
                    self._scan_file(file_path)
        
        return self._categorize_usages()
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if a file should be skipped."""
        skip_patterns = [
            '__pycache__',
            '.git',
            'venv',
            'htmlcov',
            '.pytest_cache',
            '*.pyc',
            '*.pyo'
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _scan_file(self, file_path: Path):
        """Scan a single file for  usage."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            self.files_scanned += 1
            
            # Scan for direct  usage
            for i, line in enumerate(lines, 1):
                if '' in line:
                    self.usages.append(EmojiUsage(
                        file_path=str(file_path),
                        line_number=i,
                        line_content=line.strip(),
                        usage_type='direct',
                        context=f'Direct  usage in {file_path.name}',
                        impact_level='high'
                    ))
            
            # Scan for ButtonType.INFO usage
            for i, line in enumerate(lines, 1):
                if 'ButtonType.INFO' in line:
                    self.usages.append(EmojiUsage(
                        file_path=str(file_path),
                        line_number=i,
                        line_content=line.strip(),
                        usage_type='button_type',
                        context=f'ButtonType.INFO usage in {file_path.name}',
                        impact_level='high'
                    ))
            
            # Scan for format_info_message calls
            for i, line in enumerate(lines, 1):
                if 'format_info_message' in line:
                    self.usages.append(EmojiUsage(
                        file_path=str(file_path),
                        line_number=i,
                        line_content=line.strip(),
                        usage_type='format_info',
                        context=f'format_info_message call in {file_path.name}',
                        impact_level='high'
                    ))
            
            # Scan for action templates with 
            for i, line in enumerate(lines, 1):
                if 'ActionType.REFRESH' in line and '' in line:
                    self.usages.append(EmojiUsage(
                        file_path=str(file_path),
                        line_number=i,
                        line_content=line.strip(),
                        usage_type='action_template',
                        context=f'ActionType.REFRESH template in {file_path.name}',
                        impact_level='medium'
                    ))
                    
        except Exception as e:
            print(f"⚠️  Error scanning {file_path}: {e}")
    
    def _categorize_usages(self) -> Dict[str, List[EmojiUsage]]:
        """Categorize usages by type and impact."""
        categories = {
            'direct': [],
            'button_type': [],
            'format_info': [],
            'action_template': [],
            'high_impact': [],
            'medium_impact': [],
            'low_impact': []
        }
        
        for usage in self.usages:
            categories[usage.usage_type].append(usage)
            
            if usage.impact_level == 'high':
                categories['high_impact'].append(usage)
            elif usage.impact_level == 'medium':
                categories['medium_impact'].append(usage)
            else:
                categories['low_impact'].append(usage)
        
        return categories
    
    def generate_report(self) -> str:
        """Generate a comprehensive report of findings."""
        categories = self._categorize_usages()
        
        report = []
        report.append("#  Emoji Usage Report")
        report.append("=" * 50)
        report.append(f"📊 **Summary Statistics**")
        report.append(f"  Files scanned: {self.files_scanned}")
        report.append(f"  Total usages found: {len(self.usages)}")
        report.append(f"  High impact: {len(categories['high_impact'])}")
        report.append(f"  Medium impact: {len(categories['medium_impact'])}")
        report.append(f"  Low impact: {len(categories['low_impact'])}")
        report.append("")
        
        # Direct usage
        if categories['direct']:
            report.append("## 🔍 Direct  Usage")
            report.append("These are literal  characters in the code:")
            for usage in categories['direct']:
                report.append(f"  - **{usage.file_path}:{usage.line_number}**")
                report.append(f"    ```{usage.line_content}```")
            report.append("")
        
        # Button type usage
        if categories['button_type']:
            report.append("## 🔘 ButtonType.INFO Usage")
            report.append("These will generate  prefixes on buttons:")
            for usage in categories['button_type']:
                report.append(f"  - **{usage.file_path}:{usage.line_number}**")
                report.append(f"    ```{usage.line_content}```")
            report.append("")
        
        # Format info usage
        if categories['format_info']:
            report.append("## 📝 format_info_message Usage")
            report.append("These will generate  prefixes on messages:")
            for usage in categories['format_info']:
                report.append(f"  - **{usage.file_path}:{usage.line_number}**")
                report.append(f"    ```{usage.line_content}```")
            report.append("")
        
        # Action template usage
        if categories['action_template']:
            report.append("## ⚙️ Action Template Usage")
            report.append("These define  in action templates:")
            for usage in categories['action_template']:
                report.append(f"  - **{usage.file_path}:{usage.line_number}**")
                report.append(f"    ```{usage.line_content}```")
            report.append("")
        
        # High impact items
        if categories['high_impact']:
            report.append("## ⚠️ High Impact Items")
            report.append("These require immediate attention:")
            for usage in categories['high_impact']:
                report.append(f"  - **{usage.file_path}:{usage.line_number}** - {usage.usage_type}")
            report.append("")
        
        return "\n".join(report)
    
    def generate_removal_plan(self) -> str:
        """Generate a step-by-step removal plan."""
        categories = self._categorize_usages()
        
        plan = []
        plan.append("#  Emoji Removal Plan")
        plan.append("=" * 50)
        plan.append("")
        
        plan.append("## 🎯 Phase 1: Core System Changes")
        plan.append("")
        
        # Core system files
        core_files = set()
        for usage in categories['high_impact']:
            if 'ux_helpers.py' in usage.file_path or 'enhanced_ux_helpers.py' in usage.file_path:
                core_files.add(usage.file_path)
        
        if core_files:
            plan.append("### 1.1 Update Core UX Files")
            for file_path in sorted(core_files):
                plan.append(f"  - **{file_path}**")
                plan.append("    - Remove  from `format_info_message()` function")
                plan.append("    - Remove  from `ButtonType.INFO` configuration")
                plan.append("    - Remove  from `ActionType.REFRESH` template")
            plan.append("")
        
        plan.append("## 🔧 Phase 2: Plugin Updates")
        plan.append("")
        
        # Plugin files
        plugin_files = set()
        for usage in categories['format_info'] + categories['button_type']:
            if 'plugins/' in usage.file_path:
                plugin_files.add(usage.file_path)
        
        if plugin_files:
            plan.append("### 2.1 Update Plugin Files")
            for file_path in sorted(plugin_files):
                plan.append(f"  - **{file_path}**")
                plan.append("    - Review message titles (many already have appropriate emojis)")
                plan.append("    - Update button text patterns if needed")
                plan.append("    - Ensure no functionality is broken")
            plan.append("")
        
        plan.append("## 🧪 Phase 3: Testing Strategy")
        plan.append("")
        plan.append("### 3.1 Automated Testing")
        plan.append("  - Create test to verify no  appears in output")
        plan.append("  - Test all message formatting functions")
        plan.append("  - Test all button generation functions")
        plan.append("  - Run full test suite to ensure no regressions")
        plan.append("")
        
        plan.append("### 3.2 Manual Testing")
        plan.append("  - Test all info messages display correctly")
        plan.append("  - Test all buttons function properly")
        plan.append("  - Test navigation flows")
        plan.append("  - Test error message clarity")
        plan.append("")
        
        plan.append("## 📋 Phase 4: Validation")
        plan.append("")
        plan.append("### 4.1 Final Checks")
        plan.append("  - Run detection script again to verify no  remains")
        plan.append("  - Manual verification of key user flows")
        plan.append("  - Performance testing to ensure no degradation")
        plan.append("  - Documentation updates")
        
        return "\n".join(plan)

def main():
    """Main function to run the detection."""
    detector = InfoEmojiDetector()
    
    print("🔍 Starting  emoji detection...")
    categories = detector.scan_codebase()
    
    print(f"\n📊 Detection Complete!")
    print(f"  Files scanned: {detector.files_scanned}")
    print(f"  Total usages found: {len(detector.usages)}")
    print(f"  High impact: {len(categories['high_impact'])}")
    print(f"  Medium impact: {len(categories['medium_impact'])}")
    print(f"  Low impact: {len(categories['low_impact'])}")
    
    # Generate reports
    report = detector.generate_report()
    plan = detector.generate_removal_plan()
    
    # Save reports
    with open('INFO_EMOJI_DETECTION_REPORT.md', 'w') as f:
        f.write(report)
    
    with open('INFO_EMOJI_REMOVAL_PLAN.md', 'w') as f:
        f.write(plan)
    
    print(f"\n📄 Reports generated:")
    print(f"  - INFO_EMOJI_DETECTION_REPORT.md")
    print(f"  - INFO_EMOJI_REMOVAL_PLAN.md")
    
    # Show high impact items
    if categories['high_impact']:
        print(f"\n⚠️  High Impact Items Found:")
        for usage in categories['high_impact'][:5]:  # Show first 5
            print(f"  - {usage.file_path}:{usage.line_number} ({usage.usage_type})")
        if len(categories['high_impact']) > 5:
            print(f"  ... and {len(categories['high_impact']) - 5} more")

if __name__ == "__main__":
    main() 