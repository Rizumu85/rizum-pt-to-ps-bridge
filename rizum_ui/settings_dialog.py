"""Shared Painter settings-dialog surface."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from .theme import Theme, default_theme


PAINTER_SETTINGS_FRAME_WIDTH = 2
PAINTER_SETTINGS_FRAME_COLOR = "#f3f3f3"
_SURFACE_OBJECT_NAME = "RizumPainterSettingsSurface"


class PainterSettingsDialog(QtWidgets.QDialog):
    """Painter dialog with a narrow light frame and rounded dark surface."""

    def __init__(
        self,
        parent=None,
        *,
        theme: Theme = default_theme,
        frame_width: int = PAINTER_SETTINGS_FRAME_WIDTH,
    ):
        super().__init__(parent)
        self._settings_theme = theme
        self._settings_frame_color = QtGui.QColor(PAINTER_SETTINGS_FRAME_COLOR)
        self._settings_frame_width = 0
        self._settings_surface_radius = 0.0

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

    def settingsSurfaceRadius(self) -> float:
        return self._settings_surface_radius

    def setSettingsFrameWidth(self, width: int) -> None:
        width = max(0, int(width))
        self._settings_frame_width = width
        self._settings_surface_radius = max(
            0.0,
            float(self._settings_theme.radius_window - width),
        )
        self._settings_outer_layout.setContentsMargins(
            width,
            0,
            width,
            width,
        )
        self._settings_surface.setStyleSheet(
            f"""
            QFrame#{_SURFACE_OBJECT_NAME} {{
                background: {self._settings_theme.surface};
                border: 0;
                border-radius: {self._settings_surface_radius:g}px;
            }}
            """
        )
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), self._settings_frame_color)


__all__ = [
    "PAINTER_SETTINGS_FRAME_COLOR",
    "PAINTER_SETTINGS_FRAME_WIDTH",
    "PainterSettingsDialog",
]
