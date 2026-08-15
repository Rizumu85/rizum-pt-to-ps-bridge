"""Painter UI registration for Rizum PT-to-PS Bridge."""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .exporter import (
    ExportCancelled,
    default_output_dir,
    list_export_targets,
    write_build_bundles,
)
from .photoshop_automation import write_photoshop_launcher
from .export_selection_memory import (
    ExportSelectionMemory,
    current_project_identity,
    target_selection_key,
)


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
ActionButton = _components.ActionButton
apply_theme = _vendored_ui.apply_theme
build_compact_dock_stylesheet = _components.build_compact_dock_stylesheet
compact_action_bar_width = _components.compact_action_bar_width
compact_footer_button_width = _components.compact_footer_button_width
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
set_compact_footer_button_width = _components.set_compact_footer_button_width
update_export_tree_item = _components.update_export_tree_item
PainterSettingsDialog = _settings_dialog.PainterSettingsDialog
PAINTER_DIALOG_STYLE = _settings_controls.PAINTER_DIALOG_STYLE
AnimatedSaveButton = _settings_controls.AnimatedSaveButton
IconActionButton = _settings_controls.IconActionButton
SecondaryActionButton = _settings_controls.SecondaryActionButton
PAINTER_SETTINGS_LAYOUT = _settings_layout.PAINTER_SETTINGS_LAYOUT
default_theme = _vendored_ui.default_theme

LAST_EXPORT_FILENAME = "_last_export.json"
SETTINGS_ORG = "Rizum"
SETTINGS_APP = "PTBridge"
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
        "QWidget#RizumPtToPsSmokeTestPanel",
    )
    widget.setStyleSheet(
        widget.styleSheet()
        + compact_stylesheet
        + f"""
QWidget#RizumPtToPsSmokeTestPanel {{
    background: {BRIDGE_DOCK_BG};
    border: 0;
}}
QWidget#RizumPtToPsSmokeTestPanel QLabel#RizumDimLabel {{
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


def _section_label(QtWidgets, text):
    label = QtWidgets.QLabel(text)
    label.setObjectName("RizumSettingsSection")
    label.setFixedHeight(22)
    return label


def _settings_row(QtWidgets, label_text, meta_text, control):
    row = QtWidgets.QWidget()
    row.setObjectName("RizumSettingsRow")
    row.setFixedHeight(42 if meta_text else 36)
    layout = QtWidgets.QHBoxLayout(row)
    layout.setContentsMargins(8, 0, 8, 0)
    layout.setSpacing(12)

    text_block = QtWidgets.QWidget()
    text_layout = QtWidgets.QVBoxLayout(text_block)
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(1)
    label = QtWidgets.QLabel(label_text)
    label.setObjectName("RizumDialogTitle")
    text_layout.addWidget(label)
    if meta_text:
        meta = QtWidgets.QLabel(meta_text)
        meta.setObjectName("RizumSettingsMeta")
        text_layout.addWidget(meta)
    layout.addWidget(text_block, 1)
    layout.addWidget(control, 0)
    return row


def _settings_label(QtWidgets, text, object_name):
    label = QtWidgets.QLabel(text)
    label.setObjectName(object_name)
    return label


def _settings_section(QtWidgets, text, first=False):
    label = _settings_label(QtWidgets, text.upper(), "RizumSettingsSection")
    metric = (
        PAINTER_SETTINGS_LAYOUT.first_section_height
        if first
        else PAINTER_SETTINGS_LAYOUT.section_height
    )
    label._rizum_layout_metric = metric
    label.setFixedHeight(metric.design)
    return label


def _settings_frame_row(QtWidgets, height=40):
    row = QtWidgets.QFrame()
    row.setObjectName("RizumSettingsRow")
    row._rizum_base_height = height
    row.setFixedHeight(height)
    layout = QtWidgets.QHBoxLayout(row)
    layout.setContentsMargins(
        0,
        PAINTER_SETTINGS_LAYOUT.row_padding_y.design,
        0,
        PAINTER_SETTINGS_LAYOUT.row_padding_y.design,
    )
    layout.setSpacing(PAINTER_SETTINGS_LAYOUT.row_spacing)
    return row, layout


def _settings_text_block(QtWidgets, name, meta=""):
    widget = QtWidgets.QWidget()
    widget.setObjectName("RizumSettingsTexts")
    layout = QtWidgets.QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    layout.addWidget(_settings_label(QtWidgets, name, "RizumSettingsItemName"))
    if meta:
        layout.addWidget(_settings_label(QtWidgets, meta, "RizumSettingsItemMeta"))
    return widget


def _make_settings_toggle(QtCore, QtGui, QtWidgets, checked=False):
    class _SettingsToggle(QtWidgets.QAbstractButton):
        BASE_WIDTH = 36
        BASE_HEIGHT = 20
        MIN_HEIGHT = 15

        def __init__(self):
            super().__init__()
            self.setObjectName("RizumSettingsToggle")
            self.setCheckable(True)
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)
            self.setStyleSheet("background: transparent; border: 0;")
            self._compact_height = self.BASE_HEIGHT
            self._knob_margin = 3.0
            self._knob_size = 14.0
            self._offset = 0.0
            self._animation = None
            self.toggled.connect(self._animate_to_state)
            self.setCompactHeight(self.BASE_HEIGHT)
            self.setChecked(bool(checked))

        def _knob_travel(self):
            return max(
                0.0,
                float(self.width()) - self._knob_size - self._knob_margin * 2,
            )

        def setCompactHeight(self, height):
            if self._animation is not None:
                self._animation.stop()
                self._animation = None
            self._compact_height = max(self.MIN_HEIGHT, int(round(height)))
            scale = self._compact_height / float(self.BASE_HEIGHT)
            self._knob_margin = 3.0 * scale
            self._knob_size = 14.0 * scale
            self.setFixedSize(
                max(27, int(round(self.BASE_WIDTH * scale))),
                self._compact_height,
            )
            self._offset = self._knob_travel() if self.isChecked() else 0.0
            self.updateGeometry()
            self.update()

        def getOffset(self):
            return self._offset

        def setOffset(self, value):
            self._offset = float(value)
            self.update()

        offset = QtCore.Property(float, getOffset, setOffset)

        def _animate_to_state(self, enabled):
            if self._animation is not None:
                self._animation.stop()
            animation = QtCore.QPropertyAnimation(self, b"offset", self)
            animation.setDuration(180)
            animation.setStartValue(self._offset)
            animation.setEndValue(self._knob_travel() if enabled else 0.0)
            animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            self._animation = animation
            animation.start()

        def paintEvent(self, event):
            del event
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            track = QtCore.QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(
                QtGui.QColor(PAINTER_DIALOG_STYLE["accent"])
                if self.isChecked()
                else QtGui.QColor(PAINTER_DIALOG_STYLE["control"])
            )
            painter.drawRoundedRect(track, track.height() / 2.0, track.height() / 2.0)
            painter.setBrush(QtGui.QColor(PAINTER_DIALOG_STYLE["muted"]))
            painter.drawEllipse(
                QtCore.QRectF(
                    self._knob_margin + self._offset,
                    self._knob_margin,
                    self._knob_size,
                    self._knob_size,
                )
            )
            painter.end()

    return _SettingsToggle()


def _make_settings_reveal_row(QtCore, QtWidgets, content, expanded_height):
    class _SettingsRevealRow(QtWidgets.QFrame):
        def __init__(self):
            super().__init__()
            self.setObjectName("RizumSettingsRevealRow")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)
            self.setStyleSheet("background: transparent; border: 0;")
            self._expanded_height = int(expanded_height)
            self._gap = PAINTER_SETTINGS_LAYOUT.body_spacing.design
            self._progress = 1.0
            self._gap_layout = None
            self._geometry_callback = None
            self._animation = None
            reveal_layout = QtWidgets.QVBoxLayout(self)
            reveal_layout.setContentsMargins(0, 0, 0, 0)
            reveal_layout.setSpacing(0)
            reveal_layout.addWidget(content)
            self.setFixedHeight(self._expanded_height)

        def setExpandedHeight(self, height):
            self._expanded_height = max(0, int(round(height)))
            self._sync_geometry()

        def expandedHeight(self):
            return self._expanded_height

        def setGapLayout(self, layout):
            self._gap_layout = layout
            self._sync_geometry()

        def setGap(self, gap):
            self._gap = max(0, int(round(gap)))
            self._sync_geometry()

        def setGeometryCallback(self, callback):
            self._geometry_callback = callback

        def _sync_geometry(self):
            progress = max(0.0, min(1.0, self._progress))
            self.setFixedHeight(round(self._expanded_height * progress))
            if self._gap_layout is not None:
                self._gap_layout.setSpacing(round(self._gap * progress))
            if self._geometry_callback is not None:
                self._geometry_callback(progress)

        def getRevealProgress(self):
            return self._progress

        def setRevealProgress(self, value):
            self._progress = float(value)
            self._sync_geometry()

        revealProgress = QtCore.Property(
            float,
            getRevealProgress,
            setRevealProgress,
        )

        def setExpanded(self, expanded, animate=True):
            target = 1.0 if expanded else 0.0
            self.setAttribute(
                QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                not expanded,
            )
            if self._animation is not None:
                self._animation.stop()
            if not animate:
                self.setRevealProgress(target)
                return
            animation = QtCore.QPropertyAnimation(self, b"revealProgress", self)
            animation.setDuration(
                max(100, round(180 * abs(target - self._progress)))
            )
            animation.setStartValue(self._progress)
            animation.setEndValue(target)
            animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            self._animation = animation
            animation.start()

    return _SettingsRevealRow()


def _show_modal_message(QtWidgets, parent, title, message):
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setModal(True)
    dialog.setFixedWidth(318)
    apply_theme(dialog, mode="overlay")

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(10)

    title_label = QtWidgets.QLabel(title)
    title_label.setObjectName("RizumDialogTitle")
    layout.addWidget(title_label)
    layout.addWidget(make_inset_separator(0, thickness=1))

    message_label = QtWidgets.QLabel(message)
    message_label.setObjectName("RizumDimLabel")
    message_label.setWordWrap(True)
    message_label.setMinimumHeight(42)
    layout.addWidget(message_label)

    footer = QtWidgets.QHBoxLayout()
    footer.setContentsMargins(0, 6, 0, 0)
    footer.addStretch(1)
    ok_button = ActionButton.create("OK", "dialog-primary")
    ok_button.clicked.connect(dialog.accept)
    set_compact_footer_button_width(
        ok_button,
        compact_footer_button_width(ok_button, minimum=68, maximum=96),
    )
    footer.addWidget(ok_button)
    layout.addLayout(footer)

    dialog.setStyleSheet(dialog.styleSheet() + BRIDGE_DIALOG_STYLESHEET)
    dialog.exec()


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

    bridge_button = make_icon_button(
        "action-bridge.svg",
        "Layer mapping is not available yet. Export, then build in Photoshop.",
    )
    bridge_button.setObjectName("RizumBridgeDockBridge")
    bridge_button.setEnabled(False)
    bridge_button.setAttribute(
        QtCore.Qt.WidgetAttribute.WA_AlwaysShowToolTips,
        True,
    )
    bridge_button.setToolTip(
        "Layer mapping is not available yet. Export, then build in Photoshop."
    )

    settings_button = make_icon_button("settings.svg", "Settings")
    settings_button.setObjectName("RizumBridgeDockSettings")

    layout.addWidget(export_button, 1)
    layout.addWidget(bridge_button)
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
        export_button.setCompactHeight(control_height)
        export_button.setMinimumWidth(metric(96, 72))
        for button in (bridge_button, settings_button):
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
            + icon_frame * 2
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


class SettingsDialog:
    """Global Painter-side bridge settings."""

    def __init__(self, panel):
        self.panel = panel
        self.QtCore = panel.QtCore
        self.QtGui = panel.QtGui
        self.QtWidgets = panel.QtWidgets

        self.dialog = PainterSettingsDialog(panel.widget)
        self.dialog.setObjectName("RizumSettingsDialog")
        self.dialog.setWindowTitle("Settings")
        self.dialog.setModal(True)
        self.dialog.setSizePolicy(
            self.QtWidgets.QSizePolicy.Policy.Fixed,
            self.QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._settings_sections = []
        self._settings_rows = []
        self._text_blocks = []
        self._base_height = None
        self._design_height = None

        surface_layout = self.dialog.settingsSurfaceLayout()

        body = self.QtWidgets.QWidget()
        body.setObjectName("RizumSettingsBody")
        body_layout = self.QtWidgets.QVBoxLayout(body)
        body_layout.setContentsMargins(
            PAINTER_SETTINGS_LAYOUT.body_margin_x.design,
            PAINTER_SETTINGS_LAYOUT.body_margin_top.design,
            PAINTER_SETTINGS_LAYOUT.body_margin_x.design,
            PAINTER_SETTINGS_LAYOUT.body_margin_bottom.design,
        )
        body_layout.setSpacing(PAINTER_SETTINGS_LAYOUT.body_spacing.design)
        self._settings_body = body
        self._body_layout = body_layout

        export_section = _settings_section(self.QtWidgets, "Export", first=True)
        self._settings_sections.append(export_section)
        body_layout.addWidget(export_section)

        padding_stack = self.QtWidgets.QWidget()
        padding_stack.setObjectName("RizumSettingsPaddingStack")
        padding_stack_layout = self.QtWidgets.QVBoxLayout(padding_stack)
        padding_stack_layout.setContentsMargins(0, 0, 0, 0)
        padding_stack_layout.setSpacing(0)

        self.infinite_padding = _make_settings_toggle(self.QtCore, self.QtGui, self.QtWidgets)
        padding_row, padding_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.detail_row_height.design,
        )
        self._settings_rows.append(padding_row)
        padding_texts = self._make_text_block("Padding", "Infinite")
        self.padding_meta = padding_texts.findChild(self.QtWidgets.QLabel, "RizumSettingsItemMeta")
        padding_layout.addWidget(padding_texts)
        padding_layout.addStretch(1)
        padding_layout.addWidget(self.infinite_padding)
        padding_stack_layout.addWidget(padding_row)

        dilation_row, dilation_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.detail_row_height.design,
        )
        self._settings_rows.append(dilation_row)
        dilation_layout.addWidget(self._make_text_block("Dilation", "px"))
        dilation_layout.addStretch(1)
        self.dilation_stepper = make_compact_stepper(8, minimum=0, maximum=999, step=1)
        dilation_layout.addWidget(self.dilation_stepper)
        self.dilation_reveal = _make_settings_reveal_row(
            self.QtCore,
            self.QtWidgets,
            dilation_row,
            PAINTER_SETTINGS_LAYOUT.detail_row_height.design,
        )
        self.dilation_reveal.setGapLayout(padding_stack_layout)
        self.dilation_reveal.setGeometryCallback(self._sync_dialog_height)
        padding_stack_layout.addWidget(self.dilation_reveal)
        body_layout.addWidget(padding_stack)

        self.bit_depth = make_combo_input([("Texture Set", None), ("8-bit", 8), ("16-bit", 16)])
        self.bit_depth.setFitToContents(False)
        self.bit_depth.setFixedWidth(126)
        bit_depth_row, bit_depth_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.row_height.design,
        )
        self._settings_rows.append(bit_depth_row)
        bit_depth_layout.addWidget(_settings_label(self.QtWidgets, "Bit depth", "RizumSettingsItemName"))
        bit_depth_layout.addStretch(1)
        bit_depth_layout.addWidget(self.bit_depth)
        body_layout.addWidget(bit_depth_row)

        self.export_uv_map = _make_settings_toggle(
            self.QtCore,
            self.QtGui,
            self.QtWidgets,
        )
        uv_map_row, uv_map_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.detail_row_height.design,
        )
        self._settings_rows.append(uv_map_row)
        self.uv_map_texts = self._make_text_block(
            "UV map",
            "Add wireframe as the top Photoshop layer",
        )
        uv_map_layout.addWidget(self.uv_map_texts)
        uv_map_layout.addStretch(1)
        uv_map_layout.addWidget(self.export_uv_map)
        body_layout.addWidget(uv_map_row)

        self.auto_open_photoshop = _make_settings_toggle(self.QtCore, self.QtGui, self.QtWidgets)
        auto_row, auto_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.detail_row_height.design,
        )
        self._settings_rows.append(auto_row)
        self.auto_texts = self._make_text_block(
            "Auto-build in Photoshop",
            "Hand off after a successful export",
        )
        auto_layout.addWidget(self.auto_texts)
        auto_layout.addStretch(1)
        auto_layout.addWidget(self.auto_open_photoshop)

        photoshop_section = _settings_section(self.QtWidgets, "Photoshop")
        self._settings_sections.append(photoshop_section)
        body_layout.addWidget(photoshop_section)
        body_layout.addWidget(auto_row)
        path_row, path_row_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.row_height.design,
        )
        self._settings_rows.append(path_row)
        self.path_field = self.QtWidgets.QFrame()
        self.path_field.setObjectName("RizumSettingsMockSelect")
        self.path_field.setFixedHeight(PAINTER_SETTINGS_LAYOUT.control_height.design)
        path_layout = self.QtWidgets.QHBoxLayout(self.path_field)
        path_layout.setContentsMargins(8, 0, 8, 0)
        path_layout.setSpacing(6)
        self.photoshop_path = self.QtWidgets.QLineEdit()
        self.photoshop_path.setObjectName("RizumSettingsPathInput")
        self.photoshop_path.setPlaceholderText("Photoshop.exe")
        self.photoshop_path.setFrame(False)
        self.photoshop_path.setClearButtonEnabled(False)
        self.photoshop_path.setCursorPosition(0)
        self.photoshop_path.setAlignment(self.panel.QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.photoshop_path.setSizePolicy(
            self.QtWidgets.QSizePolicy.Policy.Expanding,
            self.QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.browse_button = make_icon_button("folder.svg", "Browse executable", size=14, compact=False)
        self.browse_button.setFixedSize(26, 26)
        self.browse_button.clicked.connect(self.browse_photoshop)
        path_layout.addWidget(self.photoshop_path, 1, self.panel.QtCore.Qt.AlignmentFlag.AlignVCenter)
        path_row_layout.addWidget(self.path_field, 1)
        path_row_layout.addWidget(self.browse_button)
        body_layout.addWidget(path_row)

        about_section = _settings_section(self.QtWidgets, "About")
        self._settings_sections.append(about_section)
        body_layout.addWidget(about_section)
        version_row, version_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.row_height.design,
        )
        self._settings_rows.append(version_row)
        version_layout.addWidget(_settings_label(self.QtWidgets, "Version", "RizumSettingsItemName"))
        version_layout.addStretch(1)
        version_layout.addWidget(_settings_label(self.QtWidgets, "2.0.0", "RizumSettingsItemMeta"))
        body_layout.addWidget(version_row)

        surface_layout.addWidget(body)
        self._footer_separator = make_inset_separator(
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            thickness=1,
        )
        self._footer_separator.setObjectName("RizumSettingsFooterDivider")
        surface_layout.addWidget(self._footer_separator)

        footer = self.QtWidgets.QWidget()
        footer.setObjectName("RizumSettingsFooter")
        footer_outer = self.QtWidgets.QVBoxLayout(footer)
        footer_outer.setContentsMargins(0, 0, 0, 0)
        footer_outer.setSpacing(0)
        footer_row = self.QtWidgets.QWidget()
        footer_row.setObjectName("RizumSettingsFooterRow")
        footer_layout = self.QtWidgets.QHBoxLayout(footer_row)
        footer_layout.setContentsMargins(
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            0,
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            0,
        )
        footer_layout.setSpacing(PAINTER_SETTINGS_LAYOUT.footer_button_spacing)
        self.footer_hint = _settings_label(
            self.QtWidgets,
            "Changes save automatically",
            "RizumSettingsFooterHint",
        )
        footer_layout.addWidget(self.footer_hint)
        footer_layout.addStretch(1)
        self.done_button = SecondaryActionButton(
            "Done",
            PAINTER_DIALOG_STYLE["accent"],
            PAINTER_DIALOG_STYLE["accent_hover"],
            PAINTER_DIALOG_STYLE["accent_pressed"],
            PAINTER_DIALOG_STYLE["accent_text"],
            default_theme.radius_small,
        )
        self.done_button.clicked.connect(self.save)
        footer_layout.addWidget(self.done_button)
        footer_outer.addWidget(footer_row)
        surface_layout.addWidget(footer)
        self._footer = footer
        self._footer_outer = footer_outer
        self._footer_row = footer_row
        self._footer_layout = footer_layout

        self._bind_toggle_row(padding_row, self.infinite_padding)
        self._bind_toggle_row(uv_map_row, self.export_uv_map)
        self._bind_toggle_row(auto_row, self.auto_open_photoshop)
        self.infinite_padding.toggled.connect(self._sync_padding_mode)

        apply_theme(self.dialog, mode="overlay")
        self.dialog.syncSettingsUiScale()
        self.load_values()
        self.dialog.settingsUiScaleChanged.connect(self._apply_ui_scale)
        self._apply_ui_scale(self.dialog.settingsUiScale())

    def open(self):
        self.load_values()
        return self.dialog.exec()

    def _make_text_block(self, name, meta=""):
        block = _settings_text_block(self.QtWidgets, name, meta)
        block._rizum_name_label = block.findChild(
            self.QtWidgets.QLabel,
            "RizumSettingsItemName",
        )
        block._rizum_meta_label = block.findChild(
            self.QtWidgets.QLabel,
            "RizumSettingsItemMeta",
        )
        self._text_blocks.append(block)
        return block

    def _metric(self, pixels, minimum=None):
        return self.dialog.settingsMetric(pixels, minimum)

    def _text_font(self, pixel_size, weight):
        font = self.QtGui.QFont(self.dialog.font())
        font.setPixelSize(self._metric(pixel_size))
        font.setWeight(weight)
        return font

    def _bind_toggle_row(self, row, toggle):
        def press(event):
            if event.button() == self.QtCore.Qt.MouseButton.LeftButton:
                toggle.toggle()
                event.accept()
                return
            self.QtWidgets.QFrame.mousePressEvent(row, event)

        row.mousePressEvent = press

    def _current_extra_height(self):
        progress = max(
            0.0,
            min(1.0, self.dilation_reveal.getRevealProgress()),
        )
        return round(self.dilation_reveal.expandedHeight() * progress) + round(
            self._body_layout.spacing() * progress
        )

    def _sync_dialog_height(self, _progress=0.0):
        del _progress
        if self._base_height is None:
            return
        self.dialog.setFixedHeight(
            self._base_height + self._current_extra_height()
        )
        self.dialog.updateGeometry()

    def _required_width(self):
        metric = self._metric
        body_margin = PAINTER_SETTINGS_LAYOUT.body_margin_x.resolve(self.dialog)
        footer_margin = PAINTER_SETTINGS_LAYOUT.footer_margin_x.resolve(self.dialog)
        footer_need = (
            self.footer_hint.sizeHint().width()
            + self.done_button.width()
            + PAINTER_SETTINGS_LAYOUT.footer_button_spacing
            + 2 * footer_margin
        )
        bit_depth_need = (
            self.bit_depth.width()
            + PAINTER_SETTINGS_LAYOUT.row_spacing
            + self._settings_rows[2].layout().itemAt(0).widget().sizeHint().width()
            + 2 * body_margin
        )
        auto_need = (
            self.auto_texts.sizeHint().width()
            + PAINTER_SETTINGS_LAYOUT.row_spacing
            + self.auto_open_photoshop.width()
            + 2 * body_margin
        )
        uv_map_need = (
            self.uv_map_texts.sizeHint().width()
            + PAINTER_SETTINGS_LAYOUT.row_spacing
            + self.export_uv_map.width()
            + 2 * body_margin
        )
        return max(
            metric(338, 254),
            footer_need,
            bit_depth_need,
            auto_need,
            uv_map_need,
        )

    def _apply_ui_scale(self, _scale):
        metric = self._metric
        body_margin = PAINTER_SETTINGS_LAYOUT.body_margin_x.resolve(self.dialog)
        self._body_layout.setContentsMargins(
            body_margin,
            PAINTER_SETTINGS_LAYOUT.body_margin_top.resolve(self.dialog),
            body_margin,
            PAINTER_SETTINGS_LAYOUT.body_margin_bottom.resolve(self.dialog),
        )
        self._body_layout.setSpacing(
            PAINTER_SETTINGS_LAYOUT.body_spacing.resolve(self.dialog)
        )
        for label in self._settings_sections:
            label.setFixedHeight(label._rizum_layout_metric.resolve(self.dialog))
        row_padding = PAINTER_SETTINGS_LAYOUT.row_padding_y.resolve(self.dialog)
        for row in self._settings_rows:
            row.setFixedHeight(
                metric(
                    row._rizum_base_height,
                    round(row._rizum_base_height * 0.75),
                )
            )
            row.layout().setContentsMargins(0, row_padding, 0, row_padding)
            row.layout().setSpacing(PAINTER_SETTINGS_LAYOUT.row_spacing)

        name_metrics = self.QtGui.QFontMetrics(
            self._text_font(13, self.QtGui.QFont.Weight.Medium)
        )
        meta_metrics = self.QtGui.QFontMetrics(
            self._text_font(11, self.QtGui.QFont.Weight.Medium)
        )
        text_spacing = PAINTER_SETTINGS_LAYOUT.text_spacing.resolve(self.dialog)
        for block in self._text_blocks:
            block.layout().setSpacing(text_spacing)
            block._rizum_name_label.setFixedHeight(name_metrics.height())
            if block._rizum_meta_label is not None:
                block._rizum_meta_label.setFixedHeight(meta_metrics.height())
                block.setFixedHeight(
                    name_metrics.height() + text_spacing + meta_metrics.height()
                )

        self.infinite_padding.setCompactHeight(metric(20))
        self.export_uv_map.setCompactHeight(metric(20))
        self.auto_open_photoshop.setCompactHeight(metric(20))
        self.dilation_stepper.setCompactHeight(
            PAINTER_SETTINGS_LAYOUT.stepper_height.resolve(self.dialog)
        )
        control_height = PAINTER_SETTINGS_LAYOUT.control_height.resolve(self.dialog)
        self.bit_depth.setCompactHeight(control_height)
        self.bit_depth.setFitToContents(True)
        self.bit_depth.fitToContents()
        combo_margins = self.bit_depth.layout().contentsMargins()
        localized_width = max(
            self.bit_depth.width(),
            self.bit_depth._label.sizeHint().width()
            + combo_margins.left()
            + combo_margins.right()
            + self.bit_depth.layout().spacing()
            + self.bit_depth._arrow_size
            + metric(6, 5),
        )
        self.bit_depth.setFitToContents(False)
        self.bit_depth.setFixedWidth(max(metric(126, 95), localized_width))
        self.dilation_reveal.setExpandedHeight(
            PAINTER_SETTINGS_LAYOUT.detail_row_height.resolve(self.dialog)
        )
        self.dilation_reveal.setGap(self._body_layout.spacing())

        self.path_field.setFixedHeight(control_height)
        self.photoshop_path.setFixedHeight(max(15, control_height - metric(8, 6)))
        browse_size = metric(26)
        self.browse_button.setFixedSize(browse_size, browse_size)
        if hasattr(self.browse_button, "setPaintedIconSize"):
            self.browse_button.setPaintedIconSize(metric(14))
        if hasattr(self.browse_button, "setCompactTooltipScale"):
            self.browse_button.setCompactTooltipScale(
                self.dialog.settingsUiScale()
            )

        footer_margin = PAINTER_SETTINGS_LAYOUT.footer_margin_x.resolve(self.dialog)
        footer_top = PAINTER_SETTINGS_LAYOUT.footer_top.resolve(self.dialog)
        footer_gap = PAINTER_SETTINGS_LAYOUT.footer_gap.resolve(self.dialog)
        footer_bottom = PAINTER_SETTINGS_LAYOUT.footer_bottom.resolve(self.dialog)
        footer_row_height = PAINTER_SETTINGS_LAYOUT.footer_row_height.resolve(self.dialog)
        self._footer_outer.setContentsMargins(
            0,
            footer_top + footer_gap,
            0,
            footer_bottom,
        )
        self._footer_row.setFixedHeight(footer_row_height)
        self._footer.setFixedHeight(
            footer_top + footer_gap + footer_row_height + footer_bottom
        )
        self._footer_layout.setContentsMargins(
            footer_margin,
            0,
            footer_margin,
            0,
        )
        self._footer_separator.layout().setContentsMargins(
            footer_margin,
            0,
            footer_margin,
            0,
        )
        button_height = PAINTER_SETTINGS_LAYOUT.footer_button_height.resolve(self.dialog)
        self.done_button.setCompactHeight(button_height)
        self.done_button.setFixedWidth(
            max(metric(72, 54), self.done_button.sizeHint().width() + metric(8, 6))
        )
        self.dialog.setFixedWidth(self._required_width())
        self._restyle()
        self._remeasure_base_height()

    def _restyle(self):
        theme = PAINTER_DIALOG_STYLE
        self.dialog._update_surface_stylesheet()
        surface = self.dialog.settingsSurface()
        surface.setStyleSheet(
            surface.styleSheet()
            + f"""
QFrame#RizumPainterSettingsSurface {{
    background: {theme["surface"]};
}}
QWidget#RizumSettingsBody,
QWidget#RizumSettingsFooter,
QWidget#RizumSettingsFooterRow,
QWidget#RizumSettingsPaddingStack,
QWidget#RizumSettingsTexts,
QWidget#RizumSettingsFooterDivider,
QFrame#RizumSettingsRevealRow {{
    background: transparent;
    border: 0;
}}
QLabel#RizumSettingsSection {{ color: {theme["faint"]}; }}
QLabel#RizumSettingsItemName {{ color: {theme["text"]}; }}
QLabel#RizumSettingsItemMeta,
QLabel#RizumSettingsFooterHint {{ color: {theme["muted"]}; }}
QFrame#RizumSettingsRow,
QFrame#RizumSettingsRow:hover {{
    background: transparent;
    border: 0;
}}
QWidget#RizumSettingsFooterDivider QFrame#RizumInsetSeparator {{
    background: #3a3b3e;
}}
QFrame#RizumSettingsMockSelect {{
    background: transparent;
    border: 0;
}}
QLineEdit#RizumSettingsPathInput {{
    color: {theme["muted"]};
    background: transparent;
    border: 0;
    padding: 0;
    selection-background-color: {theme["control_hover"]};
    selection-color: {theme["text"]};
}}
QLineEdit#RizumSettingsPathInput:hover,
QLineEdit#RizumSettingsPathInput:focus {{
    color: {theme["text"]};
    background: transparent;
    border: 0;
}}
QPushButton[variant="icon"] {{
    background: transparent;
    border: 0;
    border-radius: {default_theme.radius_small}px;
}}
QPushButton[variant="icon"]:hover {{
    background: {theme["control_hover"]};
}}
QPushButton[variant="icon"]:pressed {{
    background: {theme["control_pressed"]};
}}
"""
        )
        self.dilation_stepper.setTheme(
            {
                "window_bg": theme["surface"],
                "text": theme["text"],
                "muted": theme["muted"],
                "control_hover": theme["control_hover"],
            }
        )
        self.browse_button.setProperty("iconColor", theme["muted"])
        self.browse_button.setProperty("iconHoverColor", theme["text"])
        self.browse_button.update()

    def _remeasure_base_height(self):
        self.dialog.setMinimumHeight(0)
        self.dialog.setMaximumHeight(16777215)
        self.dialog.layout().invalidate()
        self.dialog.settingsSurfaceLayout().invalidate()
        self.dialog.layout().activate()
        self.dialog.settingsSurfaceLayout().activate()
        measured = max(
            1,
            self.dialog.sizeHint().height() - self._current_extra_height(),
        )
        scale = self.dialog.settingsUiScale()
        if self._design_height is None:
            normalizer = scale if scale >= 1.0 else 1.0
            self._design_height = int(round(measured / normalizer))
        self._base_height = max(measured, int(round(self._design_height * scale)))
        self._sync_dialog_height()

    def load_values(self):
        settings = self.panel.user_settings
        self.photoshop_path.setText(settings.get("photoshop_path") or "")
        self.infinite_padding.setChecked(bool(settings.get("infinite_padding")))
        self.dilation_stepper.setValue(int(settings.get("dilation") or 8), emit=False)
        self.auto_open_photoshop.setChecked(bool(settings.get("auto_open_photoshop")))
        self.export_uv_map.setChecked(bool(settings.get("export_uv_map")))
        self._sync_padding_mode(animate=False)

        bit_depth = settings.get("bit_depth")
        index = self.bit_depth.findData(bit_depth)
        self.bit_depth.setCurrentIndex(index if index >= 0 else 0)

    def _sync_padding_mode(self, _enabled=None, animate=True):
        infinite = self.infinite_padding.isChecked()
        if self.padding_meta is not None:
            self.padding_meta.setText("Infinite" if infinite else "Custom")
        self.dilation_reveal.setExpanded(not infinite, animate=animate)
        self._sync_dialog_height()

    def browse_photoshop(self):
        path, _selected_filter = self.QtWidgets.QFileDialog.getOpenFileName(
            self.dialog,
            "Choose Photoshop executable",
            self.photoshop_path.text() or "",
            "Executable (*.exe);;All Files (*)",
        )
        if path:
            self.photoshop_path.setText(path)

    def save(self):
        self.panel.save_user_settings(
            {
                "photoshop_path": self.photoshop_path.text().strip(),
                "infinite_padding": self.infinite_padding.isChecked(),
                "dilation": self.dilation_stepper.value(),
                "auto_open_photoshop": self.auto_open_photoshop.isChecked(),
                "export_uv_map": self.export_uv_map.isChecked(),
                "bit_depth": self.bit_depth.currentData(),
            }
        )
        self.dialog.accept()


class ExportDialog:
    """Focused target/channel export dialog launched from the Painter dock."""

    DEFAULT_TREE_VIEWPORT_HEIGHT = 500
    MINIMUM_TREE_VIEWPORT_HEIGHT = 375

    def __init__(self, panel):
        self.panel = panel
        self.QtCore = panel.QtCore
        self.QtGui = panel.QtGui
        self.QtWidgets = panel.QtWidgets
        self.targets = []
        self.groups = []
        self._selection_memory = None
        self._updating_checks = False
        self._target_error = ""
        self._height_animation = None
        self._height_animation_token = 0

        self.dialog = PainterSettingsDialog(panel.widget)
        self.dialog.setObjectName("RizumExportDialog")
        self.dialog.setWindowTitle("Export")
        self.dialog.setModal(True)
        self.dialog.setSizePolicy(
            self.QtWidgets.QSizePolicy.Policy.Fixed,
            self.QtWidgets.QSizePolicy.Policy.Expanding,
        )
        surface_layout = self.dialog.settingsSurfaceLayout()

        self.scope_combo = make_combo_input([("Current Stack", "current"), ("All Stacks", "all")])
        self.scope_combo.setObjectName("RizumExportScopeInput")
        self.scope_combo.currentIndexChanged.connect(self._scope_changed)

        self.expand_button = make_icon_button("chevrons-down.svg", "Expand all")
        self.collapse_button = make_icon_button("chevrons-up.svg", "Collapse all")
        self.all_button = make_icon_button("circle-dot.svg", "Select all")
        self.none_button = make_icon_button("circle-slash.svg", "Select none")
        for button in (
            self.expand_button,
            self.collapse_button,
            self.all_button,
            self.none_button,
        ):
            button.setProperty("accent", True)
        self.expand_button.clicked.connect(self.tree_expand_all)
        self.collapse_button.clicked.connect(self.tree_collapse_all)
        self.all_button.clicked.connect(lambda: self.set_all_checked(True))
        self.none_button.clicked.connect(lambda: self.set_all_checked(False))

        self.icon_bar = make_compact_icon_toolbar(
            self.expand_button,
            self.collapse_button,
            None,
            self.all_button,
            self.none_button,
        )
        self.top_controls = make_compact_action_bar(
            [self.scope_combo],
            self.icon_bar,
            object_name="RizumExportTopControls",
            height=PAINTER_SETTINGS_LAYOUT.row_height.design,
            margins=(
                PAINTER_SETTINGS_LAYOUT.body_margin_x.design,
                0,
                PAINTER_SETTINGS_LAYOUT.body_margin_x.design,
                0,
            ),
            spacing=PAINTER_SETTINGS_LAYOUT.row_spacing,
        )
        surface_layout.addWidget(self.top_controls)

        self.top_separator = make_inset_separator(
            PAINTER_SETTINGS_LAYOUT.body_margin_x.design,
            thickness=1,
        )
        self.top_separator.setObjectName("RizumExportTopDivider")
        surface_layout.addWidget(self.top_separator)

        self.tree_scroll = self.QtWidgets.QScrollArea()
        self.tree_scroll.setObjectName("RizumExportTreeScroll")
        self.tree_scroll.setWidgetResizable(True)
        self.tree_scroll.setFrameShape(self.QtWidgets.QFrame.Shape.NoFrame)
        self.tree_scroll.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.tree_scroll.setVerticalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.tree_scroll.viewport().setAutoFillBackground(False)
        internal_scrollbar = self.tree_scroll.verticalScrollBar()
        internal_scrollbar.setObjectName("RizumExportInternalScrollbar")
        internal_scrollbar.setStyleSheet(
            "QScrollBar#RizumExportInternalScrollbar {"
            " min-width: 0; max-width: 0; width: 0;"
            " background: transparent; border: 0; }"
        )
        internal_scrollbar.setFixedWidth(0)
        internal_scrollbar.valueChanged.connect(
            self._refresh_tree_hover
        )

        # Painter can reclaim a native scrollbar lane even under AlwaysOn.
        # Keep scrolling internal, but render it through a fixed-width proxy.
        self.tree_scrollbar = self.QtWidgets.QScrollBar(
            self.QtCore.Qt.Orientation.Vertical
        )
        self.tree_scrollbar.setObjectName("RizumExportTreeScrollbar")
        self.tree_scrollbar.setFocusPolicy(
            self.QtCore.Qt.FocusPolicy.NoFocus
        )
        self.tree_scrollbar.valueChanged.connect(internal_scrollbar.setValue)
        internal_scrollbar.valueChanged.connect(self.tree_scrollbar.setValue)
        internal_scrollbar.rangeChanged.connect(self._sync_scrollbar_range)

        self.tree_container = self.QtWidgets.QWidget()
        self.tree_container.setObjectName("RizumExportTreeContainer")
        self.tree_container.setSizePolicy(
            self.QtWidgets.QSizePolicy.Policy.Expanding,
            self.QtWidgets.QSizePolicy.Policy.Expanding,
        )
        tree_container_layout = self.QtWidgets.QHBoxLayout(self.tree_container)
        tree_container_layout.setContentsMargins(0, 0, 0, 0)
        tree_container_layout.setSpacing(0)
        tree_container_layout.addWidget(self.tree_scroll, 1)
        tree_container_layout.addWidget(self.tree_scrollbar)

        self.tree = self.QtWidgets.QFrame()
        self.tree.setObjectName("RizumExportTree")
        self.tree.setMinimumWidth(0)
        self.tree.setSizePolicy(
            self.QtWidgets.QSizePolicy.Policy.Expanding,
            self.QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.tree_layout = self.QtWidgets.QVBoxLayout(self.tree)
        self.tree_layout.setContentsMargins(12, 8, 12, 8)
        self.tree_layout.setSpacing(PAINTER_SETTINGS_LAYOUT.body_spacing.design)
        self.status = self.QtWidgets.QLabel("")
        self.status.setObjectName("RizumExportEmptyState")
        self.status.setWordWrap(True)
        self.status.setAlignment(self.QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status.hide()
        self.tree_layout.addWidget(self.status)
        self.tree_layout.addStretch(1)
        self.tree_scroll.setWidget(self.tree)
        self.tree_scroll.setSizePolicy(
            self.QtWidgets.QSizePolicy.Policy.Expanding,
            self.QtWidgets.QSizePolicy.Policy.Expanding,
        )
        surface_layout.addWidget(self.tree_container, 1)

        self.export_pngs = self.QtWidgets.QCheckBox("Export PNGs")
        self.export_pngs.setChecked(True)
        self.export_pngs.setVisible(False)

        self.footer_separator = make_inset_separator(
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            thickness=1,
        )
        self.footer_separator.setObjectName("RizumExportFooterDivider")
        surface_layout.addWidget(self.footer_separator)

        self.footer = self.QtWidgets.QWidget()
        self.footer.setObjectName("RizumExportFooter")
        self.footer_outer = self.QtWidgets.QVBoxLayout(self.footer)
        self.footer_outer.setContentsMargins(0, 0, 0, 0)
        self.footer_outer.setSpacing(0)
        self.footer_row = self.QtWidgets.QWidget()
        self.footer_row.setObjectName("RizumExportFooterRow")
        self.footer_layout = self.QtWidgets.QHBoxLayout(self.footer_row)
        self.footer_layout.setContentsMargins(
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            0,
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            0,
        )
        self.footer_layout.setSpacing(PAINTER_SETTINGS_LAYOUT.footer_button_spacing)
        theme = PAINTER_DIALOG_STYLE
        self.cancel_button = SecondaryActionButton(
            "Cancel",
            theme["control"],
            theme["control_hover"],
            theme["control_pressed"],
            theme["text"],
            default_theme.radius_small,
        )
        self.cancel_button.setObjectName("RizumExportCancel")
        self.run_button = AnimatedSaveButton("Export")
        self.run_button.setObjectName("RizumExportConfirm")
        self.cancel_button.clicked.connect(self.dialog.reject)
        self.run_button.clicked.connect(self.export_checked)
        self.footer_layout.addWidget(self.cancel_button)
        self.footer_layout.addStretch(1)
        self.footer_layout.addWidget(self.run_button)
        self.footer_outer.addWidget(self.footer_row)
        surface_layout.addWidget(self.footer)

        apply_theme(self.dialog, mode="overlay")
        self.dialog.syncSettingsUiScale()
        self.dialog.settingsUiScaleChanged.connect(self._apply_ui_scale)
        self._apply_ui_scale(self.dialog.settingsUiScale())

    def open(self):
        self.refresh_targets()
        self._position_for_default_expansion()
        # Windows recenters a parented modal as exec() begins, so repeat the
        # placement after the native window has completed its first show.
        self.QtCore.QTimer.singleShot(
            0,
            self._position_for_default_expansion,
        )
        return self.dialog.exec()

    def tree_expand_all(self):
        for group in self.groups:
            group["widget"].setExpanded(True)

    def tree_collapse_all(self):
        for group in self.groups:
            group["widget"].setExpanded(False)

    def _metric(self, pixels, minimum=None):
        return self.dialog.settingsMetric(pixels, minimum)

    def _selection_counter(self, selected, total):
        theme = PAINTER_DIALOG_STYLE
        return (
            f'<span style="color:{theme["text"]};">{selected}</span>'
            f'<span style="color:{theme["faint"]};"> / {total}</span>'
        )

    @staticmethod
    def _selection_tooltip(selected, total):
        return f"{selected} of {total} channels selected"

    def _footer_button_width(self, button, minimum=56, maximum=112):
        scale = self.dialog.settingsUiScale()
        width = button.sizeHint().width() + self._metric(16, 12)
        return max(
            self._metric(minimum),
            min(int(round(maximum * scale)), width),
        )

    def _required_width(self):
        margin = PAINTER_SETTINGS_LAYOUT.body_margin_x.resolve(self.dialog)
        toolbar_width = compact_action_bar_width(
            [self.scope_combo],
            self.icon_bar,
            minimum=PAINTER_SETTINGS_LAYOUT.dialog_width.resolve(self.dialog),
            horizontal_margins=margin * 2,
            spacing=PAINTER_SETTINGS_LAYOUT.row_spacing,
            spacing_budget=PAINTER_SETTINGS_LAYOUT.row_spacing,
        )
        footer_width = (
            margin * 2
            + self.cancel_button.width()
            + self.run_button.width()
            + PAINTER_SETTINGS_LAYOUT.footer_button_spacing
        )
        return max(
            PAINTER_SETTINGS_LAYOUT.dialog_width.resolve(self.dialog),
            toolbar_width,
            footer_width,
        )

    def _expanded_tree_height(self):
        margins = self.tree_layout.contentsMargins()
        if not self.groups:
            return margins.top() + self._metric(72, 54) + margins.bottom()

        height = margins.top() + margins.bottom()
        for index, group in enumerate(self.groups):
            if index:
                height += self.tree_layout.spacing()
            height += group["widget"].height()
        return height

    def _first_group_prefix_height(self, group, maximum):
        widget = group["widget"]
        group_margins = widget.layout().contentsMargins()
        base = (
            group_margins.top()
            + widget._rizum_header.height()
            + group_margins.bottom()
        )
        if not widget.isExpanded() or base >= maximum:
            return min(base, maximum)

        height = base
        content_layout = widget._rizum_content_layout
        for index, child in enumerate(group["children"]):
            row_height = child["row"].height()
            addition = row_height + (content_layout.spacing() if index else 0)
            if height + addition > maximum:
                break
            height += addition
        return height

    def _quantized_tree_height(self, content_height, maximum):
        if content_height <= maximum or not self.groups:
            return content_height

        margins = self.tree_layout.contentsMargins()
        height = margins.top()
        complete_groups = 0
        truncated = False
        for group in self.groups:
            spacing = self.tree_layout.spacing() if complete_groups else 0
            candidate = (
                height
                + spacing
                + group["widget"].height()
                + margins.bottom()
            )
            if candidate > maximum:
                truncated = True
                if not complete_groups:
                    available = max(
                        0,
                        maximum - height - spacing - margins.bottom(),
                    )
                    height += spacing + self._first_group_prefix_height(
                        group,
                        available,
                    )
                break
            height += spacing + group["widget"].height()
            complete_groups += 1
        if truncated:
            # The tree's bottom margin exists only after its final group. When
            # more groups follow, ending on that hypothetical margin exposes
            # the first pixels of the next header inside the viewport.
            return max(1, height + self.tree_layout.spacing())
        return max(1, height + margins.bottom())

    def _sync_toolbar_gutter(self):
        margin = PAINTER_SETTINGS_LAYOUT.body_margin_x.resolve(self.dialog)
        gutter = self._metric(10, 8)
        self.top_controls.layout().setContentsMargins(
            margin,
            0,
            margin + max(0, gutter),
            0,
        )

    def _refresh_tree_hover(self, *_args):
        for group in self.groups:
            for child in group["children"]:
                hover_filter = getattr(
                    child["row"],
                    "_rizum_hover_filter",
                    None,
                )
                if hover_filter is not None:
                    hover_filter.refresh_hovered()

    def _sync_scrollbar_range(self, minimum, maximum):
        internal = self.tree_scroll.verticalScrollBar()
        self.tree_scrollbar.setRange(minimum, maximum)
        self.tree_scrollbar.setPageStep(internal.pageStep())
        self.tree_scrollbar.setSingleStep(internal.singleStep())
        self.tree_scrollbar.setValue(internal.value())
        self._set_tree_scrollable(maximum > minimum)

    def _set_tree_scrollable(self, scrolling):
        scrolling = bool(scrolling)
        if self.tree_scrollbar.property("scrollable") == scrolling:
            return
        self.tree_scrollbar.setProperty("scrollable", scrolling)
        self.tree_scrollbar.style().unpolish(self.tree_scrollbar)
        self.tree_scrollbar.style().polish(self.tree_scrollbar)
        self.tree_scrollbar.update()

    def _sync_tree_content_height(self):
        self.tree_layout.activate()
        content_height = self._expanded_tree_height()
        self.tree.setFixedHeight(content_height)
        viewport_height = max(1, self.tree_scroll.viewport().height())
        scrolling = content_height > viewport_height
        self._set_tree_scrollable(scrolling)
        if not scrolling:
            self.tree_scroll.verticalScrollBar().setValue(0)

    def _dialog_height_for_viewport(self, viewport_height):
        return (
            self.top_controls.height()
            + self.top_separator.height()
            + int(round(viewport_height))
            + self.footer_separator.height()
            + self.footer.height()
        )

    def _position_for_default_expansion(self):
        parent_window = self.dialog.parentWidget()
        if parent_window is not None:
            parent_window = parent_window.window()
        parent_geometry = (
            parent_window.frameGeometry()
            if parent_window is not None and parent_window.isVisible()
            else None
        )
        screen = None
        if parent_geometry is not None:
            screen = self.QtGui.QGuiApplication.screenAt(
                parent_geometry.center()
            )
        screen = screen or self.dialog.screen()
        screen = screen or self.QtGui.QGuiApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        anchor = parent_geometry or available
        frame_width = max(1, self.dialog.frameGeometry().width())
        reserve_height = min(
            available.height(),
            self._dialog_height_for_viewport(
                self._metric(
                    self.DEFAULT_TREE_VIEWPORT_HEIGHT,
                    self.MINIMUM_TREE_VIEWPORT_HEIGHT,
                )
            ),
        )
        x = anchor.center().x() - frame_width // 2
        x = max(
            available.left(),
            min(x, available.right() - frame_width + 1),
        )
        y = available.top() + max(
            0,
            (available.height() - reserve_height) // 2,
        )
        self.dialog.move(x, y)

    def _set_viewport_height(self, viewport_height):
        viewport_height = max(1, int(round(viewport_height)))
        self.dialog.resize(
            self.dialog.width(),
            self._dialog_height_for_viewport(viewport_height),
        )
        self.dialog.updateGeometry()

    def _stop_height_animation(self):
        animation = self._height_animation
        self._height_animation = None
        if animation is not None:
            self._height_animation_token += 1
            animation.stop()
            animation.deleteLater()

    def _animate_viewport_height(self, target_height):
        start_height = max(1, self.tree_scroll.height())
        target_height = max(1, int(round(target_height)))
        threshold = self._metric(32, 24)
        if (
            not self.dialog.isVisible()
            or abs(target_height - start_height) < threshold
        ):
            self._stop_height_animation()
            self._set_viewport_height(target_height)
            return

        self._stop_height_animation()
        self._height_animation_token += 1
        token = self._height_animation_token
        animation = self.QtCore.QVariantAnimation(self.dialog)
        animation.setDuration(165)
        animation.setStartValue(start_height)
        animation.setEndValue(target_height)
        animation.setEasingCurve(
            self.QtCore.QEasingCurve.Type.OutCubic
        )
        animation.valueChanged.connect(self._set_viewport_height)

        def finish():
            if token != self._height_animation_token:
                return
            self._set_viewport_height(target_height)
            self._height_animation = None
            animation.deleteLater()

        animation.finished.connect(finish)
        self._height_animation = animation
        animation.start()

    def _sync_tree_height(self, animate=False, reset_scroll=False):
        self.tree_layout.activate()
        content_height = self._expanded_tree_height()
        viewport_height = self._quantized_tree_height(
            content_height,
            self._metric(
                self.DEFAULT_TREE_VIEWPORT_HEIGHT,
                self.MINIMUM_TREE_VIEWPORT_HEIGHT,
            ),
        )
        self.tree.setFixedHeight(content_height)
        scrollbar = self.tree_scroll.verticalScrollBar()
        scrolling = content_height > viewport_height
        self._set_tree_scrollable(scrolling)
        if reset_scroll:
            scrollbar.setValue(0)
        self._sync_toolbar_gutter()
        if animate:
            self._animate_viewport_height(viewport_height)
        else:
            self._stop_height_animation()
            self._set_viewport_height(viewport_height)
        self.QtCore.QTimer.singleShot(0, self._refresh_tree_hover)

    def _apply_ui_scale(
        self,
        _scale,
        animate_height=False,
        reset_scroll=False,
    ):
        margin = PAINTER_SETTINGS_LAYOUT.body_margin_x.resolve(self.dialog)
        self.top_controls.setFixedHeight(
            PAINTER_SETTINGS_LAYOUT.row_height.resolve(self.dialog)
        )
        self.top_controls.layout().setContentsMargins(margin, 0, margin, 0)
        self.top_controls.layout().setSpacing(PAINTER_SETTINGS_LAYOUT.row_spacing)
        self.scope_combo.setCompactHeight(
            PAINTER_SETTINGS_LAYOUT.control_height.resolve(self.dialog)
        )
        self.scope_combo.fitToContents()

        icon_frame = self._metric(22, 17)
        icon_size = self._metric(16, 12)
        for button in (
            self.expand_button,
            self.collapse_button,
            self.all_button,
            self.none_button,
        ):
            button.setFixedSize(icon_frame, icon_frame)
            button.setPaintedIconSize(icon_size)
            if hasattr(button, "setCompactTooltipScale"):
                button.setCompactTooltipScale(self.dialog.settingsUiScale())
        for separator in self.icon_bar.findChildren(self.QtWidgets.QFrame):
            if separator.width() == 1:
                separator.setFixedHeight(self._metric(14, 11))

        tree_margin_x = self._metric(12, 9)
        tree_margin_y = self._metric(8, 6)
        self.tree_layout.setContentsMargins(
            tree_margin_x,
            tree_margin_y,
            tree_margin_x,
            tree_margin_y,
        )
        self.tree_layout.setSpacing(
            PAINTER_SETTINGS_LAYOUT.body_spacing.resolve(self.dialog)
        )
        checkbox_size = self._metric(14, 11)
        group_height = self._metric(36, 27)
        child_height = self._metric(32, 24)
        for group in self.groups:
            for checkbox in (
                group["parent"],
                *(child["checkbox"] for child in group["children"]),
            ):
                checkbox.setSize(checkbox_size)
            group["subtitle"].setFixedWidth(self._metric(42, 32))
            group["subtitle"].setCompactTooltipScale(
                self.dialog.settingsUiScale()
            )
            group["widget"].setCompactHeight(group_height)
            for child in group["children"]:
                child["row"].setRightInset(
                    self._metric(4, 3),
                    self._metric(4, 3),
                )
                update_export_tree_item(
                    child["row"],
                    minimum_height=child_height,
                )
            group["widget"].refreshLayout()

        footer_margin = PAINTER_SETTINGS_LAYOUT.footer_margin_x.resolve(self.dialog)
        footer_top = PAINTER_SETTINGS_LAYOUT.footer_top.resolve(self.dialog)
        footer_gap = PAINTER_SETTINGS_LAYOUT.footer_gap.resolve(self.dialog)
        footer_bottom = PAINTER_SETTINGS_LAYOUT.footer_bottom.resolve(self.dialog)
        footer_row_height = PAINTER_SETTINGS_LAYOUT.footer_row_height.resolve(self.dialog)
        self.footer_outer.setContentsMargins(
            0,
            footer_top + footer_gap,
            0,
            footer_bottom,
        )
        self.footer_row.setFixedHeight(footer_row_height)
        self.footer.setFixedHeight(
            footer_top + footer_gap + footer_row_height + footer_bottom
        )
        self.footer_layout.setContentsMargins(
            footer_margin,
            0,
            footer_margin,
            0,
        )
        self.footer_separator.layout().setContentsMargins(
            footer_margin,
            0,
            footer_margin,
            0,
        )
        self.top_separator.layout().setContentsMargins(margin, 0, margin, 0)
        button_height = PAINTER_SETTINGS_LAYOUT.footer_button_height.resolve(
            self.dialog
        )
        for button in (self.cancel_button, self.run_button):
            button.setCompactHeight(button_height)
            button.setFixedWidth(self._footer_button_width(button))

        self._restyle()
        # Painter's host stylesheet applies a 24 px icon-button minimum during
        # polish, so restore the shared compact frame after the local style lands.
        for button in (
            self.expand_button,
            self.collapse_button,
            self.all_button,
            self.none_button,
        ):
            button.setFixedSize(icon_frame, icon_frame)
        self.icon_bar.layout().invalidate()
        self.icon_bar.layout().activate()
        scrollbar_gutter = self._metric(10, 8)
        self.tree_scroll.verticalScrollBar().setFixedWidth(0)
        self.tree_scrollbar.setFixedWidth(scrollbar_gutter)
        minimum_viewport_height = self._metric(72, 54)
        self.tree_container.setMinimumHeight(minimum_viewport_height)
        self.tree_scroll.setMinimumHeight(minimum_viewport_height)
        self.dialog.setMinimumHeight(
            self._dialog_height_for_viewport(minimum_viewport_height)
        )
        self.dialog.setMaximumHeight(16777215)
        self.dialog.setFixedWidth(self._required_width())
        self._sync_tree_height(
            animate=animate_height,
            reset_scroll=reset_scroll,
        )

    def _restyle(self):
        theme = PAINTER_DIALOG_STYLE
        self.dialog._update_surface_stylesheet()
        item_px = self._metric(13)
        meta_px = self._metric(11)
        surface = self.dialog.settingsSurface()
        surface.setStyleSheet(
            surface.styleSheet()
            + f"""
QFrame#RizumPainterSettingsSurface {{
    background: {theme["surface"]};
}}
QWidget#RizumExportTopControls,
QWidget#RizumExportTreeContainer,
QScrollArea#RizumExportTreeScroll,
QScrollArea#RizumExportTreeScroll > QWidget > QWidget,
QFrame#RizumExportTree,
QWidget#RizumExportFooter,
QWidget#RizumExportFooterRow,
QWidget#RizumExportTopDivider,
QWidget#RizumExportFooterDivider,
QFrame#RizumCollapsibleHeader,
QFrame#RizumCollapsibleContent,
QWidget#RizumCollapsibleContentInner,
QFrame#RizumExportTreeItemHost {{
    background: transparent;
    border: 0;
}}
QScrollBar#RizumExportTreeScrollbar {{
    background: transparent;
    border: 0;
    margin: 0;
    width: {self._metric(10, 8)}px;
}}
QScrollBar#RizumExportTreeScrollbar::handle:vertical {{
    background: #515151;
    border: 0;
    border-radius: {max(3, self._metric(4, 3))}px;
    min-height: {self._metric(28, 21)}px;
    margin: {self._metric(2, 1)}px;
}}
QScrollBar#RizumExportTreeScrollbar::handle:vertical:hover {{
    background: #686868;
}}
QScrollBar#RizumExportTreeScrollbar::handle:vertical:pressed {{
    background: #777777;
}}
QScrollBar#RizumExportTreeScrollbar[scrollable="false"]::handle:vertical {{
    background: transparent;
}}
QScrollBar#RizumExportTreeScrollbar::add-line:vertical,
QScrollBar#RizumExportTreeScrollbar::sub-line:vertical {{
    background: transparent;
    border: 0;
    height: 0;
}}
QScrollBar#RizumExportTreeScrollbar::add-page:vertical,
QScrollBar#RizumExportTreeScrollbar::sub-page:vertical {{
    background: transparent;
}}
QWidget#RizumExportTopDivider QFrame#RizumInsetSeparator,
QWidget#RizumExportFooterDivider QFrame#RizumInsetSeparator {{
    background: #3a3b3e;
}}
QFrame#RizumExportScopeInput {{
    background: transparent;
    border: 0;
    border-radius: {default_theme.radius_small}px;
}}
QFrame#RizumExportScopeInput:focus {{
    background: transparent;
}}
QFrame#RizumExportScopeInput:hover {{
    background: {default_theme.action_hover};
}}
QFrame#RizumCollapsibleGroup {{
    background: transparent;
    border: 0;
    border-radius: {default_theme.radius_small}px;
}}
QFrame#RizumCollapsibleGroup:hover {{
    background: {theme["control_pressed"]};
    border: 0;
}}
QFrame#RizumExportTreeItem {{
    background: transparent;
    border: 0;
    border-radius: {default_theme.radius_small}px;
}}
QFrame#RizumExportTreeItem[hovered="true"][child="true"] {{
    background: {default_theme.action_hover};
}}
QFrame#RizumExportTreeItem[pressed="true"][child="true"] {{
    background: {default_theme.action_pressed};
}}
QLabel#RizumExportItemName,
QLabel#RizumCollapsibleTitle {{
    color: {theme["text"]};
    font-size: {item_px}px;
    font-weight: 500;
    background: transparent;
    border: 0;
}}
QLabel#RizumExportMeta,
QLabel#RizumCollapsibleSubtitle,
QLabel#RizumExportEmptyState {{
    color: {theme["muted"]};
    font-size: {meta_px}px;
    font-weight: 500;
    background: transparent;
    border: 0;
}}
QLabel#RizumSvgLabel,
QLabel#RizumSvgLabel:hover {{
    background: transparent;
    border: 0;
}}
"""
        )
        for button in (
            self.expand_button,
            self.collapse_button,
            self.all_button,
            self.none_button,
        ):
            button.setProperty("iconColor", theme["muted"])
            button.setProperty("iconAccentColor", theme["muted"])
            button.setProperty("iconHoverColor", theme["text"])
            button.update()

    def refresh_targets(self):
        self._target_error = ""
        if not self.panel._project_is_open():
            self.targets = []
            self.refresh_tree()
            _show_modal_message(
                self.QtWidgets,
                self.dialog,
                "Export",
                "Open a Painter project to export.",
            )
            return
        if not self.panel._project_is_ready():
            self.targets = []
            self.refresh_tree()
            _show_modal_message(
                self.QtWidgets,
                self.dialog,
                "Export",
                "Painter project is still loading or not editable.",
            )
            return

        self._selection_memory = ExportSelectionMemory(
            self.QtCore,
            SETTINGS_ORG,
            SETTINGS_APP,
            current_project_identity(),
        )
        remembered_scope = self._selection_memory.scope()
        remembered_index = self.scope_combo.findData(remembered_scope)
        if remembered_index >= 0:
            previous_signal_state = self.scope_combo.blockSignals(True)
            self.scope_combo.setCurrentIndex(remembered_index)
            self.scope_combo.blockSignals(previous_signal_state)

        try:
            self.targets = list_export_targets(settings=self.panel._base_export_settings())
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            self.targets = []
            self._target_error = (
                f"Could not list export targets: {type(exc).__name__}: {exc}"
            )
        self.refresh_tree()

    def _clear_groups(self):
        for group in self.groups:
            self.tree_layout.removeWidget(group["widget"])
            group["widget"].deleteLater()
        self.groups.clear()

    def _show_tree_message(self, message):
        self.status.setText(message)
        self.status.setVisible(bool(message))

    def _scope_changed(self, *_args):
        if self._selection_memory is not None:
            self._selection_memory.remember_scope(
                self.scope_combo.currentData()
            )
            self._selection_memory.save()
        self.refresh_tree(
            animate_height=self.dialog.isVisible(),
            reset_scroll=True,
        )

    def refresh_tree(
        self,
        *_args,
        animate_height=False,
        reset_scroll=False,
    ):
        self._updating_checks = True
        self._clear_groups()

        visible_targets = [
            target
            for target in self._visible_targets()
            if target.get("channels")
        ]
        if not visible_targets:
            if self._target_error:
                message = self._target_error
            elif (
                self.scope_combo.currentText() == "Current Stack"
                and self._active_target_key() is None
            ):
                message = "Select a stack in Painter to export."
            elif self.scope_combo.currentText() == "Current Stack":
                message = "No exportable channels found for Current Stack."
            else:
                message = "No exportable channels were found."
            self._show_tree_message(message)
            self.run_button.setDirty(
                False,
                animate=self.dialog.isVisible(),
            )
            self._updating_checks = False
            self._apply_ui_scale(
                self.dialog.settingsUiScale(),
                animate_height=animate_height,
                reset_scroll=reset_scroll,
            )
            return

        select_current = self.scope_combo.currentText() == "Current Stack"
        self._show_tree_message("")

        for target in visible_targets:
            self._add_group(target, checked=select_current)

        self._updating_checks = False
        self._refresh_selection_state()
        self._apply_ui_scale(
            self.dialog.settingsUiScale(),
            animate_height=animate_height,
            reset_scroll=reset_scroll,
        )

    def _add_group(self, target, checked):
        parent_checkbox = make_mock_checkbox(False)
        group = {
            "target": target,
            "parent": parent_checkbox,
            "children": [],
        }
        labels = target.get("channel_labels", {})
        child_rows = []
        selection_key = target_selection_key(target)

        for channel in target.get("channels", []):
            remembered = checked
            if self._selection_memory is not None:
                remembered = self._selection_memory.checked(
                    selection_key,
                    channel,
                    checked,
                )
            checkbox = make_mock_checkbox(remembered)
            row = make_export_tree_item(
                labels.get(channel) or channel,
                checkbox,
                child=True,
            )
            child = {
                "channel": channel,
                "checkbox": checkbox,
                "row": row,
            }
            group["children"].append(child)
            child_rows.append(row)

            def row_press(event, cb=checkbox, owner=group):
                if event.button() == self.QtCore.Qt.MouseButton.LeftButton:
                    cb.toggle()
                    self._update_group(owner)
                    event.accept()

            row.mousePressEvent = row_press
            old_checkbox_press = checkbox.mousePressEvent

            def checkbox_press(
                event,
                owner=group,
                old=old_checkbox_press,
            ):
                old(event)
                if event.button() == self.QtCore.Qt.MouseButton.LeftButton:
                    self._update_group(owner)

            checkbox.mousePressEvent = checkbox_press

        old_parent_press = parent_checkbox.mousePressEvent

        def parent_press(event, owner=group, old=old_parent_press):
            old(event)
            if event.button() != self.QtCore.Qt.MouseButton.LeftButton:
                return
            next_checked = owner["parent"].isChecked()
            for child in owner["children"]:
                child["checkbox"].setChecked(next_checked)
            self._update_group(owner)

        parent_checkbox.mousePressEvent = parent_press
        total = len(group["children"])
        selected = sum(
            1
            for child in group["children"]
            if child["checkbox"].isChecked()
        )
        widget = make_collapsible_group(
            self._target_label(target),
            self._selection_counter(selected, total),
            children=child_rows,
            trailing_widget=parent_checkbox,
            expanded=True,
        )
        group["widget"] = widget
        subtitle = widget.findChild(
            self.QtWidgets.QLabel,
            "RizumCollapsibleSubtitle",
        )
        subtitle.setTextFormat(self.QtCore.Qt.TextFormat.RichText)
        tooltip = self._selection_tooltip(selected, total)
        install_compact_tooltip(subtitle, tooltip)
        subtitle.setAccessibleName(tooltip)
        group["subtitle"] = subtitle
        self.tree_layout.insertWidget(self.tree_layout.count() - 1, widget)
        self.groups.append(group)
        # Follow every animation frame so a collapsed tree cannot retain the
        # expanded content height as a blank scroll range.
        content = widget._rizum_content
        sync_group_height = content._height_changed

        def sync_export_tree_height(value, sync_group=sync_group_height):
            sync_group(value)
            self._sync_tree_content_height()

        content._height_changed = sync_export_tree_height
        self._update_group(group, refresh_total=False)

    def _update_group(self, group, refresh_total=True):
        selected = sum(
            1
            for child in group["children"]
            if child["checkbox"].isChecked()
        )
        total = len(group["children"])
        if not selected:
            group["parent"].setChecked(False)
        elif selected == total:
            group["parent"].setChecked(True)
        else:
            group["parent"].setIndeterminate(True)

        tooltip = self._selection_tooltip(selected, total)
        group["widget"].refreshLayout(
            subtitle_text=self._selection_counter(selected, total)
        )
        group["subtitle"].setCompactTooltipText(tooltip)
        group["subtitle"].setAccessibleName(tooltip)
        if refresh_total and not self._updating_checks:
            self._refresh_selection_state()

    def _visible_targets(self):
        if self.scope_combo.currentText() == "Current Stack":
            active_key = self._active_target_key()
            if active_key is None:
                return []
            texture_set_name, stack_name = active_key
            matches = [
                target
                for target in self.targets
                if target.get("texture_set") == texture_set_name
                and (target.get("stack") or "") == (stack_name or "")
            ]
            return matches
        return self.targets

    def _active_target_key(self):
        try:
            return self.panel.active_target_key()
        except Exception:
            return None

    def _target_label(self, target):
        texture_set = target.get("texture_set") or "(unknown texture set)"
        stack = target.get("stack") or "(default)"
        return stack if stack != "(default)" else texture_set

    def set_all_checked(self, checked):
        self._updating_checks = True
        for group in self.groups:
            for child in group["children"]:
                child["checkbox"].setChecked(checked)
            self._update_group(group, refresh_total=False)
        self._updating_checks = False
        self._refresh_selection_state()

    def _refresh_selection_state(self):
        if not self._updating_checks:
            self._remember_visible_selections()
        selected_total = sum(
            1
            for group in self.groups
            for child in group["children"]
            if child["checkbox"].isChecked()
        )
        self.run_button.setDirty(
            selected_total > 0,
            animate=self.dialog.isVisible(),
        )

    def _remember_visible_selections(self):
        if self._selection_memory is None:
            return
        # Keep choices project-scoped because production files commonly reuse
        # texture-set names while requiring different export channel subsets.
        for group in self.groups:
            self._selection_memory.remember_target(
                target_selection_key(group["target"]),
                {
                    child["channel"]: child["checkbox"].isChecked()
                    for child in group["children"]
                },
            )
        self._selection_memory.save()

    def selected_exports(self):
        selections = []
        for group in self.groups:
            channels = [
                child["channel"]
                for child in group["children"]
                if child["checkbox"].isChecked()
            ]
            if channels:
                selections.append((group["target"], channels))
        return selections

    def export_checked(self):
        selections = self.selected_exports()
        if not selections:
            self.run_button.setDirty(
                False,
                animate=self.dialog.isVisible(),
            )
            return

        result = self.panel._run_export_selections(
            "export dialog selection",
            selections,
            export_pngs=self.export_pngs.isChecked(),
        )
        if not result["ok"]:
            _show_modal_message(
                self.QtWidgets,
                self.dialog,
                "Export failed",
                result["message"],
            )
            return

        settings = self.panel.user_settings
        if settings.get("auto_open_photoshop"):
            try:
                launcher_path = write_photoshop_launcher(result["export_list"])
            except Exception as exc:  # noqa: BLE001 - surface launch preparation errors.
                _show_modal_message(
                    self.QtWidgets,
                    self.dialog,
                    "Photoshop",
                    f"Could not prepare the Photoshop build script: {exc}",
                )
                return
            launched, message = self.panel.launch_photoshop(launcher_path)
            if not launched:
                _show_modal_message(self.QtWidgets, self.dialog, "Photoshop", message)
                return
            self.dialog.accept()
            return

        self._show_export_handoff(result)
        self.dialog.accept()

    def _show_export_handoff(self, result):
        dialog = self.QtWidgets.QDialog(self.dialog)
        dialog.setWindowTitle("Export complete")
        dialog.setModal(True)
        dialog.setMinimumWidth(340)
        apply_theme(dialog, mode="overlay")

        layout = self.QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        title = self.QtWidgets.QLabel("Export complete")
        title.setObjectName("RizumDialogTitle")
        layout.addWidget(title)
        layout.addWidget(make_inset_separator(0, thickness=1))

        summary = self.QtWidgets.QLabel(
            f"Exported {result['count']} build request(s). Continue in Photoshop when ready."
        )
        summary.setObjectName("RizumDimLabel")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        path = self.QtWidgets.QLineEdit(str(result["output_dir"]))
        path.setObjectName("RizumPathInput")
        path.setReadOnly(True)
        path.setFrame(False)
        path.setCursorPosition(0)
        layout.addWidget(path)

        footer = self.QtWidgets.QHBoxLayout()
        footer.setContentsMargins(0, 6, 0, 0)
        open_button = ActionButton.create("Open Folder", "dialog-secondary")
        copy_button = ActionButton.create("Copy List", "dialog-secondary")
        done_button = ActionButton.create("Done", "dialog-primary")
        open_button.clicked.connect(self.panel.open_output_folder)
        copy_button.clicked.connect(self.panel.copy_last_export_list_path)
        done_button.clicked.connect(dialog.accept)
        footer.addWidget(open_button)
        footer.addWidget(copy_button)
        footer.addStretch(1)
        footer.addWidget(done_button)
        layout.addLayout(footer)
        for button, minimum, maximum in (
            (open_button, 86, 116),
            (copy_button, 78, 106),
            (done_button, 68, 96),
        ):
            set_compact_footer_button_width(
                button,
                compact_footer_button_width(button, minimum=minimum, maximum=maximum),
            )
        dialog.setStyleSheet(dialog.styleSheet() + BRIDGE_DIALOG_STYLESHEET)
        dialog.exec()

class SmokeTestPanel:
    """Painter dock panel for the PT Bridge workflow."""

    def __init__(self):
        from PySide6 import QtCore, QtGui, QtWidgets

        self.QtCore = QtCore
        self.QtGui = QtGui
        self.QtWidgets = QtWidgets
        self._running = False
        self._closing = False
        self.targets = []
        self.last_paths = []
        self.last_export_list_path = None
        self.last_output_dir = None
        self.user_settings = self._load_user_settings()
        self.widget = QtWidgets.QWidget()
        self.widget.setObjectName("RizumPtToPsSmokeTestPanel")
        self.widget.setWindowTitle("PT Bridge")
        self.widget.setMinimumSize(BRIDGE_DOCK_MIN_WIDTH, BRIDGE_DOCK_TOOLBAR_HEIGHT)
        self.widget.resize(BRIDGE_DOCK_DEFAULT_WIDTH, BRIDGE_DOCK_TOOLBAR_HEIGHT)
        apply_theme(self.widget, mode="overlay")
        _apply_bridge_dock_surface(self.widget)
        self.widget.setStyleSheet(self.widget.styleSheet() + BRIDGE_DIALOG_STYLESHEET)

        outer_layout = QtWidgets.QVBoxLayout(self.widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.export_pngs = QtWidgets.QCheckBox("Export PNGs")
        self.export_pngs.setChecked(True)

        self.refresh_targets_button = QtWidgets.QPushButton("Refresh Targets")
        self.refresh_targets_button.clicked.connect(self.refresh_targets)

        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.setEnabled(False)
        self.target_combo.currentIndexChanged.connect(self.refresh_channel_combo)

        self.channel_combo = QtWidgets.QComboBox()
        self.channel_combo.setEnabled(False)

        self.run_selected_button = QtWidgets.QPushButton("Export Selected Target")
        self.run_selected_button.clicked.connect(self.export_selected_target)

        self.run_stack_button = QtWidgets.QPushButton("Export Selected Stack")
        self.run_stack_button.clicked.connect(self.export_selected_stack)

        self.run_channel_button = QtWidgets.QPushButton("Export Selected Channel")
        self.run_channel_button.clicked.connect(self.export_selected_channel)

        self.run_all_button = QtWidgets.QPushButton("Export All Targets")
        self.run_all_button.clicked.connect(self.export_all_targets)

        self.copy_request_button = QtWidgets.QPushButton("Copy Last Request Path")
        self.copy_request_button.setEnabled(False)
        self.copy_request_button.clicked.connect(self.copy_last_request_path)

        self.copy_export_list_button = QtWidgets.QPushButton("Copy Last Export List Path")
        self.copy_export_list_button.setEnabled(False)
        self.copy_export_list_button.clicked.connect(self.copy_last_export_list_path)

        self.open_output_button = QtWidgets.QPushButton("Open Output Folder")
        self.open_output_button.setEnabled(False)
        self.open_output_button.clicked.connect(self.open_output_folder)

        self.status = QtWidgets.QLabel("Ready")
        self.status.setWordWrap(True)

        self.output = QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(120)

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

            return _call_or_attr(substance_painter.project, "is_open", False)
        except Exception:
            return False

    def _project_is_ready(self):
        try:
            import substance_painter.project

            return (
                _call_or_attr(substance_painter.project, "is_open", False)
                and _call_or_attr(substance_painter.project, "is_in_edition_state", False)
            )
        except Exception:
            return False

    def active_target_key(self):
        import substance_painter.textureset

        stack = _call_or_attr(substance_painter.textureset, "get_active_stack")
        texture_set = _call_or_attr(stack, "material")
        return (_call_or_attr(texture_set, "name"), _call_or_attr(stack, "name") or "")

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.open()

    def open_bridge_dialog(self):
        _show_modal_message(
            self.QtWidgets,
            self.widget,
            "Bridge",
            "Bridge mapping will be implemented later.",
        )

    def _load_user_settings(self):
        store = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        bit_depth = _optional_int(store.value("bit_depth", None))
        return {
            "photoshop_path": store.value("photoshop_path", "", str) or "",
            "infinite_padding": _to_bool(store.value("infinite_padding", False)),
            "dilation": _optional_int(store.value("dilation", 8)) or 8,
            "auto_open_photoshop": _to_bool(store.value("auto_open_photoshop", True)),
            "export_uv_map": _to_bool(store.value("export_uv_map", False)),
            "bit_depth": bit_depth,
        }

    def save_user_settings(self, values):
        store = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        store.setValue("photoshop_path", values.get("photoshop_path") or "")
        store.setValue("infinite_padding", bool(values.get("infinite_padding")))
        store.setValue("dilation", int(values.get("dilation") or 8))
        store.setValue("auto_open_photoshop", bool(values.get("auto_open_photoshop")))
        store.setValue("export_uv_map", bool(values.get("export_uv_map")))
        bit_depth = values.get("bit_depth")
        if bit_depth:
            store.setValue("bit_depth", int(bit_depth))
        else:
            store.remove("bit_depth")
        store.sync()
        self.user_settings = self._load_user_settings()
        _show_modal_message(
            self.QtWidgets,
            self.widget,
            "Settings",
            "Settings saved.",
        )

    def open_export_dialog(self):
        if not self._project_is_open():
            _show_modal_message(
                self.QtWidgets,
                self.widget,
                "Export",
                "Open a Painter project to export.",
            )
            return

        dialog = ExportDialog(self)
        dialog.open()

    def refresh_targets(self):
        if not self._project_is_open():
            _show_modal_message(
                self.QtWidgets,
                self.widget,
                "Export",
                "Open a Painter project to refresh export targets.",
            )
            return

        self.status.setText("Refreshing export targets...")
        self.QtWidgets.QApplication.processEvents()

        try:
            self.targets = list_export_targets()
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            self.targets = []
            self.target_combo.clear()
            self.channel_combo.clear()
            self.target_combo.setEnabled(False)
            self.channel_combo.setEnabled(False)
            self.status.setText("Target refresh failed.")
            self.output.setPlainText(f"{type(exc).__name__}: {exc}")
            return

        self.target_combo.clear()
        for target in self.targets:
            stack_label = target["stack"] or "(default)"
            tile_label = f"{target['uv_tile_count']} tile(s)"
            self.target_combo.addItem(
                f"{target['texture_set']} / {stack_label} / {tile_label}",
                target,
            )

        enabled = bool(self.targets)
        self.target_combo.setEnabled(enabled)
        self.channel_combo.setEnabled(enabled)
        self.refresh_channel_combo()
        self.status.setText(f"Found {len(self.targets)} export target(s).")
        self.output.setPlainText(self._format_targets(self.targets))

    def refresh_channel_combo(self):
        self.channel_combo.clear()
        target = self._selected_target()
        if not target:
            return

        channels = target.get("channels", [])
        channel_labels = target.get("channel_labels", {})
        preferred = "BaseColor" if "BaseColor" in channels else None
        for channel in channels:
            label = channel_labels.get(channel) or channel
            display = label if label == channel else f"{label} ({channel})"
            self.channel_combo.addItem(display, channel)
        if preferred:
            index = self.channel_combo.findData(preferred)
            if index >= 0:
                self.channel_combo.setCurrentIndex(index)

    def export_selected_target(self):
        target = self._selected_target()
        channel = self._selected_channel()
        if not target or not channel:
            self.status.setText("Click Refresh Targets, then choose a target/channel.")
            return

        settings = {
            **self._base_export_settings(),
            "texture_sets": [target["texture_set"]],
            "stacks": [target["stack"]],
            "channels": [channel],
        }
        self._run_export("selected target", settings)

    def export_selected_stack(self):
        target = self._selected_target()
        if not target:
            self.status.setText("Click Refresh Targets, then choose a target.")
            return

        channels = list(target.get("channels") or [])
        if not channels:
            self.status.setText("The selected stack has no exportable channels.")
            return

        stack_label = target["stack"] or "(default)"
        settings = {
            **self._base_export_settings(),
            "texture_sets": [target["texture_set"]],
            "stacks": [target["stack"]],
            "channels": channels,
        }
        self._run_export(
            f"{target['texture_set']} / {stack_label} stack",
            settings,
        )

    def export_selected_channel(self):
        channel = self._selected_channel()
        if not channel:
            self.status.setText("Click Refresh Targets, then choose a channel.")
            return

        settings = {
            **self._base_export_settings(),
            "channels": [channel],
        }
        self._run_export(f"{channel} channel", settings)

    def export_all_targets(self):
        self._run_export("all targets", self._base_export_settings())

    def _run_export(self, label, settings):
        if not self._project_is_open():
            _show_modal_message(
                self.QtWidgets,
                self.widget,
                "Export",
                "Open a Painter project before exporting.",
            )
            return
        if not self._project_is_ready():
            _show_modal_message(
                self.QtWidgets,
                self.widget,
                "Export",
                "Painter project is still loading or not editable.",
            )
            return

        export_pngs = self.export_pngs.isChecked()
        self._running = True
        self._set_action_buttons_enabled(False)
        self.status.setText(f"Exporting {label}...")
        self.QtWidgets.QApplication.processEvents()
        progress = self._create_export_progress(label)

        try:
            output_dir = default_output_dir(settings)
            paths = write_build_bundles(
                output_dir,
                settings=settings,
                export_pngs=export_pngs,
                progress_callback=lambda event: self._update_export_progress(
                    progress,
                    event,
                ),
            )
        except ExportCancelled:
            self.status.setText("Export cancelled.")
            self.output.setPlainText("Export was cancelled before completion.")
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            self.status.setText("Export failed.")
            self.output.setPlainText(f"{type(exc).__name__}: {exc}")
        else:
            self.last_paths = paths
            self.last_output_dir = Path(output_dir)
            self.last_export_list_path = self._write_last_export_list(
                label,
                paths,
                self.last_output_dir,
                settings,
                export_pngs,
            )
            self.copy_request_button.setEnabled(bool(paths))
            self.copy_export_list_button.setEnabled(self.last_export_list_path is not None)
            self.open_output_button.setEnabled(True)
            mode = "JSON + PNG" if export_pngs else "JSON-only"
            self.status.setText(f"Export completed ({mode}).")
            lines = [
                f"Wrote {len(paths)} build request(s):",
                f"Output folder: {self.last_output_dir}",
                f"Last export list: {self.last_export_list_path}",
            ]
            lines.extend(str(path) for path in paths)
            self.output.setPlainText("\n".join(lines))
        finally:
            progress.close()
            self._running = False
            self._set_action_buttons_enabled(True)

    def _run_export_selections(self, label, selections, export_pngs):
        if not self._project_is_open():
            return {"ok": False, "message": "Open a Painter project before exporting."}
        if not self._project_is_ready():
            return {
                "ok": False,
                "message": "Painter project is still loading or not editable.",
            }
        if not selections:
            return {"ok": False, "message": "No channels were selected."}

        base_settings = self._base_export_settings()
        output_dir = default_output_dir(base_settings)
        all_paths = []
        texture_sets = []
        stacks = []
        channels = []

        self._running = True
        self._set_action_buttons_enabled(False)
        self.status.setText(f"Exporting {label}...")
        self.QtWidgets.QApplication.processEvents()
        progress = self._create_export_progress(label)

        try:
            for target, selected_channels in selections:
                texture_set = target["texture_set"]
                stack = target["stack"]
                stack_label = stack or "(default)"
                settings = {
                    **base_settings,
                    "texture_sets": [texture_set],
                    "stacks": [stack],
                    "channels": list(selected_channels),
                }
                texture_sets.append(texture_set)
                stacks.append(stack)
                channels.extend(selected_channels)
                self.status.setText(f"Exporting {texture_set} / {stack_label}...")
                all_paths.extend(
                    write_build_bundles(
                        output_dir,
                        settings=settings,
                        export_pngs=export_pngs,
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
            self._running = False
            self._set_action_buttons_enabled(True)

        combined_settings = {
            **base_settings,
            "texture_sets": sorted(set(texture_sets)),
            "stacks": _unique_preserving_order(stacks),
            "channels": sorted(set(channels)),
        }
        self.last_paths = all_paths
        self.last_output_dir = Path(output_dir)
        self.last_export_list_path = self._write_last_export_list(
            label,
            all_paths,
            self.last_output_dir,
            combined_settings,
            export_pngs,
        )
        self.copy_request_button.setEnabled(bool(all_paths))
        self.copy_export_list_button.setEnabled(self.last_export_list_path is not None)
        self.open_output_button.setEnabled(True)

        mode = "JSON + PNG" if export_pngs else "JSON-only"
        self.status.setText(f"Export completed ({mode}).")
        return {
            "ok": True,
            "message": f"Exported {len(all_paths)} build request(s).",
            "count": len(all_paths),
            "output_dir": self.last_output_dir,
            "export_list": self.last_export_list_path,
            "paths": list(all_paths),
        }

    def copy_last_request_path(self):
        if not self.last_paths:
            self.status.setText("No exported build request path to copy yet.")
            return

        self.QtWidgets.QApplication.clipboard().setText(str(self.last_paths[-1]))
        self.status.setText("Copied last build_request.json path.")

    def copy_last_export_list_path(self):
        if self.last_export_list_path is None:
            self.status.setText("No last export list path to copy yet.")
            return

        self.QtWidgets.QApplication.clipboard().setText(str(self.last_export_list_path))
        self.status.setText("Copied last export list path.")

    def open_output_folder(self):
        if self.last_output_dir is None:
            self.status.setText("No output folder to open yet.")
            return

        path = str(self.last_output_dir)
        url = self.QtCore.QUrl.fromLocalFile(path)
        if self.QtGui.QDesktopServices.openUrl(url):
            self.status.setText("Opened output folder.")
        else:
            self.status.setText(f"Could not open output folder: {path}")

    def launch_photoshop(self, launcher_path):
        executable = Path(self.user_settings.get("photoshop_path") or "")
        if not executable.is_file():
            return False, "Set a valid Photoshop executable in Settings."

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

        self.status.setText("Export complete. Opening Photoshop...")
        return True, ""

    def _selected_target(self):
        index = self.target_combo.currentIndex()
        if index < 0:
            return None
        return self.target_combo.itemData(index)

    def _selected_channel(self):
        index = self.channel_combo.currentIndex()
        if index < 0:
            return None
        return self.channel_combo.itemData(index) or self.channel_combo.currentText()

    def _base_export_settings(self):
        settings = {
            "normal_map_format": "OpenGL",
            "infinite_padding": bool(self.user_settings.get("infinite_padding")),
            "dilation": int(self.user_settings.get("dilation") or 8),
            "keep_alpha": True,
            "export_uv_map": bool(self.user_settings.get("export_uv_map")),
        }
        bit_depth = self.user_settings.get("bit_depth")
        if bit_depth:
            settings["bit_depth"] = int(bit_depth)
        return settings

    def _write_last_export_list(self, label, paths, output_dir, settings, export_pngs):
        list_path = output_dir / LAST_EXPORT_FILENAME
        payload = {
            "schema_version": 1,
            "request_type": "build_list",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "label": label,
            "export_pngs": bool(export_pngs),
            "output_dir": str(output_dir),
            "settings": {
                "texture_sets": settings.get("texture_sets"),
                "stacks": settings.get("stacks"),
                "channels": settings.get("channels"),
                "export_uv_map": bool(settings.get("export_uv_map")),
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
        self.dock_bridge_button.setEnabled(False)
        self.dock_settings_button.setEnabled(enabled)
        self.refresh_targets_button.setEnabled(enabled)
        self.run_selected_button.setEnabled(enabled)
        self.run_stack_button.setEnabled(enabled)
        self.run_channel_button.setEnabled(enabled)
        self.run_all_button.setEnabled(enabled)
        if enabled:
            self.copy_request_button.setEnabled(bool(self.last_paths))
            self.copy_export_list_button.setEnabled(self.last_export_list_path is not None)
            self.open_output_button.setEnabled(self.last_output_dir is not None)
        else:
            self.copy_request_button.setEnabled(False)
            self.copy_export_list_button.setEnabled(False)
            self.open_output_button.setEnabled(False)

    def _create_export_progress(self, label):
        progress = self.QtWidgets.QProgressDialog(
            f"Exporting {label}...",
            "Cancel",
            0,
            0,
            self.widget,
        )
        progress.setWindowTitle("Rizum PT-to-PS Export")
        modality = getattr(self.QtCore.Qt, "ApplicationModal", None)
        if modality is None:
            modality = self.QtCore.Qt.WindowModality.ApplicationModal
        progress.setWindowModality(modality)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimumDuration(0)
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
        self.status.setText(text)
        progress.dialog.repaint()
        self.QtWidgets.QApplication.processEvents()
        return not progress.wasCanceled()

    def _format_targets(self, targets):
        lines = ["Available export targets.", ""]
        if not targets:
            lines.append("No texture set targets were found.")
            return "\n".join(lines)

        for index, target in enumerate(targets, start=1):
            stack = target["stack"] or "(default)"
            channel_labels = target.get("channel_labels", {})
            channels = ", ".join(
                channel_labels.get(channel) or channel for channel in target["channels"]
            ) or "(none)"
            lines.append(
                f"[{index}] {target['texture_set']} / {stack} / "
                f"{target['uv_tile_count']} tile(s)"
            )
            lines.append(f"    Channels: {channels}")
        return "\n".join(lines)


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


def _call_or_attr(obj, name, default=None):
    value = getattr(obj, name, default)
    return value() if callable(value) else value


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _optional_int(value):
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def register():
    """Register Painter UI elements and return handles for cleanup."""
    import substance_painter as sp

    global _ACTIVE_DOCK, _ACTIVE_PANEL
    panel = SmokeTestPanel()
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
