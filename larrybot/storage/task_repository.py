from sqlalchemy.orm import Session
from larrybot.models.task import Task
from larrybot.models.task_dependency import TaskDependency
from larrybot.models.task_time_entry import TaskTimeEntry
from larrybot.models.task_comment import TaskComment
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
from sqlalchemy import or_, and_, func
from larrybot.utils.caching import cached, cache_invalidate, cache_clear
from larrybot.utils.background_processing import background_task, submit_background_job
import logging

logger = logging.getLogger(__name__)

class TaskRepository:
    """
    Repository for CRUD operations on Task model with advanced features and caching.
    """
    def __init__(self, session: Session):
        self.session = session

    def add_task(self, description: str) -> Task:
        task = Task(description=description, done=False)
        self.session.add(task)
        self.session.commit()
        
        # Invalidate task list caches
        cache_invalidate('list_incomplete_tasks')
        cache_invalidate('task_statistics')
        
        return task

    @cached(ttl=60.0)  # Cache for 1 minute - frequently accessed
    def list_incomplete_tasks(self) -> List[Task]:
        """Get all incomplete tasks with caching for improved performance."""
        logger.debug("Fetching incomplete tasks from database")
        return self.session.query(Task).filter_by(done=False).all()

    @cached(ttl=300.0)  # Cache for 5 minutes
    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Get task by ID with caching."""
        return self.session.query(Task).filter_by(id=task_id).first()

    def mark_task_done(self, task_id: int) -> Optional[Task]:
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task and not task.done:
            task.done = True
            task.status = 'Done'
            self.session.commit()
            
            # Invalidate related caches
            cache_invalidate('list_incomplete_tasks')
            cache_invalidate('task_statistics')
            cache_invalidate('analytics')  # Invalidate analytics caches
            cache_invalidate(f'get_task_by_id')
            
            return task
        return None

    def edit_task(self, task_id: int, new_description: str) -> Optional[Task]:
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            task.description = new_description
            self.session.commit()
            
            # Invalidate caches
            cache_invalidate(f'get_task_by_id')
            cache_invalidate('list_incomplete_tasks')
            
            return task
        return None

    def remove_task(self, task_id: int) -> Optional[Task]:
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            self.session.delete(task)
            self.session.commit()
            
            # Invalidate all related caches
            cache_invalidate('list_incomplete_tasks')
            cache_invalidate('task_statistics')
            cache_invalidate('analytics')  # Invalidate analytics caches
            cache_invalidate('get_task_by_id')  # Pattern match for all get_task_by_id calls
            
            return task
        return None

    def assign_task_to_client(self, task_id: int, client_name: str) -> Optional[Task]:
        from larrybot.models.client import Client
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if not task:
            return None
        client = self.session.query(Client).filter_by(name=client_name).first()
        if not client:
            return None
        task.client_id = client.id
        self.session.commit()
        
        # Invalidate caches
        cache_invalidate(f'get_task_by_id')
        cache_invalidate('get_tasks_by_client')
        
        return task

    def unassign_task(self, task_id: int) -> Optional[Task]:
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if not task:
            return None
        task.client_id = None
        self.session.commit()
        
        # Invalidate caches
        cache_invalidate(f'get_task_by_id')
        cache_invalidate('get_tasks_by_client')
        
        return task

    @cached(ttl=180.0)  # Cache for 3 minutes
    def get_tasks_by_client(self, client_name: str) -> List[Task]:
        """Get tasks by client with caching."""
        from larrybot.models.client import Client
        client = self.session.query(Client).filter_by(name=client_name).first()
        if not client:
            return []
        return self.session.query(Task).filter_by(client_id=client.id).all()

    def add_task_with_metadata(
        self, 
        description: str, 
        priority: str = "Medium",
        due_date: Optional[datetime] = None,
        category: Optional[str] = None,
        estimated_hours: Optional[float] = None,
        tags: Optional[List[str]] = None,
        parent_id: Optional[int] = None
    ) -> Task:
        """Create task with advanced metadata."""
        task = Task(
            description=description,
            priority=priority,
            due_date=due_date,
            category=category,
            estimated_hours=estimated_hours,
            parent_id=parent_id,
            tags=json.dumps(tags) if tags else None
        )
        self.session.add(task)
        self.session.commit()
        
        # Invalidate caches
        cache_invalidate('list_incomplete_tasks')
        cache_invalidate('task_statistics')
        cache_invalidate('analytics')  # Invalidate analytics caches
        cache_invalidate('get_tasks_by_priority')
        cache_invalidate('get_tasks_by_category')
        
        return task

    @cached(ttl=300.0)  # Cache for 5 minutes
    def get_tasks_by_priority(self, priority: str) -> List[Task]:
        """Get all tasks with a specific priority - cached."""
        return self.session.query(Task).filter_by(priority=priority).all()

    def update_priority(self, task_id: int, priority: str) -> Optional[Task]:
        """Update task priority."""
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            task.priority = priority
            self.session.commit()
            
            # Invalidate caches
            cache_invalidate(f'get_task_by_id')
            cache_invalidate('get_tasks_by_priority')
            
            return task
        return None

    @cached(ttl=180.0)  # Cache for 3 minutes - changes frequently
    def get_overdue_tasks(self) -> List[Task]:
        """Get all overdue tasks - cached with shorter TTL."""
        now = datetime.utcnow()
        return self.session.query(Task).filter(
            Task.due_date < now,
            Task.done == False
        ).all()

    @cached(ttl=300.0)
    def get_tasks_due_between(self, start_date: datetime, end_date: datetime) -> List[Task]:
        """Get tasks due between two dates - cached."""
        return self.session.query(Task).filter(
            Task.due_date >= start_date,
            Task.due_date <= end_date
        ).all()

    def get_tasks_due_today(self) -> List[Task]:
        """Get tasks due today."""
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        return self.get_tasks_due_between(start_of_day, end_of_day)

    def update_due_date(self, task_id: int, due_date: datetime) -> Optional[Task]:
        """Update task due date."""
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            task.due_date = due_date
            self.session.commit()
            
            # Invalidate caches
            cache_invalidate(f'get_task_by_id')
            cache_invalidate('get_overdue_tasks')
            cache_invalidate('get_tasks_due_between')
            
            return task
        return None

    @cached(ttl=300.0)
    def get_tasks_by_category(self, category: str) -> List[Task]:
        """Get all tasks in a specific category - cached."""
        return self.session.query(Task).filter_by(category=category).all()

    @cached(ttl=600.0)  # Cache for 10 minutes - categories change infrequently  
    def get_all_categories(self) -> List[str]:
        """Get all unique categories - cached with longer TTL."""
        categories = self.session.query(Task.category).filter(
            Task.category.isnot(None)
        ).distinct().all()
        return [cat[0] for cat in categories if cat[0]]

    def update_category(self, task_id: int, category: str) -> Optional[Task]:
        """Update task category."""
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            task.category = category
            self.session.commit()
            
            # Invalidate caches
            cache_invalidate(f'get_task_by_id')
            cache_invalidate('get_tasks_by_category')
            cache_invalidate('get_all_categories')
            
            return task
        return None

    @cached(ttl=300.0)
    def get_tasks_by_status(self, status: str) -> List[Task]:
        """Get all tasks with a specific status - cached."""
        return self.session.query(Task).filter_by(status=status).all()

    def update_status(self, task_id: int, status: str) -> Optional[Task]:
        """Update task status."""
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            task.status = status
            if status == 'Done':
                task.done = True
            self.session.commit()
            
            # Invalidate caches
            cache_invalidate(f'get_task_by_id')
            cache_invalidate('get_tasks_by_status')
            cache_invalidate('list_incomplete_tasks')
            cache_invalidate('task_statistics')
            cache_invalidate('analytics')  # Invalidate analytics caches
            
            return task
        return None

    def start_time_tracking(self, task_id: int) -> bool:
        """Start time tracking for a task."""
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task and not task.started_at:
            task.started_at = datetime.utcnow()
            self.session.commit()
            return True
        return False

    def stop_time_tracking(self, task_id: int) -> Optional[float]:
        """Stop time tracking and return duration in hours."""
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task and task.started_at:
            end_time = datetime.utcnow()
            duration = (end_time - task.started_at).total_seconds() / 3600  # Convert to hours
            task.actual_hours = (task.actual_hours or 0) + duration
            task.started_at = None
            self.session.commit()
            return duration
        return None

    def add_time_entry(self, task_id: int, started_at: datetime, ended_at: datetime, description: str = "") -> bool:
        """Add a time entry for a task."""
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            duration_minutes = int((ended_at - started_at).total_seconds() / 60)
            time_entry = TaskTimeEntry(
                task_id=task_id,
                started_at=started_at,
                ended_at=ended_at,
                duration_minutes=duration_minutes,
                description=description
            )
            self.session.add(time_entry)
            self.session.commit()
            return True
        return False

    def get_task_time_summary(self, task_id: int) -> Dict[str, float]:
        """Get time tracking summary for a task."""
        task = self.get_task_by_id(task_id)
        if not task:
            return {}
        
        total_actual = float(task.actual_hours or 0)
        total_estimated = float(task.estimated_hours or 0)
        
        # Get time entries
        time_entries = self.session.query(TaskTimeEntry).filter_by(task_id=task_id).all()
        total_from_entries = sum(entry.duration_minutes for entry in time_entries) / 60.0
        
        return {
            'estimated_hours': total_estimated,
            'actual_hours': total_actual,
            'time_entries_hours': total_from_entries,
            'time_entries_count': len(time_entries)
        }

    def add_task_dependency(self, task_id: int, dependency_id: int) -> bool:
        """Add a dependency between tasks."""
        if task_id == dependency_id:
            return False
        
        # Check if dependency already exists
        existing = self.session.query(TaskDependency).filter_by(
            task_id=task_id,
            dependency_id=dependency_id
        ).first()
        
        if existing:
            return False
        
        dependency = TaskDependency(task_id=task_id, dependency_id=dependency_id)
        self.session.add(dependency)
        self.session.commit()
        return True

    def remove_task_dependency(self, task_id: int, dependency_id: int) -> bool:
        """Remove a dependency between tasks."""
        dependency = self.session.query(TaskDependency).filter_by(
            task_id=task_id,
            dependency_id=dependency_id
        ).first()
        
        if dependency:
            self.session.delete(dependency)
            self.session.commit()
            return True
        return False

    def get_task_dependencies(self, task_id: int) -> List[Task]:
        """Get all tasks that this task depends on."""
        dependencies = self.session.query(TaskDependency).filter_by(task_id=task_id).all()
        dependency_ids = [dep.dependency_id for dep in dependencies]
        return self.session.query(Task).filter(Task.id.in_(dependency_ids)).all()

    def get_task_dependents(self, task_id: int) -> List[Task]:
        """Get all tasks that depend on this task."""
        dependents = self.session.query(TaskDependency).filter_by(dependency_id=task_id).all()
        dependent_ids = [dep.task_id for dep in dependents]
        return self.session.query(Task).filter(Task.id.in_(dependent_ids)).all()

    def add_subtask(self, parent_id: int, description: str) -> Optional[Task]:
        """Add a subtask to a parent task."""
        parent = self.get_task_by_id(parent_id)
        if parent:
            return self.add_task_with_metadata(
                description=description,
                parent_id=parent_id
            )
        return None

    def get_subtasks(self, parent_id: int) -> List[Task]:
        """Get all subtasks of a parent task."""
        return self.session.query(Task).filter_by(parent_id=parent_id).all()

    def add_tags(self, task_id: int, tags: List[str]) -> Optional[Task]:
        """Add tags to a task."""
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            current_tags = json.loads(task.tags) if task.tags else []
            current_tags.extend(tags)
            task.tags = json.dumps(list(set(current_tags)))  # Remove duplicates
            self.session.commit()
            return task
        return None

    def remove_tags(self, task_id: int, tags: List[str]) -> Optional[Task]:
        """Remove tags from a task."""
        # Query directly to ensure we have a session-attached object
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task and task.tags:
            current_tags = json.loads(task.tags)
            current_tags = [tag for tag in current_tags if tag not in tags]
            task.tags = json.dumps(current_tags) if current_tags else None
            self.session.commit()
            return task
        return None

    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        """Get all tasks with a specific tag."""
        tasks = self.session.query(Task).filter(Task.tags.isnot(None)).all()
        return [task for task in tasks if task.tags and tag in json.loads(task.tags)]

    def get_tasks_with_filters(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        due_before: Optional[datetime] = None,
        due_after: Optional[datetime] = None,
        overdue_only: bool = False,
        client_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        done: Optional[bool] = None
    ) -> List[Task]:
        """Get tasks with advanced filtering."""
        query = self.session.query(Task)
        
        if status is not None:
            query = query.filter(Task.status == status)
        
        if priority is not None:
            query = query.filter(Task.priority == priority)
        
        if category is not None:
            query = query.filter(Task.category == category)
        
        if due_before is not None:
            query = query.filter(Task.due_date <= due_before)
        
        if due_after is not None:
            query = query.filter(Task.due_date >= due_after)
        
        if overdue_only:
            now = datetime.utcnow()
            query = query.filter(Task.due_date < now, Task.done == False)
        
        if client_id is not None:
            query = query.filter(Task.client_id == client_id)
        
        if parent_id is not None:
            query = query.filter(Task.parent_id == parent_id)
        
        if done is not None:
            query = query.filter(Task.done == done)
        
        return query.all()

    def search_tasks_by_text(self, search_text: str, case_sensitive: bool = False) -> List[Task]:
        """Search tasks by text in description, comments, and tags."""
        if not search_text.strip():
            return []
        
        query = self.session.query(Task)
        
        if case_sensitive:
            # Case-sensitive search
            query = query.filter(
                or_(
                    Task.description.contains(search_text),
                    Task.tags.contains(search_text)
                )
            )
        else:
            # Case-insensitive search
            search_lower = search_text.lower()
            query = query.filter(
                or_(
                    func.lower(Task.description).contains(search_lower),
                    func.lower(Task.tags).contains(search_lower)
                )
            )
        
        # Also search in comments
        comment_tasks = self.session.query(TaskComment.task_id).filter(
            func.lower(TaskComment.comment).contains(search_lower)
        ).distinct()
        
        comment_task_ids = [row[0] for row in comment_tasks]
        
        if comment_task_ids:
            # Combine with main search results
            main_results = query.all()
            comment_results = self.session.query(Task).filter(Task.id.in_(comment_task_ids)).all()
            
            # Merge and deduplicate
            all_tasks = main_results + comment_results
            seen_ids = set()
            unique_tasks = []
            for task in all_tasks:
                if task.id not in seen_ids:
                    seen_ids.add(task.id)
                    unique_tasks.append(task)
            return unique_tasks
        
        return query.all()

    def get_tasks_with_advanced_filters(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        due_before: Optional[datetime] = None,
        due_after: Optional[datetime] = None,
        overdue_only: bool = False,
        client_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        done: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        has_comments: Optional[bool] = None,
        has_time_entries: Optional[bool] = None,
        estimated_hours_min: Optional[float] = None,
        estimated_hours_max: Optional[float] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: Optional[int] = None
    ) -> List[Task]:
        """Get tasks with advanced filtering and sorting options."""
        query = self.session.query(Task)
        
        # Basic filters
        if status is not None:
            query = query.filter(Task.status == status)
        
        if priority is not None:
            query = query.filter(Task.priority == priority)
        
        if category is not None:
            query = query.filter(Task.category == category)
        
        if due_before is not None:
            query = query.filter(Task.due_date <= due_before)
        
        if due_after is not None:
            query = query.filter(Task.due_date >= due_after)
        
        if overdue_only:
            now = datetime.utcnow()
            query = query.filter(Task.due_date < now, Task.done == False)
        
        if client_id is not None:
            query = query.filter(Task.client_id == client_id)
        
        if parent_id is not None:
            query = query.filter(Task.parent_id == parent_id)
        
        if done is not None:
            query = query.filter(Task.done == done)
        
        # Advanced filters
        if tags:
            for tag in tags:
                query = query.filter(Task.tags.contains(tag))
        
        if has_comments is not None:
            if has_comments:
                # Tasks with comments
                commented_tasks = self.session.query(TaskComment.task_id).distinct()
                task_ids = [row[0] for row in commented_tasks]
                if task_ids:
                    query = query.filter(Task.id.in_(task_ids))
                else:
                    return []  # No tasks with comments
            else:
                # Tasks without comments
                commented_tasks = self.session.query(TaskComment.task_id).distinct()
                task_ids = [row[0] for row in commented_tasks]
                if task_ids:
                    query = query.filter(~Task.id.in_(task_ids))
        
        if has_time_entries is not None:
            if has_time_entries:
                # Tasks with time entries
                from larrybot.models.task_time_entry import TaskTimeEntry
                timed_tasks = self.session.query(TaskTimeEntry.task_id).distinct()
                task_ids = [row[0] for row in timed_tasks]
                if task_ids:
                    query = query.filter(Task.id.in_(task_ids))
                else:
                    return []  # No tasks with time entries
            else:
                # Tasks without time entries
                from larrybot.models.task_time_entry import TaskTimeEntry
                timed_tasks = self.session.query(TaskTimeEntry.task_id).distinct()
                task_ids = [row[0] for row in timed_tasks]
                if task_ids:
                    query = query.filter(~Task.id.in_(task_ids))
        
        if estimated_hours_min is not None:
            query = query.filter(Task.estimated_hours >= estimated_hours_min)
        
        if estimated_hours_max is not None:
            query = query.filter(Task.estimated_hours <= estimated_hours_max)
        
        if created_after is not None:
            query = query.filter(Task.created_at >= created_after)
        
        if created_before is not None:
            query = query.filter(Task.created_at <= created_before)
        
        # Sorting
        sort_column = getattr(Task, sort_by, Task.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Limiting
        if limit is not None:
            query = query.limit(limit)
        
        return query.all()

    def get_tasks_by_multiple_tags(self, tags: List[str], match_all: bool = False) -> List[Task]:
        """Get tasks by multiple tags with option to match all or any."""
        if not tags:
            return []
        
        tasks = self.session.query(Task).filter(Task.tags.isnot(None)).all()
        
        if match_all:
            # Must have ALL tags
            return [task for task in tasks if task.tags and all(tag in json.loads(task.tags) for tag in tags)]
        else:
            # Must have ANY tag
            return [task for task in tasks if task.tags and any(tag in json.loads(task.tags) for tag in tags)]

    def get_tasks_by_time_range(self, start_date: datetime, end_date: datetime, include_completed: bool = True) -> List[Task]:
        """Get tasks created or due within a specific time range."""
        query = self.session.query(Task).filter(
            or_(
                and_(Task.created_at >= start_date, Task.created_at <= end_date),
                and_(Task.due_date >= start_date, Task.due_date <= end_date)
            )
        )
        
        if not include_completed:
            query = query.filter(Task.done == False)
        
        return query.all()

    def get_tasks_by_priority_range(self, min_priority: str, max_priority: str) -> List[Task]:
        """Get tasks within a priority range."""
        priority_order = ['Low', 'Medium', 'High', 'Critical']
        
        try:
            min_index = priority_order.index(min_priority)
            max_index = priority_order.index(max_priority)
        except ValueError:
            return []
        
        if min_index > max_index:
            min_index, max_index = max_index, min_index
        
        valid_priorities = priority_order[min_index:max_index + 1]
        return self.session.query(Task).filter(Task.priority.in_(valid_priorities)).all()

    def bulk_update_status(self, task_ids: List[int], status: str) -> int:
        """Update status for multiple tasks."""
        updated = self.session.query(Task).filter(Task.id.in_(task_ids)).update(
            {Task.status: status, Task.done: (status == 'Done')},
            synchronize_session=False
        )
        self.session.commit()
        
        # Clear cache to ensure consistency
        cache_clear()
        
        return updated

    def bulk_update_priority(self, task_ids: List[int], priority: str) -> int:
        """Update priority for multiple tasks."""
        updated = self.session.query(Task).filter(Task.id.in_(task_ids)).update(
            {Task.priority: priority},
            synchronize_session=False
        )
        self.session.commit()
        
        # Clear cache to ensure consistency
        cache_clear()
        
        return updated

    def bulk_update_category(self, task_ids: List[int], category: str) -> int:
        """Update category for multiple tasks."""
        updated = self.session.query(Task).filter(Task.id.in_(task_ids)).update(
            {Task.category: category},
            synchronize_session=False
        )
        self.session.commit()
        
        # Clear cache to ensure consistency
        cache_clear()
        
        return updated

    def bulk_assign_to_client(self, task_ids: List[int], client_name: str) -> int:
        """Assign multiple tasks to a client."""
        # First get the client
        from larrybot.storage.client_repository import ClientRepository
        client_repo = ClientRepository(self.session)
        client = client_repo.get_client_by_name(client_name)
        if not client:
            return 0
        
        # Update tasks with client_id
        updated = self.session.query(Task).filter(Task.id.in_(task_ids)).update(
            {Task.client_id: client.id},
            synchronize_session=False
        )
        self.session.commit()
        
        # Clear cache to ensure consistency
        cache_clear()
        
        return updated

    def bulk_delete_tasks(self, task_ids: List[int]) -> int:
        """Delete multiple tasks."""
        deleted = self.session.query(Task).filter(Task.id.in_(task_ids)).delete(
            synchronize_session=False
        )
        self.session.commit()
        
        # Clear entire cache after bulk deletion to ensure consistency
        # This is needed because cache keys are hashed and we can't target specific entries
        cache_clear()
        
        return deleted

    def add_comment(self, task_id: int, comment: str) -> Optional[TaskComment]:
        """Add a comment to a task."""
        task = self.get_task_by_id(task_id)
        if task:
            task_comment = TaskComment(task_id=task_id, comment=comment)
            self.session.add(task_comment)
            self.session.commit()
            return task_comment
        return None

    def get_comments(self, task_id: int) -> List[TaskComment]:
        """Get all comments for a task."""
        return self.session.query(TaskComment).filter_by(task_id=task_id).order_by(TaskComment.created_at).all()

    # === ANALYTICS FUNCTIONS WITH BACKGROUND PROCESSING === #

    @cached(ttl=900.0)  # Cache for 15 minutes - expensive computation
    def get_task_statistics(self) -> Dict[str, Any]:
        """Get comprehensive task statistics with caching."""
        return self._compute_task_statistics()

    def _compute_task_statistics(self) -> Dict[str, Any]:
        """Compute task statistics (called from cache or background)."""
        logger.debug("Computing task statistics from database")
        
        total_tasks = self.session.query(Task).count()
        completed_tasks = self.session.query(Task).filter_by(done=True).count()
        pending_tasks = total_tasks - completed_tasks
        
        # Priority distribution
        priority_stats = self.session.query(
            Task.priority, func.count(Task.id)
        ).group_by(Task.priority).all()
        
        # Status distribution  
        status_stats = self.session.query(
            Task.status, func.count(Task.id)
        ).group_by(Task.status).all()
        
        # Overdue tasks
        now = datetime.utcnow()
        overdue_count = self.session.query(Task).filter(
            Task.due_date < now,
            Task.done == False
        ).count()
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'incomplete_tasks': pending_tasks,  # Add the expected key for tests
            'overdue_tasks': overdue_count,
            'completion_rate': (completed_tasks / max(1, total_tasks)) * 100,
            'priority_distribution': dict(priority_stats),
            'status_distribution': dict(status_stats)
        }

    def get_task_statistics_async(self) -> str:
        """Get task statistics via background processing."""
        job_id = submit_background_job(
            self._compute_task_statistics,
            priority=3,  # Medium priority
            job_id=f"task_stats_{int(datetime.utcnow().timestamp())}"
        )
        return job_id

    @cached(ttl=1800.0)  # Cache for 30 minutes - very expensive computation
    def get_advanced_task_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get advanced analytics with caching."""
        return self._compute_advanced_analytics(days)

    def _compute_advanced_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Compute advanced analytics (called from cache or background)."""
        logger.debug(f"Computing advanced analytics for {days} days")
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Tasks created in period
        tasks_created = self.session.query(Task).filter(
            Task.created_at >= start_date,
            Task.created_at <= end_date
        ).count()
        
        # Tasks completed in period
        tasks_completed = self.session.query(Task).filter(
            Task.done == True,
            Task.created_at >= start_date,
            Task.created_at <= end_date
        ).count()
        
        # Overall task statistics 
        total_tasks = self.session.query(Task).count()
        completed_tasks_total = self.session.query(Task).filter_by(done=True).count()
        
        # Priority analysis
        priority_analysis = {}
        priorities = ['High', 'Medium', 'Low']
        for priority in priorities:
            priority_tasks = self.session.query(Task).filter_by(priority=priority).all()
            priority_analysis[priority] = {
                'total': len(priority_tasks),
                'completed': sum(1 for task in priority_tasks if task.done)
            }
        
        # Average completion time for completed tasks
        completed_tasks = self.session.query(Task).filter(
            Task.done == True,
            Task.created_at >= start_date
        ).all()
        
        if completed_tasks:
            completion_times = []
            for task in completed_tasks:
                if task.updated_at and task.created_at:
                    duration = (task.updated_at - task.created_at).total_seconds() / 3600  # hours
                    completion_times.append(duration)
            
            avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        else:
            avg_completion_time = 0
        
        # Task creation trend (daily breakdown)
        daily_stats = {}
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            created_count = self.session.query(Task).filter(
                Task.created_at >= day_start,
                Task.created_at < day_end
            ).count()
            
            completed_count = self.session.query(Task).filter(
                Task.done == True,
                Task.updated_at >= day_start,
                Task.updated_at < day_end
            ).count()
            
            daily_stats[day.strftime('%Y-%m-%d')] = {
                'created': created_count,
                'completed': completed_count
            }
        
        return {
            'overall_stats': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks_total,
                'completion_rate': round((completed_tasks_total / max(1, total_tasks)) * 100, 1)
            },
            'priority_analysis': priority_analysis,
            'period_days': days,
            'tasks_created': tasks_created,
            'tasks_completed': tasks_completed,
            'avg_completion_time_hours': round(avg_completion_time, 2),
            'productivity_score': round((tasks_completed / max(1, tasks_created)) * 100, 1),
            'daily_breakdown': daily_stats
        }

    def get_advanced_task_analytics_async(self, days: int = 30) -> str:
        """Get advanced analytics via background processing."""
        job_id = submit_background_job(
            self._compute_advanced_analytics,
            days,
            priority=4,  # Lower priority - heavy computation
            job_id=f"advanced_analytics_{days}d_{int(datetime.utcnow().timestamp())}"
        )
        return job_id

    @cached(ttl=1800.0)  # Cache for 30 minutes - very expensive computation
    def get_productivity_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get productivity report with caching."""
        return self._compute_productivity_report(start_date, end_date)

    def _compute_productivity_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Compute productivity report (called from cache or background)."""
        logger.debug(f"Computing productivity report from {start_date} to {end_date}")
        
        # Tasks in time range
        tasks_in_range = self.session.query(Task).filter(
            Task.created_at >= start_date,
            Task.created_at <= end_date
        ).all()
        
        # Completion metrics
        total_tasks = len(tasks_in_range)
        completed_tasks = sum(1 for task in tasks_in_range if task.done)
        
        # Time tracking metrics
        total_estimated_hours = sum(task.estimated_hours or 0 for task in tasks_in_range)
        total_actual_hours = sum(task.actual_hours or 0 for task in tasks_in_range)
        
        # Priority analysis
        priority_breakdown = {}
        for task in tasks_in_range:
            priority = task.priority or 'Unknown'
            if priority not in priority_breakdown:
                priority_breakdown[priority] = {'total': 0, 'completed': 0}
            priority_breakdown[priority]['total'] += 1
            if task.done:
                priority_breakdown[priority]['completed'] += 1
        
        # Calculate productivity metrics
        completion_rate = (completed_tasks / max(1, total_tasks)) * 100
        time_efficiency = (total_estimated_hours / max(1, total_actual_hours)) * 100 if total_actual_hours > 0 else 0
        
        return {
            'summary': {
                'tasks_created': total_tasks,
                'tasks_completed': completed_tasks,
                'completion_rate': round(completion_rate, 1)
            },
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_rate': round(completion_rate, 1),
            'estimated_hours': round(total_estimated_hours, 1),
            'actual_hours': round(total_actual_hours, 1),
            'time_efficiency': round(time_efficiency, 1),
            'priority_breakdown': priority_breakdown
        }

    def get_productivity_report_async(self, start_date: datetime, end_date: datetime) -> str:
        """Get productivity report via background processing."""
        job_id = submit_background_job(
            self._compute_productivity_report,
            start_date,
            end_date,
            priority=4,  # Lower priority - heavy computation
            job_id=f"productivity_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        )
        return job_id 