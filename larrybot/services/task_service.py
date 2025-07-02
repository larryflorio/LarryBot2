from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from larrybot.services.base_service import BaseService
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task import Task
from larrybot.models.task_comment import TaskComment
import json
import re

class TaskService(BaseService):
    """
    Service layer for advanced task management business logic.
    """
    
    def __init__(self, task_repository: TaskRepository):
        super().__init__()
        self.task_repository = task_repository

    async def execute(self, *args, **kwargs) -> Any:
        """Execute the service operation."""
        # Default implementation - can be overridden by specific operations
        return await self.create_task_with_metadata(*args, **kwargs)

    async def create_task_with_metadata(
        self, 
        description: str, 
        priority: str = "Medium",
        due_date: Optional[datetime] = None,
        category: Optional[str] = None,
        estimated_hours: Optional[float] = None,
        tags: Optional[List[str]] = None,
        parent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create task with advanced metadata."""
        try:
            # Validate priority
            if priority not in ['Low', 'Medium', 'High', 'Critical']:
                return self._handle_error(ValueError(f"Invalid priority: {priority}"))
            
            # Validate due date
            if due_date and due_date < datetime.utcnow():
                return self._handle_error(ValueError("Due date cannot be in the past"))
            
            # Validate parent task exists
            if parent_id:
                parent = self.task_repository.get_task_by_id(parent_id)
                if not parent:
                    return self._handle_error(ValueError(f"Parent task {parent_id} not found"))
            
            task = self.task_repository.add_task_with_metadata(
                description=description,
                priority=priority,
                due_date=due_date,
                category=category,
                estimated_hours=estimated_hours,
                tags=tags,
                parent_id=parent_id
            )
            
            return self._create_success_response(
                self._task_to_dict(task),
                f"Task created successfully with ID {task.id}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error creating task")

    async def get_tasks_with_filters(
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
    ) -> Dict[str, Any]:
        """Get tasks with advanced filtering."""
        try:
            tasks = self.task_repository.get_tasks_with_filters(
                status=status,
                priority=priority,
                category=category,
                due_before=due_before,
                due_after=due_after,
                overdue_only=overdue_only,
                client_id=client_id,
                parent_id=parent_id,
                done=done
            )
            
            return self._create_success_response(
                [self._task_to_dict(task) for task in tasks],
                f"Found {len(tasks)} tasks"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error retrieving tasks")

    async def update_task_priority(self, task_id: int, priority: str) -> Dict[str, Any]:
        """Update task priority."""
        try:
            if priority not in ['Low', 'Medium', 'High', 'Critical']:
                return self._handle_error(ValueError(f"Invalid priority: {priority}"))
            
            task = self.task_repository.update_priority(task_id, priority)
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            return self._create_success_response(
                self._task_to_dict(task),
                f"Task {task_id} priority updated to {priority}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error updating task priority")

    async def update_task_due_date(self, task_id: int, due_date: datetime) -> Dict[str, Any]:
        """Update task due date."""
        try:
            if due_date < datetime.utcnow():
                return self._handle_error(ValueError("Due date cannot be in the past"))
            
            task = self.task_repository.update_due_date(task_id, due_date)
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            return self._create_success_response(
                self._task_to_dict(task),
                f"Task {task_id} due date updated to {due_date.strftime('%Y-%m-%d %H:%M')}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error updating task due date")

    async def update_task_category(self, task_id: int, category: str) -> Dict[str, Any]:
        """Update task category."""
        try:
            task = self.task_repository.update_category(task_id, category)
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            return self._create_success_response(
                self._task_to_dict(task),
                f"Task {task_id} category updated to {category}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error updating task category")

    async def update_task_status(self, task_id: int, status: str) -> Dict[str, Any]:
        """Update task status."""
        try:
            valid_statuses = ['Todo', 'In Progress', 'Review', 'Done']
            if status not in valid_statuses:
                return self._handle_error(ValueError(f"Invalid status: {status}"))
            
            task = self.task_repository.update_status(task_id, status)
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            return self._create_success_response(
                self._task_to_dict(task),
                f"Task {task_id} status updated to {status}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error updating task status")

    async def start_time_tracking(self, task_id: int) -> Dict[str, Any]:
        """Start time tracking for a task."""
        try:
            task = self.task_repository.get_task_by_id(task_id)
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            if task.started_at:
                return self._handle_error(ValueError(f"Time tracking already started for task {task_id}"))
            
            success = self.task_repository.start_time_tracking(task_id)
            if not success:
                return self._handle_error(ValueError(f"Failed to start time tracking for task {task_id}"))
            
            return self._create_success_response(
                {"task_id": task_id, "started_at": datetime.utcnow()},
                f"Time tracking started for task {task_id}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error starting time tracking")

    async def stop_time_tracking(self, task_id: int) -> Dict[str, Any]:
        """Stop time tracking for a task."""
        try:
            task = self.task_repository.get_task_by_id(task_id)
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            if not task.started_at:
                return self._handle_error(ValueError(f"Time tracking not started for task {task_id}"))
            
            duration = self.task_repository.stop_time_tracking(task_id)
            if duration is None:
                return self._handle_error(ValueError(f"Failed to stop time tracking for task {task_id}"))
            
            return self._create_success_response(
                {"task_id": task_id, "duration_hours": duration},
                f"Time tracking stopped for task {task_id}. Duration: {duration:.2f} hours"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error stopping time tracking")

    async def add_subtask(self, parent_id: int, description: str) -> Dict[str, Any]:
        """Add a subtask to a parent task."""
        try:
            parent = self.task_repository.get_task_by_id(parent_id)
            if not parent:
                return self._handle_error(ValueError(f"Parent task {parent_id} not found"))
            
            subtask = self.task_repository.add_subtask(parent_id, description)
            if not subtask:
                return self._handle_error(ValueError(f"Failed to create subtask"))
            
            return self._create_success_response(
                self._task_to_dict(subtask),
                f"Subtask created with ID {subtask.id} for parent task {parent_id}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error creating subtask")

    async def get_subtasks(self, parent_id: int) -> Dict[str, Any]:
        """Get all subtasks of a parent task."""
        try:
            parent = self.task_repository.get_task_by_id(parent_id)
            if not parent:
                return self._handle_error(ValueError(f"Parent task {parent_id} not found"))
            
            subtasks = self.task_repository.get_subtasks(parent_id)
            
            return self._create_success_response(
                [self._task_to_dict(task) for task in subtasks],
                f"Found {len(subtasks)} subtasks for task {parent_id}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error retrieving subtasks")

    async def add_task_dependency(self, task_id: int, dependency_id: int) -> Dict[str, Any]:
        """Add a dependency between tasks."""
        try:
            # Check if tasks exist
            task = self.task_repository.get_task_by_id(task_id)
            dependency = self.task_repository.get_task_by_id(dependency_id)
            
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            if not dependency:
                return self._handle_error(ValueError(f"Dependency task {dependency_id} not found"))
            
            if task_id == dependency_id:
                return self._handle_error(ValueError("Task cannot depend on itself"))
            
            success = self.task_repository.add_task_dependency(task_id, dependency_id)
            if not success:
                return self._handle_error(ValueError(f"Dependency already exists or failed to create"))
            
            return self._create_success_response(
                {"task_id": task_id, "dependency_id": dependency_id},
                f"Task {task_id} now depends on task {dependency_id}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error adding task dependency")

    async def get_task_dependencies(self, task_id: int) -> Dict[str, Any]:
        """Get all tasks that this task depends on."""
        try:
            task = self.task_repository.get_task_by_id(task_id)
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            dependencies = self.task_repository.get_task_dependencies(task_id)
            
            return self._create_success_response(
                [self._task_to_dict(dep) for dep in dependencies],
                f"Found {len(dependencies)} dependencies for task {task_id}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error retrieving task dependencies")

    async def add_tags(self, task_id: int, tags: List[str]) -> Dict[str, Any]:
        """Add tags to a task."""
        try:
            task = self.task_repository.get_task_by_id(task_id)
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            if not tags:
                return self._handle_error(ValueError("No tags provided"))
            
            updated_task = self.task_repository.add_tags(task_id, tags)
            if not updated_task:
                return self._handle_error(ValueError(f"Failed to add tags to task {task_id}"))
            
            return self._create_success_response(
                self._task_to_dict(updated_task),
                f"Tags {tags} added to task {task_id}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error adding tags")

    async def get_tasks_by_tag(self, tag: str) -> Dict[str, Any]:
        """Get all tasks with a specific tag."""
        try:
            tasks = self.task_repository.get_tasks_by_tag(tag)
            
            return self._create_success_response(
                [self._task_to_dict(task) for task in tasks],
                f"Found {len(tasks)} tasks with tag '{tag}'"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error retrieving tasks by tag")

    async def add_comment(self, task_id: int, comment: str) -> Dict[str, Any]:
        """Add a comment to a task."""
        try:
            task = self.task_repository.get_task_by_id(task_id)
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            if not comment.strip():
                return self._handle_error(ValueError("Comment cannot be empty"))
            
            task_comment = self.task_repository.add_comment(task_id, comment)
            if not task_comment:
                return self._handle_error(ValueError(f"Failed to add comment to task {task_id}"))
            
            return self._create_success_response(
                self._comment_to_dict(task_comment),
                f"Comment added to task {task_id}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error adding comment")

    async def get_comments(self, task_id: int) -> Dict[str, Any]:
        """Get all comments for a task."""
        try:
            task = self.task_repository.get_task_by_id(task_id)
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            comments = self.task_repository.get_comments(task_id)
            
            return self._create_success_response(
                [self._comment_to_dict(comment) for comment in comments],
                f"Found {len(comments)} comments for task {task_id}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error retrieving comments")

    async def get_task_analytics(self) -> Dict[str, Any]:
        """Get comprehensive task analytics."""
        try:
            stats = self.task_repository.get_task_statistics()
            
            # Add additional analytics
            overdue_tasks = self.task_repository.get_overdue_tasks()
            tasks_due_today = self.task_repository.get_tasks_due_today()
            
            analytics = {
                **stats,
                'overdue_tasks_details': [self._task_to_dict(task) for task in overdue_tasks],
                'tasks_due_today': [self._task_to_dict(task) for task in tasks_due_today],
                'categories': self.task_repository.get_all_categories()
            }
            
            return self._create_success_response(
                analytics,
                "Task analytics retrieved successfully"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error retrieving task analytics")

    async def suggest_priority(self, description: str) -> Dict[str, Any]:
        """Suggest priority for a task based on description."""
        try:
            # Simple priority suggestion logic based on keywords
            description_lower = description.lower()
            
            # High priority keywords
            high_priority_keywords = ['urgent', 'critical', 'deadline', 'emergency', 'asap', 'important']
            if any(keyword in description_lower for keyword in high_priority_keywords):
                suggested_priority = 'High'
            elif any(word in description_lower for word in ['meeting', 'call', 'review', 'presentation']):
                suggested_priority = 'Medium'
            else:
                suggested_priority = 'Low'
            
            return self._create_success_response(
                {
                    'suggested_priority': suggested_priority,
                    'reasoning': f"Based on keywords in description: {description}"
                },
                f"Suggested priority: {suggested_priority}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error suggesting priority")

    async def bulk_update_status(self, task_ids: List[int], status: str) -> Dict[str, Any]:
        """Update status for multiple tasks."""
        try:
            if not task_ids:
                return self._handle_error(ValueError("No task IDs provided"))
            
            valid_statuses = ['Todo', 'In Progress', 'Review', 'Done']
            if status not in valid_statuses:
                return self._handle_error(ValueError(f"Invalid status: {status}"))
            
            # Validate all task IDs exist
            for task_id in task_ids:
                task = self.task_repository.get_task_by_id(task_id)
                if not task:
                    return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            updated_count = self.task_repository.bulk_update_status(task_ids, status)
            
            return self._create_success_response(
                {
                    'updated_count': updated_count,
                    'task_ids': task_ids,
                    'new_status': status
                },
                f"Updated status to '{status}' for {updated_count} tasks"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error updating task statuses")

    async def bulk_update_priority(self, task_ids: List[int], priority: str) -> Dict[str, Any]:
        """Update priority for multiple tasks."""
        try:
            if not task_ids:
                return self._handle_error(ValueError("No task IDs provided"))
            
            if priority not in ['Low', 'Medium', 'High', 'Critical']:
                return self._handle_error(ValueError(f"Invalid priority: {priority}"))
            
            # Validate all task IDs exist
            for task_id in task_ids:
                task = self.task_repository.get_task_by_id(task_id)
                if not task:
                    return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            updated_count = self.task_repository.bulk_update_priority(task_ids, priority)
            
            return self._create_success_response(
                {
                    'updated_count': updated_count,
                    'task_ids': task_ids,
                    'new_priority': priority
                },
                f"Updated priority to '{priority}' for {updated_count} tasks"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error updating task priorities")

    async def bulk_assign_to_client(self, task_ids: List[int], client_name: str) -> Dict[str, Any]:
        """Assign multiple tasks to a client."""
        try:
            # Validate all task IDs exist
            for task_id in task_ids:
                task = self.task_repository.get_task_by_id(task_id)
                if not task:
                    return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            updated_count = self.task_repository.bulk_assign_to_client(task_ids, client_name)
            
            if updated_count == 0:
                return self._handle_error(ValueError(f"Client '{client_name}' not found"))
            
            return self._create_success_response(
                {
                    'updated_count': updated_count,
                    'task_ids': task_ids,
                    'client_name': client_name
                },
                f"Assigned {updated_count} tasks to client '{client_name}'"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error assigning tasks to client")

    async def bulk_delete_tasks(self, task_ids: List[int]) -> Dict[str, Any]:
        """Delete multiple tasks."""
        try:
            # Validate all task IDs exist
            for task_id in task_ids:
                task = self.task_repository.get_task_by_id(task_id)
                if not task:
                    return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            deleted_count = self.task_repository.bulk_delete_tasks(task_ids)
            
            return self._create_success_response(
                {
                    'deleted_count': deleted_count,
                    'task_ids': task_ids
                },
                f"Deleted {deleted_count} tasks"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error deleting tasks")

    async def add_manual_time_entry(self, task_id: int, duration_minutes: int, description: str = "") -> Dict[str, Any]:
        """Add manual time entry for a task."""
        try:
            task = self.task_repository.get_task_by_id(task_id)
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            if duration_minutes <= 0:
                return self._handle_error(ValueError("Duration must be positive"))
            
            # Create a time entry with start time 1 hour ago and end time now
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=duration_minutes)
            
            success = self.task_repository.add_time_entry(task_id, start_time, end_time, description)
            if not success:
                return self._handle_error(ValueError(f"Failed to add time entry for task {task_id}"))
            
            return self._create_success_response(
                {
                    'task_id': task_id,
                    'duration_minutes': duration_minutes,
                    'description': description,
                    'start_time': start_time,
                    'end_time': end_time
                },
                f"Added {duration_minutes} minutes to task {task_id}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error adding time entry")

    async def get_task_time_summary(self, task_id: int) -> Dict[str, Any]:
        """Get comprehensive time summary for a task."""
        try:
            task = self.task_repository.get_task_by_id(task_id)
            if not task:
                return self._handle_error(ValueError(f"Task {task_id} not found"))
            
            time_summary = self.task_repository.get_task_time_summary(task_id)
            comments = self.task_repository.get_comments(task_id)
            
            return self._create_success_response(
                {
                    'task_id': task_id,
                    'task_description': task.description,
                    'estimated_hours': time_summary.get('estimated_hours', 0),
                    'actual_hours': time_summary.get('actual_hours', 0),
                    'time_entries_hours': time_summary.get('time_entries_hours', 0),
                    'time_entries_count': time_summary.get('time_entries_count', 0),
                    'comments_count': len(comments),
                    'efficiency': (time_summary.get('estimated_hours', 0) / time_summary.get('actual_hours', 1)) * 100 if time_summary.get('actual_hours', 0) > 0 else 0
                },
                f"Time summary for task {task_id}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error getting time summary")

    async def search_tasks_by_text(self, search_text: str, case_sensitive: bool = False) -> Dict[str, Any]:
        """Search tasks by text in description, comments, and tags."""
        try:
            if not search_text.strip():
                return self._handle_error(ValueError("Search text cannot be empty"))
            
            tasks = self.task_repository.search_tasks_by_text(search_text, case_sensitive)
            
            return self._create_success_response(
                [self._task_to_dict(task) for task in tasks],
                f"Found {len(tasks)} tasks matching '{search_text}'"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error searching tasks")

    async def get_tasks_with_advanced_filters(
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
    ) -> Dict[str, Any]:
        """Get tasks with advanced filtering and sorting options."""
        try:
            # Validate sort parameters
            valid_sort_fields = ['created_at', 'due_date', 'priority', 'status', 'category']
            if sort_by not in valid_sort_fields:
                return self._handle_error(ValueError(f"Invalid sort field: {sort_by}"))
            
            if sort_order not in ['asc', 'desc']:
                return self._handle_error(ValueError(f"Invalid sort order: {sort_order}"))
            
            tasks = self.task_repository.get_tasks_with_advanced_filters(
                status=status,
                priority=priority,
                category=category,
                due_before=due_before,
                due_after=due_after,
                overdue_only=overdue_only,
                client_id=client_id,
                parent_id=parent_id,
                done=done,
                tags=tags,
                has_comments=has_comments,
                has_time_entries=has_time_entries,
                estimated_hours_min=estimated_hours_min,
                estimated_hours_max=estimated_hours_max,
                created_after=created_after,
                created_before=created_before,
                sort_by=sort_by,
                sort_order=sort_order,
                limit=limit
            )
            
            return self._create_success_response(
                [self._task_to_dict(task) for task in tasks],
                f"Found {len(tasks)} tasks with advanced filters"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error retrieving tasks with advanced filters")

    async def get_tasks_by_multiple_tags(self, tags: List[str], match_all: bool = False) -> Dict[str, Any]:
        """Get tasks by multiple tags with option to match all or any."""
        try:
            if not tags:
                return self._handle_error(ValueError("No tags provided"))
            
            tasks = self.task_repository.get_tasks_by_multiple_tags(tags, match_all)
            
            match_type = "all" if match_all else "any"
            return self._create_success_response(
                [self._task_to_dict(task) for task in tasks],
                f"Found {len(tasks)} tasks matching {match_type} of tags: {', '.join(tags)}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error retrieving tasks by tags")

    async def get_tasks_by_time_range(self, start_date: datetime, end_date: datetime, include_completed: bool = True) -> Dict[str, Any]:
        """Get tasks created or due within a specific time range."""
        try:
            if start_date >= end_date:
                return self._handle_error(ValueError("Start date must be before end date"))
            
            tasks = self.task_repository.get_tasks_by_time_range(start_date, end_date, include_completed)
            
            completed_text = "including completed" if include_completed else "excluding completed"
            return self._create_success_response(
                [self._task_to_dict(task) for task in tasks],
                f"Found {len(tasks)} tasks in time range ({completed_text})"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error retrieving tasks by time range")

    async def get_tasks_by_priority_range(self, min_priority: str, max_priority: str) -> Dict[str, Any]:
        """Get tasks within a priority range."""
        try:
            valid_priorities = ['Low', 'Medium', 'High', 'Critical']
            if min_priority not in valid_priorities or max_priority not in valid_priorities:
                return self._handle_error(ValueError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"))
            
            tasks = self.task_repository.get_tasks_by_priority_range(min_priority, max_priority)
            
            return self._create_success_response(
                [self._task_to_dict(task) for task in tasks],
                f"Found {len(tasks)} tasks in priority range {min_priority} to {max_priority}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error retrieving tasks by priority range")

    async def get_advanced_task_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get advanced task analytics for the specified number of days."""
        try:
            if days <= 0 or days > 365:
                return self._handle_error(ValueError("Days must be between 1 and 365"))
            
            analytics = self.task_repository.get_advanced_task_analytics(days)
            
            return self._create_success_response(
                analytics,
                f"Advanced analytics for the last {days} days"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error retrieving advanced analytics")

    async def get_productivity_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get detailed productivity report for a specific time period."""
        try:
            if start_date >= end_date:
                return self._handle_error(ValueError("Start date must be before end date"))
            
            if (end_date - start_date).days > 365:
                return self._handle_error(ValueError("Date range cannot exceed 365 days"))
            
            report = self.task_repository.get_productivity_report(start_date, end_date)
            
            return self._create_success_response(
                report,
                f"Productivity report from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            )
            
        except Exception as e:
            return self._handle_error(e, "Error generating productivity report")

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert task model to dictionary."""
        return {
            'id': task.id,
            'description': task.description,
            'done': task.done,
            'priority': task.priority_enum.name.title(),  # Use human-readable format
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'category': task.category,
            'status': task.status,
            'estimated_hours': float(task.estimated_hours) if task.estimated_hours else None,
            'actual_hours': float(task.actual_hours) if task.actual_hours else None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'parent_id': task.parent_id,
            'tags': json.loads(task.tags) if task.tags else [],
            'client_id': task.client_id,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat()
        }

    def _comment_to_dict(self, comment: TaskComment) -> Dict[str, Any]:
        """Convert comment model to dictionary."""
        return {
            'id': comment.id,
            'task_id': comment.task_id,
            'comment': comment.comment,
            'created_at': comment.created_at.isoformat()
        }

    def _handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """Handle errors consistently across services."""
        return {
            "success": False,
            "message": f"{context}: {str(error)}" if context else str(error)
        } 