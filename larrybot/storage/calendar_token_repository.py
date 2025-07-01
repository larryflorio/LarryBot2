from sqlalchemy.orm import Session
from larrybot.models.calendar_token import CalendarToken
from typing import Optional
from datetime import datetime

class CalendarTokenRepository:
    """
    Repository for CRUD operations on CalendarToken model.
    """
    def __init__(self, session: Session):
        self.session = session

    def add_token(self, provider: str, access_token: str, refresh_token: Optional[str], expiry: Optional[datetime]) -> CalendarToken:
        token = CalendarToken(provider=provider, access_token=access_token, refresh_token=refresh_token, expiry=expiry)
        self.session.add(token)
        self.session.commit()
        return token

    def get_token_by_provider(self, provider: str) -> Optional[CalendarToken]:
        return self.session.query(CalendarToken).filter_by(provider=provider).first()

    def remove_token_by_provider(self, provider: str) -> Optional[CalendarToken]:
        token = self.get_token_by_provider(provider)
        if token:
            self.session.delete(token)
            self.session.commit()
            return token
        return None 