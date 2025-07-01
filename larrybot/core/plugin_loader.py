import importlib
import pkgutil
import os
import logging
from typing import List, Any

logger = logging.getLogger(__name__)

class PluginLoader:
    """
    Discovers and loads plugins from the plugins/ directory.
    Plugins should define a 'register' function for integration.
    """
    def __init__(self, plugins_package: str = 'larrybot.plugins'):
        self.plugins_package = plugins_package
        self.plugins: List[Any] = []

    def discover_and_load(self) -> None:
        """Discover and import all plugins in the plugins package."""
        try:
            package = importlib.import_module(self.plugins_package)
            package_path = package.__path__
            for _, name, is_pkg in pkgutil.iter_modules(package_path):
                if not is_pkg:
                    module_name = f"{self.plugins_package}.{name}"
                    try:
                        module = importlib.import_module(module_name)
                        self.plugins.append(module)
                    except (ImportError, SyntaxError, Exception) as e:
                        logger.warning(f"Failed to load plugin {module_name}: {e}")
                        # Continue loading other plugins
                        continue
        except ModuleNotFoundError:
            # Re-raise if the main package doesn't exist
            raise

    def register_plugins(self, *args, **kwargs) -> None:
        """Call the 'register' function of each loaded plugin, if it exists."""
        for plugin in self.plugins:
            if hasattr(plugin, 'register'):
                try:
                    plugin.register(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Failed to register plugin {plugin.__name__}: {e}")
                    # Continue with other plugins
                    continue 