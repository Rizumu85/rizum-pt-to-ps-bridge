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


def _svg_with_breathing_room(source):
    """Give 24px stroke icons a small viewBox margin so strokes are not clipped."""
    source = source.replace('viewBox="0 0 24 24"', 'viewBox="-2 -2 28 28"')
    source = source.replace("viewBox='0 0 24 24'", "viewBox='-2 -2 28 28'")
    return source


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
            if tooltip:
                self.setToolTip(tooltip)

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

    return _DockActionButton()


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
    from PySide6 import QtGui, QtWidgets

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
    layout.setContentsMargins(6, 3, 6, 3)
    layout.setSpacing(6)

    label = QtWidgets.QLabel(label_text)
    label.setObjectName("RizumHintLabel")
    text_width = compact_text_width(label_text, widget=label, minimum=0, maximum=maximum - 26)
    label.setMinimumWidth(text_width)
    label.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Preferred,
        QtWidgets.QSizePolicy.Policy.Preferred,
    )
    layout.addWidget(label)
    layout.addWidget(checkbox)

    row_width = min(maximum, max(minimum, text_width + checkbox.width() + 24))
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
        maximum=max(0, maximum - 26),
    )
    label.setMinimumWidth(text_width)
    row_width = min(maximum, max(minimum, text_width + checkbox.width() + 24))
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

        def set_hovered(self, is_hovered):
            if row.property(property_name) == is_hovered:
                return
            row.setProperty(property_name, is_hovered)
            row.style().unpolish(row)
            row.style().polish(row)
            row.update()

        def refresh_hovered(self):
            self.set_hovered(any(widget.underMouse() for widget in watched))

        def eventFilter(self, obj, event):
            event_type = event.type()
            if event_type == QtCore.QEvent.Type.Enter:
                self.set_hovered(True)
            elif event_type == QtCore.QEvent.Type.Leave:
                QtCore.QTimer.singleShot(0, self.refresh_hovered)
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
        host_layout.setContentsMargins(24, 0, 0, 0)
        host_layout.setSpacing(0)

        row = QtWidgets.QFrame()
        row.setObjectName("RizumExportTreeItem")
        row.setProperty("child", "true")
        row.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        row_layout = QtWidgets.QHBoxLayout(row)
        row_layout.setContentsMargins(8, 4, 8, 4)
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
            self.setFixedSize(14, 14)
            self._angle = 90.0 if is_expanded else 0.0

        def getAngle(self):
            return self._angle

        def setAngle(self, angle):
            self._angle = float(angle)
            self.update()

        angle = QtCore.Property(float, getAngle, setAngle)

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.translate(self.width() / 2, self.height() / 2)
            painter.rotate(self._angle)
            painter.translate(-self.width() / 2, -self.height() / 2)
            pen = QtGui.QPen(QtGui.QColor("#9e9e9e"))
            pen.setWidthF(1.7)
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPolyline(
                [
                    QtCore.QPointF(5.0, 3.7),
                    QtCore.QPointF(8.4, 7.0),
                    QtCore.QPointF(5.0, 10.3),
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


def make_icon_button(icon_name, tooltip="", size=16, compact=True):
    """Create a themed icon button from the shared icons folder."""
    from PySide6 import QtCore, QtGui, QtWidgets

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
            self._visual_scale = 1.0
            self._visual_opacity = 1.0
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

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
            key = (color, round(dpr, 2), size)
            if key in self._pixmap_cache:
                return self._pixmap_cache[key]
            pixel_size = max(1, int(round(size * dpr)))
            pixmap = QtGui.QPixmap(pixel_size, pixel_size)
            pixmap.setDevicePixelRatio(dpr)
            pixmap.fill(QtCore.Qt.GlobalColor.transparent)
            if QtSvg is not None and self._icon_source:
                source = self._icon_source
                source = source.replace("currentColor", color)
                source = _svg_with_breathing_room(source)
                renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(source.encode("utf-8")))
                painter = QtGui.QPainter(pixmap)
                renderer.render(painter, QtCore.QRectF(0, 0, size, size))
                painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(QtCore.QRectF(0, 0, size, size), QtGui.QColor(color))
                painter.end()
            else:
                base = self._icon.pixmap(QtCore.QSize(pixel_size, pixel_size))
                painter = QtGui.QPainter(pixmap)
                painter.drawPixmap(QtCore.QRectF(0, 0, size, size), base, QtCore.QRectF(base.rect()))
                painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(QtCore.QRectF(0, 0, size, size), QtGui.QColor(color))
                painter.end()
            self._pixmap_cache[key] = pixmap
            return pixmap

        def paintEvent(self, event):
            super().paintEvent(event)
            if self.property("accent"):
                color = self.property("iconAccentColor") or "#ffffff"
            elif self.underMouse():
                color = self.property("iconHoverColor") or "#ffffff"
            else:
                color = self.property("iconColor") or "#9e9e9e"
            pixmap = self._rendered_pixmap(color)
            visual_size = max(1, int(round(size * self._visual_scale)))
            target = QtCore.QRect(
                int((self.width() - visual_size) / 2),
                int((self.height() - visual_size) / 2),
                visual_size,
                visual_size,
            )
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
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
        button.setToolTip(tooltip)
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
            layout.setContentsMargins(8, 6, 8, 6)
            layout.setSpacing(4)
            self._label = QtWidgets.QLabel()
            self._label.setObjectName("RizumMockText")
            self._label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._label.setMinimumWidth(0)
            self._label.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Preferred,
            )
            layout.addWidget(self._label, 1)
            layout.addWidget(CompactSpinArrows(self._step_by))

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

        def wheelEvent(self, event):
            direction = 1 if event.angleDelta().y() > 0 else -1
            self._step_by(self._step * direction)

        def _step_by(self, delta):
            self.setValue(self._value + delta)

    return _SpinInput()


def make_compact_stepper(value=8, minimum=0, maximum=999, step=1):
    """Create a compact three-part numeric stepper with a Painter-style edit value."""
    from PySide6 import QtCore, QtGui, QtWidgets

    class _CompactStepper(QtWidgets.QWidget):
        valueChanged = QtCore.Signal(int)

        def __init__(self):
            super().__init__()
            self.setObjectName("RizumCompactStepper")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.setMouseTracking(True)
            self.setFixedSize(84, 24)
            self._value = int(value)
            self._minimum = int(minimum)
            self._maximum = int(maximum)
            self._step = int(step)
            self._hover_part = None
            self._pressed_part = None
            self._animated_part = None
            self._visual_scale = 1.0
            self._visual_opacity = 1.0
            self._animation = None
            self._editing = False
            self._edit_text = str(self._value)
            self._replace_edit_text = False
            self._theme = {
                "background": "#1b1b1b",
                "text": "#e0e0e0",
                "muted": "#9e9e9e",
                "hover": "rgba(255, 255, 255, 0.04)",
            }
            self.setValue(value, emit=False)

        def setTheme(self, theme):
            self._theme = {
                "background": theme.get("window_bg", "#1b1b1b"),
                "text": theme.get("text", "#e0e0e0"),
                "muted": theme.get("muted", theme.get("text_secondary", "#9e9e9e")),
                "hover": theme.get(
                    "control_hover",
                    theme.get("hover", "rgba(255, 255, 255, 0.04)"),
                ),
            }
            self.update()

        def value(self):
            return self._value

        def setValue(self, value, emit=True):
            next_value = max(self._minimum, min(self._maximum, int(value)))
            if next_value == self._value:
                self._edit_text = str(self._value)
                return
            self._value = next_value
            self._edit_text = str(self._value)
            self.update()
            if emit:
                self.valueChanged.emit(self._value)

        def setRange(self, minimum, maximum):
            self._minimum = int(minimum)
            self._maximum = int(maximum)
            self.setValue(self._value)

        def setSingleStep(self, step):
            self._step = int(step)

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
            x_positions = {"minus": 0, "value": 30, "plus": 60}
            return QtCore.QRectF(x_positions[part], 0, 24, 24)

        def _hover_rect_for(self, part):
            rect = self._rect_for(part)
            if part == "value":
                return rect
            return rect.adjusted(1, 1, -1, -1)

        def _hover_color(self):
            color = self._theme.get("hover", "rgba(255, 255, 255, 0.04)")
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
            base = QtGui.QColor(self._theme.get("background", "#1b1b1b"))
            if not base.isValid():
                base = QtGui.QColor("#1b1b1b")
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
            self._editing = True
            self._edit_text = str(self._value)
            self._replace_edit_text = True
            self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
            self.update()

        def _commit_edit(self):
            if not self._editing:
                return
            text = self._edit_text.strip()
            if text:
                self.setValue(int(text))
            else:
                self._edit_text = str(self._value)
            self._editing = False
            self._replace_edit_text = False
            self.update()

        def _cancel_edit(self):
            if not self._editing:
                return
            self._edit_text = str(self._value)
            self._editing = False
            self._replace_edit_text = False
            self.update()

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
                if part == self._pressed_part:
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
            if self._editing:
                if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
                    self._commit_edit()
                    event.accept()
                    return
                if event.key() == QtCore.Qt.Key.Key_Escape:
                    self._cancel_edit()
                    event.accept()
                    return
                if event.key() == QtCore.Qt.Key.Key_Backspace:
                    self._edit_text = "" if self._replace_edit_text else self._edit_text[:-1]
                    self._replace_edit_text = False
                    self.update()
                    event.accept()
                    return
                text = event.text()
                if text and text.isdigit():
                    seed = "" if self._replace_edit_text else self._edit_text
                    next_text = (seed + text).lstrip("0") or "0"
                    if int(next_text) <= self._maximum:
                        self._edit_text = next_text
                        self._replace_edit_text = False
                    self.update()
                    event.accept()
                    return
                event.accept()
                return
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
            self._commit_edit()
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
                if part == self._hover_part or (part == "value" and self._editing):
                    rect = self._hover_rect_for(part)
                    painter.setPen(QtCore.Qt.PenStyle.NoPen)
                    painter.setBrush(self._hover_color())
                    painter.drawRoundedRect(rect, 4, 4)

            symbol_center_y = self._value_visual_center_y()
            self._draw_step_symbol(painter, "minus", symbol_center_y)
            self._draw_value_text(painter)
            if self._editing and self.hasFocus():
                self._draw_edit_cursor(painter)
            self._draw_step_symbol(painter, "plus", symbol_center_y)
            painter.end()

        def _value_font(self):
            font = QtGui.QFont(self.font())
            font.setPixelSize(12)
            font.setWeight(QtGui.QFont.Weight.Medium)
            return font

        def _value_baseline(self, font):
            rect = self._rect_for("value")
            metrics = QtGui.QFontMetricsF(font)
            return rect.center().y() + (metrics.ascent() - metrics.descent()) / 2

        def _value_visual_center_y(self):
            font = self._value_font()
            metrics = QtGui.QFontMetricsF(font)
            baseline = self._value_baseline(font)
            bounds = metrics.tightBoundingRect("8")
            return baseline + bounds.y() + bounds.height() / 2

        def _value_text(self):
            return self._edit_text if self._editing else str(self._value)

        def _draw_value_text(self, painter):
            rect = self._rect_for("value")
            font = self._value_font()
            painter.setFont(font)
            painter.setPen(QtGui.QColor(self._theme["text"]))
            metrics = QtGui.QFontMetricsF(font)
            text = self._value_text()
            text_width = metrics.horizontalAdvance(text)
            baseline = self._value_baseline(font)
            painter.drawText(
                QtCore.QPointF(rect.center().x() - text_width / 2, baseline),
                text,
            )

        def _draw_edit_cursor(self, painter):
            rect = self._rect_for("value")
            font = self._value_font()
            metrics = QtGui.QFontMetricsF(font)
            text_width = metrics.horizontalAdvance(self._value_text())
            cursor_x = rect.center().x() + text_width / 2 + 1
            cursor_top = rect.center().y() - 6
            painter.setPen(QtGui.QPen(QtGui.QColor(self._theme["text"]), 1))
            painter.drawLine(
                QtCore.QPointF(cursor_x, cursor_top),
                QtCore.QPointF(cursor_x, cursor_top + 12),
            )

        def _draw_step_symbol(self, painter, part, center_y):
            rect = self._rect_for(part)
            scale = self._visual_scale if part == self._animated_part else 1.0
            opacity = self._visual_opacity if part == self._animated_part else 1.0
            color = self._theme["text"] if part == self._hover_part else self._theme["muted"]
            pen = QtGui.QPen(QtGui.QColor(color), 1.6)
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            previous_opacity = painter.opacity()
            painter.setOpacity(previous_opacity * max(0.0, min(1.0, opacity)))
            painter.setPen(pen)
            half = 3.6 * scale
            center = QtCore.QPointF(rect.center().x(), center_y - 0.5)
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
    from PySide6 import QtCore, QtWidgets

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
            layout.setContentsMargins(8, 4, 10, 4)
            layout.setSpacing(6)
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
            self._arrow = CompactChevronDown()
            layout.addWidget(self._arrow)

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
                self.fitToContents()
            else:
                self._label.setMinimumWidth(0)
                self.setMinimumWidth(0)
                self.setMaximumWidth(16777215)

        def fitToContents(self):
            if not self._fit_to_contents or not self._items:
                return
            metrics = self._label.fontMetrics()
            display_texts = [str(item[0]) for item in self._items]
            if self._display_prefix or self._display_value:
                display_texts.append(f"{self._display_prefix} {self._display_value}".strip())
            text_width = max(metrics.horizontalAdvance(text) for text in display_texts)
            margins = self.layout().contentsMargins()
            width = (
                text_width
                + margins.left()
                + margins.right()
                + self.layout().spacing()
                + self._arrow.width()
                + 6
            )
            self._label.setMinimumWidth(text_width)
            self.setFixedWidth(width)

        def refreshMetrics(self):
            self.fitToContents()

        def setCompactHeight(self, height):
            height = int(height)
            self.setFixedHeight(height)
            vertical_margin = 3 if height <= 28 else 4
            self.layout().setContentsMargins(8, vertical_margin, 10, vertical_margin)
            self._label.setMinimumHeight(max(0, height - vertical_margin * 2))
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
                QtCore.QTimer.singleShot(0, self.fitToContents)

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
                QtCore.QTimer.singleShot(0, self.fitToContents)

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
            for index, item in enumerate(self._items):
                action = menu.addAction(item[0])
                action.triggered.connect(lambda checked=False, i=index: self.setCurrentIndex(i))
            self._menu = menu
            menu.aboutToHide.connect(self._close_menu)
            self._arrow.setOpen(True)
            menu_width = menu.sizeHint().width()
            popup_x = self.width() - menu_width if self._popup_alignment == "right" else 0
            menu.popup(self.mapToGlobal(QtCore.QPoint(popup_x, self.height() + 4)))

        def _close_menu(self):
            self._arrow.setOpen(False)
            self._last_menu_close_ms = QtCore.QDateTime.currentMSecsSinceEpoch()
            self._menu = None

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
                self.setFixedSize(10, 10)
                self._angle = 0.0

            def getAngle(self):
                return self._angle

            def setAngle(self, angle):
                self._angle = float(angle)
                self.update()

            angle = QtCore.Property(float, getAngle, setAngle)

            def setOpen(self, is_open):
                old_animation = getattr(self, "_rizum_arrow_animation", None)
                if old_animation is not None:
                    old_animation.stop()
                self._rizum_arrow_animation = None
                self.setAngle(0.0)

            def paintEvent(self, event):
                painter = QtGui.QPainter(self)
                painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
                painter.translate(self.width() / 2, self.height() / 2)
                painter.rotate(self._angle)
                painter.translate(-self.width() / 2, -self.height() / 2)
                pen = QtGui.QPen(QtGui.QColor("#9e9e9e"))
                pen.setWidthF(1.4)
                pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.drawPolyline(
                    [
                        QtCore.QPointF(2.5, 4.0),
                        QtCore.QPointF(5.0, 6.5),
                        QtCore.QPointF(7.5, 4.0),
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
            self.setFixedSize(14, 14)
            self._checked = bool(checked)
            self._indeterminate = False
            self.setProperty("checked", self._checked)
            self.setProperty("indeterminate", False)

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

            if self._checked or self._indeterminate:
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.setBrush(QtGui.QColor("#ffffff"))
                painter.drawRoundedRect(QtCore.QRectF(0, 0, 14, 14), 3, 3)

                pen = QtGui.QPen(QtGui.QColor("#1b1b1b"))
                pen.setWidthF(1.6)
                pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                if self._indeterminate:
                    painter.drawLine(QtCore.QPointF(3.6, 7.0), QtCore.QPointF(10.4, 7.0))
                else:
                    painter.drawPolyline(
                        [
                            QtCore.QPointF(4.0, 7.2),
                            QtCore.QPointF(6.0, 9.2),
                            QtCore.QPointF(10.0, 4.8),
                        ]
                    )
            else:
                rect = QtCore.QRectF(0.75, 0.75, 12.5, 12.5)
                pen = QtGui.QPen(QtGui.QColor("#ffffff"))
                pen.setWidthF(1.5)
                pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(rect, 3, 3)

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
    else:
        row.addWidget(control, 1)
    widget._rizum_label = label
    widget._rizum_control = control
    return widget
