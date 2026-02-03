# client_server_stream/server/plugins/loader.py
import importlib
import pkgutil
from typing import Dict

from client_server_stream.server.plugins.base import StreamPlugin
import client_server_stream.server.plugins as plugins_pkg


def discover_plugins() -> Dict[str, StreamPlugin]:
    plugins: Dict[str, StreamPlugin] = {}

    # IMPORTANT: use the package's __path__, not this module's
    for _, module_name, _ in pkgutil.iter_modules(plugins_pkg.__path__):
        if module_name in ("base", "loader"):
            continue

        module = importlib.import_module(
            f"{plugins_pkg.__name__}.{module_name}"
        )

        for obj in vars(module).values():
            if (
                isinstance(obj, type)
                and issubclass(obj, StreamPlugin)
                and obj is not StreamPlugin
            ):
                instance = obj()

                if not hasattr(instance, "name"):
                    raise RuntimeError(
                        f"Plugin {obj.__name__} missing 'name' attribute"
                    )

                if instance.name in plugins:
                    raise RuntimeError(
                        f"Duplicate plugin name: {instance.name}"
                    )

                plugins[instance.name] = instance

    return plugins
