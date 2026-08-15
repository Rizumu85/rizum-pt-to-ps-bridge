"""Painter export request generation."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from . import bridge, geometry_mask, pixel_export
from .blend_map import decide_node_blending
from .udim import uv_to_udim

SCHEMA_VERSION = 1
BUILD_REQUEST_FILENAME = "build_request.json"
EFFECT_NODE_KINDS = {
    "AnchorPointEffect",
    "ColorSelectionEffect",
    "CompareMaskEffect",
    "FillEffect",
    "FilterEffect",
    "GeneratorEffect",
    "LevelsEffect",
    "PaintEffect",
}


class ExportCancelled(RuntimeError):
    """Raised when the user cancels an in-progress Painter export."""


def build_export_requests(settings=None):
    """Build read-only Photoshop request previews from the active project.

    M1 only emits metadata. PNG export via ``alg.mapexport.save`` is introduced
    after this traversal contract is stable.
    """
    settings = settings or {}
    modules = _load_painter_modules()
    return _build_export_requests(modules, settings)


def list_export_targets(settings=None):
    """List available texture set / stack / channel targets for the UI."""
    settings = settings or {}
    modules = _load_painter_modules()
    textureset = modules["textureset"]
    layerstack = modules["layerstack"]
    targets = []

    for texture_set in _call_or_attr(textureset, "all_texture_sets", []):
        texture_set_name = _call_or_attr(texture_set, "name")
        if not _matches_filter(texture_set_name, settings.get("texture_sets")):
            continue

        for stack in _call_or_attr(texture_set, "all_stacks", []):
            stack_name = _call_or_attr(stack, "name") or ""
            if not _matches_filter(stack_name, settings.get("stacks")):
                continue

            stack_channels = _call_or_attr(stack, "all_channels", {})
            used_identifiers = _used_channel_identifier_set(
                texture_set_name,
                stack_name,
            )
            root_layers = layerstack.get_root_layer_nodes(stack)
            layer_records = [
                _node_record(node, stack_channels.keys(), settings)
                for node in root_layers
            ]
            channels = [
                _enum_name(channel_type)
                for channel_type, channel in stack_channels.items()
                if _channel_should_export(
                    _enum_name(channel_type),
                    channel,
                    used_identifiers,
                    layer_records,
                )
                and _matches_filter(_enum_name(channel_type), settings.get("channels"))
            ]
            if not channels:
                continue
            channel_labels = {
                _enum_name(channel_type): _channel_label(
                    _enum_name(channel_type),
                    channel,
                )
                for channel_type, channel in stack_channels.items()
                if _channel_should_export(
                    _enum_name(channel_type),
                    channel,
                    used_identifiers,
                    layer_records,
                )
                and _matches_filter(_enum_name(channel_type), settings.get("channels"))
            }
            targets.append(
                {
                    "texture_set": texture_set_name,
                    "stack": stack_name,
                    "channels": channels,
                    "channel_labels": channel_labels,
                    "uv_tile_count": len(_uv_tiles(texture_set)),
                }
            )

    return targets


def default_output_dir(settings=None):
    """Return the default folder for Painter-to-Photoshop build bundles."""
    settings = settings or {}
    if settings.get("output_dir"):
        return Path(settings["output_dir"])

    modules = _load_painter_modules()
    project = modules["project"]
    project_name = _safe_filename(_call_or_attr(project, "name") or "project")

    export_root = None
    try:
        export_root_text = bridge.export_project_path()
        if export_root_text:
            export_root = Path(str(export_root_text))
    except Exception:
        export_root = None

    if export_root is None:
        project_path = _call_or_attr(project, "file_path")
        export_root = Path(project_path).parent if project_path else Path.cwd()

    return export_root / f"{project_name}_photoshop_export"


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


def write_build_bundles(
    output_dir,
    settings=None,
    export_pngs=True,
    progress_callback=None,
):
    """Write one build bundle per generated request and return JSON paths."""
    settings = settings or {}
    _notify_progress(
        progress_callback,
        stage="prepare",
        value=0,
        total=0,
        text="Preparing export requests...",
    )
    requests = build_export_requests(settings)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    total = len(requests)
    _notify_progress(
        progress_callback,
        stage="bundles",
        value=0,
        total=total,
        text=f"Writing {total} build request(s)...",
    )

    written = []
    geometry_baker = geometry_mask.GeometryMaskBaker(
        checkpoint=lambda: _notify_progress(
            progress_callback,
            stage="heartbeat",
            value=0,
            total=0,
            text="",
        )
    )
    try:
        for index, request in enumerate(requests, start=1):
            _notify_progress(
                progress_callback,
                stage="bundles",
                value=index - 1,
                total=total,
                text=f"Exporting {index} of {total}: {_request_label(request)}",
            )
            validate_request_preview(request)
            bundle_path = output_path / _bundle_name(request, index)
            asset_path = bundle_path / "png"
            asset_path.mkdir(parents=True, exist_ok=True)

            build_request = build_request_from_preview(request, bundle_path, settings)
            build_request["assets_exported"] = bool(export_pngs)
            if export_pngs:
                export_request_assets(
                    build_request,
                    progress_callback=progress_callback,
                    progress_prefix=f"{index} of {total}",
                    geometry_baker=geometry_baker,
                )
                if _count_layer_assets(build_request["layers"]) == 0:
                    shutil.rmtree(bundle_path, ignore_errors=True)
                    continue

            request_path = bundle_path / BUILD_REQUEST_FILENAME
            build_request["build_request_file"] = str(request_path)
            request_path.write_text(
                json.dumps(build_request, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            written.append(request_path)
            _notify_progress(
                progress_callback,
                stage="bundles",
                value=index,
                total=total,
                text=f"Finished {index} of {total}: {_request_label(request)}",
            )
    finally:
        geometry_baker.close()

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
    request["channel_identifier"] = _request_channel_identifier(request)
    request["channel_identifier_candidates"] = _request_channel_identifier_candidates(
        request
    )
    request["export_settings"] = _export_settings(request, settings)

    for node in request["layers"]:
        _annotate_node_assets(
            node,
            asset_path,
            request_channel=request["channel"],
            request=request,
        )

    return request


def export_request_assets(
    build_request,
    progress_callback=None,
    progress_prefix="",
    geometry_baker=None,
):
    """Export all PNG payloads referenced by a build request."""
    if build_request.get("request_type") != "build":
        raise ValueError("PNG export requires request_type='build'")

    export_settings = build_request["export_settings"]
    request_channel = build_request["channel_identifier"]
    channel_candidates = build_request.get("channel_identifier_candidates") or [
        request_channel
    ]
    if not str(build_request.get("channel") or "").startswith("User"):
        channel_candidates = [request_channel]
    assets = list(_iter_assets(build_request["layers"], request_channel))
    layer_assets = [asset for asset in assets if asset["kind"] == "layer"]
    initial_mask_count = sum(
        asset["kind"] in {"mask", "geometry_mask"} for asset in assets
    )
    total = len(layer_assets) + initial_mask_count
    completed = 0
    for asset in layer_assets:
        index = completed + 1
        layer_label = asset.get("label") or asset["uid_hex"]
        prefix = f"{progress_prefix}: " if progress_prefix else ""
        _notify_progress(
            progress_callback,
            stage="assets",
            value=index - 1,
            total=total,
            text=f"{prefix}exporting PNG {index} of {total}: {layer_label}",
        )
        candidates = _dedupe_text([asset["channel"], *channel_candidates])
        if pixel_export.export_layer_png(asset, export_settings, candidates):
            _remove_asset_by_path(build_request["layers"], asset["path"])
            _remove_file_if_exists(asset["path"])
        completed += 1
        _notify_progress(
            progress_callback,
            stage="assets",
            value=completed,
            total=total,
            text=f"{prefix}finished PNG {index} of {total}: {layer_label}",
        )

    # Re-plan masks after empty channel layers are pruned so their now-orphaned
    # masks are neither exported nor left beside the finished bundle.
    mask_assets = [
        asset
        for asset in _iter_assets(build_request["layers"], request_channel)
        if asset["kind"] == "mask"
    ]
    total = len(layer_assets) + len(mask_assets)
    for asset in mask_assets:
        index = completed + 1
        layer_label = asset.get("label") or asset["uid_hex"]
        prefix = f"{progress_prefix}: " if progress_prefix else ""
        _notify_progress(
            progress_callback,
            stage="assets",
            value=completed,
            total=total,
            text=f"{prefix}exporting PNG {index} of {total}: {layer_label}",
        )
        pixel_export.export_mask_png(asset, export_settings)
        completed += 1
        _notify_progress(
            progress_callback,
            stage="assets",
            value=completed,
            total=total,
            text=f"{prefix}finished PNG {index} of {total}: {layer_label}",
        )

    geometry_assets = [
        asset
        for asset in _iter_assets(build_request["layers"], request_channel)
        if asset["kind"] == "geometry_mask"
    ]
    total += len(geometry_assets)
    owns_baker = geometry_baker is None
    if owns_baker:
        geometry_baker = geometry_mask.GeometryMaskBaker(
            checkpoint=lambda: _notify_progress(
                progress_callback,
                stage="heartbeat",
                value=0,
                total=0,
                text="",
            )
        )
    try:
        diagnostics = []
        for asset in geometry_assets:
            index = completed + 1
            layer_label = asset.get("label") or asset["uid_hex"]
            prefix = f"{progress_prefix}: " if progress_prefix else ""
            _notify_progress(
                progress_callback,
                stage="assets",
                value=completed,
                total=total,
                text=f"{prefix}exporting Geometry Mask {index} of {total}: {layer_label}",
            )
            try:
                diagnostics.append(geometry_baker.bake(asset, asset["path"]))
            except geometry_mask.GeometryMaskExportError as exc:
                error_path = Path(build_request["asset_dir"]).parent / "geometry_mask_error.json"
                geometry_mask.write_error_diagnostics(error_path, exc)
                raise RuntimeError(
                    f"Could not export Geometry Mask for {layer_label}. "
                    f"Diagnostics: {error_path}. {exc}"
                ) from exc
            completed += 1
            _notify_progress(
                progress_callback,
                stage="assets",
                value=completed,
                total=total,
                text=f"{prefix}finished Geometry Mask {index} of {total}: {layer_label}",
            )
        if diagnostics:
            build_request["geometry_mask_diagnostics"] = diagnostics
        _finalize_geometry_masks(build_request["layers"])
    finally:
        if owns_baker:
            geometry_baker.close()

    build_request["empty_layer_assets_removed"] = _count_pruned_assets(
        build_request["layers"]
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

    for texture_set in _call_or_attr(textureset, "all_texture_sets", []):
        texture_set_name = _call_or_attr(texture_set, "name")
        if not _matches_filter(texture_set_name, settings.get("texture_sets")):
            continue

        uv_tiles = _uv_tiles(texture_set)

        for stack in _call_or_attr(texture_set, "all_stacks", []):
            stack_name = _call_or_attr(stack, "name") or ""
            if not _matches_filter(stack_name, settings.get("stacks")):
                continue

            channels = _call_or_attr(stack, "all_channels", {})
            used_identifiers = _used_channel_identifier_set(
                texture_set_name,
                stack_name,
            )
            root_layers = layerstack.get_root_layer_nodes(stack)
            layer_records = [
                _node_record(node, channels.keys(), settings) for node in root_layers
            ]

            for channel_type, channel in channels.items():
                channel_name = _enum_name(channel_type)
                if not _channel_should_export(
                    channel_name,
                    channel,
                    used_identifiers,
                    layer_records,
                ):
                    continue
                if not _matches_filter(channel_name, settings.get("channels")):
                    continue

                is_color = _call_or_attr(channel, "is_color", False)
                for uv_tile in uv_tiles:
                    requests.append(
                        {
                            "schema_version": SCHEMA_VERSION,
                            "request_type": "preview",
                            "generated_at": generated_at,
                            "project": project_info,
                            "texture_set": texture_set_name,
                            "texture_set_original": _call_or_attr(
                                texture_set,
                                "original_name",
                            ),
                            "stack": stack_name,
                            "channel": channel_name,
                            "channel_label": _channel_label(channel_name, channel),
                            "channel_identifier": _resolved_channel_identifier(
                                channel_name,
                                channel,
                                used_identifiers,
                            ),
                            "channel_identifier_candidates": _channel_export_candidates(
                                channel_name,
                                channel,
                                used_identifiers,
                            ),
                            "channel_role": _channel_role(channel_name, is_color),
                            "channel_format": _enum_name(_call_or_attr(channel, "format")),
                            "bit_depth": _call_or_attr(channel, "bit_depth"),
                            "is_color": is_color,
                            "udim": uv_tile["udim"],
                            "uv_tile": uv_tile,
                            "normal_map_format": settings.get("normal_map_format"),
                            "baseline_cache_key": None,
                            "layers": _layers_for_uv_tile(
                                layer_records,
                                uv_tile,
                                channel_name,
                            ),
                        }
                    )

    return requests


def _project_info(project):
    uuid = _call_or_attr(project, "get_uuid")
    return {
        "name": _call_or_attr(project, "name"),
        "path": _call_or_attr(project, "file_path"),
        "uuid": str(uuid) if uuid is not None else None,
    }


def _uv_tiles(texture_set):
    if _call_or_attr(texture_set, "has_uv_tiles", False):
        return [_uv_tile_record(tile) for tile in _call_or_attr(texture_set, "all_uv_tiles", [])]

    resolution = _call_or_attr(texture_set, "get_resolution")
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
        "resolution": _resolution_record(_call_or_attr(tile, "get_resolution")),
    }


def _node_record(node, channel_types, settings):
    uid = _call_or_attr(node, "uid")
    record = {
        "uid": uid,
        "uid_hex": format(uid, "x"),
        "name": _call_or_attr(node, "get_name"),
        "kind": _enum_name(_call_or_attr(node, "get_type")),
        "visible": _call_or_attr(node, "is_visible", True),
        "has_blending": _call_or_attr(node, "has_blending", False),
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

    active_channels = _active_channels(node)
    if active_channels is not None:
        record["active_channels"] = active_channels
    if hasattr(node, "has_mask"):
        record.update(_mask_record(node))
    if hasattr(node, "get_geometry_mask"):
        record["geometry_mask"] = _geometry_mask_record(node)
    if hasattr(node, "sub_layers"):
        record["children"] = [
            _node_record(child, channel_types, settings)
            for child in _call_or_attr(node, "sub_layers", [])
        ]
    if hasattr(node, "content_effects"):
        record["content_effects"] = [
            _node_record(effect, channel_types, settings)
            for effect in _call_or_attr(node, "content_effects", [])
        ]
    if hasattr(node, "mask_effects"):
        record["mask_effects"] = [
            _node_record(effect, channel_types, settings)
            for effect in _call_or_attr(node, "mask_effects", [])
        ]

    return record


def _mask_record(node):
    has_mask = _call_or_attr(node, "has_mask", False)
    record = {"has_mask": has_mask}
    if has_mask:
        record["mask_enabled"] = _call_or_attr(node, "is_mask_enabled", True)
        record["mask_background"] = _enum_name(_call_or_attr(node, "get_mask_background"))
    else:
        record["mask_enabled"] = False
        record["mask_background"] = None
    return record


def _geometry_mask_record(node):
    params = _call_or_attr(node, "get_geometry_mask")
    inclusion_list = bool(getattr(params, "inclusion_list", True))
    if hasattr(params, "uv_tiles"):
        return {
            "mode": "uv_tile",
            "inclusion_list": inclusion_list,
            "uv_tiles": [
                {
                    "u": int(tile.u),
                    "v": int(tile.v),
                    "name": str(getattr(tile, "name", "")),
                }
                for tile in params.uv_tiles
            ],
        }
    listed_meshes = [str(mesh) for mesh in getattr(params, "meshes", [])]
    texture_set = _call_or_attr(node, "get_texture_set")
    all_meshes = [
        str(mesh) for mesh in _call_or_attr(texture_set, "all_mesh_names", [])
    ]
    if inclusion_list:
        enabled_meshes = listed_meshes
    else:
        excluded = set(listed_meshes)
        enabled_meshes = [mesh for mesh in all_meshes if mesh not in excluded]
    return {
        "mode": "mesh",
        "inclusion_list": inclusion_list,
        "meshes": listed_meshes,
        "enabled_meshes": enabled_meshes,
        "is_restrictive": bool(all_meshes)
        and set(enabled_meshes) != set(all_meshes),
        "is_empty": bool(all_meshes) and not enabled_meshes,
    }


def _layers_for_uv_tile(layer_records, uv_tile, channel_name):
    layers = deepcopy(layer_records)
    layers = _filter_nodes_for_uv_tile(layers, uv_tile)
    _project_nodes_for_channel(layers, channel_name)
    return layers


def _project_nodes_for_channel(nodes, channel_name, in_mask_stack=False):
    for node in nodes:
        decision_key = "mask" if in_mask_stack else channel_name
        decision = (node.get("blend_decisions") or {}).get(decision_key)
        if decision is not None:
            # A PSD request represents one channel. Letting another channel's
            # blend mode win here collapses otherwise editable folder trees.
            node["bake_policy"] = decision["bake_policy"]
            node["sync_direction"] = decision["sync_direction"]
            node["ps_blend_mode"] = decision["ps_blend_mode"]
            node["warnings"] = list(decision.get("warnings") or [])

        _project_nodes_for_channel(
            node.get("children", []),
            channel_name,
        )
        _project_nodes_for_channel(
            node.get("content_effects", []),
            channel_name,
        )
        _project_nodes_for_channel(
            node.get("mask_effects", []),
            channel_name,
            in_mask_stack=True,
        )


def _filter_nodes_for_uv_tile(nodes, uv_tile):
    kept = []
    tile_key = (int(uv_tile["u"]), int(uv_tile["v"]))
    for node in nodes:
        geometry_mask = node.get("geometry_mask") or {}
        if geometry_mask.get("mode") == "mesh" and geometry_mask.get("is_empty"):
            continue
        if geometry_mask.get("mode") == "uv_tile":
            listed = {
                (int(tile["u"]), int(tile["v"]))
                for tile in geometry_mask.get("uv_tiles", [])
            }
            is_enabled = tile_key in listed
            if not geometry_mask.get("inclusion_list", True):
                is_enabled = not is_enabled
            if not is_enabled:
                continue

        node["children"] = _filter_nodes_for_uv_tile(
            node.get("children", []),
            uv_tile,
        )
        kept.append(node)
    return kept


def _blend_modes(node, channel_types):
    if _call_or_attr(node, "is_in_mask_stack", False):
        return {"mask": _enum_name(node.get_blending_mode(None))}
    return {
        _enum_name(channel_type): _enum_name(node.get_blending_mode(channel_type))
        for channel_type in channel_types
    }


def _opacities(node, channel_types):
    if _call_or_attr(node, "is_in_mask_stack", False):
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


def _notify_progress(callback, **payload):
    if callback is None:
        return
    if callback(payload) is False:
        raise ExportCancelled("Export cancelled by user.")


def _request_label(request):
    stack = request.get("stack") or "(default)"
    channel = request.get("channel_label") or request.get("channel")
    udim = request.get("udim")
    tile = "" if not _request_uses_udim(request) else f" / {udim}"
    return f"{request.get('texture_set')} / {stack} / {channel}{tile}"


def _channel_role(channel_name, is_color):
    normalized = str(channel_name or "").lower()
    if normalized in {"normal", "normalmap"}:
        return "normal"
    if normalized in {"opacity", "alpha"}:
        return "opacity"
    if normalized.startswith("user"):
        return "user"
    if is_color:
        return "color"
    return "data"


def _channel_label(channel_name, channel=None):
    if channel is not None and str(channel_name or "").startswith("User"):
        label = _safe_call(channel, "label")
        if label:
            return str(label)

    labels = {
        "BaseColor": "Base Color",
        "Diffuse": "Diffuse",
        "Opacity": "Opacity",
        "Normal": "Normal",
        "Height": "Height",
        "Roughness": "Roughness",
        "Metallic": "Metallic",
        "Metalness": "Metalness",
        "Specular": "Specular",
        "Glossiness": "Glossiness",
        "Emissive": "Emissive",
        "AmbientOcclusion": "Ambient Occlusion",
    }
    text = str(channel_name or "").strip()
    return labels.get(text, text or "Unknown")


def _used_channel_identifier_set(texture_set_name, stack_name):
    try:
        identifiers = bridge.document_structure_channel_identifiers(
            texture_set_name,
            stack_name,
        )
    except Exception:
        identifiers = None
    if not identifiers:
        try:
            identifiers = bridge.used_channel_identifiers(texture_set_name, stack_name)
        except Exception:
            return None
    if identifiers is None:
        return None
    return {
        str(item).strip().lower(): str(item).strip()
        for item in identifiers
        if str(item).strip()
    }


def _channel_is_used(channel_name, channel, used_identifiers):
    if used_identifiers is None:
        return True

    candidates = _channel_identifier_candidates(channel_name, channel)
    return any(candidate in used_identifiers for candidate in candidates)


def _channel_should_export(channel_name, channel, used_identifiers, layer_records):
    if _channel_is_used(channel_name, channel, used_identifiers):
        return True
    return _channel_has_active_node(layer_records, channel_name)


def _channel_has_active_node(nodes, channel_name):
    target = str(channel_name or "")
    for node in nodes:
        active_channels = node.get("active_channels")
        if active_channels is not None and target in {
            str(channel) for channel in active_channels
        }:
            return True
        if _channel_has_active_node(node.get("children", []), channel_name):
            return True
        if _channel_has_active_node(node.get("content_effects", []), channel_name):
            return True
    return False


def _resolved_channel_identifier(channel_name, channel, used_identifiers):
    if used_identifiers is not None:
        for candidate in _channel_identifier_candidates(channel_name, channel):
            identifier = used_identifiers.get(candidate)
            if identifier:
                return identifier
    return _channel_identifier_from_name_and_label(channel_name, _channel_label(channel_name, channel))


def _request_channel_identifier(request):
    identifier = str(request.get("channel_identifier") or "").strip()
    if identifier:
        return identifier
    return _channel_identifier_from_name_and_label(
        request.get("channel"),
        request.get("channel_label"),
    )


def _request_channel_identifier_candidates(request):
    candidates = list(request.get("channel_identifier_candidates") or [])
    if not candidates:
        candidates = [
            _channel_identifier_from_name_and_label(
                request.get("channel"),
                request.get("channel_label"),
            )
        ]
    candidates.extend(_user_channel_identifier_variants(request.get("channel")))
    return _dedupe_text(candidates)


def _channel_identifier_from_name_and_label(channel_name, channel_label):
    channel_text = str(channel_name or "").strip()
    label = str(channel_label or "").strip()
    if channel_text.startswith("User") and label:
        return label
    return bridge.channel_identifier(channel_text)


def _channel_export_candidates(channel_name, channel, used_identifiers):
    primary = _resolved_channel_identifier(channel_name, channel, used_identifiers)
    label = _channel_label(channel_name, channel)
    candidates = [
        primary,
        label,
        str(label).lower() if label else None,
        channel_name,
        str(channel_name).lower() if channel_name else None,
        bridge.channel_identifier(channel_name),
        *_user_channel_identifier_variants(channel_name),
    ]
    return _dedupe_text(candidates)


def _channel_identifier_candidates(channel_name, channel):
    candidates = {str(channel_name or "").strip().lower()}
    identifier = bridge.channel_identifier(channel_name)
    if identifier:
        candidates.add(str(identifier).strip().lower())
    label = _channel_label(channel_name, channel)
    if label:
        candidates.add(str(label).strip().lower())
    for candidate in _user_channel_identifier_variants(channel_name):
        candidates.add(candidate.lower())
    return candidates


def _user_channel_identifier_variants(channel_name):
    text = str(channel_name or "").strip()
    if not text.lower().startswith("user"):
        return []
    suffix = text[4:].strip()
    if not suffix.isdigit():
        return []
    return [f"user{suffix}", f"user {suffix}"]


def _dedupe_text(values):
    result = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _safe_call(obj, name):
    method = getattr(obj, name, None)
    if not callable(method):
        return None
    try:
        return method()
    except Exception:
        return None


def _active_channels(node):
    try:
        active_channels = getattr(node, "active_channels")
    except Exception:
        return None
    if active_channels is None:
        return None
    try:
        return sorted(_enum_name(channel) for channel in active_channels)
    except Exception:
        return None


def _call_or_attr(obj, name, default=None):
    value = getattr(obj, name, default)
    return value() if callable(value) else value


def _matches_filter(value, accepted_values):
    if not accepted_values:
        return True
    return str(value) in {str(item) for item in accepted_values}


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
        _safe_filename(_channel_name_for_path(request)),
    ]
    if _request_uses_udim(request):
        parts.append(str(request["udim"]))
    return parts


def _channel_name_for_path(request):
    label = str(request.get("channel_label") or "").strip()
    channel = str(request.get("channel") or "").strip()
    if label and channel.startswith("User"):
        return label
    return channel


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


def _annotate_node_assets(
    node,
    asset_path,
    request_channel=None,
    in_mask_stack=False,
    request=None,
):
    if (
        not in_mask_stack
        and _node_needs_pixel_asset(node)
        and _node_is_active_for_channel(node, request_channel)
    ):
        prefix = "baked" if node.get("bake_policy") == "bake" else "uid"
        node["asset"] = _asset_record(
            node,
            request_channel=None,
            path=asset_path / f"{prefix}_{node['uid_hex']}.png",
        )

    if (
        not in_mask_stack
        and node.get("has_mask")
        and node.get("mask_enabled")
    ):
        node["mask_asset"] = _asset_record(
            node,
            request_channel="mask",
            path=asset_path / f"uid_{node['uid_hex']}_mask.png",
        )
        node["mask_asset"]["source"] = "painter_layer_mask"
        node["mask_asset"]["fidelity"] = "lossless"

    geometry = node.get("geometry_mask") or {}
    if (
        not in_mask_stack
        and geometry.get("mode") == "mesh"
        and geometry.get("is_restrictive")
        and geometry.get("enabled_meshes")
    ):
        node["geometry_mask_asset"] = _asset_record(
            node,
            request_channel="geometry_mask",
            path=asset_path / f"uid_{node['uid_hex']}_geometry_mask.png",
        )
        node["geometry_mask_asset"].update(
            {
                "source": "painter_geometry_mask",
                "fidelity": "uv_rasterized",
                "enabled_meshes": list(geometry["enabled_meshes"]),
                "texture_set": request["texture_set"],
                "texture_set_original": request.get("texture_set_original"),
                "uv_tile": deepcopy(request["uv_tile"]),
                "resolution": list(request["export_settings"]["resolution"]),
                "padding": request["export_settings"]["padding"],
                "dilation": int(request["export_settings"]["dilation"]),
            }
        )

    for child in node.get("children", []):
        _annotate_node_assets(
            child,
            asset_path,
            request_channel=request_channel,
            request=request,
        )
    for effect in node.get("content_effects", []):
        _annotate_node_assets(
            effect,
            asset_path,
            request_channel=request_channel,
            request=request,
        )
    for effect in node.get("mask_effects", []):
        _annotate_node_assets(
            effect,
            asset_path,
            request_channel=request_channel,
            in_mask_stack=True,
            request=request,
        )


def _node_is_active_for_channel(node, request_channel):
    active_channels = node.get("active_channels")
    if active_channels is None:
        return True
    return str(request_channel or "") in {str(channel) for channel in active_channels}


def _asset_record(node, request_channel, path):
    return {
        "uid": node["uid"],
        "uid_hex": node["uid_hex"],
        "label": node.get("name"),
        "channel": request_channel,
        "path": str(path),
    }


def _node_needs_pixel_asset(node):
    if node.get("kind") in EFFECT_NODE_KINDS:
        return False
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
                "kind": "layer",
                "channel": asset["channel"] or request_channel,
            }
        mask_asset = node.get("mask_asset")
        if mask_asset is not None:
            yield {
                **mask_asset,
                "kind": "mask",
            }
        geometry_asset = node.get("geometry_mask_asset")
        if geometry_asset is not None:
            yield {
                **geometry_asset,
                "kind": "geometry_mask",
            }

        yield from _iter_assets(node.get("children", []), request_channel)
        yield from _iter_assets(node.get("content_effects", []), request_channel)


def _remove_asset_by_path(nodes, asset_path):
    target = str(asset_path)
    for node in nodes:
        asset = node.get("asset")
        if asset is not None and str(asset.get("path")) == target:
            node.pop("asset", None)
            node.pop("mask_asset", None)
            node.pop("geometry_mask_asset", None)
            node["asset_pruned"] = "empty_alpha"
            return True
        if _remove_asset_by_path(node.get("children", []), asset_path):
            return True
        if _remove_asset_by_path(node.get("content_effects", []), asset_path):
            return True
    return False


def _count_pruned_assets(nodes):
    total = 0
    for node in nodes:
        if node.get("asset_pruned"):
            total += 1
        total += _count_pruned_assets(node.get("children", []))
        total += _count_pruned_assets(node.get("content_effects", []))
    return total


def _count_layer_assets(nodes):
    total = 0
    for node in nodes:
        if node.get("asset") is not None:
            total += 1
        total += _count_layer_assets(node.get("children", []))
        total += _count_layer_assets(node.get("content_effects", []))
    return total


def _finalize_geometry_masks(nodes):
    for node in nodes:
        geometry_asset = node.get("geometry_mask_asset")
        regular_asset = node.get("mask_asset")
        if geometry_asset is not None:
            if regular_asset is not None:
                geometry_mask.combine_masks(
                    regular_asset["path"],
                    geometry_asset["path"],
                )
                _remove_file_if_exists(geometry_asset["path"])
                regular_asset["source"] = "painter_layer_and_geometry_mask"
                regular_asset["fidelity"] = "lossless_layer_mask_uv_rasterized_geometry"
            else:
                geometry_asset["channel"] = "mask"
                node["mask_asset"] = geometry_asset
            node.pop("geometry_mask_asset", None)
        _finalize_geometry_masks(node.get("children", []))
        _finalize_geometry_masks(node.get("content_effects", []))


def _remove_file_if_exists(path):
    try:
        Path(path).unlink(missing_ok=True)
    except TypeError:
        file_path = Path(path)
        if file_path.exists():
            file_path.unlink()


def _safe_filename(value):
    text = str(value or "unnamed")
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text)
