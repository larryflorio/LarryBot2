"""
Automated Cache Management System for LarryBot2

This module provides intelligent cache invalidation based on operation types,
eliminating the need for manual cache_invalidate() calls throughout the codebase.
"""
import logging
import inspect
from typing import Dict, List, Set, Callable, Any, Optional
from functools import wraps
from enum import Enum
from dataclasses import dataclass
logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of operations that affect cached data."""
    TASK_CREATE = 'task_create'
    TASK_UPDATE = 'task_update'
    TASK_DELETE = 'task_delete'
    TASK_STATUS_CHANGE = 'task_status_change'
    TASK_PRIORITY_CHANGE = 'task_priority_change'
    TASK_CATEGORY_CHANGE = 'task_category_change'
    TASK_CLIENT_CHANGE = 'task_client_change'
    TASK_DUE_DATE_CHANGE = 'task_due_date_change'
    BULK_OPERATION = 'bulk_operation'
    CLIENT_CREATE = 'client_create'
    CLIENT_UPDATE = 'client_update'
    CLIENT_DELETE = 'client_delete'
    HABIT_CREATE = 'habit_create'
    HABIT_UPDATE = 'habit_update'
    HABIT_DELETE = 'habit_delete'
    REMINDER_CREATE = 'reminder_create'
    REMINDER_UPDATE = 'reminder_update'
    REMINDER_DELETE = 'reminder_delete'


@dataclass
class CacheInvalidationRule:
    """Rule for cache invalidation based on operation type."""
    operation_type: OperationType
    cache_patterns: List[str]
    conditional_patterns: Optional[Dict[str, List[str]]] = None
    description: str = ''


class AutomatedCacheManager:
    """
    Automated cache management system that intelligently invalidates
    related caches based on operation types.
    """

    def __init__(self):
        self._rules: Dict[OperationType, CacheInvalidationRule] = {}
        self._setup_default_rules()
        logger.info('AutomatedCacheManager initialized with default rules')

    def _setup_default_rules(self):
        """Setup default cache invalidation rules."""
        self.add_rule(CacheInvalidationRule(operation_type=OperationType.
            TASK_CREATE, cache_patterns=['list_incomplete_tasks',
            'task_statistics', 'analytics', 'get_tasks_by_priority',
            'get_tasks_by_category', 'get_all_categories'], description=
            'Invalidate task lists and statistics when creating tasks'))
        self.add_rule(CacheInvalidationRule(operation_type=OperationType.
            TASK_UPDATE, cache_patterns=['get_task_by_id',
            'list_incomplete_tasks'], description=
            'Invalidate task details when updating tasks'))
        self.add_rule(CacheInvalidationRule(operation_type=OperationType.
            TASK_DELETE, cache_patterns=['list_incomplete_tasks',
            'task_statistics', 'analytics', 'get_task_by_id',
            'get_tasks_by_priority', 'get_tasks_by_category',
            'get_tasks_by_status', 'get_tasks_by_client'], description=
            'Comprehensive cache invalidation for task deletion'))
        self.add_rule(CacheInvalidationRule(operation_type=OperationType.
            TASK_STATUS_CHANGE, cache_patterns=['get_task_by_id',
            'get_tasks_by_status', 'list_incomplete_tasks',
            'task_statistics', 'analytics'], description=
            'Invalidate status-related caches when task status changes'))
        self.add_rule(CacheInvalidationRule(operation_type=OperationType.
            TASK_PRIORITY_CHANGE, cache_patterns=['get_task_by_id',
            'get_tasks_by_priority'], description=
            'Invalidate priority-related caches when task priority changes'))
        self.add_rule(CacheInvalidationRule(operation_type=OperationType.
            TASK_CATEGORY_CHANGE, cache_patterns=['get_task_by_id',
            'get_tasks_by_category', 'get_all_categories'], description=
            'Invalidate category-related caches when task category changes'))
        self.add_rule(CacheInvalidationRule(operation_type=OperationType.
            TASK_CLIENT_CHANGE, cache_patterns=['get_task_by_id',
            'get_tasks_by_client'], description=
            'Invalidate client-related caches when task assignment changes'))
        self.add_rule(CacheInvalidationRule(operation_type=OperationType.
            TASK_DUE_DATE_CHANGE, cache_patterns=['get_task_by_id',
            'get_overdue_tasks', 'get_tasks_due_between', 'get_tasks_with_filters'], description=
            'Invalidate date-related caches when task due date changes'))
        self.add_rule(CacheInvalidationRule(operation_type=OperationType.
            BULK_OPERATION, cache_patterns=['get_tasks_by_status',
            'get_tasks_by_priority', 'get_tasks_by_category',
            'get_tasks_by_client', 'list_incomplete_tasks',
            'task_statistics', 'analytics'], description=
            'Comprehensive cache invalidation for bulk operations'))
        self.add_rule(CacheInvalidationRule(operation_type=OperationType.
            CLIENT_CREATE, cache_patterns=['get_all_clients'], description=
            'Invalidate client lists when creating clients'))
        self.add_rule(CacheInvalidationRule(operation_type=OperationType.
            CLIENT_UPDATE, cache_patterns=['get_all_clients',
            'get_client_by_name'], description=
            'Invalidate client data when updating clients'))
        self.add_rule(CacheInvalidationRule(operation_type=OperationType.
            CLIENT_DELETE, cache_patterns=['get_all_clients',
            'get_client_by_name', 'get_tasks_by_client'], description=
            'Invalidate client and related task data when deleting clients'))

    def add_rule(self, rule: CacheInvalidationRule):
        """Add a cache invalidation rule."""
        self._rules[rule.operation_type] = rule
        logger.debug(
            f'Added cache rule for {rule.operation_type.value}: {rule.description}'
            )

    def invalidate_for_operation(self, operation_type: OperationType,
        context: Optional[Dict[str, Any]]=None) ->int:
        """
        Automatically invalidate caches for a given operation type.
        
        Args:
            operation_type: The type of operation that occurred
            context: Optional context for conditional invalidation
            
        Returns:
            Number of cache patterns invalidated
        """
        rule = self._rules.get(operation_type)
        if not rule:
            logger.warning(
                f'No cache invalidation rule found for {operation_type.value}')
            return 0
        from larrybot.utils.caching import cache_invalidate
        invalidated_count = 0
        for pattern in rule.cache_patterns:
            count = cache_invalidate(pattern)
            invalidated_count += count
            if count > 0:
                logger.debug(
                    f"Invalidated {count} cache entries for pattern '{pattern}'"
                    )
        if rule.conditional_patterns and context:
            for condition, patterns in rule.conditional_patterns.items():
                if context.get(condition):
                    for pattern in patterns:
                        count = cache_invalidate(pattern)
                        invalidated_count += count
                        if count > 0:
                            logger.debug(
                                f"Conditionally invalidated {count} cache entries for pattern '{pattern}'"
                                )
        logger.info(
            f'Automated cache invalidation for {operation_type.value}: {invalidated_count} total entries invalidated'
            )
        return invalidated_count

    def get_rule(self, operation_type: OperationType) ->Optional[
        CacheInvalidationRule]:
        """Get the cache invalidation rule for an operation type."""
        return self._rules.get(operation_type)

    def list_rules(self) ->List[CacheInvalidationRule]:
        """List all cache invalidation rules."""
        return list(self._rules.values())


_automated_cache_manager = AutomatedCacheManager()


def auto_invalidate_cache(operation_type: OperationType, context: Optional[
    Dict[str, Any]]=None):
    """
    Decorator for automatic cache invalidation based on operation type.
    
    Usage:
        @auto_invalidate_cache(OperationType.TASK_CREATE)
        def add_task(self, description: str) -> Task:
            # Implementation
            return task
    """

    def decorator(func: Callable) ->Callable:

        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            try:
                _automated_cache_manager.invalidate_for_operation(
                    operation_type, context)
            except Exception as e:
                logger.error(
                    f'Error in automatic cache invalidation for {operation_type.value}: {e}'
                    )
            return result
        return wrapper
    return decorator


def invalidate_caches_for(operation_type: OperationType, context: Optional[
    Dict[str, Any]]=None) ->int:
    """
    Manually trigger cache invalidation for an operation type.
    
    Args:
        operation_type: The type of operation that occurred
        context: Optional context for conditional invalidation
        
    Returns:
        Number of cache patterns invalidated
    """
    return _automated_cache_manager.invalidate_for_operation(operation_type,
        context)


def get_cache_manager() ->AutomatedCacheManager:
    """Get the global automated cache manager instance."""
    return _automated_cache_manager


def add_custom_rule(rule: CacheInvalidationRule):
    """Add a custom cache invalidation rule."""
    _automated_cache_manager.add_rule(rule)


def invalidate_task_caches():
    """Invalidate all task-related caches."""
    return invalidate_caches_for(OperationType.TASK_UPDATE)


def invalidate_analytics_caches():
    """Invalidate analytics caches."""
    from larrybot.utils.caching import cache_invalidate
    return cache_invalidate('analytics')


def invalidate_all_task_lists():
    """Invalidate all task list caches."""
    from larrybot.utils.caching import cache_invalidate
    patterns = ['list_incomplete_tasks', 'get_tasks_by_status',
        'get_tasks_by_priority', 'get_tasks_by_category', 'get_tasks_by_client'
        ]
    total = 0
    for pattern in patterns:
        total += cache_invalidate(pattern)
    return total
