#!/usr/bin/env python3
"""
Documentation Accuracy Verification Script
==========================================

This script verifies that all documentation statistics match the actual codebase.
Run this script to ensure documentation accuracy before publishing updates.
"""

import subprocess
import os
import glob
import re
from datetime import datetime
from pathlib import Path

def get_test_statistics():
    """Get accurate test count and results."""
    print("🧪 Collecting Test Statistics...")
    
    try:
        # Get test collection count
        result = subprocess.run(
            ['python', '-m', 'pytest', '--collect-only', '-q'],
            capture_output=True, text=True, cwd='.'
        )
        
        # Parse test count from output
        lines = result.stdout.split('\n')
        test_count = None
        for line in lines:
            if 'tests collected' in line:
                test_count = int(line.split()[0])
                break
        
        print(f"   📊 Total Tests Collected: {test_count}")
        
    except Exception as e:
        print(f"   ❌ Error collecting tests: {e}")
        test_count = "ERROR"
    
    # Get test results
    try:
        result = subprocess.run(
            ['python', '-m', 'pytest', '--tb=no', '-q'],
            capture_output=True, text=True, cwd='.', timeout=120
        )
        
        # Parse results
        output = result.stdout
        if 'passed' in output and 'failed' in output:
            # Extract pass/fail counts
            passed = failed = 0
            for line in output.split('\n'):
                if 'passed' in line and 'failed' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'failed,':
                            failed = int(parts[i-1])
                        elif part == 'passed':
                            passed = int(parts[i-1])
            
            print(f"   ✅ Tests Passed: {passed}")
            print(f"   ❌ Tests Failed: {failed}")
            
            return {
                'total_tests': test_count,
                'passed_tests': passed,
                'failed_tests': failed,
                'success_rate': f"{(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "N/A"
            }
        else:
            return {
                'total_tests': test_count,
                'passed_tests': test_count,
                'failed_tests': 0,
                'success_rate': "100%" if test_count else "N/A"
            }
            
    except Exception as e:
        print(f"   ⚠️  Test execution timeout/error: {e}")
        return {
            'total_tests': test_count,
            'passed_tests': "Unknown",
            'failed_tests': "Unknown", 
            'success_rate': "Unknown"
        }

def get_coverage_statistics():
    """Get accurate coverage statistics."""
    print("\n📈 Collecting Coverage Statistics...")
    
    try:
        result = subprocess.run(
            ['python', '-m', 'pytest', '--cov=larrybot', '--cov-report=term-missing', '--tb=no', '-q'],
            capture_output=True, text=True, cwd='.', timeout=180
        )
        
        output = result.stdout
        
        # Extract coverage info from TOTAL line
        for line in output.split('\n'):
            if line.startswith('TOTAL'):
                parts = line.split()
                if len(parts) >= 4:
                    statements = int(parts[1])
                    missing = int(parts[2])
                    coverage = parts[3].rstrip('%')
                    
                    print(f"   📊 Total Statements: {statements}")
                    print(f"   📊 Missing Coverage: {missing}")
                    print(f"   📊 Coverage Percentage: {coverage}%")
                    
                    return {
                        'total_statements': statements,
                        'missing_statements': missing,
                        'coverage_percentage': f"{coverage}%"
                    }
        
        return {
            'total_statements': "Unknown",
            'missing_statements': "Unknown",
            'coverage_percentage': "Unknown"
        }
        
    except Exception as e:
        print(f"   ❌ Error getting coverage: {e}")
        return {
            'total_statements': "ERROR",
            'missing_statements': "ERROR", 
            'coverage_percentage': "ERROR"
        }

def get_command_count():
    """Count actual commands registered in plugins."""
    print("\n🤖 Counting Commands...")
    
    command_count = 0
    plugin_files = glob.glob('larrybot/plugins/*.py')
    
    for file_path in plugin_files:
        if '__init__' in file_path:
            continue
            
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                # Count command_registry.register calls
                matches = re.findall(r'command_registry\.register\s*\(', content)
                file_commands = len(matches)
                command_count += file_commands
                
                if file_commands > 0:
                    print(f"   📁 {os.path.basename(file_path)}: {file_commands} commands")
                    
        except Exception as e:
            print(f"   ❌ Error reading {file_path}: {e}")
    
    print(f"   📊 Total Commands: {command_count}")
    return command_count

def get_plugin_count():
    """Count actual plugins."""
    print("\n🔌 Counting Plugins...")
    
    plugin_files = [f for f in glob.glob('larrybot/plugins/*.py') if '__init__' not in f]
    plugin_count = len(plugin_files)
    
    print("   📁 Active Plugins:")
    for plugin_file in sorted(plugin_files):
        plugin_name = os.path.basename(plugin_file).replace('.py', '')
        print(f"      • {plugin_name}")
    
    print(f"   📊 Total Plugins: {plugin_count}")
    return plugin_count

def get_documentation_files():
    """Count documentation files."""
    print("\n📚 Counting Documentation Files...")
    
    doc_files = glob.glob('docs/**/*.md', recursive=True)
    print(f"   📊 Documentation Files: {len(doc_files)}")
    return doc_files

def verify_documentation_accuracy():
    """Verify documentation accuracy against actual codebase."""
    print("🔍 Verifying Documentation Accuracy...")
    
    # Get actual statistics
    test_stats = get_test_statistics()
    coverage_stats = get_coverage_statistics()
    command_count = get_command_count()
    plugin_count = get_plugin_count()
    doc_files = get_documentation_files()
    
    # Check documentation files for accuracy
    errors = []
    
    for doc_file in doc_files:
        try:
            with open(doc_file, 'r') as f:
                content = f.read()
                
            # Check test count claims
            test_patterns = [
                r'(\d+)\s+tests?\s+passing',
                r'(\d+)\s+total\s+tests?',
                r'Tests?[:\s]*(\d+)'
            ]
            
            for pattern in test_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    doc_count = int(match)
                    if doc_count != test_stats['total_tests']:
                        errors.append(f"{doc_file}: Claims {doc_count} tests, actual is {test_stats['total_tests']}")
            
            # Check coverage claims
            coverage_patterns = [
                r'(\d+)%\s+coverage',
                r'coverage[:\s]*(\d+)%',
                r'(\d+)\s+statements?,\s*(\d+)\s+missing'
            ]
            
            for pattern in coverage_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        doc_coverage = int(match[0])
                        actual_coverage = int(coverage_stats['coverage_percentage'].rstrip('%'))
                        if doc_coverage != actual_coverage:
                            errors.append(f"{doc_file}: Claims {doc_coverage}% coverage, actual is {actual_coverage}%")
                    else:
                        doc_coverage = int(match)
                        actual_coverage = int(coverage_stats['coverage_percentage'].rstrip('%'))
                        if doc_coverage != actual_coverage:
                            errors.append(f"{doc_file}: Claims {doc_coverage}% coverage, actual is {actual_coverage}%")
            
            # Check command count claims
            command_patterns = [
                r'(\d+)\s+commands?',
                r'commands?[:\s]*(\d+)'
            ]
            
            for pattern in command_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    doc_count = int(match)
                    if doc_count != command_count:
                        errors.append(f"{doc_file}: Claims {doc_count} commands, actual is {command_count}")
            
            # Check plugin count claims
            plugin_patterns = [
                r'(\d+)\s+plugins?',
                r'plugins?[:\s]*(\d+)'
            ]
            
            for pattern in plugin_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    doc_count = int(match)
                    if doc_count != plugin_count:
                        errors.append(f"{doc_file}: Claims {doc_count} plugins, actual is {plugin_count}")
                        
        except Exception as e:
            print(f"   ⚠️  Error reading {doc_file}: {e}")
    
    return errors

def main():
    """Main verification function."""
    print("=" * 60)
    print("📋 LARRYBOT2 DOCUMENTATION ACCURACY VERIFICATION")
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Verify documentation accuracy
    errors = verify_documentation_accuracy()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    if errors:
        print(f"❌ {len(errors)} accuracy issues found:")
        for error in errors:
            print(f"   • {error}")
        print("\n⚠️  Documentation contains inaccuracies that must be corrected.")
        return 1
    else:
        print("✅ All documentation statistics appear accurate!")
        print("Documentation is ready for publication.")
        return 0

if __name__ == "__main__":
    exit(main()) 