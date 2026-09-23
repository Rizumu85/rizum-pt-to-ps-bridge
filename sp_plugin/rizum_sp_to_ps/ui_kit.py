"""Vendored Rizum UI loading and settings shared by the Painter dialogs."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path


def _load_vendored_ui():
    package_name = "_rizum_pt_to_ps_bridge_ui"
    package_dir = Path(__file__).resolve().parents[2] / "rizum_ui"
    package = sys.modules.get(package_name)
    if package is not None:
        return package

    spec = importlib.util.spec_from_file_location(
        package_name,
        package_dir / "__init__.py",
        submodule_search_locations=[str(package_dir)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load vendored UI package from {package_dir}")
    package = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = package
    spec.loader.exec_module(package)
    return package


_vendored_ui = _load_vendored_ui()
_components = importlib.import_module(f"{_vendored_ui.__name__}.components")
_settings_dialog = importlib.import_module(
    f"{_vendored_ui.__name__}.settings_dialog"
)
_settings_controls = importlib.import_module(
    f"{_vendored_ui.__name__}.settings_controls"
)
_settings_layout = importlib.import_module(
    f"{_vendored_ui.__name__}.settings_layout"
)

_components = importlib.reload(_components)
_settings_controls = importlib.reload(_settings_controls)
_settings_dialog = importlib.reload(_settings_dialog)
_settings_layout = importlib.reload(_settings_layout)
apply_theme = _vendored_ui.apply_theme
build_compact_dock_stylesheet = _components.build_compact_dock_stylesheet
compact_action_bar_width = _components.compact_action_bar_width
install_compact_tooltip = _components.install_compact_tooltip
make_combo_input = _components.make_combo_input
make_collapsible_group = _components.make_collapsible_group
make_compact_action_bar = _components.make_compact_action_bar
make_compact_icon_toolbar = _components.make_compact_icon_toolbar
make_compact_stepper = _components.make_compact_stepper
make_export_tree_item = _components.make_export_tree_item
make_icon_button = _components.make_icon_button
make_inset_separator = _components.make_inset_separator
make_mock_checkbox = _components.make_mock_checkbox
update_export_tree_item = _components.update_export_tree_item
PainterSettingsDialog = _settings_dialog.PainterSettingsDialog
PAINTER_DIALOG_STYLE = _settings_controls.PAINTER_DIALOG_STYLE
AnimatedSaveButton = _settings_controls.AnimatedSaveButton
IconActionButton = _settings_controls.IconActionButton
SecondaryActionButton = _settings_controls.SecondaryActionButton
PAINTER_SETTINGS_LAYOUT = _settings_layout.PAINTER_SETTINGS_LAYOUT
default_theme = _vendored_ui.default_theme
SETTINGS_ORG = "Rizum"
SETTINGS_APP = "PTBridge"


def call_or_attr(obj, name, default=None):
    value = getattr(obj, name, default)
    return value() if callable(value) else value


def to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def optional_int(value):
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
