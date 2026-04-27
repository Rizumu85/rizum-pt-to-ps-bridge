"""Substance 3D Painter entry point for Rizum PT-to-PS Bridge."""

from . import ui

_registered_ui = None


def start_plugin():
    """Start the Painter side of the bridge."""
    global _registered_ui
    if _registered_ui is None:
        _registered_ui = ui.register()


def close_plugin():
    """Stop the Painter side of the bridge and remove registered UI."""
    global _registered_ui
    if _registered_ui is not None:
        ui.unregister(_registered_ui)
        _registered_ui = None


if __name__ == "__main__":
    start_plugin()
