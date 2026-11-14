"""Input events where they arrive, instead of every event of the application.

A filter on QApplication is called for each event of every object. Painter
sends about 400 a second when nothing happens and 3,000 to 5,000 while the
pointer moves or a stroke is painted, and each call into Python costs a few
microseconds, most of it for wrapping the receiver. On the user's project
the application filters of four plugins took about 40 ms of every second of
painting (2026-11-13, measured with ``tools/painter_perf_check.py``).

Qt hands keyboard, mouse, tablet and wheel input to a window first (a
``QWindow``: the main window's, a floating panel's, the 3D view's own) and
only then to widgets. A filter on the windows sees each input event exactly
once and nothing else: no timers, no paints, and none of the repeats an
application filter gets while an event travels up through the widgets.

What a window filter gets:

- ``KeyPress`` / ``KeyRelease``, and ``ShortcutOverride`` before a shortcut
  fires. A key that fires a shortcut sends the override and the release, not
  the press.
- ``MouseButtonPress`` / ``MouseButtonRelease`` / ``MouseMove``, ``Wheel``,
  ``TabletPress`` / ``TabletMove`` / ``TabletRelease``.
- ``watched`` is the ``QWindow``. The widget under the pointer is
  ``QApplication.widgetAt(event.globalPosition().toPoint())``, the one with
  the keyboard ``QApplication.focusWidget()``.

What it does not get: ``Show``, ``Shortcut`` and the application's own
events. Use ``QGuiApplication.applicationStateChanged`` and
``focusWindowChanged`` for those.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui


# A window that appears without taking the focus (a new native view) is
# found by this sweep. One that takes the focus, or whose appearing moves the
# focus (a dialog, a menu), is found at once. Painter has over a hundred
# windows, most of them hidden, and a sweep takes 0.4 ms.
SWEEP_MS = 5000


class WindowInputWatch(QtCore.QObject):
    """Keeps an event filter installed on every window of the application."""

    def __init__(self, event_filter: QtCore.QObject):
        super().__init__()
        self._filter = event_filter
        self._running = False
        # Owned, so it dies with the watch: nothing runs after the close.
        self._sweep = QtCore.QTimer(self)
        self._sweep.setInterval(SWEEP_MS)
        self._sweep.timeout.connect(self._install)

    def start(self) -> None:
        app = QtGui.QGuiApplication.instance()
        if app is None or self._running:
            return
        self._running = True
        app.focusWindowChanged.connect(self._install)
        app.focusObjectChanged.connect(self._install)
        self._install()
        self._sweep.start()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._sweep.stop()
        app = QtGui.QGuiApplication.instance()
        if app is None:
            return
        app.focusWindowChanged.disconnect(self._install)
        app.focusObjectChanged.disconnect(self._install)
        for window in QtGui.QGuiApplication.allWindows():
            window.removeEventFilter(self._filter)

    @QtCore.Slot()
    def _install(self, *_arguments) -> None:
        # Installing again moves the filter to the front of the window's
        # list; it does not add a second one.
        for window in QtGui.QGuiApplication.allWindows():
            window.installEventFilter(self._filter)
