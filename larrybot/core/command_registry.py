from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass
from larrybot.core.middleware import MiddlewareChain


@dataclass
class CommandMetadata:
    """Metadata for a command."""
    name: str
    description: str
    usage: str
    category: str
    requires_auth: bool = True
    rate_limited: bool = True


class CommandRegistry:
    """
    Enhanced registry for bot commands and their handlers.
    Supports middleware, metadata, and better error handling.
    """

    def __init__(self):
        self._commands: Dict[str, Callable[[Any, Any], Any]] = {}
        self._metadata: Dict[str, CommandMetadata] = {}
        self._middleware_chain = MiddlewareChain()

    def register(self, command: str, handler: Callable[[Any, Any], Any],
        metadata: Optional[CommandMetadata]=None) ->None:
        """Register a handler for a command with optional metadata."""
        self._commands[command] = handler
        if hasattr(handler, '_command_metadata'):
            decorator_metadata = handler._command_metadata
            self._metadata[command] = CommandMetadata(name=command,
                description=decorator_metadata.get('description',
                f'Handler for {command}'), usage=decorator_metadata.get(
                'usage', f'{command} [args]'), category=decorator_metadata.
                get('category', 'general'))
        elif metadata:
            self._metadata[command] = metadata
        else:
            self._metadata[command] = CommandMetadata(name=command,
                description=f'Handler for {command}', usage=
                f'{command} [args]', category='general')

    def register_with_middleware(self, command: str, handler: Callable[[Any,
        Any], Any], middleware: List[Any]=None, metadata: Optional[
        CommandMetadata]=None) ->None:
        """Register a command with specific middleware."""
        self.register(command, handler, metadata)
        if middleware:
            for mw in middleware:
                self._middleware_chain.add_middleware(mw)

    def dispatch(self, command: str, update, context) ->Any:
        """Dispatch a command to its handler with middleware support."""
        handler = self._commands.get(command)
        if not handler:
            raise ValueError(f'No handler registered for command: {command}')
        return self._middleware_chain.execute(update, context, handler)

    def get_command_info(self) ->List[CommandMetadata]:
        """Get information about all registered commands."""
        return list(self._metadata.values())

    def get_commands_by_category(self, category: str) ->List[str]:
        """Get all commands in a specific category."""
        return [cmd for cmd, meta in self._metadata.items() if meta.
            category == category]

    def add_middleware(self, middleware: Any) ->None:
        """Add middleware to the chain."""
        self._middleware_chain.add_middleware(middleware)

    def has_command(self, command: str) ->bool:
        """Check if a command is registered."""
        return command in self._commands

    def get_command_metadata(self, command: str) ->Optional[CommandMetadata]:
        """Get metadata for a specific command."""
        return self._metadata.get(command)
