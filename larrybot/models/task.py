"""
Enhanced Task model with advanced type safety for LarryBot2 Phase 2

This module provides the Task model with comprehensive enum-based type safety,
validation, and enterprise-grade data consistency.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from larrybot.models import Base
from larrybot.models.enums import TaskStatus, TaskPriority, validate_enum_value


class Task(Base):
    """Enhanced Task model with comprehensive type safety and functionality."""
    
    __tablename__ = 'tasks'
    
    # Primary fields with enhanced type safety
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    description_rich: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Enhanced enum-based status and priority
    status: Mapped[TaskStatus] = mapped_column(
        String(20),  # Keep as String to handle existing data, convert in Python
        default=TaskStatus.TODO.value, 
        nullable=False
    )
    _priority: Mapped[TaskPriority] = mapped_column(
        "priority",  # Map to 'priority' column in database
        String(20),  # Keep as String to handle existing data, convert in Python
        default=TaskPriority.MEDIUM.value, 
        nullable=False
    )
    
    # Backward compatibility field
    done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Optional fields with proper typing
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Progress tracking
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    
    # Hierarchy support
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey('tasks.id'), 
        nullable=True
    )
    
    # Tags as JSON string for flexibility
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Client relationship
    client_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey('clients.id'), 
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships with proper typing
    client = relationship("Client", back_populates="tasks")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan")
    time_entries = relationship("TaskTimeEntry", back_populates="task", cascade="all, delete-orphan")
    dependencies = relationship(
        "TaskDependency", 
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan"
    )
    
    # Dependents (tasks that depend on this task)
    dependents = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.dependency_id",
        back_populates="dependency"
    )
    
    # Self-referential relationship for subtasks
    parent = relationship("Task", remote_side=[id], back_populates="children")
    children = relationship("Task", back_populates="parent")
    
    def __init__(self, **kwargs):
        """Initialize task with enhanced validation."""
        # Validate and convert enum values
        if 'status' in kwargs:
            status_value = kwargs['status']
            if isinstance(status_value, str):
                # Convert string to enum, handling legacy values
                if status_value == 'Done':
                    kwargs['status'] = TaskStatus.DONE.value
                elif status_value == 'Todo':
                    kwargs['status'] = TaskStatus.TODO.value
                elif status_value == 'In Progress':
                    kwargs['status'] = TaskStatus.IN_PROGRESS.value
                else:
                    # Try to find matching enum value
                    enum_value = TaskStatus.from_string(status_value)
                    kwargs['status'] = enum_value.value if enum_value else TaskStatus.TODO.value
            elif isinstance(status_value, TaskStatus):
                kwargs['status'] = status_value.value
        
        if 'priority' in kwargs:
            priority_value = kwargs.pop('priority')  # Remove from kwargs so it doesn't conflict
            if priority_value is None:
                # Explicitly setting priority to None
                kwargs['_priority'] = None
            elif isinstance(priority_value, str):
                # Convert string to enum value, handling legacy values
                if priority_value in ['Low', 'Medium', 'High', 'Critical', 'Urgent']:
                    enum_value = TaskPriority.from_string(priority_value)
                    kwargs['_priority'] = enum_value.value if enum_value else TaskPriority.MEDIUM.value
                else:
                    enum_value = TaskPriority.from_string(priority_value)
                    kwargs['_priority'] = enum_value.value if enum_value else TaskPriority.MEDIUM.value
            elif isinstance(priority_value, TaskPriority):
                kwargs['_priority'] = priority_value.value
            elif isinstance(priority_value, int):
                kwargs['_priority'] = priority_value
        
        # Set default timestamps if not provided
        if 'created_at' not in kwargs:
            kwargs['created_at'] = datetime.utcnow()
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = datetime.utcnow()
        
        # Ensure defaults for required enum fields
        if 'status' not in kwargs:
            kwargs['status'] = TaskStatus.TODO.value
        if '_priority' not in kwargs:
            # Only set default if priority wasn't explicitly set to None
            kwargs['_priority'] = TaskPriority.MEDIUM.value
        
        # Ensure done field is properly set based on status (unless explicitly provided)
        if 'done' not in kwargs:
            status_value = kwargs.get('status', TaskStatus.TODO.value)
            # Handle both string and enum values for status
            if isinstance(status_value, str):
                status_enum = TaskStatus.from_string(status_value) or TaskStatus.TODO
            else:
                status_enum = status_value
            kwargs['done'] = status_enum.is_completed if hasattr(status_enum, 'is_completed') else False
        
        super().__init__(**kwargs)
    
    @property
    def status_enum(self) -> TaskStatus:
        """Get status as enum type."""
        if not self.status:
            return TaskStatus.TODO
        return TaskStatus.from_string(self.status) or TaskStatus.TODO
    
    @status_enum.setter  
    def status_enum(self, value: TaskStatus) -> None:
        """Set status using enum type and synchronize done field."""
        self.status = value.value
        # Synchronize done field with status
        self.done = value.is_completed
        if value.is_completed and not self.completed_at:
            self.completed_at = datetime.utcnow()
    
    @property
    def priority_enum(self) -> Optional[TaskPriority]:
        """Get priority as enum type."""
        if self._priority is None:
            return None
        if not self._priority:
            return TaskPriority.MEDIUM
        
        # Handle both string and integer values
        if isinstance(self._priority, int):
            # Convert integer to enum by value
            try:
                return TaskPriority(self._priority)
            except ValueError:
                return TaskPriority.MEDIUM
        elif isinstance(self._priority, str):
            # First try to convert string numbers to integers
            try:
                int_value = int(self._priority)
                return TaskPriority(int_value)
            except (ValueError, TypeError):
                # If not a number, try name-based lookup
                return TaskPriority.from_string(self._priority) or TaskPriority.MEDIUM
        else:
            return TaskPriority.MEDIUM
    
    @priority_enum.setter
    def priority_enum(self, value: TaskPriority) -> None:
        """Set priority using enum type."""
        self._priority = value.value
    
    @hybrid_property
    def priority(self) -> Optional[str]:
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
    def priority(self, value) -> None:
        """Set priority from various input types."""
        if value is None:
            # Handle explicit None values - keep as None for factory tests
            self._priority = None
            return
            
        if isinstance(value, str):
            # Convert string to enum value
            if value in ['Low', 'Medium', 'High', 'Critical', 'Urgent']:
                enum_value = TaskPriority.from_string(value)
                self._priority = enum_value.value if enum_value else TaskPriority.MEDIUM.value
            else:
                enum_value = TaskPriority.from_string(value)
                self._priority = enum_value.value if enum_value else TaskPriority.MEDIUM.value
        elif isinstance(value, TaskPriority):
            self._priority = value.value
        elif isinstance(value, int):
            # Handle direct integer assignment
            try:
                TaskPriority(value)  # Validate it's a valid priority value
                self._priority = value
            except ValueError:
                self._priority = TaskPriority.MEDIUM.value
        else:
            self._priority = TaskPriority.MEDIUM.value
    
    def set_done(self, value: bool) -> None:
        """Set completion status and synchronize with status field."""
        self.done = value  # Set the database column
        if value:
            self.status = TaskStatus.DONE.value
            if not self.completed_at:
                self.completed_at = datetime.utcnow()
        else:
            # If unmarking as done, set to appropriate status
            if self.status_enum == TaskStatus.DONE:
                self.status = (TaskStatus.IN_PROGRESS.value if self.started_at else TaskStatus.TODO.value)
                self.completed_at = None
    
    def is_done(self) -> bool:
        """Check if task is completed (backward compatibility)."""
        return self.done or self.status_enum.is_completed
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date or self.status_enum.is_completed:
            return False
        return datetime.utcnow() > self.due_date
    
    @property
    def days_until_due(self) -> Optional[int]:
        """Get days until due date."""
        if not self.due_date:
            return None
        delta = self.due_date - datetime.utcnow()
        return delta.days
    
    @property
    def time_spent_hours(self) -> float:
        """Get total time spent on task from time entries."""
        if not self.time_entries:
            return 0.0
        return sum(entry.hours for entry in self.time_entries)
    
    @property
    def completion_percentage(self) -> int:
        """Get task completion percentage."""
        if self.status_enum == TaskStatus.DONE:
            return 100
        elif self.status_enum == TaskStatus.CANCELLED:
            return 0
        else:
            return max(0, min(100, self.progress))
    
    @property
    def sla_hours_remaining(self) -> Optional[float]:
        """Get SLA hours remaining based on priority."""
        sla_hours = self.priority_enum.sla_hours
        if not sla_hours:
            return None
        
        hours_elapsed = (datetime.utcnow() - self.created_at).total_seconds() / 3600
        return max(0, sla_hours - hours_elapsed)
    
    @property
    def is_sla_violated(self) -> bool:
        """Check if SLA is violated."""
        remaining = self.sla_hours_remaining
        return remaining is not None and remaining <= 0 and not self.status_enum.is_completed
    
    @property
    def estimated_completion_date(self) -> Optional[datetime]:
        """Estimate completion date based on progress and time entries."""
        if self.status_enum == TaskStatus.DONE:
            return self.completed_at
        
        if not self.estimated_hours or self.progress <= 0:
            return None
        
        hours_spent = self.time_spent_hours
        if hours_spent <= 0:
            return None
        
        # Calculate based on current velocity
        remaining_hours = self.estimated_hours * (100 - self.progress) / 100
        hours_per_day = hours_spent / max(1, (datetime.utcnow() - self.created_at).days or 1)
        
        if hours_per_day > 0:
            days_remaining = remaining_hours / hours_per_day
            return datetime.utcnow() + timedelta(days=days_remaining)
        
        return None
    
    def get_tags_list(self) -> List[str]:
        """Get tags as a list."""
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except (json.JSONDecodeError, TypeError):
            # Handle legacy comma-separated tags
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    def set_tags_list(self, tags: List[str]) -> None:
        """Set tags from a list."""
        if not tags:
            self.tags = None
        else:
            # Clean and deduplicate tags
            clean_tags = list(set(tag.strip() for tag in tags if tag.strip()))
            self.tags = json.dumps(clean_tags)
    
    def add_tag(self, tag: str) -> bool:
        """Add a tag to the task. Returns True if tag was added."""
        current_tags = self.get_tags_list()
        tag = tag.strip()
        
        if tag and tag not in current_tags:
            current_tags.append(tag)
            self.set_tags_list(current_tags)
            return True
        return False
    
    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from the task. Returns True if tag was removed."""
        current_tags = self.get_tags_list()
        tag = tag.strip()
        
        if tag in current_tags:
            current_tags.remove(tag)
            self.set_tags_list(current_tags)
            return True
        return False
    
    def can_transition_to_status(self, new_status: TaskStatus) -> bool:
        """Check if task can transition to new status."""
        if new_status == self.status_enum:
            return True
        
        return new_status in self.status_enum.can_transition_to
    
    def transition_to_status(self, new_status: TaskStatus, force: bool = False) -> bool:
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
        
        # Update timestamps based on status transition
        now = datetime.utcnow()
        
        if new_status == TaskStatus.IN_PROGRESS and not self.started_at:
            self.started_at = now
        elif new_status == TaskStatus.DONE and not self.completed_at:
            self.completed_at = now
        elif new_status in [TaskStatus.TODO, TaskStatus.BLOCKED] and old_status == TaskStatus.DONE:
            # Reopening task
            self.completed_at = None
        
        self.updated_at = now
        return True
    
    def calculate_priority_score(self) -> float:
        """
        Calculate a priority score for task sorting.
        Higher score = higher priority.
        """
        base_score = self.priority_enum.weight * 100
        
        # Adjust for due date urgency
        if self.due_date:
            days_until_due = self.days_until_due
            if days_until_due is not None:
                if days_until_due < 0:  # Overdue
                    base_score += 1000 + abs(days_until_due) * 10
                elif days_until_due <= 1:  # Due today or tomorrow
                    base_score += 500
                elif days_until_due <= 7:  # Due this week
                    base_score += 100
        
        # Adjust for SLA violation
        if self.is_sla_violated:
            base_score += 2000
        
        # Adjust for progress (lower progress = higher priority for incomplete tasks)
        if not self.status_enum.is_completed:
            current_progress = self.progress if self.progress is not None else 0
            progress_penalty = (100 - current_progress) / 10
            base_score += progress_penalty
        
        return base_score
    
    def to_dict(self, include_relations: bool = False) -> Dict[str, Any]:
        """Convert task to dictionary with enhanced type information."""
        result = {
            'id': self.id,
            'description': self.description,
            'status': self.status_enum.value,
            'status_display': f"{self.status_enum.color_code} {self.status_enum.value}",
            'priority': self.priority_enum.name.title(),
            'priority_display': f"{self.priority_enum.color_code} {self.priority_enum.name.title()}",
            'priority_weight': self.priority_enum.weight,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'category': self.category,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'time_spent_hours': self.time_spent_hours,
            'progress': self.progress,
            'completion_percentage': self.completion_percentage,
            'parent_id': self.parent_id,
            'tags': self.get_tags_list(),
            'client_id': self.client_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'done': self.done,  # Backward compatibility
            'is_overdue': self.is_overdue,
            'days_until_due': self.days_until_due,
            'sla_hours_remaining': self.sla_hours_remaining,
            'is_sla_violated': self.is_sla_violated,
            'priority_score': self.calculate_priority_score()
        }
        
        if include_relations:
            result.update({
                'client': self.client.to_dict() if self.client else None,
                'comments_count': len(self.comments) if self.comments else 0,
                'attachments_count': len(self.attachments) if self.attachments else 0,
                'time_entries_count': len(self.time_entries) if self.time_entries else 0,
                'subtasks_count': len(self.children) if self.children else 0
            })
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary with validation."""
        # Fields to exclude from constructor (display fields and computed properties)
        excluded_fields = {
            'status_display', 'priority_display', 'priority_weight', 'time_spent_hours',
            'completion_percentage', 'is_overdue', 'days_until_due', 'sla_hours_remaining',
            'is_sla_violated', 'priority_score', 'client', 'comments_count',
            'attachments_count', 'time_entries_count', 'subtasks_count'
        }
        
        # Filter out excluded fields
        filtered_data = {k: v for k, v in data.items() if k not in excluded_fields}
        
        # Handle enum conversion
        if 'status' in filtered_data and isinstance(filtered_data['status'], str):
            filtered_data['status'] = validate_enum_value(TaskStatus, filtered_data['status'], 'status')
        if 'priority' in filtered_data and isinstance(filtered_data['priority'], str):
            filtered_data['priority'] = validate_enum_value(TaskPriority, filtered_data['priority'], 'priority')
        
        # Handle datetime conversion
        datetime_fields = ['due_date', 'created_at', 'updated_at', 'started_at', 'completed_at']
        for field in datetime_fields:
            if field in filtered_data and isinstance(filtered_data[field], str):
                try:
                    filtered_data[field] = datetime.fromisoformat(filtered_data[field].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    filtered_data[field] = None
        
        # Handle tags conversion
        if 'tags' in data and isinstance(data['tags'], list):
            task = cls(**{k: v for k, v in filtered_data.items() if k != 'tags'})
            task.set_tags_list(data['tags'])
            return task
        
        return cls(**filtered_data)
    
    def __repr__(self) -> str:
        """Enhanced string representation."""
        return (
            f"<Task(id={self.id}, "
            f"description='{self.description[:50]}...', "
            f"status={self.status}, "
            f"priority={self.priority_enum.name.upper()})>"
        )


# Add missing import for timedelta
from datetime import timedelta 