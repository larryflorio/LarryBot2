from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass
from larrybot.core.plugin_loader import PluginLoader
from larrybot.core.interfaces import PluginInterface
from larrybot.core.dependency_injection import DependencyContainer


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str]
    enabled: bool = True


class PluginManager:
    """
    Enhanced plugin manager with lifecycle management, dependency injection,
    and metadata support.
    """

    def __init__(self, container: DependencyContainer):
        self.container = container
        self.plugins: Dict[str, Any] = {}
        self.metadata: Dict[str, PluginMetadata] = {}
        self.loader = PluginLoader()

    def register_plugin_metadata(self, plugin_name: str, metadata:
        PluginMetadata) ->None:
        """Register metadata for a plugin."""
        self.metadata[plugin_name] = metadata

    def discover_and_load(self) ->None:
        """Discover and load all plugins."""
        self.loader.discover_and_load()
        for plugin in self.loader.plugins:
            plugin_name = plugin.__name__
            self.plugins[plugin_name] = plugin
            if plugin_name not in self.metadata:
                self.metadata[plugin_name] = PluginMetadata(name=
                    plugin_name, version='1.0.0', description=
                    f'Plugin {plugin_name}', author='Unknown', dependencies=[])

    def register_plugins(self, *args, **kwargs) ->None:
        """Register all enabled plugins."""
        for plugin_name, plugin in self.plugins.items():
            metadata = self.metadata.get(plugin_name)
            if metadata and metadata.enabled:
                if self._check_dependencies(metadata.dependencies):
                    if hasattr(plugin, 'register'):
                        plugin.register(*args, **kwargs)
                else:
                    print(
                        f'Warning: Plugin {plugin_name} has unmet dependencies'
                        )

    def _check_dependencies(self, dependencies: List[str]) ->bool:
        """Check if all dependencies are available."""
        for dep in dependencies:
            if not self.container.has(dep):
                return False
        return True

    def enable_plugin(self, plugin_name: str) ->None:
        """Enable a plugin."""
        if plugin_name in self.metadata:
            self.metadata[plugin_name].enabled = True

    def disable_plugin(self, plugin_name: str) ->None:
        """Disable a plugin."""
        if plugin_name in self.metadata:
            self.metadata[plugin_name].enabled = False

    def get_plugin_info(self) ->List[PluginMetadata]:
        """Get information about all plugins."""
        return list(self.metadata.values())

    def get_enabled_plugins(self) ->List[str]:
        """Get list of enabled plugin names."""
        return [name for name, meta in self.metadata.items() if meta.enabled]

    def get_loaded_plugins(self) ->list:
        """Return a list of loaded plugin info dicts for health checks."""
        plugins_info = []
        for name, plugin in self.plugins.items():
            meta = self.metadata.get(name)
            plugins_info.append({'name': name, 'enabled': meta.enabled if
                meta else True, 'version': meta.version if meta else
                'unknown', 'description': meta.description if meta else '',
                'author': meta.author if meta else ''})
        return plugins_info
