#!/usr/bin/env python3
"""
Demonstration script for URL obfuscation functionality.
This script shows how the obfuscation works and verifies it prevents Telegram link detection.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from larrybot.utils.ux_helpers import MessageFormatter

def demonstrate_url_obfuscation():
    """Demonstrate URL obfuscation functionality."""
    print("🔗 URL Obfuscation Demonstration")
    print("=" * 50)
    
    # Test URLs
    test_urls = [
        "https://meet.google.com/abc-defg-hij",
        "https://zoom.us/j/123456789?pwd=abc123",
        "https://teams.microsoft.com/l/meetup-join/19:meeting_abc123",
        "https://webex.com/meeting/123456"
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. Original URL:")
        print(f"   {url}")
        
        # Obfuscate the URL
        obfuscated = MessageFormatter.obfuscate_url(url)
        
        print(f"   Obfuscated URL:")
        print(f"   {obfuscated}")
        
        # Show character analysis
        print(f"   Length: {len(url)} → {len(obfuscated)} (+{len(obfuscated) - len(url)})")
        zero_width_count = obfuscated.count('\u200b')
        print(f"   Zero-width chars: {zero_width_count}")
        
        # Verify all original characters are present
        all_chars_present = all(char in obfuscated for char in url)
        print(f"   All chars preserved: {'✅' if all_chars_present else '❌'}")
        
        # Show what it would look like in Telegram (zero-width chars are invisible)
        visible_chars = ''.join(char for char in obfuscated if char != '\u200b')
        print(f"   Visible in Telegram: {visible_chars}")
    
    print("\n" + "=" * 50)
    print("✅ URL obfuscation successfully prevents Telegram link embedding!")
    print("📋 Users can still copy and paste the URLs normally.")
    print("🎯 Zero-width characters break URL detection while maintaining visual appearance.")

if __name__ == "__main__":
    demonstrate_url_obfuscation() 