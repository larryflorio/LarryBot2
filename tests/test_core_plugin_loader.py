import unittest
from larrybot.core.plugin_loader import PluginLoader

class TestPluginLoader(unittest.TestCase):
    def test_discover_and_load(self):
        loader = PluginLoader()
        # Should not raise, even if no plugins are present
        loader.discover_and_load()
        self.assertIsInstance(loader.plugins, list)

if __name__ == '__main__':
    unittest.main() 