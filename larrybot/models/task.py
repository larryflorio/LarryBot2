"""
Enhanced Task model with advanced type safety for LarryBot2 Phase 2

This module provides the Task model with comprehensive enum-based type safety,
validation, and enterprise-grade data consistency.

All datetime fields are stored as UTC and must be timezone-aware in the application layer.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
from larrybot.models import Base
from larrybot.models.enums import TaskStatus, TaskPriority, validate_enum_value
from larrybot.utils.basic_datetime import get_utc_now, get_current_datetime
from larrybot.utils.datetime_utils import is_overdue, days_until_due, hours_elapsed_since, ensure_timezone_aware


class Task(Base):
    """Enhanced Task model with comprehensive type safety and functionality."""
    __tablename__ = 'tasks'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    description_rich: Mapped[Optional[str]] = mapped_column(Text, nullable=True
        )
    status: Mapped[TaskStatus] = mapped_column(String(20), default=
        TaskStatus.TODO.value, nullable=False)
    _priority: Mapped[TaskPriority] = mapped_column('priority', String(20),
        default=TaskPriority.MEDIUM.value, nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=
        True), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float,
        nullable=True)
    actual_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey(
        'tasks.id'), nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey(
        'clients.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
        default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
        default=get_utc_now, onupdate=get_utc_now, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(
        timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(
        timezone=True), nullable=True)
    client = relationship('Client', back_populates='tasks')
    comments = relationship('TaskComment', back_populates='task', cascade=
        'all, delete-orphan')
    attachments = relationship('TaskAttachment', back_populates='task',
        cascade='all, delete-orphan')
    time_entries = relationship('TaskTimeEntry', back_populates='task',
        cascade='all, delete-orphan')
    dependencies = relationship('TaskDependency', foreign_keys=
        'TaskDependency.task_id', back_populates='task', cascade=
        'all, delete-orphan')
    dependents = relationship('TaskDependency', foreign_keys=
        'TaskDependency.dependency_id', back_populates='dependency')
    parent = relationship('Task', remote_side=[id], back_populates='children')
    children = relationship('Task', back_populates='parent')
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sla_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sla_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(
        timezone=True), nullable=True)
    task_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255),
        nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    __table_args__ = Index('idx_tasks_status', 'status'), Index(
        'idx_tasks_priority', 'priority'), Index('idx_tasks_due_date',
        'due_date'), Index('idx_tasks_created_at', 'created_at'), Index(
        'idx_tasks_category', 'category'), Index('idx_tasks_external_id',
        'external_id')

    def __init__(self, **kwargs):
        """Initialize task with enhanced validation."""
        if 'status' in kwargs:
            status_value = kwargs['status']
            if isinstance(status_value, str):
                if status_value == 'Done':
                    kwargs['status'] = TaskStatus.DONE.value
                elif status_value == 'Todo':
                    kwargs['status'] = TaskStatus.TODO.value
                elif status_value == 'In Progress':
                    kwargs['status'] = TaskStatus.IN_PROGRESS.value
                else:
                    enum_value = TaskStatus.from_string(status_value)
                    kwargs['status'] = (enum_value.value if enum_value else
                        TaskStatus.TODO.value)
            elif isinstance(status_value, TaskStatus):
                kwargs['status'] = status_value.value
        if 'priority' in kwargs:
            priority_value = kwargs.pop('priority')
            if priority_value is None:
                kwargs['_priority'] = None
            elif isinstance(priority_value, str):
                if priority_value in ['Low', 'Medium', 'High', 'Critical',
                    'Urgent']:
                    enum_value = TaskPriority.from_string(priority_value)
                    kwargs['_priority'] = (enum_value.value if enum_value else
                        TaskPriority.MEDIUM.value)
                else:
                    enum_value = TaskPriority.from_string(priority_value)
                    kwargs['_priority'] = (enum_value.value if enum_value else
                        TaskPriority.MEDIUM.value)
            elif isinstance(priority_value, TaskPriority):
                kwargs['_priority'] = priority_value.value
            elif isinstance(priority_value, int):
                kwargs['_priority'] = priority_value
        if 'created_at' not in kwargs:
            kwargs['created_at'] = get_utc_now()
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = get_utc_now()
        if 'status' not in kwargs:
            kwargs['status'] = TaskStatus.TODO.value
        if '_priority' not in kwargs:
            kwargs['_priority'] = TaskPriority.MEDIUM.value
        if 'done' not in kwargs:
            status_value = kwargs.get('status', TaskStatus.TODO.value)
            if isinstance(status_value, str):
                status_enum = TaskStatus.from_string(status_value
                    ) or TaskStatus.TODO
            else:
                status_enum = status_value
            kwargs['done'] = status_enum.is_completed if hasattr(status_enum,
                'is_completed') else False
        super().__init__(**kwargs)

    @property
    def status_enum(self) ->TaskStatus:
        """Get status as enum type."""
        if not self.status:
            return TaskStatus.TODO
        return TaskStatus.from_string(self.status) or TaskStatus.TODO

    @status_enum.setter
    def status_enum(self, value: TaskStatus) ->None:
        """Set status using enum type and synchronize done field."""
        self.status = value.value
        self.done = value.is_completed
        if value.is_completed and not self.completed_at:
            self.completed_at = get_utc_now()

    @property
    def priority_enum(self) ->Optional[TaskPriority]:
        """Get priority as enum type."""
        if self._priority is None:
            return None
        if not self._priority:
            return TaskPriority.MEDIUM
        if isinstance(self._priority, int):
            try:
                return TaskPriority(self._priority)
            except ValueError:
                return TaskPriority.MEDIUM
        elif isinstance(self._priority, str):
            try:
                int_value = int(self._priority)
                return TaskPriority(int_value)
            except (ValueError, TypeError):
                return TaskPriority.from_string(self._priority
                    ) or TaskPriority.MEDIUM
        else:
            return TaskPriority.MEDIUM

    @priority_enum.setter
    def priority_enum(self, value: TaskPriority) ->None:
        """Set priority using enum type."""
        self._priority = value.value

    @hybrid_property
    def priority(self) ->Optional[str]:
        """Get priority as human-readable string for backward compatibility."""
        if self._priority is None:
            return None
        priority_enum = self.priority_enum
        if priority_enum is None:
            return None
        return priority_enum.name.title()

    @priority.expression
    def priority(cls):
        """Expression for SQLAlchemy queries - returns the database column."""
        return cls._priority

    @priority.setter
    def priority(self, value) ->None:
        """Set priority from various input types."""
        if value is None:
            self._priority = None
            return
        if isinstance(value, str):
            if value in ['Low', 'Medium', 'High', 'Critical', 'Urgent']:
                enum_value = TaskPriority.from_string(value)
                self._priority = (enum_value.value if enum_value else
                    TaskPriority.MEDIUM.value)
            else:
                enum_value = TaskPriority.from_string(value)
                self._priority = (enum_value.value if enum_value else
                    TaskPriority.MEDIUM.value)
        elif isinstance(value, TaskPriority):
            self._priority = value.value
        elif isinstance(value, int):
            try:
                TaskPriority(value)
                self._priority = value
            except ValueError:
                self._priority = TaskPriority.MEDIUM.value
        else:
            self._priority = TaskPriority.MEDIUM.value

    def set_done(self, value: bool) ->None:
        """Set completion status and synchronize with status field."""
        self.done = value
        if value:
            self.status = TaskStatus.DONE.value
            if not self.completed_at:
                self.completed_at = get_utc_now()
        elif self.status_enum == TaskStatus.DONE:
            self.status = (TaskStatus.IN_PROGRESS.value if self.started_at else
                TaskStatus.TODO.value)
            self.completed_at = None

    def is_done(self) ->bool:
        """Check if task is completed (backward compatibility)."""
        return self.done or self.status_enum.is_completed

    @property
    def is_overdue(self) ->bool:
        """Check if task is overdue."""
        if not self.due_date or self.status_enum.is_completed:
            return False
        return is_overdue(self.due_date)

    @property
    def days_until_due(self) ->Optional[int]:
        """Get days until due date."""
        return days_until_due(self.due_date)

    @property
    def time_spent_hours(self) ->float:
        """Get total time spent on task from time entries."""
        if not self.time_entries:
            return 0.0
        return sum(entry.hours for entry in self.time_entries)

    @property
    def completion_percentage(self) ->int:
        """Get task completion percentage."""
        if self.status_enum == TaskStatus.DONE:
            return 100
        elif self.status_enum == TaskStatus.CANCELLED:
            return 0
        else:
            return max(0, min(100, self.progress))

    @property
    def sla_hours_remaining(self) ->Optional[float]:
        """Get SLA hours remaining based on priority."""
        sla_hours = self.priority_enum.sla_hours
        if not sla_hours:
            return None
        if self.created_at is None:
            return sla_hours
        normalized_created_at = ensure_timezone_aware(self.created_at)
        delta = get_current_datetime() - normalized_created_at
        hours_elapsed = delta.total_seconds() / 3600
        return max(0, sla_hours - hours_elapsed)

    @property
    def is_sla_violated(self) ->bool:
        """Check if SLA is violated."""
        remaining = self.sla_hours_remaining
        return (remaining is not None and remaining <= 0 and not self.
            status_enum.is_completed)

    @property
    def estimated_completion_date(self) ->Optional[datetime]:
        """Estimate completion date based on progress and time entries."""
        if self.status_enum == TaskStatus.DONE:
            return self.completed_at
        if not self.estimated_hours or self.progress <= 0:
            return None
        hours_spent = self.time_spent_hours
        if hours_spent <= 0:
            return None
        if self.created_at is None:
            return None
        delta = get_current_datetime() - self.created_at
        days_elapsed = delta.days or 1
        hours_per_day = hours_spent / days_elapsed
        if hours_per_day > 0:
            days_remaining = (self.estimated_hours - hours_spent
                ) / hours_per_day
            return get_current_datetime() + timedelta(days=days_remaining)
        return None

    def get_tags_list(self) ->List[str]:
        """Get tags as a list."""
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except (json.JSONDecodeError, TypeError):
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    def set_tags_list(self, tags: List[str]) ->None:
        """Set tags from a list."""
        if not tags:
            self.tags = None
        else:
            clean_tags = list(set(tag.strip() for tag in tags if tag.strip()))
            self.tags = json.dumps(clean_tags)

    def add_tag(self, tag: str) ->bool:
        """Add a tag to the task. Returns True if tag was added."""
        current_tags = self.get_tags_list()
        tag = tag.strip()
        if tag and tag not in current_tags:
            current_tags.append(tag)
            self.set_tags_list(current_tags)
            return True
        return False

    def remove_tag(self, tag: str) ->bool:
        """Remove a tag from the task. Returns True if tag was removed."""
        current_tags = self.get_tags_list()
        tag = tag.strip()
        if tag in current_tags:
            current_tags.remove(tag)
            self.set_tags_list(current_tags)
            return True
        return False

    def can_transition_to_status(self, new_status: TaskStatus) ->bool:
        """Check if task can transition to new status."""
        if new_status == self.status_enum:
            return True
        return new_status in self.status_enum.can_transition_to

    def transition_to_status(self, new_status: TaskStatus, force: bool=False
        ) ->bool:
        """
        Transition task to new status with validation.
        
        Args:
            new_status: The target status
            force: Skip validation if True
            
        Returns:
            True if transition was successful
        """
        if not force and not self.can_transition_to_status(new_status):
            return False
        old_status = self.status_enum
        self.status = new_status
        now = get_utc_now()
        if new_status == TaskStatus.IN_PROGRESS and not self.started_at:
            self.started_at = now
        elif new_status == TaskStatus.DONE and not self.completed_at:
            self.completed_at = now
        elif new_status in [TaskStatus.TODO, TaskStatus.BLOCKED
            ] and old_status == TaskStatus.DONE:
            self.completed_at = None
        self.updated_at = now
        return True

    def calculate_priority_score(self) ->float:
        """
        Calculate a priority score for task sorting.
        Higher score = higher priority.
        """
        base_score = self.priority_enum.weight * 100
        if self.due_date:
            days_until_due = self.days_until_due
            if days_until_due is not None:
                if days_until_due < 0:
                    base_score += 1000 + abs(days_until_due) * 10
                elif days_until_due <= 1:
                    base_score += 500
                elif days_until_due <= 7:
                    base_score += 100
        if self.is_sla_violated:
            base_score += 2000
        if not self.status_enum.is_completed:
            current_progress = (self.progress if self.progress is not None else
                0)
            progress_penalty = (100 - current_progress) / 10
            base_score += progress_penalty
        return base_score

    def to_dict(self, include_relations: bool=False) ->Dict[str, Any]:
        """Convert task to dictionary with enhanced type information."""
        result = {'id': self.id, 'description': self.description, 'status':
            self.status_enum.value, 'status_display':
            f'{self.status_enum.color_code} {self.status_enum.value}',
            'priority': self.priority_enum.name.title(), 'priority_display':
            f'{self.priority_enum.color_code} {self.priority_enum.name.title()}'
            , 'priority_weight': self.priority_enum.weight, 'due_date': 
            self.due_date.isoformat() if self.due_date else None,
            'category': self.category, 'estimated_hours': self.
            estimated_hours, 'actual_hours': self.actual_hours,
            'time_spent_hours': self.time_spent_hours, 'progress': self.
            progress, 'completion_percentage': self.completion_percentage,
            'parent_id': self.parent_id, 'tags': self.get_tags_list(),
            'client_id': self.client_id, 'created_at': self.created_at.
            isoformat(), 'updated_at': self.updated_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else
            None, 'completed_at': self.completed_at.isoformat() if self.
            completed_at else None, 'done': self.done, 'is_overdue': self.
            is_overdue, 'days_until_due': self.days_until_due,
            'sla_hours_remaining': self.sla_hours_remaining,
            'is_sla_violated': self.is_sla_violated, 'priority_score': self
            .calculate_priority_score(), 'title': self.title, 'sla_hours':
            self.sla_hours, 'sla_deadline': self.sla_deadline.isoformat() if
            self.sla_deadline else None, 'task_metadata': self.
            task_metadata, 'external_id': self.external_id, 'source': self.
            source}
        if include_relations:
            result.update({'client': self.client.to_dict() if self.client else
                None, 'comments_count': len(self.comments) if self.comments
                 else 0, 'attachments_count': len(self.attachments) if self
                .attachments else 0, 'time_entries_count': len(self.
                time_entries) if self.time_entries else 0, 'subtasks_count':
                len(self.children) if self.children else 0})
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) ->'Task':
        """Create task from dictionary with validation."""
        excluded_fields = {'status_display', 'priority_display',
            'priority_weight', 'time_spent_hours', 'completion_percentage',
            'is_overdue', 'days_until_due', 'sla_hours_remaining',
            'is_sla_violated', 'priority_score', 'client', 'comments_count',
            'attachments_count', 'time_entries_count', 'subtasks_count'}
        filtered_data = {k: v for k, v in data.items() if k not in
            excluded_fields}
        if 'status' in filtered_data and isinstance(filtered_data['status'],
            str):
            filtered_data['status'] = validate_enum_value(TaskStatus,
                filtered_data['status'], 'status')
        if 'priority' in filtered_data and isinstance(filtered_data[
            'priority'], str):
            filtered_data['priority'] = validate_enum_value(TaskPriority,
                filtered_data['priority'], 'priority')
        datetime_fields = ['due_date', 'created_at', 'updated_at',
            'started_at', 'completed_at']
        for field in datetime_fields:
            if field in filtered_data and isinstance(filtered_data[field], str
                ):
                try:
                    filtered_data[field] = datetime.fromisoformat(filtered_data
                        [field].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    filtered_data[field] = None
        if 'tags' in data and isinstance(data['tags'], list):
            task = cls(**{k: v for k, v in filtered_data.items() if k !=
                'tags'})
            task.set_tags_list(data['tags'])
            return task
        return cls(**filtered_data)

    def __repr__(self) ->str:
        """Enhanced string representation."""
        return (
            f"<Task(id={self.id}, description='{self.description[:50]}...', status={self.status}, priority={self.priority_enum.name.upper()})>"
            )


from datetime import timedelta
