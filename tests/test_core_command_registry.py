import unittest
from unittest.mock import MagicMock
from larrybot.core.command_registry import CommandRegistry, CallbackMetadata
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

    def test_register_callback(self):
        """Test callback registration and retrieval."""
        registry = CommandRegistry()
        
        async def callback_handler(query, context):
            return 'callback_ok'
        
        # Register callback with metadata
        metadata = CallbackMetadata(
            pattern='test_callback',
            description='Test callback handler',
            plugin='test_plugin',
            requires_auth=True,
            expected_parts=2
        )
        registry.register_callback('test_callback', callback_handler, metadata)
        
        # Test callback retrieval
        handler = registry.get_callback_handler('test_callback:value')
        self.assertIsNotNone(handler)
        
        # Test callback info
        callback_info = registry.get_callback_info()
        self.assertEqual(len(callback_info), 1)
        self.assertEqual(callback_info[0].pattern, 'test_callback')
        self.assertEqual(callback_info[0].plugin, 'test_plugin')

    def test_callback_validation(self):
        """Test callback data validation."""
        registry = CommandRegistry()
        
        async def callback_handler(query, context):
            return 'callback_ok'
        
        # Register callback requiring 3 parts
        metadata = CallbackMetadata(
            pattern='test_callback',
            description='Test callback handler',
            plugin='test_plugin',
            expected_parts=3
        )
        registry.register_callback('test_callback', callback_handler, metadata)
        
        # Test valid callback data
        handler = registry.get_callback_handler('test_callback:part1:part2')
        self.assertIsNotNone(handler)
        
        # Test invalid callback data (not enough parts)
        handler = registry.get_callback_handler('test_callback:part1')
        self.assertIsNone(handler)

    def test_callback_pattern_matching(self):
        """Test callback pattern matching."""
        registry = CommandRegistry()
        
        async def callback_handler(query, context):
            return 'callback_ok'
        
        registry.register_callback('test_callback', callback_handler)
        
        # Test prefix match (with value)
        handler = registry.get_callback_handler('test_callback:value')
        self.assertIsNotNone(handler)
        
        # Test prefix match (with multiple parts)
        handler = registry.get_callback_handler('test_callback:part1:part2')
        self.assertIsNotNone(handler)
        
        # Test no match
        handler = registry.get_callback_handler('other_callback')
        self.assertIsNone(handler)
        
        # Test exact match with custom metadata (no validation)
        async def exact_callback_handler(query, context):
            return 'exact_callback_ok'
        
        metadata = CallbackMetadata(
            pattern='exact_callback',
            description='Exact callback handler',
            plugin='test_plugin',
            expected_parts=1  # Allow exact match
        )
        registry.register_callback('exact_callback', exact_callback_handler, metadata)
        
        handler = registry.get_callback_handler('exact_callback')
        self.assertIsNotNone(handler)

    def test_callback_decorator_metadata(self):
        """Test callback registration with decorator metadata."""
        registry = CommandRegistry()
        
        async def callback_handler(query, context):
            return 'callback_ok'
        
        # Simulate decorator metadata
        callback_handler._callback_metadata = {
            'pattern': 'decorated_callback',
            'description': 'Decorated callback',
            'plugin': 'decorated_plugin',
            'requires_auth': False,
            'expected_parts': 2
        }
        
        registry.register_callback('decorated_callback', callback_handler)
        
        # Test metadata extraction
        metadata = registry.get_callback_metadata('decorated_callback')
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.description, 'Decorated callback')
        self.assertEqual(metadata.plugin, 'decorated_plugin')
        self.assertFalse(metadata.requires_auth)

    def test_get_callbacks_by_plugin(self):
        """Test getting callbacks by plugin."""
        registry = CommandRegistry()
        
        async def handler1(query, context):
            return 'handler1'
        
        async def handler2(query, context):
            return 'handler2'
        
        registry.register_callback('plugin1_callback', handler1)
        registry.register_callback('plugin2_callback', handler2)
        
        # Set metadata for plugin1
        registry._callback_metadata['plugin1_callback'] = CallbackMetadata(
            pattern='plugin1_callback',
            description='Plugin 1 callback',
            plugin='plugin1'
        )
        
        # Set metadata for plugin2
        registry._callback_metadata['plugin2_callback'] = CallbackMetadata(
            pattern='plugin2_callback',
            description='Plugin 2 callback',
            plugin='plugin2'
        )
        
        plugin1_callbacks = registry.get_callbacks_by_plugin('plugin1')
        self.assertEqual(len(plugin1_callbacks), 1)
        self.assertIn('plugin1_callback', plugin1_callbacks)

    def test_has_callback(self):
        """Test callback existence check."""
        registry = CommandRegistry()
        
        async def callback_handler(query, context):
            return 'callback_ok'
        
        registry.register_callback('test_callback', callback_handler)
        
        self.assertTrue(registry.has_callback('test_callback'))
        self.assertFalse(registry.has_callback('nonexistent_callback'))

if __name__ == '__main__':
    unittest.main() 