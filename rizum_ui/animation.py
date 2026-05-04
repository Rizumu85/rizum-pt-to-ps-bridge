"""Small animation helpers that work with ordinary Qt widgets."""

from __future__ import annotations


def fade_in(widget, duration=160, start=0.0, end=1.0):
    """Fade a widget in and keep the animation alive on the widget."""
    from PySide6 import QtCore, QtWidgets

    effect = widget.graphicsEffect()
    if effect is None:
        effect = QtWidgets.QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    effect.setOpacity(start)

    animation = QtCore.QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
    widget._rizum_fade_animation = animation
    animation.start()
    return animation
