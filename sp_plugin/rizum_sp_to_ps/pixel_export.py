"""Rendered pixel export adapter for Painter layer-stack nodes."""

from __future__ import annotations

def export_layer_png(
    asset,
    export_settings,
    channel_name,
    uv_tile,
    node_exporter,
):
    """Export one layer tile and report whether its payload is transparent."""
    node_exporter.export_layer(
        asset,
        export_settings,
        channel_name,
        uv_tile,
    )
    return png_is_fully_transparent(asset["path"])


def export_mask_png(asset, export_settings, uv_tile, node_exporter):
    """Export one lossless rendered layer or folder mask."""
    try:
        node_exporter.export_mask(asset, export_settings, uv_tile)
    except Exception as exc:
        label = asset.get("label") or asset.get("uid_hex") or asset["uid"]
        raise RuntimeError(
            "Painter could not export the rendered mask for "
            f"{label}. Host error: {exc}"
        ) from exc


def png_is_fully_transparent(path):
    """Return whether a readable alpha-bearing PNG contains no visible pixels."""
    try:
        from PySide6 import QtGui
    except Exception:
        return False

    image = QtGui.QImage(str(path))
    if image.isNull() or not image.hasAlphaChannel():
        return False

    rgba_format = getattr(QtGui.QImage, "Format_RGBA8888", None)
    if rgba_format is None:
        rgba_format = QtGui.QImage.Format.Format_RGBA8888
    rgba = image.convertToFormat(rgba_format)
    data = rgba.constBits()
    if hasattr(data, "tobytes"):
        raw = data.tobytes()
    else:
        data.setsize(rgba.sizeInBytes())
        raw = bytes(data)
    return not any(raw[index] for index in range(3, len(raw), 4))
