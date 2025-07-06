from abc import ABC, abstractmethod
from typing import Any, Protocol, Callable, TYPE_CHECKING
from telegram import Update
from telegram.ext import ContextTypes
if TYPE_CHECKING:
    from larrybot.core.event_bus import EventBus
    from larrybot.core.command_registry import CommandRegistry


class PluginInterface(Protocol):
    """Protocol defining the interface that all plugins must implement."""

    def register(self, event_bus: 'EventBus', command_registry:
        'CommandRegistry') ->None:
        """Register the plugin with the core system."""
        ...


class EventListener(Protocol):
    """Protocol for event listeners."""

    def __call__(self, data: Any) ->None:
        """Handle an event with the given data."""
        ...


class CommandHandler(Protocol):
    """Protocol for command handlers."""

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE
        ) ->None:
        """Handle a command with the given update and context."""
        ...


class RepositoryInterface(ABC):
    """Abstract base class for repository implementations."""

    @abstractmethod
    def __init__(self, session):
        """Initialize repository with database session."""
        pass


class ServiceInterface(ABC):
    """Abstract base class for service layer implementations."""

    @abstractmethod
    async def execute(self, *args, **kwargs) ->Any:
        """Execute the service operation."""
        pass


class ConfigProvider(Protocol):
    """Protocol for configuration providers."""

    def get(self, key: str, default: Any=None) ->Any:
        """Get configuration value."""
        ...

    def validate(self) ->None:
        """Validate configuration."""
        ...
