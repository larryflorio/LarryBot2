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


@dataclass
class CallbackMetadata:
    """Metadata for a callback handler."""
    pattern: str
    description: str
    plugin: str
    requires_auth: bool = True
    expected_parts: int = 2


class CommandRegistry:
    """
    Enhanced registry for bot commands and their handlers.
    Supports middleware, metadata, and better error handling.
    Now includes callback registration support.
    """

    def __init__(self):
        self._commands: Dict[str, Callable[[Any, Any], Any]] = {}
        self._callbacks: Dict[str, Callable] = {}
        self._callback_metadata: Dict[str, CallbackMetadata] = {}
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

    def register_callback(self, pattern: str, handler: Callable, 
                         metadata: Optional[CallbackMetadata] = None) -> None:
        """Register a callback handler for a specific pattern."""
        self._callbacks[pattern] = handler
        
        if hasattr(handler, '_callback_metadata'):
            decorator_metadata = handler._callback_metadata
            self._callback_metadata[pattern] = CallbackMetadata(
                pattern=pattern,
                description=decorator_metadata.get('description', f'Handler for {pattern}'),
                plugin=decorator_metadata.get('plugin', 'general'),
                requires_auth=decorator_metadata.get('requires_auth', True),
                expected_parts=decorator_metadata.get('expected_parts', 2)
            )
        elif metadata:
            self._callback_metadata[pattern] = metadata
        else:
            self._callback_metadata[pattern] = CallbackMetadata(
                pattern=pattern,
                description=f'Handler for {pattern}',
                plugin='general',
                requires_auth=True,
                expected_parts=2
            )

    def get_callback_handler(self, callback_data: str) -> Optional[Callable]:
        """Get the appropriate callback handler for the given data."""
        for pattern, handler in self._callbacks.items():
            if callback_data.startswith(pattern):
                # Validate callback data format if metadata exists
                metadata = self._callback_metadata.get(pattern)
                if metadata and not self._validate_callback_data(callback_data, metadata.expected_parts):
                    continue
                return handler
        return None

    def _validate_callback_data(self, callback_data: str, expected_parts: int) -> bool:
        """Validate callback data format."""
        parts = callback_data.split(':')
        return len(parts) >= expected_parts

    def get_callback_info(self) -> List[CallbackMetadata]:
        """Get information about all registered callbacks."""
        return list(self._callback_metadata.values())

    def get_callbacks_by_plugin(self, plugin: str) -> List[str]:
        """Get all callbacks in a specific plugin."""
        return [pattern for pattern, meta in self._callback_metadata.items() 
                if meta.plugin == plugin]

    def has_callback(self, pattern: str) -> bool:
        """Check if a callback pattern is registered."""
        return pattern in self._callbacks

    def get_callback_metadata(self, pattern: str) -> Optional[CallbackMetadata]:
        """Get metadata for a specific callback."""
        return self._callback_metadata.get(pattern)

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
