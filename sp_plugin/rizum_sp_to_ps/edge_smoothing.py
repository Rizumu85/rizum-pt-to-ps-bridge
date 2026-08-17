"""Fast edge-only antialiasing for final Painter export payloads."""

from __future__ import annotations

import ctypes
import os
from functools import lru_cache
from pathlib import Path

ALGORITHM_ID = "directional-corner-coverage-aa-v3"
_NATIVE_ERROR = (1 << 64) - 1


@lru_cache(maxsize=1)
def _native_library():
    path = Path(__file__).with_name("native") / "rizum_edge_smoothing_v3.dll"
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
        )
        function.restype = ctypes.c_uint64
    return library


def smooth_png(path):
    """Smooth directional color and coverage corners without growing bounds."""
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
        function(pixels, image.width(), image.height(), image.bytesPerLine())
    )
    if changed_pixels == _NATIVE_ERROR:
        raise RuntimeError(f"Invalid image buffer while smoothing {source_path}")

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
