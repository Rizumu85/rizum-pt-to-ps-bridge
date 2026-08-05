"""Shared Painter settings-dialog surface."""

from __future__ import annotations

import re

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


def _qss_rules_for(stylesheet, object_name):
    if not object_name:
        return
    for selector, body in re.findall(
        r"([^{}]+)\{([^{}]*)\}", stylesheet or ""
    ):
        if any(
            part.strip().endswith(f"#{object_name}")
            for part in selector.split(",")
        ):
            yield body


def _qss_last_declaration(stylesheet, object_name, prop_pattern):
    value = None
    for body in _qss_rules_for(stylesheet, object_name):
        declarations = re.findall(prop_pattern, body)
        if declarations:
            value = declarations[-1].strip()
    return value


def _surface_path(
    rect: QtCore.QRectF,
    top_radius: float,
    bottom_radius: float,
) -> QtGui.QPainterPath:
    tl = tr = max(0.0, float(top_radius))
    bl = br = max(0.0, float(bottom_radius))
    path = QtGui.QPainterPath()
    path.moveTo(rect.left() + tl, rect.top())
    path.lineTo(rect.right() - tr, rect.top())
    if tr > 0:
        path.arcTo(rect.right() - 2 * tr, rect.top(), 2 * tr, 2 * tr, 90.0, -90.0)
    path.lineTo(rect.right(), rect.bottom() - br)
    if br > 0:
        path.arcTo(
            rect.right() - 2 * br,
            rect.bottom() - 2 * br,
            2 * br,
            2 * br,
            0.0,
            -90.0,
        )
    path.lineTo(rect.left() + bl, rect.bottom())
    if bl > 0:
        path.arcTo(rect.left(), rect.bottom() - 2 * bl, 2 * bl, 2 * bl, 270.0, -90.0)
    path.lineTo(rect.left(), rect.top() + tl)
    if tl > 0:
        path.arcTo(rect.left(), rect.top(), 2 * tl, 2 * tl, 180.0, -90.0)
    path.closeSubpath()
    return path


class _PainterSettingsSurface(QtWidgets.QFrame):
    """Dialog-wide surface painting the dark panel as one path.

    Native windows leave their outer frame and clipping to the platform.
    Embedded previews keep the painted Painter-like frame so designers can
    inspect the dialog without changing the production window chrome.
    QSS remains the color source: consumers restyle the surface by appending
    a background rule for its object name, and the last declaration wins.
    """

    def __init__(self, parent=None, *, fallback_color=PAINTER_SETTINGS_FRAME_COLOR):
        super().__init__(parent)
        self._fallback_color = QtGui.QColor(fallback_color)
        self._painted_color = QtGui.QColor(self._fallback_color)
        self._frame_width = 0.0
        self._frame_bottom = 0.0
        self._top_radius = 0.0
        self._bottom_radius = 0.0
        self._delegate_native_chrome = False

    def paintedSurfaceColor(self) -> QtGui.QColor:
        return QtGui.QColor(self._painted_color)

    def setPaintedFrame(
        self,
        width: float,
        bottom: float,
        top_radius: float,
        bottom_radius: float,
    ) -> None:
        # width/bottom are device pixels; radii stay device-independent.
        self._frame_width = float(width)
        self._frame_bottom = float(bottom)
        self._top_radius = float(top_radius)
        self._bottom_radius = float(bottom_radius)
        self.update()

    def setDelegatesNativeChrome(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._delegate_native_chrome:
            return
        self._delegate_native_chrome = enabled
        self.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_OpaquePaintEvent,
            enabled,
        )
        self.update()

    def setStyleSheet(self, stylesheet) -> None:
        super().setStyleSheet(stylesheet)
        # The style sheet only carries the surface color for consumers; with
        # WA_StyledBackground set, Qt would fill the widget rectangle with it
        # and cover the painted frame ring.
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
        self._resolve_painted_color()
        self.update()

    def event(self, event) -> bool:
        result = super().event(event)
        # Polish passes (own or ancestor style sheets) re-arm the attribute.
        if event.type() in (
            QtCore.QEvent.Type.Polish,
            QtCore.QEvent.Type.StyleChange,
        ):
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
        return result

    def _resolve_painted_color(self) -> None:
        color = QtGui.QColor(self._fallback_color)
        declaration = _qss_last_declaration(
            self.styleSheet(),
            self.objectName(),
            r"background(?:-color)?\s*:\s*([^;]+)",
        )
        if declaration is not None:
            candidate = QtGui.QColor(declaration)
            if candidate.isValid():
                color = candidate
        self._painted_color = color

    def paintEvent(self, event) -> None:
        del event
        if not self._painted_color.isValid():
            return
        if self._delegate_native_chrome:
            painter = QtGui.QPainter(self)
            painter.fillRect(self.rect(), self._painted_color)
            return
        dpr = max(1.0, self.devicePixelRatioF())
        inset = self._frame_width / dpr
        rect = QtCore.QRectF(self.rect())
        rect.adjust(inset, 0.0, -inset, -self._frame_bottom / dpr)
        if rect.isEmpty():
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self._painted_color)
        painter.drawPath(
            _surface_path(rect, self._top_radius, self._bottom_radius)
        )


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
    """Painter dialog whose native chrome stays owned by the platform."""

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
        self._settings_frame_bottom_override = None
        self._settings_frame_bottom_width = 0
        self._settings_bottom_edge_extension = True
        self._settings_surface_top_radius = 0.0
        self._settings_surface_radius = 0.0
        self._settings_ui_scale = _configured_ui_scale()

        self._settings_outer_layout = QtWidgets.QVBoxLayout(self)
        self._settings_outer_layout.setContentsMargins(0, 0, 0, 0)
        self._settings_outer_layout.setSpacing(0)

        self._settings_surface = _PainterSettingsSurface(
            self,
            fallback_color=self._settings_theme.surface,
        )
        self._settings_surface.setObjectName(_SURFACE_OBJECT_NAME)
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

    def settingsBottomEdgeExtensionEnabled(self) -> bool:
        return self._settings_bottom_edge_extension

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
        # Frame thickness is specified in device pixels so the painted ring
        # measures the same physical width at every DPR.
        width = max(0, int(width))
        self._settings_frame_width = width
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
        self._settings_frame_bottom_override = max(0, int(width))
        self._update_frame_margins()
        self.update()

    def setSettingsBottomEdgeExtensionEnabled(self, enabled: bool) -> None:
        # Retained for embedded consumers; the painted frame has no QSS
        # bottom edge to extend, so the flag no longer affects rendering.
        self._settings_bottom_edge_extension = bool(enabled)

    def _update_frame_margins(self) -> None:
        if self._settings_frame_bottom_override is None:
            bottom = self._settings_frame_width
        else:
            bottom = self._settings_frame_bottom_override
        self._settings_frame_bottom_width = bottom
        if self.isWindow():
            self._settings_surface_layout.setContentsMargins(0, 0, 0, 0)
            self._settings_surface.setPaintedFrame(0, 0, 0, 0)
            self._settings_surface.setDelegatesNativeChrome(True)
            return

        self._settings_surface.setDelegatesNativeChrome(False)
        # Content insets stay whole DIPs; the painted ring compensates below
        # that so it always lands on exact device pixels.
        self._settings_surface_layout.setContentsMargins(
            self._settings_frame_width,
            0,
            self._settings_frame_width,
            bottom,
        )
        self._settings_surface.setPaintedFrame(
            self._settings_frame_width,
            bottom,
            self._settings_surface_top_radius,
            self._settings_surface_radius,
        )

    def _update_surface_stylesheet(self) -> None:
        section_px = self.settingsMetric(10)
        item_px = self.settingsMetric(13)
        meta_px = self.settingsMetric(11)
        button_px = self.settingsMetric(12)
        # The surface shape is painted in _PainterSettingsSurface.paintEvent;
        # QSS only carries the color so consumers can keep restyling it.
        self._settings_surface.setStyleSheet(
            f"""
            QFrame#{_SURFACE_OBJECT_NAME} {{
                background: {self._settings_theme.surface};
                border: 0;
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
        self._update_frame_margins()
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
        if self.isWindow():
            return

        painter = QtGui.QPainter(self)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self._settings_frame_color)
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
