#!/usr/bin/env python3
"""
Test script to demonstrate natural language date parsing in LarryBot2.

This script shows how the enhanced DateTimeService can parse both
structured (YYYY-MM-DD) and natural language date inputs.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from larrybot.services.datetime_service import DateTimeService
from datetime import datetime


def test_natural_language_parsing():
    """Test various natural language date inputs."""
    print("🧪 Testing Natural Language Date Parsing")
    print("=" * 50)
    
    # Test cases with expected results
    test_cases = [
        # Natural language inputs
        ("Monday", "Day of week"),
        ("tomorrow", "Relative day"),
        ("next week", "Relative week"),
        ("in 3 days", "Relative days"),
        ("next month", "Relative month"),
        ("this weekend", "Relative period"),
        
        # Structured inputs (should still work)
        ("2025-07-15", "Structured date"),
        ("2025-12-31", "Year boundary"),
        
        # Edge cases
        ("invalid date", "Invalid input"),
        ("", "Empty input"),
        ("  2025-07-15  ", "Whitespace input"),
    ]
    
    for date_input, description in test_cases:
        print(f"\n📅 Testing: '{date_input}' ({description})")
        
        # Test with NLP enabled
        result_nlp = DateTimeService.parse_user_date(date_input, use_nlp=True)
        if result_nlp:
            print(f"   ✅ NLP Enabled: {result_nlp.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"   ❌ NLP Enabled: Failed to parse")
        
        # Test with NLP disabled
        result_no_nlp = DateTimeService.parse_user_date(date_input, use_nlp=False)
        if result_no_nlp:
            print(f"   ✅ NLP Disabled: {result_no_nlp.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"   ❌ NLP Disabled: Failed to parse")


def test_performance_comparison():
    """Compare performance of structured vs natural language parsing."""
    print("\n\n⚡ Performance Comparison")
    print("=" * 50)
    
    import time
    
    # Test structured parsing performance
    start_time = time.time()
    for _ in range(1000):
        DateTimeService.parse_user_date("2025-07-15", use_nlp=False)
    structured_time = time.time() - start_time
    
    # Test natural language parsing performance
    start_time = time.time()
    for _ in range(1000):
        DateTimeService.parse_user_date("Monday", use_nlp=True)
    nlp_time = time.time() - start_time
    
    print(f"📊 Structured parsing (1000 iterations): {structured_time:.4f}s")
    print(f"📊 NLP parsing (1000 iterations): {nlp_time:.4f}s")
    print(f"📊 Performance ratio: {nlp_time/structured_time:.2f}x slower")


def test_error_handling():
    """Test error handling for various edge cases."""
    print("\n\n🛡️ Error Handling Tests")
    print("=" * 50)
    
    edge_cases = [
        None,
        "",
        "   ",
        "invalid-date-string",
        "2025-13-01",  # Invalid month
        "2025-02-30",  # Invalid day for February
        "not-a-date-at-all",
    ]
    
    for case in edge_cases:
        print(f"\n🔍 Testing: {repr(case)}")
        try:
            result = DateTimeService.parse_user_date(case)
            if result:
                print(f"   ✅ Result: {result.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"   ❌ Result: None (expected)")
        except Exception as e:
            print(f"   💥 Exception: {e}")


def main():
    """Run all tests."""
    print("🚀 LarryBot2 Natural Language Date Parsing Demo")
    print("=" * 60)
    
    test_natural_language_parsing()
    test_performance_comparison()
    test_error_handling()
    
    print("\n\n✅ Demo completed successfully!")
    print("\n💡 Key Features:")
    print("   • Supports both structured (YYYY-MM-DD) and natural language")
    print("   • Graceful fallback from structured to NLP parsing")
    print("   • Configurable NLP usage with use_nlp parameter")
    print("   • Consistent timezone-aware datetime output")
    print("   • Robust error handling")


if __name__ == "__main__":
    main() 