# Rizum PT-to-PS Bridge — Phase 1 Implementation Plan

**Status**: prep docs complete. Plan refinement in progress (see handoff
log §0 below). M0 (scaffolding) not yet started.

**Dev branch**: `claude/refactor-sp-psd-export-Q3uVE`

**Current refinement branch**: `claude/plan-refine-m0-m5`

**Phase 1 scope**: feature parity with v1.1.8 + UDIM + color fidelity (A+B
mixed default) + selective sync-back. UXP plugin shipped as unpacked folder
with installer scripts. No `.ccx`, no smart objects, no live sync, no PS→SP
layer deletion.

**Phase 2 (out of scope, noted for future)**: `.ccx` packaging, smart-object
based live anchor refs, PS → SP layer deletion reconciliation, richer conflict
resolution UI.

---

## 0. Session handoff log

Read this first if you're a new agent picking up the project.

### What's done

- **`design.md`** (locked decisions): architecture split, UXP plugin
  distribution via External folder installer (no CC required), UDIM one-PSD-
  per-tile, naming follows user's SP export preset (auto-inserts `$udim`),
  export path from `alg.mapexport.exportPath()`, color fidelity via PS
  doc-level "Blend RGB Colors Using Gamma 1.0" toggle (method C rejected),
  layer structure mapping incl. clipping groups for sub-effects, flattened
  masks, anchor refs baked as normal raster, sync-back via file manifest
  (user-triggered, selective, non-destructive), metadata via layer-name
  suffix `‡<sp_uid>` + sidecar `<psdname>.rizum.json`.
- **`analysis.md`** (API audit): every `design.md §5–6` claim mapped to a
  real API call. SP Python covers everything except per-layer export,
  which goes through JS fallback `alg.mapexport.save` +
  `alg.mapexport.exportPath`. UXP covers most; three ops need `batchPlay`:
  PNG placement, layer mask add/fill, blend-gamma-1.0 toggle. Blend-gamma
  toggle is the color-fidelity win — validate at M3 start.
- **`plan.md`**: M0–M5 drafted, M3 already rewritten around blend-gamma.
  **This file's milestones are being refined right now** — pinning exact
  API calls to each task and tightening verify criteria.

### User's standing rules

- Chat summaries in Chinese, all file content in English
  (`rizum-claude.md`)
- Develop on `claude/refactor-sp-psd-export-Q3uVE` (or a sub-branch for
  isolated work). Merge to main when user says "commit to main"
- Never push to main without explicit permission
- `analysis.md`, `design.md`, `plan.md` are living — update when
  implementation uncovers new facts
- Update `- [x]` checkboxes in this file as tasks complete
- Style: surgical changes, no speculative scope, minimum code

### Key design choices you cannot silently change

1. **UXP plugin, not ExtendScript** on PS side; ships as unpacked folder
   copied to `%APPDATA%\Adobe\UXP\Plugins\External\` via installer scripts
2. **Python first** on SP side; JS fallback only where Python is absent
   (confirmed absences: `alg.mapexport.save`, `alg.mapexport.exportPath`)
3. **One PSD per UDIM tile**; filename from user's SP preset
4. **Color fidelity = blend-gamma 1.0 doc toggle** (primary) with per-mode
   LUT as fallback if UXP can't set the toggle
5. **Sub-effects inside a layer → PS clipping group**
6. **Masks flatten on export**; sync-back preserves old mask stack as
   hidden backup + new top mask
7. **Anchor refs bake to normal raster** (no locked read-only layer, no
   metadata)
8. **Sync is user-triggered**: Push button in UXP + Apply dialog in SP.
   Manifest JSON + PNGs in `<sp_project_dir>/_pt_sync_inbox/`
9. **Metadata**: `‡<sp_uid>` layer-name suffix + sidecar JSON (no XMP per
   layer — unreliable in UXP)
10. **Minimum PS 23.3** (UXP manifest v5 requirement)

### Where to resume

The current task is **this file's refinement**. Each milestone below needs:
- Specific API calls named (linking to `analysis.md §N.M`)
- Verification criteria tight enough that a pass/fail is objective
- Out-of-scope explicitly listed to prevent scope creep

Milestones M2 and M4 should be split:
- **M2a** minimal PSD build (pixel layers + blend mode + opacity + group
  nesting + metadata suffix)
- **M2b** masks + clipping sub-effects + sidecar JSON
- **M4a** UXP push side (panel UI + manifest write)
- **M4b** SP apply side (inbox watcher + diff dialog + resource import)

If refinement isn't done yet, finish it. If it's done, start **M0** —
scaffold the directory tree per §M0 and commit.

### Files to reference while working

- `design.md` — authoritative decisions
- `analysis.md` §1 (SP Python), §2 (SP JS), §3 (UXP), §4 (gaps), §6
  (color management), §7 (bake matrix), §8 (old-plugin patterns to port)
- `ps-export_Rizum v1.1.8/ps-export-Rizum/` — old plugin; `photoshop.js`
  + `footer.jsx` are the most useful references for action-descriptor
  sequences
- `pt-python-doc-md/substance_painter/` — SP Python docs
- `uxp-photoshop-main/src/pages/ps_reference/` — UXP docs

---

## Milestones

Each milestone ends with a verifiable artifact. Do not advance until the
verification passes.

### M0 — Scaffolding

**Input**: empty repo (except existing docs + reference material).
**Output**: directory tree + stub files, each importable/loadable without
error. No behavior yet.

- [ ] Create directory tree:
  ```
  sp_plugin/rizum_sp_to_ps/
    __init__.py           # registers with sp.ui on project load; empty hooks
    plugin.json           # SP plugin manifest (min_api_version, description)
    ui.py                 # PySide6 panel; stub render only
    exporter.py           # empty module
    blend_map.py          # SP→PS mapping constants only (table from analysis §3.6)
    compensation.py       # placeholder; unused unless M3 falls back to LUT
    udim.py               # udim_number(u, v) helper; nothing else
    metadata.py           # constants + uid-suffix regex only
    bridge.py             # JS fallback wrappers for mapexport.save/exportPath
    sync_inbox.py         # empty module
    settings.py           # sp.project.Metadata("Rizum") wrapper
  ps_plugin/
    manifest.json         # UXP v5 manifest, one panel entrypoint, fullAccess
    index.html            # panel shell; loads src/main.js
    src/
      main.js             # entrypoints.setup stub
      build-psd.js        # empty module
      sync-back.js        # empty module
      blend_map.js        # mirror of sp-side mapping constants
      metadata.js         # uid suffix helpers
      batchplay/
        place-png.js      # placeEvent recipe (ported from old footer.jsx §8.2)
        add-mask.js       # layerToMask port
        fill-solid.js     # fillSolidColour port
        blend-gamma.js    # set colorSettings rgbColorBlendGamma = 1.0
    styles.css            # minimal Spectrum CSS overrides
  installers/
    install-ps-plugin-windows.bat
    install-ps-plugin-mac.sh
    uninstall-ps-plugin-windows.bat
    uninstall-ps-plugin-mac.sh
  README.md               # end-user install instructions (3 steps)
  ```
- [ ] `sp_plugin/rizum_sp_to_ps/plugin.json`: set
      `min_api_version` to the SP version that ships Python layerstack API
      with effects support. The 0.3.4 Python API is the reference version
      used in `analysis.md` — pin `"min_api_version": "2.0.0"` (SP 10+)
      and document the reason in a leading comment in `__init__.py`
- [ ] `ps_plugin/manifest.json`:
      ```json
      { "manifestVersion": 5,
        "id": "com.rizum.pt-to-ps-bridge",
        "name": "Rizum PT to PS Bridge",
        "version": "2.0.0",
        "main": "index.html",
        "host": { "app": "PS", "minVersion": "23.3.0" },
        "entrypoints": [{ "type": "panel", "id": "rizumBridge",
                          "label": {"default": "Rizum PT Bridge"},
                          "minimumSize": {"width": 260, "height": 320} }],
        "requiredPermissions": {
          "localFileSystem": "fullAccess",
          "clipboard": "read"
        }
      }
      ```
- [ ] `sp_plugin/rizum_sp_to_ps/__init__.py`: register entry via
      `sp.event.DISPATCHER.connect(sp.event.ProjectEditionEntered, ...)`
      to show a "Rizum PT → PS" menu action wired to a no-op handler.
      Matches v1.1.8's "Send To" affordance (old `main.qml:23`).
- [ ] `ps_plugin/src/main.js`: implement `entrypoints.setup` with
      `panels.rizumBridge.create(rootNode)` that renders a single
      placeholder "Build from Painter" button. No click handler yet.
- **Verify**:
  - `python -c "import ast; ast.parse(open('sp_plugin/rizum_sp_to_ps/__init__.py').read())"` succeeds for every `.py` file
  - `node -e "JSON.parse(require('fs').readFileSync('ps_plugin/manifest.json'))"` succeeds
  - Load the SP plugin into Painter → "Rizum PT → PS" menu item appears
  - Load the UXP plugin via UDT → panel shows with placeholder button
  - `git log --oneline -1` shows the scaffolding commit

### M1 — SP-side traversal + export request generation

**Input**: M0 scaffolding + an SP project open.
**Output**: a `<project>_photoshop_export/` folder containing per-(material,
stack, channel, udim) subfolders, each with a full PNG set and a
`build_request.json` that the UXP plugin can consume in M2.

**In scope**: full traversal, per-layer/effect/mask export via JS bridge,
UDIM enumeration, bake-decision computation. **Not in scope**: compensation
LUT (M3), PSD construction (M2).

- [ ] `udim.py`: one function `udim_number(u: int, v: int) -> int`
      returning `1001 + u + 10*v`. Unit test with (0,0)=1001, (9,0)=1010,
      (0,1)=1011.
- [ ] `blend_map.py`: three constants —
      - `PS_REPRESENTABLE: dict[BlendingMode, str]` (SP enum → UXP
        BlendMode name, from `analysis.md §3.6`)
      - `BAKE_ALWAYS: set[BlendingMode]` (SignedAddition, InverseDivide,
        InverseSubtract, NormalMapCombine, NormalMapDetail,
        NormalMapInverseDetail, Replace)
      - `APPROXIMATE_IN_PRESERVE_MODE: dict[BlendingMode, str]` (Tint →
        HUE, Value → LUMINOSITY)
      - one function `policy(mode, export_mode) -> Literal["keep", "bake", "approximate"]`
- [ ] `metadata.py`:
      - `UID_SUFFIX_RE = re.compile(r"‡([0-9a-f]+)$")`
      - `make_ps_name(sp_name: str, sp_uid: int) -> str` → `f"{sp_name} ‡{sp_uid:x}"`
      - `parse_ps_name(ps_name: str) -> tuple[str, int | None]`
- [ ] `bridge.py`: wraps `sp.js.evaluate` with `export_layer_png(uid,
      channel, out_path, *, padding, dilation, bit_depth, keep_alpha,
      resolution)` and `project_export_path() -> str`. See `analysis.md
      §2.2` for exact JS string format.
- [ ] `exporter.py` — traversal (`analysis.md §1.1`):
      ```
      for ts in sp.textureset.all_texture_sets():
          for stack in ts.all_stacks():
              channels = stack.all_channels()  # Dict[ChannelType, Channel]
              uv_tiles = ts.all_uv_tiles() if ts.has_uv_tiles() else [None]
              for channel in channels:
                  for tile in uv_tiles:
                      build_one(ts, stack, channel, tile)
      ```
- [ ] `exporter.py` — per-layer walk via
      `sp.layerstack.get_root_layer_nodes(stack)` then recurse into
      `GroupLayerNode.sub_layers()`. For each node, branch on
      `node.get_type()` (`NodeType` enum) to decide handler. Fill/Paint
      layer → one PNG. Group → recurse. Content effects →
      `LayerNode.content_effects()`. Mask → if `has_mask()`, export the
      merged mask via `alg.mapexport.save([uid, "mask"], ...)`.
- [ ] `exporter.py` — bake decision per `blend_map.policy()` + the matrix
      in `analysis.md §7`. For bake cases, export `[effect_uid, channel]`;
      PNG file named `baked_<uid>.png`. For keep cases, export
      `[layer_uid, channel]`; file named `uid_<uid>.png`. Masks:
      `uid_<uid>_mask.png`.
- [ ] `exporter.py` — emit `build_request.json` schema:
      ```json
      {
        "rizum_version": "2.0.0",
        "sp_project_uuid": "<from sp.project.get_uuid()>",
        "texture_set": "MatName",
        "stack": "",
        "channel": "BaseColor",
        "udim": 1001,
        "width": 2048, "height": 2048,
        "bit_depth": 8,
        "color_channel": true,
        "psd_filename": "MatName_BaseColor.1001.psd",
        "export_mode": "bake_unsupported" | "preserve_all",
        "apply_blend_gamma_1": true,
        "layers": [
          {"sp_uid": "a3f7", "kind": "paint_layer", "name": "Base",
           "visible": true, "opacity": 1.0, "blend": "NORMAL",
           "png": "uid_a3f7.png",
           "mask": {"png": "uid_a3f7_mask.png"} | null,
           "sub_effects": [...]}
        ],
        "default_background": {"rgb": [128,128,255]} | null
      }
      ```
      Full schema in a fixture file to be cross-referenced by M2.
- [ ] `exporter.py` — default background for `normal` channel: emit
      `{"rgb":[128,128,255]}` so the PS side inserts a fill at the bottom
      (ported from old `photoshop.js:189-192`).
- [ ] Wire `ui.py` into the exporter. Minimal dialog: "Naming preset"
      dropdown (populated from `sp.export.list_resource_export_presets()`),
      padding checkbox, dilation slider 0–64, bit-depth dropdown
      (TextureSet value/8/16), "Color handling" dropdown (Bake unsupported
      / Preserve all), Export button.
- **Verify** on a test SP project with:
  - ≥ 3 top-level layers covering Normal, Multiply, SignedAddition modes
  - 2 UDIM tiles (1001, 1002)
  - 1 layer with a sub-effect stack (fill effect inside paint layer)
  - 1 layer with a mask
  - Both color channel (BaseColor) and data channel (Roughness)

  After export, the destination folder contains:
  - One `build_request.json` per (stack, channel, udim) — 4 files total
  - Every `png` field referenced in the JSON exists on disk
  - The SignedAddition layer appears as a `baked_<uid>.png` entry, not a
    `uid_<uid>.png` entry
  - The mask'd layer's entry has a non-null `mask` field
  - The sub-effect stack entry has a populated `sub_effects` array
  - Normal-channel JSON has `default_background.rgb == [128,128,255]`;
    BaseColor JSON has `default_background: null`

### M2 — UXP plugin: consume request → build PSD

- [ ] UXP panel with one button: "Build from Painter" (opens file dialog to
      `build_request.json`)
- [ ] Parse request → create PSD → for each entry:
      - raster layer (from PNG)
      - group (with mask)
      - clipping-group sub-effects
      - blend mode + opacity
      - layer mask from grayscale PNG
      - `rizum_sp_uid` metadata write (XMP + sidecar JSON)
- [ ] Save PSD at path specified by request
- **Verify**: run M1 bundle through M2; open resulting PSD in a human PS;
  visual result ≈ SP viewport for the "Bake unsupported modes" default
  policy. Manual visual diff is acceptable for this milestone.

### M3 — Color handling (blend-gamma + bake policy)

- [ ] At PSD creation in UXP, set document-level "Blend RGB Colors Using
      Gamma 1.0" via `batchPlay` (see `analysis.md §6.3`). **Validate
      first** that the action descriptor is honored by comparing a two-
      layer Multiply test PSD before/after
- [ ] If gamma toggle works: no per-layer pre-compensation needed for the
      PS-representable blend-mode set. Skip `compensation.py`
- [ ] If gamma toggle does not work: fall back to empirical per-mode
      pre-compensation LUT in `compensation.py`, calibrated from captured
      SP viewport vs PS output diffs
- [ ] Bake path (method A) in `exporter.py` for SP-only modes
      (SignedAddition/Tint/Value/NormalMap*/Inverse*), calling
      `alg.mapexport.save([effect_uid, channel], ...)` via bridge
- [ ] "Preserve all layers" toggle in UI bypasses bake; Tint→HUE,
      Value→LUMINOSITY, SignedAddition→LINEARDODGE with `[!]` prefix in
      the PS layer name
- **Verify**: composite image diff between SP viewport and built PSD for a
  test project with every PS-representable blend mode. Max per-pixel ΔE
  < 1.0 for editable layers; exact match on baked layers. "Preserve all
  layers" mode shows `[!]` prefixes only on SP-only modes.

### M4 — Sync-back (PS → SP)

- [ ] UXP panel: "Push to Painter" list + diff preview + mask-applied detection
- [ ] UXP writes manifest + PNGs to `<sp_project_dir>/_pt_sync_inbox/`
- [ ] SP `sync_inbox.py` watches inbox, shows toast, diff dialog, applies
      via embedded resource import + layer-stack mutation
- [ ] Conflict detection (baseline timestamp compare)
- **Verify**: end-to-end test:
  1. Export SP → build PSD
  2. Edit 2 layers in PS (one content, one apply-mask)
  3. Push to Painter, apply in SP
  4. Delete the inbox folder → reload `.spp` → content is still embedded and
     intact
  5. Modify the same layer in SP then push again from PS → conflict dialog appears

### M5 — Distribution

- [ ] `install-ps-plugin-windows.bat`: locate `%APPDATA%\Adobe\UXP\Plugins\External\`,
      copy `ps_plugin/` into it, patch `plugins.json`
- [ ] `install-ps-plugin-mac.sh`: equivalent for macOS
- [ ] Matching uninstallers
- [ ] `README.md` with three-step install instructions, tested on a clean
      Windows and macOS VM without Creative Cloud app installed
- [ ] Manifest `host.minVersion = "23.3.0"` (UXP manifest v5 floor)
- **Verify**: on a machine with only Photoshop ≥ 23.3 (no CC Desktop, no
  Adobe ID logged in), run installer → start PS → plugin appears in
  Plugins panel → full round-trip works

---

## Cross-cutting checks

Run at the end of each milestone:

- **Code volume**: does any single file exceed ~400 lines? If so, audit for
  speculative abstractions per `rizum-claude.md §2`
- **Behavioral parity**: does this milestone regress any v1.1.8 feature?
  (UDIM is added, nothing is subtracted)
- **Dependencies**: no new pip packages beyond what SP Python ships with; no
  npm packages in UXP plugin beyond what `uxp-photoshop-main` shows as
  idiomatic

---

## Open tasks before starting M0

Before writing any implementation code:

1. Populate `analysis.md` — deep-read SP Python modules (`layerstack`,
   `textureset`, `export`, `resource`, `ui`, `event`, `js`) and confirm every
   capability in `design.md §5–6` has a concrete API call
2. Deep-read `uxp-photoshop-main/reference-ps.js` for: PSD creation, layer
   add/group/clip, mask set, blend-mode enum, XMP read/write, file I/O,
   modal scope
3. For every capability that turns out to be missing, decide JS-fallback
   (SP side) or reject-scope (PS side)
4. Refine this plan: collapse or split milestones as needed, pin specific
   API calls to each task

Only after step 4 does M0 start.
