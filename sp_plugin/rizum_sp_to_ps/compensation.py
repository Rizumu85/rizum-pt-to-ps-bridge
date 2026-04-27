"""Optional color compensation fallback.

This module is only used if Photoshop's document-level blend-gamma setting
cannot be set through batchPlay during M3 validation.
"""


def apply_compensation(_image_path, _blend_mode):
    """Apply the M3 fallback LUT compensation to an exported raster."""
    raise NotImplementedError("M3 decides whether this fallback is needed.")
