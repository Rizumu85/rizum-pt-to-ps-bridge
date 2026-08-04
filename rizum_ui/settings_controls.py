"""Compact interaction controls for Painter settings dialogs."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from PySide6 import QtCore, QtGui, QtWidgets

from .components import FOOTER_BUTTON_PADDING_X
from .theme import default_theme


class TextActionButton(QtWidgets.QAbstractButton):
    """Text-only secondary action with quiet hover and press feedback."""

    BASE_HEIGHT = 28
    MIN_HEIGHT = 21

    def __init__(
        self,
        text: str,
        muted: str = "#a8acb2",
        active: str = "#f0f0f0",
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

    def __init__(
        self,
        text: str,
        background: str = "#303236",
        hover_background: str = "#383a3e",
        pressed_background: str = "#2b2d30",
        text_color: str = "#f0f0f0",
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
        self.setCompactHeight(self.BASE_HEIGHT)

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

    def paintEvent(self, event) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
        if self.isDown():
            background = self._pressed_background
        elif self.underMouse() or self.hasFocus():
            background = self._hover_background
        else:
            background = self._background
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
        painter.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()


class AnimatedSaveButton(QtWidgets.QAbstractButton):
    """Save action that communicates clean, dirty, and saved states in place."""

    BASE_HEIGHT = 28
    MIN_HEIGHT = 21
    ACTIVATION_DURATION = 140
    FEEDBACK_DURATION = 500

    def __init__(
        self,
        text: str,
        disabled_background: str = "#303236",
        disabled_text: str = "#858a90",
        active_background: str = "#f2f2f2",
        active_text: str = "#202123",
        radius: float = default_theme.radius_small,
        parent=None,
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
        self._radius = float(radius)
        self._compact_height = self.BASE_HEIGHT
        self._dirty = None
        self._feedback_active = False
        self._activation_progress = 0.0
        self._pulse_progress = 0.0
        self._check_progress = 0.0
        self._state_animation = None
        self._feedback_animation = None
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

    def setDirty(self, dirty: bool, animate: bool = True) -> None:
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
        if dirty:
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
                background = background.darker(112)
            elif self.underMouse():
                background = background.lighter(104)
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
        center = QtCore.QPointF(self.rect().center())
        pen = QtGui.QPen(text_color, max(1.4, 1.7 * scale))
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline(
            QtGui.QPolygonF(
                [
                    QtCore.QPointF(center.x() - 4.5 * scale, center.y()),
                    QtCore.QPointF(center.x() - 1.2 * scale, center.y() + 3.0 * scale),
                    QtCore.QPointF(center.x() + 5.2 * scale, center.y() - 3.8 * scale),
                ]
            )
        )
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
            self._layout.setCurrentWidget(self._rows[target_mode])
        self.setHeightProgress(1.0 if target_mode is not None else 0.0)
        self.update()


__all__ = [
    "AnimatedSaveButton",
    "ModeParameterSlot",
    "SecondaryActionButton",
    "ShortcutCaptureField",
    "TextActionButton",
]
