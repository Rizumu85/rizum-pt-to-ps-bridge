"""Metadata constants and sidecar helpers shared by Painter code."""

UID_SUFFIX_PREFIX = "\u2021"
SIDECAR_EXTENSION = ".rizum.json"


def format_uid_suffix(uid_hex):
    """Format the stable Photoshop layer-name suffix for a Painter uid."""
    return f"{UID_SUFFIX_PREFIX}{uid_hex}"
