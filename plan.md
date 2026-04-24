# Rizum PT-to-PS Bridge — Phase 1 Implementation Plan

**Status**: draft. Must be refined after `analysis.md` is populated by a deep
read of SP Python docs (`pt-python-doc-md/`) and UXP reference
(`uxp-photoshop-main/reference-ps.js` + co).

**Dev branch**: `claude/refactor-sp-psd-export-Q3uVE`

**Phase 1 scope**: feature parity with v1.1.8 + UDIM + color fidelity (A+B
mixed default) + selective sync-back. UXP plugin shipped as unpacked folder
with installer scripts. No `.ccx`, no smart objects, no live sync, no PS→SP
layer deletion.

**Phase 2 (out of scope, noted for future)**: `.ccx` packaging, smart-object
based live anchor refs, PS → SP layer deletion reconciliation, richer conflict
resolution UI.

---

## Milestones

Each milestone ends with a verifiable artifact. Do not advance until the
verification passes.

### M0 — Scaffolding

- [ ] Create branch `claude/refactor-sp-psd-export-Q3uVE`
- [ ] Directory skeleton:
  ```
  sp_plugin/rizum_sp_to_ps/
    __init__.py           # entry + UI registration
    plugin.json           # SP plugin manifest
    ui.py                 # PySide6 export dialog + settings panel
    exporter.py           # traverse stack → emit PNGs + PSD-build request
    blend_map.py          # SP BlendingMode → PS + bake decision matrix
    compensation.py       # method-B gamma pre-compensation per blend mode
    udim.py               # UDIM tile enumeration
    metadata.py           # rizum_sp_uid schema + sidecar JSON IO
    sync_inbox.py         # QFileSystemWatcher + manifest apply
  ps_plugin/
    manifest.json         # UXP plugin manifest
    src/
      main.js             # panel entry
      build-psd.js        # consume SP request → build PSD
      sync-back.js        # push-to-painter panel
      blend_map.js        # mirror of sp-side map for sync-back
      metadata.js         # rizum_sp_uid read/write
  installers/
    install-ps-plugin-windows.bat
    install-ps-plugin-mac.sh
    uninstall-ps-plugin-windows.bat
    uninstall-ps-plugin-mac.sh
  README.md               # end-user install instructions
  ```
- **Verify**: `ls` returns the tree; `git log --oneline -1` on branch shows
  the scaffolding commit.

### M1 — SP-side document traversal & export request generation

- [ ] `exporter.py` walks texture sets × stacks × channels × layer tree
      using Python API (JS fallback only where proven necessary per
      `analysis.md`)
- [ ] Per layer record: uid, name, kind, blend mode, opacity, visibility,
      mask presence, sub-effect list, UDIM tile list
- [ ] Decide per layer: kept-editable vs baked (per §4 of `design.md`)
- [ ] Emit one request bundle per (material, stack, channel, UDIM tile):
      - directory of PNGs (`uid_<uid>.png`, `uid_<uid>_mask.png`, `baked_<uid>.png`)
      - `build_request.json` describing PS layer tree
- **Verify**: run on an SP project with ≥ 3 layers (one Normal, one Multiply,
  one SignedAddition), 2 UDIM tiles, at least one sub-effect stack;
  inspect the emitted `build_request.json` + PNG set; confirm schema matches
  what `build-psd.js` will consume.

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
