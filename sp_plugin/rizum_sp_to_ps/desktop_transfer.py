"""Execute explicit desktop mappings across Painter and Photoshop."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from . import exporter, photoshop_automation
from .blend_map import DIRECT_BLEND_MODES


SCHEMA_VERSION = 3
REQUEST_TYPE = "desktop_transfer"


class DesktopTransferError(RuntimeError):
    """Raised when a desktop transfer cannot be applied safely."""


@dataclass(frozen=True)
class PhotoshopLayer:
    """A Photoshop layer rendered by the mapper, or a folder of them."""

    name: str
    kind: str
    png: Path | None
    mask_png: Path | None
    blend_mode: str
    opacity: float
    visible: bool
    children: tuple["PhotoshopLayer", ...] = ()
    color: tuple[float, float, float] | None = None

    def assets(self):
        yield from (path for path in (self.png, self.mask_png) if path is not None)
        for child in self.children:
            yield from child.assets()


@dataclass(frozen=True)
class PainterImportItem:
    """One mapped Photoshop layer or folder and its Painter destination."""

    order: int
    layer: PhotoshopLayer
    target_uid: int
    target_kind: str
    insertion: str

    @property
    def name(self):
        return self.layer.name


@dataclass(frozen=True)
class PhotoshopExportItem:
    """One Painter node insertion requested for the selected Photoshop document."""

    order: int
    name: str
    source_uid: int
    source_kind: str
    target_layer_id: int | None
    target_index_path: tuple[int, ...]
    target_name: str
    target_kind: str
    insertion: str
    blend_mode: str
    opacity: float
    visible: bool


@dataclass(frozen=True)
class TransferPlan:
    """Validated bidirectional work requested by one desktop Apply action."""

    manifest_path: Path
    project_uuid: str
    project_path: str
    texture_set: str
    stack: str
    channel: str
    photoshop_document: dict
    photoshop_context: dict
    painter_imports: tuple[PainterImportItem, ...]
    photoshop_exports: tuple[PhotoshopExportItem, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TransferResult:
    """Summary returned after both host handoffs are prepared."""

    imported_count: int
    exported_count: int
    names: tuple[str, ...]
    warnings: tuple[str, ...]
    photoshop_launch: photoshop_automation.PhotoshopScriptLaunch | None = None

    @property
    def count(self):
        return self.imported_count + self.exported_count


def load_transfer_plan(manifest_path):
    """Read and validate a desktop transfer manifest without importing Painter."""
    path = Path(manifest_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DesktopTransferError(f"Could not read transfer manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DesktopTransferError(f"Transfer manifest is not valid JSON: {path}") from exc

    root = _mapping(payload, "transfer manifest")
    if root.get("schema_version") != SCHEMA_VERSION:
        raise DesktopTransferError("Transfer manifest uses an unsupported schema_version.")
    if root.get("request_type") != REQUEST_TYPE:
        raise DesktopTransferError("JSON file is not a desktop_transfer manifest.")

    painter_record = _mapping(root.get("painter"), "painter")
    photoshop_record = _mapping(root.get("photoshop"), "photoshop")
    context = _mapping(painter_record.get("context"), "painter.context")
    document = _mapping(painter_record.get("document", {}), "painter.document")
    photoshop_document = _mapping(
        photoshop_record.get("document", {}),
        "photoshop.document",
    )
    photoshop_context = _mapping(
        photoshop_record.get("context", {}),
        "photoshop.context",
    )
    texture_set = _required_text(context, "texture_set", "painter.context")
    channel = _required_text(context, "channel", "painter.context")
    stack = _optional_text(context.get("stack"))

    transfers = root.get("transfers")
    if not isinstance(transfers, list) or not transfers:
        raise DesktopTransferError("Transfer manifest contains no mapped layers.")

    painter_imports = []
    photoshop_exports = []
    for index, record in enumerate(transfers):
        direction, item = _transfer_item(record, index, path.parent)
        if direction == "photoshop_to_painter":
            painter_imports.append(item)
        else:
            photoshop_exports.append(item)
    return TransferPlan(
        manifest_path=path,
        project_uuid=_optional_text(document.get("uuid")),
        project_path=_optional_text(document.get("path")),
        texture_set=texture_set,
        stack=stack,
        channel=channel,
        photoshop_document=dict(photoshop_document),
        photoshop_context=dict(photoshop_context),
        painter_imports=tuple(painter_imports),
        photoshop_exports=tuple(photoshop_exports),
        warnings=tuple(str(value) for value in root.get("warnings") or ()),
    )


def apply_transfer_manifest(manifest_path, settings=None, painter=None):
    """Execute local Painter work and prepare any Photoshop-side handoff."""
    plan = load_transfer_plan(manifest_path)
    if painter is None:
        try:
            import substance_painter as painter
        except ImportError as exc:
            raise DesktopTransferError(
                "Desktop transfers must be applied inside Substance 3D Painter."
            ) from exc
    _validate_project(plan, painter.project)
    launcher = _prepare_photoshop_transfer(plan, settings or {})
    result = apply_transfer_plan(plan, painter)
    return TransferResult(
        imported_count=result.imported_count,
        exported_count=len(plan.photoshop_exports),
        names=tuple(
            [item.name for item in plan.painter_imports]
            + [item.name for item in plan.photoshop_exports]
        ),
        warnings=plan.warnings + result.warnings,
        photoshop_launch=launcher,
    )


def apply_transfer_plan(plan, painter):
    """Apply only the Photoshop-to-Painter portion as one history entry."""
    _validate_project(plan, painter.project)
    resolved = [
        _resolve_target(item, plan, painter.layerstack)
        for item in plan.painter_imports
    ]

    resources = {}
    for item in plan.painter_imports:
        for path in item.layer.assets():
            if path not in resources:
                resources[path] = _import_texture(path, painter.resource)

    warnings = []
    # The desktop Apply action is one user intent; grouping every layerstack edit
    # keeps both recomputation and Painter history aligned with that decision.
    if resolved:
        modification = painter.layerstack.ScopedModification(
            "PT Bridge: import Photoshop layers"
        )
    else:
        modification = _NullContext()
    with modification:
        for item, target_node, channel_type, channel_is_color in resolved:
            position = _insertion_position(item, target_node, painter.layerstack)
            target = _InsertTarget(painter, channel_type, channel_is_color, resources, warnings)
            _insert_photoshop_layer(item.layer, position, target)

    return TransferResult(
        imported_count=len(plan.painter_imports),
        exported_count=0,
        names=tuple(item.name for item in plan.painter_imports),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class _InsertTarget:
    painter: object
    channel_type: object
    channel_is_color: bool
    resources: dict
    warnings: list


def _insert_photoshop_layer(layer, position, target):
    layerstack = target.painter.layerstack
    channel_type = target.channel_type
    resources = target.resources
    warnings = target.warnings
    if layer.kind == "group":
        # A Photoshop folder stays a folder so its layers remain editable in Painter.
        node = layerstack.insert_group(position)
    else:
        node = layerstack.insert_fill(position)
        node.active_channels = {channel_type}
        node.set_source(channel_type, _layer_source(layer, target))
    node.set_name(layer.name)
    node.set_visible(layer.visible)
    node.set_opacity(max(0.0, min(100.0, layer.opacity)) / 100.0, channel_type)

    blending_mode = _resolve_blending_mode(layerstack, layer.blend_mode)
    if blending_mode is None:
        warnings.append(
            f"{layer.name}: Photoshop blend mode {layer.blend_mode!r} "
            "has no direct Painter equivalent; Normal was kept."
        )
    else:
        node.set_blending_mode(blending_mode, channel_type)

    if layer.mask_png is not None:
        node.add_mask(layerstack.MaskBackground.Black)
        mask_position = layerstack.InsertPosition.inside_node(
            node,
            layerstack.NodeStack.Mask,
        )
        mask_fill = layerstack.insert_fill(mask_position)
        mask_fill.set_name("Photoshop Mask")
        mask_fill.set_source(None, resources[layer.mask_png].identifier())

    previous = None
    for child in layer.children:
        child_position = (
            layerstack.InsertPosition.inside_node(node, layerstack.NodeStack.Substack)
            if previous is None
            else layerstack.InsertPosition.below_node(previous)
        )
        previous = _insert_photoshop_layer(child, child_position, target)
    return node


def _layer_source(layer, target):
    if layer.color is None:
        return target.resources[layer.png].identifier()
    colormanagement = target.painter.colormanagement
    # Photoshop fill colours are document (sRGB-encoded) values. Colour
    # channels keep that encoding; data channels take the values as-is.
    space = (
        colormanagement.GenericColorSpace.sRGB
        if target.channel_is_color
        else colormanagement.GenericColorSpace.Working
    )
    return colormanagement.Color(*layer.color, space)


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        return False


def _prepare_photoshop_transfer(plan, settings):
    if not plan.photoshop_exports:
        return None

    context = {
        "texture_set": plan.texture_set,
        "stack": plan.stack,
        "channel": plan.channel,
    }
    target_udim = plan.photoshop_context.get("udim")
    if target_udim is not None:
        context["udim"] = target_udim

    output_dir = plan.manifest_path.parent / "painter_to_photoshop"
    rendered = exporter.export_desktop_nodes(
        output_dir / "assets",
        context,
        [format(item.source_uid, "x") for item in plan.photoshop_exports],
        settings,
    )
    if len(rendered) != len(plan.photoshop_exports):
        raise DesktopTransferError(
            "Painter did not render every mapped Photoshop transfer source."
        )

    layers = []
    for item, asset in zip(plan.photoshop_exports, rendered):
        layers.append(
            {
                "order": item.order,
                "name": item.name,
                "source_uid": format(item.source_uid, "x"),
                "source_kind": item.source_kind,
                "png": asset["png"],
                "mask_png": asset.get("mask_png"),
                "target_layer_id": item.target_layer_id,
                "target_index_path": list(item.target_index_path),
                "target_name": item.target_name,
                "target_kind": item.target_kind,
                "insertion": item.insertion,
                "blend_mode": item.blend_mode,
                "opacity": item.opacity,
                "visible": item.visible,
            }
        )

    request_path = output_dir / "photoshop_transfer.json"
    exporter.write_json_atomic(
        request_path,
        {
            "schema_version": 1,
            "request_type": "painter_to_photoshop_transfer",
            "document": plan.photoshop_document,
            "context": plan.photoshop_context,
            "layers": layers,
        },
    )
    return photoshop_automation.write_photoshop_transfer_launcher(request_path)


def _transfer_item(value, fallback_order, manifest_dir):
    record = _mapping(value, f"transfers[{fallback_order}]")
    source = _mapping(record.get("source"), f"transfers[{fallback_order}].source")
    target = _mapping(record.get("target"), f"transfers[{fallback_order}].target")
    direction = _required_text(
        record,
        "direction",
        f"transfers[{fallback_order}]",
    )
    hosts = {
        "photoshop_to_painter": ("photoshop", "substance_painter"),
        "painter_to_photoshop": ("substance_painter", "photoshop"),
    }
    if direction not in hosts:
        raise DesktopTransferError(
            f"Transfer {fallback_order + 1} uses unsupported direction {direction!r}."
        )
    expected_source, expected_target = hosts[direction]
    if source.get("host") != expected_source or target.get("host") != expected_target:
        raise DesktopTransferError(
            f"Transfer {fallback_order + 1} hosts do not match {direction}."
        )

    insertion = _required_text(record, "insertion", f"transfers[{fallback_order}]")
    target_kind = _required_text(
        target,
        "kind",
        f"transfers[{fallback_order}].target",
    )
    if insertion not in {"after", "inside"}:
        raise DesktopTransferError(
            f"Transfer {fallback_order + 1} uses unsupported insertion {insertion!r}."
        )
    if insertion == "inside" and "group" not in target_kind.casefold():
        raise DesktopTransferError(
            f"Transfer {fallback_order + 1} can only insert inside a group."
        )

    if direction == "painter_to_photoshop":
        target_layer_id = (
            _decimal_id(target.get("id"), fallback_order)
            if _optional_text(target.get("id"))
            else None
        )
        target_index_path = _index_path(target.get("index_path"), fallback_order)
        if target_layer_id is None and not target_index_path:
            raise DesktopTransferError(
                f"Transfer {fallback_order + 1} has no Photoshop layer id or position."
            )
        logical_path = _optional_text(source.get("path")).replace("\\", "/")
        name = logical_path.rsplit("/", 1)[-1] if logical_path else "Painter Layer"
        return direction, PhotoshopExportItem(
            order=_integer(record.get("order"), fallback_order),
            name=name,
            source_uid=_uid(source.get("id"), fallback_order),
            source_kind=_required_text(
                source,
                "kind",
                f"transfers[{fallback_order}].source",
            ),
            target_layer_id=target_layer_id,
            target_index_path=target_index_path,
            target_name=_optional_text(target.get("path")).replace("\\", "/").rsplit("/", 1)[-1],
            target_kind=target_kind,
            insertion=insertion,
            blend_mode=_optional_text(source.get("blend_mode")) or "normal",
            opacity=_number(source.get("opacity"), 100.0),
            visible=source.get("visible") is not False,
        )

    return direction, PainterImportItem(
        order=_integer(record.get("order"), fallback_order),
        layer=_photoshop_layer(source, manifest_dir, f"transfers[{fallback_order}].source"),
        target_uid=_uid(target.get("id"), fallback_order),
        target_kind=target_kind,
        insertion=insertion,
    )


def _photoshop_layer(source, manifest_dir, label):
    kind = "group" if _optional_text(source.get("kind")) == "group" else "layer"
    logical_path = _optional_text(source.get("path")).replace("\\", "/")
    children = source.get("children") or []
    if not isinstance(children, list):
        raise DesktopTransferError(f"Transfer {label}.children must be a list.")
    color = _color(source.get("color"), label)
    return PhotoshopLayer(
        name=logical_path.rsplit("/", 1)[-1] if logical_path else "Photoshop Layer",
        kind=kind,
        color=color,
        png=None if kind == "group" or color is not None
        else _asset_path(source.get("png"), manifest_dir, "source PNG"),
        mask_png=_asset_path(source.get("mask_png"), manifest_dir, "source mask PNG", required=False),
        blend_mode=_optional_text(source.get("blend_mode")) or "normal",
        opacity=_number(source.get("opacity"), 100.0),
        visible=source.get("visible") is not False,
        children=tuple(
            _photoshop_layer(_mapping(child, f"{label}.children[{index}]"), manifest_dir, f"{label}.children[{index}]")
            for index, child in enumerate(children)
        ),
    )


def _validate_project(plan, project):
    if not _call_or_attr(project, "is_open", False):
        raise DesktopTransferError("Open the Painter project used by this transfer.")
    if not _call_or_attr(project, "is_in_edition_state", False):
        raise DesktopTransferError("Painter project is still loading or not editable.")

    current_uuid = _call_or_attr(project, "get_uuid")
    if plan.project_uuid and current_uuid is not None:
        if str(current_uuid) != plan.project_uuid:
            # A stale manifest must never mutate another open project merely
            # because an old node UID happens to resolve there as well.
            raise DesktopTransferError(
                "Transfer belongs to a different Painter project. Reopen Bridge "
                "from the intended project."
            )
        return

    current_path = _optional_text(_call_or_attr(project, "file_path"))
    if plan.project_path and current_path:
        if _normalized_path(current_path) != _normalized_path(plan.project_path):
            raise DesktopTransferError(
                "Transfer belongs to a different Painter project. Reopen Bridge "
                "from the intended project."
            )


def _resolve_target(item, plan, layerstack):
    try:
        node = layerstack.get_node_by_uid(item.target_uid)
    except (TypeError, ValueError) as exc:
        raise DesktopTransferError(
            f"Painter target for {item.name!r} no longer exists. Refresh Bridge and map again."
        ) from exc

    stack = _call_or_attr(node, "get_stack")
    material = _call_or_attr(stack, "material")
    texture_set_name = _optional_text(material.name)
    stack_name = _optional_text(_call_or_attr(stack, "name"))
    if texture_set_name != plan.texture_set or stack_name != plan.stack:
        raise DesktopTransferError(
            f"Painter target for {item.name!r} moved outside the mapped stack. "
            "Refresh Bridge and map again."
        )

    channel_type = _matching_channel_type(stack, plan.channel)
    channel = _call_or_attr(stack, "all_channels", {}).get(channel_type)
    return item, node, channel_type, bool(_call_or_attr(channel, "is_color", True))


def _matching_channel_type(stack, expected):
    target = _normalized(expected)
    channels = _call_or_attr(stack, "all_channels", {})
    for channel_type in channels:
        if _normalized(getattr(channel_type, "name", channel_type)) == target:
            return channel_type
    available = ", ".join(
        str(getattr(channel_type, "name", channel_type)) for channel_type in channels
    )
    raise DesktopTransferError(
        f"Mapped Painter channel {expected!r} is unavailable. "
        f"Available channels: {available or '(none)'}."
    )


def _insertion_position(item, target_node, layerstack):
    if item.insertion == "after":
        return layerstack.InsertPosition.below_node(target_node)

    children = list(_call_or_attr(target_node, "sub_layers", []))
    if children:
        # Desktop group drops append visually; targeting the final child keeps
        # Painter's insertion order identical to the mapping preview.
        return layerstack.InsertPosition.below_node(children[-1])
    # Folder children live in the Substack; Content only accepts effects.
    return layerstack.InsertPosition.inside_node(
        target_node,
        layerstack.NodeStack.Substack,
    )


def _import_texture(path, resource):
    try:
        return resource.import_project_resource(str(path), resource.Usage.TEXTURE)
    except Exception as exc:
        raise DesktopTransferError(f"Painter could not import texture: {path}") from exc


def _resolve_blending_mode(layerstack, photoshop_mode):
    normalized = _normalized(photoshop_mode)
    aliases = {
        _normalized(ps_name): painter_name
        for painter_name, ps_name in DIRECT_BLEND_MODES.items()
    }
    aliases.update({"hue": "Tint", "luminosity": "Value"})
    painter_name = aliases.get(normalized)
    return getattr(layerstack.BlendingMode, painter_name, None) if painter_name else None


def _asset_path(value, manifest_dir, label, required=True):
    text = _optional_text(value)
    if not text:
        if required:
            raise DesktopTransferError(f"Transfer is missing its {label} path.")
        return None
    path = Path(text)
    if not path.is_absolute():
        path = manifest_dir / path
    path = path.resolve()
    if not path.is_file():
        raise DesktopTransferError(f"Transfer {label} does not exist: {path}")
    return path


def _uid(value, index):
    text = _optional_text(value)
    try:
        return int(text, 16)
    except (TypeError, ValueError) as exc:
        raise DesktopTransferError(
            f"Transfer {index + 1} has an invalid Painter node UID: {text!r}."
        ) from exc


def _decimal_id(value, index):
    text = _optional_text(value)
    try:
        return int(text, 10)
    except (TypeError, ValueError) as exc:
        raise DesktopTransferError(
            f"Transfer {index + 1} has an invalid Photoshop layer id: {text!r}."
        ) from exc


def _color(value, label):
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or len(value) != 3
        or not all(isinstance(item, (int, float)) for item in value)
    ):
        raise DesktopTransferError(f"Transfer {label}.color must be three numbers.")
    return tuple(max(0.0, min(1.0, float(item))) for item in value)


def _index_path(value, index):
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, int) and item >= 0 for item in value):
        raise DesktopTransferError(
            f"Transfer {index + 1} has an invalid Photoshop layer position: {value!r}."
        )
    return tuple(value)


def _mapping(value, label):
    if not isinstance(value, dict):
        raise DesktopTransferError(f"Transfer {label} must be a JSON object.")
    return value


def _required_text(mapping, key, label):
    value = _optional_text(mapping.get(key))
    if not value:
        raise DesktopTransferError(f"Transfer {label} is missing {key}.")
    return value


def _optional_text(value):
    return str(value).strip() if value is not None else ""


def _integer(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _number(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _normalized(value):
    return "".join(
        character.casefold()
        for character in str(value or "")
        if character.isalnum()
    )


def _normalized_path(value):
    return os.path.normcase(os.path.abspath(str(value)))


def _call_or_attr(obj, name, default=None):
    value = getattr(obj, name, default)
    return value() if callable(value) else value
