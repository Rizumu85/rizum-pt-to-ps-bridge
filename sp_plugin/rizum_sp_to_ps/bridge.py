"""Painter JS bridge wrappers for map export gaps."""

from __future__ import annotations

import json
from pathlib import Path

CHANNEL_IDENTIFIERS = {
    "BaseColor": "basecolor",
    "Height": "height",
    "Specular": "specular",
    "SpecularEdgeColor": "specularedgecolor",
    "Opacity": "opacity",
    "Emissive": "emissive",
    "Displacement": "displacement",
    "Glossiness": "glossiness",
    "Roughness": "roughness",
    "Anisotropylevel": "anisotropylevel",
    "Anisotropyangle": "anisotropyangle",
    "Transmissive": "transmissive",
    "Reflection": "reflection",
    "Ior": "ior",
    "Metallic": "metallic",
    "Normal": "normal",
    "AO": "ao",
    "Diffuse": "diffuse",
    "Specularlevel": "specularlevel",
    "BlendingMask": "blendingmask",
    "Translucency": "translucency",
    "Scattering": "scattering",
    "ScatterColor": "scattercolor",
    "SheenOpacity": "sheenopacity",
    "SheenRoughness": "sheenroughness",
    "SheenColor": "sheencolor",
    "CoatOpacity": "coatopacity",
    "CoatColor": "coatcolor",
    "CoatRoughness": "coatroughness",
    "CoatSpecularLevel": "coatspecularlevel",
    "CoatNormal": "coatnormal",
}


def export_project_path():
    """Return Painter's project-level export path via the JS API."""
    return _evaluate_json("alg.mapexport.exportPath()")


def export_layer_png(
    uid,
    channel,
    out_path,
    *,
    padding="Infinite",
    dilation=0,
    resolution=None,
    bit_depth=8,
    keep_alpha=False,
):
    """Export one Painter layer/effect/mask contribution to a PNG file."""
    script = build_mapexport_save_script(
        uid,
        channel,
        out_path,
        padding=padding,
        dilation=dilation,
        resolution=resolution,
        bit_depth=bit_depth,
        keep_alpha=keep_alpha,
    )
    return _evaluate_json(script)


def channel_identifier(channel_name):
    """Return the legacy JS mapexport channel identifier for a Python name."""
    if channel_name is None:
        return None
    if str(channel_name).lower() == "mask":
        return "mask"
    return CHANNEL_IDENTIFIERS.get(str(channel_name), str(channel_name).lower())


def build_mapexport_save_script(
    uid,
    channel,
    out_path,
    *,
    padding="Infinite",
    dilation=0,
    resolution=None,
    bit_depth=8,
    keep_alpha=False,
):
    """Build the JS source for `alg.mapexport.save` without executing it."""
    target = [int(uid), channel_identifier(channel)] if channel else [int(uid)]
    options = {
        "padding": padding,
        "dilation": int(dilation),
        "bitDepth": int(bit_depth),
        "keepAlpha": bool(keep_alpha),
    }
    if resolution is not None:
        options["resolution"] = [int(resolution[0]), int(resolution[1])]

    path_text = str(Path(out_path))
    return (
        f"alg.mapexport.save({json.dumps(target)}, "
        f"{json.dumps(path_text)}, {json.dumps(options, sort_keys=True)})"
    )


def _evaluate_json(script):
    try:
        import substance_painter.js as painter_js
    except ImportError as exc:
        raise RuntimeError("Painter JS bridge is only available inside Painter.") from exc

    result = painter_js.evaluate(script)
    if result in (None, ""):
        return None
    try:
        return json.loads(result)
    except (TypeError, json.JSONDecodeError):
        return result
