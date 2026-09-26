"""Painter dock registration for Rizum PT-to-PS Bridge."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from .exporter import (
    ExportCancelled,
    default_output_dir,
    write_build_bundles,
)
from .edge_smoothing import DEFAULT_STRENGTH
from .photoshop_automation import find_photoshop_executable, write_photoshop_launcher
from .photoshop_job import PhotoshopJob
from .ui_kit import (
    IconActionButton,
    PAINTER_DIALOG_STYLE,
    SETTINGS_APP,
    SETTINGS_ORG,
    apply_theme,
    build_compact_dock_stylesheet,
    call_or_attr,
    default_theme,
    make_icon_button,
    optional_int,
    to_bool,
)
from .ui_dialogs import (
    show_modal_message,
    CompactProgressDialog,
)
from .settings_ui import (
    SettingsDialog,
)
from .export_ui import (
    ExportDialog,
)


LAST_EXPORT_FILENAME = "_last_export.json"
_ACTIVE_PANEL = None
_ACTIVE_DOCK = None

BRIDGE_DOCK_BG = "#2b2b2b"
BRIDGE_DOCK_MIN_WIDTH = 210
BRIDGE_DOCK_TOOLBAR_HEIGHT = 44
BRIDGE_DOCK_DEFAULT_WIDTH = 290
BRIDGE_DOCK_DEFAULT_HEIGHT = 78


BRIDGE_DIALOG_STYLESHEET = """
QDialog {
    background: #1b1b1b;
    color: #e0e0e0;
}
QWidget#RizumDialogBody,
QWidget#RizumDialogToolbar,
QWidget#RizumDialogFooter,
QWidget#RizumSettingsBody,
QWidget#RizumSettingsRow,
QWidget#RizumPathField {
    background: transparent;
    border: 0;
}
QWidget#RizumSettingsBody,
QWidget#RizumSettingsFooter,
QWidget#RizumSettingsFooterRow,
QWidget#RizumSettingsTexts {
    background: transparent;
    border: 0;
}
QLabel#RizumDialogTitle {
    color: #e0e0e0;
    font-size: 13px;
    font-weight: 600;
}
QLabel#RizumDimLabel,
QLabel#RizumSettingsMeta {
    color: #9e9e9e;
    font-size: 12px;
    font-weight: 400;
}
QFrame#RizumSettingsRow {
    background: transparent;
    border: 0;
    border-radius: 6px;
}
QFrame#RizumSettingsRow:hover {
    background: #2b2b2b;
    border: 0;
}
QFrame#RizumSettingsMockSelect {
    background: #222222;
    border: 1px solid transparent;
    border-radius: 6px;
}
QLineEdit#RizumSettingsPathInput {
    color: #9e9e9e;
    background: transparent;
    border: 0;
    padding: 0;
    selection-background-color: #343434;
    selection-color: #e0e0e0;
}
QLineEdit#RizumSettingsPathInput:hover,
QLineEdit#RizumSettingsPathInput:focus {
    color: #e0e0e0;
    background: transparent;
    border: 0;
}
QTreeWidget {
    background: #1b1b1b;
    border: 0;
    color: #e0e0e0;
    outline: 0;
    padding: 4px 0;
}
QTreeWidget::item {
    min-height: 28px;
    padding: 4px 8px;
    border-radius: 6px;
}
QTreeWidget::item:hover {
    background: rgba(255, 255, 255, 18);
}
QPlainTextEdit {
    background: #222222;
    border: 0;
    border-radius: 6px;
    color: #e0e0e0;
    padding: 8px;
}
QLineEdit#RizumPathInput {
    background: transparent;
    border: 0;
    color: #e0e0e0;
    padding: 0;
}
QWidget#RizumPathField {
    background: #222222;
    border-radius: 6px;
}
QCheckBox {
    color: #e0e0e0;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid #ffffff;
    background: transparent;
}
QCheckBox::indicator:checked {
    background: #ffffff;
}
QComboBox {
    min-height: 28px;
    padding: 2px 8px;
    border: 0;
    border-radius: 6px;
    background: #222222;
    color: #e0e0e0;
}
"""


def _apply_bridge_dock_surface(widget):
    """Apply shared dock styling without replacing Painter's unique dock objectName."""
    from PySide6 import QtGui

    compact_stylesheet = build_compact_dock_stylesheet().replace(
        "QWidget#RizumCompactDockSurface",
        "QWidget#RizumPtToPsBridgePanel",
    )
    widget.setStyleSheet(
        widget.styleSheet()
        + compact_stylesheet
        + f"""
QWidget#RizumPtToPsBridgePanel {{
    background: {BRIDGE_DOCK_BG};
    border: 0;
}}
QWidget#RizumPtToPsBridgePanel QLabel#RizumDimLabel {{
    background: transparent;
    border: 0;
    color: #9e9e9e;
    font-size: 12px;
}}
"""
    )
    palette = widget.palette()
    panel_color = QtGui.QColor(BRIDGE_DOCK_BG)
    palette.setColor(QtGui.QPalette.ColorRole.Window, panel_color)
    palette.setColor(QtGui.QPalette.ColorRole.Base, panel_color)
    widget.setPalette(palette)
    widget.setAutoFillBackground(True)


def _make_bridge_dock_toolbar(QtCore, QtWidgets):
    """Create the responsive primary-action strip used by the live dock."""
    toolbar = QtWidgets.QWidget()
    toolbar.setObjectName("RizumBridgeDockToolbar")
    toolbar.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    toolbar.setStyleSheet(
        "QWidget#RizumBridgeDockToolbar { background: transparent; border: 0; }"
    )
    layout = QtWidgets.QHBoxLayout(toolbar)

    theme = PAINTER_DIALOG_STYLE
    export_button = IconActionButton(
        "Export",
        "action-export.svg",
        theme["accent"],
        theme["accent_hover"],
        theme["accent_pressed"],
        theme["accent_text"],
        default_theme.radius_small,
    )
    export_button.setObjectName("RizumBridgeDockExport")
    export_button.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )

    # Bridge is a primary workflow next to Export, so it gets a label rather
    # than an unlabelled glyph; desktop_bridge.DesktopBridgeController owns
    # its enabled state and tooltip.
    bridge_button = IconActionButton(
        "Bridge",
        "action-bridge.svg",
        theme["control"],
        theme["control_hover"],
        theme["control_pressed"],
        theme["text"],
        default_theme.radius_small,
    )
    bridge_button.setObjectName("RizumBridgeDockBridge")
    bridge_button.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    bridge_button.setAttribute(
        QtCore.Qt.WidgetAttribute.WA_AlwaysShowToolTips,
        True,
    )

    settings_button = make_icon_button("settings.svg", "Settings")
    settings_button.setObjectName("RizumBridgeDockSettings")

    layout.addWidget(export_button, 1)
    layout.addWidget(bridge_button, 1)
    layout.addWidget(settings_button)

    def set_ui_scale(scale):
        scale = max(0.75, min(2.0, float(scale)))

        def metric(value, minimum):
            return max(minimum, int(round(value * scale)))

        margin = metric(12, 9)
        spacing = metric(6, 5)
        control_height = metric(28, 21)
        icon_frame = metric(22, 17)
        icon_size = metric(16, 12)
        toolbar_height = metric(BRIDGE_DOCK_TOOLBAR_HEIGHT, 33)

        layout.setContentsMargins(margin, 0, margin, 0)
        layout.setSpacing(spacing)
        for button in (export_button, bridge_button):
            button.setCompactHeight(control_height)
            button.setMinimumWidth(metric(80, 64))
        for button in (settings_button,):
            button.setStyleSheet(
                f"QPushButton#{button.objectName()} {{"
                f" min-width: {icon_frame}px; max-width: {icon_frame}px;"
                f" min-height: {icon_frame}px; max-height: {icon_frame}px;"
                " padding: 0; margin: 0; border: 0; background: transparent; }"
            )
            button.setFixedSize(icon_frame, icon_frame)
            button.setPaintedIconSize(icon_size)
            if hasattr(button, "setCompactTooltipScale"):
                button.setCompactTooltipScale(scale)

        toolbar.setFixedHeight(toolbar_height)
        toolbar.setMinimumWidth(
            margin * 2
            + export_button.minimumWidth()
            + bridge_button.minimumWidth()
            + icon_frame
            + spacing * 2
        )
        toolbar.updateGeometry()

    toolbar.setUiScale = set_ui_scale
    toolbar.actionButtons = lambda: (
        export_button,
        bridge_button,
        settings_button,
    )
    return toolbar

class BridgePanel:
    """Painter dock panel for the PT Bridge workflow."""

    def __init__(self):
        from PySide6 import QtCore, QtGui, QtWidgets

        self.QtCore = QtCore
        self.QtGui = QtGui
        self.QtWidgets = QtWidgets
        self._closing = False
        self._build_job = None
        self.user_settings = self._load_user_settings()
        self.widget = QtWidgets.QWidget()
        self.widget.setObjectName("RizumPtToPsBridgePanel")
        self.widget.setWindowTitle("PT Bridge")
        self.widget.setMinimumSize(BRIDGE_DOCK_MIN_WIDTH, BRIDGE_DOCK_TOOLBAR_HEIGHT)
        self.widget.resize(BRIDGE_DOCK_DEFAULT_WIDTH, BRIDGE_DOCK_TOOLBAR_HEIGHT)
        apply_theme(self.widget, mode="overlay")
        _apply_bridge_dock_surface(self.widget)
        self.widget.setStyleSheet(self.widget.styleSheet() + BRIDGE_DIALOG_STYLESHEET)

        outer_layout = QtWidgets.QVBoxLayout(self.widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        dock_actions = _make_bridge_dock_toolbar(QtCore, QtWidgets)
        self._dock_toolbar = dock_actions
        self.dock_export_button, self.dock_bridge_button, self.dock_settings_button = (
            dock_actions.actionButtons()
        )
        self.dock_export_button.clicked.connect(self.open_export_dialog)
        self.dock_settings_button.clicked.connect(self.open_settings_dialog)
        outer_layout.addWidget(
            dock_actions,
            0,
            QtCore.Qt.AlignmentFlag.AlignTop,
        )
        outer_layout.addStretch(1)

        class _DockScaleFilter(QtCore.QObject):
            def eventFilter(filter_self, watched, event):
                del filter_self, watched
                if event.type() in (
                    QtCore.QEvent.Type.FontChange,
                    QtCore.QEvent.Type.ApplicationFontChange,
                ) and not self._closing:
                    QtCore.QTimer.singleShot(0, self._apply_dock_ui_scale)
                return False

        self._dock_scale_filter = _DockScaleFilter(self.widget)
        self.widget.installEventFilter(self._dock_scale_filter)
        self._apply_dock_ui_scale()

    def close(self):
        """Stop owned Qt helpers before Painter removes the dock."""
        self._closing = True
        self.widget.removeEventFilter(self._dock_scale_filter)
        if self._build_job is not None:
            self._build_job.stop()
            self._build_job = None

    def _current_ui_scale(self):
        app = self.QtWidgets.QApplication.instance()
        value = app.property("rizumUiFontScale") if app is not None else 1.0
        try:
            return max(0.75, min(2.0, float(value or 1.0)))
        except (TypeError, ValueError):
            return 1.0

    def _apply_dock_ui_scale(self):
        if self._closing:
            return
        scale = self._current_ui_scale()
        self._dock_toolbar.setUiScale(scale)
        minimum_width = max(
            int(round(BRIDGE_DOCK_MIN_WIDTH * scale)),
            self._dock_toolbar.minimumWidth(),
        )
        self.widget.setMinimumSize(minimum_width, self._dock_toolbar.height())
        self.widget.updateGeometry()
        if _ACTIVE_PANEL is self and _ACTIVE_DOCK is not None:
            _resize_floating_dock(_ACTIVE_DOCK, self)

    def _project_is_open(self):
        try:
            import substance_painter.project

            return call_or_attr(substance_painter.project, "is_open", False)
        except Exception:
            return False

    def _project_is_ready(self):
        try:
            import substance_painter.project

            return (
                call_or_attr(substance_painter.project, "is_open", False)
                and call_or_attr(substance_painter.project, "is_in_edition_state", False)
            )
        except Exception:
            return False

    def active_target_key(self):
        import substance_painter.textureset

        stack = call_or_attr(substance_painter.textureset, "get_active_stack")
        texture_set = call_or_attr(stack, "material")
        return (texture_set.name, call_or_attr(stack, "name") or "")

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.open()

    def _load_user_settings(self):
        store = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        bit_depth = optional_int(store.value("bit_depth", None))
        return {
            "photoshop_path": store.value("photoshop_path", "", str) or "",
            "infinite_padding": to_bool(store.value("infinite_padding", False)),
            "dilation": optional_int(store.value("dilation", 8)) or 8,
            "export_uv_map": to_bool(store.value("export_uv_map", False)),
            "bit_depth": bit_depth,
            "edge_smoothing": _smoothing_strength(store.value("edge_smoothing", None)),
            # On by default: a finished PSD holds the pixels, and 4K PNGs per
            # layer filled the export folder with copies nobody opens.
            "cleanup_layer_pngs": to_bool(store.value("cleanup_layer_pngs", True)),
            "psd_size": optional_int(store.value("psd_size", None)),
            "render_scale": _render_scale(store.value("render_scale", 1)),
        }

    def save_user_settings(self, values):
        store = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        store.setValue("photoshop_path", values.get("photoshop_path") or "")
        store.setValue("infinite_padding", bool(values.get("infinite_padding")))
        store.setValue("dilation", int(values.get("dilation") or 8))
        store.setValue("export_uv_map", bool(values.get("export_uv_map")))
        store.setValue("edge_smoothing", _smoothing_strength(values.get("edge_smoothing")))
        store.setValue("cleanup_layer_pngs", bool(values.get("cleanup_layer_pngs", True)))
        if values.get("psd_size"):
            store.setValue("psd_size", int(values["psd_size"]))
        else:
            store.remove("psd_size")
        store.setValue("render_scale", _render_scale(values.get("render_scale")))
        bit_depth = values.get("bit_depth")
        if bit_depth:
            store.setValue("bit_depth", int(bit_depth))
        else:
            store.remove("bit_depth")
        store.sync()
        self.user_settings = self._load_user_settings()

    def open_export_dialog(self):
        dialog = ExportDialog(self)
        dialog.open()

    def _run_export_selections(self, label, selections, overrides=None):
        if not self._project_is_open():
            return {"ok": False, "message": "Open a Painter project before exporting."}
        if not self._project_is_ready():
            return {
                "ok": False,
                "message": "Painter project is still loading or not editable.",
            }
        if not selections:
            return {"ok": False, "message": "No channels were selected."}

        base_settings = self._base_export_settings(overrides)
        output_dir = default_output_dir(base_settings)
        all_paths = []
        texture_sets = []
        stacks = []
        channels = []

        self._set_action_buttons_enabled(False)
        progress = self._create_export_progress(label)

        try:
            for target, selected_channels in selections:
                texture_set = target["texture_set"]
                stack = target["stack"]
                settings = {
                    **base_settings,
                    "texture_sets": [texture_set],
                    "stacks": [stack],
                    "channels": list(selected_channels),
                }
                texture_sets.append(texture_set)
                stacks.append(stack)
                channels.extend(selected_channels)
                all_paths.extend(
                    write_build_bundles(
                        output_dir,
                        settings=settings,
                        progress_callback=lambda event: self._update_export_progress(
                            progress,
                            event,
                        ),
                    )
                )
        except ExportCancelled:
            return {
                "ok": False,
                "message": "Export cancelled. Completed files were kept.",
            }
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            return {"ok": False, "message": f"{type(exc).__name__}: {exc}"}
        finally:
            progress.close()
            self._set_action_buttons_enabled(True)

        combined_settings = {
            **base_settings,
            "texture_sets": sorted(set(texture_sets)),
            "stacks": _unique_preserving_order(stacks),
            "channels": sorted(set(channels)),
        }
        output_dir = Path(output_dir)
        export_list = self._write_last_export_list(
            label,
            all_paths,
            output_dir,
            combined_settings,
        )
        return {
            "ok": True,
            "message": f"Exported {len(all_paths)} build request(s).",
            "count": len(all_paths),
            "output_dir": output_dir,
            "export_list": export_list,
            "paths": list(all_paths),
        }

    def photoshop_executable(self):
        return find_photoshop_executable(self.user_settings.get("photoshop_path") or "")

    def launch_photoshop(self, launcher_path):
        executable = self.photoshop_executable()
        if executable is None:
            return False, "Photoshop was not found. Set Photoshop.exe in Settings."

        # Passing JSX to Photoshop is the host-supported zero-click path used
        # by the released exporter; UXP panels are lazy and cannot receive a
        # reliable external launch event when they have never been opened.
        started = self.QtCore.QProcess.startDetached(
            str(executable),
            [str(Path(launcher_path).resolve())],
        )
        if isinstance(started, tuple):
            started = started[0]
        if not started:
            return False, f"Could not launch Photoshop: {executable}"
        return True, ""

    def start_photoshop_build(self, export_list, output_dir):
        """Launch the PSD build and watch it until Photoshop reports back."""
        receipts = Path(output_dir) / "_desktop_bridge" / "photoshop_build"
        launch = write_photoshop_launcher(export_list, receipts)
        launched, message = self.launch_photoshop(launch.launcher_path)
        if not launched:
            return False, message
        if self._build_job is not None:
            self._build_job.stop()
        # Photoshop shows its own build progress and error summary, so Painter
        # stays quiet on success and only speaks up when the script never ran.
        self._build_job = PhotoshopJob(
            self.QtCore,
            self.widget,
            launch,
            on_progress=lambda _progress: None,
            on_done=lambda _result: self._photoshop_build_finished(launch),
            on_failed=self._photoshop_build_failed,
        )
        self._build_job.start()
        return True, ""

    def _photoshop_build_finished(self, launch):
        self._build_job = None
        for receipt in (launch.progress_path, launch.result_path):
            receipt.unlink(missing_ok=True)

    def _photoshop_build_failed(self, message):
        self._build_job = None
        if not self._closing:
            show_modal_message(self.QtWidgets, self.widget, "Photoshop build", message)

    def _base_export_settings(self, overrides=None):
        settings = {
            "normal_map_format": "OpenGL",
            "infinite_padding": bool(self.user_settings.get("infinite_padding")),
            "dilation": int(self.user_settings.get("dilation") or 8),
            "keep_alpha": True,
            "export_uv_map": bool(self.user_settings.get("export_uv_map")),
            # These were read from Settings only by Bridge transfers; exports
            # silently used their defaults.
            "edge_smoothing": self.user_settings.get("edge_smoothing"),
            "cleanup_layer_pngs": self.user_settings.get("cleanup_layer_pngs", True),
            "psd_size": self.user_settings.get("psd_size"),
            "render_scale": self.user_settings.get("render_scale", 1),
            # The Export dialog's size choices apply to this export only.
            **(overrides or {}),
        }
        bit_depth = self.user_settings.get("bit_depth")
        if bit_depth:
            settings["bit_depth"] = int(bit_depth)
        return settings

    def _write_last_export_list(self, label, paths, output_dir, settings):
        list_path = output_dir / LAST_EXPORT_FILENAME
        payload = {
            "schema_version": 1,
            "request_type": "build_list",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "label": label,
            "output_dir": str(output_dir),
            "settings": {
                "texture_sets": settings.get("texture_sets"),
                "stacks": settings.get("stacks"),
                "channels": settings.get("channels"),
                "export_uv_map": bool(settings.get("export_uv_map")),
                "cleanup_layer_pngs": bool(settings.get("cleanup_layer_pngs", True)),
            },
            "build_requests": [
                {
                    "path": str(path),
                    "relative_path": str(path.relative_to(output_dir))
                    if _is_relative_to(path, output_dir)
                    else str(path),
                }
                for path in paths
            ],
        }
        list_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return list_path

    def _set_action_buttons_enabled(self, enabled):
        self.dock_export_button.setEnabled(enabled)
        self.dock_settings_button.setEnabled(enabled)

    def _create_export_progress(self, label):
        progress = CompactProgressDialog(self, "Export", f"Exporting {label}...")
        progress.show()
        self.QtWidgets.QApplication.processEvents()
        return progress

    def _update_export_progress(self, progress, event):
        if event.get("stage") == "heartbeat":
            # Painter host exports must stay on its UI thread. Geometry work
            # therefore yields cooperatively so returning to Painter still
            # repaints the dialog and lets Cancel or the title-bar X respond.
            progress.dialog.repaint()
            self.QtWidgets.QApplication.processEvents()
            return not progress.wasCanceled()

        total = int(event.get("total") or 0)
        value = int(event.get("value") or 0)
        text = event.get("text") or "Exporting..."
        if total > 0:
            progress.setRange(0, total)
            progress.setValue(max(0, min(value, total)))
        else:
            progress.setRange(0, 0)
        progress.setLabelText(text)
        progress.dialog.repaint()
        self.QtWidgets.QApplication.processEvents()
        return not progress.wasCanceled()

def _render_scale(value):
    scale = optional_int(value) or 1
    return scale if scale in (1, 2, 4) else 1


def _smoothing_strength(value):
    strength = optional_int(value)
    return DEFAULT_STRENGTH if strength is None else max(0, min(100, strength))


def _is_relative_to(path, parent):
    try:
        Path(path).relative_to(parent)
        return True
    except ValueError:
        return False


def _unique_preserving_order(values):
    seen = set()
    unique = []
    for value in values:
        marker = "" if value is None else value
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(value)
    return unique


def register():
    """Register Painter UI elements and return handles for cleanup."""
    import substance_painter as sp

    global _ACTIVE_DOCK, _ACTIVE_PANEL
    panel = BridgePanel()
    _ACTIVE_PANEL = panel
    dock = sp.ui.add_dock_widget(panel.widget)
    _ACTIVE_DOCK = dock
    dock.setObjectName("RizumPtToPsBridgeDock")
    dock.setWindowTitle("PT Bridge")
    _connect_floating_resize(dock, panel)
    dock.show()
    dock.raise_()
    _resize_floating_dock(dock, panel)
    sp.logging.info("Rizum PT-to-PS Painter plugin loaded")
    return [dock]


def unregister(handles):
    """Remove Painter UI elements registered by this plugin."""
    import substance_painter as sp

    global _ACTIVE_DOCK, _ACTIVE_PANEL
    if _ACTIVE_PANEL is not None:
        _ACTIVE_PANEL.close()
        _ACTIVE_PANEL = None
    _ACTIVE_DOCK = None

    for handle in handles:
        sp.ui.delete_ui_element(handle)
    handles.clear()
    sp.logging.info("Rizum PT-to-PS Painter plugin unloaded")


def _connect_floating_resize(dock, panel):
    try:
        dock.topLevelChanged.connect(lambda floating: _resize_floating_dock(dock, panel) if floating else None)
    except Exception:
        pass


def _resize_floating_dock(dock, panel):
    if dock is None or panel is None:
        return
    scale = panel._current_ui_scale()
    minimum_width = panel.widget.minimumWidth()
    minimum_height = max(
        panel._dock_toolbar.height(),
        int(round(BRIDGE_DOCK_DEFAULT_HEIGHT * scale)),
    )
    default_width = max(
        minimum_width,
        int(round(BRIDGE_DOCK_DEFAULT_WIDTH * scale)),
    )
    try:
        dock.setMinimumSize(minimum_width, minimum_height)
    except Exception:
        pass
    try:
        if hasattr(dock, "isFloating") and not dock.isFloating():
            return
    except Exception:
        pass
    try:
        dock.resize(default_width, minimum_height)
    except Exception:
        pass
    try:
        panel.widget.resize(default_width, panel._dock_toolbar.height())
    except Exception:
        pass
    try:
        panel.QtCore.QTimer.singleShot(
            0,
            lambda: dock.resize(default_width, minimum_height),
        )
    except Exception:
        pass
