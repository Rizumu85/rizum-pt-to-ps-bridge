"""Local Painter loader for Rizum PT-to-PS Bridge."""

import sys
from pathlib import Path

_PLUGIN_ROOT = str(Path(__file__).resolve().parent)
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

from sp_plugin.rizum_sp_to_ps import close_plugin as _close_plugin  # noqa: E402
from sp_plugin.rizum_sp_to_ps import start_plugin as _start_plugin  # noqa: E402


def start_plugin():
    """Start the Painter bridge from the repository root plugin folder."""
    _start_plugin()


def close_plugin():
    """Stop the Painter bridge from the repository root plugin folder."""
    _close_plugin()


def reload_plugin():
    """Reload the package modules Painter keeps cached between plugin toggles."""
    import importlib

    from sp_plugin import rizum_sp_to_ps as bridge_package
    from sp_plugin.rizum_sp_to_ps import desktop_bridge, desktop_transfer

    global _close_plugin, _start_plugin
    importlib.reload(desktop_transfer)
    importlib.reload(desktop_bridge)
    importlib.reload(bridge_package.ui)
    bridge_package = importlib.reload(bridge_package)
    _close_plugin = bridge_package.close_plugin
    _start_plugin = bridge_package.start_plugin


if __name__ == "__main__":
    start_plugin()
