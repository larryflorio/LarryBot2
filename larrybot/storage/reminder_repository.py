from sqlalchemy.orm import Session
from larrybot.models.reminder import Reminder
from typing import List, Optional
from datetime import datetime
from sqlalchemy import text


class ReminderRepository:
    """
    Repository for CRUD operations on Reminder model.
    Optimized for performance and minimal database blocking.
    """

    def __init__(self, session: Session):
        self.session = session

    def add_reminder(self, task_id: int, remind_at: datetime) ->Reminder:
        reminder = Reminder(task_id=task_id, remind_at=remind_at)
        self.session.add(reminder)
        self.session.commit()
        return reminder

    def list_reminders(self) ->List[Reminder]:
        """List all reminders with optimized query."""
        return self.session.query(Reminder).order_by(Reminder.remind_at).all()

    def get_reminder_by_id(self, reminder_id: int) ->Optional[Reminder]:
        return self.session.query(Reminder).filter_by(id=reminder_id).first()

    def delete_reminder(self, reminder_id: int) ->Optional[Reminder]:
        """Delete reminder with minimal blocking."""
        reminder = self.get_reminder_by_id(reminder_id)
        if reminder:
            self.session.delete(reminder)
            return reminder
        return None

    def list_due_reminders(self, now: datetime) ->List[Reminder]:
        """
        List due reminders with optimized query and minimal locking.
        Orders by remind_at to process oldest reminders first.
        """
        return self.session.query(Reminder).filter(Reminder.remind_at <= now
            ).order_by(Reminder.remind_at).all()

    def delete_multiple_reminders(self, reminder_ids: List[int]) ->int:
        """
        Delete multiple reminders in a single efficient operation.
        Returns the number of reminders deleted.
        """
        if not reminder_ids:
            return 0
        deleted_count = self.session.query(Reminder).filter(Reminder.id.in_
            (reminder_ids)).delete(synchronize_session=False)
        return deleted_count

    def get_next_reminder(self, now: datetime) ->Optional[Reminder]:
        """Get the next upcoming reminder after the given time."""
        return self.session.query(Reminder).filter(Reminder.remind_at > now
            ).order_by(Reminder.remind_at).first()

    def count_due_reminders(self, now: datetime) ->int:
        """Count due reminders without fetching full objects."""
        return self.session.query(Reminder).filter(Reminder.remind_at <= now
            ).count()
