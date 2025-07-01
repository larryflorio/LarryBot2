#!/usr/bin/env python3
"""
Command Redundancy Analysis and Consolidation Recommendations for LarryBot2

This script analyzes the current command structure, identifies redundancies,
and provides specific consolidation recommendations while maintaining all functionality.
"""

import sys
import os
import re
import glob
from collections import defaultdict
from typing import Dict, List, Tuple, Set

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def extract_commands_from_file(file_path: str) -> List[Dict]:
    """Extract command information from a Python file."""
    commands = []
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Method 1: Find command_registry.register calls
        register_pattern = r'command_registry\.register\s*\(\s*["\']([^"\']+)["\'],\s*([^,\)]+)'
        for match in re.finditer(register_pattern, content):
            command = match.group(1)
            handler = match.group(2).strip()
            
            commands.append({
                'command': command,
                'handler': handler,
                'file': os.path.basename(file_path),
                'registration_method': 'direct_register'
            })
        
        # Method 2: Find @command_handler decorators
        decorator_pattern = r'@command_handler\s*\(\s*["\']([^"\']+)["\'],\s*["\']([^"\']*)["\'],\s*["\']([^"\']*)["\'],\s*["\']([^"\']*)["\']'
        for match in re.finditer(decorator_pattern, content):
            command = match.group(1)
            description = match.group(2)
            usage = match.group(3)
            category = match.group(4)
            
            # Find the function name after the decorator
            func_match = re.search(r'@command_handler.*?\n\s*(?:@[^\n]*\n\s*)*async\s+def\s+(\w+)', content[match.end():], re.DOTALL)
            handler = func_match.group(1) if func_match else 'unknown_handler'
            
            commands.append({
                'command': command,
                'handler': handler,
                'file': os.path.basename(file_path),
                'description': description,
                'usage': usage,
                'category': category,
                'registration_method': 'decorator'
            })
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return commands

def analyze_command_redundancies() -> Dict:
    """Analyze all commands and identify redundancies."""
    print("🔍 Analyzing Command Structure...")
    
    # Get all Python files in plugins and handlers
    plugin_files = glob.glob('larrybot/plugins/*.py')
    handler_files = glob.glob('larrybot/handlers/*.py')
    
    all_commands = []
    file_command_counts = {}
    
    # Process all files
    for file_path in plugin_files + handler_files:
        if '__init__' in file_path:
            continue
            
        commands = extract_commands_from_file(file_path)
        all_commands.extend(commands)
        
        if commands:
            file_command_counts[os.path.basename(file_path)] = len(commands)
            print(f"   📁 {os.path.basename(file_path)}: {len(commands)} commands")
    
    print(f"\n📊 Total Commands Found: {len(all_commands)}")
    
    # Group commands by similarity and identify redundancies
    redundancies = identify_redundancies(all_commands)
    
    return {
        'total_commands': len(all_commands),
        'all_commands': all_commands,
        'file_counts': file_command_counts,
        'redundancies': redundancies
    }

def identify_redundancies(commands: List[Dict]) -> Dict:
    """Identify redundant command patterns."""
    redundancies = {
        'task_creation': [],
        'task_listing': [],
        'search_commands': [],
        'analytics_hierarchy': [],
        'namespace_conflicts': [],
        'similar_functionality': []
    }
    
    # Group commands by name patterns
    command_groups = defaultdict(list)
    for cmd in commands:
        command_groups[cmd['command']].append(cmd)
    
    # Task creation redundancy
    add_commands = [cmd for cmd in commands if cmd['command'] in ['/add', '/addtask']]
    if len(add_commands) >= 2:
        redundancies['task_creation'] = add_commands
    
    # Task listing redundancy  
    list_commands = [cmd for cmd in commands if cmd['command'] in ['/list', '/tasks']]
    if len(list_commands) >= 2:
        redundancies['task_listing'] = list_commands
    
    # Search redundancy
    search_commands = [cmd for cmd in commands if cmd['command'] in ['/search', '/search_advanced']]
    if len(search_commands) >= 2:
        redundancies['search_commands'] = search_commands
    
    # Analytics hierarchy
    analytics_commands = [cmd for cmd in commands if '/analytics' in cmd['command']]
    if len(analytics_commands) >= 2:
        redundancies['analytics_hierarchy'] = analytics_commands
    
    # Namespace conflicts (multiple commands with same name)
    for cmd_name, cmd_list in command_groups.items():
        if len(cmd_list) > 1:
            redundancies['namespace_conflicts'].extend(cmd_list)
    
    # Similar functionality patterns
    bulk_commands = [cmd for cmd in commands if cmd['command'].startswith('/bulk_')]
    if len(bulk_commands) >= 3:  # If 3+ bulk commands, suggest consolidation
        redundancies['similar_functionality'].extend(bulk_commands)
    
    return redundancies

def generate_consolidation_plan(analysis: Dict) -> Dict:
    """Generate specific consolidation recommendations."""
    print("\n🎯 Generating Consolidation Plan...")
    
    plan = {
        'high_priority_mergers': [],
        'medium_priority_optimizations': [],
        'namespace_resolutions': [],
        'command_hierarchies': [],
        'estimated_reduction': 0
    }
    
    redundancies = analysis['redundancies']
    
    # High Priority: Task Creation Consolidation
    if redundancies['task_creation']:
        plan['high_priority_mergers'].append({
            'type': 'task_creation_merge',
            'commands_to_merge': ['/add', '/addtask'],
            'target_command': '/add',
            'strategy': 'enhance_basic_with_optional_params',
            'description': 'Merge /add + /addtask → Enhanced /add with optional metadata',
            'implementation': 'Add optional parameters: priority, due_date, category to /add',
            'backward_compatibility': 'Full - existing /add usage remains unchanged',
            'estimated_savings': 1
        })
    
    # High Priority: Task Listing Consolidation  
    if redundancies['task_listing']:
        plan['high_priority_mergers'].append({
            'type': 'task_listing_merge', 
            'commands_to_merge': ['/list', '/tasks'],
            'target_command': '/list',
            'strategy': 'enhance_basic_with_filtering',
            'description': 'Merge /list + /tasks → Enhanced /list with optional filters',
            'implementation': 'Add optional parameters: status, priority, category filters to /list',
            'backward_compatibility': 'Full - existing /list behavior as default',
            'estimated_savings': 1
        })
    
    # High Priority: Search Consolidation
    if redundancies['search_commands']:
        plan['high_priority_mergers'].append({
            'type': 'search_merge',
            'commands_to_merge': ['/search', '/search_advanced'], 
            'target_command': '/search',
            'strategy': 'enhance_basic_with_advanced_features',
            'description': 'Merge /search + /search_advanced → Enhanced /search',
            'implementation': 'Add optional advanced search flags to /search',
            'backward_compatibility': 'Full - basic search as default behavior',
            'estimated_savings': 1
        })
    
    # Medium Priority: Analytics Hierarchy
    if redundancies['analytics_hierarchy']:
        plan['command_hierarchies'].append({
            'type': 'analytics_streamlining',
            'commands': [cmd['command'] for cmd in redundancies['analytics_hierarchy']],
            'strategy': 'unified_command_with_complexity_levels',
            'description': 'Create /analytics [basic|detailed|advanced] [days] hierarchy',
            'implementation': 'Single command with optional complexity and time parameters',
            'estimated_savings': 2  # Keep one, remove 2 others
        })
    
    # Namespace Conflict Resolution
    start_conflicts = [cmd for cmd in redundancies['namespace_conflicts'] if cmd['command'] == '/start']
    if len(start_conflicts) > 1:
        plan['namespace_resolutions'].append({
            'type': 'start_command_conflict',
            'conflict_commands': start_conflicts,
            'resolution': 'Rename time tracking /start to /time_start',
            'rationale': 'Bot /start command takes precedence as core functionality',
            'estimated_savings': 0  # Rename, not removal
        })
    
    # Calculate total estimated reduction
    total_savings = (
        sum(item['estimated_savings'] for item in plan['high_priority_mergers']) +
        sum(item['estimated_savings'] for item in plan['command_hierarchies']) +
        len([item for item in plan['medium_priority_optimizations']])
    )
    
    plan['estimated_reduction'] = total_savings
    plan['target_command_count'] = analysis['total_commands'] - total_savings
    
    return plan

def print_detailed_analysis(analysis: Dict, plan: Dict):
    """Print comprehensive analysis and recommendations."""
    print("\n" + "="*80)
    print("📋 LARRYBOT2 COMMAND REDUNDANCY ANALYSIS REPORT")
    print("="*80)
    
    print(f"\n📊 CURRENT STATE:")
    print(f"   • Total Commands: {analysis['total_commands']}")
    print(f"   • Plugin Files: {len(analysis['file_counts'])}")
    print(f"   • Commands per file:")
    for file, count in sorted(analysis['file_counts'].items(), key=lambda x: x[1], reverse=True):
        print(f"     - {file}: {count} commands")
    
    print(f"\n🔍 REDUNDANCY ANALYSIS:")
    redundancies = analysis['redundancies']
    
    if redundancies['task_creation']:
        print(f"\n   📝 Task Creation Redundancy:")
        for cmd in redundancies['task_creation']:
            print(f"     • {cmd['command']} ({cmd['file']}) - {cmd.get('description', 'Basic task creation')}")
    
    if redundancies['task_listing']:
        print(f"\n   📋 Task Listing Redundancy:")
        for cmd in redundancies['task_listing']:
            print(f"     • {cmd['command']} ({cmd['file']}) - {cmd.get('description', 'Task listing')}")
    
    if redundancies['search_commands']:
        print(f"\n   🔍 Search Command Redundancy:")
        for cmd in redundancies['search_commands']:
            print(f"     • {cmd['command']} ({cmd['file']}) - {cmd.get('description', 'Search functionality')}")
    
    if redundancies['analytics_hierarchy']:
        print(f"\n   📈 Analytics Command Hierarchy:")
        for cmd in redundancies['analytics_hierarchy']:
            print(f"     • {cmd['command']} ({cmd['file']}) - {cmd.get('description', 'Analytics functionality')}")
    
    if redundancies['namespace_conflicts']:
        print(f"\n   ⚠️  Namespace Conflicts:")
        conflicts = defaultdict(list)
        for cmd in redundancies['namespace_conflicts']:
            conflicts[cmd['command']].append(cmd)
        for cmd_name, cmd_list in conflicts.items():
            if len(cmd_list) > 1:
                print(f"     • {cmd_name}:")
                for cmd in cmd_list:
                    print(f"       - {cmd['file']}: {cmd.get('description', 'No description')}")
    
    print(f"\n🎯 CONSOLIDATION PLAN:")
    print(f"   • Estimated Reduction: {plan['estimated_reduction']} commands")
    print(f"   • Target Command Count: {plan['target_command_count']} (from {analysis['total_commands']})")
    print(f"   • Reduction Percentage: {(plan['estimated_reduction']/analysis['total_commands']*100):.1f}%")
    
    print(f"\n🔥 HIGH PRIORITY MERGERS:")
    for merger in plan['high_priority_mergers']:
        print(f"\n   📌 {merger['type'].replace('_', ' ').title()}:")
        print(f"      • Commands: {' + '.join(merger['commands_to_merge'])} → {merger['target_command']}")
        print(f"      • Strategy: {merger['strategy']}")
        print(f"      • Description: {merger['description']}")
        print(f"      • Implementation: {merger['implementation']}")
        print(f"      • Compatibility: {merger['backward_compatibility']}")
        print(f"      • Savings: {merger['estimated_savings']} command(s)")
    
    if plan['command_hierarchies']:
        print(f"\n📊 COMMAND HIERARCHIES:")
        for hierarchy in plan['command_hierarchies']:
            print(f"\n   📌 {hierarchy['type'].replace('_', ' ').title()}:")
            print(f"      • Commands: {hierarchy['commands']}")
            print(f"      • Strategy: {hierarchy['strategy']}")
            print(f"      • Description: {hierarchy['description']}")
            print(f"      • Savings: {hierarchy['estimated_savings']} command(s)")
    
    if plan['namespace_resolutions']:
        print(f"\n🔧 NAMESPACE RESOLUTIONS:")
        for resolution in plan['namespace_resolutions']:
            print(f"\n   📌 {resolution['type'].replace('_', ' ').title()}:")
            print(f"      • Resolution: {resolution['resolution']}")
            print(f"      • Rationale: {resolution['rationale']}")

def generate_implementation_guide(plan: Dict):
    """Generate step-by-step implementation guide."""
    print(f"\n🛠️  IMPLEMENTATION GUIDE:")
    print("="*50)
    
    print("\n📋 PHASE 1: High Priority Mergers")
    for i, merger in enumerate(plan['high_priority_mergers'], 1):
        print(f"\n{i}. {merger['type'].replace('_', ' ').title()}")
        print(f"   Target: {merger['target_command']}")
        print(f"   Action: {merger['implementation']}")
        
        if merger['type'] == 'task_creation_merge':
            print(f"   Steps:")
            print(f"     a) Enhance /add handler to accept optional parameters")
            print(f"     b) Update argument parsing: /add <desc> [priority] [due_date] [category]")
            print(f"     c) Maintain existing /add behavior for single argument")
            print(f"     d) Add validation for new optional parameters")
            print(f"     e) Update tests to cover new functionality")
            print(f"     f) Mark /addtask as deprecated (redirect to /add)")
        
        elif merger['type'] == 'task_listing_merge':
            print(f"   Steps:")
            print(f"     a) Enhance /list handler to accept optional filters")
            print(f"     b) Update argument parsing: /list [status] [priority] [category]")
            print(f"     c) Maintain existing /list behavior with no arguments")
            print(f"     d) Add filtering logic from /tasks command")
            print(f"     e) Update keyboard interactions")
            print(f"     f) Mark /tasks as deprecated (redirect to /list)")
        
        elif merger['type'] == 'search_merge':
            print(f"   Steps:")
            print(f"     a) Enhance /search handler with advanced features")
            print(f"     b) Add optional flags for advanced search modes")
            print(f"     c) Maintain simple text search as default")
            print(f"     d) Integrate advanced search functionality")
            print(f"     e) Update help text and usage examples")
            print(f"     f) Mark /search_advanced as deprecated")
    
    print(f"\n📋 PHASE 2: Namespace Resolutions")
    for resolution in plan['namespace_resolutions']:
        if resolution['type'] == 'start_command_conflict':
            print(f"   • Rename time tracking /start to /time_start")
            print(f"   • Update all references in advanced_tasks.py")
            print(f"   • Update command registration")
            print(f"   • Update documentation and help text")
    
    print(f"\n📋 PHASE 3: Testing and Validation")
    print(f"   • Run full test suite before changes")
    print(f"   • Test each consolidated command thoroughly")
    print(f"   • Verify backward compatibility")
    print(f"   • Update documentation")
    print(f"   • Run final test suite validation")

if __name__ == "__main__":
    print("🚀 Starting Command Redundancy Analysis...")
    
    # Change to project root directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Run analysis
    analysis = analyze_command_redundancies()
    plan = generate_consolidation_plan(analysis)
    
    # Print results
    print_detailed_analysis(analysis, plan)
    generate_implementation_guide(plan)
    
    print(f"\n✅ Analysis Complete!")
    print(f"📊 Current: {analysis['total_commands']} commands")
    print(f"🎯 Target: {plan['target_command_count']} commands") 
    print(f"📉 Reduction: {plan['estimated_reduction']} commands ({(plan['estimated_reduction']/analysis['total_commands']*100):.1f}%)") 