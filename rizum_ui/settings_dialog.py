"""Shared Painter settings-dialog surface."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from .theme import Theme, default_theme


PAINTER_SETTINGS_FRAME_WIDTH = 2
PAINTER_SETTINGS_FRAME_COLOR = "#f3f3f3"
_SURFACE_OBJECT_NAME = "RizumPainterSettingsSurface"
_UI_FONT_SCALE_PROPERTY = "rizumUiFontScale"
_UI_FONT_SETTINGS_ORG = "Rizum"
_UI_FONT_SETTINGS_APP = "PainterUiFont"
_MIN_UI_SCALE = 0.75
_MAX_UI_SCALE = 2.0
_DIALOG_GUARD_SELECTOR = 'QDialog[rizumPainterSettingsDialog="true"]'


def _bounded_ui_scale(value) -> float:
    try:
        scale = float(value)
    except (TypeError, ValueError):
        scale = 1.0
    return max(_MIN_UI_SCALE, min(_MAX_UI_SCALE, scale))


def _configured_ui_scale() -> float:
    app = QtWidgets.QApplication.instance()
    if app is not None:
        try:
            scale = app.property(_UI_FONT_SCALE_PROPERTY)
            if scale is not None:
                return _bounded_ui_scale(scale)
        except RuntimeError:
            pass

    settings = QtCore.QSettings(
        _UI_FONT_SETTINGS_ORG,
        _UI_FONT_SETTINGS_APP,
    )
    return _bounded_ui_scale(settings.value("scale", 1.0))


class PainterSettingsDialog(QtWidgets.QDialog):
    """Painter dialog with a narrow light frame and rounded dark surface."""

    settingsUiScaleChanged = QtCore.Signal(float)

    def __init__(
        self,
        parent=None,
        *,
        theme: Theme = default_theme,
        frame_width: int = PAINTER_SETTINGS_FRAME_WIDTH,
    ):
        super().__init__(parent)
        self.setObjectName("RizumPainterSettingsDialog")
        self.setProperty("rizumPainterSettingsDialog", True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet(
            ""
        )
        self._settings_theme = theme
        self._settings_frame_color = QtGui.QColor(PAINTER_SETTINGS_FRAME_COLOR)
        self._settings_frame_width = 0
        self._settings_frame_bottom_width = 0
        self._settings_bottom_edge_blend = True
        self._settings_surface_top_radius = 0.0
        self._settings_surface_radius = 0.0
        self._settings_ui_scale = _configured_ui_scale()

        self._settings_outer_layout = QtWidgets.QVBoxLayout(self)
        self._settings_outer_layout.setSpacing(0)

        self._settings_surface = QtWidgets.QFrame(self)
        self._settings_surface.setObjectName(_SURFACE_OBJECT_NAME)
        self._settings_surface.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_StyledBackground,
            True,
        )
        self._settings_surface_layout = QtWidgets.QVBoxLayout(
            self._settings_surface
        )
        self._settings_surface_layout.setContentsMargins(0, 0, 0, 0)
        self._settings_surface_layout.setSpacing(0)
        self._settings_outer_layout.addWidget(self._settings_surface)

        self.setSettingsFrameWidth(frame_width)

    def settingsSurface(self):
        return self._settings_surface

    def settingsSurfaceLayout(self):
        return self._settings_surface_layout

    def settingsFrameWidth(self) -> int:
        return self._settings_frame_width

    def settingsFrameBottomWidth(self) -> int:
        return self._settings_frame_bottom_width

    def settingsBottomEdgeBlendEnabled(self) -> bool:
        return self._settings_bottom_edge_blend

    def settingsSurfaceRadius(self) -> float:
        return self._settings_surface_radius

    def settingsSurfaceTopRadius(self) -> float:
        return self._settings_surface_top_radius

    def settingsWindowRadius(self) -> float:
        return float(self._settings_theme.radius_window)

    def settingsUiScale(self) -> float:
        return self._settings_ui_scale

    def settingsMetric(self, pixels: float, minimum: int | None = None) -> int:
        if minimum is None:
            minimum = int(round(float(pixels) * _MIN_UI_SCALE))
        return max(
            int(minimum),
            int(round(float(pixels) * self._settings_ui_scale)),
        )

    def setSettingsUiScale(self, scale: float) -> None:
        scale = _bounded_ui_scale(scale)
        changed = abs(scale - self._settings_ui_scale) > 0.0001
        if not changed:
            return
        self._settings_ui_scale = scale
        self._update_surface_stylesheet()
        self.settingsUiScaleChanged.emit(scale)

    def syncSettingsUiScale(self) -> None:
        self.setSettingsUiScale(_configured_ui_scale())

    def setSettingsFrameWidth(self, width: int) -> None:
        width = max(0, int(width))
        self._settings_frame_width = width
        # Painter contributes the final visible bottom pixel outside the
        # client area; embedded previews opt back into the full frame width.
        self._settings_frame_bottom_width = max(0, width - 1)
        self._settings_surface_top_radius = float(
            self._settings_theme.radius_window
        )
        # The inset bottom curve stays concentric with Painter's outer curve.
        self._settings_surface_radius = max(
            0.0,
            float(self._settings_theme.radius_window - width),
        )
        self._update_frame_margins()
        self._update_surface_stylesheet()
        self.update()

    def setSettingsFrameBottomWidth(self, width: int) -> None:
        self._settings_frame_bottom_width = max(0, int(width))
        self._update_frame_margins()
        self.update()

    def setSettingsBottomEdgeBlendEnabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._settings_bottom_edge_blend:
            return
        self._settings_bottom_edge_blend = enabled
        self._update_surface_stylesheet()
        self.update()

    def _update_frame_margins(self) -> None:
        self._settings_outer_layout.setContentsMargins(
            self._settings_frame_width,
            0,
            self._settings_frame_width,
            self._settings_frame_bottom_width,
        )

    def _update_surface_stylesheet(self) -> None:
        section_px = self.settingsMetric(10)
        item_px = self.settingsMetric(13)
        meta_px = self.settingsMetric(11)
        button_px = self.settingsMetric(12)
        bottom_edge = (
            "1px solid transparent"
            if self._settings_bottom_edge_blend
            else "0"
        )
        self._settings_surface.setStyleSheet(
            f"""
            QFrame#{_SURFACE_OBJECT_NAME} {{
                background: {self._settings_theme.surface};
                border: 0;
                border-bottom: {bottom_edge};
                border-top-left-radius: {self._settings_surface_top_radius:g}px;
                border-top-right-radius: {self._settings_surface_top_radius:g}px;
                border-bottom-left-radius: {self._settings_surface_radius:g}px;
                border-bottom-right-radius: {self._settings_surface_radius:g}px;
            }}
            QLabel#RizumSettingsSection {{
                color: {self._settings_theme.text_faint};
                font-size: {section_px}px;
                font-weight: 700;
                letter-spacing: 0.5px;
                background: transparent;
                border: 0;
            }}
            QLabel#RizumSettingsItemName {{
                color: {self._settings_theme.text};
                font-size: {item_px}px;
                font-weight: 500;
                background: transparent;
                border: 0;
            }}
            QLabel#RizumSettingsItemMeta,
            QLabel#RizumSettingsFooterHint,
            QLineEdit#RizumSettingsPathInput {{
                color: {self._settings_theme.text_muted};
                font-size: {meta_px}px;
                font-weight: 500;
            }}
            QLabel#RizumSettingsItemMeta,
            QLabel#RizumSettingsFooterHint {{
                background: transparent;
                border: 0;
            }}
            QLabel#RizumMockText,
            QFrame#RizumSegmentedControl {{
                font-size: {item_px}px;
                font-weight: 500;
            }}
            QLabel#RizumStatusPill,
            QPushButton[variant="dialog-primary"],
            QPushButton[variant="dialog-secondary"] {{
                font-size: {button_px}px;
            }}
            """
        )

    def setStyleSheet(self, stylesheet: str) -> None:
        # Consumers replace the dialog QSS and object name after construction.
        guard = (
            f'{_DIALOG_GUARD_SELECTOR} '
            "{ background: transparent; border: 0; }"
        )
        stylesheet = str(stylesheet or "")
        if _DIALOG_GUARD_SELECTOR not in stylesheet:
            stylesheet = f"{stylesheet}\n{guard}"
        super().setStyleSheet(stylesheet)

    def showEvent(self, event) -> None:
        self.syncSettingsUiScale()
        super().showEvent(event)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if hasattr(self, "_settings_surface") and event.type() in (
            QtCore.QEvent.Type.FontChange,
            QtCore.QEvent.Type.ApplicationFontChange,
        ):
            self.syncSettingsUiScale()

    def paintEvent(self, event) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self._settings_frame_color)
        if self.isWindow():
            painter.fillRect(self.rect(), self._settings_frame_color)
            return

        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.drawRoundedRect(
            QtCore.QRectF(self.rect()),
            self.settingsWindowRadius(),
            self.settingsWindowRadius(),
        )


__all__ = [
    "PAINTER_SETTINGS_FRAME_COLOR",
    "PAINTER_SETTINGS_FRAME_WIDTH",
    "PainterSettingsDialog",
]
