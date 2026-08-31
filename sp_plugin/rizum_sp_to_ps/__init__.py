"""Substance 3D Painter entry point for Rizum PT-to-PS Bridge."""

from . import desktop_bridge, ui

_registered_ui = None
_registered_bridge = None


def start_plugin():
    """Start the Painter side of the bridge."""
    global _registered_bridge, _registered_ui
    if _registered_ui is None:
        _registered_ui = ui.register()
        try:
            _registered_bridge = desktop_bridge.attach(
                ui._ACTIVE_PANEL,
                ui._show_modal_message,
            )
        except Exception:
            ui.unregister(_registered_ui)
            _registered_ui = None
            raise


def close_plugin():
    """Stop the Painter side of the bridge and remove registered UI."""
    global _registered_bridge, _registered_ui
    if _registered_bridge is not None:
        _registered_bridge.close()
        _registered_bridge = None
    if _registered_ui is not None:
        ui.unregister(_registered_ui)
        _registered_ui = None


if __name__ == "__main__":
    start_plugin()
