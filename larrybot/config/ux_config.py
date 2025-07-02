"""
UX Configuration for LarryBot2

This module provides configuration settings for enhanced UX features.
"""

from typing import Dict, Any


class UXConfig:
    """Configuration for UX features."""
    
    # Visual preferences
    ENABLE_PROGRESSIVE_DISCLOSURE = True
    ENABLE_SMART_NAVIGATION = True
    ENABLE_ENHANCED_FEEDBACK = True
    ENABLE_ERROR_RECOVERY = True
    
    # Layout settings
    MAX_ITEMS_PER_PAGE = 10
    ENABLE_BREADCRUMBS = True
    ENABLE_STATUS_INDICATORS = True
    
    # Message formatting
    ENABLE_ENHANCED_LAYOUTS = True
    ENABLE_INFO_CARDS = True
    ENABLE_PROGRESSIVE_LISTS = True
    
    # Navigation settings
    ENABLE_CONTEXTUAL_KEYBOARDS = True
    ENABLE_QUICK_ACTIONS = True
    MAX_BUTTONS_PER_ROW = 3
    
    # Error handling
    ENABLE_ERROR_RECOVERY_SUGGESTIONS = True
    ENABLE_CONTEXTUAL_HELP = True
    ENABLE_ALTERNATIVE_SUGGESTIONS = True
    
    # Visual feedback
    ENABLE_LOADING_INDICATORS = True
    ENABLE_SUCCESS_ANIMATIONS = True
    ENABLE_PROGRESS_BARS = True
    ENABLE_ENHANCED_CONFIRMATIONS = True
    
    # Performance settings
    ENABLE_LAZY_LOADING = True
    CACHE_NAVIGATION_STATES = True
    MAX_CACHE_SIZE = 100
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration settings as a dictionary."""
        return {
            'progressive_disclosure': cls.ENABLE_PROGRESSIVE_DISCLOSURE,
            'smart_navigation': cls.ENABLE_SMART_NAVIGATION,
            'enhanced_feedback': cls.ENABLE_ENHANCED_FEEDBACK,
            'error_recovery': cls.ENABLE_ERROR_RECOVERY,
            'max_items_per_page': cls.MAX_ITEMS_PER_PAGE,
            'enable_breadcrumbs': cls.ENABLE_BREADCRUMBS,
            'enable_status_indicators': cls.ENABLE_STATUS_INDICATORS,
            'enhanced_layouts': cls.ENABLE_ENHANCED_LAYOUTS,
            'info_cards': cls.ENABLE_INFO_CARDS,
            'progressive_lists': cls.ENABLE_PROGRESSIVE_LISTS,
            'contextual_keyboards': cls.ENABLE_CONTEXTUAL_KEYBOARDS,
            'quick_actions': cls.ENABLE_QUICK_ACTIONS,
            'max_buttons_per_row': cls.MAX_BUTTONS_PER_ROW,
            'error_recovery_suggestions': cls.ENABLE_ERROR_RECOVERY_SUGGESTIONS,
            'contextual_help': cls.ENABLE_CONTEXTUAL_HELP,
            'alternative_suggestions': cls.ENABLE_ALTERNATIVE_SUGGESTIONS,
            'loading_indicators': cls.ENABLE_LOADING_INDICATORS,
            'success_animations': cls.ENABLE_SUCCESS_ANIMATIONS,
            'progress_bars': cls.ENABLE_PROGRESS_BARS,
            'enhanced_confirmations': cls.ENABLE_ENHANCED_CONFIRMATIONS,
            'lazy_loading': cls.ENABLE_LAZY_LOADING,
            'cache_navigation_states': cls.CACHE_NAVIGATION_STATES,
            'max_cache_size': cls.MAX_CACHE_SIZE
        }
    
    @classmethod
    def is_feature_enabled(cls, feature_name: str) -> bool:
        """Check if a specific feature is enabled."""
        feature_map = {
            'progressive_disclosure': cls.ENABLE_PROGRESSIVE_DISCLOSURE,
            'smart_navigation': cls.ENABLE_SMART_NAVIGATION,
            'enhanced_feedback': cls.ENABLE_ENHANCED_FEEDBACK,
            'error_recovery': cls.ENABLE_ERROR_RECOVERY,
            'breadcrumbs': cls.ENABLE_BREADCRUMBS,
            'status_indicators': cls.ENABLE_STATUS_INDICATORS,
            'enhanced_layouts': cls.ENABLE_ENHANCED_LAYOUTS,
            'info_cards': cls.ENABLE_INFO_CARDS,
            'progressive_lists': cls.ENABLE_PROGRESSIVE_LISTS,
            'contextual_keyboards': cls.ENABLE_CONTEXTUAL_KEYBOARDS,
            'quick_actions': cls.ENABLE_QUICK_ACTIONS,
            'error_recovery_suggestions': cls.ENABLE_ERROR_RECOVERY_SUGGESTIONS,
            'contextual_help': cls.ENABLE_CONTEXTUAL_HELP,
            'alternative_suggestions': cls.ENABLE_ALTERNATIVE_SUGGESTIONS,
            'loading_indicators': cls.ENABLE_LOADING_INDICATORS,
            'success_animations': cls.ENABLE_SUCCESS_ANIMATIONS,
            'progress_bars': cls.ENABLE_PROGRESS_BARS,
            'enhanced_confirmations': cls.ENABLE_ENHANCED_CONFIRMATIONS,
            'lazy_loading': cls.ENABLE_LAZY_LOADING,
            'cache_navigation_states': cls.CACHE_NAVIGATION_STATES
        }
        
        return feature_map.get(feature_name, False) 