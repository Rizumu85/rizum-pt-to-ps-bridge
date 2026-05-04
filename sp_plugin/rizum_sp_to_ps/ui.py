"""Painter UI registration for Rizum PT-to-PS Bridge."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .exporter import (
    ExportCancelled,
    default_output_dir,
    list_export_targets,
    write_build_bundles,
)
from rizum_ui import (
    ActionButton,
    apply_theme,
    build_compact_dock_stylesheet,
    compact_footer_button_width,
    make_combo_input,
    make_compact_dock_card,
    make_compact_dock_layout,
    make_compact_stepper,
    make_icon_button,
    make_inset_separator,
    set_compact_footer_button_width,
)

LAST_EXPORT_FILENAME = "_last_export.json"
SETTINGS_ORG = "Rizum"
SETTINGS_APP = "PTBridge"
_ACTIVE_PANEL = None
_ACTIVE_DOCK = None

BRIDGE_DOCK_BG = "#2b2b2b"
BRIDGE_DOCK_ACTIONS_WIDTH = 260
BRIDGE_DOCK_DEFAULT_WIDTH = 290
BRIDGE_DOCK_DEFAULT_HEIGHT = 99


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
QDialog#RizumSettingsDialog {
    background: #f3f3f3;
    color: #e0e0e0;
}
QFrame#RizumSettingsCard {
    background: #1b1b1b;
    border: 0;
    border-radius: 6px;
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
QLabel#RizumSettingsSection {
    color: #9e9e9e;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    background: transparent;
    border: 0;
}
QLabel#RizumSettingsItemName {
    color: #e0e0e0;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
    border: 0;
}
QLabel#RizumSettingsItemMeta,
QLabel#RizumSettingsFooterHint {
    color: #9e9e9e;
    font-size: 11px;
    font-weight: 500;
    background: transparent;
    border: 0;
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
    font-size: 11px;
    font-weight: 500;
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
    label.setFixedHeight(28 if first else 40)
    return label


def _settings_frame_row(QtWidgets, height=40):
    row = QtWidgets.QFrame()
    row.setObjectName("RizumSettingsRow")
    row.setFixedHeight(height)
    layout = QtWidgets.QHBoxLayout(row)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)
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
        def __init__(self):
            super().__init__()
            self.setObjectName("RizumSettingsToggle")
            self.setCheckable(True)
            self.setChecked(bool(checked))
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.setFixedSize(36, 20)

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            track = QtCore.QRectF(0, 0, self.width(), self.height())
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor("#3a3a3a" if self.isChecked() else "#2f2f2f"))
            painter.drawRoundedRect(track, 10, 10)

            knob_size = 14
            knob_x = self.width() - knob_size - 3 if self.isChecked() else 3
            knob_rect = QtCore.QRectF(knob_x, 3, knob_size, knob_size)
            painter.setBrush(QtGui.QColor("#a0a0a0"))
            painter.drawEllipse(knob_rect)
            painter.end()

    return _SettingsToggle()


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


def _bridge_icon_pixmap(QtCore, QtGui, QtWidgets, icon_name, size, color):
    try:
        from PySide6 import QtSvg
    except Exception:
        QtSvg = None

    icon_path = Path(__file__).resolve().parents[2] / "icons" / icon_name
    dpr = QtWidgets.QApplication.primaryScreen().devicePixelRatio() if QtWidgets.QApplication.primaryScreen() else 1.0
    pixel_size = max(1, int(round(size * dpr)))
    if QtSvg is None:
        pixmap = QtGui.QIcon(str(icon_path)).pixmap(QtCore.QSize(pixel_size, pixel_size))
        pixmap.setDevicePixelRatio(dpr)
        return pixmap

    source = icon_path.read_text(encoding="utf-8")
    source = source.replace('stroke="#9E9E9E"', f'stroke="{color}"')
    source = source.replace('stroke="#9e9e9e"', f'stroke="{color}"')
    source = source.replace('viewBox="0 0 24 24"', 'viewBox="-2 -2 28 28"')
    pixmap = QtGui.QPixmap(pixel_size, pixel_size)
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(source.encode("utf-8")))
    renderer.render(painter, QtCore.QRectF(0, 0, size, size))
    painter.end()
    return pixmap


def _make_bridge_dock_action_button(QtCore, QtGui, QtWidgets, label, icon_name, primary=False):
    class _BridgeDockActionButton(QtWidgets.QAbstractButton):
        def __init__(self):
            super().__init__()
            self.setObjectName("RizumBridgeDockActionButton")
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.setFixedSize(70, 48)
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            self._visual_scale = 1.0
            self._animation = None

        def sizeHint(self):
            return QtCore.QSize(70, 48)

        def minimumSizeHint(self):
            return QtCore.QSize(70, 48)

        def getVisualScale(self):
            return self._visual_scale

        def setVisualScale(self, value):
            self._visual_scale = float(value)
            self.update()

        visualScale = QtCore.Property(float, getVisualScale, setVisualScale)

        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._animate_scale(0.92, 120)
            super().mousePressEvent(event)

        def mouseReleaseEvent(self, event):
            super().mouseReleaseEvent(event)
            self._animate_scale(1.0, 280)

        def leaveEvent(self, event):
            super().leaveEvent(event)
            if not self.isDown():
                self._animate_scale(1.0, 220)

        def _animate_scale(self, scale, duration):
            if self._animation is not None:
                self._animation.stop()
            animation = QtCore.QPropertyAnimation(self, b"visualScale", self)
            animation.setDuration(duration)
            animation.setStartValue(self._visual_scale)
            animation.setEndValue(float(scale))
            animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            self._animation = animation
            animation.start()

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)

            base_rect = QtCore.QRectF(0.5, 0.5, 69, 47)
            scale = max(0.1, min(1.0, self._visual_scale))
            rect = QtCore.QRectF(
                base_rect.center().x() - base_rect.width() * scale / 2,
                base_rect.center().y() - base_rect.height() * scale / 2,
                base_rect.width() * scale,
                base_rect.height() * scale,
            )

            hovered = self.underMouse()
            if primary:
                fill = QtGui.QColor("#ffffff")
                if hovered:
                    fill.setAlphaF(0.9)
                text_color = QtGui.QColor("#1b1b1b")
            else:
                fill = QtGui.QColor("#262626" if hovered else "#222222")
                text_color = QtGui.QColor("#e0e0e0" if hovered else "#9e9e9e")
            if self.isDown():
                fill = QtGui.QColor("#dedede") if primary else QtGui.QColor(255, 255, 255, 8)

            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            for offset_y, spread, alpha in ((3, 1, 34), (7, 4, 18), (10, 7, 8)):
                shadow_rect = rect.adjusted(-spread, -spread, spread, spread).translated(0, offset_y)
                painter.setBrush(QtGui.QColor(0, 0, 0, alpha))
                painter.drawRoundedRect(shadow_rect, 12 + spread, 12 + spread)

            painter.setBrush(fill)
            painter.drawRoundedRect(rect, 12, 12)

            icon_size = max(14, min(20, int(round(18 * scale))))
            icon_gap = max(3, int(round(4 * scale)))
            label_height = 12
            content_height = icon_size + icon_gap + label_height
            content_top = rect.top() + (rect.height() - content_height) / 2 - 1
            icon_pixmap = _bridge_icon_pixmap(
                QtCore,
                QtGui,
                QtWidgets,
                icon_name,
                icon_size,
                text_color.name(),
            )
            icon_x = int(rect.center().x() - icon_size / 2)
            icon_y = int(round(content_top))
            painter.drawPixmap(QtCore.QPoint(icon_x, icon_y), icon_pixmap)

            font = QtGui.QFont(self.font())
            font.setFamilies(["Segoe UI", "Arial", "sans-serif"])
            font.setPixelSize(max(8, int(round(10 * scale))))
            font.setWeight(QtGui.QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.setPen(text_color)
            text_rect = QtCore.QRectF(
                rect.left() + 5,
                icon_y + icon_size + icon_gap,
                rect.width() - 10,
                max(10, int(round(label_height * scale))),
            )
            painter.drawText(
                text_rect,
                QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter,
                label,
            )
            painter.end()

    return _BridgeDockActionButton()


def _make_bridge_dock_actions_panel(QtCore, QtGui, QtWidgets):
    class _BridgeDockActionsPanel(QtWidgets.QFrame):
        def __init__(self):
            super().__init__()
            self.setObjectName("RizumBridgeDockActionsPanel")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor("#1b1b1b"))
            painter.drawRoundedRect(rect, 10, 10)
            painter.end()

    panel = _BridgeDockActionsPanel()
    panel.setFixedSize(BRIDGE_DOCK_ACTIONS_WIDTH, 78)
    panel.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Fixed,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    layout = QtWidgets.QHBoxLayout(panel)
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(8)
    buttons = [
        _make_bridge_dock_action_button(QtCore, QtGui, QtWidgets, "Export", "action-export.svg", True),
        _make_bridge_dock_action_button(QtCore, QtGui, QtWidgets, "Bridge", "action-bridge.svg", False),
        _make_bridge_dock_action_button(QtCore, QtGui, QtWidgets, "Settings", "action-sun.svg", False),
    ]
    for button in buttons:
        layout.addWidget(button)
    panel.actionButtons = lambda: list(buttons)
    return panel


class SettingsDialog:
    """Global Painter-side bridge settings."""

    def __init__(self, panel):
        self.panel = panel
        self.QtCore = panel.QtCore
        self.QtGui = panel.QtGui
        self.QtWidgets = panel.QtWidgets

        self.dialog = self.QtWidgets.QDialog(panel.widget)
        self.dialog.setObjectName("RizumSettingsDialog")
        self.dialog.setWindowTitle("Settings")
        self.dialog.setModal(True)
        self.dialog.setMinimumSize(386, 544)
        self.dialog.resize(386, 544)
        apply_theme(self.dialog, mode="overlay")

        layout = self.QtWidgets.QVBoxLayout(self.dialog)
        layout.setContentsMargins(2, 0, 2, 2)
        layout.setSpacing(0)

        card = self.QtWidgets.QFrame()
        card.setObjectName("RizumSettingsCard")
        card_layout = self.QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        body = self.QtWidgets.QWidget()
        body.setObjectName("RizumSettingsBody")
        body_layout = self.QtWidgets.QVBoxLayout(body)
        body_layout.setContentsMargins(12, 8, 12, 0)
        body_layout.setSpacing(2)

        body_layout.addWidget(_settings_section(self.QtWidgets, "Export", first=True))
        self.infinite_padding = _make_settings_toggle(self.QtCore, self.QtGui, self.QtWidgets)
        padding_row, padding_layout = _settings_frame_row(self.QtWidgets, 51)
        padding_texts = _settings_text_block(self.QtWidgets, "Padding", "Infinite")
        self.padding_meta = padding_texts.findChild(self.QtWidgets.QLabel, "RizumSettingsItemMeta")
        padding_layout.addWidget(padding_texts)
        padding_layout.addStretch(1)
        padding_layout.addWidget(self.infinite_padding)
        body_layout.addWidget(padding_row)

        self.dilation_row, dilation_layout = _settings_frame_row(self.QtWidgets, 51)
        dilation_layout.addWidget(_settings_text_block(self.QtWidgets, "Dilation", "px"))
        dilation_layout.addStretch(1)
        self.dilation_stepper = make_compact_stepper(8, minimum=0, maximum=999, step=1)
        self.dilation_stepper.setTheme(
            {
                "window_bg": "#1b1b1b",
                "text": "#e0e0e0",
                "muted": "#9e9e9e",
                "control_hover": "#343434",
            }
        )
        dilation_layout.addWidget(self.dilation_stepper)
        body_layout.addWidget(self.dilation_row)

        self.bit_depth = make_combo_input([("Texture Set", None), ("8-bit", 8), ("16-bit", 16)])
        self.bit_depth.setFitToContents(False)
        self.bit_depth.setFixedWidth(126)
        bit_depth_row, bit_depth_layout = _settings_frame_row(self.QtWidgets, 40)
        bit_depth_layout.addWidget(_settings_label(self.QtWidgets, "Bit depth", "RizumSettingsItemName"))
        bit_depth_layout.addStretch(1)
        bit_depth_layout.addWidget(self.bit_depth)
        body_layout.addWidget(bit_depth_row)

        self.auto_open_photoshop = _make_settings_toggle(self.QtCore, self.QtGui, self.QtWidgets)
        auto_row, auto_layout = _settings_frame_row(self.QtWidgets, 36)
        auto_layout.addWidget(_settings_label(self.QtWidgets, "Auto-open Photoshop", "RizumSettingsItemName"))
        auto_layout.addStretch(1)
        auto_layout.addWidget(self.auto_open_photoshop)
        body_layout.addWidget(auto_row)

        body_layout.addWidget(_settings_section(self.QtWidgets, "Photoshop"))
        path_row, path_row_layout = _settings_frame_row(self.QtWidgets, 45)
        path_row_layout.setContentsMargins(8, 5, 8, 5)
        path_field = self.QtWidgets.QFrame()
        path_field.setObjectName("RizumSettingsMockSelect")
        path_field.setFixedHeight(34)
        path_layout = self.QtWidgets.QHBoxLayout(path_field)
        path_layout.setContentsMargins(8, 0, 8, 0)
        path_layout.setSpacing(6)
        self.photoshop_path = self.QtWidgets.QLineEdit()
        self.photoshop_path.setObjectName("RizumSettingsPathInput")
        self.photoshop_path.setPlaceholderText("Photoshop.exe")
        self.photoshop_path.setFrame(False)
        self.photoshop_path.setClearButtonEnabled(False)
        self.photoshop_path.setMinimumHeight(20)
        self.photoshop_path.setAlignment(self.panel.QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.browse_button = make_icon_button("folder.svg", "Browse executable", size=14, compact=False)
        self.browse_button.setFixedSize(26, 26)
        self.browse_button.clicked.connect(self.browse_photoshop)
        path_layout.addWidget(self.photoshop_path, 1, self.panel.QtCore.Qt.AlignmentFlag.AlignVCenter)
        path_row_layout.addWidget(path_field, 1)
        path_row_layout.addWidget(self.browse_button)
        body_layout.addWidget(path_row)

        body_layout.addWidget(_settings_section(self.QtWidgets, "About"))
        version_row, version_layout = _settings_frame_row(self.QtWidgets, 34)
        version_layout.addWidget(_settings_label(self.QtWidgets, "Version", "RizumSettingsItemName"))
        version_layout.addStretch(1)
        version_layout.addWidget(_settings_label(self.QtWidgets, "2.0.0", "RizumSettingsItemMeta"))
        body_layout.addWidget(version_row)

        card_layout.addWidget(body)
        card_layout.addStretch(1)

        footer = self.QtWidgets.QWidget()
        footer.setObjectName("RizumSettingsFooter")
        footer.setFixedHeight(48)
        footer_layout = self.QtWidgets.QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 0, 16, 0)
        footer_layout.setSpacing(0)
        footer_layout.addWidget(_settings_label(self.QtWidgets, "Changes save automatically", "RizumSettingsFooterHint"))
        footer_layout.addStretch(1)
        self.done_button = ActionButton.create("Done", "dialog-primary")
        self.done_button.clicked.connect(self.save)
        footer_layout.addWidget(self.done_button)
        card_layout.addWidget(footer)
        set_compact_footer_button_width(self.done_button, compact_footer_button_width(self.done_button, minimum=68, maximum=96))
        layout.addWidget(card)
        self.dialog.setStyleSheet(self.dialog.styleSheet() + BRIDGE_DIALOG_STYLESHEET)
        self.infinite_padding.toggled.connect(self._sync_padding_mode)

        self.load_values()

    def open(self):
        self.load_values()
        return self.dialog.exec()

    def load_values(self):
        settings = self.panel.user_settings
        self.photoshop_path.setText(settings.get("photoshop_path") or "")
        self.infinite_padding.setChecked(bool(settings.get("infinite_padding")))
        self.dilation_stepper.setValue(int(settings.get("dilation") or 8), emit=False)
        self.auto_open_photoshop.setChecked(bool(settings.get("auto_open_photoshop")))
        self._sync_padding_mode()

        bit_depth = settings.get("bit_depth")
        index = self.bit_depth.findData(bit_depth)
        self.bit_depth.setCurrentIndex(index if index >= 0 else 0)

    def _sync_padding_mode(self):
        infinite = self.infinite_padding.isChecked()
        if self.padding_meta is not None:
            self.padding_meta.setText("Infinite" if infinite else "Custom")
        self.dilation_row.setVisible(not infinite)

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
                "bit_depth": self.bit_depth.currentData(),
            }
        )
        self.dialog.accept()


class ExportDialog:
    """Focused target/channel export dialog launched from the Painter dock."""

    def __init__(self, panel):
        self.panel = panel
        self.QtCore = panel.QtCore
        self.QtWidgets = panel.QtWidgets
        self.targets = []
        self._updating_checks = False

        self.dialog = self.QtWidgets.QDialog(panel.widget)
        self.dialog.setWindowTitle("Export")
        self.dialog.setModal(True)
        self.dialog.setFixedWidth(318)
        self.dialog.resize(318, 420)
        apply_theme(self.dialog, mode="overlay")

        layout = self.QtWidgets.QVBoxLayout(self.dialog)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = self.QtWidgets.QLabel("Export")
        title.setObjectName("RizumDialogTitle")
        layout.addWidget(title)
        layout.addWidget(make_inset_separator(0, thickness=1))

        toolbar_widget = self.QtWidgets.QWidget()
        toolbar_widget.setObjectName("RizumDialogToolbar")
        header = self.QtWidgets.QHBoxLayout(toolbar_widget)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)
        self.scope_combo = make_combo_input([("Current Stack", "current"), ("All Stacks", "all")])
        self.scope_combo.setCompactHeight(28)
        self.scope_combo.currentIndexChanged.connect(self.refresh_tree)
        header.addWidget(self.scope_combo, 0)
        header.addStretch(1)

        self.expand_button = make_icon_button("chevrons-down.svg", "Expand all", size=14)
        self.collapse_button = make_icon_button("chevrons-up.svg", "Collapse all", size=14)
        self.all_button = make_icon_button("circle-dot.svg", "Select all", size=14)
        self.none_button = make_icon_button("circle-slash.svg", "Select none", size=14)
        self.expand_button.clicked.connect(self.tree_expand_all)
        self.collapse_button.clicked.connect(self.tree_collapse_all)
        self.all_button.clicked.connect(lambda: self.set_all_checked(True))
        self.none_button.clicked.connect(lambda: self.set_all_checked(False))
        header.addWidget(self.expand_button)
        header.addWidget(self.collapse_button)
        header.addSpacing(8)
        header.addWidget(self.all_button)
        header.addWidget(self.none_button)
        layout.addWidget(toolbar_widget)
        layout.addWidget(make_inset_separator(0, thickness=1))

        self.tree = self.QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.setMinimumHeight(150)
        layout.addWidget(self.tree, 1)

        self.export_pngs = self.QtWidgets.QCheckBox("Export PNGs")
        self.export_pngs.setChecked(True)
        self.export_pngs.setVisible(False)

        self.status = self.QtWidgets.QLabel("")
        self.status.setObjectName("RizumDimLabel")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.output = self.QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(72)
        self.output.setVisible(False)
        layout.addWidget(self.output)

        footer = self.QtWidgets.QHBoxLayout()
        footer.setContentsMargins(0, 6, 0, 0)
        self.cancel_button = ActionButton.create("Cancel", "dialog-secondary")
        self.run_button = ActionButton.create("Export", "dialog-primary")
        self.cancel_button.clicked.connect(self.dialog.reject)
        self.run_button.clicked.connect(self.export_checked)
        footer.addWidget(self.cancel_button)
        footer.addStretch(1)
        footer.addWidget(self.run_button)
        layout.addLayout(footer)
        set_compact_footer_button_width(
            self.cancel_button,
            compact_footer_button_width(self.cancel_button, minimum=74, maximum=96),
        )
        set_compact_footer_button_width(
            self.run_button,
            compact_footer_button_width(self.run_button, minimum=82, maximum=108),
        )
        self.dialog.setStyleSheet(self.dialog.styleSheet() + BRIDGE_DIALOG_STYLESHEET)

    def open(self):
        self.refresh_targets()
        return self.dialog.exec()

    def tree_expand_all(self):
        self.tree.expandAll()

    def tree_collapse_all(self):
        self.tree.collapseAll()

    def _enum(self, group, name):
        container = getattr(self.QtCore.Qt, group, self.QtCore.Qt)
        return getattr(container, name)

    def _checked(self):
        return self._enum("CheckState", "Checked")

    def _unchecked(self):
        return self._enum("CheckState", "Unchecked")

    def _partial(self):
        return self._enum("CheckState", "PartiallyChecked")

    def _user_role(self):
        return self._enum("ItemDataRole", "UserRole")

    def _checkable_flags(self):
        return (
            self._enum("ItemFlag", "ItemIsEnabled")
            | self._enum("ItemFlag", "ItemIsSelectable")
            | self._enum("ItemFlag", "ItemIsUserCheckable")
        )

    def refresh_targets(self):
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

        try:
            self.targets = list_export_targets(settings=self.panel._base_export_settings())
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            self.targets = []
            self.status.setText(f"Could not list export targets: {type(exc).__name__}: {exc}")
        self.refresh_tree()

    def refresh_tree(self):
        self._updating_checks = True
        self.tree.clear()

        visible_targets = self._visible_targets()
        if not visible_targets:
            if self.scope_combo.currentText() == "Current Stack":
                self.status.setText("No exportable channels found for Current Stack.")
            else:
                self.status.setText("No exportable channels were found.")
            self.run_button.setEnabled(False)
            self._updating_checks = False
            return

        self.run_button.setEnabled(True)
        if self.scope_combo.currentText() == "Current Stack" and self._active_target_key() is None:
            self.status.setText("Showing the first available stack for Current Stack.")
        else:
            self.status.setText("")

        for target in visible_targets:
            item = self.QtWidgets.QTreeWidgetItem([self._target_label(target)])
            item.setFlags(self._checkable_flags())
            item.setCheckState(0, self._unchecked())
            item.setData(
                0,
                self._user_role(),
                {"kind": "target", "target": target},
            )
            self.tree.addTopLevelItem(item)

            labels = target.get("channel_labels", {})
            for channel in target.get("channels", []):
                child = self.QtWidgets.QTreeWidgetItem([labels.get(channel) or channel])
                child.setFlags(self._checkable_flags())
                child.setCheckState(0, self._unchecked())
                child.setData(
                    0,
                    self._user_role(),
                    {"kind": "channel", "channel": channel},
                )
                item.addChild(child)
            item.setExpanded(True)

        self._updating_checks = False

    def _visible_targets(self):
        if self.scope_combo.currentText() == "Current Stack":
            active_key = self._active_target_key()
            if active_key is None:
                return self.targets[:1]
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
        channels = target.get("channels") or []
        channel_word = "channel" if len(channels) == 1 else "channels"
        return f"{texture_set} / {stack} / {len(channels)} {channel_word}"

    def set_all_checked(self, checked):
        state = self._checked() if checked else self._unchecked()
        self._updating_checks = True
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            item.setCheckState(0, state)
            for child_index in range(item.childCount()):
                item.child(child_index).setCheckState(0, state)
        self._updating_checks = False

    def _on_item_changed(self, item, column):
        if self._updating_checks or column != 0:
            return

        data = item.data(0, self._user_role()) or {}
        if data.get("kind") == "target":
            self._updating_checks = True
            state = item.checkState(0)
            for child_index in range(item.childCount()):
                item.child(child_index).setCheckState(0, state)
            self._updating_checks = False
            return

        parent = item.parent()
        if parent is None:
            return

        checked_count = 0
        partial_count = 0
        for child_index in range(parent.childCount()):
            state = parent.child(child_index).checkState(0)
            if state == self._checked():
                checked_count += 1
            elif state == self._partial():
                partial_count += 1

        self._updating_checks = True
        if checked_count == parent.childCount():
            parent.setCheckState(0, self._checked())
        elif checked_count or partial_count:
            parent.setCheckState(0, self._partial())
        else:
            parent.setCheckState(0, self._unchecked())
        self._updating_checks = False

    def selected_exports(self):
        selections = []
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            data = item.data(0, self._user_role()) or {}
            target = data.get("target")
            if not target:
                continue

            channels = []
            for child_index in range(item.childCount()):
                child = item.child(child_index)
                if child.checkState(0) != self._checked():
                    continue
                child_data = child.data(0, self._user_role()) or {}
                channel = child_data.get("channel")
                if channel:
                    channels.append(channel)
            if channels:
                selections.append((target, channels))
        return selections

    def export_checked(self):
        selections = self.selected_exports()
        if not selections:
            _show_modal_message(
                self.QtWidgets,
                self.dialog,
                "Export",
                "Choose at least one channel to export.",
            )
            return

        self.output.setVisible(True)
        self.output.clear()
        self.output.setPlainText(
            self.panel._run_export_selections(
                "export dialog selection",
                selections,
                export_pngs=self.export_pngs.isChecked(),
            )
        )


class SmokeTestPanel:
    """Painter dock panel for the PT Bridge workflow."""

    def __init__(self):
        from PySide6 import QtCore, QtGui, QtWidgets

        self.QtCore = QtCore
        self.QtGui = QtGui
        self.QtWidgets = QtWidgets
        self._running = False
        self.targets = []
        self.last_paths = []
        self.last_export_list_path = None
        self.last_output_dir = None
        self.user_settings = self._load_user_settings()
        self.widget = QtWidgets.QWidget()
        self.widget.setObjectName("RizumPtToPsSmokeTestPanel")
        self.widget.setWindowTitle("PT Bridge")
        self.widget.setMinimumSize(BRIDGE_DOCK_DEFAULT_WIDTH, BRIDGE_DOCK_DEFAULT_HEIGHT)
        self.widget.resize(BRIDGE_DOCK_DEFAULT_WIDTH, BRIDGE_DOCK_DEFAULT_HEIGHT)
        apply_theme(self.widget, mode="overlay")
        _apply_bridge_dock_surface(self.widget)
        self.widget.setStyleSheet(self.widget.styleSheet() + BRIDGE_DIALOG_STYLESHEET)

        outer_layout = make_compact_dock_layout(self.widget)

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

        card = make_compact_dock_card()
        card_layout = card.layout()
        outer_layout.addWidget(card)

        content = QtWidgets.QWidget()
        content.setObjectName("RizumTransparent")
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 6)
        content_layout.setSpacing(10)

        dock_actions = _make_bridge_dock_actions_panel(QtCore, QtGui, QtWidgets)
        self.dock_export_button, self.dock_bridge_button, self.dock_settings_button = (
            dock_actions.actionButtons()
        )
        self.dock_export_button.clicked.connect(self.open_export_dialog)
        self.dock_bridge_button.clicked.connect(self.open_bridge_dialog)
        self.dock_settings_button.clicked.connect(self.open_settings_dialog)
        content_layout.addWidget(
            dock_actions,
            0,
            QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignHCenter,
        )
        content_layout.addStretch(1)
        card_layout.addWidget(content)

    def close(self):
        """Stop owned Qt helpers before Painter removes the dock."""
        pass

    def _project_is_open(self):
        try:
            import substance_painter.project

            return substance_painter.project.is_open()
        except Exception:
            return False

    def _project_is_ready(self):
        try:
            import substance_painter.project

            return (
                substance_painter.project.is_open()
                and substance_painter.project.is_in_edition_state()
            )
        except Exception:
            return False

    def active_target_key(self):
        import substance_painter.textureset

        stack = substance_painter.textureset.get_active_stack()
        texture_set = stack.material()
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
            "auto_open_photoshop": _to_bool(store.value("auto_open_photoshop", False)),
            "bit_depth": bit_depth,
        }

    def save_user_settings(self, values):
        store = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        store.setValue("photoshop_path", values.get("photoshop_path") or "")
        store.setValue("infinite_padding", bool(values.get("infinite_padding")))
        store.setValue("dilation", int(values.get("dilation") or 8))
        store.setValue("auto_open_photoshop", bool(values.get("auto_open_photoshop")))
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
            return "Open a Painter project before exporting."
        if not self._project_is_ready():
            return "Painter project is still loading or not editable."
        if not selections:
            return "No channels were selected."

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
            return "Export was cancelled before completion."
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            return f"{type(exc).__name__}: {exc}"
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
        lines = [
            f"Wrote {len(all_paths)} build request(s):",
            f"Output folder: {self.last_output_dir}",
            f"Last export list: {self.last_export_list_path}",
        ]
        lines.extend(str(path) for path in all_paths)
        return "\n".join(lines)

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
        self.dock_bridge_button.setEnabled(enabled)
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
    try:
        dock.setMinimumSize(BRIDGE_DOCK_DEFAULT_WIDTH, BRIDGE_DOCK_DEFAULT_HEIGHT)
    except Exception:
        pass
    try:
        if hasattr(dock, "isFloating") and not dock.isFloating():
            return
    except Exception:
        pass
    try:
        dock.resize(BRIDGE_DOCK_DEFAULT_WIDTH, BRIDGE_DOCK_DEFAULT_HEIGHT)
    except Exception:
        pass
    try:
        panel.widget.resize(BRIDGE_DOCK_DEFAULT_WIDTH, BRIDGE_DOCK_DEFAULT_HEIGHT)
    except Exception:
        pass
    try:
        panel.QtCore.QTimer.singleShot(
            0,
            lambda: dock.resize(BRIDGE_DOCK_DEFAULT_WIDTH, BRIDGE_DOCK_DEFAULT_HEIGHT),
        )
    except Exception:
        pass
