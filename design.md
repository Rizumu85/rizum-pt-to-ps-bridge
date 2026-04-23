# Rizum PT-to-PS Bridge — Design Decisions

Source of truth for design choices agreed in the pre-implementation discussion.
Subject to revision only if `analysis.md` later reveals an API constraint that
makes one of these infeasible — otherwise these are locked.

---

## 1. Architecture split

| Side | Language | Framework |
|---|---|---|
| Substance Painter plugin | **Python** (SP Python API) | PySide6 for UI |
| Photoshop plugin | **UXP plugin** (`.ccx`/unpacked folder) | UXP JS + Spectrum Web Components |
| Transport (both directions) | **File-based** (PNG + JSON manifest in a known folder) | — |

**Rule**: Python first on SP side. Fall back to the legacy SP JS API (`alg.*`)
only if a specific capability is genuinely absent from Python. JS fallback will
be invoked via `substance_painter.js.evaluate` (or equivalent) and the list of
such calls kept explicit in `analysis.md §2`.

**No sockets, no daemons, no background polling beyond a single
`QFileSystemWatcher`.** The user triggers every cross-boundary action.

---

## 2. Photoshop plugin distribution

Must install on **any Photoshop ≥ 23 regardless of Creative Cloud status,
Adobe ID, or license legitimacy.**

Method: unpacked UXP plugin folder written directly into
`%APPDATA%\Adobe\UXP\Plugins\External\` (Windows) or
`~/Library/Application Support/Adobe/UXP/Plugins/External/` (macOS), with
`plugins.json` patched to register the plugin.

Ship a `.zip` release containing:

```
rizum-pt-to-ps-bridge-vX.Y.Z.zip
├── sp_plugin/rizum_sp_to_ps/          # copy to SP Plugins dir manually
├── ps_plugin/                         # unpacked UXP plugin
├── install-ps-plugin-windows.bat
├── install-ps-plugin-mac.sh
├── uninstall-ps-plugin-windows.bat
├── uninstall-ps-plugin-mac.sh
└── README.md
```

Optional later: add `.ccx` packaging for CC-enabled users (not Phase 1).

---

## 3. UDIM handling

**One PSD per UDIM tile.** Output filename pattern:

```
<MatName>_<StackName>_<Channel>.<UDIM>.psd
```

Each tile's PSD has an identical layer structure (same `rizum_sp_uid` on
corresponding layers across tiles). Export progress UI reports per tile.

---

## 4. Color fidelity strategy

Default: **"Bake unsupported modes"** (A+B mixed).

- PS-representable blend modes (Normal, Multiply, Screen, LinearDodge,
  LinearBurn, Darken, Lighten, ColorBurn, ColorDodge, Difference, Exclusion,
  Overlay, SoftLight, HardLight, VividLight, LinearLight, PinLight, Color,
  Saturation, PassThrough[group-only]) → kept as editable PS layers with
  per-layer gamma pre-compensation (method B) so PS's gamma-encoded blend
  math reproduces SP's linear-space result.
- SP-only modes (`SignedAddition`, `InverseDivide`, `InverseSubtract`, `Tint`,
  `Value`, `NormalMapCombine`, `NormalMapDetail`, `NormalMapInverseDetail`,
  `Replace`) → that layer **plus everything below it in its enclosing stack**
  is baked to a single Normal raster layer (method A). Remaining layers
  above stay editable.

Toggle: **"Preserve all layers"** (B-only).

- Every SP layer → exactly one PS layer, no baking.
- Unrepresentable modes map to the closest PS equivalent and get a `[!]`
  prefix in the PS layer name; entries logged to the export report.
- Explicitly accepts color drift on those specific layers.

Option C (rewrite SP viewport shader) was considered and **rejected**: SP layer
blending happens inside the Substance Engine, not in any user-controllable
shader. The view shader sees already-composited channel textures.

---

## 5. Layer structure mapping

### 5.1 Top-level layers

| SP | PS |
|---|---|
| Paint layer | Raster layer, blend mode mapped, opacity mapped |
| Fill layer | Raster layer (fill baked to PNG), blend mode mapped |
| Group/folder | PS layer group, blend mode mapped; PassThrough folder → PASS THROUGH |
| Layer mask (SP) | PS layer mask on the generated PS layer/group |

### 5.2 Sub-effects inside a layer's channel

Each SP sub-effect (fill/paint) becomes its own PS layer inside a **clipping
group** rooted at a base silhouette layer:

```
PS group "<sp_layer_name>"     (group mask = SP layer's combined mask)
  ├─ effect_n  (clipped to base, blend mode = sub-effect's blend mode)
  ├─ …
  ├─ effect_1  (clipped to base)
  └─ base      (SP layer's underlying content, silhouette source for clipping)
```

Filter/generator/level sub-effects (non-fill/paint) → baked into a static
raster sibling.

### 5.3 Sub-effects inside a mask

**Flattened** to a single grayscale PNG used as the PS layer mask. PS has no
native concept of stacked mask effects. Loss of editable stack is declared in
the export report.

### 5.4 Anchor point references

Each anchor reference is **baked in place** as a regular Normal-mode raster
layer. No special locking, no hidden metadata beyond the standard
`rizum_sp_uid`. Treated identically to any other baked layer on sync-back.

---

## 6. Sync-back protocol (PS → SP)

**User-initiated, selective, non-destructive.** No live sync.

### 6.1 Push (UXP side)

UXP panel lists every PS layer tagged with `rizum_sp_uid`:

```
☑ DiffuseBase         [changed 2m ago]
☑ Scratches_Overlay   [changed 14s ago]
☐ Rust_Fill           [unchanged]
⊘ [!baked] anchor_L3  cannot sync
```

User checks what to push + clicks **Push to Painter**. UXP writes to
`<sp_project_dir>/_pt_sync_inbox/<psdname>_<timestamp>/`:

- `manifest.json` (schema below)
- `uid_<uid>.png` for each selected layer

### 6.2 Apply (SP side)

Python plugin watches the inbox with `QFileSystemWatcher`. New manifest →
non-blocking toast. User opens the diff dialog, reviews each update with
old/new thumbnails, clicks Apply. Python imports PNGs as **embedded
session resources** (`resource.import_session_resource(...)` or equivalent)
and mutates the layer stack accordingly. Manifest renamed to
`manifest.applied.json`; PNGs left on disk.

**PNGs are transport only.** Once applied, data lives inside `.spp`. Deleting
the inbox folder is always safe.

### 6.3 Mask sync-back

**Non-destructive, implicit** (no per-layer opt-in needed):

- SP's existing mask effect stack → every effect set `visible=false` as a
  hidden backup
- PS's flat mask → inserted as a single new fill effect at the **top** of the
  SP mask stack, visible

User can recover the original stack by deleting the top effect and re-enabling
the hidden ones.

### 6.4 "Apply Layer Mask" in PS

If UXP detects a layer that had a mask in the original SP export but no mask
channel in PS (user ran `Apply Layer Mask`), the sync panel flags it:

```
☑ DiffuseBase   [changed 2m]   ⚠ mask was applied in PS
```

Apply logic on SP side:

1. Split incoming RGBA into RGB + A
2. RGB → paint layer content (SP's existing content stack becomes hidden
   backup, new fill on top — same pattern as §6.3)
3. A → new top-of-mask-stack fill; original mask stack hidden as backup

Avoids the double-mask pitfall.

### 6.5 Manifest schema

```json
{
  "psd_file": "absolute/path/to.psd",
  "timestamp": "ISO-8601",
  "udim": 1001,
  "baseline_export_timestamp": "ISO-8601",
  "layers": [
    {
      "uid": "<sp_uid>",
      "png": "uid_<sp_uid>.png",
      "mode": "update",
      "ps_name": "…",
      "ps_hash": "sha1:…",
      "mask_applied_in_ps": false,
      "include_mask": false
    }
  ],
  "new_layers": [
    {
      "png": "new_<guid>.png",
      "ps_name": "…",
      "insert_after_uid": "<sp_uid>",
      "blend_mode": "Multiply",
      "opacity": 80
    }
  ],
  "deleted_uids": []
}
```

### 6.6 Confirmed sync rules

1. Per-layer selective push, not global
2. New layers in PS can be inserted as new paint layers in SP; position chosen
   by "insert after" picker in UXP panel (default: nearest tagged neighbor)
3. PS → SP deletion is **not** supported in Phase 1. `deleted_uids` stays
   empty. User deletes in SP manually if wanted.
4. Mask sync-back is implicit & non-destructive per §6.3
5. Conflict detection: if SP's layer `last_modified` > manifest's
   `baseline_export_timestamp`, dialog asks: use PS / keep SP / keep both

---

## 7. Metadata schema

Stored per-PS-layer in XMP, mirrored in `<psdname>.rizum.json` next to the PSD
(XMP on PSD layers is inconsistent across PS versions; the JSON is the
authoritative fallback).

```json
{
  "rizum_sp_uid": "<uid>",
  "rizum_sp_kind": "layer" | "fill_effect" | "paint_effect" |
                    "baked_effect" | "anchor_ref" | "flattened_mask",
  "rizum_sync_direction": "both" | "sp_to_ps_only"
}
```

`baked_effect` and `anchor_ref` get `sync_direction: "sp_to_ps_only"` —
UXP panel renders them as "cannot sync" entries.

---

## 8. Open design questions

Revisit as `analysis.md` gets filled in. Current list:

- B-method pre-compensation formula: needs to be validated against each PS
  blend mode's actual gamma behavior. Known-clean for Multiply/Screen/linear
  ops; uncertain for Overlay/SoftLight/HardLight.
- Where exactly to write metadata on PS side: PSD XMP packet vs layer
  XMP vs sidecar-only. Depends on UXP API coverage.
- SP Python API surface for layer-stack mutation (creating paint layers,
  inserting effects, setting mask-effect visibility) — assumed present,
  must confirm in `analysis.md §1`.
- Whether `substance_painter.export` can target a single sub-effect or only
  full channels. Affects how we render per-layer PNGs.
