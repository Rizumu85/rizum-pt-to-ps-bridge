"""Resolve Photoshop output names from Painter export presets."""

from __future__ import annotations

import re
from pathlib import Path

from . import bridge

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_SEPARATOR_RUN = re.compile(r"([._-])\1+")
_UDIM_OPTIONAL_GROUP = re.compile(
    r"\(([^()]*(?:\$udim|\$uvTileName)[^()]*)\)",
    flags=re.IGNORECASE,
)


def load_project_preset(painter_export):
    """Return the selected Painter preset name and its Python API object."""
    if painter_export is None:
        return None, None

    try:
        selected = str(bridge.project_export_preset() or "").strip()
    except Exception:
        return None, None
    if not selected:
        return None, None

    presets = []
    for list_name in (
        "list_predefined_export_presets",
        "list_resource_export_presets",
    ):
        list_presets = getattr(painter_export, list_name, None)
        if callable(list_presets):
            try:
                presets.extend(list_presets())
            except Exception:
                continue

    selected_key = _normalized(selected)
    for preset in presets:
        identities = _preset_identities(preset)
        if any(_normalized(identity) == selected_key for identity in identities):
            return selected, preset
    return selected, None


def list_output_maps(preset, stack):
    """Read output-map definitions from either Painter preset class."""
    if preset is None:
        return []
    getter = getattr(preset, "list_output_maps", None)
    if not callable(getter):
        return []

    # Resource presets take no stack argument while predefined presets require
    # one. Their shared method name hides that API split.
    try:
        maps = getter() if hasattr(preset, "resource_id") else getter(stack)
    except Exception:
        try:
            maps = getter()
        except Exception:
            return []
    return list(maps or [])


def resolve_output_naming(request, preset_name, output_maps, mesh_path=None):
    """Return diagnostic naming metadata and a filesystem-safe output stem."""
    pattern = select_output_pattern(output_maps, request)
    if pattern:
        stem = render_output_pattern(pattern, request, mesh_path=mesh_path)
        return {
            "source": "project_export_preset",
            "preset": preset_name,
            "pattern": pattern,
            "stem": stem,
        }

    return {
        "source": "bridge_default",
        "preset": preset_name,
        "pattern": None,
        "stem": default_output_stem(request),
    }


def select_output_pattern(output_maps, request):
    """Choose the preset map that represents the request's Painter channel."""
    candidates = _request_channel_candidates(request)
    matches = []
    for index, output_map in enumerate(output_maps or []):
        pattern = str(output_map.get("fileName") or "").strip()
        if not pattern:
            continue

        source_names = {
            _normalized(channel.get("srcMapName"))
            for channel in output_map.get("channels", [])
            if str(channel.get("srcMapType") or "").lower() == "documentmap"
        }
        source_names.discard("")
        exact_matches = source_names.intersection(candidates)
        if exact_matches:
            # A one-channel map is a truer name for a one-channel PSD than an
            # ORM-style packed map that happens to include the same channel.
            matches.append((200 - len(source_names), -index, pattern))
            continue

        pattern_key = _normalized(pattern)
        if any(candidate and candidate in pattern_key for candidate in candidates):
            matches.append((50, -index, pattern))

    if not matches:
        return None
    return max(matches)[2]


def render_output_pattern(pattern, request, mesh_path=None):
    """Expand Painter filename tokens for one Photoshop request."""
    text = str(pattern or "")
    uses_udim = bool(request.get("uv_tile", {}).get("is_udim"))
    udim = str(request.get("udim") or request.get("uv_tile", {}).get("udim") or "")
    text = _resolve_udim_optional_groups(text, uses_udim)

    if not uses_udim:
        # Non-UDIM projects should never inherit a synthetic 1001 suffix from
        # Painter's internal tile representation.
        text = re.sub(r"[._-]?\$udim(?:[._-])?", "_", text, flags=re.IGNORECASE)

    project = request.get("project") or {}
    mesh_name = Path(str(mesh_path or project.get("mesh_path") or "")).stem
    if not mesh_name:
        mesh_name = str(project.get("name") or "project")
    texture_set = str(request.get("texture_set") or "texture_set")
    scene_material = str(request.get("texture_set_original") or texture_set)
    uv_tile_name = str(request.get("uv_tile", {}).get("name") or "") if uses_udim else ""
    color_space = "sRGB" if request.get("is_color") else "Linear"

    replacements = {
        "$colorSpace": color_space,
        "$mesh": mesh_name,
        "$project": str(project.get("name") or "project"),
        "$sceneMaterial": scene_material,
        "$textureSet": texture_set,
        "$udim": udim if uses_udim else "",
        "$uvTileName": uv_tile_name,
    }
    for token, value in replacements.items():
        text = re.sub(
            re.escape(token),
            lambda _match, value=value: value,
            text,
            flags=re.IGNORECASE,
        )

    text = _strip_known_extension(text)
    text = _safe_output_stem(text)
    if uses_udim and "$udim" not in str(pattern).lower() and udim:
        # A multi-tile preset without $udim would overwrite sibling PSDs, so
        # append the tile while preserving the user's naming pattern.
        text = f"{text}.{udim}"
    return text or default_output_stem(request)


def _resolve_udim_optional_groups(pattern, uses_udim):
    # Painter uses parentheses as conditional syntax around UV-tile tokens;
    # treating them as filename characters creates the literal "(_)" suffix.
    return _UDIM_OPTIONAL_GROUP.sub(
        lambda match: match.group(1) if uses_udim else "",
        str(pattern),
    )


def default_output_stem(request):
    """Return the bridge's deterministic name when no preset map is compatible."""
    channel = str(request.get("channel") or "")
    channel_name = channel
    if channel.startswith("User") and request.get("channel_label"):
        channel_name = request["channel_label"]
    parts = [
        request.get("texture_set"),
        request.get("stack") or "stack",
        channel_name,
    ]
    stem = "_".join(_legacy_safe_component(part) for part in parts)
    if request.get("uv_tile", {}).get("is_udim"):
        stem = f"{stem}.{request.get('udim')}"
    return stem


def _request_channel_candidates(request):
    values = [
        request.get("channel"),
        request.get("channel_label"),
        request.get("channel_identifier"),
        *(request.get("channel_identifier_candidates") or []),
    ]
    candidates = {_normalized(value) for value in values}
    candidates.discard("")
    return candidates


def _preset_identities(preset):
    identities = []
    name = getattr(preset, "name", None)
    url = getattr(preset, "url", None)
    if name:
        identities.append(name)
    if url:
        identities.append(url)

    resource_id = getattr(preset, "resource_id", None)
    if resource_id is not None:
        resource_name = getattr(resource_id, "name", None)
        if resource_name:
            identities.append(resource_name)
        resource_url = getattr(resource_id, "url", None)
        if callable(resource_url):
            try:
                identities.append(resource_url())
            except Exception:
                pass
    return identities


def _strip_known_extension(value):
    text = str(value)
    suffix = Path(text).suffix.lower()
    if suffix in {
        ".bmp",
        ".exr",
        ".hdr",
        ".jpeg",
        ".jpg",
        ".png",
        ".tga",
        ".tif",
        ".tiff",
    }:
        return text[: -len(suffix)]
    return text


def _safe_output_stem(value):
    text = _INVALID_FILENAME_CHARS.sub("_", str(value or "unnamed"))
    text = _SEPARATOR_RUN.sub(r"\1", text)
    return text.strip(" ._-")


def _legacy_safe_component(value):
    return "".join(
        character if character.isalnum() or character in ("-", "_") else "_"
        for character in str(value or "unnamed")
    )


def _normalized(value):
    return "".join(
        character.lower()
        for character in str(value or "")
        if character.isalnum()
    )
