"""
Enhanced Enum Types for LarryBot2 Phase 2 Type Safety

This module provides strongly-typed enums for better type safety, validation,
and enterprise-grade data consistency across the application.
"""
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Any


class TaskStatus(Enum):
    """Enhanced task status with comprehensive functionality."""
    TODO = 'Todo'
    IN_PROGRESS = 'In Progress'
    REVIEW = 'Review'
    DONE = 'Done'
    BLOCKED = 'Blocked'
    CANCELLED = 'Cancelled'

    def __str__(self) ->str:
        return self.value

    @property
    def is_active(self) ->bool:
        """Check if status represents an active task."""
        return self in {TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus
            .REVIEW}

    @property
    def is_completed(self) ->bool:
        """Check if status represents a completed task."""
        return self in {TaskStatus.DONE, TaskStatus.CANCELLED}

    @property
    def can_transition_to(self) ->List['TaskStatus']:
        """Get valid status transitions from current status."""
        transitions = {TaskStatus.TODO: [TaskStatus.IN_PROGRESS, TaskStatus
            .BLOCKED, TaskStatus.CANCELLED], TaskStatus.IN_PROGRESS: [
            TaskStatus.REVIEW, TaskStatus.DONE, TaskStatus.BLOCKED,
            TaskStatus.TODO], TaskStatus.REVIEW: [TaskStatus.DONE,
            TaskStatus.IN_PROGRESS, TaskStatus.TODO], TaskStatus.BLOCKED: [
            TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
            TaskStatus.DONE: [TaskStatus.IN_PROGRESS], TaskStatus.CANCELLED:
            [TaskStatus.TODO]}
        return transitions.get(self, [])

    @property
    def color_code(self) ->str:
        """Get color code for UI display."""
        colors = {TaskStatus.TODO: '🔵', TaskStatus.IN_PROGRESS: '🟡',
            TaskStatus.REVIEW: '🟠', TaskStatus.DONE: '🟢', TaskStatus.
            BLOCKED: '🔴', TaskStatus.CANCELLED: '⚫'}
        return colors.get(self, '⚪')

    @classmethod
    def from_string(cls, status_str: str) ->Optional['TaskStatus']:
        """Create TaskStatus from string, case-insensitive."""
        if isinstance(status_str, cls):
            return status_str
        if not isinstance(status_str, str):
            return None
        for status in cls:
            if status.value.lower() == status_str.lower():
                return status
        return None

    @classmethod
    def get_display_options(cls) ->Dict[str, str]:
        """Get status options for UI display."""
        return {status.value: f'{status.color_code} {status.value}' for
            status in cls}


class TaskPriority(IntEnum):
    """Enhanced task priority with comprehensive functionality and ordering."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    URGENT = 5

    def __str__(self) ->str:
        return self.name.title()

    @property
    def weight(self) ->int:
        """Get numeric weight for sorting and calculations."""
        return self.value

    @property
    def description(self) ->str:
        """Get human-readable description."""
        descriptions = {TaskPriority.LOW:
            'Low priority - can be done when time permits', TaskPriority.
            MEDIUM: 'Medium priority - normal workflow item', TaskPriority.
            HIGH: 'High priority - should be completed soon', TaskPriority.
            CRITICAL: 'Critical priority - needs immediate attention',
            TaskPriority.URGENT: 'Urgent priority - drop everything else'}
        return descriptions[self]

    @property
    def color_code(self) ->str:
        """Get color code for UI display."""
        colors = {TaskPriority.LOW: '🟢', TaskPriority.MEDIUM: '🟡',
            TaskPriority.HIGH: '🟠', TaskPriority.CRITICAL: '🔴',
            TaskPriority.URGENT: '🚨'}
        return colors[self]

    @property
    def sla_hours(self) ->Optional[int]:
        """Get SLA hours for priority level."""
        sla_mapping = {TaskPriority.LOW: None, TaskPriority.MEDIUM: 72,
            TaskPriority.HIGH: 24, TaskPriority.CRITICAL: 4, TaskPriority.
            URGENT: 1}
        return sla_mapping[self]

    @classmethod
    def from_string(cls, priority_str: str) ->Optional['TaskPriority']:
        """Create TaskPriority from string, case-insensitive."""
        try:
            return cls[priority_str.upper()]
        except KeyError:
            for priority in cls:
                if priority.name.lower() == priority_str.lower():
                    return priority
            return None

    @classmethod
    def get_display_options(cls) ->Dict[str, str]:
        """Get priority options for UI display."""
        return {priority.name:
            f'{priority.color_code} {priority.name.title()}' for priority in
            cls}

    def compare_urgency(self, other: 'TaskPriority') ->int:
        """Compare urgency with another priority. Returns -1, 0, or 1."""
        if self.value > other.value:
            return 1
        elif self.value < other.value:
            return -1
        return 0


class ReminderType(Enum):
    """Enhanced reminder types with functionality."""
    ONCE = 'once'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    YEARLY = 'yearly'
    CUSTOM = 'custom'

    def __str__(self) ->str:
        return self.value.title()

    @property
    def is_recurring(self) ->bool:
        """Check if reminder type is recurring."""
        return self != ReminderType.ONCE

    @property
    def description(self) ->str:
        """Get human-readable description."""
        descriptions = {ReminderType.ONCE: 'One-time reminder',
            ReminderType.DAILY: 'Repeats every day', ReminderType.WEEKLY:
            'Repeats every week', ReminderType.MONTHLY:
            'Repeats every month', ReminderType.YEARLY:
            'Repeats every year', ReminderType.CUSTOM: 'Custom repeat pattern'}
        return descriptions[self]


class ClientStatus(Enum):
    """Client relationship status."""
    PROSPECT = 'prospect'
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    ARCHIVED = 'archived'

    def __str__(self) ->str:
        return self.value.title()

    @property
    def is_billable(self) ->bool:
        """Check if client status allows billing."""
        return self in {ClientStatus.ACTIVE}

    @property
    def color_code(self) ->str:
        """Get color code for UI display."""
        colors = {ClientStatus.PROSPECT: '🟡', ClientStatus.ACTIVE: '🟢',
            ClientStatus.INACTIVE: '🟠', ClientStatus.ARCHIVED: '⚫'}
        return colors[self]


class HabitFrequency(Enum):
    """Habit tracking frequency."""
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'

    def __str__(self) ->str:
        return self.value.title()

    @property
    def days_interval(self) ->int:
        """Get interval in days."""
        intervals = {HabitFrequency.DAILY: 1, HabitFrequency.WEEKLY: 7,
            HabitFrequency.MONTHLY: 30}
        return intervals[self]


class FileAttachmentType(Enum):
    """File attachment types with validation."""
    DOCUMENT = 'document'
    IMAGE = 'image'
    AUDIO = 'audio'
    VIDEO = 'video'
    ARCHIVE = 'archive'
    OTHER = 'other'

    def __str__(self) ->str:
        return self.value.title()

    @property
    def allowed_extensions(self) ->List[str]:
        """Get allowed file extensions for this type."""
        extensions = {FileAttachmentType.DOCUMENT: ['.pdf', '.doc', '.docx',
            '.txt', '.md', '.rtf'], FileAttachmentType.IMAGE: ['.jpg',
            '.jpeg', '.png', '.gif', '.bmp', '.svg'], FileAttachmentType.
            AUDIO: ['.mp3', '.wav', '.ogg', '.m4a', '.aac'],
            FileAttachmentType.VIDEO: ['.mp4', '.avi', '.mov', '.wmv',
            '.mkv'], FileAttachmentType.ARCHIVE: ['.zip', '.rar', '.7z',
            '.tar', '.gz'], FileAttachmentType.OTHER: []}
        return extensions[self]

    @property
    def max_size_mb(self) ->Optional[int]:
        """Get maximum file size in MB for this type."""
        sizes = {FileAttachmentType.DOCUMENT: 50, FileAttachmentType.IMAGE:
            25, FileAttachmentType.AUDIO: 100, FileAttachmentType.VIDEO: 
            500, FileAttachmentType.ARCHIVE: 200, FileAttachmentType.OTHER: 100
            }
        return sizes[self]

    @classmethod
    def from_extension(cls, extension: str) ->'FileAttachmentType':
        """Determine file type from extension."""
        ext = extension.lower()
        for file_type in cls:
            if ext in file_type.allowed_extensions:
                return file_type
        return cls.OTHER


class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = 'healthy'
    WARNING = 'warning'
    CRITICAL = 'critical'
    UNKNOWN = 'unknown'

    def __str__(self) ->str:
        return self.value.title()

    @property
    def color_code(self) ->str:
        """Get color code for UI display."""
        colors = {HealthStatus.HEALTHY: '🟢', HealthStatus.WARNING: '🟡',
            HealthStatus.CRITICAL: '🔴', HealthStatus.UNKNOWN: '⚪'}
        return colors[self]

    @property
    def needs_attention(self) ->bool:
        """Check if status requires attention."""
        return self in {HealthStatus.WARNING, HealthStatus.CRITICAL}


class AnalyticsTimeRange(Enum):
    """Time ranges for analytics and reporting."""
    TODAY = 'today'
    YESTERDAY = 'yesterday'
    THIS_WEEK = 'this_week'
    LAST_WEEK = 'last_week'
    THIS_MONTH = 'this_month'
    LAST_MONTH = 'last_month'
    THIS_QUARTER = 'this_quarter'
    THIS_YEAR = 'this_year'
    LAST_30_DAYS = 'last_30_days'
    LAST_90_DAYS = 'last_90_days'
    ALL_TIME = 'all_time'

    def __str__(self) ->str:
        return self.value.replace('_', ' ').title()

    @property
    def description(self) ->str:
        """Get human-readable description."""
        descriptions = {AnalyticsTimeRange.TODAY: "Today's activity",
            AnalyticsTimeRange.YESTERDAY: "Yesterday's activity",
            AnalyticsTimeRange.THIS_WEEK: 'This week (Monday to Sunday)',
            AnalyticsTimeRange.LAST_WEEK: 'Last week', AnalyticsTimeRange.
            THIS_MONTH: 'This month', AnalyticsTimeRange.LAST_MONTH:
            'Last month', AnalyticsTimeRange.THIS_QUARTER: 'This quarter',
            AnalyticsTimeRange.THIS_YEAR: 'This year', AnalyticsTimeRange.
            LAST_30_DAYS: 'Last 30 days', AnalyticsTimeRange.LAST_90_DAYS:
            'Last 90 days', AnalyticsTimeRange.ALL_TIME: 'All recorded data'}
        return descriptions[self]


def validate_enum_value(enum_class: type, value: Any, field_name: str='field'
    ) ->Any:
    """Validate and convert value to enum type."""
    if value is None:
        return None
    if isinstance(value, enum_class):
        return value
    if isinstance(value, str):
        if hasattr(enum_class, 'from_string'):
            result = enum_class.from_string(value)
            if result is not None:
                return result
        try:
            return enum_class[value.upper()]
        except (KeyError, AttributeError):
            pass
        for enum_item in enum_class:
            if enum_item.value == value:
                return enum_item
    valid_values = [item.value for item in enum_class]
    raise ValueError(
        f"Invalid {field_name} value: {value}. Valid values are: {', '.join(valid_values)}"
        )


def get_enum_choices(enum_class: type) ->List[tuple]:
    """Get choices list for form fields."""
    return [(item.value, str(item)) for item in enum_class]


def enum_to_dict(enum_class: type) ->Dict[str, Any]:
    """Convert enum to dictionary for JSON serialization."""
    return {'choices': [{'value': item.value, 'label': str(item)} for item in
        enum_class], 'default': list(enum_class)[0].value if enum_class else
        None}
