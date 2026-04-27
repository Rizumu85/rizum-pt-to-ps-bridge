"""Importable Painter module for Rizum PT-to-PS Bridge local development."""

import sys
from pathlib import Path

_PLUGIN_ROOT = str(Path(__file__).resolve().parent)
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

from sp_plugin.rizum_sp_to_ps import close_plugin, start_plugin  # noqa: E402


if __name__ == "__main__":
    start_plugin()
