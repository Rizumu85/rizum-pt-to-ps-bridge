"""Morphological antialiasing, like Clip Studio Paint's, for final Painter payloads."""

from __future__ import annotations

import ctypes
import os
from functools import lru_cache
from pathlib import Path

ALGORITHM_ID = "morphological-aa-v5"
# The one user setting: 0 leaves edges as Painter drew them, 100 smooths fully.
DEFAULT_STRENGTH = 100
_NATIVE_ERROR = (1 << 64) - 1


@lru_cache(maxsize=1)
def _native_library():
    path = Path(__file__).with_name("native") / "rizum_edge_smoothing_v5.dll"
    if not path.is_file():
        # Mixing filtered and unfiltered layers would make one PSD internally
        # inconsistent, so a damaged installation must stop the whole export.
        raise RuntimeError(f"Bundled edge smoothing library is missing: {path}")

    library = ctypes.CDLL(str(path))
    for name, sample_type in (
        ("rizum_smooth_rgba8", ctypes.c_uint8),
        ("rizum_smooth_rgba16", ctypes.c_uint16),
    ):
        function = getattr(library, name)
        function.argtypes = (
            ctypes.POINTER(sample_type),
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.c_float,
        )
        function.restype = ctypes.c_uint64
    return library


def smooth_image(image, strength=DEFAULT_STRENGTH):
    """Smooth a QImage; returns the smoothed copy and how many pixels changed.

    The settings preview runs this same pass, so what it shows is what the
    export writes.
    """
    from PySide6 import QtGui

    formats = QtGui.QImage.Format
    is_16_bit = image.depth() > 32 or image.format() == formats.Format_Grayscale16
    target_format = formats.Format_RGBA64 if is_16_bit else formats.Format_RGBA8888
    image = image.convertToFormat(target_format)
    bits = image.bits()
    pointer = ctypes.addressof(ctypes.c_uint8.from_buffer(bits))
    library = _native_library()
    if is_16_bit:
        function = library.rizum_smooth_rgba16
        pixels = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint16))
    else:
        function = library.rizum_smooth_rgba8
        pixels = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint8))

    changed_pixels = int(
        function(
            pixels,
            image.width(),
            image.height(),
            image.bytesPerLine(),
            max(0.0, min(1.0, float(strength) / 100.0)),
        )
    )
    if changed_pixels == _NATIVE_ERROR:
        raise RuntimeError("Invalid image buffer for edge smoothing")
    return image, changed_pixels, is_16_bit


def smooth_png(path, strength=DEFAULT_STRENGTH):
    """Rebuild jagged colour and coverage edges as smooth lines, in place."""
    try:
        from PySide6 import QtGui
    except ImportError as exc:
        raise RuntimeError("Edge smoothing requires Painter's bundled PySide6.") from exc

    source_path = Path(path)
    image = QtGui.QImage(str(source_path))
    if image.isNull():
        raise RuntimeError(
            f"Could not read exported PNG for edge smoothing: {source_path}"
        )

    try:
        image, changed_pixels, is_16_bit = smooth_image(image, strength)
    except RuntimeError as exc:
        raise RuntimeError(f"{exc}: {source_path}") from exc

    result = {
        "algorithm": ALGORITHM_ID,
        "bit_depth": 16 if is_16_bit else 8,
        "changed_pixels": changed_pixels,
    }
    if changed_pixels == 0:
        # Unchanged payloads keep Painter's original encoding and avoid a PNG
        # recompression pass, which matters when a stack contains many 4K layers.
        return result

    temporary_path = source_path.with_name(
        f".{source_path.stem}.rizum-smoothing-{os.getpid()}.png"
    )
    try:
        if not image.save(str(temporary_path), "PNG"):
            raise RuntimeError(f"Could not write smoothed PNG: {source_path}")
        os.replace(temporary_path, source_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return result
