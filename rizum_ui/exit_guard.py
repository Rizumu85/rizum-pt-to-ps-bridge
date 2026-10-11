"""Keep Painter from crashing when it exits.

Two crashes, both at exit, both invisible until the crash report appears.

Python event filters. PySide tags every C++ QObject it hands to Python with a dynamic property whose
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

Projects in Adobe ACE color management. Painter 12.1.2 crashes on exit when
the project open at that moment uses ACE color management, with or without
plugins (access violation in ``ACE.dll`` under
``~ToolBarSourceColorPickerView``): the swatch in the contextual toolbar
releases its ACE transform while the main window is destroyed, after Painter
has already freed it. Deleting that view when the plugins are closed for the
exit, while the transform is still valid, avoids it. The user and a friend
met the crash report on every exit and took the plugins for its cause.
"""

from __future__ import annotations

import shiboken6
from PySide6 import QtCore, QtGui, QtWidgets


PYSIDE_PROPERTY = "_PySideInvalidatePtr"
STATIC_CLASSES = frozenset({"QPMCache"})
DONE_PROPERTY = "rizumExitGuardDone"
QUITTING_PROPERTY = "rizumExitGuardQuitting"
TOOLBAR_SWATCH_CLASS = "Alg::ToolBarSourceColorPickerView"
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
    if app is None:
        return None
    if app.property(QUITTING_PROPERTY) is None:
        app.setProperty(QUITTING_PROPERTY, False)
        app.aboutToQuit.connect(_mark_quitting)
    if app.property(DONE_PROPERTY):
        return None
    guard = _ExitGuard(app)
    app.installEventFilter(guard)
    # The cache runs its timer only while it holds something, and the guard
    # needs one timer event to reach the cache object.
    QtGui.QPixmapCache.insert("rizum-exit-guard", QtGui.QPixmap(1, 1))
    return guard


def remove(guard, done=False):
    """Call when the plugin closes; also stops a guard that is still waiting."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        return
    if not done and app.property(QUITTING_PROPERTY):
        _delete_toolbar_swatch(app)
    if guard is None:
        return
    if done:
        app.setProperty(DONE_PROPERTY, True)
    try:
        app.removeEventFilter(guard)
        guard.deleteLater()
    except RuntimeError:
        # Already deleted with the application.
        pass


def _mark_quitting():
    app = QtWidgets.QApplication.instance()
    if app is not None:
        app.setProperty(QUITTING_PROPERTY, True)


def _delete_toolbar_swatch(app):
    # Only once Qt has announced the exit: a plugin is also closed when the
    # user disables or reloads it, and then Painter still uses the view.
    # Painter closes its plugins after that announcement and before it
    # destroys its windows, which is the moment measured to be safe.
    for widget in app.allWidgets():
        if widget.metaObject().className() == TOOLBAR_SWATCH_CLASS:
            shiboken6.delete(widget)
