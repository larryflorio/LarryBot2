from sqlalchemy.orm import Session, joinedload, selectinload
from larrybot.models.task import Task
from larrybot.models.task_dependency import TaskDependency
from larrybot.models.task_time_entry import TaskTimeEntry
from larrybot.models.task_comment import TaskComment
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
from sqlalchemy import or_, and_, func, text, desc, asc
from larrybot.utils.caching import cached, cache_invalidate, cache_clear
from larrybot.utils.cache_automation import auto_invalidate_cache, OperationType, invalidate_caches_for
from larrybot.utils.background_processing import background_task, submit_background_job
from larrybot.utils.datetime_utils import get_current_datetime, get_current_utc_datetime, get_today_date, get_start_of_day, get_end_of_day, get_utc_now
import logging
from larrybot.models.enums import TaskStatus
logger = logging.getLogger(__name__)


class TaskRepository:
    """
    Repository for CRUD operations on Task model with advanced features and caching.
    """

    def __init__(self, session: Session):
        self.session = session

    @auto_invalidate_cache(OperationType.TASK_CREATE)
    def add_task(self, description: str) ->Task:
        task = Task(description=description, done=False)
        self.session.add(task)
        self.session.commit()
        return task

    @cached(ttl=60.0)
    def list_incomplete_tasks(self) ->List[Task]:
        """List all incomplete tasks with optimized client loading."""
        return self.session.query(Task).options(joinedload(Task.client)
            ).filter_by(done=False).order_by(Task.created_at.desc()).all()

    @cached(ttl=300.0)
    def get_task_by_id(self, task_id: int) ->Optional[Task]:
        """Get task by ID with optimized relationship loading."""
        return self.session.query(Task).options(joinedload(Task.client),
            selectinload(Task.comments), selectinload(Task.time_entries),
            selectinload(Task.dependencies), selectinload(Task.dependents),
            selectinload(Task.children), selectinload(Task.attachments)
            ).filter_by(id=task_id).first()

    @auto_invalidate_cache(OperationType.TASK_STATUS_CHANGE)
    def mark_task_done(self, task_id: int) ->Optional[Task]:
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task and not task.done:
            task.done = True
            task.status = TaskStatus.DONE.value
            self.session.commit()
            return task
        return None

    @auto_invalidate_cache(OperationType.TASK_UPDATE)
    def edit_task(self, task_id: int, new_description: str) ->Optional[Task]:
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            task.description = new_description
            self.session.commit()
            return task
        return None

    @auto_invalidate_cache(OperationType.TASK_DELETE)
    def remove_task(self, task_id: int) ->Optional[Task]:
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            self.session.delete(task)
            self.session.commit()
            return task
        return None

    @auto_invalidate_cache(OperationType.TASK_CLIENT_CHANGE)
    def assign_task_to_client(self, task_id: int, client_name: str) ->Optional[
        Task]:
        from larrybot.models.client import Client
        result = self.session.query(Task, Client).outerjoin(Client, Task.
            client_id == Client.id).filter(Task.id == task_id).first()
        if not result:
            return None
        task, _ = result
        client = self.session.query(Client).filter_by(name=client_name).first()
        if not client:
            return None
        task.client_id = client.id
        self.session.commit()
        return task

    @auto_invalidate_cache(OperationType.TASK_CLIENT_CHANGE)
    def unassign_task(self, task_id: int) ->Optional[Task]:
        task = self.session.query(Task).filter_by(id=task_id).first()
        if not task:
            return None
        task.client_id = None
        self.session.commit()
        return task

    @cached(ttl=180.0)
    def get_tasks_by_client(self, client_name: str) ->List[Task]:
        """Get tasks by client with optimized join and caching."""
        from larrybot.models.client import Client
        return self.session.query(Task).join(Client, Task.client_id ==
            Client.id).options(joinedload(Task.client)).filter(Client.name ==
            client_name).order_by(Task.created_at.desc()).all()

    @auto_invalidate_cache(OperationType.TASK_CREATE)
    def add_task_with_metadata(self, description: str, priority: str=
        'Medium', due_date: Optional[datetime]=None, category: Optional[str
        ]=None, estimated_hours: Optional[float]=None, tags: Optional[List[
        str]]=None, parent_id: Optional[int]=None, client_id: Optional[int]
        =None) ->Task:
        """Create task with advanced metadata."""
        task = Task(description=description, priority=priority, due_date=
            due_date, category=category, estimated_hours=estimated_hours,
            parent_id=parent_id, client_id=client_id, tags=json.dumps(tags) if
            tags else None)
        self.session.add(task)
        self.session.commit()
        return task

    @cached(ttl=300.0)
    def get_tasks_by_priority(self, priority: str) ->List[Task]:
        """Get all tasks with a specific priority with optimized loading."""
        from larrybot.models.enums import TaskPriority
        priority_enum = TaskPriority.from_string(priority)
        if priority_enum:
            possible_values = [priority_enum.name, priority_enum.name.title
                (), priority_enum.value]
        else:
            possible_values = [priority]
        return self.session.query(Task).options(joinedload(Task.client)
            ).filter(Task._priority.in_(possible_values)).order_by(Task.
            created_at.desc()).all()

    @auto_invalidate_cache(OperationType.TASK_PRIORITY_CHANGE)
    def update_priority(self, task_id: int, priority: str) ->Optional[Task]:
        """Update task priority."""
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            task.priority = priority
            self.session.commit()
            return task
        return None

    @cached(ttl=180.0)
    def get_overdue_tasks(self) ->List[Task]:
        """Get all overdue tasks with optimized client loading."""
        now = get_current_utc_datetime()
        return self.session.query(Task).options(joinedload(Task.client)
            ).filter(Task.due_date < now, Task.done == False).order_by(Task
            .due_date.asc()).all()

    @cached(ttl=300.0)
    def get_tasks_due_between(self, start_date: datetime, end_date: datetime
        ) ->List[Task]:
        """Get tasks due between two dates with optimized loading."""
        return self.session.query(Task).options(joinedload(Task.client)
            ).filter(Task.due_date >= start_date, Task.due_date <= end_date
            ).order_by(Task.due_date.asc()).all()

    def get_tasks_due_today(self) ->List[Task]:
        """Get tasks due today."""
        today = get_today_date()
        start_of_day = get_start_of_day()
        end_of_day = get_end_of_day()
        return self.get_tasks_due_between(start_of_day, end_of_day)

    @auto_invalidate_cache(OperationType.TASK_DUE_DATE_CHANGE)
    def update_due_date(self, task_id: int, due_date: datetime) ->Optional[Task
        ]:
        """Update task due date."""
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            task.due_date = due_date
            self.session.commit()
            return task
        return None

    @cached(ttl=300.0)
    def get_tasks_by_category(self, category: str) ->List[Task]:
        """Get all tasks in a specific category with optimized loading."""
        return self.session.query(Task).options(joinedload(Task.client)
            ).filter_by(category=category).order_by(Task.created_at.desc()
            ).all()

    @cached(ttl=600.0)
    def get_all_categories(self) ->List[str]:
        """Get all unique categories - cached with longer TTL."""
        categories = self.session.query(Task.category).filter(Task.category
            .isnot(None)).distinct().all()
        return [cat[0] for cat in categories if cat[0]]

    @auto_invalidate_cache(OperationType.TASK_CATEGORY_CHANGE)
    def update_category(self, task_id: int, category: str) ->Optional[Task]:
        """Update task category."""
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            task.category = category
            self.session.commit()
            return task
        return None

    @cached(ttl=300.0)
    def get_tasks_by_status(self, status: str) ->List[Task]:
        """Get all tasks with a specific status with optimized loading."""
        from larrybot.models.enums import TaskStatus
        status_enum = TaskStatus.from_string(status)
        if status_enum:
            possible_values = [status_enum.value, status]
        else:
            possible_values = [status]
        return self.session.query(Task).options(joinedload(Task.client)
            ).filter(Task.status.in_(possible_values)).order_by(Task.
            created_at.desc()).all()

    @auto_invalidate_cache(OperationType.TASK_STATUS_CHANGE)
    def update_status(self, task_id: int, status: str) ->Optional[Task]:
        """Update task status."""
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            task.status = status
            if status == 'Done':
                task.done = True
            self.session.commit()
            return task
        return None

    def start_time_tracking(self, task_id: int) ->bool:
        """Start time tracking for a task."""
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task and not task.started_at:
            task.started_at = get_current_utc_datetime()
            self.session.commit()
            return True
        return False

    def stop_time_tracking(self, task_id: int) ->Optional[float]:
        """Stop time tracking and return duration in hours."""
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task and task.started_at:
            from larrybot.utils.datetime_utils import safe_datetime_arithmetic, get_current_utc_datetime
            end_time = get_current_utc_datetime()
            delta = safe_datetime_arithmetic(end_time, task.started_at)
            duration = max(0, delta.total_seconds() / 3600)
            task.actual_hours = (task.actual_hours or 0) + duration
            task.started_at = None
            self.session.commit()
            return duration
        return None

    def add_time_entry(self, task_id: int, started_at: datetime, ended_at:
        datetime, description: str='') ->bool:
        """Add a time entry for a task."""
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            duration_minutes = int((ended_at - started_at).total_seconds() / 60
                )
            duration_hours = duration_minutes / 60.0
            time_entry = TaskTimeEntry(task_id=task_id, started_at=
                started_at, ended_at=ended_at, duration_minutes=
                duration_minutes, description=description)
            self.session.add(time_entry)
            task.actual_hours = (task.actual_hours or 0) + duration_hours
            self.session.commit()
            return True
        return False

    def get_task_time_summary(self, task_id: int) ->Dict[str, float]:
        """Get time tracking summary for a task."""
        task = self.get_task_by_id(task_id)
        if not task:
            return {}
        total_actual = float(task.actual_hours or 0)
        total_estimated = float(task.estimated_hours or 0)
        time_entries = self.session.query(TaskTimeEntry).filter_by(task_id=
            task_id).all()
        total_from_entries = sum(entry.duration_minutes for entry in
            time_entries) / 60.0
        return {'estimated_hours': total_estimated, 'actual_hours':
            total_actual, 'time_entries_hours': total_from_entries,
            'time_entries_count': len(time_entries)}

    def add_task_dependency(self, task_id: int, dependency_id: int) ->bool:
        """Add a dependency between tasks."""
        if task_id == dependency_id:
            return False
        existing = self.session.query(TaskDependency).filter_by(task_id=
            task_id, dependency_id=dependency_id).first()
        if existing:
            return False
        dependency = TaskDependency(task_id=task_id, dependency_id=
            dependency_id)
        self.session.add(dependency)
        self.session.commit()
        return True

    def remove_task_dependency(self, task_id: int, dependency_id: int) ->bool:
        """Remove a dependency between tasks."""
        dependency = self.session.query(TaskDependency).filter_by(task_id=
            task_id, dependency_id=dependency_id).first()
        if dependency:
            self.session.delete(dependency)
            self.session.commit()
            return True
        return False

    def get_task_dependencies(self, task_id: int) ->List[Task]:
        """Get task dependencies with optimized loading."""
        return self.session.query(Task).join(TaskDependency, Task.id ==
            TaskDependency.dependency_id).options(joinedload(Task.client)
            ).filter(TaskDependency.task_id == task_id).all()

    def get_task_dependents(self, task_id: int) ->List[Task]:
        """Get task dependents with optimized loading."""
        return self.session.query(Task).join(TaskDependency, Task.id ==
            TaskDependency.task_id).options(joinedload(Task.client)).filter(
            TaskDependency.dependency_id == task_id).all()

    def add_subtask(self, parent_id: int, description: str) ->Optional[Task]:
        """Add a subtask to a parent task."""
        parent = self.get_task_by_id(parent_id)
        if parent:
            return self.add_task_with_metadata(description=description,
                parent_id=parent_id)
        return None

    def get_subtasks(self, parent_id: int) ->List[Task]:
        """Get subtasks with optimized client loading."""
        return self.session.query(Task).options(joinedload(Task.client)
            ).filter_by(parent_id=parent_id).order_by(Task.created_at.asc()
            ).all()

    @auto_invalidate_cache(OperationType.TASK_UPDATE)
    def add_tags(self, task_id: int, tags: List[str]) ->Optional[Task]:
        """Add tags to a task."""
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task:
            current_tags = json.loads(task.tags) if task.tags else []
            current_tags.extend(tags)
            task.tags = json.dumps(list(set(current_tags)))
            self.session.commit()
            return task
        return None

    @auto_invalidate_cache(OperationType.TASK_UPDATE)
    def remove_tags(self, task_id: int, tags: List[str]) ->Optional[Task]:
        """Remove tags from a task."""
        task = self.session.query(Task).filter_by(id=task_id).first()
        if task and task.tags:
            current_tags = json.loads(task.tags)
            current_tags = [tag for tag in current_tags if tag not in tags]
            task.tags = json.dumps(current_tags) if current_tags else None
            self.session.commit()
            return task
        return None

    def get_tasks_by_tag(self, tag: str) ->List[Task]:
        """Get tasks by tag with optimized loading."""
        return self.session.query(Task).options(joinedload(Task.client)
            ).filter(Task.tags.like(f'%"{tag}"%')).order_by(Task.created_at
            .desc()).all()

    def get_tasks_with_filters(self, status: Optional[str]=None, priority:
        Optional[str]=None, category: Optional[str]=None, due_before:
        Optional[datetime]=None, due_after: Optional[datetime]=None,
        overdue_only: bool=False, client_id: Optional[int]=None, parent_id:
        Optional[int]=None, done: Optional[bool]=None) ->List[Task]:
        """Get tasks with filters using optimized query building."""
        query = self.session.query(Task).options(joinedload(Task.client))
        filters = []
        if status:
            from larrybot.models.enums import TaskStatus
            status_enum = TaskStatus.from_string(status)
            if status_enum:
                possible_values = [status_enum.value, status]
                filters.append(Task.status.in_(possible_values))
            else:
                filters.append(Task.status == status)
        if priority:
            from larrybot.models.enums import TaskPriority
            priority_enum = TaskPriority.from_string(priority)
            if priority_enum:
                possible_values = [priority_enum.name, priority_enum.name.
                    title(), priority_enum.value]
                filters.append(Task._priority.in_(possible_values))
            else:
                filters.append(Task._priority == priority)
        if category:
            filters.append(Task.category == category)
        if due_before:
            filters.append(Task.due_date < due_before)
        if due_after:
            filters.append(Task.due_date > due_after)
        if overdue_only:
            filters.append(Task.due_date < get_utc_now())
            filters.append(Task.done == False)
        if client_id:
            filters.append(Task.client_id == client_id)
        if parent_id:
            filters.append(Task.parent_id == parent_id)
        if done is not None:
            filters.append(Task.done == done)
        if filters:
            query = query.filter(and_(*filters))
        return query.order_by(Task.created_at.desc()).all()

    def search_tasks_by_text(self, search_text: str, case_sensitive: bool=False
        ) ->List[Task]:
        """Search tasks by text with optimized full-text search."""
        if not search_text.strip():
            return []
        if case_sensitive:
            search_filter = or_(Task.description.contains(search_text),
                Task.category.contains(search_text), Task.status.contains(
                search_text))
        else:
            search_lower = search_text.lower()
            search_filter = or_(func.lower(Task.description).contains(
                search_lower), func.lower(Task.category).contains(
                search_lower), func.lower(Task.status).contains(search_lower))
        return self.session.query(Task).options(joinedload(Task.client)
            ).filter(search_filter).order_by(Task.created_at.desc()).all()

    def get_tasks_with_advanced_filters(self, status: Optional[str]=None,
        priority: Optional[str]=None, category: Optional[str]=None,
        due_before: Optional[datetime]=None, due_after: Optional[datetime]=
        None, overdue_only: bool=False, client_id: Optional[int]=None,
        parent_id: Optional[int]=None, done: Optional[bool]=None, tags:
        Optional[List[str]]=None, has_comments: Optional[bool]=None,
        has_time_entries: Optional[bool]=None, estimated_hours_min:
        Optional[float]=None, estimated_hours_max: Optional[float]=None,
        created_after: Optional[datetime]=None, created_before: Optional[
        datetime]=None, sort_by: str='created_at', sort_order: str='desc',
        limit: Optional[int]=None) ->List[Task]:
        """Get tasks with advanced filtering and optimized queries."""
        query = self.session.query(Task).options(joinedload(Task.client))
        filters = []
        if status:
            from larrybot.models.enums import TaskStatus
            status_enum = TaskStatus.from_string(status)
            if status_enum:
                possible_values = [status_enum.value, status]
                filters.append(Task.status.in_(possible_values))
            else:
                filters.append(Task.status == status)
        if priority:
            from larrybot.models.enums import TaskPriority
            priority_enum = TaskPriority.from_string(priority)
            if priority_enum:
                possible_values = [priority_enum.name, priority_enum.name.
                    title(), priority_enum.value]
                filters.append(Task._priority.in_(possible_values))
            else:
                filters.append(Task._priority == priority)
        if category:
            filters.append(Task.category == category)
        if due_before:
            filters.append(Task.due_date <= due_before)
        if due_after:
            filters.append(Task.due_date >= due_after)
        if overdue_only:
            filters.append(Task.due_date < get_utc_now())
            filters.append(Task.done == False)
        if client_id:
            filters.append(Task.client_id == client_id)
        if parent_id:
            filters.append(Task.parent_id == parent_id)
        if done is not None:
            filters.append(Task.done == done)
        if estimated_hours_min is not None:
            filters.append(Task.estimated_hours >= estimated_hours_min)
        if estimated_hours_max is not None:
            filters.append(Task.estimated_hours <= estimated_hours_max)
        if created_after:
            filters.append(Task.created_at >= created_after)
        if created_before:
            filters.append(Task.created_at <= created_before)
        if tags:
            tag_filters = []
            for tag in tags:
                tag_filters.append(Task.tags.like(f'%"{tag}"%'))
            filters.append(or_(*tag_filters))
        if has_comments is not None:
            comment_subquery = self.session.query(TaskComment.task_id
                ).distinct()
            if has_comments:
                filters.append(Task.id.in_(comment_subquery))
            else:
                filters.append(~Task.id.in_(comment_subquery))
        if has_time_entries is not None:
            time_entry_subquery = self.session.query(TaskTimeEntry.task_id
                ).distinct()
            if has_time_entries:
                filters.append(Task.id.in_(time_entry_subquery))
            else:
                filters.append(~Task.id.in_(time_entry_subquery))
        if filters:
            query = query.filter(and_(*filters))
        sort_column = getattr(Task, sort_by, Task.created_at)
        if sort_order.lower() == 'asc':
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        if limit:
            query = query.limit(limit)
        return query.all()

    def get_tasks_by_multiple_tags(self, tags: List[str], match_all: bool=False
        ) ->List[Task]:
        """Get tasks by multiple tags with optimized query."""
        if not tags:
            return []
        if match_all:
            filters = [Task.tags.like(f'%"{tag}"%') for tag in tags]
            query_filter = and_(*filters)
        else:
            filters = [Task.tags.like(f'%"{tag}"%') for tag in tags]
            query_filter = or_(*filters)
        return self.session.query(Task).options(joinedload(Task.client)
            ).filter(query_filter).order_by(Task.created_at.desc()).all()

    def get_tasks_by_time_range(self, start_date: datetime, end_date:
        datetime, include_completed: bool=True) ->List[Task]:
        """Get tasks by creation time range with optimized filtering."""
        query = self.session.query(Task).options(joinedload(Task.client)
            ).filter(Task.created_at >= start_date, Task.created_at <= end_date
            )
        if not include_completed:
            query = query.filter(Task.done == False)
        return query.order_by(Task.created_at.desc()).all()

    def get_tasks_by_priority_range(self, min_priority: str, max_priority: str
        ) ->List[Task]:
        """Get tasks by priority range with optimized query."""
        from larrybot.models.enums import TaskPriority
        min_enum = TaskPriority.from_string(min_priority) or TaskPriority.LOW
        max_enum = TaskPriority.from_string(max_priority
            ) or TaskPriority.URGENT
        valid_priorities = []
        for priority_enum in TaskPriority:
            if min_enum.value <= priority_enum.value <= max_enum.value:
                valid_priorities.extend([priority_enum.name, priority_enum.
                    name.title(), priority_enum.value])
        return self.session.query(Task).options(joinedload(Task.client)
            ).filter(Task._priority.in_(valid_priorities)).order_by(Task.
            created_at.desc()).all()

    @auto_invalidate_cache(OperationType.BULK_OPERATION)
    def bulk_update_status(self, task_ids: List[int], status: str) ->int:
        """Bulk update task status - optimized for performance."""
        if not task_ids:
            return 0
        is_done = status in ['Done', 'Cancelled'] or hasattr(TaskStatus,
            'from_string') and TaskStatus.from_string(status
            ) and TaskStatus.from_string(status).is_completed
        updated_count = self.session.query(Task).filter(Task.id.in_(task_ids)
            ).update({'status': status, 'done': is_done},
            synchronize_session=False)
        self.session.commit()
        return updated_count

    @auto_invalidate_cache(OperationType.BULK_OPERATION)
    def bulk_update_priority(self, task_ids: List[int], priority: str) ->int:
        """Bulk update task priority - optimized for performance."""
        if not task_ids:
            return 0
        updated_count = self.session.query(Task).filter(Task.id.in_(task_ids)
            ).update({'_priority': priority}, synchronize_session=False)
        self.session.commit()
        return updated_count

    @auto_invalidate_cache(OperationType.BULK_OPERATION)
    def bulk_update_category(self, task_ids: List[int], category: str) ->int:
        """Bulk update task category - optimized for performance."""
        if not task_ids:
            return 0
        updated_count = self.session.query(Task).filter(Task.id.in_(task_ids)
            ).update({'category': category}, synchronize_session=False)
        self.session.commit()
        return updated_count

    @auto_invalidate_cache(OperationType.BULK_OPERATION)
    def bulk_assign_to_client(self, task_ids: List[int], client_name: str
        ) ->int:
        """Bulk assign tasks to client - optimized for performance."""
        if not task_ids:
            return 0
        from larrybot.models.client import Client
        client = self.session.query(Client).filter_by(name=client_name).first()
        if not client:
            return 0
        updated_count = self.session.query(Task).filter(Task.id.in_(task_ids)
            ).update({'client_id': client.id}, synchronize_session=False)
        self.session.commit()
        return updated_count

    @auto_invalidate_cache(OperationType.BULK_OPERATION)
    def bulk_delete_tasks(self, task_ids: List[int]) ->int:
        """Bulk delete tasks - optimized for performance."""
        if not task_ids:
            return 0
        try:
            comment_deleted = self.session.query(TaskComment).filter(
                TaskComment.task_id.in_(task_ids)).delete(synchronize_session
                =False)
            time_deleted = self.session.query(TaskTimeEntry).filter(
                TaskTimeEntry.task_id.in_(task_ids)).delete(synchronize_session
                =False)
            dep_deleted = self.session.query(TaskDependency).filter(or_(
                TaskDependency.task_id.in_(task_ids), TaskDependency.
                dependency_id.in_(task_ids))).delete(synchronize_session=False)
            subtask_deleted = self.session.query(Task).filter(Task.
                parent_id.in_(task_ids)).delete(synchronize_session=False)
            deleted_count = self.session.query(Task).filter(Task.id.in_(
                task_ids)).delete(synchronize_session=False)
            self.session.commit()
            self.session.expunge_all()
            return deleted_count
        except Exception as e:
            self.session.rollback()
            logger.error(f'Error in bulk_delete_tasks: {e}')
            raise

    def add_comment(self, task_id: int, comment: str) ->Optional[TaskComment]:
        """Add a comment to a task."""
        task = self.get_task_by_id(task_id)
        if task:
            task_comment = TaskComment(task_id=task_id, comment=comment)
            self.session.add(task_comment)
            self.session.commit()
            return task_comment
        return None

    def get_comments(self, task_id: int) ->List[TaskComment]:
        """Get task comments with optimized loading."""
        return self.session.query(TaskComment).filter_by(task_id=task_id
            ).order_by(TaskComment.created_at.asc()).all()

    @cached(ttl=900.0)
    def get_task_statistics(self) ->Dict[str, Any]:
        """Get comprehensive task statistics with caching."""
        return self._compute_task_statistics()

    def _compute_task_statistics(self) ->Dict[str, Any]:
        """Compute task statistics (called from cache or background)."""
        logger.debug('Computing task statistics from database')
        total_tasks = self.session.query(Task).count()
        completed_tasks = self.session.query(Task).filter_by(done=True).count()
        pending_tasks = total_tasks - completed_tasks
        priority_stats_raw = self.session.query(Task._priority, func.count(
            Task.id)).group_by(Task._priority).all()
        priority_distribution = {}
        for priority_raw, count in priority_stats_raw:
            try:
                from larrybot.models.enums import TaskPriority
                if isinstance(priority_raw, int):
                    priority_enum = TaskPriority(priority_raw)
                    priority_key = priority_enum.name.title()
                elif isinstance(priority_raw, str):
                    try:
                        int_value = int(priority_raw)
                        priority_enum = TaskPriority(int_value)
                        priority_key = priority_enum.name.title()
                    except (ValueError, TypeError):
                        priority_enum = TaskPriority.from_string(priority_raw)
                        priority_key = priority_enum.name.title(
                            ) if priority_enum else str(priority_raw)
                else:
                    priority_key = str(priority_raw)
                priority_distribution[priority_key] = count
            except Exception:
                priority_distribution[str(priority_raw)] = count
        status_stats = self.session.query(Task.status, func.count(Task.id)
            ).group_by(Task.status).all()
        now = get_utc_now()
        overdue_count = self.session.query(Task).filter(Task.due_date < now,
            Task.done == False).count()
        return {'total_tasks': total_tasks, 'completed_tasks':
            completed_tasks, 'pending_tasks': pending_tasks,
            'incomplete_tasks': pending_tasks, 'overdue_tasks':
            overdue_count, 'completion_rate': completed_tasks / max(1,
            total_tasks) * 100, 'priority_distribution':
            priority_distribution, 'status_distribution': dict(status_stats)}

    def get_task_statistics_async(self) ->str:
        """Get task statistics via background processing."""
        job_id = submit_background_job(self._compute_task_statistics,
            priority=3, job_id=f'task_stats_{int(get_utc_now().timestamp())}')
        return job_id

    @cached(ttl=1800.0)
    def get_advanced_task_analytics(self, days: int=30) ->Dict[str, Any]:
        """Get advanced analytics with caching."""
        return self._compute_advanced_analytics(days)

    def _compute_advanced_analytics(self, days: int=30) ->Dict[str, Any]:
        """Compute advanced analytics (called from cache or background)."""
        logger.debug(f'Computing advanced analytics for {days} days')
        end_date = get_utc_now()
        start_date = end_date - timedelta(days=days)
        tasks_created = self.session.query(Task).filter(Task.created_at >=
            start_date, Task.created_at <= end_date).count()
        tasks_completed = self.session.query(Task).filter(Task.done == True,
            Task.created_at >= start_date, Task.created_at <= end_date).count()
        total_tasks = self.session.query(Task).count()
        completed_tasks_total = self.session.query(Task).filter_by(done=True
            ).count()
        priority_analysis = {}
        all_tasks = self.session.query(Task).all()
        priority_groups = {}
        for task in all_tasks:
            try:
                priority_key = task.priority_enum.name.title()
                if priority_key not in priority_groups:
                    priority_groups[priority_key] = []
                priority_groups[priority_key].append(task)
            except Exception:
                priority_key = str(task.priority
                    ) if task.priority else 'Unknown'
                if priority_key not in priority_groups:
                    priority_groups[priority_key] = []
                priority_groups[priority_key].append(task)
        for priority_key, tasks in priority_groups.items():
            priority_analysis[priority_key] = {'total': len(tasks),
                'completed': sum(1 for task in tasks if task.done)}
        completed_tasks = self.session.query(Task).filter(Task.done == True,
            Task.created_at >= start_date).all()
        if completed_tasks:
            completion_times = []
            for task in completed_tasks:
                if task.updated_at and task.created_at:
                    duration = (task.updated_at - task.created_at
                        ).total_seconds() / 3600
                    completion_times.append(duration)
            avg_completion_time = sum(completion_times) / len(completion_times
                ) if completion_times else 0
        else:
            avg_completion_time = 0
        daily_stats = {}
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            created_count = self.session.query(Task).filter(Task.created_at >=
                day_start, Task.created_at < day_end).count()
            completed_count = self.session.query(Task).filter(Task.done == 
                True, Task.updated_at >= day_start, Task.updated_at < day_end
                ).count()
            daily_stats[day.strftime('%Y-%m-%d')] = {'created':
                created_count, 'completed': completed_count}
        return {'overall_stats': {'total_tasks': total_tasks,
            'completed_tasks': completed_tasks_total, 'completion_rate':
            round(completed_tasks_total / max(1, total_tasks) * 100, 1)},
            'priority_analysis': priority_analysis, 'period_days': days,
            'tasks_created': tasks_created, 'tasks_completed':
            tasks_completed, 'avg_completion_time_hours': round(
            avg_completion_time, 2), 'productivity_score': round(
            tasks_completed / max(1, tasks_created) * 100, 1),
            'daily_breakdown': daily_stats}

    def get_advanced_task_analytics_async(self, days: int=30) ->str:
        """Get advanced analytics via background processing."""
        job_id = submit_background_job(self._compute_advanced_analytics,
            days, priority=4, job_id=
            f'advanced_analytics_{days}d_{int(get_utc_now().timestamp())}')
        return job_id

    @cached(ttl=1800.0)
    def get_productivity_report(self, start_date: datetime, end_date: datetime
        ) ->Dict[str, Any]:
        """Get productivity report with caching."""
        return self._compute_productivity_report(start_date, end_date)

    def _compute_productivity_report(self, start_date: datetime, end_date:
        datetime) ->Dict[str, Any]:
        """Compute productivity report (called from cache or background)."""
        logger.debug(
            f'Computing productivity report from {start_date} to {end_date}')
        tasks_in_range = self.session.query(Task).filter(Task.created_at >=
            start_date, Task.created_at <= end_date).all()
        total_tasks = len(tasks_in_range)
        completed_tasks = sum(1 for task in tasks_in_range if task.done)
        total_estimated_hours = sum(task.estimated_hours or 0 for task in
            tasks_in_range)
        total_actual_hours = sum(task.actual_hours or 0 for task in
            tasks_in_range)
        priority_breakdown = {}
        for task in tasks_in_range:
            priority = task.priority or 'Unknown'
            if priority not in priority_breakdown:
                priority_breakdown[priority] = {'total': 0, 'completed': 0}
            priority_breakdown[priority]['total'] += 1
            if task.done:
                priority_breakdown[priority]['completed'] += 1
        completion_rate = completed_tasks / max(1, total_tasks) * 100
        time_efficiency = total_estimated_hours / max(1, total_actual_hours
            ) * 100 if total_actual_hours > 0 else 0
        return {'summary': {'tasks_created': total_tasks, 'tasks_completed':
            completed_tasks, 'completion_rate': round(completion_rate, 1)},
            'period_start': start_date.isoformat(), 'period_end': end_date.
            isoformat(), 'total_tasks': total_tasks, 'completed_tasks':
            completed_tasks, 'completion_rate': round(completion_rate, 1),
            'estimated_hours': round(total_estimated_hours, 1),
            'actual_hours': round(total_actual_hours, 1), 'time_efficiency':
            round(time_efficiency, 1), 'priority_breakdown': priority_breakdown
            }

    def get_productivity_report_async(self, start_date: datetime, end_date:
        datetime) ->str:
        """Get productivity report via background processing."""
        job_id = submit_background_job(self._compute_productivity_report,
            start_date, end_date, priority=4, job_id=
            f"productivity_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
            )
        return job_id

    def get_tasks_by_ids(self, task_ids: List[int]) ->List[Task]:
        """Batch load tasks by IDs with optimized relationships."""
        if not task_ids:
            return []
        return self.session.query(Task).options(joinedload(Task.client),
            selectinload(Task.comments), selectinload(Task.time_entries)
            ).filter(Task.id.in_(task_ids)).all()
