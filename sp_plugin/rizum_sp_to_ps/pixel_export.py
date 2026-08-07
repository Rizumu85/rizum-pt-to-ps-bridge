"""Rendered pixel export adapter for Painter's legacy JS map exporter."""

from __future__ import annotations

from . import bridge


def export_layer_png(asset, export_settings, channel_candidates):
    """Export one layer and report whether every successful result was transparent."""
    wrote_transparent = False
    errors = []
    for channel in channel_candidates:
        try:
            bridge.export_layer_png_raw(
                asset["uid"],
                channel,
                asset["path"],
                padding=export_settings["padding"],
                dilation=export_settings["dilation"],
                resolution=export_settings["resolution"],
                bit_depth=export_settings["bit_depth"],
                keep_alpha=export_settings["keep_alpha"],
            )
        except Exception as exc:  # noqa: BLE001 - alternate IDs are intentional.
            errors.append(f"{channel}: {type(exc).__name__}: {exc}")
            continue

        if not png_is_fully_transparent(asset["path"]):
            return False
        wrote_transparent = True

    if wrote_transparent:
        return True
    if errors:
        raise RuntimeError("; ".join(errors))
    return False


def export_mask_png(asset, export_settings):
    """Export one lossless rendered layer or folder mask."""
    try:
        bridge.export_mask_png(
            asset["uid"],
            asset["path"],
            padding=export_settings["padding"],
            dilation=export_settings["dilation"],
            resolution=export_settings["resolution"],
            bit_depth=export_settings["bit_depth"],
            keep_alpha=export_settings["keep_alpha"],
        )
    except Exception as exc:
        # Alpha reconstruction is deliberately not a fallback: it loses folder
        # masks and grayscale values, which silently changes the authored result.
        label = asset.get("label") or asset.get("uid_hex") or asset["uid"]
        raise RuntimeError(
            "Painter could not export the rendered mask for "
            f"{label}. Painter 12.1.2 or newer is required. Host error: {exc}"
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
