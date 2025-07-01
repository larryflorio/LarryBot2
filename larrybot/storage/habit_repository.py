from sqlalchemy.orm import Session
from larrybot.models.habit import Habit
from typing import List, Optional
import datetime

class HabitRepository:
    """
    Repository for CRUD and streak logic on Habit model.
    """
    def __init__(self, session: Session):
        self.session = session

    def add_habit(self, name: str) -> Habit:
        habit = Habit(name=name, streak=0, last_completed=None)
        self.session.add(habit)
        self.session.commit()
        return habit

    def get_habit_by_name(self, name: str) -> Optional[Habit]:
        return self.session.query(Habit).filter_by(name=name).first()

    def list_habits(self) -> List[Habit]:
        return self.session.query(Habit).all()

    def mark_habit_done(self, name: str) -> Optional[Habit]:
        habit = self.get_habit_by_name(name)
        today = datetime.date.today()
        if habit:
            if habit.last_completed == today:
                return habit  # Already marked today
            if habit.last_completed == today - datetime.timedelta(days=1):
                habit.streak += 1
            else:
                habit.streak = 1
            habit.last_completed = today
            self.session.commit()
            return habit
        return None

    def delete_habit(self, name: str) -> Optional[Habit]:
        habit = self.get_habit_by_name(name)
        if habit:
            self.session.delete(habit)
            self.session.commit()
            return habit
        return None 