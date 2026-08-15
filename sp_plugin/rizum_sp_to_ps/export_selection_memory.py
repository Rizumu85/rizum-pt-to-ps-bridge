"""Per-project persistence for Painter export channel choices."""

from __future__ import annotations

import hashlib
import json


SETTINGS_KEY_PREFIX = "export/channelSelections"


def current_project_identity():
    """Return the stable identity of the open Painter project, when available."""
    try:
        import substance_painter.project as project

        value = getattr(project, "get_uuid", None)
        uuid = value() if callable(value) else value
    except Exception:
        return None
    return f"uuid:{uuid}" if uuid is not None else None


def target_selection_key(target):
    """Build a collision-free key for one texture-set stack."""
    return json.dumps(
        [target.get("texture_set") or "", target.get("stack") or ""],
        ensure_ascii=True,
        separators=(",", ":"),
    )


class ExportSelectionMemory:
    """Store channel checkbox state without coupling it to dialog widgets."""

    def __init__(self, QtCore, organization, application, project_identity):
        self._QtCore = QtCore
        self._organization = organization
        self._application = application
        self._settings_key = None
        self._targets = {}
        if project_identity:
            digest = hashlib.sha256(project_identity.encode("utf-8")).hexdigest()
            self._settings_key = f"{SETTINGS_KEY_PREFIX}/{digest}"
            self._load()

    def checked(self, target_key, channel, default):
        target = self._targets.get(target_key)
        if target is None or channel not in target:
            return bool(default)
        return bool(target[channel])

    def remember_target(self, target_key, channel_states):
        self._targets[target_key] = {
            str(channel): bool(checked)
            for channel, checked in channel_states.items()
        }

    def save(self):
        if self._settings_key is None:
            return
        store = self._QtCore.QSettings(self._organization, self._application)
        store.setValue(
            self._settings_key,
            json.dumps(self._targets, ensure_ascii=True, separators=(",", ":")),
        )
        store.sync()

    def _load(self):
        store = self._QtCore.QSettings(self._organization, self._application)
        raw = store.value(self._settings_key, "", str) or ""
        try:
            payload = json.loads(raw) if raw else {}
        except (TypeError, ValueError):
            payload = {}
        if not isinstance(payload, dict):
            return
        self._targets = {
            str(target_key): {
                str(channel): bool(checked)
                for channel, checked in channel_states.items()
            }
            for target_key, channel_states in payload.items()
            if isinstance(channel_states, dict)
        }
