# Recommended Implementation: User Channel Export & UDIM Solo Fallback

## 1. User Channel Export Hardening

Current multi-candidate fallback in `_export_asset_png` is correct but can be
tightened: when `documentStructure()` or `channelIdentifiers()` returns a
resolved identifier, prefer it as the primary candidate and only fall through
other spellings if it produces transparent output.

### `bridge.py` — add raw-identifier export helper

```python
def export_layer_png_raw(uid, raw_channel, out_path, **kwargs):
    """Export using the exact engine channel string, no identifier mapping."""
    script = build_mapexport_save_script_raw(uid, raw_channel, out_path, **kwargs)
    return _evaluate_json(script)


def build_mapexport_save_script_raw(uid, raw_channel, out_path, **kwargs):
    target = [int(uid), str(raw_channel)]
    options = {
        "padding": kwargs.get("padding", "Infinite"),
        "dilation": int(kwargs.get("dilation", 0)),
        "bitDepth": int(kwargs.get("bit_depth", 8)),
        "keepAlpha": bool(kwargs.get("keep_alpha", False)),
    }
    resolution = kwargs.get("resolution")
    if resolution is not None:
        options["resolution"] = [int(resolution[0]), int(resolution[1])]
    return (
        f"alg.mapexport.save({json.dumps(target)}, "
        f"{json.dumps(str(Path(out_path)))}, {json.dumps(options, sort_keys=True)})"
    )
```

### `exporter.py` — try resolved identifier first

In `_export_asset_png`, reorder candidates so the request's resolved
`channel_identifier` (which comes from `documentStructure()` already) is tried
before derived candidates:

```python
def _export_asset_png(asset, export_settings, channel_candidates):
    # Prefer the request-level resolved identifier
    primary = channel_candidates[0] if channel_candidates else asset["channel"]
    fallbacks = [c for c in channel_candidates if c != primary]
    candidates = _dedupe_text([asset["channel"], primary, *fallbacks])
    # ... rest unchanged
```

## 2. Python Solo-Export Fallback for UDIM Per-Layer PNG

New module: `sp_plugin/rizum_sp_to_ps/solo_export.py`

```python
"""Per-layer channel export via temporary visibility isolation.

Fallback for UDIM projects where alg.mapexport.save cannot target a single tile.
"""

from __future__ import annotations

import substance_painter as sp


def export_layer_channel_for_tile(target_uid, channel_type, uv_tiles, export_dir,
                                  export_config):
    """Export a single layer's contribution for specific UV tiles.

    Hides all other layers, exports via export_project_textures with a uvTiles
    filter, then restores all visibility inside ScopedModification undo groups.
    """
    target_node = sp.layerstack.get_node_by_uid(int(target_uid))
    stack = target_node.get_stack()
    ts_name = stack.material().name()
    stack_name = stack.name() or ""
    root_path = f"{ts_name}/{stack_name}" if stack_name else ts_name

    all_nodes = _collect_descendants(
        sp.layerstack.get_root_layer_nodes(stack)
    )

    # Snapshot current visibility
    saved = {}
    for node in all_nodes:
        try:
            saved[node.uid()] = node.is_visible()
        except Exception:
            continue

    try:
        with sp.layerstack.ScopedModification("Solo layer export"):
            for node in all_nodes:
                if node.uid() != target_node.uid():
                    try:
                        node.set_visible(False)
                    except Exception:
                        pass
            try:
                target_node.set_visible(True)
            except Exception:
                pass

        result = sp.export.export_project_textures({
            "exportPath": str(export_dir),
            "exportList": [{
                "rootPath": root_path,
                "filter": {
                    "uvTiles": [[int(t["u"]), int(t["v"])] for t in uv_tiles],
                },
            }],
            "exportParameters": [{
                "parameters": {
                    "paddingAlgorithm": export_config.get("padding", "transparent"),
                    "dilationDistance": int(export_config.get("dilation", 0)),
                },
            }],
        })
        return result
    finally:
        with sp.layerstack.ScopedModification("Restore visibility"):
            for node in all_nodes:
                try:
                    node.set_visible(saved.get(node.uid(), True))
                except Exception:
                    pass


def _collect_descendants(roots):
    nodes = []
    for root in roots:
        nodes.append(root)
        if hasattr(root, "sub_layers"):
            nodes.extend(_collect_descendants(root.sub_layers()))
        if hasattr(root, "content_effects"):
            nodes.extend(root.content_effects())
        if hasattr(root, "mask_effects"):
            nodes.extend(root.mask_effects())
    return nodes
```

### Usage gate

Call solo export only when **all** conditions are true:

1. `texture_set.has_uv_tiles()` is True
2. The build request requires per-tile per-layer PNGs
3. The user explicitly opts into UDIM per-layer mode (or it's the only path)

For non-UDIM projects, keep the existing `alg.mapexport.save` path — it is
faster, doesn't mutate visibility, and doesn't risk thumbnail regeneration.

### Integration point in `exporter.py`

In `_export_asset_png`, add a branch before the JS fallback loop:

```python
def _export_asset_png(asset, export_settings, channel_candidates,
                      uv_tile=None):
    # Non-UDIM or single-tile-not-requested: use fast JS bridge
    if uv_tile is None or not uv_tile.get("is_udim"):
        return _export_asset_png_js(asset, export_settings, channel_candidates)

    # UDIM single-tile: use Python solo export fallback
    from . import solo_export
    solo_export.export_layer_channel_for_tile(
        asset["uid"],
        asset["channel"],
        [uv_tile],
        Path(asset["path"]).parent,
        export_settings,
    )
```

## 3. Design Decisions

| Decision | Rationale |
|---|---|
| **Two `ScopedModification` blocks** (solo + restore) | Two undo entries: user can undo restore separately if needed. Single block would roll back both silently. |
| **`try/finally` still required** | `ScopedModification` provides undo grouping, not exception safety. Visibility state must be restored even if export raises. |
| **Gate behind `has_uv_tiles()`** | Non-UDIM projects should never pay the visibility-mutation cost. |
| **Keep `alg.mapexport.save` as primary path** | It is the documented, non-mutating, fast path. Solo export is only a UDIM fallback. |
| **Custom label as primary channel identifier** | When `channelIdentifiers(stackPath)` returns `SCol`, the JS engine recognizes it. Using the label avoids the ambiguity of guessing `user0` vs `user 0`. |
