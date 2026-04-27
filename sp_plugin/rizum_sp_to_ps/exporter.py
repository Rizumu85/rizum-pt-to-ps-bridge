"""Painter export request generation."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from . import bridge
from .blend_map import decide_node_blending
from .udim import uv_to_udim

SCHEMA_VERSION = 1
BUILD_REQUEST_FILENAME = "build_request.json"


def build_export_requests(settings=None):
    """Build read-only Photoshop request previews from the active project.

    M1 only emits metadata. PNG export via ``alg.mapexport.save`` is introduced
    after this traversal contract is stable.
    """
    settings = settings or {}
    modules = _load_painter_modules()
    return _build_export_requests(modules, settings)


def write_request_previews(output_dir, settings=None):
    """Write one preview JSON file per generated request and return paths."""
    requests = build_export_requests(settings)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    written = []
    for index, request in enumerate(requests, start=1):
        validate_request_preview(request)
        filename = _preview_filename(request, index)
        path = output_path / filename
        path.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")
        written.append(path)
    return written


def write_build_bundles(output_dir, settings=None, export_pngs=True):
    """Write one build bundle per generated request and return JSON paths."""
    settings = settings or {}
    requests = build_export_requests(settings)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    written = []
    for index, request in enumerate(requests, start=1):
        validate_request_preview(request)
        bundle_path = output_path / _bundle_name(request, index)
        asset_path = bundle_path / "png"
        asset_path.mkdir(parents=True, exist_ok=True)

        build_request = build_request_from_preview(request, bundle_path, settings)
        build_request["assets_exported"] = bool(export_pngs)
        if export_pngs:
            export_request_assets(build_request)

        request_path = bundle_path / BUILD_REQUEST_FILENAME
        build_request["build_request_file"] = str(request_path)
        request_path.write_text(
            json.dumps(build_request, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(request_path)

    return written


def build_request_from_preview(preview_request, bundle_dir, settings=None):
    """Promote one preview request to a Photoshop build request."""
    settings = settings or {}
    request = deepcopy(preview_request)
    bundle_path = Path(bundle_dir)
    asset_path = bundle_path / "png"

    request["request_type"] = "build"
    request["asset_dir"] = str(asset_path)
    request["psd_file"] = str(_psd_path(request, bundle_path, settings))
    request["channel_identifier"] = bridge.channel_identifier(request["channel"])
    request["export_settings"] = _export_settings(request, settings)

    for node in request["layers"]:
        _annotate_node_assets(node, asset_path)

    return request


def export_request_assets(build_request):
    """Export all PNG payloads referenced by a build request."""
    if build_request.get("request_type") != "build":
        raise ValueError("PNG export requires request_type='build'")

    export_settings = build_request["export_settings"]
    request_channel = build_request["channel_identifier"]
    for asset in _iter_assets(build_request["layers"], request_channel):
        bridge.export_layer_png(
            asset["uid"],
            asset["channel"],
            asset["path"],
            padding=export_settings["padding"],
            dilation=export_settings["dilation"],
            resolution=export_settings["resolution"],
            bit_depth=export_settings["bit_depth"],
            keep_alpha=export_settings["keep_alpha"],
        )


def validate_request_preview(request):
    """Validate the minimal M1 request-preview contract."""
    required = {
        "schema_version",
        "request_type",
        "project",
        "texture_set",
        "stack",
        "channel",
        "channel_format",
        "bit_depth",
        "is_color",
        "udim",
        "uv_tile",
        "normal_map_format",
        "baseline_cache_key",
        "layers",
    }
    missing = sorted(required.difference(request))
    if missing:
        raise ValueError(f"request preview missing fields: {', '.join(missing)}")
    if request["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported request preview schema version")
    if request["request_type"] != "preview":
        raise ValueError("request preview must use request_type='preview'")
    if not isinstance(request["layers"], list):
        raise ValueError("request preview layers must be a list")


def _load_painter_modules():
    try:
        import substance_painter.layerstack as layerstack
        import substance_painter.project as project
        import substance_painter.textureset as textureset
    except ImportError as exc:
        raise RuntimeError(
            "Painter export requests must be built inside Substance 3D Painter."
        ) from exc

    return {
        "layerstack": layerstack,
        "project": project,
        "textureset": textureset,
    }


def _build_export_requests(modules, settings):
    textureset = modules["textureset"]
    layerstack = modules["layerstack"]
    project = modules["project"]

    project_info = _project_info(project)
    generated_at = datetime.now(timezone.utc).isoformat()
    requests = []

    for texture_set in textureset.all_texture_sets():
        texture_set_name = _call_or_attr(texture_set, "name")
        uv_tiles = _uv_tiles(texture_set)

        for stack in texture_set.all_stacks():
            stack_name = _call_or_attr(stack, "name") or ""
            channels = stack.all_channels()
            root_layers = layerstack.get_root_layer_nodes(stack)
            layer_records = [
                _node_record(node, channels.keys(), settings) for node in root_layers
            ]

            for channel_type, channel in channels.items():
                for uv_tile in uv_tiles:
                    requests.append(
                        {
                            "schema_version": SCHEMA_VERSION,
                            "request_type": "preview",
                            "generated_at": generated_at,
                            "project": project_info,
                            "texture_set": texture_set_name,
                            "stack": stack_name,
                            "channel": _enum_name(channel_type),
                            "channel_format": _enum_name(channel.format()),
                            "bit_depth": channel.bit_depth(),
                            "is_color": channel.is_color(),
                            "udim": uv_tile["udim"],
                            "uv_tile": uv_tile,
                            "normal_map_format": settings.get("normal_map_format"),
                            "baseline_cache_key": None,
                            "layers": deepcopy(layer_records),
                        }
                    )

    return requests


def _project_info(project):
    uuid = project.get_uuid()
    return {
        "name": project.name(),
        "path": project.file_path(),
        "uuid": str(uuid) if uuid is not None else None,
    }


def _uv_tiles(texture_set):
    if texture_set.has_uv_tiles():
        return [_uv_tile_record(tile) for tile in texture_set.all_uv_tiles()]

    resolution = texture_set.get_resolution()
    return [
        {
            "u": 0,
            "v": 0,
            "name": "1001",
            "udim": 1001,
            "is_udim": False,
            "resolution": _resolution_record(resolution),
        }
    ]


def _uv_tile_record(tile):
    return {
        "u": int(tile.u),
        "v": int(tile.v),
        "name": tile.name,
        "udim": uv_to_udim(tile.u, tile.v),
        "is_udim": True,
        "resolution": _resolution_record(tile.get_resolution()),
    }


def _node_record(node, channel_types, settings):
    record = {
        "uid": node.uid(),
        "uid_hex": format(node.uid(), "x"),
        "name": node.get_name(),
        "kind": _enum_name(node.get_type()),
        "visible": node.is_visible(),
        "has_blending": node.has_blending(),
        "blend_mode": None,
        "opacity": None,
        "bake_policy": "no_blending",
        "sync_direction": "none",
        "ps_blend_mode": None,
        "blend_decisions": {},
        "warnings": [],
    }

    if record["has_blending"]:
        record["blend_mode"] = _blend_modes(node, channel_types)
        record["opacity"] = _opacities(node, channel_types)
        record.update(
            decide_node_blending(
                record["blend_mode"],
                preserve_all_layers=settings.get("preserve_all_layers", False),
            )
        )

    if hasattr(node, "has_mask"):
        record.update(_mask_record(node))
    if hasattr(node, "sub_layers"):
        record["children"] = [
            _node_record(child, channel_types, settings) for child in node.sub_layers()
        ]
    if hasattr(node, "content_effects"):
        record["content_effects"] = [
            _node_record(effect, channel_types, settings)
            for effect in node.content_effects()
        ]
    if hasattr(node, "mask_effects"):
        record["mask_effects"] = [
            _node_record(effect, channel_types, settings)
            for effect in node.mask_effects()
        ]

    return record


def _mask_record(node):
    has_mask = node.has_mask()
    record = {"has_mask": has_mask}
    if has_mask:
        record["mask_enabled"] = node.is_mask_enabled()
        record["mask_background"] = _enum_name(node.get_mask_background())
    else:
        record["mask_enabled"] = False
        record["mask_background"] = None
    return record


def _blend_modes(node, channel_types):
    if node.is_in_mask_stack():
        return {"mask": _enum_name(node.get_blending_mode(None))}
    return {
        _enum_name(channel_type): _enum_name(node.get_blending_mode(channel_type))
        for channel_type in channel_types
    }


def _opacities(node, channel_types):
    if node.is_in_mask_stack():
        return {"mask": node.get_opacity(None)}
    return {
        _enum_name(channel_type): node.get_opacity(channel_type)
        for channel_type in channel_types
    }


def _resolution_record(resolution):
    return {
        "width": int(resolution.width),
        "height": int(resolution.height),
    }


def _enum_name(value):
    return getattr(value, "name", str(value))


def _call_or_attr(obj, name):
    value = getattr(obj, name)
    return value() if callable(value) else value


def _preview_filename(request, index):
    parts = _name_parts(request, index)
    return "_".join(parts) + ".build_request.preview.json"


def _bundle_name(request, index):
    return "_".join(_name_parts(request, index))


def _psd_path(request, bundle_path, settings):
    if settings.get("psd_file"):
        return Path(settings["psd_file"])
    return bundle_path / f"{_bundle_name(request, 0)[5:]}.psd"


def _name_parts(request, index):
    parts = [
        f"{index:04d}",
        _safe_filename(request["texture_set"]),
        _safe_filename(request["stack"] or "stack"),
        _safe_filename(request["channel"]),
    ]
    if _request_uses_udim(request):
        parts.append(str(request["udim"]))
    return parts


def _request_uses_udim(request):
    return request.get("uv_tile", {}).get("is_udim", True)


def _export_settings(request, settings):
    infinite_padding = settings.get("infinite_padding", False)
    padding = "Infinite" if infinite_padding else "Transparent"
    dilation = 0 if infinite_padding else int(settings.get("dilation", 0))
    resolution = request["uv_tile"]["resolution"]
    return {
        "padding": padding,
        "dilation": dilation,
        "bit_depth": int(settings.get("bit_depth") or request["bit_depth"]),
        "keep_alpha": bool(settings.get("keep_alpha", True)),
        "resolution": [int(resolution["width"]), int(resolution["height"])],
    }


def _annotate_node_assets(node, asset_path, in_mask_stack=False):
    if not in_mask_stack and _node_needs_pixel_asset(node):
        prefix = "baked" if node.get("bake_policy") == "bake" else "uid"
        node["asset"] = _asset_record(
            node,
            request_channel=None,
            path=asset_path / f"{prefix}_{node['uid_hex']}.png",
        )

    if not in_mask_stack and node.get("has_mask") and node.get("mask_enabled"):
        node["mask_asset"] = _asset_record(
            node,
            request_channel="mask",
            path=asset_path / f"uid_{node['uid_hex']}_mask.png",
        )

    for child in node.get("children", []):
        _annotate_node_assets(child, asset_path)
    for effect in node.get("content_effects", []):
        _annotate_node_assets(effect, asset_path)
    for effect in node.get("mask_effects", []):
        _annotate_node_assets(effect, asset_path, in_mask_stack=True)


def _asset_record(node, request_channel, path):
    return {
        "uid": node["uid"],
        "uid_hex": node["uid_hex"],
        "channel": request_channel,
        "path": str(path),
    }


def _node_needs_pixel_asset(node):
    if node.get("bake_policy") == "hidden":
        return False
    if node.get("children"):
        return node.get("bake_policy") == "bake"
    return True


def _iter_assets(nodes, request_channel=None):
    for node in nodes:
        asset = node.get("asset")
        if asset is not None:
            yield {
                **asset,
                "channel": asset["channel"] or request_channel,
            }
        mask_asset = node.get("mask_asset")
        if mask_asset is not None:
            yield mask_asset

        yield from _iter_assets(node.get("children", []), request_channel)
        yield from _iter_assets(node.get("content_effects", []), request_channel)


def _safe_filename(value):
    text = str(value or "unnamed")
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text)
