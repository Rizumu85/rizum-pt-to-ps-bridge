"""Generate a Photoshop-executable build script for a Painter export list."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

LAUNCHER_FILENAME = "_build_in_photoshop.jsx"
_EXPORT_LIST_TOKEN = "__RIZUM_EXPORT_LIST_PATH__"
TRANSFER_LAUNCHER_FILENAME = "_transfer_to_photoshop.jsx"
TRANSFER_RESULT_FILENAME = "photoshop_transfer_result.json"
TRANSFER_PROGRESS_FILENAME = "photoshop_transfer_progress.json"
_TRANSFER_REQUEST_TOKEN = "__RIZUM_TRANSFER_REQUEST_PATH__"
_JSON_RUNTIME_TOKEN = "__RIZUM_JSON_RUNTIME__"


@dataclass(frozen=True)
class PhotoshopScriptLaunch:
    launcher_path: Path
    request_path: Path
    result_path: Path
    progress_path: Path


def _embed_json_runtime(template):
    if template.count(_JSON_RUNTIME_TOKEN) != 1:
        raise RuntimeError("Photoshop template has an invalid JSON runtime token")
    # A fresh ExtendScript engine has no JSON. Scope our codec to this script so
    # transfer receipts never depend on another installed extension.
    # Unmodified public-domain JSON-js, commit 7e83f38a2312429fd4933169c1f6a27fd65e889c:
    # https://github.com/douglascrockford/JSON-js/blob/7e83f38a2312429fd4933169c1f6a27fd65e889c/json2.js
    codec = (Path(__file__).parent / "vendor" / "json2.js").read_text(encoding="utf-8")
    return template.replace(_JSON_RUNTIME_TOKEN, "var JSON = {};\n" + codec)


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


def write_photoshop_transfer_launcher(request_path):
    """Write the JSX entry point for mapped Painter-to-Photoshop inserts."""
    request = Path(request_path).resolve()
    template_path = Path(__file__).with_name("photoshop_transfer.jsx")
    template = template_path.read_text(encoding="utf-8")
    if template.count(_TRANSFER_REQUEST_TOKEN) != 1:
        raise RuntimeError("Photoshop transfer template has an invalid request token")

    script = _embed_json_runtime(template).replace(
        _TRANSFER_REQUEST_TOKEN,
        json.dumps(str(request), ensure_ascii=True),
    )
    launcher_path = request.parent / TRANSFER_LAUNCHER_FILENAME
    result_path = request.parent / TRANSFER_RESULT_FILENAME
    progress_path = request.parent / TRANSFER_PROGRESS_FILENAME
    result_path.unlink(missing_ok=True)
    progress_path.unlink(missing_ok=True)
    launcher_path.write_text(script, encoding="utf-8")
    return PhotoshopScriptLaunch(launcher_path, request, result_path, progress_path)
