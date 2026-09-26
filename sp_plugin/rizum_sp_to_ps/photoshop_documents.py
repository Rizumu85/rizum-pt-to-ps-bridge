"""Which Photoshop document each Painter texture set, or one of its channels, maps to."""

from __future__ import annotations

import json
from pathlib import Path


SETTINGS_KEY = "photoshop_documents"


def _texture_set_key(texture_set, stack):
    return f"{texture_set}/{stack}" if stack else str(texture_set)


def _same_file(first, second):
    try:
        return Path(first).resolve() == Path(second).resolve()
    except OSError:
        return str(first) == str(second)


class DocumentMemory:
    """
    A PSD belongs to a texture set: the first one connected there serves all
    its channels. Artists sometimes keep one PSD per channel instead, so a
    different PSD connected on a channel is kept for that channel alone, and
    connecting the texture set's own PSD again drops the channel's override.
    Keyed by project, since texture set names repeat across projects.
    """

    def __init__(self, text=""):
        try:
            store = json.loads(text) if text else {}
        except ValueError:
            store = {}
        self._store = store if isinstance(store, dict) else {}

    def dumps(self):
        return json.dumps(self._store, sort_keys=True)

    def _entry(self, project, texture_set, stack):
        texture_sets = self._store.setdefault(str(project), {})
        return texture_sets.setdefault(_texture_set_key(texture_set, stack), {})

    def remember(self, project, texture_set, stack, channel, path):
        entry = self._entry(project, texture_set, stack)
        channels = entry.setdefault("channels", {})
        default = entry.get("document")
        if not default or not Path(default).is_file():
            entry["document"] = str(path)
            channels.pop(channel, None)
        elif _same_file(default, path):
            channels.pop(channel, None)
        else:
            channels[channel] = str(path)

    def resolve(self, project, texture_set, stack, channel):
        entry = self._store.get(str(project), {}).get(_texture_set_key(texture_set, stack), {})
        for candidate in ((entry.get("channels") or {}).get(channel), entry.get("document")):
            # A moved or deleted PSD falls through instead of failing to open.
            if candidate and Path(candidate).is_file():
                return candidate
        return None
