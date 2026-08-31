"""Compact interaction controls for Painter settings dialogs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from types import MappingProxyType

from PySide6 import QtCore, QtGui, QtWidgets

from .components import FOOTER_BUTTON_PADDING_X, render_svg_pixmap
from .theme import default_theme


PAINTER_DIALOG_STYLE = MappingProxyType(
    {
        "surface": "#202020",
        "control": "#333333",
        "control_hover": "#444444",
        "control_pressed": "#2c2c2c",
        "text": "#f2f2f2",
        "muted": "#9a9a9a",
        "faint": "#858585",
        "accent": "#f2f2f2",
        "accent_hover": "#ffffff",
        "accent_pressed": "#dedede",
        "accent_text": "#202020",
    }
)


class SettingsToggle(QtWidgets.QAbstractButton):
    """Painter-style settings switch with runtime compact scaling."""

    BASE_WIDTH = 36
    BASE_HEIGHT = 20
    MIN_HEIGHT = 15
    ANIMATION_DURATION = 160

    def __init__(
        self,
        checked: bool = False,
        visual_style: Mapping[str, str] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RizumSettingsToggle")
        self.setCheckable(True)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent; border: 0;")
        self._visual_style = dict(PAINTER_DIALOG_STYLE)
        if visual_style:
            self._visual_style.update(visual_style)
        self._compact_height = self.BASE_HEIGHT
        self._knob_margin = 3.0
        self._knob_size = 14.0
        self._offset = 0.0
        self._animation = QtCore.QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(self.ANIMATION_DURATION)
        self._animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate_to_state)
        self.blockSignals(True)
        self.setChecked(bool(checked))
        self.blockSignals(False)
        self.setCompactHeight(self.BASE_HEIGHT)

    def setVisualStyle(self, visual_style: Mapping[str, str]) -> None:
        self._visual_style = dict(PAINTER_DIALOG_STYLE)
        self._visual_style.update(visual_style)
        self.update()

    def compactHeight(self) -> int:
        return self._compact_height

    def setCompactHeight(self, height: int) -> None:
        self._animation.stop()
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

    def _knob_travel(self) -> float:
        return max(
            0.0,
            float(self.width()) - self._knob_size - 2 * self._knob_margin,
        )

    def getOffset(self) -> float:
        return self._offset

    def setOffset(self, value: float) -> None:
        self._offset = float(value)
        self.update()

    offset = QtCore.Property(float, getOffset, setOffset)

    def _animate_to_state(self, checked: bool) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(
            self._knob_travel() if checked else 0.0
        )
        self._animation.start()

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.update()

    def paintEvent(self, event) -> None:
        del event
        style = self._visual_style
        if self.isDown():
            track_key = "accent_pressed" if self.isChecked() else "control_pressed"
        elif self.underMouse():
            track_key = "accent_hover" if self.isChecked() else "control_hover"
        else:
            track_key = "accent" if self.isChecked() else "control"

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        track = QtCore.QRectF(
            0.5,
            0.5,
            self.width() - 1.0,
            self.height() - 1.0,
        )
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor(style[track_key]))
        painter.drawRoundedRect(
            track,
            track.height() / 2.0,
            track.height() / 2.0,
        )
        painter.setBrush(QtGui.QColor(style["muted"]))
        painter.drawEllipse(
            QtCore.QRectF(
                self._knob_margin + self._offset,
                self._knob_margin,
                self._knob_size,
                self._knob_size,
            )
        )
        painter.end()


class StatusBanner(QtWidgets.QFrame):
    """Compact dock status surface with an optional in-place action."""

    actionTriggered = QtCore.Signal()

    BASE_HEIGHT = 54
    MIN_HEIGHT = 41  # round(54 x 0.75)
    STATUS_TRANSITION_DURATION = 140
    _TONES = {
        "neutral": "#666666",
        "accent": "#f2f2f2",
        "info": "#6aa8ff",
        "good": default_theme.success,
        "warn": default_theme.warning,
        "bad": default_theme.danger,
    }

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        tone: str = "neutral",
        action_text: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RizumStatusBanner")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            """
QFrame#RizumStatusBanner {
    background: transparent;
    border: 0;
}
QFrame#RizumStatusBanner QLabel#RizumStatusBannerTitle {
    color: #f2f2f2;
    background: transparent;
    border: 0;
}
QFrame#RizumStatusBanner QLabel#RizumStatusBannerSubtitle {
    color: #9a9a9a;
    background: transparent;
    border: 0;
}
"""
        )
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._compact_height = self.BASE_HEIGHT
        self._tone = "neutral"
        self._tone_color = QtGui.QColor(self._TONES["neutral"])
        self._tone_start_color = QtGui.QColor(self._tone_color)
        self._tone_target_color = QtGui.QColor(self._tone_color)
        self._tone_progress = 1.0
        self._accent_width = 3
        self._radius = float(default_theme.radius_small)
        self._status_animation = None

        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setContentsMargins(12, 7, 10, 7)
        self._layout.setSpacing(8)

        text_host = QtWidgets.QWidget(self)
        text_host.setObjectName("RizumTransparent")
        self._text_host = text_host
        self._text_opacity = QtWidgets.QGraphicsOpacityEffect(text_host)
        self._text_opacity.setOpacity(1.0)
        text_host.setGraphicsEffect(self._text_opacity)
        self._text_layout = QtWidgets.QVBoxLayout(text_host)
        self._text_layout.setContentsMargins(0, 0, 0, 0)
        self._text_layout.setSpacing(1)
        self._title = QtWidgets.QLabel(title, text_host)
        self._title.setObjectName("RizumStatusBannerTitle")
        self._subtitle = QtWidgets.QLabel(subtitle, text_host)
        self._subtitle.setObjectName("RizumStatusBannerSubtitle")
        for label in (self._title, self._subtitle):
            label.setAttribute(
                QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            label.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Ignored,
                QtWidgets.QSizePolicy.Policy.Preferred,
            )
        self._text_layout.addWidget(self._title)
        self._text_layout.addWidget(self._subtitle)
        self._layout.addWidget(text_host, 1)

        self._action = TextActionButton(action_text, parent=self)
        self._action_opacity = QtWidgets.QGraphicsOpacityEffect(self._action)
        self._action_opacity.setOpacity(1.0)
        self._action.setGraphicsEffect(self._action_opacity)
        self._action.clicked.connect(self.actionTriggered)
        self._layout.addWidget(self._action)
        self.setStatus(title, subtitle, tone, action_text)
        self.setCompactHeight(self.BASE_HEIGHT)

    def title(self) -> str:
        return self._title.text()

    def subtitle(self) -> str:
        return self._subtitle.text()

    def tone(self) -> str:
        return self._tone

    def actionText(self) -> str:
        return self._action.text()

    def setStatus(
        self,
        title: str,
        subtitle: str = "",
        tone: str = "neutral",
        action_text: str = "",
        *,
        animate: bool = False,
    ) -> None:
        title = str(title)
        subtitle = str(subtitle)
        action_text = str(action_text)
        next_tone = tone if tone in self._TONES else "neutral"
        changed = (
            title != self._title.text()
            or subtitle != self._subtitle.text()
            or action_text != self._action.text()
            or next_tone != self._tone
        )

        self._title.setText(title)
        self._subtitle.setText(subtitle)
        self._subtitle.setVisible(bool(subtitle))
        self._tone = next_tone
        self._action.setText(action_text)
        self._action.setVisible(bool(action_text))
        self._action.setCompactHeight(
            max(
                TextActionButton.MIN_HEIGHT,
                int(round(26 * self._compact_height / self.BASE_HEIGHT)),
            )
        )
        self._transition_status(
            QtGui.QColor(self._TONES[self._tone]),
            animate=animate and changed,
        )
        self.updateGeometry()
        self.update()

    def _stop_status_animation(self) -> None:
        if self._status_animation is None:
            return
        self._status_animation.stop()
        self._status_animation.deleteLater()
        self._status_animation = None

    def toneProgress(self) -> float:
        return self._tone_progress

    def setToneProgress(self, value: float) -> None:
        self._tone_progress = max(0.0, min(1.0, float(value)))
        progress = self._tone_progress
        start = self._tone_start_color
        target = self._tone_target_color
        self._tone_color = QtGui.QColor(
            round(start.red() + (target.red() - start.red()) * progress),
            round(start.green() + (target.green() - start.green()) * progress),
            round(start.blue() + (target.blue() - start.blue()) * progress),
            round(start.alpha() + (target.alpha() - start.alpha()) * progress),
        )
        self.update()

    animatedToneProgress = QtCore.Property(
        float,
        toneProgress,
        setToneProgress,
    )

    def _transition_status(self, target_color: QtGui.QColor, *, animate: bool) -> None:
        self._stop_status_animation()
        self._tone_start_color = QtGui.QColor(self._tone_color)
        self._tone_target_color = QtGui.QColor(target_color)
        self.setToneProgress(0.0)
        if not animate:
            self._text_opacity.setOpacity(1.0)
            self._action_opacity.setOpacity(1.0)
            self.setToneProgress(1.0)
            return

        app = QtWidgets.QApplication.instance()
        reduced_motion = bool(app and app.property("rizumReduceMotion"))
        duration = 80 if reduced_motion else self.STATUS_TRANSITION_DURATION
        group = QtCore.QParallelAnimationGroup(self)
        for effect in (self._text_opacity, self._action_opacity):
            effect.setOpacity(0.35)
            fade = QtCore.QPropertyAnimation(effect, b"opacity", group)
            fade.setDuration(duration)
            fade.setStartValue(0.35)
            fade.setEndValue(1.0)
            fade.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            group.addAnimation(fade)
        tone_animation = QtCore.QPropertyAnimation(
            self,
            b"animatedToneProgress",
            group,
        )
        tone_animation.setDuration(duration)
        tone_animation.setStartValue(0.0)
        tone_animation.setEndValue(1.0)
        tone_animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        group.addAnimation(tone_animation)
        self._status_animation = group

        def finish() -> None:
            if self._status_animation is group:
                self._status_animation = None
            group.deleteLater()

        group.finished.connect(finish)
        group.start()

    def setCompactHeight(self, height: int) -> None:
        self._compact_height = max(self.MIN_HEIGHT, int(round(height)))
        scale = self._compact_height / float(self.BASE_HEIGHT)
        self.setFixedHeight(self._compact_height)
        self._accent_width = max(2, int(round(3 * scale)))
        self._radius = max(4.5, default_theme.radius_small * scale)
        self._layout.setContentsMargins(
            max(9, int(round(12 * scale))),
            max(5, int(round(7 * scale))),
            max(8, int(round(10 * scale))),
            max(5, int(round(7 * scale))),
        )
        self._layout.setSpacing(max(6, int(round(8 * scale))))
        self._text_layout.setSpacing(max(1, int(round(scale))))

        title_font = QtGui.QFont(self.font())
        title_font.setPixelSize(max(9, int(round(12 * scale))))
        title_font.setWeight(QtGui.QFont.Weight.Medium)
        subtitle_font = QtGui.QFont(self.font())
        subtitle_font.setPixelSize(max(8, int(round(10 * scale))))
        subtitle_font.setWeight(QtGui.QFont.Weight.Normal)
        self._title.setFont(title_font)
        self._subtitle.setFont(subtitle_font)
        self._action.setCompactHeight(max(21, int(round(26 * scale))))
        self.updateGeometry()
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor("#252525"))
        frame = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.drawRoundedRect(frame, self._radius, self._radius)
        painter.setBrush(self._tone_color)
        accent = QtCore.QRectF(
            frame.left(),
            frame.top() + self._radius,
            self._accent_width,
            max(1.0, frame.height() - self._radius * 2),
        )
        painter.drawRoundedRect(
            accent,
            self._accent_width / 2.0,
            self._accent_width / 2.0,
        )
        painter.end()


class TextActionButton(QtWidgets.QAbstractButton):
    """Text-only secondary action with quiet hover and press feedback."""

    BASE_HEIGHT = 28
    MIN_HEIGHT = 21

    def __init__(
        self,
        text: str,
        muted: str = PAINTER_DIALOG_STYLE["muted"],
        active: str = PAINTER_DIALOG_STYLE["text"],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setObjectName("RizumTextAction")
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self._muted = QtGui.QColor(muted)
        self._active = QtGui.QColor(active)
        self._compact_height = self.BASE_HEIGHT
        self._hover_progress = 0.0
        self._press_progress = 0.0
        self._hover_animation = None
        self._press_animation = None
        self.setCompactHeight(self.BASE_HEIGHT)

    def _scale(self) -> float:
        return self._compact_height / float(self.BASE_HEIGHT)

    def _font(self) -> QtGui.QFont:
        font = QtGui.QFont(self.font())
        font.setPixelSize(max(9, int(round(12 * self._scale()))))
        font.setWeight(QtGui.QFont.Weight.Normal)
        return font

    def sizeHint(self) -> QtCore.QSize:
        width = QtGui.QFontMetrics(self._font()).horizontalAdvance(self.text()) + 2
        return QtCore.QSize(max(1, width), self._compact_height)

    def setCompactHeight(self, height: int) -> None:
        self._compact_height = max(self.MIN_HEIGHT, int(round(height)))
        hint = self.sizeHint()
        self.setFixedSize(hint.width(), self._compact_height)
        self.updateGeometry()
        self.update()

    def _animate(self, name: str, target: float, duration: int) -> None:
        attribute = f"_{name}_animation"
        previous = getattr(self, attribute)
        if previous is not None:
            previous.stop()
        animation = QtCore.QPropertyAnimation(
            self,
            b"hoverProgress" if name == "hover" else b"pressProgress",
            self,
        )
        animation.setDuration(duration)
        animation.setStartValue(
            self._hover_progress if name == "hover" else self._press_progress
        )
        animation.setEndValue(float(target))
        animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        setattr(self, attribute, animation)
        animation.start()

    def getHoverProgress(self) -> float:
        return self._hover_progress

    def setHoverProgress(self, value: float) -> None:
        self._hover_progress = max(0.0, min(1.0, float(value)))
        self.update()

    hoverProgress = QtCore.Property(float, getHoverProgress, setHoverProgress)

    def getPressProgress(self) -> float:
        return self._press_progress

    def setPressProgress(self, value: float) -> None:
        self._press_progress = max(0.0, min(1.0, float(value)))
        self.update()

    pressProgress = QtCore.Property(float, getPressProgress, setPressProgress)

    def enterEvent(self, event) -> None:
        self._animate("hover", 1.0, 120)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate("hover", 0.0, 140)
        self._animate("press", 0.0, 100)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._animate("press", 1.0, 70)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._animate("press", 0.0, 120)
        super().mouseReleaseEvent(event)

    def focusInEvent(self, event) -> None:
        self._animate("hover", 1.0, 120)
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        if not self.underMouse():
            self._animate("hover", 0.0, 140)
        self._animate("press", 0.0, 100)
        super().focusOutEvent(event)

    def paintEvent(self, event) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
        progress = self._hover_progress
        color = QtGui.QColor(
            round(self._muted.red() + (self._active.red() - self._muted.red()) * progress),
            round(
                self._muted.green()
                + (self._active.green() - self._muted.green()) * progress
            ),
            round(
                self._muted.blue()
                + (self._active.blue() - self._muted.blue()) * progress
            ),
        )
        if self._press_progress:
            color.setAlphaF(max(0.62, 1.0 - 0.28 * self._press_progress))
        painter.setFont(self._font())
        painter.setPen(color)
        y_offset = round(self._press_progress * max(1.0, self._scale()))
        painter.drawText(
            self.rect().translated(0, y_offset),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            self.text(),
        )
        painter.end()


class SecondaryActionButton(QtWidgets.QAbstractButton):
    """Host-independent compact secondary dialog action."""

    BASE_HEIGHT = 28
    MIN_HEIGHT = 21
    HOVER_DURATION = 100
    TEXT_TRANSITION_DURATION = 120

    def __init__(
        self,
        text: str,
        background: str = PAINTER_DIALOG_STYLE["control"],
        hover_background: str = PAINTER_DIALOG_STYLE["control_hover"],
        pressed_background: str = PAINTER_DIALOG_STYLE["control_pressed"],
        text_color: str = PAINTER_DIALOG_STYLE["text"],
        radius: float = default_theme.radius_small,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setObjectName("RizumSecondaryAction")
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet(
            "QAbstractButton#RizumSecondaryAction { background: transparent; border: 0; }"
        )
        self._background = QtGui.QColor(background)
        self._hover_background = QtGui.QColor(hover_background)
        self._pressed_background = QtGui.QColor(pressed_background)
        self._text_color = QtGui.QColor(text_color)
        self._radius = float(radius)
        self._compact_height = self.BASE_HEIGHT
        self._hover_progress = 0.0
        self._hover_animation = None
        self._content_opacity = 1.0
        self._text_animation = None
        self.setCompactHeight(self.BASE_HEIGHT)

    @staticmethod
    def _blend(
        start: QtGui.QColor,
        end: QtGui.QColor,
        progress: float,
    ) -> QtGui.QColor:
        progress = max(0.0, min(1.0, float(progress)))
        return QtGui.QColor(
            round(start.red() + (end.red() - start.red()) * progress),
            round(start.green() + (end.green() - start.green()) * progress),
            round(start.blue() + (end.blue() - start.blue()) * progress),
            round(start.alpha() + (end.alpha() - start.alpha()) * progress),
        )

    def _scale(self) -> float:
        return self._compact_height / float(self.BASE_HEIGHT)

    def _font(self) -> QtGui.QFont:
        font = QtGui.QFont(self.font())
        font.setPixelSize(max(9, int(round(12 * self._scale()))))
        font.setWeight(QtGui.QFont.Weight.Normal)
        return font

    def sizeHint(self) -> QtCore.QSize:
        text_width = QtGui.QFontMetrics(self._font()).horizontalAdvance(self.text())
        return QtCore.QSize(
            text_width + 2 * FOOTER_BUTTON_PADDING_X + 2,
            self._compact_height,
        )

    def setCompactHeight(self, height: int) -> None:
        self._compact_height = max(self.MIN_HEIGHT, int(round(height)))
        self.setFixedHeight(self._compact_height)
        self.updateGeometry()
        self.update()

    def hoverProgress(self) -> float:
        return self._hover_progress

    def setHoverProgress(self, value: float) -> None:
        self._hover_progress = max(0.0, min(1.0, float(value)))
        self.update()

    animatedHoverProgress = QtCore.Property(
        float,
        hoverProgress,
        setHoverProgress,
    )

    def contentOpacity(self) -> float:
        return self._content_opacity

    def setContentOpacity(self, value: float) -> None:
        self._content_opacity = max(0.0, min(1.0, float(value)))
        self.update()

    animatedContentOpacity = QtCore.Property(
        float,
        contentOpacity,
        setContentOpacity,
    )

    def setAnimatedText(self, text: str, *, animate: bool = True) -> None:
        text = str(text)
        if text == self.text():
            return
        if self._text_animation is not None:
            self._text_animation.stop()
            self._text_animation.deleteLater()
            self._text_animation = None
        self.setText(text)
        self.updateGeometry()
        if not animate:
            self.setContentOpacity(1.0)
            return

        app = QtWidgets.QApplication.instance()
        reduced_motion = bool(app and app.property("rizumReduceMotion"))
        duration = 80 if reduced_motion else self.TEXT_TRANSITION_DURATION
        self.setContentOpacity(0.35)
        animation = QtCore.QPropertyAnimation(
            self,
            b"animatedContentOpacity",
            self,
        )
        animation.setDuration(duration)
        animation.setStartValue(0.35)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._text_animation = animation

        def finish() -> None:
            if self._text_animation is animation:
                self._text_animation = None
            animation.deleteLater()

        animation.finished.connect(finish)
        animation.start()

    def _animate_hover(self, target: float) -> None:
        if self._hover_animation is not None:
            self._hover_animation.stop()
            self._hover_animation.deleteLater()
        animation = QtCore.QPropertyAnimation(
            self,
            b"animatedHoverProgress",
            self,
        )
        animation.setDuration(self.HOVER_DURATION)
        animation.setStartValue(self._hover_progress)
        animation.setEndValue(float(target))
        animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._hover_animation = animation

        def clear_animation() -> None:
            if self._hover_animation is animation:
                self._hover_animation = None
            animation.deleteLater()

        animation.finished.connect(clear_animation)
        animation.start()

    def enterEvent(self, event) -> None:
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
        if self.isDown():
            background = self._pressed_background
        else:
            hover_progress = max(
                self._hover_progress,
                1.0 if self.hasFocus() else 0.0,
            )
            background = self._blend(
                self._background,
                self._hover_background,
                hover_progress,
            )
        radius = max(4.0, self._radius * self._scale())
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(
            QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            radius,
            radius,
        )
        painter.setFont(self._font())
        painter.setPen(self._text_color)
        painter.setOpacity(self._content_opacity)
        painter.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()


class IconActionButton(SecondaryActionButton):
    """Compact action that centers an SVG icon next to its label.

    Painted icon geometry follows the font-scale standard: the icon size
    lives on ``self`` and can be changed at runtime via
    ``setPaintedIconSize`` (cache invalidation + base x 0.75 floor), and
    ``setCompactHeight`` re-derives it from the 28 px baseline so callers
    only need the one call.
    """

    BASE_ICON_SIZE = 14
    MIN_ICON_SIZE = 10  # round(14 x 0.75)
    ICON_GAP = 6

    def __init__(self, text: str, icon_name: str, *args, **kwargs) -> None:
        self._icon_name = icon_name
        self._icon_size = self.BASE_ICON_SIZE
        self._icon_cache: dict = {}
        super().__init__(text, *args, **kwargs)

    def paintedIconSize(self) -> int:
        return self._icon_size

    def setPaintedIconSize(self, icon_size: int) -> None:
        new_size = max(self.MIN_ICON_SIZE, int(round(icon_size)))
        if new_size == self._icon_size:
            return
        self._icon_size = new_size
        self._icon_cache.clear()
        self.updateGeometry()
        self.update()

    def setCompactHeight(self, height: int) -> None:
        super().setCompactHeight(height)
        self.setPaintedIconSize(
            round(self.BASE_ICON_SIZE * self._compact_height / float(self.BASE_HEIGHT))
        )

    def _icon_gap(self) -> int:
        return max(4, int(round(self.ICON_GAP * self._scale())))

    def sizeHint(self) -> QtCore.QSize:
        hint = super().sizeHint()
        return QtCore.QSize(
            hint.width() + self._icon_size + self._icon_gap(),
            hint.height(),
        )

    def _icon_pixmap(self, color: str) -> QtGui.QPixmap:
        dpr = self.devicePixelRatioF()
        key = (color, self._icon_size, round(dpr, 2))
        pixmap = self._icon_cache.get(key)
        if pixmap is None:
            pixmap = render_svg_pixmap(self._icon_name, self._icon_size, color)
            self._icon_cache[key] = pixmap
        return pixmap

    def paintEvent(self, event) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(
            QtGui.QPainter.RenderHint.SmoothPixmapTransform, True
        )
        if self.isDown():
            background = self._pressed_background
        else:
            hover_progress = max(
                self._hover_progress,
                1.0 if self.hasFocus() else 0.0,
            )
            background = self._blend(
                self._background,
                self._hover_background,
                hover_progress,
            )
        radius = max(4.0, self._radius * self._scale())
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(
            QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            radius,
            radius,
        )
        font = self._font()
        painter.setFont(font)
        painter.setOpacity(self._content_opacity)
        icon_size = self._icon_size
        icon_gap = self._icon_gap()
        text_width = QtGui.QFontMetrics(font).horizontalAdvance(self.text())
        content_width = icon_size + icon_gap + text_width
        left = max(0.0, (self.width() - content_width) / 2.0)
        painter.drawPixmap(
            int(round(left)),
            int(round((self.height() - icon_size) / 2.0)),
            self._icon_pixmap(self._text_color.name()),
        )
        painter.setPen(self._text_color)
        painter.drawText(
            QtCore.QRectF(
                left + icon_size + icon_gap,
                0,
                text_width + 1,
                self.height(),
            ),
            QtCore.Qt.AlignmentFlag.AlignLeft
            | QtCore.Qt.AlignmentFlag.AlignVCenter,
            self.text(),
        )
        painter.end()


class AnimatedSaveButton(QtWidgets.QAbstractButton):
    """Save action that communicates clean, dirty, and saved states in place."""

    BASE_HEIGHT = 28
    MIN_HEIGHT = 21
    ACTIVATION_DURATION = 140
    FEEDBACK_DURATION = 500
    HOVER_DURATION = 100

    def __init__(
        self,
        text: str,
        disabled_background: str = PAINTER_DIALOG_STYLE["control"],
        disabled_text: str = PAINTER_DIALOG_STYLE["faint"],
        active_background: str = PAINTER_DIALOG_STYLE["accent"],
        active_text: str = PAINTER_DIALOG_STYLE["accent_text"],
        radius: float = default_theme.radius_small,
        parent=None,
        *,
        active_hover_background: str = PAINTER_DIALOG_STYLE["accent_hover"],
        active_pressed_background: str = PAINTER_DIALOG_STYLE["accent_pressed"],
    ) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setObjectName("RizumAnimatedSave")
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet(
            "QAbstractButton#RizumAnimatedSave { background: transparent; border: 0; }"
        )
        self._disabled_background = QtGui.QColor(disabled_background)
        self._disabled_text = QtGui.QColor(disabled_text)
        self._active_background = QtGui.QColor(active_background)
        self._active_text = QtGui.QColor(active_text)
        self._active_hover_background = QtGui.QColor(active_hover_background)
        self._active_pressed_background = QtGui.QColor(active_pressed_background)
        self._radius = float(radius)
        self._compact_height = self.BASE_HEIGHT
        self._dirty = None
        self._feedback_active = False
        self._activation_progress = 0.0
        self._pulse_progress = 0.0
        self._check_progress = 0.0
        self._hover_progress = 0.0
        self._state_animation = None
        self._feedback_animation = None
        self._hover_animation = None
        self.setCompactHeight(self.BASE_HEIGHT)
        self.setDirty(False, animate=False)

    @staticmethod
    def _blend(start: QtGui.QColor, end: QtGui.QColor, progress: float) -> QtGui.QColor:
        progress = max(0.0, min(1.0, float(progress)))
        return QtGui.QColor(
            round(start.red() + (end.red() - start.red()) * progress),
            round(start.green() + (end.green() - start.green()) * progress),
            round(start.blue() + (end.blue() - start.blue()) * progress),
            round(start.alpha() + (end.alpha() - start.alpha()) * progress),
        )

    def _scale(self) -> float:
        return self._compact_height / float(self.BASE_HEIGHT)

    def _font(self) -> QtGui.QFont:
        font = QtGui.QFont(self.font())
        font.setPixelSize(max(9, int(round(12 * self._scale()))))
        font.setWeight(QtGui.QFont.Weight.Normal)
        return font

    def sizeHint(self) -> QtCore.QSize:
        text_width = QtGui.QFontMetrics(self._font()).horizontalAdvance(self.text())
        return QtCore.QSize(
            text_width + 2 * FOOTER_BUTTON_PADDING_X + 2,
            self._compact_height,
        )

    def setCompactHeight(self, height: int) -> None:
        self._compact_height = max(self.MIN_HEIGHT, int(round(height)))
        self.setFont(self._font())
        self.setFixedHeight(self._compact_height)
        self.updateGeometry()
        self.update()

    def isDirty(self) -> bool:
        return bool(self._dirty)

    def feedbackActive(self) -> bool:
        return self._feedback_active

    def activationDuration(self) -> int:
        return self.ACTIVATION_DURATION

    def feedbackDuration(self) -> int:
        return self.FEEDBACK_DURATION

    def activationProgress(self) -> float:
        return self._activation_progress

    def setActivationProgress(self, value: float) -> None:
        self._activation_progress = max(0.0, min(1.0, float(value)))
        self.update()

    animatedActivationProgress = QtCore.Property(
        float, activationProgress, setActivationProgress
    )

    def pulseProgress(self) -> float:
        return self._pulse_progress

    def setPulseProgress(self, value: float) -> None:
        self._pulse_progress = max(0.0, min(1.0, float(value)))
        self.update()

    animatedPulseProgress = QtCore.Property(float, pulseProgress, setPulseProgress)

    def checkProgress(self) -> float:
        return self._check_progress

    def setCheckProgress(self, value: float) -> None:
        self._check_progress = max(0.0, min(1.0, float(value)))
        self.update()

    animatedCheckProgress = QtCore.Property(float, checkProgress, setCheckProgress)

    def hoverProgress(self) -> float:
        return self._hover_progress

    def setHoverProgress(self, value: float) -> None:
        self._hover_progress = max(0.0, min(1.0, float(value)))
        self.update()

    animatedHoverProgress = QtCore.Property(
        float,
        hoverProgress,
        setHoverProgress,
    )

    def _animate_hover(self, target: float) -> None:
        self._stop_animation("_hover_animation")
        animation = QtCore.QPropertyAnimation(
            self,
            b"animatedHoverProgress",
            self,
        )
        animation.setDuration(self.HOVER_DURATION)
        animation.setStartValue(self._hover_progress)
        animation.setEndValue(float(target))
        animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._hover_animation = animation
        animation.finished.connect(
            lambda: self._clear_animation("_hover_animation", animation)
        )
        animation.start()

    def _stop_animation(self, attribute: str) -> None:
        animation = getattr(self, attribute)
        if animation is None:
            return
        animation.stop()
        animation.deleteLater()
        setattr(self, attribute, None)

    def _clear_animation(self, attribute: str, animation) -> None:
        if getattr(self, attribute) is animation:
            setattr(self, attribute, None)
        animation.deleteLater()

    def setDirty(
        self,
        dirty: bool,
        animate: bool = True,
        *,
        pulse: bool = True,
    ) -> None:
        dirty = bool(dirty)
        if self._feedback_active and not dirty:
            self._dirty = False
            return
        if dirty and self._feedback_active:
            self._stop_animation("_feedback_animation")
            self._feedback_active = False
            self.setCheckProgress(0.0)
        if dirty == self._dirty and not self._feedback_active:
            return
        self._dirty = dirty
        self._stop_animation("_state_animation")
        self.setCursor(
            QtCore.Qt.CursorShape.PointingHandCursor
            if dirty
            else QtCore.Qt.CursorShape.ArrowCursor
        )
        super().setEnabled(dirty)
        if not dirty:
            self._stop_animation("_hover_animation")
            self.setHoverProgress(0.0)

        target = 1.0 if dirty else 0.0
        if not animate:
            self.setActivationProgress(target)
            self.setPulseProgress(0.0)
            return

        group = QtCore.QParallelAnimationGroup(self)
        activation = QtCore.QPropertyAnimation(
            self, b"animatedActivationProgress", group
        )
        activation.setDuration(self.ACTIVATION_DURATION if dirty else 120)
        activation.setStartValue(self._activation_progress)
        activation.setEndValue(target)
        activation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        group.addAnimation(activation)
        if dirty and pulse:
            pulse = QtCore.QPropertyAnimation(self, b"animatedPulseProgress", group)
            pulse.setDuration(190)
            pulse.setStartValue(0.0)
            pulse.setKeyValueAt(0.58, 0.0)
            pulse.setKeyValueAt(0.78, 1.0)
            pulse.setEndValue(0.0)
            pulse.setEasingCurve(QtCore.QEasingCurve.Type.InOutSine)
            group.addAnimation(pulse)
        else:
            self.setPulseProgress(0.0)
        self._state_animation = group
        group.finished.connect(lambda: self._clear_animation("_state_animation", group))
        group.start()

    def showSavedFeedback(self) -> None:
        if not self._dirty:
            return
        self._stop_animation("_state_animation")
        self._stop_animation("_feedback_animation")
        self._dirty = False
        self._feedback_active = True
        super().setEnabled(False)
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        self._stop_animation("_hover_animation")
        self.setHoverProgress(0.0)
        self.setActivationProgress(1.0)
        self.setPulseProgress(0.0)
        self.setCheckProgress(0.0)

        group = QtCore.QParallelAnimationGroup(self)
        check = QtCore.QPropertyAnimation(self, b"animatedCheckProgress", group)
        check.setDuration(self.FEEDBACK_DURATION)
        check.setStartValue(0.0)
        check.setKeyValueAt(0.22, 1.0)
        check.setKeyValueAt(0.72, 1.0)
        check.setEndValue(0.0)
        group.addAnimation(check)
        activation = QtCore.QPropertyAnimation(
            self, b"animatedActivationProgress", group
        )
        activation.setDuration(self.FEEDBACK_DURATION)
        activation.setStartValue(1.0)
        activation.setKeyValueAt(0.72, 1.0)
        activation.setEndValue(0.0)
        activation.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)
        group.addAnimation(activation)
        self._feedback_animation = group

        def finish() -> None:
            self._feedback_active = False
            self.setCheckProgress(0.0)
            self.setActivationProgress(0.0)
            self._clear_animation("_feedback_animation", group)

        group.finished.connect(finish)
        group.start()

    def enterEvent(self, event) -> None:
        if self._dirty and self.isEnabled():
            self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.update()

    def _checkmark_polygon(self) -> QtGui.QPolygonF:
        scale = self._scale()
        center = QtCore.QRectF(self.rect()).center()
        # The authored path bounds are offset from its origin; compensate so
        # the visible mark, rather than that origin, shares the text center.
        # Extra +1.0 design px: a bounds-centered check reads optically high
        # against the Save label, so bias the mark down (user report).
        origin = QtCore.QPointF(
            center.x() - 0.35 * scale,
            center.y() + 1.4 * scale,
        )
        return QtGui.QPolygonF(
            [
                QtCore.QPointF(origin.x() - 4.5 * scale, origin.y()),
                QtCore.QPointF(
                    origin.x() - 1.2 * scale,
                    origin.y() + 3.0 * scale,
                ),
                QtCore.QPointF(
                    origin.x() + 5.2 * scale,
                    origin.y() - 3.8 * scale,
                ),
            ]
        )

    def paintEvent(self, event) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)

        background = self._blend(
            self._disabled_background,
            self._active_background,
            self._activation_progress,
        )
        if self._pulse_progress:
            background = self._blend(
                background, QtGui.QColor("#ffffff"), 0.12 * self._pulse_progress
            )
        if self._dirty and self.isEnabled():
            if self.isDown():
                background = self._active_pressed_background
            elif self._hover_progress:
                background = self._blend(
                    background,
                    self._active_hover_background,
                    self._hover_progress,
                )
        text_color = self._blend(
            self._disabled_text,
            self._active_text,
            self._activation_progress,
        )
        radius = max(4.0, self._radius * self._scale())
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(
            QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            radius,
            radius,
        )

        painter.setFont(self._font())
        painter.setPen(text_color)
        painter.setOpacity(1.0 - self._check_progress)
        painter.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, self.text())

        painter.setOpacity(self._check_progress)
        scale = self._scale()
        pen = QtGui.QPen(text_color, max(1.4, 1.7 * scale))
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline(self._checkmark_polygon())
        painter.end()


class ShortcutCaptureField(QtWidgets.QFrame):
    """Painted shortcut field with stable capture, clear, and conflict states."""

    shortcutChanged = QtCore.Signal(str)
    captureStateChanged = QtCore.Signal(bool)

    BASE_HEIGHT = 30
    MIN_HEIGHT = 23

    def __init__(
        self,
        action_name: str = "",
        shortcut: str = "",
        parent=None,
        *,
        visual_style: Mapping[str, str] | None = None,
        capture_text: str = "Type shortcut…",
        empty_text: str = "Not set",
        conflict_text: str = "Shortcut conflict",
        normalizer: Callable[[str], str] | None = None,
        formatter: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RizumShortcutCapture")
        self._action_name = action_name
        self._visual_style = dict(visual_style or {})
        self._capture_text = str(capture_text)
        self._empty_text = str(empty_text)
        self._conflict_text = str(conflict_text)
        self._normalizer = normalizer or (lambda value: str(value or "").strip())
        self._formatter = formatter or (lambda value: value)
        self._shortcut = ""
        self._capturing = False
        self._conflicted = False
        self._compact_height = self.BASE_HEIGHT
        self._hovered = False
        self._hover_clear = False
        self._pressed_clear = False
        self.setFixedHeight(self.BASE_HEIGHT)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        self.setStyleSheet(
            "QFrame#RizumShortcutCapture { background: transparent; border: 0; }"
        )
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
        self.setAccessibleName(action_name)
        self.setShortcut(shortcut, emit=False)

    def actionName(self) -> str:
        return self._action_name

    def shortcut(self) -> str:
        return self._shortcut

    def setShortcut(self, text: str, emit: bool = True) -> None:
        text = self._normalizer(text)
        if text == self._shortcut:
            self.refreshMetrics()
            self.update()
            return
        self._shortcut = text
        self.refreshMetrics()
        self.update()
        if emit:
            self.shortcutChanged.emit(self._shortcut)

    def isCapturing(self) -> bool:
        return self._capturing

    def setConflicted(self, conflicted: bool, detail: str | None = None) -> None:
        conflicted = bool(conflicted)
        self._conflicted = conflicted
        description = detail or self._conflict_text
        self.setAccessibleDescription(description if conflicted else "")
        self.update()

    def setCompactHeight(self, height: int) -> None:
        self._compact_height = max(self.MIN_HEIGHT, int(round(height)))
        self.setFixedHeight(self._compact_height)
        self.refreshMetrics()
        self.update()

    def refreshMetrics(self) -> None:
        self.setFixedWidth(self.sizeHint().width())
        self.updateGeometry()

    def _scale(self) -> float:
        return self._compact_height / float(self.BASE_HEIGHT)

    def _scaled(self, value: float) -> int:
        return max(int(round(value * 0.75)), int(round(value * self._scale())))

    def _font(self) -> QtGui.QFont:
        font = QtGui.QFont(self.font())
        font.setPixelSize(self._scaled(12))
        font.setWeight(QtGui.QFont.Weight.Medium)
        return font

    def _display_text(self) -> str:
        if self._capturing:
            return self._capture_text
        if not self._shortcut:
            return self._empty_text
        return self._formatter(self._shortcut) or self._shortcut

    def _clear_slot_width(self) -> int:
        return self._scaled(22) if self._shortcut and not self._capturing else 0

    def _reserved_clear_slot_width(self) -> int:
        return self._scaled(22) if self._shortcut else 0

    def _clear_rect(self) -> QtCore.QRectF:
        slot = self._clear_slot_width()
        if not slot:
            return QtCore.QRectF()
        return QtCore.QRectF(self.width() - slot, 0, slot, self.height())

    def _conflict_rect(self) -> QtCore.QRectF:
        if not self._conflicted or self._capturing:
            return QtCore.QRectF()
        return self._clear_rect()

    def sizeHint(self) -> QtCore.QSize:
        metrics = QtGui.QFontMetrics(self._font())
        candidates = [self._display_text(), self._capture_text, self._empty_text]
        if self._shortcut:
            candidates.append(self._formatter(self._shortcut) or self._shortcut)
        text_width = max(metrics.horizontalAdvance(text) for text in candidates)
        width = (
            self._scaled(10)
            + text_width
            + self._reserved_clear_slot_width()
            + self._scaled(8)
        )
        return QtCore.QSize(max(self._scaled(64), width), self._compact_height)

    def minimumSizeHint(self) -> QtCore.QSize:
        return self.sizeHint()

    def startCapture(self) -> None:
        if self._capturing:
            return
        self._capturing = True
        self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
        self.refreshMetrics()
        self.update()
        self.captureStateChanged.emit(True)

    def cancelCapture(self) -> None:
        if not self._capturing:
            return
        self._capturing = False
        self.refreshMetrics()
        self.update()
        self.captureStateChanged.emit(False)

    def finishCapture(self, text: str) -> None:
        self._capturing = False
        self.setShortcut(text)
        self.captureStateChanged.emit(False)

    def keyPressEvent(self, event) -> None:
        if self._capturing:
            key = event.key()
            if key == QtCore.Qt.Key.Key_Escape:
                self.cancelCapture()
                event.accept()
                return
            if key in (QtCore.Qt.Key.Key_Backspace, QtCore.Qt.Key.Key_Delete):
                self.finishCapture("")
                event.accept()
                return
            if key in (
                QtCore.Qt.Key.Key_Control,
                QtCore.Qt.Key.Key_Shift,
                QtCore.Qt.Key.Key_Alt,
                QtCore.Qt.Key.Key_Meta,
                QtCore.Qt.Key.Key_unknown,
            ):
                event.accept()
                return
            if key in (QtCore.Qt.Key.Key_Tab, QtCore.Qt.Key.Key_Backtab):
                self.cancelCapture()
                event.ignore()
                return
            sequence = QtGui.QKeySequence(int(event.modifiers()) | key)
            text = sequence.toString(QtGui.QKeySequence.SequenceFormat.PortableText)
            if text:
                self.finishCapture(text)
            event.accept()
            return
        if event.key() in (
            QtCore.Qt.Key.Key_Return,
            QtCore.Qt.Key.Key_Enter,
            QtCore.Qt.Key.Key_Space,
        ):
            self.startCapture()
            event.accept()
            return
        if event.key() in (QtCore.Qt.Key.Key_Backspace, QtCore.Qt.Key.Key_Delete):
            if self._shortcut:
                self.setShortcut("")
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event) -> None:
        self.cancelCapture()
        super().focusOutEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self._clear_rect().contains(event.position()):
                self._pressed_clear = True
            else:
                self.startCapture()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            was_clear = self._pressed_clear
            self._pressed_clear = False
            if was_clear and self._clear_rect().contains(event.position()):
                self.setShortcut("")
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        hover_clear = self._clear_rect().contains(event.position())
        if hover_clear != self._hover_clear:
            self._hover_clear = hover_clear
            self.update()
        super().mouseMoveEvent(event)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._hover_clear = False
        self._pressed_clear = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)

        theme = default_theme
        radius = float(self._scaled(self._visual_style.get("field_radius", 6)))
        rect = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        background = QtGui.QColor(
            self._visual_style.get("control", theme.surface_control)
        )
        if self._hovered or self._capturing:
            hover = self._visual_style.get("control_hover")
            background = QtGui.QColor(hover) if hover else background.lighter(112)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(rect, radius, radius)

        border_color = None
        if self._capturing:
            border_color = QtGui.QColor(theme.accent)
        elif self._conflicted:
            border_color = QtGui.QColor(theme.warning)
        elif self.hasFocus():
            border_color = QtGui.QColor(theme.border)
        elif self._visual_style.get("border"):
            border_color = QtGui.QColor(self._visual_style["border"])
        if border_color is not None:
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.setPen(QtGui.QPen(border_color, 1))
            painter.drawRoundedRect(rect, radius, radius)

        text = self._display_text()
        if self._conflicted and not self._capturing:
            text_color = QtGui.QColor(theme.warning)
        elif self._capturing:
            text_color = QtGui.QColor(
                self._visual_style.get("muted", theme.text_muted)
            )
        elif self._shortcut:
            text_color = QtGui.QColor(self._visual_style.get("text", theme.text))
        else:
            text_color = QtGui.QColor(
                self._visual_style.get("faint", theme.text_faint)
            )
        font = self._font()
        painter.setFont(font)
        painter.setPen(text_color)
        metrics = QtGui.QFontMetricsF(font)
        available = (
            rect.width()
            - self._scaled(10)
            - self._clear_slot_width()
            - self._scaled(8)
        )
        text = metrics.elidedText(
            text, QtCore.Qt.TextElideMode.ElideRight, int(available)
        )
        baseline = rect.center().y() + (metrics.ascent() - metrics.descent()) / 2
        painter.drawText(QtCore.QPointF(self._scaled(10), baseline), text)

        conflict_rect = self._conflict_rect()
        if not conflict_rect.isEmpty() and not self._hover_clear:
            marker_size = self._scaled(10)
            marker = QtCore.QRectF(
                conflict_rect.center().x() - marker_size / 2,
                conflict_rect.center().y() - marker_size / 2,
                marker_size,
                marker_size,
            )
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(theme.warning))
            painter.drawEllipse(marker)
            marker_font = QtGui.QFont(font)
            marker_font.setPixelSize(self._scaled(8))
            marker_font.setWeight(QtGui.QFont.Weight.Bold)
            painter.setFont(marker_font)
            painter.setPen(background)
            painter.drawText(marker, QtCore.Qt.AlignmentFlag.AlignCenter, "!")

        clear_rect = self._clear_rect()
        if not clear_rect.isEmpty() and (not self._conflicted or self._hover_clear):
            glyph_color = (
                QtGui.QColor(self._visual_style.get("text", theme.text))
                if self._hover_clear
                else QtGui.QColor(self._visual_style.get("faint", theme.text_faint))
            )
            scale = self._scale()
            pen = QtGui.QPen(glyph_color, max(1.2, 1.4 * scale))
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            half = 3.2 * scale
            center = clear_rect.center()
            painter.drawLine(
                QtCore.QPointF(center.x() - half, center.y() - half),
                QtCore.QPointF(center.x() + half, center.y() + half),
            )
            painter.drawLine(
                QtCore.QPointF(center.x() - half, center.y() + half),
                QtCore.QPointF(center.x() + half, center.y() - half),
            )
        painter.end()


class ModeParameterSlot(QtWidgets.QFrame):
    """Atomic stacked slot for mode-specific rows without compositor effects."""

    def __init__(self, rows: Mapping[str, QtWidgets.QWidget], height: int, parent=None):
        super().__init__(parent)
        self.setObjectName("RizumModeParameterSlot")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        self.setStyleSheet(
            "QFrame#RizumModeParameterSlot { background: transparent; border: 0; }"
        )
        self._rows = dict(rows)
        self._mode = None
        self._expanded_height = max(0, int(round(height)))
        self._height_progress = 0.0
        self._geometry_callback = None
        self._layout = QtWidgets.QStackedLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.setStackingMode(QtWidgets.QStackedLayout.StackingMode.StackOne)
        for row in self._rows.values():
            row.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            row.setFixedHeight(self._expanded_height)
            self._layout.addWidget(row)
        self.setFixedHeight(0)
        self.hide()

    def expandedHeight(self) -> int:
        return self._expanded_height

    def setExpandedHeight(self, height: int) -> None:
        self._expanded_height = max(0, int(round(height)))
        for row in self._rows.values():
            row.setFixedHeight(self._expanded_height)
        self._sync_geometry()

    def setGeometryCallback(self, callback) -> None:
        self._geometry_callback = callback

    def heightProgress(self) -> float:
        return self._height_progress

    def setHeightProgress(self, value: float) -> None:
        self._height_progress = max(0.0, min(1.0, float(value)))
        self._sync_geometry()

    animatedHeightProgress = QtCore.Property(float, heightProgress, setHeightProgress)

    def rowOpacity(self, mode: str) -> float:
        return 1.0 if mode == self._mode else 0.0

    def progress(self) -> float:
        return self._height_progress

    def currentMode(self) -> str | None:
        return self._mode

    def _sync_geometry(self) -> None:
        self.setFixedHeight(round(self._expanded_height * self._height_progress))
        if self._geometry_callback is not None:
            self._geometry_callback(self._height_progress)

    def setMode(self, mode: str | None, animate: bool = True) -> None:
        del animate
        target_mode = mode if mode in self._rows else None
        self._mode = target_mode
        for key, row in self._rows.items():
            row.setAttribute(
                QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                key != target_mode,
            )
        if target_mode is not None:
            self.show()
            self._layout.setCurrentWidget(self._rows[target_mode])
            self.setHeightProgress(1.0)
        else:
            self.setHeightProgress(0.0)
            self.hide()
        self.update()


__all__ = [
    "AnimatedSaveButton",
    "ModeParameterSlot",
    "PAINTER_DIALOG_STYLE",
    "SettingsToggle",
    "StatusBanner",
    "SecondaryActionButton",
    "ShortcutCaptureField",
    "TextActionButton",
]
