"""
Enhanced Task model with advanced type safety for LarryBot2 Phase 2

This module provides the Task model with comprehensive enum-based type safety,
validation, and enterprise-grade data consistency.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
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
    
    # Enhanced enum-based status and priority
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), 
        default=TaskStatus.TODO, 
        nullable=False
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority), 
        default=TaskPriority.MEDIUM, 
        nullable=False
    )
    
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
            kwargs['status'] = validate_enum_value(TaskStatus, kwargs['status'], 'status')
        if 'priority' in kwargs:
            kwargs['priority'] = validate_enum_value(TaskPriority, kwargs['priority'], 'priority')
        
        # Set default timestamps if not provided
        if 'created_at' not in kwargs:
            kwargs['created_at'] = datetime.utcnow()
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = datetime.utcnow()
        
        super().__init__(**kwargs)
    
    @property
    def done(self) -> bool:
        """Check if task is completed (backward compatibility)."""
        return self.status.is_completed
    
    @done.setter
    def done(self, value: bool) -> None:
        """Set completion status (backward compatibility)."""
        if value:
            self.status = TaskStatus.DONE
            if not self.completed_at:
                self.completed_at = datetime.utcnow()
        else:
            # If unmarking as done, set to appropriate status
            if self.status == TaskStatus.DONE:
                self.status = TaskStatus.IN_PROGRESS if self.started_at else TaskStatus.TODO
                self.completed_at = None
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date or self.status.is_completed:
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
        if self.status == TaskStatus.DONE:
            return 100
        elif self.status == TaskStatus.CANCELLED:
            return 0
        else:
            return max(0, min(100, self.progress))
    
    @property
    def sla_hours_remaining(self) -> Optional[float]:
        """Get SLA hours remaining based on priority."""
        sla_hours = self.priority.sla_hours
        if not sla_hours:
            return None
        
        hours_elapsed = (datetime.utcnow() - self.created_at).total_seconds() / 3600
        return max(0, sla_hours - hours_elapsed)
    
    @property
    def is_sla_violated(self) -> bool:
        """Check if SLA is violated."""
        remaining = self.sla_hours_remaining
        return remaining is not None and remaining <= 0 and not self.status.is_completed
    
    @property
    def estimated_completion_date(self) -> Optional[datetime]:
        """Estimate completion date based on progress and time entries."""
        if self.status.is_completed:
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
        if new_status == self.status:
            return True
        
        return new_status in self.status.can_transition_to
    
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
        
        old_status = self.status
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
        base_score = self.priority.weight * 100
        
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
        if not self.status.is_completed:
            progress_penalty = (100 - self.progress) / 10
            base_score += progress_penalty
        
        return base_score
    
    def to_dict(self, include_relations: bool = False) -> Dict[str, Any]:
        """Convert task to dictionary with enhanced type information."""
        result = {
            'id': self.id,
            'description': self.description,
            'status': self.status.value,
            'status_display': f"{self.status.color_code} {self.status.value}",
            'priority': self.priority.name,
            'priority_display': f"{self.priority.color_code} {self.priority.name.title()}",
            'priority_weight': self.priority.weight,
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
        # Handle enum conversion
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = validate_enum_value(TaskStatus, data['status'], 'status')
        if 'priority' in data and isinstance(data['priority'], str):
            data['priority'] = validate_enum_value(TaskPriority, data['priority'], 'priority')
        
        # Handle datetime conversion
        datetime_fields = ['due_date', 'created_at', 'updated_at', 'started_at', 'completed_at']
        for field in datetime_fields:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    data[field] = None
        
        # Handle tags conversion
        if 'tags' in data and isinstance(data['tags'], list):
            task = cls(**{k: v for k, v in data.items() if k != 'tags'})
            task.set_tags_list(data['tags'])
            return task
        
        return cls(**data)
    
    def __repr__(self) -> str:
        """Enhanced string representation."""
        return (
            f"<Task(id={self.id}, "
            f"description='{self.description[:50]}...', "
            f"status={self.status.value}, "
            f"priority={self.priority.name})>"
        )


# Add missing import for timedelta
from datetime import timedelta 