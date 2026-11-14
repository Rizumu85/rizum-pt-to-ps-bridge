"""Painter's registered keyboard shortcuts, for plugins that let the user pick one.

Qt fires neither of two enabled actions that share a shortcut, so a plugin key
that Painter already uses silently disables a Painter command. A settings
dialog marks such a key with :func:`shortcut_conflicts`.
"""

from __future__ import annotations

from typing import Iterable

from PySide6 import QtGui, QtWidgets


PORTABLE = QtGui.QKeySequence.SequenceFormat.PortableText


def canonical(text: str) -> str:
    """The portable spelling of a shortcut, so equal keys compare equal."""
    text = str(text or "").strip()
    if not text:
        return ""
    return QtGui.QKeySequence.fromString(text, PORTABLE).toString(PORTABLE)


def _action_label(action: QtGui.QAction) -> str:
    return action.text().split("\t", 1)[0].replace("&", "").strip() or action.objectName()


def registered_shortcut_index(
    main_window,
    *,
    ignore: Iterable = (),
    unknown_label: str = "Painter command",
) -> dict[str, list[str]]:
    """Map every shortcut held by an action or QShortcut to the commands using it.

    ``ignore`` holds the plugin's own actions and shortcuts. The scan reads
    wrappers that exist only for this call and keeps none of them: what a
    plugin keeps of Painter's widgets past its close crashes Painter when it
    exits (see docs/integration.md). Painter's shortcuts do not change while
    a modal settings dialog is open, so a dialog scans once.
    """
    ignored = {id(item) for item in ignore}
    app = QtWidgets.QApplication.instance()
    actions = list(main_window.findChildren(QtGui.QAction)) if main_window is not None else []
    if app is not None:
        actions.extend(app.findChildren(QtGui.QAction))
        for widget in app.allWidgets():
            try:
                actions.extend(widget.actions())
            except RuntimeError:
                continue

    index: dict[str, list[str]] = {}

    def add(sequence: QtGui.QKeySequence, label: str) -> None:
        portable = sequence.toString(PORTABLE)
        if portable:
            labels = index.setdefault(portable, [])
            if label not in labels:
                labels.append(label)

    seen = set()
    for action in actions:
        if id(action) in ignored or id(action) in seen:
            continue
        seen.add(id(action))
        try:
            sequences = action.shortcuts()
            label = _action_label(action) or unknown_label
        except (AttributeError, RuntimeError):
            continue
        for sequence in sequences:
            add(sequence, label)

    shortcuts = list(main_window.findChildren(QtGui.QShortcut)) if main_window is not None else []
    if app is not None:
        shortcuts.extend(app.findChildren(QtGui.QShortcut))
    seen.clear()
    for shortcut in shortcuts:
        if id(shortcut) in ignored or id(shortcut) in seen:
            continue
        seen.add(id(shortcut))
        try:
            add(shortcut.key(), shortcut.objectName() or unknown_label)
        except RuntimeError:
            continue
    return index


def shortcut_conflicts(shortcut: str, index: dict[str, list[str]]) -> list[str]:
    """The commands in ``index`` that already use ``shortcut``."""
    key = canonical(shortcut)
    return list(index.get(key, ())) if key else []
