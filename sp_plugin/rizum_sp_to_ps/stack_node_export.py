"""Render Painter layer-stack nodes and distribute their UV-tile payloads."""

from __future__ import annotations

import json
import math
import re
import shutil
import tempfile
from pathlib import Path


_TRAILING_UDIM = re.compile(r"(?:^|[._(])_?(1\d{3})\)?$")


class StackNodeExportError(RuntimeError):
    """Raised when Painter cannot render or identify a requested node tile."""


class StackNodeExporter:
    """Cache one native node render and copy the requested tile into each bundle."""

    def __init__(self, backend=None):
        self._backend = backend
        self._temporary_dir = None
        self._cache = {}
        self._sequence = 0

    def close(self):
        if self._temporary_dir is not None:
            self._temporary_dir.cleanup()
            self._temporary_dir = None
        self._cache.clear()

    def export_layer(
        self,
        asset,
        export_settings,
        channel_name,
        uv_tile,
    ):
        self._export(
            asset,
            export_settings,
            channel_name=channel_name,
            uv_tile=uv_tile,
        )

    def export_mask(self, asset, export_settings, uv_tile):
        self._export(
            asset,
            export_settings,
            channel_name=None,
            uv_tile=uv_tile,
        )

    def _export(self, asset, export_settings, channel_name, uv_tile):
        parameters = _native_export_parameters(export_settings)
        cache_key = (
            int(asset["uid"]),
            str(channel_name or "__mask__"),
            json.dumps(parameters, sort_keys=True),
        )
        tile_paths = self._cache.get(cache_key)
        if tile_paths is None:
            template = self._next_template()
            written = self._backend_instance().export(
                int(asset["uid"]),
                channel_name,
                template,
                parameters,
            )
            tile_paths = _index_exported_tiles(written, template)
            self._cache[cache_key] = tile_paths

        tile_key = int(uv_tile["udim"]) if uv_tile.get("is_udim") else None
        source = tile_paths.get(tile_key)
        if source is None:
            available = ", ".join(
                "non-UDIM" if key is None else str(key)
                for key in sorted(tile_paths, key=lambda key: (-1 if key is None else key))
            )
            raise StackNodeExportError(
                f"Painter did not render UDIM {tile_key or '(none)'} for node "
                f"{asset['uid']}. Available outputs: {available or '(none)'}."
            )

        output = Path(asset["path"])
        output.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != output.resolve():
            shutil.copyfile(source, output)

    def _next_template(self):
        if self._temporary_dir is None:
            self._temporary_dir = tempfile.TemporaryDirectory(
                prefix="rizum_stack_node_export_"
            )
        self._sequence += 1
        return Path(self._temporary_dir.name) / f"node_{self._sequence}(_$udim).png"

    def _backend_instance(self):
        if self._backend is None:
            self._backend = _PainterStackNodeBackend()
        return self._backend


class _PainterStackNodeBackend:
    def __init__(self):
        try:
            import _substance_painter as native_painter
            import substance_painter as painter
        except ImportError as exc:
            raise StackNodeExportError(
                "Layer-stack node export must run inside Substance 3D Painter."
            ) from exc

        self._painter = painter
        native_export = getattr(native_painter, "export", None)
        self._export_stack_node_texture = getattr(
            native_export,
            "export_stack_node_texture",
            None,
        )
        if not callable(self._export_stack_node_texture):
            raise StackNodeExportError(
                "This Painter build does not provide stack-node texture export. "
                "Update Substance 3D Painter before using this plugin."
            )

    def export(self, uid, channel_name, template, parameters):
        node = self._painter.layerstack.get_node_by_uid(int(uid))
        channel_type = _resolve_channel_type(node, channel_name)

        # Adobe's own 12.1 engine suite uses this native entry point for true
        # node/mask UDIM exports; the public export module has no equivalent yet.
        result = self._painter.export.TextureExportResult(
            *self._export_stack_node_texture(
                int(uid),
                channel_type,
                str(template),
                json.dumps(parameters),
            )
        )
        if result.status != self._painter.export.ExportStatus.Success:
            raise StackNodeExportError(
                result.message or f"Painter failed to export layer-stack node {uid}."
            )
        return _flatten_texture_paths(result.textures)


def _resolve_channel_type(node, channel_name):
    if channel_name is None:
        return None

    stack = _call_or_attr(node, "get_stack")
    channels = _call_or_attr(stack, "all_channels", {})
    target = _normalized(channel_name)
    for channel_type in channels:
        if _normalized(getattr(channel_type, "name", channel_type)) == target:
            return channel_type
    available = ", ".join(
        str(getattr(channel_type, "name", channel_type)) for channel_type in channels
    )
    raise StackNodeExportError(
        f"Painter node {getattr(node, 'uid', '(unknown)')} has no channel "
        f"matching {channel_name}. Available channels: {available or '(none)'}."
    )


def _native_export_parameters(export_settings):
    width, height = [int(value) for value in export_settings["resolution"]]
    if width != height or width <= 0 or width & (width - 1):
        raise StackNodeExportError(
            "Painter node export requires a square power-of-two tile resolution; "
            f"received {width}x{height}."
        )
    return {
        "fileFormat": "png",
        "bitDepth": str(int(export_settings["bit_depth"])),
        "dithering": False,
        "paddingAlgorithm": str(export_settings["padding"]).casefold(),
        "dilationDistance": max(0, int(export_settings["dilation"])),
        "keepAlpha": bool(export_settings["keep_alpha"]),
        "sizeLog2": int(math.log2(width)),
    }


def _index_exported_tiles(written, template):
    paths = [Path(path) for path in written or []]
    if not paths:
        prefix = Path(template).name.split("(_$udim)", 1)[0]
        paths = list(Path(template).parent.glob(f"{prefix}*.png"))

    indexed = {}
    for path in paths:
        if not path.exists():
            continue
        match = _TRAILING_UDIM.search(path.stem)
        udim = int(match.group(1)) if match else None
        indexed[udim] = path
    if not indexed:
        raise StackNodeExportError(
            f"Painter reported a successful node export but wrote no PNGs for {template}."
        )
    return indexed


def _flatten_texture_paths(textures):
    if isinstance(textures, dict):
        return [path for paths in textures.values() for path in paths]
    if isinstance(textures, (list, tuple, set)):
        return list(textures)
    return [textures] if textures else []


def _call_or_attr(obj, name, default=None):
    value = getattr(obj, name, default)
    return value() if callable(value) else value


def _normalized(value):
    return "".join(
        character.casefold()
        for character in str(value or "")
        if character.isalnum()
    )
