---
title: Models API Reference
description: Data model reference for LarryBot2
last_updated: 2025-06-28
---

> **Timezone Handling:**
> - All datetimes in LarryBot2 are stored in UTC in the database for consistency and reliability.
> - All datetimes are transparently converted to and from the user's configured/system timezone for display and business logic.
> - All datetimes are timezone-aware and Daylight Saving Time (DST) is handled automatically.
> - **Best Practice:** Always use the provided timezone utilities for all datetime operations in plugins and integrations.

# Models API Reference 📊

> **Breadcrumbs:** [Home](../../README.md) > [API Reference](README.md) > Models

This document provides a complete reference for all data models in LarryBot2.

## 🎯 Model Overview

LarryBot2 uses SQLAlchemy ORM with SQLite database. All models include standard fields like `id`, `created_at`, and `updated_at` where applicable.

## 📋 Core Models

### Task Model
```python
class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)
    done = Column(Boolean, default=False)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=True)
    priority = Column(String, default='medium')  # low, medium, high
    due_date = Column(Date, nullable=True)  # Displayed in local timezone, stored as UTC
    category = Column(String, nullable=True)
    status = Column(String, default='todo')  # todo, in_progress, done
    estimated_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, default=0.0)
    started_at = Column(DateTime, nullable=True)  # Displayed in local timezone, stored as UTC
    parent_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    tags = Column(String, nullable=True)  # comma-separated
    description_rich = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)  # Always UTC
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Always UTC
    
    # Relationships
    client = relationship("Client", back_populates="tasks")
    subtasks = relationship("Task", backref=backref("parent", remote_side=[id]))
    dependencies = relationship("TaskDependency", foreign_keys="TaskDependency.task_id")
    comments = relationship("TaskComment", back_populates="task")
    time_entries = relationship("TaskTimeEntry", back_populates="task")
    attachments = relationship("TaskAttachment", back_populates="task")
```

### Client Model
```python
class Client(Base):
    __tablename__ = 'clients'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks = relationship("Task", back_populates="client")
```

### TaskDependency Model
```python
class TaskDependency(Base):
    __tablename__ = 'task_dependencies'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    dependency_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task = relationship("Task", foreign_keys=[task_id])
    dependency = relationship("Task", foreign_keys=[dependency_id])
```

### TaskComment Model
```python
class TaskComment(Base):
    __tablename__ = 'task_comments'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    user_id = Column(Integer, nullable=False)  # Telegram user ID
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task = relationship("Task", back_populates="comments")
```

### TaskTimeEntry Model
```python
class TaskTimeEntry(Base):
    __tablename__ = 'task_time_entries'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task = relationship("Task", back_populates="time_entries")
```

### TaskAttachment Model
```python
class TaskAttachment(Base):
    __tablename__ = 'task_attachments'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    filename = Column(String(255), nullable=False)  # Internal filename (hash-based)
    original_filename = Column(String(255), nullable=False)  # Original filename
    file_path = Column(String(500), nullable=False)  # Local storage path
    file_url = Column(String(500), nullable=True)    # External URL (optional)
    file_size = Column(Integer, nullable=False)      # Size in bytes
    mime_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="attachments")
```

### Reminder Model
```python
class Reminder(Base):
    __tablename__ = 'reminders'
    
    id = Column(Integer, primary_key=True)
    message = Column(String, nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Habit Model
```python
class Habit(Base):
    __tablename__ = 'habits'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    frequency = Column(String, nullable=False)  # daily, weekly, monthly
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### CalendarToken Model
```python
class CalendarToken(Base):
    __tablename__ = 'calendar_tokens'
    
    id = Column(Integer, primary_key=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    token_expiry = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Metrics Model
```python
class Metrics(Base):
    __tablename__ = 'metrics'
    
    id = Column(Integer, primary_key=True)
    metric_type = Column(String, nullable=False)  # command_execution, system_health, etc.
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float, nullable=False)
    metadata = Column(Text, nullable=True)  # JSON string
    timestamp = Column(DateTime, default=datetime.utcnow)
```

## 🔗 Model Relationships

### Task Relationships
```python
# Task -> Client (Many-to-One)
task.client = client
client.tasks = [task1, task2, task3]

# Task -> Subtasks (One-to-Many)
task.subtasks = [subtask1, subtask2]
subtask.parent = task

# Task -> Dependencies (Many-to-Many through TaskDependency)
task.dependencies = [dependency1, dependency2]
dependency.task = task
dependency.dependency = dependent_task

# Task -> Comments (One-to-Many)
task.comments = [comment1, comment2]
comment.task = task

# Task -> Time Entries (One-to-Many)
task.time_entries = [time_entry1, time_entry2]
time_entry.task = task

# Task -> Attachments (One-to-Many)
task.attachments = [attachment1, attachment2]
attachment.task = task
```

### Client Relationships
```python
# Client -> Tasks (One-to-Many)
client.tasks = [task1, task2, task3]
task.client = client
```

## 📊 Model Validation

### Task Validation
```python
def validate_task_data(data):
    """Validate task data before creation/update."""
    errors = []
    
    # Required fields
    if not data.get('description', '').strip():
        errors.append("Description is required")
    
    # Priority validation
    if data.get('priority') and data['priority'] not in ['low', 'medium', 'high']:
        errors.append("Priority must be low, medium, or high")
    
    # Status validation
    if data.get('status') and data['status'] not in ['todo', 'in_progress', 'done']:
        errors.append("Status must be todo, in_progress, or done")
    
    # Date validation
    if data.get('due_date'):
        try:
            datetime.strptime(data['due_date'], '%Y-%m-%d')
        except ValueError:
            errors.append("Due date must be in YYYY-MM-DD format")
    
    # Hours validation
    if data.get('estimated_hours') and data['estimated_hours'] < 0:
        errors.append("Estimated hours cannot be negative")
    
    if data.get('actual_hours') and data['actual_hours'] < 0:
        errors.append("Actual hours cannot be negative")
    
    return errors
```

### Client Validation
```python
def validate_client_data(data):
    """Validate client data before creation/update."""
    errors = []
    
    # Required fields
    if not data.get('name', '').strip():
        errors.append("Client name is required")
    
    # Name uniqueness (for creation)
    if 'id' not in data:  # New client
        existing_client = session.query(Client).filter_by(name=data['name']).first()
        if existing_client:
            errors.append("Client name already exists")
    
    return errors
```

## 🔍 Query Examples

### Task Queries
```python
# Get all tasks
tasks = session.query(Task).all()

# Get incomplete tasks
incomplete_tasks = session.query(Task).filter(Task.done == False).all()

# Get tasks by priority
high_priority_tasks = session.query(Task).filter(Task.priority == 'high').all()

# Get tasks with due dates
tasks_with_due_dates = session.query(Task).filter(Task.due_date.isnot(None)).all()

# Get tasks by client
client_tasks = session.query(Task).filter(Task.client_id == client_id).all()

# Get tasks by category
dev_tasks = session.query(Task).filter(Task.category == 'Development').all()

# Get tasks with tags
urgent_tasks = session.query(Task).filter(Task.tags.contains('urgent')).all()

# Get subtasks
subtasks = session.query(Task).filter(Task.parent_id.isnot(None)).all()

# Get tasks with time tracking
active_tasks = session.query(Task).filter(Task.started_at.isnot(None)).all()
```

### Client Queries
```python
# Get all clients
clients = session.query(Client).all()

# Get client by name
client = session.query(Client).filter(Client.name == 'Acme Corp').first()

# Get clients with tasks
clients_with_tasks = session.query(Client).join(Task).distinct().all()
```

### Analytics Queries
```python
# Task completion statistics
completed_tasks = session.query(Task).filter(Task.done == True).count()
total_tasks = session.query(Task).count()
completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0

# Time tracking statistics
total_time = session.query(func.sum(TaskTimeEntry.duration_minutes)).scalar() or 0
avg_time_per_task = session.query(func.avg(TaskTimeEntry.duration_minutes)).scalar() or 0

# Priority distribution
priority_stats = session.query(
    Task.priority,
    func.count(Task.id)
).group_by(Task.priority).all()

# Category distribution
category_stats = session.query(
    Task.category,
    func.count(Task.id)
).filter(Task.category.isnot(None)).group_by(Task.category).all()
```

## 🗄️ Database Schema

### Tables Overview
- `tasks` - Main task storage
- `clients` - Client information
- `task_dependencies` - Task dependency relationships
- `task_comments` - Task comments
- `task_time_entries` - Time tracking entries
- `reminders` - Scheduled reminders
- `habits` - Habit tracking
- `calendar_tokens` - Google Calendar integration
- `metrics` - System metrics and analytics

### Indexes
```sql
-- Task indexes
CREATE INDEX idx_tasks_done ON tasks(done);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_client_id ON tasks(client_id);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_tasks_category ON tasks(category);
CREATE INDEX idx_tasks_parent_id ON tasks(parent_id);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);

-- Client indexes
CREATE INDEX idx_clients_name ON clients(name);

-- Time entry indexes
CREATE INDEX idx_time_entries_task_id ON task_time_entries(task_id);
CREATE INDEX idx_time_entries_started_at ON task_time_entries(started_at);

-- Metrics indexes
CREATE INDEX idx_metrics_type ON metrics(metric_type);
CREATE INDEX idx_metrics_timestamp ON metrics(timestamp);
```

## 🔄 Model Migrations

### Alembic Migration Example
```python
# alembic/versions/xxx_add_task_metadata.py
def upgrade():
    op.add_column('tasks', sa.Column('priority', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('due_date', sa.Date(), nullable=True))
    op.add_column('tasks', sa.Column('category', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('status', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('estimated_hours', sa.Float(), nullable=True))
    op.add_column('tasks', sa.Column('actual_hours', sa.Float(), nullable=True))
    op.add_column('tasks', sa.Column('started_at', sa.DateTime(), nullable=True))
    op.add_column('tasks', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('tags', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('description_rich', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('tasks', 'description_rich')
    op.drop_column('tasks', 'tags')
    op.drop_column('tasks', 'parent_id')
    op.drop_column('tasks', 'started_at')
    op.drop_column('tasks', 'actual_hours')
    op.drop_column('tasks', 'estimated_hours')
    op.drop_column('tasks', 'status')
    op.drop_column('tasks', 'category')
    op.drop_column('tasks', 'due_date')
    op.drop_column('tasks', 'priority')
```

## 📚 Related References

- [Commands API](commands.md) - Command reference
- [Events API](events.md) - Event system reference
- [Data Layer Guide](../../developer-guide/architecture/data-layer.md) - Detailed data layer documentation
- [Repository Pattern](../../developer-guide/architecture/data-layer.md) - Data access patterns

---

**Last Updated**: June 28, 2025 