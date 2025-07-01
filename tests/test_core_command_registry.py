import unittest
from unittest.mock import MagicMock
from larrybot.core.command_registry import CommandRegistry
import asyncio

class TestCommandRegistry(unittest.TestCase):
    def test_register_and_dispatch(self):
        registry = CommandRegistry()
        
        # Create mock update and context
        mock_update = MagicMock()
        mock_context = MagicMock()
        
        async def handler(update, context):
            return 'ok', update, context
        
        registry.register('/test', handler)
        result = asyncio.run(registry.dispatch('/test', mock_update, mock_context))
        self.assertEqual(result, ('ok', mock_update, mock_context))

    def test_dispatch_unknown_command(self):
        registry = CommandRegistry()
        with self.assertRaises(ValueError):
            registry.dispatch('/unknown', None, None)

if __name__ == '__main__':
    unittest.main() 