"""Make an sRGB PSD look like Painter at hand-off (design.md §4).

Painter blends in linear space and Photoshop in sRGB, so the same layers,
modes, and opacities give a different picture. Every layer's backdrop is known
when an export is built, so each layer can be rewritten to reproduce its
Painter look under Photoshop's rules. The per-pixel work runs in the native
library (``native/painter_look.rs``); this module plans it from a build
request and applies the result to the request's layer records.
"""

from __future__ import annotations

import ctypes
import os
import tempfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from . import png_color_metadata

MATCH_PAINTER = "match_painter"
KEEP_BLEND_MODES = "keep_blend_modes"
DEFAULT_BLEND_MODES = MATCH_PAINTER

# Painter modes the native compositor models, by Painter's member name.
MODELLED_MODES = {
    "Normal", "Multiply", "Screen", "Overlay", "SoftLight", "HardLight",
    "Darken", "Lighten", "LinearDodge", "LinearBurn", "ColorBurn",
    "ColorDodge", "VividLight", "LinearLight", "SignedAddition", "PinLight",
    "Difference", "Exclusion", "Subtract", "Divide", "InverseDivide",
    "InverseSubtract", "Tint", "Saturation", "Color", "Value",
}
# Photoshop has no mode with these formulas (analysis.md §6.2).
NO_PHOTOSHOP_FORMULA = {
    "SoftLight", "Tint", "Saturation", "Color", "Value", "InverseDivide",
    "InverseSubtract",
}
# Rewritten from coverage alone, so later edits below stay correct.
BACKDROP_FREE = {"Multiply": ("multiply", "MULTIPLY"), "Divide": ("divide", "DIVIDE")}
# Solved as Normal pixels that never cross the backdrop the wrong way, so the
# layer keeps its mode.
SOLVED_KEEPING_MODE = {"Darken": "DARKEN", "Lighten": "LIGHTEN"}

# The normal channel blends with normal-map modes and is renormalized; it
# keeps today's export.
SKIPPED_CHANNELS = {"normal"}
# A pixel counts as not reproduced when the solve had to clip it.
CLIPPED_WARNING_SHARE = 0.001


def matches_painter(settings):
    return (settings or {}).get("blend_modes", DEFAULT_BLEND_MODES) != KEEP_BLEND_MODES


@dataclass
class _Leaf:
    node: dict
    emit: str
    photoshop_mode: str | None
    line: int
    content_raw: str = ""
    mask_raw: str | None = None
    out_content_raw: str | None = None
    out_mask_raw: str | None = None


@dataclass
class _Plan:
    lines: list = field(default_factory=list)
    leaves: list = field(default_factory=list)
    groups: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    inputs: list = field(default_factory=list)  # (png path, raw path, kind)


def rewrite_request(build_request, settings, work_dir=None):
    """Rewrite a build request's payloads in place; returns a summary.

    Runs after every payload is at the PSD's size (after smoothing and
    resampling), because the solve is exact only for the pixels Photoshop
    will actually read.
    """
    channel = str(build_request.get("channel") or "")
    if channel.casefold() in SKIPPED_CHANNELS:
        return {"mode": "skipped", "reason": f"{channel} channel"}
    match = matches_painter(settings)
    srgb = build_request["color_management"]["encoding"] == "srgb"
    width, height = build_request["export_settings"]["output_resolution"]

    with tempfile.TemporaryDirectory(prefix="rizum_painter_look_", dir=work_dir) as scratch:
        plan = _plan(build_request["layers"], channel, match, Path(scratch))
        emitting = [leaf for leaf in plan.leaves if leaf.emit != "none"]
        if not emitting:
            return {"mode": _mode_name(match), "rewritten_layers": 0, "warnings": plan.warnings}
        formats = {}
        for png, raw, kind in plan.inputs:
            formats[png] = _write_raw(png, raw, kind, (width, height))
        header = f"P\t{width}\t{height}\t{'srgb' if srgb else 'raw'}"
        program = "\n".join([header, *_resolve_lines(plan, formats)]) + "\n"
        clipped = _run_native(program, len(plan.lines))

        encoding = "srgb" if srgb else "raw"
        for leaf in emitting:
            content_png = leaf.node["asset"]["path"]
            _read_raw(leaf.out_content_raw, content_png, formats[content_png], (width, height))
            png_color_metadata.normalize_png(content_png, encoding)
            if leaf.out_mask_raw:
                mask_png = leaf.node["mask_asset"]["path"]
                _read_raw(leaf.out_mask_raw, mask_png, formats[mask_png], (width, height))
                png_color_metadata.normalize_png(mask_png, "raw")
            count = clipped[leaf.line]
            if count > CLIPPED_WARNING_SHARE * width * height:
                plan.warnings.append(
                    f"{leaf.node.get('name')}: {count} pixels could not match Painter exactly."
                )
    _apply_structure(plan, channel, match)
    return {
        "mode": _mode_name(match),
        "rewritten_layers": len(emitting),
        "warnings": plan.warnings,
    }


def _mode_name(match):
    return MATCH_PAINTER if match else KEEP_BLEND_MODES


def _plan(nodes, channel, match, scratch):
    plan = _Plan()
    _walk(nodes, channel, match, scratch, plan, ancestors_pass=())
    return plan


def _painter_mode(node, channel):
    modes = node.get("blend_mode") or {}
    return str(modes.get(channel) or "Normal")


def _opacity(node, channel):
    opacities = node.get("opacity") or {}
    value = opacities.get(channel)
    return 1.0 if value is None else float(value)


def _modelled(name, node, plan):
    if name in MODELLED_MODES:
        return name
    plan.warnings.append(f"{node.get('name')}: Painter's {name} blending is shown as Normal.")
    return "Normal"


def _walk(nodes, channel, match, scratch, plan, ancestors_pass):
    # Build requests list layers top first; Painter composites bottom up.
    for node in reversed(nodes):
        if node.get("visible") is False:
            continue
        mode = _painter_mode(node, channel)
        if mode == "Disable":
            continue
        if node.get("children") and not node.get("asset"):
            passthrough = mode == "Passthrough"
            group_mode = "Normal" if passthrough else _modelled(mode, node, plan)
            mask = (node.get("mask_asset") or {}).get("path")
            mask_raw = _input(plan, scratch, mask, "mask") if mask else None
            plan.lines.append(("B", passthrough, group_mode, _opacity(node, channel), mask_raw))
            plan.groups.append(node)
            _walk(node["children"], channel, match, scratch, plan, (*ancestors_pass, passthrough))
            plan.lines.append(("E",))
            continue
        asset = node.get("asset")
        if not asset:
            continue
        painter_mode = _modelled(mode, node, plan)
        emit, photoshop_mode = _emission(painter_mode, match, all(ancestors_pass))
        leaf = _Leaf(node, emit, photoshop_mode, line=len(plan.lines))
        leaf.content_raw = _input(plan, scratch, asset["path"], "content")
        mask = (node.get("mask_asset") or {}).get("path")
        if mask:
            leaf.mask_raw = _input(plan, scratch, mask, "mask")
        if emit != "none":
            leaf.out_content_raw = str(scratch / f"out_{leaf.line}.raw")
            if emit == "solve" and mask:
                leaf.out_mask_raw = str(scratch / f"out_{leaf.line}_mask.raw")
        plan.lines.append(("L", painter_mode, _opacity(node, channel), leaf, match))
        plan.leaves.append(leaf)


def _emission(painter_mode, match, all_ancestors_pass):
    """How a leaf is written, and the Photoshop mode it ends up with.

    A Photoshop mode survives only where it can still reproduce Painter:
    outside isolated groups, whose children Painter blends against a
    transparent backdrop that a Pass Through folder no longer gives them.
    """
    if match:
        if all_ancestors_pass and painter_mode in BACKDROP_FREE:
            return BACKDROP_FREE[painter_mode]
        if all_ancestors_pass and painter_mode in SOLVED_KEEPING_MODE:
            return "solve", SOLVED_KEEPING_MODE[painter_mode]
        return "solve", "NORMAL"
    if not all_ancestors_pass:
        return "none", None
    if painter_mode in BACKDROP_FREE:
        return BACKDROP_FREE[painter_mode][0], None
    if painter_mode in ("Normal", *SOLVED_KEEPING_MODE):
        return "color", None
    if painter_mode in NO_PHOTOSHOP_FORMULA:
        return "color", "NORMAL"
    return "none", None


def _input(plan, scratch, png, kind):
    raw = str(scratch / f"in_{len(plan.inputs)}.raw")
    plan.inputs.append((png, raw, kind))
    return raw


def _raw_fields(raw, formats, png):
    if raw is None:
        return ["-", "-", "-"]
    depth, stride = formats[png]
    return [raw, str(depth), str(stride)]


def _resolve_lines(plan, formats):
    png_of = {raw: png for png, raw, _kind in plan.inputs}
    for line in plan.lines:
        if line[0] == "E":
            yield "E"
        elif line[0] == "B":
            _tag, passthrough, mode, opacity, mask_raw = line
            mask_fields = _raw_fields(mask_raw, formats, png_of.get(mask_raw))
            yield "\t".join(["B", "1" if passthrough else "0", mode, f"{opacity:.6f}", *mask_fields])
        else:
            _tag, mode, opacity, leaf, match = line
            content = _raw_fields(leaf.content_raw, formats, png_of[leaf.content_raw])
            mask = _raw_fields(leaf.mask_raw, formats, png_of.get(leaf.mask_raw))
            yield "\t".join([
                "L", mode, f"{opacity:.6f}", "1", leaf.emit, "1" if match else "0",
                *content, *mask, leaf.out_content_raw or "-", leaf.out_mask_raw or "-",
            ])


def _apply_structure(plan, channel, match):
    for leaf in plan.leaves:
        if leaf.emit == "none":
            continue
        node = leaf.node
        if leaf.photoshop_mode:
            _set_photoshop_mode(node, channel, leaf.photoshop_mode)
        if match:
            # Opacity now lives in the pixel alpha (the user's choice over
            # folding it into the mask, design.md §4.2).
            node.setdefault("opacity", {})[channel] = 1.0
    if not match:
        return
    for group in plan.groups:
        # Photoshop folders mix opacity and masks in sRGB, which cannot carry
        # a per-pixel correction; their coverage is in the children now.
        _set_photoshop_mode(group, channel, "PASSTHROUGH")
        group.setdefault("opacity", {})[channel] = 1.0
        mask = group.pop("mask_asset", None)
        if mask:
            Path(mask["path"]).unlink(missing_ok=True)


def _set_photoshop_mode(node, channel, mode):
    node["ps_blend_mode"] = mode
    decision = (node.get("blend_decisions") or {}).get(channel)
    if decision is not None:
        decision["ps_blend_mode"] = mode


# ---------------------------------------------------------------- pixels


def _qt():
    from PySide6 import QtGui

    return QtGui


def _write_raw(png, raw, kind, size):
    """Decode a payload into the native library's raw layout; returns (depth, stride)."""
    QtGui = _qt()
    formats = QtGui.QImage.Format
    image = QtGui.QImage(str(png))
    if image.isNull():
        raise RuntimeError(f"Could not read payload for Painter-look rewrite: {png}")
    if (image.width(), image.height()) != tuple(size):
        raise RuntimeError(
            f"Payload {png} is {image.width()}x{image.height()}, expected {size[0]}x{size[1]}."
        )
    is_16_bit = image.depth() > 32 or image.format() == formats.Format_Grayscale16
    if kind == "mask":
        target = formats.Format_Grayscale16 if is_16_bit else formats.Format_Grayscale8
    else:
        target = formats.Format_RGBA64 if is_16_bit else formats.Format_RGBA8888
    image = image.convertToFormat(target)
    with open(raw, "wb") as handle:
        handle.write(_image_bytes(image))
    return (16 if is_16_bit else 8), image.bytesPerLine()


def _image_bytes(image):
    data = image.constBits()
    if hasattr(data, "tobytes"):
        return data.tobytes()[: image.sizeInBytes()]
    data.setsize(image.sizeInBytes())
    return bytes(data)


def _read_raw(raw, png, source_format, size):
    """Encode a native output back over its payload PNG, keeping DPI."""
    QtGui = _qt()
    formats = QtGui.QImage.Format
    depth, _stride = source_format
    width, height = size
    is_mask = str(raw).endswith("_mask.raw")
    if is_mask:
        image_format = formats.Format_Grayscale16 if depth == 16 else formats.Format_Grayscale8
        bytes_per_line = width * depth // 8
    else:
        image_format = formats.Format_RGBA64 if depth == 16 else formats.Format_RGBA8888
        bytes_per_line = width * 4 * depth // 8
    data = Path(raw).read_bytes()
    image = QtGui.QImage(data, width, height, bytes_per_line, image_format).copy()
    source = QtGui.QImage(str(png))
    image.setDotsPerMeterX(source.dotsPerMeterX())
    image.setDotsPerMeterY(source.dotsPerMeterY())
    target = Path(png)
    temporary = target.with_name(f".{target.stem}.rizum-look-{os.getpid()}.png")
    try:
        if not image.save(str(temporary), "PNG"):
            raise RuntimeError(f"Could not write rewritten payload: {png}")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


# ---------------------------------------------------------------- native


@lru_cache(maxsize=1)
def _native_library():
    path = Path(__file__).with_name("native") / "rizum_painter_look_v1.dll"
    if not path.is_file():
        raise RuntimeError(f"Bundled Painter-look library is missing: {path}")
    library = ctypes.CDLL(str(path))
    function = library.rizum_painter_look_run
    function.argtypes = (
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.c_size_t,
        ctypes.c_char_p,
        ctypes.c_size_t,
    )
    function.restype = ctypes.c_uint64
    return library


def _run_native(program, line_count):
    """Run a program; returns the clipped-pixel count for each program line."""
    encoded = program.encode("utf-8")
    counts = (ctypes.c_uint64 * line_count)()
    error = ctypes.create_string_buffer(2048)
    status = _native_library().rizum_painter_look_run(
        encoded,
        len(encoded),
        max(1, os.cpu_count() or 1),
        counts,
        line_count,
        error,
        len(error),
    )
    if status:
        raise RuntimeError(f"Painter-look rewrite failed: {error.value.decode('utf-8', 'replace')}")
    return list(counts)
