"""Color-management policy shared by Painter export and Photoshop build."""

from __future__ import annotations

SRGB_PROFILE = "sRGB IEC61966-2.1"
POLICY_SCHEMA_VERSION = 1


def resolve_policy(*, channel_role, channel_format, is_color):
    """Return a value-preserving Photoshop color policy for one channel."""
    role = str(channel_role or "").strip().lower()
    pixel_format = str(channel_format or "").strip().lower()

    # Normal, opacity, and scalar data carry measurements rather than display
    # colors. Keep them untagged even if a host reports contradictory metadata.
    forced_raw = role in {"normal", "opacity"}
    color_managed = not forced_raw and (
        is_color is True or pixel_format.startswith("srgb") or role == "color"
    )
    if color_managed:
        return {
            "schema_version": POLICY_SCHEMA_VERSION,
            "encoding": "srgb",
            "photoshop_profile": SRGB_PROFILE,
            "embed_profile": True,
            "preserve_rgb_numbers": True,
            "classification": _color_classification(role, pixel_format, is_color),
        }

    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "encoding": "raw",
        "photoshop_profile": None,
        "embed_profile": False,
        "preserve_rgb_numbers": True,
        "classification": (
            "semantic_data_channel"
            if forced_raw or role == "data"
            else "conservative_raw"
        ),
    }


def validate_policy(policy):
    """Reject incomplete policy data before Photoshop can interpret pixels."""
    if not isinstance(policy, dict):
        raise ValueError("color_management must be an object")
    if policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise ValueError("unsupported color_management schema_version")
    if policy.get("preserve_rgb_numbers") is not True:
        raise ValueError("color_management must preserve RGB numbers")

    encoding = policy.get("encoding")
    if encoding == "srgb":
        if policy.get("photoshop_profile") != SRGB_PROFILE:
            raise ValueError("sRGB color management requires the standard sRGB profile")
        if policy.get("embed_profile") is not True:
            raise ValueError("sRGB color management must embed its profile")
        return
    if encoding == "raw":
        if policy.get("photoshop_profile") is not None:
            raise ValueError("raw color management cannot assign a profile")
        if policy.get("embed_profile") is not False:
            raise ValueError("raw color management cannot embed a profile")
        return
    raise ValueError(f"unsupported color_management encoding: {encoding!r}")


def _color_classification(role, pixel_format, is_color):
    if is_color is True:
        return "channel_is_color"
    if pixel_format.startswith("srgb"):
        return "srgb_channel_format"
    if role == "color":
        return "color_channel_role"
    return "color_managed"
