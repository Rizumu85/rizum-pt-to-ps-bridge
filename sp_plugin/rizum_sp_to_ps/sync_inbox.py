"""Painter sync-inbox discovery for Photoshop-to-Painter pushes."""

from __future__ import annotations

import json
from pathlib import Path

INBOX_DIR_NAME = "_pt_sync_inbox"
MANIFEST_FILENAME = "manifest.json"
SCHEMA_VERSION = 1


def scan_current_project_inbox():
    """Scan the current Painter project's sync inbox without mutating the project."""
    project_path = _current_project_path()
    return scan_project_inbox(project_path)


def scan_project_inbox(project_path):
    """Return a summary of push manifests next to a Painter project file."""
    project_file = Path(project_path)
    inbox_path = project_file.parent / INBOX_DIR_NAME
    manifests = []

    if inbox_path.exists():
        for manifest_path in sorted(inbox_path.glob(f"*/{MANIFEST_FILENAME}")):
            manifests.append(read_push_manifest(manifest_path))

    return {
        "project_path": str(project_file),
        "inbox_path": str(inbox_path),
        "exists": inbox_path.exists(),
        "manifest_count": len(manifests),
        "manifests": manifests,
    }


def apply_latest_push_manifest():
    """Apply the newest valid push manifest to the open Painter project."""
    scan = scan_current_project_inbox()
    candidates = [manifest for manifest in scan["manifests"] if manifest["valid"]]
    if not candidates:
        return {
            "applied": False,
            "reason": "No valid pending Photoshop push manifest was found.",
            "scan": scan,
            "imports": [],
            "updates": [],
            "errors": [],
        }

    manifest = sorted(candidates, key=_manifest_sort_key)[-1]
    result = apply_push_manifest(manifest["path"])
    result["scan"] = scan
    return result


def apply_push_manifest(manifest_path):
    """Validate one push manifest without mutating the Painter project."""
    manifest = read_push_manifest(manifest_path)
    if not manifest["valid"]:
        return {
            "applied": False,
            "reason": "Manifest is not valid.",
            "manifest": manifest,
            "imports": [],
            "updates": [],
            "errors": manifest["errors"] + manifest["png_missing"],
        }

    return {
        "applied": False,
        "reason": (
            "Painter apply is disabled after host validation showed that "
            "resource import can stall or crash Painter. Manifest was validated only."
        ),
        "manifest": manifest,
        "applied_manifest_path": None,
        "imports": [],
        "updates": [],
        "pending": manifest["layers"],
        "errors": [],
    }


def read_push_manifest(manifest_path):
    """Read and validate one push manifest enough for a safe preview."""
    path = Path(manifest_path)
    errors = []
    data = None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Could not read manifest: {exc}")
        data = {}

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append("Unsupported manifest schema_version.")
    if data.get("request_type") != "push":
        errors.append("Manifest request_type is not 'push'.")

    layers = data.get("layers")
    if not isinstance(layers, list):
        errors.append("Manifest layers must be a list.")
        layers = []

    png_missing = []
    png_present = []
    manifest_dir = path.parent
    for layer in layers:
        png_path = layer.get("png") if isinstance(layer, dict) else None
        if not png_path:
            png_missing.append("<missing png field>")
            continue
        resolved = manifest_dir / png_path
        if resolved.exists():
            png_present.append(str(resolved))
        else:
            png_missing.append(str(resolved))

    return {
        "path": str(path),
        "folder": str(path.parent),
        "valid": not errors and not png_missing,
        "errors": errors,
        "created_at": data.get("created_at"),
        "rizum_version": data.get("rizum_version"),
        "psd_file": data.get("psd_file"),
        "texture_set": data.get("texture_set"),
        "stack": data.get("stack") or "(default)",
        "channel": data.get("channel"),
        "udim": _display_udim(data),
        "layer_count": len(layers),
        "png_present_count": len(png_present),
        "png_missing_count": len(png_missing),
        "png_missing": png_missing,
        "layers": [
            _layer_summary(layer) for layer in layers if isinstance(layer, dict)
        ],
    }


def format_scan_summary(scan):
    """Format a copy-friendly inbox scan report for the Painter panel."""
    lines = [
        "Painter sync inbox scan.",
        "",
        f"Project: {scan['project_path']}",
        f"Inbox: {scan['inbox_path']}",
        f"Inbox exists: {'yes' if scan['exists'] else 'no'}",
        f"Manifest count: {scan['manifest_count']}",
    ]

    if not scan["exists"]:
        lines.append("")
        lines.append("No Photoshop push inbox exists for this project yet.")
        return "\n".join(lines)

    if not scan["manifests"]:
        lines.append("")
        lines.append("No pending Photoshop push manifests were found.")
        return "\n".join(lines)

    for index, manifest in enumerate(scan["manifests"], start=1):
        lines.extend(
            [
                "",
                f"[{index}] {'valid' if manifest['valid'] else 'needs attention'}",
                f"Folder: {manifest['folder']}",
                f"Created: {manifest['created_at'] or '(unknown)'}",
                f"Rizum version: {manifest['rizum_version'] or '(unknown)'}",
                f"PSD: {manifest['psd_file'] or '(unknown)'}",
                f"Texture set: {manifest['texture_set'] or '(unknown)'}",
                f"Stack: {manifest['stack']}",
                f"Channel: {manifest['channel'] or '(unknown)'}",
                f"UDIM: {manifest['udim']}",
                f"Layers to update: {manifest['layer_count']}",
                f"PNG files present: {manifest['png_present_count']}",
                f"PNG files missing: {manifest['png_missing_count']}",
            ]
        )
        if manifest["errors"]:
            lines.append("Errors:")
            lines.extend(f"- {error}" for error in manifest["errors"])
        if manifest["png_missing"]:
            lines.append("Missing PNGs:")
            lines.extend(f"- {path}" for path in manifest["png_missing"])
        if manifest["layers"]:
            lines.append("Layer updates:")
            lines.extend(f"- {layer}" for layer in manifest["layers"])

    return "\n".join(lines)


def format_apply_summary(result):
    """Format a copy-friendly apply report for the Painter panel."""
    lines = [
        "Painter sync inbox apply.",
        "",
        f"Applied: {'yes' if result['applied'] else 'no'}",
        f"Status: {result['reason']}",
    ]
    manifest = result.get("manifest")
    if manifest:
        lines.extend(
            [
                f"Manifest: {manifest.get('path')}",
                f"Texture set: {manifest.get('texture_set') or '(unknown)'}",
                f"Stack: {manifest.get('stack') or '(default)'}",
                f"Channel: {manifest.get('channel') or '(unknown)'}",
                f"UDIM: {manifest.get('udim') or '(unknown)'}",
            ]
        )
    if result.get("applied_manifest_path"):
        lines.append(f"Applied manifest: {result['applied_manifest_path']}")
    lines.extend(
        [
            f"Resources imported: {len(result.get('imports', []))}",
            f"Layer updates inserted: {len(result.get('updates', []))}",
        ]
    )
    if result.get("pending"):
        lines.append(f"Pending layer updates: {len(result['pending'])}")
    if result.get("imports"):
        lines.append("")
        lines.append("Imported resources:")
        lines.extend(f"- {item}" for item in result["imports"])
    if result.get("updates"):
        lines.append("")
        lines.append("Layer updates:")
        lines.extend(f"- {item}" for item in result["updates"])
    if result.get("pending"):
        lines.append("")
        lines.append("Pending layer updates:")
        lines.extend(f"- {item}" for item in result["pending"])
    if result.get("errors"):
        lines.append("")
        lines.append("Errors:")
        lines.extend(f"- {error}" for error in result["errors"])
    return "\n".join(lines)


def start_watching(_project_path):
    """Start watching the project's _pt_sync_inbox folder."""
    raise NotImplementedError("Automatic inbox watching is not implemented yet.")


def _current_project_path():
    try:
        import substance_painter.project as project
    except ImportError as exc:
        raise RuntimeError("Sync inbox scanning must run inside Painter.") from exc

    if not project.is_open():
        raise RuntimeError("Open a Painter project before scanning the sync inbox.")

    path = project.file_path()
    if not path:
        raise RuntimeError("Save the Painter project before scanning the sync inbox.")
    return path


def _manifest_sort_key(manifest):
    return manifest.get("created_at") or manifest.get("folder") or manifest.get("path")


def _display_udim(data):
    if data.get("uses_udim") is False:
        return "(none)"
    return data.get("udim") or "(unknown)"


def _layer_summary(layer):
    display = layer.get("display_name") or layer.get("ps_name") or "(unnamed)"
    uid = layer.get("sp_uid") or layer.get("uid") or "(missing uid)"
    mode = layer.get("mode") or "update"
    png = layer.get("png") or "(missing png)"
    return f"{display} [rz:{uid}] {mode} -> {png}"
