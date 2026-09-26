"""Scale a rendered payload PNG down to the PSD's size."""

from __future__ import annotations

import os
from pathlib import Path


def scale_png(path, size):
    """Area-average a PNG to ``size`` in place, keeping its format and depth.

    Colour is averaged premultiplied, so transparent pixels' hidden colour
    cannot bleed a fringe into the edges being averaged.
    """
    from PySide6 import QtCore, QtGui

    source_path = Path(path)
    image = QtGui.QImage(str(source_path))
    if image.isNull():
        raise RuntimeError(f"Could not read rendered PNG to scale: {source_path}")
    width, height = int(size[0]), int(size[1])
    if (image.width(), image.height()) == (width, height):
        return
    formats = QtGui.QImage.Format
    source_format = image.format()
    is_16_bit = image.depth() > 32 or source_format == formats.Format_Grayscale16
    working = formats.Format_RGBA64_Premultiplied if is_16_bit else formats.Format_ARGB32_Premultiplied
    scaled = image.convertToFormat(working).scaled(
        width,
        height,
        QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    ).convertToFormat(source_format)
    scaled.setDotsPerMeterX(image.dotsPerMeterX())
    scaled.setDotsPerMeterY(image.dotsPerMeterY())
    temporary_path = source_path.with_name(f".{source_path.stem}.rizum-scale-{os.getpid()}.png")
    try:
        if not scaled.save(str(temporary_path), "PNG"):
            raise RuntimeError(f"Could not write scaled PNG: {source_path}")
        os.replace(temporary_path, source_path)
    finally:
        temporary_path.unlink(missing_ok=True)
