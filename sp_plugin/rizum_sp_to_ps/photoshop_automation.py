"""Generate a Photoshop-executable build script for a Painter export list."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

LAUNCHER_FILENAME = "_build_in_photoshop.jsx"
_EXPORT_LIST_TOKEN = "__RIZUM_EXPORT_LIST_PATH__"
TRANSFER_LAUNCHER_FILENAME = "_transfer_to_photoshop.jsx"
_TRANSFER_REQUEST_TOKEN = "__RIZUM_TRANSFER_REQUEST_PATH__"
DOCUMENT_LAUNCHER_FILENAME = "_export_photoshop_document.jsx"
DOCUMENT_REQUEST_FILENAME = "photoshop_document_request.json"
DOCUMENT_RESULT_FILENAME = "photoshop_document_result.json"
DOCUMENT_MANIFEST_FILENAME = "photoshop_selection.json"
_DOCUMENT_REQUEST_TOKEN = "__RIZUM_DOCUMENT_REQUEST_PATH__"


@dataclass(frozen=True)
class PhotoshopDocumentLaunch:
    launcher_path: Path
    request_path: Path
    result_path: Path
    manifest_path: Path


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

    script = template.replace(
        _TRANSFER_REQUEST_TOKEN,
        json.dumps(str(request), ensure_ascii=True),
    )
    launcher_path = request.parent / TRANSFER_LAUNCHER_FILENAME
    launcher_path.write_text(script, encoding="utf-8")
    return launcher_path


def write_photoshop_document_launcher(psd_path, output_dir):
    """Prepare a Photoshop-owned full-document manifest export."""
    source = Path(psd_path).resolve()
    if source.suffix.lower() not in {".psd", ".psb"}:
        raise ValueError(f"Expected a Photoshop document, got: {source}")
    if not source.is_file():
        raise FileNotFoundError(f"Photoshop document does not exist: {source}")

    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    request_path = destination / DOCUMENT_REQUEST_FILENAME
    result_path = destination / DOCUMENT_RESULT_FILENAME
    manifest_path = destination / DOCUMENT_MANIFEST_FILENAME
    result_path.unlink(missing_ok=True)
    manifest_path.unlink(missing_ok=True)

    request_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "request_type": "photoshop_document_export",
                "psd_file": str(source),
                "output_dir": str(destination),
                "manifest_file": str(manifest_path),
                "result_file": str(result_path),
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    template_path = Path(__file__).with_name("photoshop_document.jsx")
    template = template_path.read_text(encoding="utf-8")
    if template.count(_DOCUMENT_REQUEST_TOKEN) != 1:
        raise RuntimeError("Photoshop document template has an invalid request token")
    script = template.replace(
        _DOCUMENT_REQUEST_TOKEN,
        json.dumps(str(request_path), ensure_ascii=True),
    )
    launcher_path = destination / DOCUMENT_LAUNCHER_FILENAME
    launcher_path.write_text(script, encoding="utf-8")
    return PhotoshopDocumentLaunch(
        launcher_path=launcher_path,
        request_path=request_path,
        result_path=result_path,
        manifest_path=manifest_path,
    )
