from typing import Callable, Dict, List, Any

class EventBus:
    """
    Simple event bus for registering and emitting events.
    Listeners can subscribe to named events and will be called with event data.
    """
    def __init__(self):
        self._listeners: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(self, event_name: str, listener: Callable[[Any], None]) -> None:
        """Register a listener for a specific event name."""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(listener)

    def emit(self, event_name: str, data: Any = None) -> None:
        """Emit an event, calling all registered listeners with the provided data."""
        for listener in self._listeners.get(event_name, []):
            listener(data) 