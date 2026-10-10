"""Keep Python event filters from crashing Painter when it exits.

PySide tags every C++ QObject it hands to Python with a dynamic property whose
destructor calls back into the bindings. A Python application event filter is
handed every object that receives an event, and that includes Qt's global
pixmap cache. The cache is a static in Qt6Gui, destroyed at process exit after
an embedding host such as Painter has already unloaded the bindings, so the
callback runs in freed memory and Painter crashes on exit (access violation in
shiboken6 under ``~QPMCache``; ``tools/exit_crash_repro.py`` reproduces it).

PySide leaves the property alone once it holds a value, so the guard replaces
it with a plain one the first time the cache's timer event comes by, then
removes itself. One guard covers every Python filter in the process, other
plugins' included.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


PYSIDE_PROPERTY = "_PySideInvalidatePtr"
STATIC_CLASSES = frozenset({"QPMCache"})
DONE_PROPERTY = "rizumExitGuardDone"
_TIMER = QtCore.QEvent.Type.Timer


class _ExitGuard(QtCore.QObject):
    def eventFilter(self, watched, event):
        if (
            event.type() == _TIMER
            # PySide knows none of these classes, so it hands them over as
            # plain QObjects; the exact-type test keeps the class-name lookup
            # off every other timer event.
            and type(watched) is QtCore.QObject
            and watched.metaObject().className() in STATIC_CLASSES
        ):
            watched.setProperty(PYSIDE_PROPERTY, True)
            remove(self, done=True)
        return False


def install():
    """Start the guard; returns it for ``remove()``, or None when not needed."""
    app = QtWidgets.QApplication.instance()
    if app is None or app.property(DONE_PROPERTY):
        return None
    guard = _ExitGuard(app)
    app.installEventFilter(guard)
    # The cache runs its timer only while it holds something, and the guard
    # needs one timer event to reach the cache object.
    QtGui.QPixmapCache.insert("rizum-exit-guard", QtGui.QPixmap(1, 1))
    return guard


def remove(guard, done=False):
    """Stop a guard that is still waiting, for example when its plugin closes."""
    app = QtWidgets.QApplication.instance()
    if guard is None or app is None:
        return
    if done:
        app.setProperty(DONE_PROPERTY, True)
    try:
        app.removeEventFilter(guard)
        guard.deleteLater()
    except RuntimeError:
        # Already deleted with the application.
        pass
