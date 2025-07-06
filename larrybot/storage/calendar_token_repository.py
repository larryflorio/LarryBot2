from sqlalchemy.orm import Session
from larrybot.models.calendar_token import CalendarToken
from typing import Optional, List
from datetime import datetime


class CalendarTokenRepository:
    """
    Repository for CRUD operations on CalendarToken model.
    Enhanced to support multiple accounts per provider with account management features.
    """

    def __init__(self, session: Session):
        self.session = session

    def add_token(self, provider: str, account_id: str, account_name: str,
        access_token: str, refresh_token: Optional[str], expiry: Optional[
        datetime], account_email: Optional[str]=None, is_primary: bool=False
        ) ->CalendarToken:
        """Add a new calendar token with account information."""
        if is_primary or not self.get_all_tokens(provider):
            is_primary = True
        if is_primary:
            self._unset_primary_tokens(provider)
        token = CalendarToken(provider=provider, account_id=account_id,
            account_name=account_name, account_email=account_email,
            access_token=access_token, refresh_token=refresh_token, expiry=
            expiry, is_primary=is_primary)
        self.session.add(token)
        self.session.commit()
        return token

    def get_token_by_provider(self, provider: str) ->Optional[CalendarToken]:
        """Get the primary token for a provider (backward compatibility)."""
        return self.get_primary_token(provider)

    def get_token_by_account(self, provider: str, account_id: str) ->Optional[
        CalendarToken]:
        """Get token by provider and account ID."""
        return self.session.query(CalendarToken).filter_by(provider=
            provider, account_id=account_id, is_active=True).first()

    def get_primary_token(self, provider: str) ->Optional[CalendarToken]:
        """Get the primary token for a provider."""
        return self.session.query(CalendarToken).filter_by(provider=
            provider, is_primary=True, is_active=True).first()

    def get_all_tokens(self, provider: str) ->List[CalendarToken]:
        """Get all active tokens for a provider."""
        return self.session.query(CalendarToken).filter_by(provider=
            provider, is_active=True).order_by(CalendarToken.is_primary.
            desc(), CalendarToken.account_name).all()

    def get_active_tokens(self, provider: str) ->List[CalendarToken]:
        """Get all active tokens for a provider (alias for get_all_tokens)."""
        return self.get_all_tokens(provider)

    def set_primary_account(self, provider: str, account_id: str) ->bool:
        """Set an account as primary, unsetting others. Returns success status."""
        token = self.get_token_by_account(provider, account_id)
        if not token:
            return False
        self._unset_primary_tokens(provider)
        token.is_primary = True
        self.session.commit()
        return True

    def _unset_primary_tokens(self, provider: str) ->None:
        """Unset all primary tokens for a provider."""
        self.session.query(CalendarToken).filter_by(provider=provider,
            is_primary=True).update({'is_primary': False})
        self.session.commit()

    def deactivate_account(self, provider: str, account_id: str) ->Optional[
        CalendarToken]:
        """Deactivate an account without deleting it."""
        token = self.get_token_by_account(provider, account_id)
        if not token:
            return None
        token.is_active = False
        if token.is_primary:
            other_tokens = self.get_all_tokens(provider)
            if other_tokens:
                other_tokens[0].is_primary = True
            token.is_primary = False
        self.session.commit()
        return token

    def reactivate_account(self, provider: str, account_id: str) ->Optional[
        CalendarToken]:
        """Reactivate a deactivated account."""
        token = self.session.query(CalendarToken).filter_by(provider=
            provider, account_id=account_id, is_active=False).first()
        if not token:
            return None
        token.is_active = True
        self.session.commit()
        return token

    def update_token(self, provider: str, account_id: str, access_token:
        str, refresh_token: Optional[str], expiry: Optional[datetime]
        ) ->Optional[CalendarToken]:
        """Update token credentials for an account."""
        token = self.get_token_by_account(provider, account_id)
        if not token:
            return None
        token.access_token = access_token
        token.refresh_token = refresh_token
        token.expiry = expiry
        self.session.commit()
        return token

    def rename_account(self, provider: str, account_id: str, new_name: str
        ) ->Optional[CalendarToken]:
        """Rename an account."""
        token = self.get_token_by_account(provider, account_id)
        if not token:
            return None
        token.account_name = new_name
        self.session.commit()
        return token

    def remove_token_by_provider(self, provider: str) ->Optional[CalendarToken
        ]:
        """Remove the primary token for a provider (backward compatibility)."""
        token = self.get_primary_token(provider)
        if token:
            self.session.delete(token)
            self.session.commit()
        return token

    def remove_account(self, provider: str, account_id: str) ->Optional[
        CalendarToken]:
        """Permanently delete an account."""
        token = self.get_token_by_account(provider, account_id)
        if not token:
            return None
        if token.is_primary:
            other_tokens = self.get_all_tokens(provider)
            if other_tokens:
                other_tokens[0].is_primary = True
        self.session.delete(token)
        self.session.commit()
        return token

    def get_account_count(self, provider: str) ->int:
        """Get the number of active accounts for a provider."""
        return self.session.query(CalendarToken).filter_by(provider=
            provider, is_active=True).count()

    def has_any_accounts(self, provider: str) ->bool:
        """Check if there are any active accounts for a provider."""
        return self.get_account_count(provider) > 0
