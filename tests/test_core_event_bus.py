import unittest
from larrybot.core.event_bus import EventBus

class TestEventBus(unittest.TestCase):
    def test_subscribe_and_emit(self):
        bus = EventBus()
        results = []
        def listener(data):
            results.append(data)
        bus.subscribe('test_event', listener)
        bus.emit('test_event', 42)
        self.assertEqual(results, [42])

    def test_no_listener(self):
        bus = EventBus()
        # Should not raise
        bus.emit('no_listener_event', 'data')

if __name__ == '__main__':
    unittest.main() 