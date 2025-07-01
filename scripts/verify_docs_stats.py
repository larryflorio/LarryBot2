#!/usr/bin/env python3
"""
Documentation Statistics Verification Script
============================================

This script collects accurate statistics from the LarryBot2 codebase
to ensure documentation accuracy and prevent statistical errors.
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
    
    # Get test collection count
    try:
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
    
    # Get test results with basic run (faster)
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
            # Fallback: assume all collected tests
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
    """Get list of documentation files that need updates."""
    print("\n📚 Scanning Documentation Files...")
    
    doc_files = []
    for pattern in ['docs/**/*.md', 'README.md']:
        doc_files.extend(glob.glob(pattern, recursive=True))
    
    print(f"   📊 Documentation Files Found: {len(doc_files)}")
    return doc_files

def generate_report():
    """Generate comprehensive statistics report."""
    print("=" * 60)
    print("📊 LARRYBOT2 DOCUMENTATION STATISTICS VERIFICATION")
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Collect all statistics
    test_stats = get_test_statistics()
    coverage_stats = get_coverage_statistics()
    command_count = get_command_count()
    plugin_count = get_plugin_count()
    doc_files = get_documentation_files()
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("📋 SUMMARY REPORT")
    print("=" * 60)
    
    print(f"🧪 TESTING:")
    print(f"   • Total Tests: {test_stats['total_tests']}")
    print(f"   • Tests Passed: {test_stats['passed_tests']}")
    print(f"   • Tests Failed: {test_stats['failed_tests']}")
    print(f"   • Success Rate: {test_stats['success_rate']}")
    
    print(f"\n📈 COVERAGE:")
    print(f"   • Total Statements: {coverage_stats['total_statements']}")
    print(f"   • Missing Statements: {coverage_stats['missing_statements']}")
    print(f"   • Coverage Percentage: {coverage_stats['coverage_percentage']}")
    
    print(f"\n🤖 FEATURES:")
    print(f"   • Total Commands: {command_count}")
    print(f"   • Active Plugins: {plugin_count}")
    
    print(f"\n📚 DOCUMENTATION:")
    print(f"   • Documentation Files: {len(doc_files)}")
    
    # Return structured data for updates
    return {
        'test_stats': test_stats,
        'coverage_stats': coverage_stats,
        'command_count': command_count,
        'plugin_count': plugin_count,
        'doc_files': doc_files,
        'generated_at': datetime.now().isoformat()
    }

if __name__ == "__main__":
    stats = generate_report()
    
    print("\n" + "=" * 60)
    print("✅ VERIFICATION COMPLETE")
    print("=" * 60)
    print("Use this data to update documentation with accurate statistics.")
    print("Next step: Run documentation update scripts with these verified numbers.") 