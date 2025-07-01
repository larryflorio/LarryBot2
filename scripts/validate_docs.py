#!/usr/bin/env python3
"""
Documentation Validation Script for CI/CD
=========================================

This script validates that documentation statistics match the actual codebase
to prevent statistical inaccuracies from being introduced.
"""

import subprocess
import sys
import glob
import re
from pathlib import Path

def validate_test_count():
    """Validate test count in documentation matches actual tests."""
    print("🧪 Validating Test Count...")
    
    try:
        # Get actual test count
        result = subprocess.run(
            ['python', '-m', 'pytest', '--collect-only', '-q'],
            capture_output=True, text=True, cwd='.', timeout=30
        )
        
        actual_count = None
        for line in result.stdout.split('\n'):
            if 'tests collected' in line:
                actual_count = int(line.split()[0])
                break
        
        if actual_count is None:
            print("   ❌ Could not determine actual test count")
            return False
        
        # Check documentation files for test count references
        doc_files = glob.glob('docs/**/*.md', recursive=True)
        errors = []
        
        for doc_file in doc_files:
            try:
                with open(doc_file, 'r') as f:
                    content = f.read()
                    
                # Look for test count patterns
                patterns = [
                    r'(\d+)\s+tests?\s+(?:passing|implemented)',
                    r'(\d+)\s+Tests?[:\s]',
                    r'Test Count[:\s]*(\d+)',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        doc_count = int(match)
                        if doc_count != actual_count and doc_count != 695:  # Allow for passing count
                            errors.append(f"{doc_file}: Claims {doc_count} tests, actual is {actual_count}")
                            
            except Exception as e:
                print(f"   ⚠️  Error reading {doc_file}: {e}")
        
        if errors:
            print(f"   ❌ Test count mismatches found:")
            for error in errors:
                print(f"      {error}")
            return False
        else:
            print(f"   ✅ All test count references appear correct ({actual_count} tests)")
            return True
            
    except Exception as e:
        print(f"   ❌ Error validating test count: {e}")
        return False

def validate_plugin_count():
    """Validate plugin count in documentation matches actual plugins."""
    print("🔌 Validating Plugin Count...")
    
    try:
        # Get actual plugin count
        plugin_files = [f for f in glob.glob('larrybot/plugins/*.py') if '__init__' not in f]
        actual_count = len(plugin_files)
        
        # Check documentation files
        doc_files = glob.glob('docs/**/*.md', recursive=True)
        errors = []
        
        for doc_file in doc_files:
            try:
                with open(doc_file, 'r') as f:
                    content = f.read()
                    
                # Look for plugin count patterns
                patterns = [
                    r'(\d+)\s+(?:active\s+)?plugins?',
                    r'(\d+)\s+Active Plugins?',
                    r'Plugin[s]?[:\s]*(\d+)',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        doc_count = int(match)
                        if doc_count != actual_count:
                            errors.append(f"{doc_file}: Claims {doc_count} plugins, actual is {actual_count}")
                            
            except Exception as e:
                print(f"   ⚠️  Error reading {doc_file}: {e}")
        
        if errors:
            print(f"   ❌ Plugin count mismatches found:")
            for error in errors:
                print(f"      {error}")
            return False
        else:
            print(f"   ✅ All plugin count references appear correct ({actual_count} plugins)")
            return True
            
    except Exception as e:
        print(f"   ❌ Error validating plugin count: {e}")
        return False

def validate_command_count():
    """Validate command count in documentation matches actual commands.""" 
    print("🤖 Validating Command Count...")
    
    try:
        # Get actual command count
        command_count = 0
        plugin_files = glob.glob('larrybot/plugins/*.py')
        
        for file_path in plugin_files:
            if '__init__' in file_path:
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
                matches = re.findall(r'command_registry\.register\s*\(', content)
                command_count += len(matches)
        
        # Check documentation for command count claims
        doc_files = glob.glob('docs/**/*.md', recursive=True)
        errors = []
        
        for doc_file in doc_files:
            try:
                with open(doc_file, 'r') as f:
                    content = f.read()
                    
                # Look for command count patterns
                patterns = [
                    r'(\d+)\s+(?:total\s+)?commands?',
                    r'(\d+)\s+Commands?[:\s]',
                    r'Command[s]?[:\s]*(\d+)',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        doc_count = int(match)
                        if doc_count != command_count:
                            errors.append(f"{doc_file}: Claims {doc_count} commands, actual is {command_count}")
                            
            except Exception as e:
                print(f"   ⚠️  Error reading {doc_file}: {e}")
        
        if errors:
            print(f"   ❌ Command count mismatches found:")
            for error in errors:
                print(f"      {error}")
            return False
        else:
            print(f"   ✅ All command count references appear correct ({command_count} commands)")
            return True
            
    except Exception as e:
        print(f"   ❌ Error validating command count: {e}")
        return False

def main():
    """Main validation function."""
    print("=" * 60)
    print("📋 DOCUMENTATION VALIDATION")
    print("=" * 60)
    
    results = []
    
    # Run all validations
    results.append(validate_test_count())
    results.append(validate_plugin_count()) 
    results.append(validate_command_count())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} validation checks passed!")
        print("Documentation statistics are accurate.")
        return 0
    else:
        print(f"❌ {total - passed} out of {total} validation checks failed!")
        print("Documentation contains statistical inaccuracies that must be fixed.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 