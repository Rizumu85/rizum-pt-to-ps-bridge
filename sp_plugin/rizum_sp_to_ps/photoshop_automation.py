"""Generate a Photoshop-executable build script for a Painter export list."""

from __future__ import annotations

import json
from pathlib import Path

LAUNCHER_FILENAME = "_build_in_photoshop.jsx"
_EXPORT_LIST_TOKEN = "__RIZUM_EXPORT_LIST_PATH__"


def write_photoshop_launcher(export_list_path):
    """Write the JSX entry point Photoshop will execute after Painter export."""
    export_list = Path(export_list_path).resolve()
    template_path = Path(__file__).with_name("photoshop_build.jsx")
    template = template_path.read_text(encoding="utf-8")
    if template.count(_EXPORT_LIST_TOKEN) != 1:
        raise RuntimeError("Photoshop build template has an invalid export-list token")

    # Photoshop still accepts JSX as a process argument while UXP scripts do
    # not. Keep the path as data so the builder stays generic and inspectable.
    script = template.replace(
        _EXPORT_LIST_TOKEN,
        json.dumps(str(export_list), ensure_ascii=True),
    )
    launcher_path = export_list.parent / LAUNCHER_FILENAME
    launcher_path.write_text(script, encoding="utf-8")
    return launcher_path
