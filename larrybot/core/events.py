from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ReminderDueEvent:
    """Event emitted when a reminder is due to be sent."""
    reminder_id: int
    task_id: int
    task_description: str
    remind_at: datetime
    user_id: Optional[int] = None 