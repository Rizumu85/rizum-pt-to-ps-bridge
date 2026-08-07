"""Reusable PySide6 widgets for Rizum Painter plugins."""

from __future__ import annotations

from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

COMPACT_DOCK_MIN_WIDTH = 250
COMPACT_DOCK_DEFAULT_WIDTH = COMPACT_DOCK_MIN_WIDTH
COMPACT_DOCK_DEFAULT_HEIGHT = 184
COMPACT_DOCK_OUTER_MARGINS = (3, 0, 3, 3)
COMPACT_DOCK_PANEL_BG = "#2b2b2b"
COMPACT_DOCK_CARD_BG = "#1b1b1b"
COMPACT_DOCK_CARD_RADIUS = 10
FOOTER_BUTTON_HEIGHT = 26
FOOTER_BUTTON_PADDING_X = 8
PAINTER_FOOTER_MARGIN_X = 16
PAINTER_FOOTER_MARGIN_BOTTOM = 14
PAINTER_TITLE_BAR_HEIGHT = 32
PAINTER_WINDOW_CONTENT_RADIUS = 10
PAINTER_WINDOW_CONTENT_BOTTOM_RADIUS = 8


def make_segmented_control(options=None, current=None, parent=None):
    """Create a compact animated single-choice control."""
    from PySide6 import QtCore, QtGui, QtWidgets

    from .theme import default_theme

    base_height = 30
    minimum_height = 23

    class _SegmentedControl(QtWidgets.QFrame):
        currentIndexChanged = QtCore.Signal(int)
        currentDataChanged = QtCore.Signal(object)

        def __init__(self):
            super().__init__(parent)
            self.setObjectName("RizumSegmentedControl")
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
            self.setMouseTracking(True)
            self.setAutoFillBackground(False)
            # Painter styles every QFrame; suppress that fill so the painted
            # end-cap gutter reveals the real parent surface instead.
            self.setStyleSheet(
                "QFrame#RizumSegmentedControl { background: transparent; border: 0; }"
            )
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            self._items = []
            self._current_index = -1
            self._hovered_index = -1
            self._compact_height = base_height
            self._slider_x = 2.0
            self._slider_width = 0.0
            self._animation = None
            self._corner_radius = None
            self._paint_inset = None
            self._theme = {}
            self.setTheme({})
            self.setFixedHeight(base_height)
            self.setItems(options or [])
            if current is not None:
                self.setCurrentData(current, emit=False)

        def setTheme(self, theme):
            theme = theme or {}

            def color(keys, fallback):
                for key in keys:
                    if key in theme:
                        value = theme[key]
                        break
                else:
                    value = fallback
                if isinstance(value, QtGui.QColor):
                    return QtGui.QColor(value)
                text = str(value).strip()
                if text.startswith("rgba(") and text.endswith(")"):
                    parts = [part.strip() for part in text[5:-1].split(",")]
                    if len(parts) == 4:
                        red, green, blue = (int(float(part)) for part in parts[:3])
                        alpha_value = float(parts[3])
                        alpha = (
                            round(alpha_value * 255)
                            if alpha_value <= 1
                            else round(alpha_value)
                        )
                        return QtGui.QColor(
                            red,
                            green,
                            blue,
                            max(0, min(255, alpha)),
                        )
                return QtGui.QColor(text)

            shadow = theme.get("segment_slider_shadow")
            self._theme = {
                "track": color(
                    ("segment_bg", "secondary"),
                    default_theme.surface_control,
                ),
                "slider": color(("segment_slider_bg",), default_theme.accent),
                "active_text": color(
                    ("segment_active_text",),
                    default_theme.accent_text,
                ),
                "muted": color(
                    ("muted", "text_secondary"),
                    default_theme.text_muted,
                ),
                "hover": color(("hover",), default_theme.surface_hover),
                "shadow": None if shadow is None else QtGui.QColor(shadow),
                "slider_border": (
                    None
                    if theme.get("segment_slider_border") is None
                    else color(("segment_slider_border",), default_theme.border)
                ),
            }
            self.update()

        def setCornerRadius(self, radius):
            """Override the painted track radius while retaining scale support."""
            self._corner_radius = max(0.0, float(radius))
            self.update()

        def setPaintInset(self, inset):
            """Keep antialiased end caps clear of the widget paint boundary."""
            self._paint_inset = max(0.5, float(inset))
            self.update()

        def getSliderX(self):
            return self._slider_x

        def setSliderX(self, value):
            self._slider_x = float(value)
            self.update()

        def getSliderWidth(self):
            return self._slider_width

        def setSliderWidth(self, value):
            self._slider_width = float(value)
            self.update()

        sliderX = QtCore.Property(float, getSliderX, setSliderX)
        sliderWidth = QtCore.Property(float, getSliderWidth, setSliderWidth)

        def _scale(self):
            return self._compact_height / float(base_height)

        def _scaled(self, value, floor=None):
            scaled_value = int(round(value * self._scale()))
            if floor is None:
                floor = int(value * 0.75 + 0.5)
            return max(floor, scaled_value)

        def _device_geometry(self):
            dpr = max(1.0, float(self.devicePixelRatioF()))
            window = self.window()
            origin = (
                self.mapTo(window, QtCore.QPoint(0, 0))
                if window is not None
                else QtCore.QPoint(0, 0)
            )

            def aligned_axis(offset, extent):
                start = int(float(offset) * dpr + 0.5)
                end = int(float(offset + extent) * dpr + 0.5)
                return start / dpr - offset, end / dpr - offset

            left, right = aligned_axis(origin.x(), self.width())
            top, bottom = aligned_axis(origin.y(), self.height())
            return dpr, QtCore.QRectF(left, top, right - left, bottom - top)

        @staticmethod
        def _device_aligned_inset(value, dpr):
            return max(1, int(float(value) * dpr + 0.5)) / dpr

        def _font(self):
            font = QtGui.QFont(self.font())
            font.setWeight(QtGui.QFont.Weight.Medium)
            return font

        def _base_widths(self):
            metrics = QtGui.QFontMetrics(self._font())
            padding = self._scaled(12, 9)
            minimum = self._scaled(34, 26)
            return [
                max(minimum, metrics.horizontalAdvance(label) + padding * 2)
                for label, _data in self._items
            ]

        def _segment_rects(self):
            if not self._items:
                return []
            dpr, paint_rect = self._device_geometry()
            inset = self._device_aligned_inset(self._scaled(2, 2), dpr)
            widths = [float(width) for width in self._base_widths()]
            available = max(0.0, paint_rect.width() - inset * 2.0)
            extra = max(0.0, available - sum(widths)) / len(widths)
            rects = []
            x = paint_rect.left() + inset
            for index, width in enumerate(widths):
                segment_width = width + extra
                if index == len(widths) - 1:
                    segment_width = max(0.0, paint_rect.right() - inset - x)
                rects.append(
                    QtCore.QRectF(
                        x,
                        paint_rect.top() + inset,
                        segment_width,
                        max(0.0, paint_rect.height() - inset * 2.0),
                    )
                )
                x += segment_width
            return rects

        def _target_slider_rect(self):
            rects = self._segment_rects()
            if 0 <= self._current_index < len(rects):
                return rects[self._current_index]
            return QtCore.QRectF()

        def _stop_animation(self):
            if self._animation is not None:
                self._animation.stop()
                self._animation = None

        def _sync_slider(self):
            self._stop_animation()
            target = self._target_slider_rect()
            self._slider_x = target.x()
            self._slider_width = target.width()
            self.update()

        def _animate_slider(self):
            target = self._target_slider_rect()
            self._stop_animation()
            group = QtCore.QParallelAnimationGroup(self)
            easing = (
                QtCore.QEasingCurve.Type.OutCubic
                if self._current_index in (0, len(self._items) - 1)
                else QtCore.QEasingCurve.Type.OutBack
            )
            for prop, start, end in (
                (b"sliderX", self._slider_x, target.x()),
                (b"sliderWidth", self._slider_width, target.width()),
            ):
                animation = QtCore.QPropertyAnimation(self, prop, group)
                animation.setDuration(220)
                animation.setStartValue(start)
                animation.setEndValue(end)
                animation.setEasingCurve(easing)
                group.addAnimation(animation)
            self._animation = group
            group.start()

        def setItems(self, next_options):
            previous_data = self.currentData()
            items = []
            for option in next_options or []:
                if isinstance(option, (tuple, list)) and len(option) >= 2:
                    label, data = option[0], option[1]
                else:
                    label = data = option
                items.append((str(label), data))
            self._items = items
            self._current_index = self.findData(previous_data)
            if self._current_index < 0 and self._items:
                self._current_index = 0
            self.setAccessibleName(" / ".join(label for label, _ in items))
            self.refreshMetrics()

        def count(self):
            return len(self._items)

        def findData(self, data):
            for index, (_label, item_data) in enumerate(self._items):
                if item_data == data:
                    return index
            return -1

        def currentIndex(self):
            return self._current_index

        def currentData(self):
            if 0 <= self._current_index < len(self._items):
                return self._items[self._current_index][1]
            return None

        def currentText(self):
            if 0 <= self._current_index < len(self._items):
                return self._items[self._current_index][0]
            return ""

        def setCurrentIndex(
            self,
            index,
            *,
            animate=False,
            emit=True,
        ):
            if not self._items:
                index = -1
            else:
                index = max(0, min(int(index), len(self._items) - 1))
            if index == self._current_index:
                self._sync_slider()
                return
            self._current_index = index
            if animate and self.isVisible():
                self._animate_slider()
            else:
                self._sync_slider()
            if emit:
                self.currentIndexChanged.emit(index)
                self.currentDataChanged.emit(self.currentData())

        def setCurrentData(self, data, *, animate=False, emit=True):
            index = self.findData(data)
            if index >= 0:
                self.setCurrentIndex(
                    index,
                    animate=animate,
                    emit=emit,
                )

        def setCompactHeight(self, height):
            """Scale the fixed frame and all painted internal geometry."""
            self._compact_height = max(minimum_height, int(round(height)))
            self.setFixedHeight(self._compact_height)
            self.refreshMetrics()

        def refreshMetrics(self):
            self.setMinimumWidth(self.sizeHint().width())
            self.updateGeometry()
            self._sync_slider()

        def sizeHint(self):
            inset = self._scaled(2, 2)
            return QtCore.QSize(
                sum(self._base_widths()) + inset * 2,
                self._compact_height,
            )

        def minimumSizeHint(self):
            return self.sizeHint()

        def _index_at(self, point):
            for index, rect in enumerate(self._segment_rects()):
                if rect.contains(point):
                    return index
            return -1

        def mouseMoveEvent(self, event):
            hovered = self._index_at(event.position())
            if hovered != self._hovered_index:
                self._hovered_index = hovered
                self.update()
            super().mouseMoveEvent(event)

        def leaveEvent(self, event):
            self._hovered_index = -1
            self.update()
            super().leaveEvent(event)

        def mousePressEvent(self, event):
            if (
                self.isEnabled()
                and event.button() == QtCore.Qt.MouseButton.LeftButton
            ):
                index = self._index_at(event.position())
                if index >= 0:
                    self.setCurrentIndex(index, animate=True)
                    event.accept()
                    return
            super().mousePressEvent(event)

        def keyPressEvent(self, event):
            key = event.key()
            if key in (
                QtCore.Qt.Key.Key_Left,
                QtCore.Qt.Key.Key_Up,
            ):
                self.setCurrentIndex(self._current_index - 1, animate=True)
                event.accept()
                return
            if key in (
                QtCore.Qt.Key.Key_Right,
                QtCore.Qt.Key.Key_Down,
            ):
                self.setCurrentIndex(self._current_index + 1, animate=True)
                event.accept()
                return
            if key == QtCore.Qt.Key.Key_Home:
                self.setCurrentIndex(0, animate=True)
                event.accept()
                return
            if key == QtCore.Qt.Key.Key_End:
                self.setCurrentIndex(len(self._items) - 1, animate=True)
                event.accept()
                return
            super().keyPressEvent(event)

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self._sync_slider()

        def changeEvent(self, event):
            super().changeEvent(event)
            if event.type() in (
                QtCore.QEvent.Type.FontChange,
                QtCore.QEvent.Type.ApplicationFontChange,
            ):
                self.refreshMetrics()

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(
                QtGui.QPainter.RenderHint.Antialiasing,
                True,
            )
            if not self.isEnabled():
                painter.setOpacity(0.45)

            if self._corner_radius is None:
                outer_radius = float(self._scaled(7, 5))
                slider_radius = float(self._scaled(6, 5))
            else:
                outer_radius = float(
                    self._scaled(
                        self._corner_radius,
                        int(self._corner_radius * 0.75 + 0.5),
                    )
                )
                slider_base = max(0.0, self._corner_radius - 1.0)
                slider_radius = float(
                    self._scaled(slider_base, int(slider_base * 0.75 + 0.5))
                )
            edge_inset = (
                1.0
                if self._paint_inset is None
                else max(0.5, self._paint_inset * self._scale())
            )
            dpr, paint_rect = self._device_geometry()
            edge_inset = self._device_aligned_inset(edge_inset, dpr)
            outer = paint_rect.adjusted(
                edge_inset,
                edge_inset,
                -edge_inset,
                -edge_inset,
            )
            track = QtGui.QColor(self._theme["track"])
            if self.hasFocus():
                track = track.lighter(112)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(track)
            painter.drawRoundedRect(outer, outer_radius, outer_radius)

            rects = self._segment_rects()
            if (
                0 <= self._hovered_index < len(rects)
                and self._hovered_index != self._current_index
            ):
                painter.setBrush(self._theme["hover"])
                painter.drawRoundedRect(
                    rects[self._hovered_index],
                    slider_radius,
                    slider_radius,
                )

            slider = QtCore.QRectF(
                self._slider_x,
                rects[0].top() if rects else 0.0,
                self._slider_width,
                rects[0].height() if rects else 0.0,
            )
            shadow = self._theme["shadow"]
            if shadow is not None:
                painter.setBrush(shadow)
                painter.drawRoundedRect(
                    slider.translated(0, self._scaled(1, 1)),
                    slider_radius,
                    slider_radius,
                )
            painter.setBrush(self._theme["slider"])
            painter.drawRoundedRect(
                slider,
                slider_radius,
                slider_radius,
            )
            if self._theme["slider_border"] is not None:
                painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                painter.setPen(QtGui.QPen(self._theme["slider_border"], 1))
                painter.drawRoundedRect(
                    slider.adjusted(0.5, 0.5, -0.5, -0.5),
                    slider_radius,
                    slider_radius,
                )
                painter.setPen(QtCore.Qt.PenStyle.NoPen)

            painter.setFont(self._font())
            for index, ((label, _data), rect) in enumerate(
                zip(self._items, rects)
            ):
                painter.setPen(
                    self._theme["active_text"]
                    if index == self._current_index
                    else self._theme["muted"]
                )
                painter.drawText(
                    rect,
                    QtCore.Qt.AlignmentFlag.AlignCenter,
                    label,
                )

            painter.end()

    return _SegmentedControl()


def _svg_with_breathing_room(source):
    """Give 24px stroke icons a small viewBox margin so strokes are not clipped."""
    source = source.replace('viewBox="0 0 24 24"', 'viewBox="-2 -2 28 28"')
    source = source.replace("viewBox='0 0 24 24'", "viewBox='-2 -2 28 28'")
    return source


def _is_qt_object_alive(obj):
    if obj is None:
        return False
    try:
        import shiboken6

        return shiboken6.isValid(obj)
    except Exception:
        try:
            obj.objectName()
        except RuntimeError:
            return False
        except Exception:
            return False
        return True


def install_compact_tooltip(widget, text):
    """Install a compact tooltip with deterministic, UI-scale-aware metrics."""
    if not text:
        widget.setToolTip("")
        return widget

    from PySide6 import QtCore, QtGui, QtWidgets

    base_font_px = 14
    base_margin_x = 12
    base_margin_y = 7
    base_radius = 7

    def scaled(value, scale):
        return max(int(round(value * 0.75)), int(round(value * scale)))

    def tooltip_font(source_font, scale):
        font = QtGui.QFont(source_font)
        font.setPixelSize(scaled(base_font_px, scale))
        return font

    def tooltip_label_stylesheet(font):
        family = font.family().replace("\\", "\\\\").replace('"', '\\"')
        style = "italic" if font.italic() else "normal"
        return (
            "background: transparent; border: 0; color: #e0e0e0; "
            f'font-family: "{family}"; font-size: {font.pixelSize()}px; '
            f"font-weight: {font.weight()}; font-style: {style};"
        )

    class _CompactTooltip(QtWidgets.QFrame):
        def __init__(self, owner):
            flags = (
                QtCore.Qt.WindowType.ToolTip
                | QtCore.Qt.WindowType.FramelessWindowHint
                | QtCore.Qt.WindowType.NoDropShadowWindowHint
            )
            super().__init__(None, flags)
            self._owner = owner
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
            self.setAutoFillBackground(False)
            self.setObjectName("RizumCompactToolTip")
            self._scale_override = None
            self._scale = 1.0
            self._radius = 5
            layout = QtWidgets.QHBoxLayout(self)
            layout.setContentsMargins(9, 5, 9, 5)
            layout.setSpacing(0)
            self._layout = layout
            self._label = QtWidgets.QLabel(text)
            self._label.setObjectName("RizumCompactToolTipLabel")
            self._label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
            layout.addWidget(self._label)

        def setText(self, next_text):
            self._label.setText(next_text)
            self.adjustSize()

        def setScale(self, scale):
            self._scale_override = None if scale is None else max(0.75, float(scale))
            self.polishMetrics()

        def scale(self):
            return self._scale

        def polishMetrics(self):
            self._scale = self._scale_override if self._scale_override is not None else 1.0
            font = tooltip_font(self._owner.font(), self._scale)
            self._label.setFont(font)
            # Painter's application stylesheet assigns a generic QLabel font.
            # A local declaration is required or it silently replaces the
            # runtime pixel size set above when the tooltip is polished.
            self._label.setStyleSheet(tooltip_label_stylesheet(font))
            self._radius = scaled(base_radius, self._scale)
            self._layout.setContentsMargins(
                scaled(base_margin_x, self._scale),
                scaled(base_margin_y, self._scale),
                scaled(base_margin_x, self._scale),
                scaled(base_margin_y, self._scale),
            )
            self.updateGeometry()
            self.update()

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
            painter.setPen(QtGui.QPen(QtGui.QColor("#414141"), 1))
            painter.setBrush(QtGui.QColor("#1b1b1b"))
            painter.drawRoundedRect(rect, self._radius, self._radius)
            painter.end()

    class _CompactTooltipFilter(QtCore.QObject):
        def __init__(self, owner):
            super().__init__(owner)
            self._owner = owner
            self._tooltip = None
            self._text = str(text)
            self._scale_override = None
            self._last_global_pos = None
            self._timer = QtCore.QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.setInterval(420)
            self._timer.timeout.connect(self._show_delayed)

        def _ensure_tooltip(self):
            if _is_qt_object_alive(self._tooltip):
                return self._tooltip
            self._tooltip = _CompactTooltip(self._owner)
            self._tooltip.setScale(self._scale_override)
            return self._tooltip

        def _hide_tooltip(self):
            self._timer.stop()
            if _is_qt_object_alive(self._tooltip):
                self._tooltip.hide()

        def setScale(self, scale):
            self._scale_override = None if scale is None else max(0.75, float(scale))
            if _is_qt_object_alive(self._tooltip):
                self._tooltip.setScale(self._scale_override)
                self._tooltip.adjustSize()

        def setText(self, next_text):
            self._text = str(next_text or "")
            if not self._text:
                self._hide_tooltip()
            elif _is_qt_object_alive(self._tooltip):
                self._tooltip.setText(self._text)

        def refreshMetrics(self):
            if _is_qt_object_alive(self._tooltip):
                self._tooltip.setScale(self._scale_override)
                self._tooltip.adjustSize()

        def _event_global_pos(self, obj, event):
            if hasattr(event, "globalPosition"):
                return event.globalPosition().toPoint()
            if hasattr(event, "globalPos"):
                return event.globalPos()
            try:
                return obj.mapToGlobal(event.position().toPoint())
            except Exception:
                try:
                    return obj.mapToGlobal(event.pos())
                except Exception:
                    return QtGui.QCursor.pos()

        def _schedule_tooltip(self, global_pos):
            self._last_global_pos = QtCore.QPoint(global_pos)
            if _is_qt_object_alive(self._tooltip) and self._tooltip.isVisible():
                self._show_tooltip(self._last_global_pos)
                return
            self._timer.start()

        def _show_delayed(self):
            if not _is_qt_object_alive(self._owner) or not self._owner.underMouse():
                return
            self._show_tooltip(self._last_global_pos or QtGui.QCursor.pos())

        def _show_tooltip(self, global_pos):
            tooltip = self._ensure_tooltip()
            tooltip.polishMetrics()
            tooltip.setText(self._text)
            tooltip.adjustSize()
            scale = tooltip.scale()
            offset_x = scaled(8, scale)
            offset_y = scaled(14, scale)
            screen_pad = scaled(4, scale)
            pos = QtCore.QPoint(global_pos) + QtCore.QPoint(offset_x, offset_y)
            screen = QtGui.QGuiApplication.screenAt(global_pos)
            if screen is None:
                screen = QtWidgets.QApplication.primaryScreen()
            if screen is not None:
                bounds = screen.availableGeometry()
                if pos.x() + tooltip.width() > bounds.right():
                    pos.setX(
                        max(bounds.left(), bounds.right() - tooltip.width() - screen_pad)
                    )
                if pos.y() + tooltip.height() > bounds.bottom():
                    pos.setY(
                        max(
                            bounds.top(),
                            global_pos.y() - tooltip.height() - scaled(12, scale),
                        )
                    )
            tooltip.move(pos)
            tooltip.show()

        def eventFilter(self, obj, event):
            event_type = event.type()
            if event_type == QtCore.QEvent.Type.ToolTip:
                return True
            if event_type in (
                QtCore.QEvent.Type.Enter,
                QtCore.QEvent.Type.HoverEnter,
            ):
                self._schedule_tooltip(self._event_global_pos(obj, event))
            elif event_type in (
                QtCore.QEvent.Type.MouseMove,
                QtCore.QEvent.Type.HoverMove,
            ):
                self._last_global_pos = self._event_global_pos(obj, event)
                if _is_qt_object_alive(self._tooltip) and self._tooltip.isVisible():
                    self._show_tooltip(self._last_global_pos)
            if event_type in (
                QtCore.QEvent.Type.Leave,
                QtCore.QEvent.Type.HoverLeave,
                QtCore.QEvent.Type.MouseButtonPress,
                QtCore.QEvent.Type.Hide,
                QtCore.QEvent.Type.Destroy,
                QtCore.QEvent.Type.WindowDeactivate,
            ):
                self._hide_tooltip()
            elif event_type in (
                QtCore.QEvent.Type.FontChange,
                QtCore.QEvent.Type.ApplicationFontChange,
            ):
                self.refreshMetrics()
            return False

    widget.setToolTip("")
    widget.setMouseTracking(True)
    widget.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
    previous = getattr(widget, "_rizum_compact_tooltip_filter", None)
    if previous is not None:
        widget.removeEventFilter(previous)
    tooltip_filter = _CompactTooltipFilter(widget)
    widget.installEventFilter(tooltip_filter)
    widget._rizum_compact_tooltip_filter = tooltip_filter
    widget.setCompactTooltipScale = tooltip_filter.setScale
    widget.setCompactTooltipText = tooltip_filter.setText
    widget.refreshCompactTooltip = tooltip_filter.refreshMetrics
    return widget


class Card:
    """Factory for a compact framed surface."""

    @staticmethod
    def create(parent=None):
        from PySide6 import QtWidgets

        frame = QtWidgets.QFrame(parent)
        frame.setObjectName("RizumCard")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        return frame


class FieldLabel:
    """Factory for compact form labels."""

    @staticmethod
    def create(text, parent=None):
        from PySide6 import QtWidgets

        label = QtWidgets.QLabel(text, parent)
        label.setObjectName("RizumFieldLabel")
        return label


class SectionHeader:
    """A title/subtitle pair for dense plugin panels."""

    def __new__(cls, title, subtitle="", parent=None):
        from PySide6 import QtWidgets

        widget = QtWidgets.QWidget(parent)
        widget.setObjectName("RizumSectionHeader")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("RizumSectionTitle")
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QtWidgets.QLabel(subtitle)
            subtitle_label.setProperty("muted", True)
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        return widget


class ActionButton:
    """Primary or secondary button factory."""

    @staticmethod
    def create(text, variant="secondary", parent=None):
        from PySide6 import QtWidgets

        button = QtWidgets.QPushButton(text, parent)
        if variant != "secondary":
            button.setProperty("variant", variant)
        button.setMinimumHeight(32)

        def refresh_layout(minimum=68, maximum=140):
            set_compact_footer_button_width(
                button,
                compact_footer_button_width(button, minimum=minimum, maximum=maximum),
            )

        button.refreshLayout = refresh_layout
        return button


class PillButton:
    """Compact rounded button for secondary toolbar actions."""

    @staticmethod
    def create(text, parent=None):
        from PySide6 import QtWidgets

        button = QtWidgets.QPushButton(text, parent)
        button.setProperty("variant", "ghost")
        button.setMinimumSize(32, 32)
        return button


class StatusPill:
    """Small colored status label."""

    def __new__(cls, text, tone="neutral", parent=None):
        from PySide6 import QtWidgets

        label = QtWidgets.QLabel(text, parent)
        label.setObjectName("RizumStatusPill")
        colors = {
            "good": ("#0d3326", "#37c98b"),
            "info": ("#102b52", "#6aa8ff"),
            "warn": ("#3a2912", "#d69a38"),
            "bad": ("#3b171b", "#ff6f7d"),
            "neutral": ("#2a2a2a", "#9e9e9e"),
        }
        bg, fg = colors.get(tone, colors["neutral"])
        label.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 8px; padding: 5px 10px;"
        )
        return label


def make_dock_action_button(label, icon_name, primary=False, tooltip="", parent=None):
    """Create the compact vertical dock action button from the pro dock reference."""
    from PySide6 import QtCore, QtGui, QtWidgets

    class _DockActionButton(QtWidgets.QPushButton):
        def __init__(self):
            super().__init__("", parent)
            self.setObjectName("RizumDockActionButton")
            self.setProperty("primary", bool(primary))
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.setFixedHeight(48)
            self.setMinimumWidth(70)
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            self._visual_scale = 1.0
            self._animation = None

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

            base_rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
            scale = max(0.1, min(1.0, self._visual_scale))
            rect = QtCore.QRectF(
                base_rect.center().x() - base_rect.width() * scale / 2,
                base_rect.center().y() - base_rect.height() * scale / 2,
                base_rect.width() * scale,
                base_rect.height() * scale,
            )

            is_primary = bool(self.property("primary"))
            is_hovered = self.underMouse()
            if is_primary:
                fill = QtGui.QColor("#ffffff")
                if is_hovered:
                    fill = QtGui.QColor("#ffffff")
                    fill.setAlphaF(0.9)
                border = QtGui.QColor(0, 0, 0, 0)
                text_color = QtGui.QColor("#1b1b1b")
            else:
                fill = QtGui.QColor("#262626" if is_hovered else "#222222")
                border = QtGui.QColor(0, 0, 0, 0)
                text_color = QtGui.QColor("#e0e0e0" if is_hovered else "#9e9e9e")

            if self.isDown():
                fill = QtGui.QColor(255, 255, 255, 8) if not is_primary else QtGui.QColor("#dedede")

            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            for offset_y, spread, alpha in ((3, 1, 34), (7, 4, 18), (10, 7, 8)):
                shadow_rect = rect.adjusted(-spread, -spread, spread, spread).translated(0, offset_y)
                painter.setBrush(QtGui.QColor(0, 0, 0, alpha))
                painter.drawRoundedRect(shadow_rect, 12 + spread, 12 + spread)

            painter.setPen(QtGui.QPen(border, 1))
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, 12, 12)

            icon_size = max(14, min(20, int(round(18 * scale))))
            icon_gap = max(3, int(round(4 * scale)))
            label_height = 12
            content_height = icon_size + icon_gap + label_height
            content_top = rect.top() + (rect.height() - content_height) / 2 - 1
            icon_pixmap = _render_svg_pixmap(
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
            scaled_label_height = max(10, int(round(label_height * scale)))
            text_rect = QtCore.QRectF(
                rect.left() + 5,
                icon_y + icon_size + icon_gap,
                rect.width() - 10,
                scaled_label_height,
            )
            painter.drawText(
                text_rect,
                QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter,
                label,
            )
            painter.end()

    button = _DockActionButton()
    if tooltip:
        install_compact_tooltip(button, tooltip)
    return button


def make_dock_actions_panel(actions=None, width=260, parent=None):
    """Create the three-action dock panel matching `dock_actions_pro_v3.html`."""
    from PySide6 import QtCore, QtGui, QtWidgets

    class _DockActionsPanel(QtWidgets.QFrame):
        def __init__(self):
            super().__init__(parent)
            self.setObjectName("RizumDockActionsPanel")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor("#1b1b1b"))
            painter.drawRoundedRect(rect, 10, 10)
            painter.end()

    panel = _DockActionsPanel()
    panel.setFixedSize(width, 78)
    panel.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Fixed,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    panel.setStyleSheet(
        """
QPushButton#RizumDockActionButton {
    background: transparent;
    border: 0;
}
"""
    )
    layout = QtWidgets.QHBoxLayout(panel)
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(8)

    action_items = actions or [
        {
            "label": "Export",
            "icon": "action-export.svg",
            "primary": True,
            "tooltip": "Export selected",
        },
        {
            "label": "Bridge",
            "icon": "action-bridge.svg",
            "primary": False,
            "tooltip": "Open bridge app",
        },
        {
            "label": "Settings",
            "icon": "action-sun.svg",
            "primary": False,
            "tooltip": "Settings",
        },
    ]

    buttons = []
    for action in action_items:
        button = make_dock_action_button(
            action.get("label", ""),
            action.get("icon", ""),
            primary=bool(action.get("primary", False)),
            tooltip=action.get("tooltip", ""),
        )
        buttons.append(button)
        layout.addWidget(button)

    panel._rizum_action_buttons = buttons
    panel.actionButtons = lambda: list(buttons)
    panel.refreshLayout = lambda: panel.updateGeometry()
    return panel


def compact_progress_width(status_text="", meta_text="", widget=None, minimum=320, maximum=None):
    """Return a progress panel width that survives localized status/meta text."""
    width = max(
        compact_text_width(status_text, widget=widget, minimum=0, padding=92),
        compact_text_width(meta_text, widget=widget, minimum=0, padding=32),
        minimum,
    )
    if maximum is not None:
        width = min(width, maximum)
    return int(width)


def make_progress_panel(
    status_text="Exporting Textures",
    value=0,
    meta_text="",
    cancel_button=None,
    show_cancel=False,
    minimum_width=320,
    maximum_width=420,
    parent=None,
):
    """Create a compact pro progress body for plugin-owned panels."""
    from PySide6 import QtCore, QtGui, QtWidgets

    class _ProgressTrack(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.setObjectName("RizumProgressTrack")
            self.setFixedHeight(4)
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            self._value = 0.0
            self._animation = None

        def getValue(self):
            return self._value

        def setValue(self, next_value):
            self._value = max(0.0, min(100.0, float(next_value)))
            self.update()

        progressValue = QtCore.Property(float, getValue, setValue)

        def setProgress(self, next_value, animated=True):
            next_value = max(0.0, min(100.0, float(next_value)))
            if self._animation is not None:
                self._animation.stop()
                self._animation = None
            if not animated:
                self.setValue(next_value)
                return
            animation = QtCore.QPropertyAnimation(self, b"progressValue", self)
            animation.setDuration(400)
            animation.setStartValue(self._value)
            animation.setEndValue(next_value)
            animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            self._animation = animation
            animation.start()

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            rect = QtCore.QRectF(0, 0, self.width(), self.height())
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(255, 255, 255, 20))
            painter.drawRoundedRect(rect, 2, 2)

            fill_width = rect.width() * (self._value / 100.0)
            if fill_width <= 0:
                painter.end()
                return
            fill_rect = QtCore.QRectF(0, 0, fill_width, rect.height())
            painter.setBrush(QtGui.QColor("#ffffff"))
            painter.drawRoundedRect(fill_rect, 2, 2)
            painter.setBrush(QtGui.QColor(255, 255, 255, 38))
            glow_width = min(fill_width, 8)
            glow_rect = QtCore.QRectF(max(0.0, fill_width - glow_width), 0, glow_width, rect.height())
            painter.drawRoundedRect(glow_rect, 2, 2)
            painter.end()

    panel = QtWidgets.QWidget(parent)
    panel.setObjectName("RizumProgressPanel")
    panel.setStyleSheet(
        """
QWidget#RizumProgressPanel,
QWidget#RizumProgressPanel QWidget {
    background: transparent;
    border: 0;
}
QLabel#RizumProgressStatus {
    color: #e0e0e0;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
    border: 0;
}
QLabel#RizumProgressPercent {
    color: #666666;
    font-size: 11px;
    font-weight: 700;
    background: transparent;
    border: 0;
}
QLabel#RizumProgressMeta {
    color: #666666;
    font-size: 11px;
    font-weight: 500;
    background: transparent;
    border: 0;
}
"""
    )
    layout = QtWidgets.QVBoxLayout(panel)
    layout.setContentsMargins(16, 20, 16, 20 if not show_cancel else 0)
    layout.setSpacing(12)

    status_row = QtWidgets.QWidget()
    status_layout = QtWidgets.QHBoxLayout(status_row)
    status_layout.setContentsMargins(0, 0, 0, 0)
    status_layout.setSpacing(10)

    status_label = QtWidgets.QLabel(status_text)
    status_label.setObjectName("RizumProgressStatus")
    status_label.setWordWrap(True)
    status_label.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Preferred,
    )
    percent_label = QtWidgets.QLabel()
    percent_label.setObjectName("RizumProgressPercent")
    percent_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
    status_layout.addWidget(status_label, 1)
    status_layout.addWidget(percent_label)
    layout.addWidget(status_row)

    track = _ProgressTrack()
    layout.addWidget(track)

    meta_label = QtWidgets.QLabel(meta_text)
    meta_label.setObjectName("RizumProgressMeta")
    meta_label.setWordWrap(True)
    layout.addWidget(meta_label)

    if show_cancel:
        footer = QtWidgets.QWidget()
        footer.setObjectName("RizumTransparent")
        footer_layout = QtWidgets.QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 8, 0, 0)
        footer_layout.setSpacing(0)
        footer_layout.addStretch(1)
        if cancel_button is None:
            cancel_button = ActionButton.create("Cancel", "dialog-secondary")
            set_compact_footer_button_width(cancel_button, compact_footer_button_width(cancel_button, minimum=72))
        footer_layout.addWidget(cancel_button)
        layout.addWidget(footer)

    def update_percent(next_value):
        percent_label.setText(f"{int(round(max(0.0, min(100.0, float(next_value)))))}%")

    def refresh_layout(next_status=None, next_meta=None):
        if next_status is not None:
            status_label.setText(next_status)
        if next_meta is not None:
            meta_label.setText(next_meta)
        percent_label.setMinimumWidth(compact_text_width("100%", widget=percent_label, minimum=32, padding=2))
        panel.setMinimumWidth(
            compact_progress_width(
                status_label.text(),
                meta_label.text(),
                widget=panel,
                minimum=minimum_width,
                maximum=maximum_width,
            )
        )
        try:
            panel.updateGeometry()
        except Exception:
            pass

    def set_progress(next_value, next_status=None, next_meta=None, animated=True):
        update_percent(next_value)
        if next_status is not None:
            status_label.setText(next_status)
        if next_meta is not None:
            meta_label.setText(next_meta)
        refresh_layout()
        track.setProgress(next_value, animated=animated)

    panel._rizum_status_label = status_label
    panel._rizum_percent_label = percent_label
    panel._rizum_meta_label = meta_label
    panel._rizum_progress_track = track
    panel.setProgress = set_progress
    panel.refreshLayout = refresh_layout
    panel.value = track.getValue
    set_progress(value, status_text, meta_text, animated=False)
    return panel


def make_action_row(*buttons, parent=None):
    """Create a right-aligned action row."""
    from PySide6 import QtWidgets

    widget = QtWidgets.QWidget(parent)
    widget.setObjectName("RizumActionRow")
    layout = QtWidgets.QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addStretch(1)
    for button in buttons:
        layout.addWidget(button)
    return widget


def build_compact_dock_stylesheet():
    """Return styles learned from live Painter dock panels."""
    return f"""
QWidget#RizumCompactDockSurface {{
    background: {COMPACT_DOCK_PANEL_BG};
}}
QFrame#RizumCompactDockCard,
QFrame#RizumCompactDockCard QWidget#RizumTransparent {{
    background: {COMPACT_DOCK_CARD_BG};
    border: 0;
    border-radius: {COMPACT_DOCK_CARD_RADIUS}px;
}}
QFrame#RizumCompactDockCard QPushButton[compactFooter="true"] {{
    min-width: 0;
    padding-left: {FOOTER_BUTTON_PADDING_X}px;
    padding-right: {FOOTER_BUTTON_PADDING_X}px;
}}
"""


def apply_compact_dock_surface(widget):
    """Apply Painter-like dock surface palette and local styles."""
    from PySide6 import QtGui

    widget.setObjectName("RizumCompactDockSurface")
    widget.setStyleSheet(widget.styleSheet() + build_compact_dock_stylesheet())
    palette = widget.palette()
    panel_color = QtGui.QColor(COMPACT_DOCK_PANEL_BG)
    palette.setColor(QtGui.QPalette.ColorRole.Window, panel_color)
    palette.setColor(QtGui.QPalette.ColorRole.Base, panel_color)
    widget.setPalette(palette)
    widget.setAutoFillBackground(True)


def make_compact_dock_layout(widget):
    """Create the outer layout for compact Painter dock content."""
    from PySide6 import QtWidgets

    layout = QtWidgets.QVBoxLayout(widget)
    layout.setContentsMargins(*COMPACT_DOCK_OUTER_MARGINS)
    layout.setSpacing(0)
    return layout


def make_compact_dock_card(parent=None):
    """Create the dark rounded card used inside compact dock panels."""
    from PySide6 import QtWidgets

    card = QtWidgets.QFrame(parent)
    card.setObjectName("RizumCompactDockCard")
    card.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Expanding,
    )
    layout = QtWidgets.QVBoxLayout(card)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    return card


def set_compact_footer_button_width(button, width, height=FOOTER_BUTTON_HEIGHT):
    """Set a footer button's final visual width despite Qt padding math."""
    content_width = max(0, width - (FOOTER_BUTTON_PADDING_X * 2 + 2))
    button.setProperty("compactFooter", True)
    button.setFixedSize(width, height)
    button.setMinimumSize(width, height)
    button.setMaximumSize(width, height)
    button.setStyleSheet(
        f"min-width: {content_width}px; max-width: {content_width}px; "
        f"padding-left: {FOOTER_BUTTON_PADDING_X}px; "
        f"padding-right: {FOOTER_BUTTON_PADDING_X}px;"
    )
    try:
        button.style().unpolish(button)
        button.style().polish(button)
    except Exception:
        pass


def update_compact_field_row(row_widget, label_width=None, control_width=None):
    """Refresh fixed field-row metrics after a runtime font change."""
    try:
        label = row_widget._rizum_label
    except AttributeError:
        label = None
    try:
        control = row_widget._rizum_control
    except AttributeError:
        control = None

    if label is not None and label_width is not None:
        label.setFixedWidth(int(label_width))
    if control is not None and control_width is not None:
        control.setFixedWidth(int(control_width))
    try:
        row_widget.updateGeometry()
    except Exception:
        pass


def compact_text_width(text, widget=None, minimum=0, maximum=None, padding=0):
    """Return a clamped text width using the active Qt font metrics."""
    from PySide6 import QtCore, QtGui, QtWidgets

    if widget is not None:
        font = widget.font()
    else:
        app = QtWidgets.QApplication.instance()
        font = app.font() if app is not None else QtGui.QFont()
    width = QtGui.QFontMetrics(font).horizontalAdvance(str(text)) + padding
    width = max(minimum, width)
    if maximum is not None:
        width = min(maximum, width)
    return int(width)


def compact_label_width(labels, widget=None, minimum=28, maximum=56, padding=0):
    """Size compact field labels from localized text without bloating English."""
    if isinstance(labels, str):
        labels = [labels]
    width = minimum
    for label in labels:
        width = max(
            width,
            compact_text_width(label, widget=widget, minimum=minimum, padding=padding),
        )
    return min(maximum, int(width))


def compact_footer_button_width(button, minimum=56, maximum=112, padding=22):
    """Return a localized footer button width while preserving compact bounds."""
    return compact_text_width(
        button.text(),
        widget=button,
        minimum=minimum,
        maximum=maximum,
        padding=padding,
    )


def make_inline_checkbox_row(label_text, checkbox, parent=None, minimum=88, maximum=150):
    """Create a compact localized label + checkbox row."""
    from PySide6 import QtCore, QtWidgets

    widget = QtWidgets.QWidget(parent)
    widget.setObjectName("RizumInlineCheckbox")
    widget.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    layout = QtWidgets.QHBoxLayout(widget)
    layout.setContentsMargins(8, 4, 8, 4)
    layout.setSpacing(10)

    label = QtWidgets.QLabel(label_text)
    label.setObjectName("RizumHintLabel")
    text_width = compact_text_width(label_text, widget=label, minimum=0, maximum=maximum - 32)
    label.setMinimumWidth(text_width)
    label.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Preferred,
    )
    layout.addWidget(label)
    layout.addWidget(checkbox)

    row_width = min(maximum, max(minimum, text_width + checkbox.width() + 36))
    widget.setMinimumWidth(row_width)
    widget._rizum_label = label
    widget._rizum_checkbox = checkbox
    widget._rizum_minimum = minimum
    widget._rizum_maximum = maximum

    def toggle(event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            checkbox.toggle()

    widget.mousePressEvent = toggle
    return widget


def update_inline_checkbox_row(widget, label_text=None, minimum=None, maximum=None):
    """Refresh an inline checkbox row after translation or font-scale changes."""
    from PySide6 import QtWidgets

    label = getattr(widget, "_rizum_label", None)
    checkbox = getattr(widget, "_rizum_checkbox", None)
    minimum = int(minimum if minimum is not None else getattr(widget, "_rizum_minimum", 88))
    maximum = int(maximum if maximum is not None else getattr(widget, "_rizum_maximum", 150))
    if label is None:
        label = widget.findChild(QtWidgets.QLabel, "RizumHintLabel")
    if checkbox is None:
        checkbox = widget.findChild(QtWidgets.QWidget, "RizumMockCheckbox")
    if label is None or checkbox is None:
        return

    if label_text is not None:
        label.setText(label_text)
    text_width = compact_text_width(
        label.text(),
        widget=label,
        minimum=0,
        maximum=max(0, maximum - 32),
    )
    label.setMinimumWidth(text_width)
    row_width = min(maximum, max(minimum, text_width + checkbox.width() + 36))
    widget.setMinimumWidth(row_width)
    try:
        widget.updateGeometry()
    except Exception:
        pass


def make_compact_separator(color="#414141", height=14):
    """Create a small vertical separator for compact toolbar rows."""
    from PySide6 import QtWidgets

    separator = QtWidgets.QFrame()
    separator.setFixedSize(1, height)
    separator.setStyleSheet(f"background: {color}; border: 0;")
    return separator


def make_compact_icon_toolbar(*items, spacing=4, separator_gap=4, parent=None):
    """Create a compact toolbar that keeps icon spacing stable across panels."""
    from PySide6 import QtWidgets

    toolbar = QtWidgets.QWidget(parent)
    toolbar.setObjectName("RizumTransparent")
    layout = QtWidgets.QHBoxLayout(toolbar)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    for item in items:
        if item is None:
            layout.addSpacing(separator_gap)
            layout.addWidget(make_compact_separator("#333333"))
            layout.addSpacing(separator_gap)
        else:
            layout.addWidget(item)
    return toolbar


def _stable_widget_width(widget):
    minimum = widget.minimumWidth()
    maximum = widget.maximumWidth()
    if minimum > 0 and minimum == maximum:
        return minimum
    return max(0, widget.sizeHint().width())


def make_compact_action_bar(
    left_controls=None,
    right_toolbar=None,
    object_name="RizumCompactActionBar",
    height=40,
    margins=(16, 0, 16, 0),
    spacing=8,
    parent=None,
):
    """Create the shared compact left-controls/right-toolbar row."""
    from PySide6 import QtWidgets

    bar = QtWidgets.QWidget(parent)
    bar.setObjectName(object_name)
    bar.setFixedHeight(height)
    layout = QtWidgets.QHBoxLayout(bar)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    controls = list(left_controls or [])
    for control in controls:
        layout.addWidget(control)
    layout.addStretch(1)
    if right_toolbar is not None:
        layout.addWidget(right_toolbar)

    def refresh_layout():
        for control in controls:
            refresh = getattr(control, "refreshMetrics", None)
            if refresh is not None:
                refresh()
        refresh = getattr(right_toolbar, "refreshMetrics", None)
        if refresh is not None:
            refresh()
        bar.updateGeometry()

    bar._rizum_left_controls = controls
    bar._rizum_right_toolbar = right_toolbar
    bar.refreshLayout = refresh_layout
    return bar


def compact_action_bar_width(
    left_controls,
    right_toolbar,
    minimum=284,
    horizontal_margins=32,
    spacing=8,
    spacing_budget=16,
):
    """Return the minimum panel width for a compact action bar."""
    controls = list(left_controls or [])
    left_width = sum(_stable_widget_width(control) for control in controls)
    if len(controls) > 1:
        left_width += spacing * (len(controls) - 1)
    right_width = _stable_widget_width(right_toolbar) if right_toolbar is not None else 0
    return max(
        int(minimum),
        int(left_width + right_width + horizontal_margins + spacing_budget),
    )


def compact_top_controls_width(
    left_control,
    right_toolbar,
    minimum=284,
    horizontal_margins=32,
    separator_width=1,
    spacing_budget=26,
):
    """Return a compact top-control width that survives localized labels."""
    return compact_action_bar_width(
        [left_control],
        right_toolbar,
        minimum=minimum,
        horizontal_margins=horizontal_margins,
        spacing_budget=separator_width + spacing_budget,
    )


def bind_hover_state(host, row, *widgets, property_name="hovered"):
    """Keep a row hover property stable while moving across child widgets."""
    from PySide6 import QtCore

    watched = [widget for widget in (host, row, *widgets) if widget is not None]

    class _TreeHoverFilter(QtCore.QObject):
        def __init__(self):
            super().__init__(host)

        def set_row_property(self, name, value):
            if row.property(name) == value:
                return
            row.setProperty(name, value)
            row.style().unpolish(row)
            row.style().polish(row)
            row.update()

        def set_hovered(self, is_hovered):
            self.set_row_property(property_name, is_hovered)

        def refresh_hovered(self):
            self.set_hovered(any(widget.underMouse() for widget in watched))

        def eventFilter(self, obj, event):
            event_type = event.type()
            if event_type == QtCore.QEvent.Type.Enter:
                self.set_hovered(True)
            elif event_type == QtCore.QEvent.Type.Leave:
                QtCore.QTimer.singleShot(0, self.refresh_hovered)
            elif event_type in (
                QtCore.QEvent.Type.MouseButtonPress,
                QtCore.QEvent.Type.MouseButtonRelease,
            ) and event.button() == QtCore.Qt.MouseButton.LeftButton:
                self.set_row_property(
                    "pressed",
                    event_type == QtCore.QEvent.Type.MouseButtonPress,
                )
            return False

    for widget in watched:
        widget.setMouseTracking(True)
    hover_filter = _TreeHoverFilter()
    for widget in watched:
        widget.installEventFilter(hover_filter)
    host._rizum_hover_filter = hover_filter
    return hover_filter


def _make_control_slot(widget, size=24, align_right=False):
    """Center a small control in the same square slot used by hover action icons."""
    from PySide6 import QtCore, QtWidgets

    slot = QtWidgets.QWidget()
    slot.setObjectName("RizumControlSlot")
    slot.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
    slot.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
    slot.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
    slot.setAutoFillBackground(False)
    slot.setCursor(widget.cursor())
    slot.setFixedSize(size, size)
    layout = QtWidgets.QHBoxLayout(slot)
    layout.setContentsMargins(0, 0, 3 if align_right else 0, 0)
    layout.setSpacing(0)
    alignment = QtCore.Qt.AlignmentFlag.AlignVCenter
    alignment |= (
        QtCore.Qt.AlignmentFlag.AlignRight
        if align_right
        else QtCore.Qt.AlignmentFlag.AlignHCenter
    )
    layout.addWidget(widget, 0, alignment)

    def press(event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            widget.mousePressEvent(event)

    slot.mousePressEvent = press
    return slot


def make_export_tree_item(name, checkbox, meta="", child=False, parent=None):
    """Create the compact export tree row used inside plugin-owned panels."""
    from PySide6 import QtCore, QtWidgets

    if child:
        host = QtWidgets.QFrame(parent)
        host.setObjectName("RizumExportTreeItemHost")
        host.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        host.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        host_layout = QtWidgets.QHBoxLayout(host)
        host_layout.setContentsMargins(24, 0, 4, 0)
        host_layout.setSpacing(0)

        row = QtWidgets.QFrame()
        row.setObjectName("RizumExportTreeItem")
        row.setProperty("child", "true")
        row.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        row_layout = QtWidgets.QHBoxLayout(row)
        row_layout.setContentsMargins(8, 4, 4, 4)
        row_layout.setSpacing(10)
        row_layout.addSpacing(0)

        label = QtWidgets.QLabel(name)
        label.setObjectName("RizumExportItemName")
        label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        row_layout.addWidget(label)
        row_layout.addStretch(1)
        checkbox_slot = _make_control_slot(checkbox, align_right=True)
        row_layout.addWidget(checkbox_slot)
        host_layout.addWidget(row)
        bind_hover_state(host, row, label, checkbox_slot, checkbox)
        host._rizum_label = label
        host._rizum_row = row
        host._rizum_checkbox = checkbox
        host._rizum_checkbox_slot = checkbox_slot
        host._rizum_child = True
        host._rizum_right_inset = 4
        host._rizum_right_padding = 4

        def set_right_inset(inset, padding):
            inset = max(3, int(round(inset)))
            padding = max(3, int(round(padding)))
            host._rizum_right_inset = inset
            host._rizum_right_padding = padding
            host_layout.setContentsMargins(24, 0, inset, 0)
            row_layout.setContentsMargins(
                8,
                4,
                padding,
                4,
            )
            host_layout.invalidate()
            row.updateGeometry()

        host.setRightInset = set_right_inset
        update_export_tree_item(host, name)
        def refresh_host(name_text=None, meta_text=None):
            update_export_tree_item(host, name_text, meta_text)

        host.refreshLayout = refresh_host
        return host

    row = QtWidgets.QFrame(parent)
    row.setObjectName("RizumExportTreeItem")
    row.setProperty("child", "false")
    row.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    row.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
    row.setMouseTracking(True)
    row_layout = QtWidgets.QHBoxLayout(row)
    row_layout.setContentsMargins(8, 4, 8, 4)
    row_layout.setSpacing(10)
    row_layout.addWidget(make_svg_label("chevron-down.svg", 14))

    label = QtWidgets.QLabel(name)
    label.setObjectName("RizumExportItemName")
    label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    meta_label = None
    if meta:
        text_stack = QtWidgets.QHBoxLayout()
        text_stack.setContentsMargins(0, 0, 0, 0)
        text_stack.setSpacing(4)
        meta_label = QtWidgets.QLabel(meta)
        meta_label.setObjectName("RizumExportMeta")
        meta_label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text_stack.addWidget(label)
        text_stack.addWidget(meta_label)
        text_stack.addStretch(1)
        row_layout.addLayout(text_stack)
    else:
        row_layout.addWidget(label)
    row_layout.addStretch(1)
    checkbox_slot = _make_control_slot(checkbox, align_right=True)
    row_layout.addWidget(checkbox_slot)
    row._rizum_label = label
    row._rizum_meta_label = meta_label
    row._rizum_checkbox = checkbox
    row._rizum_checkbox_slot = checkbox_slot
    row._rizum_child = False
    bind_hover_state(row, row, label, meta_label, checkbox_slot, checkbox)
    update_export_tree_item(row, name, meta)
    def refresh_row(name_text=None, meta_text=None):
        update_export_tree_item(row, name_text, meta_text)

    row.refreshLayout = refresh_row
    return row


def update_export_tree_item(widget, name=None, meta=None, minimum_height=None):
    """Refresh export tree row text and height after i18n or font-scale changes."""
    label = getattr(widget, "_rizum_label", None)
    meta_label = getattr(widget, "_rizum_meta_label", None)
    row = getattr(widget, "_rizum_row", widget)
    is_child = bool(getattr(widget, "_rizum_child", False))

    if label is not None and name is not None:
        label.setText(name)
        widget._rizum_name = name
    if meta_label is not None and meta is not None:
        meta_label.setText(meta)
        widget._rizum_meta = meta

    base_height = 32 if is_child else 36
    minimum_height = int(minimum_height if minimum_height is not None else base_height)
    metrics_widgets = [candidate for candidate in (label, meta_label) if candidate is not None]
    text_height = 0
    for candidate in metrics_widgets:
        text_height = max(text_height, candidate.fontMetrics().height())
    height = max(minimum_height, text_height + 14)

    row.setFixedHeight(height)
    if row is not widget:
        widget.setFixedHeight(height)
    try:
        row.updateGeometry()
        widget.updateGeometry()
    except Exception:
        pass


def make_collapsible_group(
    title,
    subtitle="",
    children=None,
    leading_widget=None,
    trailing_widget=None,
    expanded=True,
    show_chevron=True,
    parent=None,
):
    """Create an animated folder-like group with optional leading/trailing slots."""
    from PySide6 import QtCore, QtGui, QtWidgets

    duration = 300

    class _CollapsibleChevron(QtWidgets.QWidget):
        def __init__(self, is_expanded):
            super().__init__()
            self.setObjectName("RizumCollapsibleChevron")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._size = 14
            self.setFixedSize(self._size, self._size)
            self._angle = 90.0 if is_expanded else 0.0

        def setSize(self, size):
            self._size = max(11, int(round(size)))
            self.setFixedSize(self._size, self._size)
            self.updateGeometry()
            self.update()

        def getAngle(self):
            return self._angle

        def setAngle(self, angle):
            self._angle = float(angle)
            self.update()

        angle = QtCore.Property(float, getAngle, setAngle)

        def paintEvent(self, event):
            scale = self._size / 14.0
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.translate(self.width() / 2, self.height() / 2)
            painter.rotate(self._angle)
            painter.translate(-self.width() / 2, -self.height() / 2)
            pen = QtGui.QPen(QtGui.QColor("#9e9e9e"))
            pen.setWidthF(1.8 * scale)
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPolyline(
                [
                    QtCore.QPointF(5.0 * scale, 3.7 * scale),
                    QtCore.QPointF(8.4 * scale, 7.0 * scale),
                    QtCore.QPointF(5.0 * scale, 10.3 * scale),
                ]
            )

    class _AnimatedHeightFrame(QtWidgets.QFrame):
        def __init__(self):
            super().__init__()
            self._animated_height = 0
            self._content_widget = None
            self._content_height = 0
            self._content_width = -1
            self._height_changed = None
            self.setAutoFillBackground(False)
            clipped_attr = getattr(QtCore.Qt.WidgetAttribute, "WA_Clipped", None)
            if clipped_attr is not None:
                self.setAttribute(clipped_attr, True)
            clip_attr = getattr(QtCore.Qt.WidgetAttribute, "WA_ClipChildren", None)
            if clip_attr is not None:
                self.setAttribute(clip_attr, True)

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self.syncContentWidth()

        def setContentWidget(self, widget):
            self._content_widget = widget
            self.syncContentSize()

        def contentHeight(self):
            return self._content_height

        def syncContentSize(self):
            if self._content_widget is None:
                return 0
            width = max(0, self.width())
            if width <= 0:
                width = max(0, self.parentWidget().width() if self.parentWidget() else 0)
            if width <= 0:
                width = max(0, self._content_widget.sizeHint().width())
            height = max(0, self._content_widget.sizeHint().height())
            self._content_width = width
            self._content_height = height
            self._content_widget.setGeometry(0, 0, width, height)
            return height

        def syncContentWidth(self):
            if self._content_widget is None:
                return
            width = max(0, self.width())
            if width == self._content_width:
                return
            self._content_width = width
            self._content_widget.setGeometry(0, 0, width, self._content_height)

        def getAnimatedHeight(self):
            return self._animated_height

        def setAnimatedHeight(self, value):
            self._animated_height = max(0, int(round(value)))
            self.setFixedHeight(self._animated_height)
            if self._height_changed is not None:
                self._height_changed(self._animated_height)
            self.update()
            self.updateGeometry()

        animatedHeight = QtCore.Property(int, getAnimatedHeight, setAnimatedHeight)

    group = QtWidgets.QFrame(parent)
    group.setObjectName("RizumCollapsibleGroup")
    group.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    group.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    group.setMouseTracking(True)
    group_layout = QtWidgets.QVBoxLayout(group)
    group_layout.setContentsMargins(0, 2, 0, 2)
    group_layout.setSpacing(0)

    header = QtWidgets.QFrame()
    header.setObjectName("RizumCollapsibleHeader")
    header.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    header.setMouseTracking(True)
    header.setFixedHeight(36)
    header_layout = QtWidgets.QHBoxLayout(header)
    header_layout.setContentsMargins(8, 4, 8, 4)
    header_layout.setSpacing(10)

    chevron = None
    if show_chevron:
        chevron = _CollapsibleChevron(expanded)
        header_layout.addWidget(chevron)

    if leading_widget is not None:
        header_layout.addWidget(leading_widget)

    title_label = QtWidgets.QLabel(title)
    title_label.setObjectName("RizumCollapsibleTitle")
    header_layout.addWidget(title_label)

    header_layout.addStretch(1)
    subtitle_label = None
    if subtitle:
        subtitle_label = QtWidgets.QLabel(subtitle)
        subtitle_label.setObjectName("RizumCollapsibleSubtitle")
        subtitle_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        header_layout.addWidget(subtitle_label)
    if trailing_widget is not None:
        if trailing_widget.objectName() == "RizumMockCheckbox":
            trailing_widget = _make_control_slot(trailing_widget, align_right=True)
            header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.addWidget(trailing_widget)
    group_layout.addWidget(header)

    content = _AnimatedHeightFrame()
    content.setObjectName("RizumCollapsibleContent")
    content.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    content.setMouseTracking(True)
    content.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    content_inner = QtWidgets.QWidget(content)
    content_inner.setObjectName("RizumCollapsibleContentInner")
    content_inner.setAutoFillBackground(False)
    content_layout = QtWidgets.QVBoxLayout(content_inner)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(2)
    for child in children or []:
        content_layout.addWidget(child)
    group_layout.addWidget(content)

    def content_height():
        return content.syncContentSize()

    def sync_inner_size():
        content.syncContentSize()

    def sync_group_height(content_height_value=None):
        if content_height_value is None:
            content_height_value = content.getAnimatedHeight()
        margins = group_layout.contentsMargins()
        total_height = (
            margins.top()
            + header.height()
            + int(content_height_value)
            + margins.bottom()
        )
        group.setFixedHeight(total_height)
        group.update()
        group.updateGeometry()

    content.setVisible(True)
    content.setContentWidget(content_inner)
    content._height_changed = sync_group_height
    sync_inner_size()
    if expanded:
        initial_height = content_height()
        content.setAnimatedHeight(initial_height)
    else:
        content.setAnimatedHeight(0)
        content_inner.move(0, 0)
    content_inner.setVisible(bool(expanded))

    def update_chevron(next_expanded):
        if chevron is None:
            return
        chevron.setAngle(90.0 if next_expanded else 0.0)

    def finish_animation_state(next_expanded, target_height):
        content.setAnimatedHeight(target_height)
        content_inner.setVisible(next_expanded)
        update_chevron(next_expanded)
        group._rizum_animating = False
        group._rizum_collapse_animation = None

    def refresh_layout(title_text=None, subtitle_text=None):
        if title_text is not None:
            title_label.setText(title_text)
        if subtitle_text is not None and subtitle_label is not None:
            subtitle_label.setText(subtitle_text)
        next_height = content_height() if group._rizum_expanded else 0
        content.setAnimatedHeight(next_height)
        content_inner.setVisible(group._rizum_expanded)
        update_chevron(group._rizum_expanded)
        try:
            group.updateGeometry()
        except Exception:
            pass

    def set_compact_height(height):
        height = max(27, int(round(height)))
        scale = height / 36.0
        group_margin = max(2, int(round(2 * scale)))
        horizontal_margin = max(6, int(round(8 * scale)))
        vertical_margin = max(3, int(round(4 * scale)))
        group_layout.setContentsMargins(0, group_margin, 0, group_margin)
        header.setFixedHeight(height)
        header_layout.setContentsMargins(
            horizontal_margin,
            vertical_margin,
            horizontal_margin,
            vertical_margin,
        )
        header_layout.setSpacing(max(8, int(round(10 * scale))))
        content_layout.setSpacing(max(2, int(round(2 * scale))))
        if chevron is not None:
            chevron.setSize(max(11, int(round(14 * scale))))
        refresh_layout()

    def set_expanded(next_expanded):
        next_expanded = bool(next_expanded)
        if group._rizum_expanded == next_expanded:
            return
        group._rizum_expanded = next_expanded
        group._rizum_animating = True
        group._rizum_animation_token += 1
        animation_token = group._rizum_animation_token
        content.setVisible(True)
        content.updateGeometry()
        target_height = content_height() if next_expanded else 0
        start_height = content.getAnimatedHeight()
        sync_inner_size()
        content_inner.move(0, 0)
        content_inner.setVisible(True)

        old_animation = getattr(group, "_rizum_collapse_animation", None)
        if old_animation is not None:
            old_animation.stop()

        height_animation = QtCore.QPropertyAnimation(content, b"animatedHeight", group)
        height_animation.setDuration(duration)
        height_animation.setStartValue(start_height)
        height_animation.setEndValue(target_height)
        height_animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

        animation_group = QtCore.QParallelAnimationGroup(group)
        animation_group.addAnimation(height_animation)
        if chevron is not None:
            chevron_animation = QtCore.QPropertyAnimation(chevron, b"angle", group)
            chevron_animation.setDuration(duration)
            chevron_animation.setStartValue(chevron.getAngle())
            chevron_animation.setEndValue(90.0 if next_expanded else 0.0)
            chevron_animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            animation_group.addAnimation(chevron_animation)

        def finish():
            if animation_token != group._rizum_animation_token:
                return
            finish_animation_state(next_expanded, target_height)

        animation_group.finished.connect(finish)
        group._rizum_collapse_animation = animation_group
        animation_group.start()

    def toggle():
        set_expanded(not group._rizum_expanded)

    group._rizum_expanded = bool(expanded)
    group._rizum_animating = False
    group._rizum_collapse_animation = None
    group._rizum_animation_token = 0
    group._rizum_header = header
    group._rizum_content = content
    group._rizum_content_inner = content_inner
    group._rizum_content_layout = content_layout
    group.setExpanded = set_expanded
    group.isExpanded = lambda: group._rizum_expanded
    group.toggle = toggle
    group.refreshLayout = refresh_layout
    group.setCompactHeight = set_compact_height
    header.mousePressEvent = lambda event: toggle() if event.button() == QtCore.Qt.MouseButton.LeftButton else None
    return group


def make_drag_collapsible_group(
    title,
    subtitle="",
    children=None,
    draggable=True,
    expanded=True,
    parent=None,
):
    """Create the drag/drop variant whose folder icon is the only disclosure marker."""
    from PySide6 import QtCore, QtGui, QtWidgets

    group = make_collapsible_group(
        title,
        subtitle,
        children=children,
        leading_widget=make_svg_label("folder-filled.svg", 14, color="#ffffff"),
        expanded=expanded,
        show_chevron=False,
        parent=parent,
    )
    group.setProperty("variant", "drag")
    group.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
    group._rizum_drag_name = title
    group._rizum_drag_folder = True
    for child in children or []:
        child._rizum_parent_group = group

    def set_group_hovered(is_hovered):
        if group.property("hovered") == is_hovered:
            return
        group.setProperty("hovered", is_hovered)
        group.style().unpolish(group)
        group.style().polish(group)

    header = group._rizum_header
    header.setCursor(
        QtCore.Qt.CursorShape.OpenHandCursor
        if draggable
        else QtCore.Qt.CursorShape.PointingHandCursor
    )
    header.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
    header._rizum_press_pos = None
    header._rizum_drag_started = False
    header._rizum_host = group

    def press(event):
        set_group_hovered(True)
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return
        header._rizum_press_pos = event.position().toPoint()
        header._rizum_drag_started = False

    def move(event):
        set_group_hovered(True)
        if not draggable or header._rizum_press_pos is None:
            return
        distance = (event.position().toPoint() - header._rizum_press_pos).manhattanLength()
        if distance < QtWidgets.QApplication.startDragDistance():
            return
        header._rizum_drag_started = True
        header._rizum_press_pos = None
        was_expanded = group.isExpanded()
        child_count = sum(
            1
            for index in range(group._rizum_content_layout.count())
            if group._rizum_content_layout.itemAt(index).widget() is not None
        )
        if was_expanded:
            group.setExpanded(False)
        group.setProperty("dragging", True)
        group.style().unpolish(group)
        group.style().polish(group)
        result = _start_drag(
            QtCore,
            QtGui,
            QtWidgets,
            header,
            title,
            folder=True,
            child_count=child_count,
            masked=False,
        )
        group.setProperty("dragging", False)
        group.style().unpolish(group)
        group.style().polish(group)
        if result == QtCore.Qt.DropAction.IgnoreAction and was_expanded:
            group.setExpanded(True)

    def release(event):
        set_group_hovered(True)
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return
        if not header._rizum_drag_started:
            group.toggle()
        header._rizum_press_pos = None
        header._rizum_drag_started = False

    header.mousePressEvent = press
    header.mouseMoveEvent = move
    header.mouseReleaseEvent = release
    group.enterEvent = lambda event: set_group_hovered(True)
    group.leaveEvent = lambda event: set_group_hovered(False)
    header.enterEvent = lambda event: set_group_hovered(True)
    header.leaveEvent = lambda event: set_group_hovered(False)
    return group


def make_inset_separator(inset, thickness=2):
    """Create an inset separator with left/right breathing room."""
    from PySide6 import QtWidgets

    wrapper = QtWidgets.QWidget()
    wrapper.setObjectName("RizumTransparent")
    wrapper.setFixedHeight(thickness)
    wrapper_layout = QtWidgets.QHBoxLayout(wrapper)
    wrapper_layout.setContentsMargins(inset, 0, inset, 0)
    wrapper_layout.setSpacing(0)
    line = QtWidgets.QFrame()
    line.setObjectName("RizumInsetSeparator")
    line.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    line.setFixedHeight(thickness)
    line.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Fixed,
    )
    wrapper_layout.addWidget(line)
    return wrapper


def make_painter_title_bar(title, parent=None):
    """Create preview chrome matching Painter's native light title bar."""
    from PySide6 import QtCore, QtGui, QtWidgets

    base_height = PAINTER_TITLE_BAR_HEIGHT

    class _PainterTitleBar(QtWidgets.QWidget):
        def __init__(self):
            super().__init__(parent)
            self.setObjectName("RizumPainterTitleBar")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
            self._compact_height = base_height
            self._layout = QtWidgets.QHBoxLayout(self)
            self._layout.setSpacing(8)

            self._app_icon = QtWidgets.QLabel("Pt")
            self._app_icon.setObjectName("RizumPainterTitleBarIcon")
            self._app_icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self._title = QtWidgets.QLabel(str(title))
            self._title.setObjectName("RizumPainterTitleBarText")
            self._close = QtWidgets.QLabel("×")
            self._close.setObjectName("RizumPainterTitleBarClose")
            self._close.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            self._layout.addWidget(self._app_icon)
            self._layout.addWidget(self._title)
            self._layout.addStretch(1)
            self._layout.addWidget(self._close)
            self.setCompactHeight(base_height)

        def setCompactHeight(self, height):
            # This represents Windows chrome, not Painter content. Native title
            # bars stay fixed when the Painter UI font scale changes.
            self._compact_height = base_height
            self.setFixedHeight(self._compact_height)
            self._layout.setContentsMargins(10, 0, 7, 0)
            self._layout.setSpacing(8)
            self._app_icon.setFixedSize(14, 14)
            self._close.setFixedSize(22, 22)

            title_font = QtGui.QFont("Segoe UI")
            title_font.setPixelSize(12)
            title_font.setWeight(QtGui.QFont.Weight.Normal)
            self._title.setFont(title_font)
            close_font = QtGui.QFont(title_font)
            close_font.setPixelSize(18)
            self._close.setFont(close_font)
            icon_font = QtGui.QFont(title_font)
            icon_font.setPixelSize(8)
            icon_font.setWeight(QtGui.QFont.Weight.Bold)
            self._app_icon.setFont(icon_font)

            self.setStyleSheet(
                """
                QWidget#RizumPainterTitleBar {
                    background: #f3f3f3;
                    border: 0;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                }
                QLabel#RizumPainterTitleBarText {
                    color: #202020;
                    background: transparent;
                    border: 0;
                }
                QLabel#RizumPainterTitleBarClose {
                    color: #222222;
                    background: transparent;
                    border: 0;
                }
                QLabel#RizumPainterTitleBarIcon {
                    color: #98e73f;
                    background: #1e3101;
                    border: 0;
                    border-radius: 2px;
                }
                """
            )
            self.updateGeometry()

    return _PainterTitleBar()


def make_painter_window_content(
    background="#1b1b1b",
    parent=None,
    *,
    rounded=True,
    top_radius=None,
    bottom_radius=None,
):
    """Create a preview container for plugin-controlled window content."""
    from PySide6 import QtCore, QtWidgets

    class _PainterWindowContent(QtWidgets.QFrame):
        def __init__(self):
            super().__init__(parent)
            self.setObjectName("RizumPainterWindowContent")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
            self._content_layout = QtWidgets.QVBoxLayout(self)
            self._content_layout.setContentsMargins(0, 0, 0, 0)
            self._content_layout.setSpacing(0)
            default_top = PAINTER_WINDOW_CONTENT_RADIUS if rounded else 0
            default_bottom = (
                PAINTER_WINDOW_CONTENT_BOTTOM_RADIUS if rounded else 0
            )
            self._top_radius = max(
                0,
                int(default_top if top_radius is None else top_radius),
            )
            self._bottom_radius = max(
                0,
                int(default_bottom if bottom_radius is None else bottom_radius),
            )
            self.setPainterContentColor(background)

        def contentLayout(self):
            return self._content_layout

        def setPainterContentColor(self, color):
            self.setStyleSheet(
                f"""
                QFrame#RizumPainterWindowContent {{
                    background: {color};
                    border: 0;
                    border-top-left-radius: {self._top_radius}px;
                    border-top-right-radius: {self._top_radius}px;
                    border-bottom-left-radius: {self._bottom_radius}px;
                    border-bottom-right-radius: {self._bottom_radius}px;
                }}
                """
            )

    return _PainterWindowContent()


def make_icon_button(icon_name, tooltip="", size=16, compact=True):
    """Create a themed icon button from the shared icons folder."""
    from PySide6 import QtCore, QtGui, QtWidgets

    from .theme import default_theme

    try:
        from PySide6 import QtSvg
    except Exception:
        QtSvg = None

    class _AnimatedIconButton(QtWidgets.QPushButton):
        def __init__(self, icon_path):
            super().__init__("")
            self._icon_path = icon_path
            self._icon = QtGui.QIcon(str(icon_path))
            self._icon_source = ""
            try:
                self._icon_source = icon_path.read_text(encoding="utf-8")
            except Exception:
                pass
            self._pixmap_cache = {}
            self._icon_size = int(size)
            self._button_base_size = 22 if compact else 32
            self._visual_scale = 1.0
            self._visual_opacity = 1.0
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        def setPaintedIconSize(self, icon_size):
            """Scale the painted icon (and invalidate the pixmap cache).

            Named setPaintedIconSize (not setIconSize) to avoid clashing with
            the non-virtual QPushButton.setIconSize(QSize) from QAbstractButton,
            which PySide6 cannot override from a Python subclass.
            """
            new_size = max(8, int(round(icon_size)))
            if new_size == self._icon_size:
                return
            self._icon_size = new_size
            self._pixmap_cache.clear()
            self.update()

        def paintedIconSize(self):
            return self._icon_size

        def getVisualScale(self):
            return self._visual_scale

        def setVisualScale(self, value):
            self._visual_scale = float(value)
            self.update()

        def getVisualOpacity(self):
            return self._visual_opacity

        def setVisualOpacity(self, value):
            self._visual_opacity = float(value)
            self.update()

        visualScale = QtCore.Property(float, getVisualScale, setVisualScale)
        visualOpacity = QtCore.Property(float, getVisualOpacity, setVisualOpacity)

        def enterEvent(self, event):
            super().enterEvent(event)
            self.update()

        def leaveEvent(self, event):
            super().leaveEvent(event)
            if not self.isDown():
                self._animate_icon(1.0, 1.0, 160)
            self.update()

        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._animate_icon(0.85, 0.7, 80)
            super().mousePressEvent(event)

        def mouseReleaseEvent(self, event):
            super().mouseReleaseEvent(event)
            self._animate_icon(1.0, 1.0, 180)

        def _animate_icon(self, scale, opacity, duration):
            old_animation = getattr(self, "_rizum_icon_animation", None)
            if old_animation is not None:
                old_animation.stop()
            easing = QtCore.QEasingCurve.Type.OutCubic
            scale_animation = QtCore.QPropertyAnimation(self, b"visualScale", self)
            scale_animation.setDuration(duration)
            scale_animation.setStartValue(self._visual_scale)
            scale_animation.setEndValue(scale)
            scale_animation.setEasingCurve(easing)
            opacity_animation = QtCore.QPropertyAnimation(self, b"visualOpacity", self)
            opacity_animation.setDuration(duration)
            opacity_animation.setStartValue(self._visual_opacity)
            opacity_animation.setEndValue(opacity)
            opacity_animation.setEasingCurve(easing)
            animation_group = QtCore.QParallelAnimationGroup(self)
            animation_group.addAnimation(scale_animation)
            animation_group.addAnimation(opacity_animation)
            self._rizum_icon_animation = animation_group
            animation_group.start()

        def _rendered_pixmap(self, color):
            dpr = self.devicePixelRatioF()
            icon_size = self._icon_size
            key = (color, round(dpr, 2), icon_size)
            if key in self._pixmap_cache:
                return self._pixmap_cache[key]
            pixel_size = max(1, int(round(icon_size * dpr)))
            pixmap = QtGui.QPixmap(pixel_size, pixel_size)
            pixmap.setDevicePixelRatio(dpr)
            pixmap.fill(QtCore.Qt.GlobalColor.transparent)
            if QtSvg is not None and self._icon_source:
                source = self._icon_source
                source = source.replace("currentColor", color)
                source = _svg_with_breathing_room(source)
                renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(source.encode("utf-8")))
                painter = QtGui.QPainter(pixmap)
                renderer.render(painter, QtCore.QRectF(0, 0, icon_size, icon_size))
                painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(QtCore.QRectF(0, 0, icon_size, icon_size), QtGui.QColor(color))
                painter.end()
            else:
                base = self._icon.pixmap(QtCore.QSize(pixel_size, pixel_size))
                painter = QtGui.QPainter(pixmap)
                painter.drawPixmap(QtCore.QRectF(0, 0, icon_size, icon_size), base, QtCore.QRectF(base.rect()))
                painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(QtCore.QRectF(0, 0, icon_size, icon_size), QtGui.QColor(color))
                painter.end()
            self._pixmap_cache[key] = pixmap
            return pixmap

        def paintEvent(self, event):
            # Don't call super().paintEvent() — we draw our own hover/pressed
            # background to match CompactStepperButtons (1px inset, 6px radius)
            # instead of the stylesheet's flat 4px-radius fill that looks bigger.
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
            # Hover/pressed background mirrors the stepper: adjusted(1,1,-1,-1)
            # so the highlight sits 1px inside the button edge. Fill and radius
            # come from the shared clickable-layer tokens.
            if self.isEnabled() and (self.underMouse() or self.isDown()):
                frame_size = max(1, min(self.width(), self.height()))
                frame_scale = max(0.75, frame_size / float(self._button_base_size))
                hover_inset = max(1, int(round(1 * frame_scale)))
                hover_radius = max(
                    5,
                    int(round(default_theme.radius_small * frame_scale)),
                )
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.setBrush(
                    QtGui.QColor(
                        default_theme.action_pressed
                        if self.isDown()
                        else default_theme.action_hover
                    )
                )
                rect = QtCore.QRectF(self.rect()).adjusted(
                    hover_inset,
                    hover_inset,
                    -hover_inset,
                    -hover_inset,
                )
                painter.drawRoundedRect(rect, hover_radius, hover_radius)
            # Priority: disabled > hover > accent > default. Hover must come
            # before accent so accent buttons still get a visible hover change
            # (accent default #e0e0e0 -> hover #ffffff) instead of staying
            # flat white.
            if not self.isEnabled():
                color = self.property("iconDisabledColor") or "#666666"
            elif self.underMouse():
                color = self.property("iconHoverColor") or "#ffffff"
            elif self.property("accent"):
                color = self.property("iconAccentColor") or "#e0e0e0"
            else:
                color = self.property("iconColor") or "#9e9e9e"
            pixmap = self._rendered_pixmap(color)
            icon_size = self._icon_size
            visual_size = max(1, int(round(icon_size * self._visual_scale)))
            target = QtCore.QRect(
                int((self.width() - visual_size) / 2),
                int((self.height() - visual_size) / 2),
                visual_size,
                visual_size,
            )
            painter.setOpacity(max(0.0, min(1.0, self._visual_opacity)))
            painter.drawPixmap(target, pixmap)
            painter.end()

    icon_path = ROOT / "icons" / icon_name
    button = _AnimatedIconButton(icon_path)
    button.setProperty("variant", "icon")
    if compact:
        button.setProperty("compact", True)
        button.setFixedSize(22, 22)
    else:
        button.setMinimumHeight(32)
    if tooltip:
        install_compact_tooltip(button, tooltip)
    return button


def _render_svg_pixmap(QtCore, QtGui, QtWidgets, icon_name, size, color=None):
    try:
        from PySide6 import QtSvg
    except Exception:
        QtSvg = None

    icon_path = ROOT / "icons" / icon_name
    if QtSvg is not None:
        dpr = _screen_dpr(QtWidgets)
        pixel_size = max(1, int(round(size * dpr)))
        source = icon_path.read_text(encoding="utf-8")
        if color is not None:
            source = source.replace("currentColor", color)
        source = _svg_with_breathing_room(source)
        pixmap = QtGui.QPixmap(pixel_size, pixel_size)
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
        renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(source.encode("utf-8")))
        renderer.render(painter, QtCore.QRectF(0, 0, size, size))
        if color is not None:
            painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(QtCore.QRectF(0, 0, size, size), QtGui.QColor(color))
        painter.end()
        return pixmap

    dpr = _screen_dpr(QtWidgets)
    pixel_size = max(1, int(round(size * dpr)))
    pixmap = QtGui.QIcon(str(icon_path)).pixmap(QtCore.QSize(pixel_size, pixel_size))
    pixmap.setDevicePixelRatio(dpr)
    return pixmap


def render_svg_pixmap(icon_name, size, color=None):
    """Public boundary for rendering a shared-folder SVG icon to a pixmap.

    Shared components outside this module must use this instead of the
    private ``_render_svg_pixmap`` worker.
    """
    from PySide6 import QtCore, QtGui, QtWidgets

    return _render_svg_pixmap(QtCore, QtGui, QtWidgets, icon_name, size, color)


def make_svg_label(icon_name, size, color=None):
    """Create a passive SVG label that does not take its own hover state."""
    from PySide6 import QtCore, QtGui, QtWidgets

    label = QtWidgets.QLabel()
    label.setObjectName("RizumSvgLabel")
    label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    label.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
    label.setPixmap(_render_svg_pixmap(QtCore, QtGui, QtWidgets, icon_name, size, color))
    label.setFixedSize(size, size)
    label.setStyleSheet("background: transparent; border: 0;")
    return label


def make_masked_svg_label(icon_name, size, color=None):
    """Create a passive SVG label with a compact mask-state badge."""
    from PySide6 import QtCore, QtGui, QtWidgets

    class _MaskedSvgLabel(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.setObjectName("RizumSvgLabel")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
            self.setFixedSize(size, size)
            self.setStyleSheet("background: transparent; border: 0;")
            self._pixmap = _render_svg_pixmap(QtCore, QtGui, QtWidgets, icon_name, size, color)

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawPixmap(QtCore.QPoint(0, 0), self._pixmap)

            badge_color = QtGui.QColor(color or "#9E9E9E")
            badge_size = max(6, int(round(size * 0.48)))
            badge_rect = QtCore.QRectF(
                self.width() - badge_size - 1.0,
                self.height() - badge_size - 1.0,
                badge_size,
                badge_size,
            )
            radius = max(1.5, badge_size * 0.22)
            painter.setPen(QtGui.QPen(badge_color, 1.0))
            painter.setBrush(QtGui.QColor("#1b1b1b"))
            painter.drawRoundedRect(badge_rect, radius, radius)

            clip_path = QtGui.QPainterPath()
            clip_path.addRoundedRect(badge_rect.adjusted(1, 1, -1, -1), max(1.0, radius - 0.5), max(1.0, radius - 0.5))
            painter.save()
            painter.setClipPath(clip_path)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(badge_color)
            painter.drawRect(
                QtCore.QRectF(
                    badge_rect.center().x(),
                    badge_rect.top() + 1,
                    badge_rect.width() / 2,
                    badge_rect.height() - 2,
                )
            )
            painter.restore()
            painter.end()

    return _MaskedSvgLabel()


def make_tree_icon_label(icon_name, size=None, folder=False, masked=False, color=None):
    """Create the standard passive tree icon, including folder and mask variants."""
    display_icon_name = "folder-filled.svg" if folder else icon_name
    icon_size = int(size if size is not None else (16 if display_icon_name == "layers.svg" else 14))
    if masked:
        return make_masked_svg_label(display_icon_name, icon_size, color=color)
    return make_svg_label(display_icon_name, icon_size, color=color)


def _screen_dpr(QtWidgets, source=None):
    if source is not None:
        try:
            return max(1.0, float(source.devicePixelRatioF()))
        except Exception:
            pass
    screen = QtWidgets.QApplication.primaryScreen()
    if screen is None:
        return 1.0
    return max(1.0, float(screen.devicePixelRatio()))


_DRAG_GHOST_SHADOW_MARGIN = 36


def _paint_blurred_shadow(QtCore, QtGui, QtWidgets, painter, logical_size, dpr, card_rect, offset_y, blur_radius, alpha):
    shadow_pixmap = QtGui.QPixmap(
        max(1, int(round(logical_size.width() * dpr))),
        max(1, int(round(logical_size.height() * dpr))),
    )
    shadow_pixmap.setDevicePixelRatio(dpr)
    shadow_pixmap.fill(QtCore.Qt.GlobalColor.transparent)

    shadow_painter = QtGui.QPainter(shadow_pixmap)
    shadow_painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    shadow_painter.setPen(QtCore.Qt.PenStyle.NoPen)
    shadow_painter.setBrush(QtGui.QColor(0, 0, 0, alpha))
    shadow_painter.drawRoundedRect(card_rect.translated(0, offset_y), 8, 8)
    shadow_painter.end()

    scene = QtWidgets.QGraphicsScene()
    scene.setSceneRect(QtCore.QRectF(0, 0, logical_size.width(), logical_size.height()))
    item = QtWidgets.QGraphicsPixmapItem(shadow_pixmap)
    blur = QtWidgets.QGraphicsBlurEffect()
    blur.setBlurRadius(blur_radius)
    blur.setBlurHints(QtWidgets.QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(blur)
    scene.addItem(item)
    scene.render(
        painter,
        QtCore.QRectF(0, 0, logical_size.width(), logical_size.height()),
        QtCore.QRectF(0, 0, logical_size.width(), logical_size.height()),
    )


def _make_drag_pixmap(QtCore, QtGui, QtWidgets, name, icon_name, folder=False, child_count=0, masked=False, source=None):
    ghost = QtWidgets.QFrame()
    ghost.setObjectName("RizumDragGhost")
    ghost.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
    ghost.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
    ghost.setAutoFillBackground(False)
    ghost.setStyleSheet(
        """
QFrame#RizumDragGhost {
    background: transparent;
    border: 0;
    color: #8f8f8f;
}
QFrame#RizumDragGhost QLabel,
QFrame#RizumDragGhost QLabel:hover {
    color: #8f8f8f;
    background: transparent;
    border: 0;
}
"""
    )
    layout = QtWidgets.QVBoxLayout(ghost) if folder and child_count else QtWidgets.QHBoxLayout(ghost)
    layout.setContentsMargins(12, 8, 16, 8)
    layout.setSpacing(4 if folder and child_count else 10)
    header = QtWidgets.QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)
    header.setSpacing(10)
    icon_widget = make_tree_icon_label(
        icon_name,
        folder=folder,
        masked=masked,
        color="#ffffff" if folder else None,
    )
    header.addWidget(icon_widget)
    label = QtWidgets.QLabel(name)
    label.setObjectName("RizumDragGhostName")
    label.setStyleSheet("color: #8f8f8f; font-weight: 400; background: transparent; border: 0;")
    header.addWidget(label)
    if isinstance(layout, QtWidgets.QVBoxLayout):
        layout.addLayout(header)
        meta = QtWidgets.QLabel(f"{child_count} item{'s' if child_count != 1 else ''}")
        meta.setStyleSheet("color: #777777; font-size: 11px; background: transparent; border: 0; padding-left: 24px;")
        layout.addWidget(meta)
    else:
        layout.addLayout(header)
    layout.activate()
    ghost.adjustSize()
    ghost.resize(ghost.sizeHint())
    ghost.ensurePolished()

    dpr = _screen_dpr(QtWidgets, source)
    logical_size = ghost.size()
    shadow_margin = _DRAG_GHOST_SHADOW_MARGIN
    pixmap = QtGui.QPixmap(
        max(1, int(round((logical_size.width() + shadow_margin * 2) * dpr))),
        max(1, int(round((logical_size.height() + shadow_margin * 2) * dpr))),
    )
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    card_rect = QtCore.QRectF(
        shadow_margin + 0.5,
        shadow_margin + 0.5,
        ghost.width() - 1,
        ghost.height() - 1,
    )
    pixmap_logical_size = QtCore.QSizeF(pixmap.deviceIndependentSize())
    _paint_blurred_shadow(
        QtCore, QtGui, QtWidgets, painter, pixmap_logical_size, dpr, card_rect, 15, 35, 96
    )
    _paint_blurred_shadow(
        QtCore, QtGui, QtWidgets, painter, pixmap_logical_size, dpr, card_rect, 5, 15, 58
    )
    card_path = QtGui.QPainterPath()
    card_path.addRoundedRect(card_rect, 8, 8)
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    fill_gradient = QtGui.QLinearGradient(card_rect.topLeft(), card_rect.topRight())
    fill_gradient.setColorAt(0.0, QtGui.QColor(42, 42, 42, 166))
    fill_gradient.setColorAt(0.68, QtGui.QColor(42, 42, 42, 132))
    fill_gradient.setColorAt(1.0, QtGui.QColor(42, 42, 42, 52))
    painter.setBrush(fill_gradient)
    painter.drawPath(card_path)

    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    stroke_gradient = QtGui.QLinearGradient(card_rect.topLeft(), card_rect.topRight())
    stroke_gradient.setColorAt(0.0, QtGui.QColor(85, 85, 85, 92))
    stroke_gradient.setColorAt(0.68, QtGui.QColor(85, 85, 85, 66))
    stroke_gradient.setColorAt(1.0, QtGui.QColor(85, 85, 85, 16))
    painter.setPen(QtGui.QPen(QtGui.QBrush(stroke_gradient), 1))
    painter.drawPath(card_path)

    content_pixmap = QtGui.QPixmap(pixmap.size())
    content_pixmap.setDevicePixelRatio(dpr)
    content_pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    content_painter = QtGui.QPainter(content_pixmap)
    content_painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    ghost.render(
        content_painter,
        QtCore.QPoint(shadow_margin, shadow_margin),
        QtGui.QRegion(),
        QtWidgets.QWidget.RenderFlag.DrawChildren,
    )
    content_painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_DestinationIn)
    content_fade = QtGui.QLinearGradient(card_rect.topLeft(), card_rect.topRight())
    content_fade.setColorAt(0.0, QtGui.QColor(255, 255, 255, 170))
    content_fade.setColorAt(0.68, QtGui.QColor(255, 255, 255, 132))
    content_fade.setColorAt(1.0, QtGui.QColor(255, 255, 255, 48))
    content_painter.fillRect(QtCore.QRectF(0, 0, pixmap_logical_size.width(), pixmap_logical_size.height()), content_fade)
    content_painter.end()

    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    painter.drawPixmap(QtCore.QPoint(0, 0), content_pixmap)
    painter.end()
    return pixmap


def _start_drag(QtCore, QtGui, QtWidgets, source, name, folder=False, child_count=0, masked=False):
    drag = QtGui.QDrag(source)
    mime = QtCore.QMimeData()
    mime.setText(name)
    mime.setData("application/x-rizum-layer-kind", b"folder" if folder else b"layer")
    mime.setData("application/x-rizum-layer-masked", b"1" if masked else b"0")
    drag.setMimeData(mime)
    drag.setPixmap(
        _make_drag_pixmap(
            QtCore,
            QtGui,
            QtWidgets,
            name,
            "folder-filled.svg" if folder else "layers.svg",
            folder=folder,
            child_count=child_count,
            masked=masked,
            source=source,
        )
    )
    drag.setHotSpot(QtCore.QPoint(15 + _DRAG_GHOST_SHADOW_MARGIN, 15 + _DRAG_GHOST_SHADOW_MARGIN))
    return drag.exec(QtCore.Qt.DropAction.CopyAction)


def make_drag_tree_item(
    name,
    icon_name="layers.svg",
    folder=False,
    draggable=False,
    removable=False,
    on_remove=None,
    masked=False,
    mapped=False,
    child=True,
    parent=None,
):
    """Create the shared PT Bridge drag/drop tree row."""
    from PySide6 import QtCore, QtGui, QtWidgets

    class _DragRow(QtWidgets.QFrame):
        def __init__(self):
            super().__init__()
            self._press_pos = None
            self._drag_started = False
            self.setObjectName("RizumDragTreeItem")
            self.setProperty("child", "true" if child else "false")
            self.setProperty("folder", bool(folder))
            self.setProperty("mapped", bool(mapped))
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.setMouseTracking(True)
            self.setCursor(
                QtCore.Qt.CursorShape.OpenHandCursor
                if draggable
                else QtCore.Qt.CursorShape.PointingHandCursor
            )
            self.setFixedHeight(34)

        def _set_hovered(self, is_hovered):
            if self.property("hovered") == is_hovered:
                return
            self.setProperty("hovered", is_hovered)
            self.style().unpolish(self)
            self.style().polish(self)

        def mousePressEvent(self, event):
            self._set_hovered(True)
            if draggable and event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._press_pos = event.position().toPoint()
                self._drag_started = False
            super().mousePressEvent(event)

        def mouseMoveEvent(self, event):
            self._set_hovered(True)
            if not draggable or self._press_pos is None:
                super().mouseMoveEvent(event)
                return
            distance = (event.position().toPoint() - self._press_pos).manhattanLength()
            if distance < QtWidgets.QApplication.startDragDistance():
                return
            self._drag_started = True
            self._press_pos = None
            self.setProperty("dragging", True)
            self.style().unpolish(self)
            self.style().polish(self)
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            _start_drag(QtCore, QtGui, QtWidgets, self, name, folder, masked=masked)
            self.setProperty("dragging", False)
            self.style().unpolish(self)
            self.style().polish(self)
            self.setCursor(
                QtCore.Qt.CursorShape.OpenHandCursor
                if draggable
                else QtCore.Qt.CursorShape.PointingHandCursor
            )

        def enterEvent(self, event):
            super().enterEvent(event)
            self._set_hovered(True)

        def leaveEvent(self, event):
            super().leaveEvent(event)
            self._set_hovered(False)

    class _RemoveButton(QtWidgets.QPushButton):
        def __init__(self):
            super().__init__("")
            self.setObjectName("RizumRemoveButton")
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.setFixedSize(24, 24)

        def paintEvent(self, event):
            super().paintEvent(event)
            if not self.underMouse():
                return
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            pen = QtGui.QPen(QtGui.QColor("#ff453a"), 1.25)
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            center = QtCore.QPointF(self.width() / 2, self.height() / 2)
            half = 3.25
            painter.drawLine(
                QtCore.QPointF(center.x() - half, center.y() - half),
                QtCore.QPointF(center.x() + half, center.y() + half),
            )
            painter.drawLine(
                QtCore.QPointF(center.x() - half, center.y() + half),
                QtCore.QPointF(center.x() + half, center.y() - half),
            )
            painter.end()

    row = _DragRow()
    row_layout = QtWidgets.QHBoxLayout(row)
    row_layout.setContentsMargins(8, 4, 8, 4)
    row_layout.setSpacing(10)
    row_layout.addWidget(make_tree_icon_label(icon_name, folder=folder, masked=masked))

    label = QtWidgets.QLabel(name)
    label.setObjectName("RizumDragItemName")
    label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    row_layout.addWidget(label, 1)

    if removable:
        remove = _RemoveButton()
        remove.clicked.connect(
            lambda: on_remove(row._rizum_host)
            if on_remove is not None
            else row._rizum_host.deleteLater()
        )
        row_layout.addWidget(remove)

    host = QtWidgets.QFrame(parent)
    host.setObjectName("RizumDragTreeItemHost")
    host.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
    host.setMouseTracking(True)
    host.setFixedHeight(36 if child else 34)
    host_layout = QtWidgets.QHBoxLayout(host)
    host_layout.setContentsMargins(24 if child else 0, 0, 4 if child else 0, 0)
    host_layout.setSpacing(0)
    host_layout.addWidget(row)
    host._rizum_row = row
    host._rizum_label = label
    host._rizum_name = name
    host._rizum_folder = bool(folder)
    host._rizum_masked = bool(masked)
    row._rizum_host = host
    row._rizum_label = label

    def set_host_hovered(is_hovered):
        row._set_hovered(is_hovered)

    host.enterEvent = lambda event: set_host_hovered(True)
    host.leaveEvent = lambda event: set_host_hovered(False)
    return host


def animate_drag_tree_item_added(item, group=None, duration=300):
    """Reveal a newly dropped row with the PT Bridge slide-in timing."""
    from PySide6 import QtCore, QtWidgets

    row = getattr(item, "_rizum_row", item)
    old_animation = getattr(item, "_rizum_added_animation", None)
    if old_animation is not None:
        old_animation.stop()
    final_host_height = max(
        1,
        int(getattr(item, "_rizum_added_final_host_height", 0) or 0),
        item.height() or 0,
        item.sizeHint().height() or 0,
        36,
    )
    final_row_height = max(
        1,
        int(getattr(row, "_rizum_added_final_row_height", 0) or 0),
        row.height() or 0,
        row.sizeHint().height() or 0,
        34,
    )
    item.setProperty("added", True)
    row.setProperty("added", True)
    row.style().unpolish(row)
    row.style().polish(row)
    item.setFixedHeight(0)
    row.setFixedHeight(0)
    if group is not None:
        group.refreshLayout()

    opacity = QtWidgets.QGraphicsOpacityEffect(row)
    opacity.setOpacity(0.0)
    row.setGraphicsEffect(opacity)

    height_animation = QtCore.QVariantAnimation(item)
    height_animation.setStartValue(0)
    height_animation.setEndValue(final_host_height)
    height_animation.setDuration(duration)
    height_animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

    def set_height(value):
        host_height = int(round(value))
        row_height = int(round(final_row_height * (host_height / final_host_height)))
        item.setFixedHeight(host_height)
        row.setFixedHeight(row_height)
        if group is not None:
            group.refreshLayout()

    height_animation.valueChanged.connect(set_height)

    opacity_animation = QtCore.QPropertyAnimation(opacity, b"opacity", item)
    opacity_animation.setStartValue(0.0)
    opacity_animation.setEndValue(1.0)
    opacity_animation.setDuration(duration)
    opacity_animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

    animation_group = QtCore.QParallelAnimationGroup(item)
    animation_group.addAnimation(height_animation)
    animation_group.addAnimation(opacity_animation)

    def finish():
        item.setFixedHeight(final_host_height)
        row.setFixedHeight(final_row_height)
        row.setGraphicsEffect(None)
        item.setProperty("added", False)
        row.setProperty("added", False)
        row.style().unpolish(row)
        row.style().polish(row)
        if group is not None:
            group.refreshLayout()

    animation_group.finished.connect(finish)
    item._rizum_added_animation = animation_group
    animation_group.start()


def make_spin_input(value=1.0, minimum=0.75, maximum=2.0, step=0.05, decimals=2):
    """Create a functional compact spin input with Painter-style arrows."""
    from PySide6 import QtCore, QtWidgets

    class _SpinInput(QtWidgets.QFrame):
        valueChanged = QtCore.Signal(float)

        def __init__(self):
            super().__init__()
            self.setObjectName("RizumMockInput")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.setFixedHeight(32)
            self._minimum = minimum
            self._maximum = maximum
            self._step = step
            self._decimals = decimals
            self._value = minimum

            layout = QtWidgets.QHBoxLayout(self)
            layout.setContentsMargins(11, 2, 2, 2)
            layout.setSpacing(8)
            self._label = QtWidgets.QLabel()
            self._label.setObjectName("RizumMockText")
            self._label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self._label.setMinimumWidth(0)
            self._label.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Preferred,
            )
            layout.addWidget(self._label, 1)
            self._stepper_buttons = CompactStepperButtons(
                lambda direction: self._step_by(self._step * direction),
                size=28,
            )
            layout.addWidget(self._stepper_buttons)

            self.setValue(value)
            self.setMinimumWidth(self.sizeHint().width())

        def value(self):
            return self._value

        def setValue(self, value):
            next_value = max(self._minimum, min(self._maximum, float(value)))
            if round(next_value, self._decimals) == round(self._value, self._decimals):
                self._value = next_value
                self._label.setText(f"{self._value:.{self._decimals}f}")
                return
            self._value = next_value
            self._label.setText(f"{self._value:.{self._decimals}f}")
            self.valueChanged.emit(self._value)

        def setRange(self, minimum, maximum):
            self._minimum = float(minimum)
            self._maximum = float(maximum)
            self.setValue(self._value)

        def setSingleStep(self, step):
            self._step = float(step)

        def setDecimals(self, decimals):
            self._decimals = int(decimals)
            self._label.setText(f"{self._value:.{self._decimals}f}")

        def setCompactHeight(self, height):
            """Scale the spin input height and its internal stepper buttons."""
            height = int(height)
            self.setFixedHeight(height)
            scale = height / 32.0
            vertical_margin = max(2, int(round(2 * scale)))
            left_margin = max(4, int(round(11 * scale)))
            right_margin = max(2, int(round(2 * scale)))
            self.layout().setContentsMargins(left_margin, vertical_margin, right_margin, vertical_margin)
            self._label.setMinimumHeight(max(0, height - vertical_margin * 2))
            # Stepper buttons default to 28 at height 32; scale proportionally.
            stepper_size = max(21, int(round(28 * scale)))
            self._stepper_buttons.setButtonSize(stepper_size)

        def wheelEvent(self, event):
            direction = 1 if event.angleDelta().y() > 0 else -1
            self._step_by(self._step * direction)

        def _step_by(self, delta):
            self.setValue(self._value + delta)

    return _SpinInput()


def make_compact_stepper(
    value=8,
    minimum=0,
    maximum=999,
    step=1,
    decimals=0,
):
    """Create a compact editable numeric stepper with Painter-style controls."""
    from PySide6 import QtCore, QtGui, QtWidgets

    from .theme import default_theme

    class _StepperLineEdit(QtWidgets.QLineEdit):
        _alignment = (
            QtCore.Qt.AlignmentFlag.AlignLeft
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )

        def __init__(self, parent=None):
            super().__init__(parent)
            super().setAlignment(self._alignment)

        def setAlignment(self, _alignment):
            # Painter host styling must not move the native editing baseline.
            super().setAlignment(self._alignment)

        def paintEvent(self, event):
            # QLineEdit keeps native input, selection, and cursor-position
            # behavior, while the parent owns every visible pixel. Painter's
            # host style can otherwise shift this text or reveal a second caret.
            event.accept()

    class _CompactStepper(QtWidgets.QWidget):
        valueChanged = QtCore.Signal(object)

        def __init__(self):
            super().__init__()
            self.setObjectName("RizumCompactStepper")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.setMouseTracking(True)
            self.setFixedSize(120, 32)
            self._compact_height = 32
            self._decimals = max(0, int(decimals))
            number_type = float if self._decimals else int
            self._minimum = number_type(minimum)
            self._maximum = number_type(maximum)
            self._step = number_type(step)
            self._value = self._normalized_value(value)
            self._hover_part = None
            self._pressed_part = None
            self._animated_part = None
            self._visual_scale = 1.0
            self._visual_opacity = 1.0
            self._animation = None
            self._editing = False
            self._replace_on_type = False
            self._outside_click_filter_installed = False
            self._theme = {
                "background": default_theme.surface,
                "text": default_theme.text,
                "muted": default_theme.text_muted,
                "hover": default_theme.surface_child_hover,
            }
            self._editor = _StepperLineEdit(self)
            self._editor.setObjectName("RizumCompactStepperEditor")
            self._editor.setFrame(False)
            self._editor.setMaxLength(16)
            self._editor.setCursor(QtCore.Qt.CursorShape.IBeamCursor)
            self._editor.editingFinished.connect(self._commit_edit)
            self._editor.textChanged.connect(self._editor_visual_changed)
            self._editor.cursorPositionChanged.connect(
                self._editor_visual_changed
            )
            self._editor.selectionChanged.connect(self._editor_visual_changed)
            self._cursor_visible = False
            self._cursor_timer = QtCore.QTimer(self)
            self._cursor_timer.setInterval(
                max(200, QtWidgets.QApplication.cursorFlashTime() // 2)
            )
            self._cursor_timer.timeout.connect(self._toggle_edit_cursor)
            if self._decimals:
                validator = QtGui.QDoubleValidator(
                    float(self._minimum),
                    float(self._maximum),
                    self._decimals,
                    self._editor,
                )
                validator.setNotation(
                    QtGui.QDoubleValidator.Notation.StandardNotation
                )
                validator.setLocale(QtCore.QLocale.c())
            else:
                validator = QtGui.QIntValidator(
                    int(self._minimum),
                    int(self._maximum),
                    self._editor,
                )
            self._editor.setValidator(validator)
            self._editor.hide()
            self._sync_editor_geometry()
            self._sync_editor_style()
            self.setValue(value, emit=False)

        def setTheme(self, theme):
            self._theme = {
                "background": theme.get("window_bg", default_theme.surface),
                "text": theme.get("text", default_theme.text),
                "muted": theme.get(
                    "muted",
                    theme.get("text_secondary", default_theme.text_muted),
                ),
                "hover": theme.get(
                    "control_hover",
                    theme.get("hover", default_theme.surface_child_hover),
                ),
            }
            self._sync_editor_style()
            self.update()

        def value(self):
            return self._value

        def setValue(self, value, emit=True):
            next_value = self._normalized_value(value)
            if next_value == self._value:
                if not self._editing:
                    self._editor.setText(self._formatted_value(self._value))
                return
            self._value = next_value
            if not self._editing:
                self._editor.setText(self._formatted_value(self._value))
            self.update()
            if emit:
                self.valueChanged.emit(self._value)

        def setRange(self, minimum, maximum):
            number_type = float if self._decimals else int
            self._minimum = number_type(minimum)
            self._maximum = number_type(maximum)
            self.setValue(self._value)

        def setSingleStep(self, step):
            number_type = float if self._decimals else int
            self._step = number_type(step)

        def setCompactHeight(self, height):
            """Scale the frame and painted geometry from the 32px baseline."""
            self._compact_height = max(24, int(round(height)))
            scale = self._compact_height / 32.0
            self.setFixedSize(
                max(90, int(round(120 * scale))),
                self._compact_height,
            )
            self._sync_editor_geometry()
            self._sync_editor_style()
            self.updateGeometry()
            self.update()

        def _normalized_value(self, value):
            number = float(value)
            number = max(float(self._minimum), min(float(self._maximum), number))
            if self._decimals:
                return round(number, self._decimals)
            return int(round(number))

        def _formatted_value(self, value):
            if self._decimals:
                return f"{float(value):.{self._decimals}f}"
            return str(int(round(float(value))))

        def _sync_editor_geometry(self):
            scale = self._geometry_scale()
            value_rect = self._rect_for("value")
            self._editor.setGeometry(
                int(round(value_rect.left())),
                0,
                max(1, int(round(value_rect.width()))),
                self._compact_height,
            )
            self._editor.setTextMargins(
                max(0, int(round(11 * scale)) - 2),
                0,
                int(round(3 * scale)),
                0,
            )

        def _sync_editor_style(self):
            font = self._value_font()
            self._editor.setFont(font)
            family = font.family().replace("\\", "\\\\").replace('"', '\\"')
            text_color = QtGui.QColor(self._theme["text"])
            if not text_color.isValid():
                text_color = QtGui.QColor(default_theme.text)
            text_name = text_color.name()
            self._editor.setStyleSheet(
                f"""
QLineEdit#RizumCompactStepperEditor {{
    background: transparent;
    border: 0;
    padding: 0;
    margin: 0;
    color: {text_name};
    selection-background-color: transparent;
    selection-color: {text_name};
    font-family: "{family}";
    font-size: {font.pixelSize()}px;
    font-weight: {font.weight()};
}}
"""
            )
            palette = self._editor.palette()
            transparent = QtGui.QColor(0, 0, 0, 0)
            palette.setColor(QtGui.QPalette.ColorRole.Text, text_color)
            palette.setColor(
                QtGui.QPalette.ColorRole.HighlightedText,
                text_color,
            )
            palette.setColor(QtGui.QPalette.ColorRole.Highlight, transparent)
            self._editor.setPalette(palette)

        def _editor_visual_changed(self, *_args):
            if self._editing:
                self._cursor_visible = True
                self._cursor_timer.start()
                self.update()

        def _toggle_edit_cursor(self):
            if not self._editing or not self._editor.hasFocus():
                self._cursor_visible = False
                self._cursor_timer.stop()
                return
            self._cursor_visible = not self._cursor_visible
            self.update()

        def _geometry_scale(self):
            return self._compact_height / 32.0

        def getVisualScale(self):
            return self._visual_scale

        def setVisualScale(self, value):
            self._visual_scale = float(value)
            self.update()

        def getVisualOpacity(self):
            return self._visual_opacity

        def setVisualOpacity(self, value):
            self._visual_opacity = float(value)
            self.update()

        visualScale = QtCore.Property(float, getVisualScale, setVisualScale)
        visualOpacity = QtCore.Property(float, getVisualOpacity, setVisualOpacity)

        def _rect_for(self, part):
            # Layout: [value][-][+] with 28x28 buttons centered vertically in
            # the 32px height. Text starts at x=11 so the left visual gap
            # matches the + glyph's right visual gap (~11px).
            scale = self._geometry_scale()
            if part == "value":
                return QtCore.QRectF(0, 0, 54 * scale, 32 * scale)
            x = 60 if part == "minus" else 90
            return QtCore.QRectF(
                x * scale,
                2 * scale,
                28 * scale,
                28 * scale,
            )

        def _hover_rect_for(self, part):
            rect = self._rect_for(part)
            if part == "value":
                return rect
            return rect.adjusted(1, 1, -1, -1)

        def _hover_color(self):
            color = self._theme.get("hover", default_theme.surface_child_hover)
            if isinstance(color, QtGui.QColor):
                parsed = QtGui.QColor(color)
                return self._composited_hover_color(parsed)
            text = str(color).strip()
            if text.startswith("rgba(") and text.endswith(")"):
                values = [part.strip() for part in text[5:-1].split(",")]
                if len(values) == 4:
                    red, green, blue = (int(float(value)) for value in values[:3])
                    alpha_value = float(values[3])
                    alpha = round(alpha_value * 255) if alpha_value <= 1 else round(alpha_value)
                    parsed = QtGui.QColor(red, green, blue, max(0, min(255, alpha)))
                    return self._composited_hover_color(parsed)
            parsed = QtGui.QColor(text)
            if parsed.isValid():
                return self._composited_hover_color(parsed)
            return self._composited_hover_color(QtGui.QColor(255, 255, 255, 10))

        def _composited_hover_color(self, overlay):
            if overlay.alpha() >= 255:
                return overlay
            base = QtGui.QColor(self._theme.get("background", default_theme.surface))
            if not base.isValid():
                base = QtGui.QColor(default_theme.surface)
            alpha = overlay.alphaF()
            return QtGui.QColor(
                round(overlay.red() * alpha + base.red() * (1 - alpha)),
                round(overlay.green() * alpha + base.green() * (1 - alpha)),
                round(overlay.blue() * alpha + base.blue() * (1 - alpha)),
            )

        def _part_at(self, pos):
            for part in ("minus", "value", "plus"):
                if self._rect_for(part).contains(QtCore.QPointF(pos)):
                    return part
            return None

        def _animate_part(self, part, scale, opacity, duration):
            if self._animation is not None:
                self._animation.stop()
            self._animated_part = part
            group = QtCore.QParallelAnimationGroup(self)
            for prop, start, end in (
                (b"visualScale", self._visual_scale, scale),
                (b"visualOpacity", self._visual_opacity, opacity),
            ):
                animation = QtCore.QPropertyAnimation(self, prop, self)
                animation.setDuration(duration)
                animation.setStartValue(start)
                animation.setEndValue(float(end))
                animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
                group.addAnimation(animation)
            self._animation = group
            if scale == 1.0 and opacity == 1.0:
                group.finished.connect(lambda: self._clear_finished_animation(part))
            group.start()

        def _clear_finished_animation(self, part):
            if self._animated_part == part:
                self._animated_part = None
                self.update()

        def _step_by(self, direction):
            self._commit_edit()
            self.setValue(self._value + direction * self._step)

        def _start_edit(self):
            if self._editing:
                return
            self._editing = True
            self._replace_on_type = True
            self._editor.setText(self._formatted_value(self._value))
            self._editor.setCursorPosition(len(self._editor.text()))
            self._editor.show()
            self._editor.raise_()
            self._editor.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
            self._cursor_visible = True
            self._cursor_timer.start()
            app = QtWidgets.QApplication.instance()
            if app is not None and not self._outside_click_filter_installed:
                app.installEventFilter(self)
                self._outside_click_filter_installed = True
            self.update()

        def _commit_edit(self):
            if not self._editing:
                return
            text = self._editor.text().strip()
            if text not in ("", "-", ".", "-."):
                try:
                    self.setValue(float(text))
                except ValueError:
                    pass
            self._finish_edit()

        def _cancel_edit(self):
            if not self._editing:
                return
            self._finish_edit()

        def _finish_edit(self):
            self._editing = False
            self._replace_on_type = False
            self._cursor_visible = False
            self._cursor_timer.stop()
            app = QtWidgets.QApplication.instance()
            if app is not None and self._outside_click_filter_installed:
                app.removeEventFilter(self)
                self._outside_click_filter_installed = False
            self._editor.hide()
            self._editor.setText(self._formatted_value(self._value))
            self.update()

        def eventFilter(self, watched, event):
            if not self._editing:
                return super().eventFilter(watched, event)

            if watched is self._editor:
                if event.type() == QtCore.QEvent.Type.KeyPress:
                    key = event.key()
                    if key in (
                        QtCore.Qt.Key.Key_Return,
                        QtCore.Qt.Key.Key_Enter,
                    ):
                        self._commit_edit()
                        event.accept()
                        return True
                    if key == QtCore.Qt.Key.Key_Escape:
                        self._cancel_edit()
                        event.accept()
                        return True

                    modifiers = event.modifiers()
                    blocked_modifiers = (
                        QtCore.Qt.KeyboardModifier.ControlModifier
                        | QtCore.Qt.KeyboardModifier.AltModifier
                        | QtCore.Qt.KeyboardModifier.MetaModifier
                    )
                    typed_text = event.text()
                    is_decimal = self._decimals and typed_text in (".", ",")
                    is_negative = typed_text == "-" and self._minimum < 0
                    is_number_character = bool(
                        typed_text
                        and (
                            typed_text.isdigit()
                            or is_decimal
                            or is_negative
                        )
                    )
                    if (
                        self._replace_on_type
                        and is_number_character
                        and not modifiers & blocked_modifiers
                    ):
                        self._editor.clear()
                    if is_decimal and typed_text == ",":
                        self._editor.insert(".")
                        self._replace_on_type = False
                        event.accept()
                        return True
                    if (
                        is_number_character
                        or modifiers & blocked_modifiers
                        or key
                        in (
                            QtCore.Qt.Key.Key_Backspace,
                            QtCore.Qt.Key.Key_Delete,
                            QtCore.Qt.Key.Key_Left,
                            QtCore.Qt.Key.Key_Right,
                            QtCore.Qt.Key.Key_Home,
                            QtCore.Qt.Key.Key_End,
                            QtCore.Qt.Key.Key_Tab,
                            QtCore.Qt.Key.Key_Backtab,
                        )
                    ):
                        self._replace_on_type = False
                elif event.type() == QtCore.QEvent.Type.MouseButtonPress:
                    self._replace_on_type = False

            if event.type() == QtCore.QEvent.Type.MouseButtonPress:
                global_position = event.globalPosition().toPoint()
                local_position = self.mapFromGlobal(global_position)
                if not self.rect().contains(local_position):
                    self._commit_edit()

            return super().eventFilter(watched, event)

        def enterEvent(self, event):
            super().enterEvent(event)
            self._hover_part = self._part_at(event.position().toPoint() if hasattr(event, "position") else event.pos())
            self.update()

        def event(self, event):
            if event.type() in (
                QtCore.QEvent.Type.HoverEnter,
                QtCore.QEvent.Type.HoverMove,
            ):
                position = event.position().toPoint() if hasattr(event, "position") else event.pos()
                next_part = self._part_at(position)
                if next_part != self._hover_part:
                    self._hover_part = next_part
                    self.update()
            elif event.type() == QtCore.QEvent.Type.HoverLeave:
                self._hover_part = None
                self.update()
            return super().event(event)

        def leaveEvent(self, event):
            super().leaveEvent(event)
            self._hover_part = None
            self._pressed_part = None
            if self._animated_part is not None:
                self._animate_part(self._animated_part, 1.0, 1.0, 160)
            self.update()

        def mouseMoveEvent(self, event):
            super().mouseMoveEvent(event)
            next_part = self._part_at(event.position().toPoint() if hasattr(event, "position") else event.pos())
            if next_part != self._hover_part:
                self._hover_part = next_part
                self.update()

        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._pressed_part = self._part_at(event.position().toPoint() if hasattr(event, "position") else event.pos())
                if self._pressed_part in ("minus", "plus"):
                    self._animate_part(self._pressed_part, 0.85, 0.7, 80)
                event.accept()
                return
            super().mousePressEvent(event)

        def mouseReleaseEvent(self, event):
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                part = self._part_at(event.position().toPoint() if hasattr(event, "position") else event.pos())
                pressed_part = self._pressed_part
                if pressed_part is not None and part == pressed_part:
                    if part == "minus":
                        self._step_by(-1)
                    elif part == "plus":
                        self._step_by(1)
                    elif part == "value":
                        self._start_edit()
                elif part != "value":
                    self._commit_edit()
                self._pressed_part = None
                if pressed_part in ("minus", "plus"):
                    self._animate_part(pressed_part, 1.0, 1.0, 180)
                event.accept()
                return
            super().mouseReleaseEvent(event)

        def keyPressEvent(self, event):
            if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
                self._start_edit()
                event.accept()
                return
            if event.key() in (QtCore.Qt.Key.Key_Minus, QtCore.Qt.Key.Key_Left):
                self._step_by(-1)
                event.accept()
                return
            if event.key() in (QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Right):
                self._step_by(1)
                event.accept()
                return
            super().keyPressEvent(event)

        def focusOutEvent(self, event):
            super().focusOutEvent(event)

        def wheelEvent(self, event):
            direction = 1 if event.angleDelta().y() > 0 else -1
            self._step_by(direction)
            event.accept()

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)

            for part in ("minus", "value", "plus"):
                is_hovered = part == self._hover_part or (part == "value" and self._editing)
                is_pressed = part == self._pressed_part
                if is_pressed and part in ("minus", "plus"):
                    rect = self._hover_rect_for(part)
                    painter.setPen(QtCore.Qt.PenStyle.NoPen)
                    painter.setBrush(QtGui.QColor(255, 255, 255, 75))
                    radius = 6 * self._geometry_scale()
                    painter.drawRoundedRect(rect, radius, radius)
                elif is_hovered:
                    rect = self._hover_rect_for(part)
                    painter.setPen(QtCore.Qt.PenStyle.NoPen)
                    painter.setBrush(self._hover_color())
                    radius = 6 * self._geometry_scale()
                    painter.drawRoundedRect(rect, radius, radius)

            symbol_center_y = self._value_visual_center_y()
            self._draw_step_symbol(painter, "minus", symbol_center_y)
            self._draw_value_text(painter)
            if (
                self._editing
                and self._editor.hasFocus()
                and self._cursor_visible
            ):
                self._draw_edit_cursor(painter)
            self._draw_step_symbol(painter, "plus", symbol_center_y)
            painter.end()

        def _value_font(self):
            font = QtGui.QFont(self.font())
            font.setPixelSize(
                max(11, int(round(14 * self._geometry_scale())))
            )
            font.setWeight(QtGui.QFont.Weight.Medium)
            return font

        def _value_baseline(self, font):
            metrics = QtGui.QFontMetrics(font)
            return float(
                (self._compact_height - metrics.height() + 1) // 2
                + metrics.ascent()
            )

        def _value_visual_center_y(self):
            font = self._value_font()
            metrics = QtGui.QFontMetricsF(font)
            baseline = self._value_baseline(font)
            bounds = metrics.tightBoundingRect("8")
            return baseline + bounds.y() + bounds.height() / 2

        def _value_text(self):
            if self._editing:
                return self._editor.text()
            return str(self._value)

        def _draw_value_text(self, painter):
            rect = self._rect_for("value")
            font = self._value_font()
            painter.setFont(font)
            baseline = self._value_baseline(font)
            scale = self._geometry_scale()
            text_x = 11 * scale
            if self._editing and self._editor.hasSelectedText():
                selection_start = self._editor.selectionStart()
                selection_end = selection_start + len(
                    self._editor.selectedText()
                )
                metrics = QtGui.QFontMetricsF(font)
                selection_left = text_x + metrics.horizontalAdvance(
                    self._value_text()[:selection_start]
                )
                selection_width = metrics.horizontalAdvance(
                    self._value_text()[selection_start:selection_end]
                )
                selection_rect = QtCore.QRectF(
                    selection_left,
                    rect.center().y() - 9 * scale,
                    selection_width,
                    18 * scale,
                )
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.setBrush(QtGui.QColor("#555555"))
                painter.drawRoundedRect(
                    selection_rect,
                    2 * scale,
                    2 * scale,
                )
            painter.setPen(QtGui.QColor(self._theme["text"]))
            # Left-align the number so it lines up with combo input text.
            painter.drawText(
                QtCore.QPointF(text_x, baseline),
                self._value_text(),
            )

        def _draw_edit_cursor(self, painter):
            font = self._value_font()
            metrics = QtGui.QFontMetricsF(font)
            scale = self._geometry_scale()
            cursor_position = max(
                0,
                min(self._editor.cursorPosition(), len(self._value_text())),
            )
            cursor_x = (
                11 * scale
                + metrics.horizontalAdvance(
                    self._value_text()[:cursor_position]
                )
                + scale
            )
            baseline = self._value_baseline(font)
            cursor_top = baseline - metrics.ascent()
            cursor_bottom = baseline + max(metrics.descent(), scale)
            painter.setPen(
                QtGui.QPen(
                    QtGui.QColor(self._theme["text"]),
                    max(1.0, scale),
                )
            )
            painter.drawLine(
                QtCore.QPointF(cursor_x, cursor_top),
                QtCore.QPointF(cursor_x, cursor_bottom),
            )

        def _draw_step_symbol(self, painter, part, center_y):
            rect = self._rect_for(part)
            scale = self._visual_scale if part == self._animated_part else 1.0
            opacity = self._visual_opacity if part == self._animated_part else 1.0
            color = self._theme["text"] if part == self._hover_part else self._theme["muted"]
            geometry_scale = self._geometry_scale()
            pen = QtGui.QPen(
                QtGui.QColor(color),
                max(1.35, 1.8 * geometry_scale),
            )
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            previous_opacity = painter.opacity()
            painter.setOpacity(previous_opacity * max(0.0, min(1.0, opacity)))
            painter.setPen(pen)
            half = 4.8 * scale * geometry_scale
            center = QtCore.QPointF(
                rect.center().x(),
                center_y - 0.5 * geometry_scale,
            )
            painter.drawLine(
                QtCore.QPointF(center.x() - half, center.y()),
                QtCore.QPointF(center.x() + half, center.y()),
            )
            if part == "plus":
                painter.drawLine(
                    QtCore.QPointF(center.x(), center.y() - half),
                    QtCore.QPointF(center.x(), center.y() + half),
                )
            painter.setOpacity(previous_opacity)

    return _CompactStepper()


def make_combo_input(options=None):
    """Create a functional compact combo input backed by a lightweight menu."""
    from PySide6 import QtCore, QtGui, QtWidgets

    class _ComboInput(QtWidgets.QFrame):
        currentIndexChanged = QtCore.Signal(int)

        def __init__(self):
            super().__init__()
            self.setObjectName("RizumMockInput")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.setFixedHeight(32)
            self._items = []
            self._current_index = -1
            self._menu = None
            self._last_menu_close_ms = 0
            self._fit_to_contents = True
            self._display_prefix = ""
            self._display_value = ""
            self._popup_alignment = "left"

            layout = QtWidgets.QHBoxLayout(self)
            layout.setContentsMargins(11, 2, 8, 2)
            layout.setSpacing(8)
            self._label = QtWidgets.QLabel()
            self._label.setObjectName("RizumMockText")
            self._label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._label.setTextFormat(QtCore.Qt.TextFormat.RichText)
            self._label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self._label.setMinimumWidth(0)
            self._label.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Preferred,
            )
            layout.addWidget(self._label, 1)
            # Chevron is drawn by _ComboInput.paintEvent (not a child widget)
            # so it inherits the combo's background including hover states.
            self._arrow_size = 14
            self._arrow_angle = 0.0
            self._arrow_anim = None

            for item in options or []:
                if isinstance(item, tuple):
                    self.addItem(item[0], item[1])
                else:
                    self.addItem(item, item)
            self.fitToContents()

        def clear(self):
            self._items = []
            self._current_index = -1
            self._display_prefix = ""
            self._display_value = ""
            self._label.setText("")
            if self._fit_to_contents:
                self.setFixedWidth(0)

        def addItem(self, text, userData=None):
            self._items.append((text, userData))
            if self._current_index < 0:
                self.setCurrentIndex(0)
            self.fitToContents()

        def setItems(self, items):
            current_data = self.currentData()
            self._items = []
            self._current_index = -1
            self._label.setText("")
            for item in items or []:
                if isinstance(item, tuple):
                    self._items.append((item[0], item[1]))
                else:
                    self._items.append((item, item))
            next_index = 0
            if current_data is not None:
                for index, item in enumerate(self._items):
                    if item[1] == current_data:
                        next_index = index
                        break
            if self._items:
                self.setCurrentIndex(next_index)
            self.fitToContents()

        def setFitToContents(self, enabled):
            self._fit_to_contents = bool(enabled)
            if self._fit_to_contents:
                self.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Preferred,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
                self.fitToContents()
            else:
                self._label.setMinimumWidth(0)
                self.setMinimumWidth(0)
                self.setMaximumWidth(16777215)
                self.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Expanding,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )

        def fitToContents(self):
            if not self._fit_to_contents or not self._items:
                return
            if not _is_qt_object_alive(self):
                return
            label = getattr(self, "_label", None)
            layout = self.layout()
            if not _is_qt_object_alive(label) or layout is None:
                return
            try:
                metrics = label.fontMetrics()
            except RuntimeError:
                return
            display_texts = [str(item[0]) for item in self._items]
            if self._display_prefix or self._display_value:
                display_texts.append(f"{self._display_prefix} {self._display_value}".strip())
            text_width = max(metrics.horizontalAdvance(text) for text in display_texts)
            margins = layout.contentsMargins()
            width = (
                text_width
                + margins.left()
                + margins.right()
                + layout.spacing()
                + self._arrow_size
                + 6
            )
            try:
                label.setMinimumWidth(text_width)
                self.setFixedWidth(width)
            except RuntimeError:
                return

        def refreshMetrics(self):
            self.fitToContents()

        def setCompactHeight(self, height):
            height = int(height)
            self.setFixedHeight(height)
            vertical_margin = 3 if height <= 28 else 4
            self.layout().setContentsMargins(8, vertical_margin, 10, vertical_margin)
            self._label.setMinimumHeight(max(0, height - vertical_margin * 2))
            # Chevron size scales with the control height (default 14 at 32).
            self._arrow_size = max(11, int(round(14 * height / 32.0)))
            self.fitToContents()

        def setPopupAlignment(self, alignment):
            self._popup_alignment = "right" if str(alignment).lower() == "right" else "left"

        def setDisplayParts(self, prefix, value):
            self._display_prefix = str(prefix)
            self._display_value = str(value)
            self._label.setText(
                '<span style="color:#666666; font-weight:400;">'
                + escape(self._display_prefix)
                + '</span> <span style="color:#e0e0e0;">'
                + escape(self._display_value)
                + "</span>"
            )
            self.fitToContents()

        def showEvent(self, event):
            super().showEvent(event)
            if self._fit_to_contents:
                self._queueFitToContents()

        def changeEvent(self, event):
            super().changeEvent(event)
            if (
                self._fit_to_contents
                and event.type()
                in (
                    QtCore.QEvent.Type.FontChange,
                    QtCore.QEvent.Type.ApplicationFontChange,
                    QtCore.QEvent.Type.StyleChange,
                    QtCore.QEvent.Type.Polish,
                )
            ):
                self._queueFitToContents()

        def _queueFitToContents(self):
            QtCore.QTimer.singleShot(0, self._fitToContentsIfAlive)

        def _fitToContentsIfAlive(self):
            if _is_qt_object_alive(self):
                self.fitToContents()

        def findData(self, data):
            for index, item in enumerate(self._items):
                if item[1] == data:
                    return index
            return -1

        def setCurrentIndex(self, index):
            if index < 0 or index >= len(self._items):
                return
            changed = index != self._current_index
            self._current_index = index
            if self._display_prefix:
                self.setDisplayParts(self._display_prefix, self._items[index][0])
            else:
                self._label.setText(self._items[index][0])
            if changed:
                self.currentIndexChanged.emit(index)

        def currentIndex(self):
            return self._current_index

        def currentText(self):
            if self._current_index < 0:
                return ""
            return self._items[self._current_index][0]

        def currentData(self):
            if self._current_index < 0:
                return None
            return self._items[self._current_index][1]

        def mousePressEvent(self, event):
            if event.button() != QtCore.Qt.MouseButton.LeftButton:
                return
            if not self._items:
                return
            now = QtCore.QDateTime.currentMSecsSinceEpoch()
            if now - self._last_menu_close_ms < 180:
                return
            if self._menu is not None and self._menu.isVisible():
                self._menu.close()
                return
            menu = QtWidgets.QMenu(self)
            menu.setObjectName("RizumPopupMenu")
            menu.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            try:
                menu.setWindowFlag(QtCore.Qt.WindowType.NoDropShadowWindowHint, True)
            except Exception:
                pass
            for index, item in enumerate(self._items):
                action = menu.addAction(item[0])
                action.triggered.connect(lambda checked=False, i=index: self.setCurrentIndex(i))
            self._menu = menu
            menu.aboutToHide.connect(self._close_menu)
            self._set_arrow_open(True)
            menu.ensurePolished()
            menu_width = max(menu.sizeHint().width(), self.width())
            menu.setFixedWidth(menu_width)
            popup_x = self.width() - menu_width if self._popup_alignment == "right" else 0
            # Start fully transparent so the popup never flashes at full opacity
            # before the open animation begins.
            menu.setWindowOpacity(0.0)
            menu.popup(self.mapToGlobal(QtCore.QPoint(popup_x, self.height() + 4)))
            QtCore.QTimer.singleShot(0, lambda: self._applyMenuMask(menu))
            QtCore.QTimer.singleShot(0, lambda: self._animate_menu_open(menu))

        def _applyMenuMask(self, menu):
            if not _is_qt_object_alive(menu):
                return
            rect = menu.rect()
            if rect.isEmpty():
                return
            # QMenu background fills the entire widget rect even with
            # border-radius, bleeding past the rounded corners. A mask clips
            # those corner pixels. The mask matches the full rect (no inset)
            # so the border stays visible on all four sides; only the
            # transparent corner triangles outside the radius are removed.
            path = QtGui.QPainterPath()
            path.addRoundedRect(QtCore.QRectF(rect), 6, 6)
            region = QtGui.QRegion()
            for polygon in path.toSubpathPolygons():
                region += QtGui.QRegion(polygon.toPolygon())
            menu.setMask(region)

        def _animate_menu_open(self, menu):
            if not _is_qt_object_alive(menu) or not menu.isVisible():
                try:
                    menu.setWindowOpacity(1.0)
                except Exception:
                    pass
                return
            # Read the settled position (Qt may have corrected it to keep the
            # popup on-screen) and animate from 6px above so the menu appears
            # to drop out of the combo.
            target = menu.pos()
            start = QtCore.QPoint(target.x(), target.y() - 6)
            menu.move(start)

            fade = QtCore.QPropertyAnimation(menu, b"windowOpacity", menu)
            fade.setDuration(140)
            fade.setStartValue(0.0)
            fade.setEndValue(1.0)
            fade.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

            slide = QtCore.QPropertyAnimation(menu, b"pos", menu)
            slide.setDuration(180)
            slide.setStartValue(start)
            slide.setEndValue(target)
            slide.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

            menu._rizum_popup_fade = fade
            menu._rizum_popup_slide = slide
            fade.start()
            slide.start()

        def _close_menu(self):
            self._set_arrow_open(False)
            self._last_menu_close_ms = QtCore.QDateTime.currentMSecsSinceEpoch()
            self._menu = None

        def _set_arrow_open(self, is_open):
            target = 180.0 if is_open else 0.0
            old_anim = getattr(self, "_arrow_anim", None)
            if old_anim is not None:
                old_anim.stop()
            anim = QtCore.QPropertyAnimation(self, b"arrowAngle", self)
            anim.setDuration(180)
            anim.setStartValue(self._arrow_angle)
            anim.setEndValue(target)
            anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            self._arrow_anim = anim
            anim.start()

        def getArrowAngle(self):
            return self._arrow_angle

        def setArrowAngle(self, angle):
            self._arrow_angle = float(angle)
            self.update()

        arrowAngle = QtCore.Property(float, getArrowAngle, setArrowAngle)

        def paintEvent(self, event):
            super().paintEvent(event)
            # Draw the chevron glyph on top of the combo's own background
            # (which already includes hover/pressed states from stylesheet).
            # This avoids the child-widget background fill problem entirely.
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            sz = self._arrow_size
            margins = self.layout().contentsMargins()
            cx = self.width() - margins.right() - sz / 2.0
            cy = self.height() / 2.0
            painter.translate(cx, cy)
            painter.rotate(self._arrow_angle)
            painter.translate(-cx, -cy)
            pen = QtGui.QPen(QtGui.QColor("#9e9e9e"))
            pen.setWidthF(1.8)
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            s = sz / 10.0
            painter.drawPolyline(
                [
                    QtCore.QPointF(cx - 2.5 * s, cy - 1.0 * s),
                    QtCore.QPointF(cx, cy + 1.5 * s),
                    QtCore.QPointF(cx + 2.5 * s, cy - 1.0 * s),
                ]
            )

    return _ComboInput()


def make_mock_input(text, mode):
    """Create a Painter-style mock spin/combo input used by compact panels."""
    if mode == "spin":
        return make_spin_input(float(text))
    if mode == "combo":
        options = ["System Default", "MiSans", "Inter", "Segoe UI", "Arial"]
        return make_combo_input(options)
    raise ValueError(f"Unsupported mock input mode: {mode}")


class CompactSpinArrows:
    """Small painted up/down chevrons that never overflow their bounds."""

    def __new__(cls, on_step=None):
        from PySide6 import QtCore, QtGui, QtWidgets

        class _SpinArrows(QtWidgets.QWidget):
            def __init__(self):
                super().__init__()
                self.setObjectName("RizumSpinArrows")
                self.setFixedSize(10, 14)
                self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
                self._active = None
                self._hover = None
                self.setMouseTracking(True)

            def paintEvent(self, event):
                painter = QtGui.QPainter(self)
                painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
                self._draw_chevron(painter, "up")
                self._draw_chevron(painter, "down")

            def mousePressEvent(self, event):
                if event.button() != QtCore.Qt.MouseButton.LeftButton:
                    return
                self._active = self._hit_direction(event.position().y())
                if on_step is not None:
                    on_step(0.05 if self._active == "up" else -0.05)
                self.update()

            def mouseReleaseEvent(self, event):
                self._active = None
                self._hover = self._hit_direction(event.position().y())
                self.update()

            def mouseMoveEvent(self, event):
                self._hover = self._hit_direction(event.position().y())
                self.update()

            def leaveEvent(self, event):
                self._active = None
                self._hover = None
                self.update()

            def _hit_direction(self, y):
                return "up" if y < self.height() / 2 else "down"

            def _draw_chevron(self, painter, direction):
                if self._active == direction:
                    color = "#e0e0e0"
                elif self._hover == direction:
                    color = "#9e9e9e"
                else:
                    color = "#666666"
                pen = QtGui.QPen(QtGui.QColor(color))
                pen.setWidthF(1.4)
                pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                if direction == "up":
                    points = [
                        QtCore.QPointF(2.5, 5.0),
                        QtCore.QPointF(5.0, 2.5),
                        QtCore.QPointF(7.5, 5.0),
                    ]
                else:
                    points = [
                        QtCore.QPointF(2.5, 9.0),
                        QtCore.QPointF(5.0, 11.5),
                        QtCore.QPointF(7.5, 9.0),
                    ]
                painter.drawPolyline(points)

        return _SpinArrows()


class CompactStepperButtons:
    """Touch-friendly horizontal - / + buttons matching the compact stepper."""

    def __new__(cls, on_step=None, size=32):
        from PySide6 import QtCore, QtGui, QtWidgets

        button_size = int(size)
        gap = 2

        class _StepperButtons(QtWidgets.QWidget):
            def __init__(self):
                super().__init__()
                self.setObjectName("RizumStepperButtons")
                self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
                self._button_size = button_size
                self._gap = gap
                self.setFixedSize(button_size * 2 + gap, button_size)
                self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
                self.setMouseTracking(True)
                self._hover = None
                self._pressed = None
                self._animated_part = None
                self._visual_scale = 1.0
                self._visual_opacity = 1.0
                self._animation = None

            def setButtonSize(self, size):
                """Scale the stepper buttons (re-lays out fixed size + symbols)."""
                new_size = max(21, int(round(size)))
                if new_size == self._button_size:
                    return
                self._button_size = new_size
                self.setFixedSize(new_size * 2 + self._gap, new_size)
                self.update()

            def buttonSize(self):
                return self._button_size

            def getVisualScale(self):
                return self._visual_scale

            def setVisualScale(self, value):
                self._visual_scale = float(value)
                self.update()

            def getVisualOpacity(self):
                return self._visual_opacity

            def setVisualOpacity(self, value):
                self._visual_opacity = float(value)
                self.update()

            visualScale = QtCore.Property(float, getVisualScale, setVisualScale)
            visualOpacity = QtCore.Property(float, getVisualOpacity, setVisualOpacity)

            def _rect_for(self, part):
                bs = self._button_size
                x = 0 if part == "minus" else bs + self._gap
                return QtCore.QRectF(x, 0, bs, bs)

            def _part_at(self, pos):
                point = QtCore.QPointF(pos)
                for part in ("minus", "plus"):
                    if self._rect_for(part).contains(point):
                        return part
                return None

            def _animate_part(self, part, scale, opacity, duration):
                if self._animation is not None:
                    self._animation.stop()
                self._animated_part = part
                group = QtCore.QParallelAnimationGroup(self)
                for prop, start, end in (
                    (b"visualScale", self._visual_scale, scale),
                    (b"visualOpacity", self._visual_opacity, opacity),
                ):
                    animation = QtCore.QPropertyAnimation(self, prop, self)
                    animation.setDuration(duration)
                    animation.setStartValue(start)
                    animation.setEndValue(float(end))
                    animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
                    group.addAnimation(animation)
                self._animation = group
                if scale == 1.0 and opacity == 1.0:
                    group.finished.connect(lambda: self._clear_finished_animation(part))
                group.start()

            def _clear_finished_animation(self, part):
                if self._animated_part == part:
                    self._animated_part = None
                    self.update()

            def paintEvent(self, event):
                painter = QtGui.QPainter(self)
                painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
                for part in ("minus", "plus"):
                    if part == self._pressed:
                        bg = QtGui.QColor(255, 255, 255, 75)
                    elif part == self._hover:
                        bg = QtGui.QColor(255, 255, 255, 30)
                    else:
                        continue
                    rect = self._rect_for(part).adjusted(1, 1, -1, -1)
                    painter.setPen(QtCore.Qt.PenStyle.NoPen)
                    painter.setBrush(bg)
                    painter.drawRoundedRect(rect, 6, 6)
                for part in ("minus", "plus"):
                    self._draw_symbol(painter, part)
                painter.end()

            def _draw_symbol(self, painter, part):
                rect = self._rect_for(part)
                scale = self._visual_scale if part == self._animated_part else 1.0
                opacity = self._visual_opacity if part == self._animated_part else 1.0
                active = part == self._hover or part == self._pressed
                color = QtGui.QColor("#e0e0e0") if active else QtGui.QColor("#9e9e9e")
                pen = QtGui.QPen(color, 1.8)
                pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                previous_opacity = painter.opacity()
                painter.setOpacity(previous_opacity * max(0.0, min(1.0, opacity)))
                painter.setPen(pen)
                # Symbol size scales with the button size (4.8 at default 32).
                half = 4.8 * (self._button_size / 32.0) * scale
                center = QtCore.QPointF(rect.center().x(), rect.center().y() - 0.5)
                painter.drawLine(
                    QtCore.QPointF(center.x() - half, center.y()),
                    QtCore.QPointF(center.x() + half, center.y()),
                )
                if part == "plus":
                    painter.drawLine(
                        QtCore.QPointF(center.x(), center.y() - half),
                        QtCore.QPointF(center.x(), center.y() + half),
                    )
                painter.setOpacity(previous_opacity)

            def mousePressEvent(self, event):
                if event.button() != QtCore.Qt.MouseButton.LeftButton:
                    return
                self._pressed = self._part_at(event.position())
                if self._pressed is not None:
                    self._animate_part(self._pressed, 0.85, 0.7, 80)
                    if on_step is not None:
                        on_step(-1 if self._pressed == "minus" else 1)
                self.update()
                event.accept()

            def mouseReleaseEvent(self, event):
                pressed = self._pressed
                self._pressed = None
                self._hover = self._part_at(event.position())
                if pressed is not None:
                    self._animate_part(pressed, 1.0, 1.0, 180)
                self.update()
                event.accept()

            def mouseMoveEvent(self, event):
                next_hover = self._part_at(event.position())
                if next_hover != self._hover:
                    self._hover = next_hover
                    self.update()

            def enterEvent(self, event):
                super().enterEvent(event)
                pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
                self._hover = self._part_at(pos)
                self.update()

            def leaveEvent(self, event):
                pressed = self._pressed
                self._pressed = None
                self._hover = None
                if pressed is not None and self._animated_part is not None:
                    self._animate_part(pressed, 1.0, 1.0, 160)
                self.update()

        return _StepperButtons()


class CompactChevronDown:
    """Small painted down chevron without a child hover surface."""

    def __new__(cls):
        from PySide6 import QtCore, QtGui, QtWidgets

        class _ChevronDown(QtWidgets.QWidget):
            def __init__(self):
                super().__init__()
                self.setObjectName("RizumChevronIcon")
                self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
                self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
                self.setAutoFillBackground(False)
                self._size = 14
                self.setFixedSize(self._size, self._size)
                self._angle = 0.0

            def setSize(self, size):
                """Scale the chevron widget and its painted glyph."""
                new_size = max(8, int(round(size)))
                if new_size == self._size:
                    return
                self._size = new_size
                self.setFixedSize(new_size, new_size)
                self.update()

            def size(self):
                return self._size

            def getAngle(self):
                return self._angle

            def setAngle(self, angle):
                self._angle = float(angle)
                self.update()

            angle = QtCore.Property(float, getAngle, setAngle)

            def setOpen(self, is_open):
                target = 180.0 if is_open else 0.0
                old_animation = getattr(self, "_rizum_arrow_animation", None)
                if old_animation is not None:
                    old_animation.stop()
                animation = QtCore.QPropertyAnimation(self, b"angle", self)
                animation.setDuration(180)
                animation.setStartValue(self._angle)
                animation.setEndValue(target)
                animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
                self._rizum_arrow_animation = animation
                animation.start()

            def paintEvent(self, event):
                painter = QtGui.QPainter(self)
                # Grab the parent's actual rendered pixels behind this widget
                # (including hover/pressed stylesheet states) and use them as
                # our background. This avoids any transparent fill (which turns
                # black on SP's opaque backing store) and matches the combo's
                # hover color exactly.
                parent = self.parent()
                if parent is not None:
                    try:
                        pos = self.mapToParent(QtCore.QPoint(0, 0))
                        pm = parent.grab(QtCore.QRect(pos.x(), pos.y(), self.width(), self.height()))
                        painter.drawPixmap(0, 0, pm)
                    except Exception:
                        pass
                painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
                painter.translate(self.width() / 2, self.height() / 2)
                painter.rotate(self._angle)
                painter.translate(-self.width() / 2, -self.height() / 2)
                pen = QtGui.QPen(QtGui.QColor("#9e9e9e"))
                pen.setWidthF(1.8)
                pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                # Glyph points scale relative to the default 10px size.
                s = self._size / 10.0
                painter.drawPolyline(
                    [
                        QtCore.QPointF(2.5 * s, 4.0 * s),
                        QtCore.QPointF(5.0 * s, 6.5 * s),
                        QtCore.QPointF(7.5 * s, 4.0 * s),
                    ]
                )

        return _ChevronDown()


def make_mock_checkbox(checked=True):
    """Create the filled/outline checkbox used by compact Rizum panels."""
    from PySide6 import QtCore, QtGui, QtWidgets

    class _Checkbox(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.setObjectName("RizumMockCheckbox")
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self._size = 14
            self.setFixedSize(self._size, self._size)
            self._checked = bool(checked)
            self._indeterminate = False
            self.setProperty("checked", self._checked)
            self.setProperty("indeterminate", False)

        def setSize(self, size):
            """Scale the checkbox widget and its painted glyph."""
            new_size = max(11, int(round(size)))
            if new_size == self._size:
                return
            self._size = new_size
            self.setFixedSize(new_size, new_size)
            self.update()

        def checkboxSize(self):
            return self._size

        def toggle(self):
            self.set_checked(not self._checked)

        def set_checked(self, checked):
            self._checked = checked
            self._indeterminate = False
            self.setProperty("checked", checked)
            self.setProperty("indeterminate", False)
            self.update()

        def set_indeterminate(self, indeterminate):
            self._indeterminate = bool(indeterminate)
            if self._indeterminate:
                self._checked = False
            self.setProperty("checked", self._checked)
            self.setProperty("indeterminate", self._indeterminate)
            self.update()

        def is_indeterminate(self):
            return self._indeterminate

        def isChecked(self):
            return self._checked and not self._indeterminate

        def setChecked(self, checked):
            self.set_checked(bool(checked))

        def setIndeterminate(self, indeterminate):
            self.set_indeterminate(bool(indeterminate))

        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self.toggle()

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            s = self._size / 14.0

            if self._checked or self._indeterminate:
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.setBrush(QtGui.QColor("#ffffff"))
                painter.drawRoundedRect(QtCore.QRectF(0, 0, 14 * s, 14 * s), 3 * s, 3 * s)

                pen = QtGui.QPen(QtGui.QColor("#1b1b1b"))
                pen.setWidthF(1.6 * s)
                pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                if self._indeterminate:
                    painter.drawLine(
                        QtCore.QPointF(3.6 * s, 7.0 * s),
                        QtCore.QPointF(10.4 * s, 7.0 * s),
                    )
                else:
                    painter.drawPolyline(
                        [
                            QtCore.QPointF(4.0 * s, 7.2 * s),
                            QtCore.QPointF(6.0 * s, 9.2 * s),
                            QtCore.QPointF(10.0 * s, 4.8 * s),
                        ]
                    )
            else:
                rect = QtCore.QRectF(0.75 * s, 0.75 * s, 12.5 * s, 12.5 * s)
                pen = QtGui.QPen(QtGui.QColor("#ffffff"))
                pen.setWidthF(1.5 * s)
                pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(rect, 3 * s, 3 * s)

    return _Checkbox()


def make_field_row(label_text, control, label_width=50, gap=18, width=None):
    """Create a compact label/control row with Painter-style spacing."""
    from PySide6 import QtCore, QtWidgets

    widget = QtWidgets.QWidget()
    widget.setObjectName("RizumTransparent")
    widget.setFixedHeight(32)
    row = QtWidgets.QHBoxLayout(widget)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(gap)
    label = FieldLabel.create(label_text)
    label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    label.setFixedWidth(label_width)
    row.addWidget(label)
    if width is not None:
        control.setFixedWidth(width)
        row.addWidget(control)
        row.addStretch(1)
    elif control.sizePolicy().horizontalPolicy() in (
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        QtWidgets.QSizePolicy.Policy.Ignored,
    ):
        row.addWidget(control, 1)
    else:
        row.addWidget(control)
        row.addStretch(1)
    widget._rizum_label = label
    widget._rizum_control = control
    return widget
