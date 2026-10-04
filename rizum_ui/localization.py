"""Painter-language detection and catalog lookup shared by Rizum plugins.

Only the mechanism lives here. Each plugin keeps its own English fallback
texts and ``i18n/*.json`` catalogs and binds these functions to them.
"""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_LANGUAGE = "en"
PAINTER_SETTINGS = ("Adobe", "Adobe Substance 3D Painter")
LANGUAGE_SETTING = "General/UI_LANGUAGE"


def normalize_language(language) -> str:
    return str(language or "").strip().lower().replace("-", "_")


def load_catalogs(directory, fallback_text) -> dict[str, dict[str, str]]:
    catalogs = {DEFAULT_LANGUAGE: dict(fallback_text)}
    directory = Path(directory)
    if not directory.exists():
        return catalogs

    for path in sorted(directory.glob("*.json")):
        language = normalize_language(path.stem)
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        catalogs[language] = {
            str(key): str(value)
            for key, value in data.items()
        }
        root = language.split("_", 1)[0]
        catalogs.setdefault(root, catalogs[language])
    return catalogs


def resolve_language(catalogs, *candidates) -> str:
    for candidate in candidates:
        language = normalize_language(candidate)
        if not language:
            continue
        if language in catalogs:
            return language
        root = language.split("_", 1)[0]
        if root in catalogs:
            return root
    return DEFAULT_LANGUAGE


# Both readers import Qt when called, not at import time: checks that run
# without PySide6 (Liquify's CI) load plugin localization modules with a stub.
def read_painter_language() -> str:
    """The language chosen in Painter's Language preference.

    Painter's log names a locale too, but only after the plugins have
    started, so reading the log left every plugin in English on a freshly
    started non-English Painter.
    """
    try:
        from PySide6 import QtCore
    except ImportError:
        return ""

    return str(QtCore.QSettings(*PAINTER_SETTINGS).value(LANGUAGE_SETTING, "") or "")


def read_system_language() -> str:
    """The second candidate after Painter's Language preference.

    The preference starts as "Default (System Language)", which names no
    language and makes Painter follow the system locale. A fresh install is
    in that state.
    """
    try:
        from PySide6 import QtCore
    except ImportError:
        return ""

    return QtCore.QLocale.system().name()


def format_text(catalogs, language, key, values) -> str:
    catalog = catalogs.get(language, catalogs[DEFAULT_LANGUAGE])
    template = catalog.get(key, catalogs[DEFAULT_LANGUAGE].get(key, key))
    try:
        return template.format(**values)
    except (KeyError, ValueError):
        return template


def supported_languages(catalogs) -> tuple[str, ...]:
    return tuple(
        sorted(
            language
            for language in catalogs
            if "_" not in language
        )
    )
