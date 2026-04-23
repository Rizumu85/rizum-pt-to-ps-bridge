# API Analysis — Skeleton

**Status**: skeleton. Fill each section by reading the named source and
writing down (a) the exact API call(s) we will use, (b) their signature and
return type, (c) gotchas, (d) gaps where no API exists.

Populating this doc **must** happen before `plan.md` milestones start.
Every design claim in `design.md §5–6` needs a line item here that points
to a real API call — otherwise the design claim is unverified.

---

## 1. SP Python API

Source: `pt-python-doc-md/substance_painter/`.

### 1.1 Document / project structure traversal
_Modules to read: `project.md`, `textureset/index.md`, `textureset/textureset.md`,
`textureset/stack.md`, `textureset/channel.md`, `layerstack/navigation.md`._

- [ ] How to enumerate texture sets
- [ ] How to enumerate stacks per texture set
- [ ] How to enumerate channels per stack
- [ ] How to walk layer tree (root → nested)
- [ ] Per-node: uid, name, enabled, kind (paint/fill/group/instanced)

### 1.2 Layer blend mode + opacity
_`layerstack/navigation.md`._

- [ ] `get_blending_mode(channel)` — confirmed present
- [ ] Opacity accessor — locate
- [ ] Per-channel override detection

### 1.3 Effects (fill / paint / filter / generator / levels / anchor)
_`layerstack/index.md`, `layerstack/layereffect/`._

- [ ] Enumerate effects on a node (channel effect stack)
- [ ] Enumerate effects on a mask
- [ ] Distinguish fill vs paint vs filter vs generator vs levels vs anchor
- [ ] Per-effect: uid, enabled, blend mode, opacity, source/params
- [ ] Anchor reference: how to identify + resolve to source node

### 1.4 Mask structure
_`layerstack/navigation.md`, `layerstack/layereffect/`._

- [ ] Detect whether a node has a mask
- [ ] Walk mask effect stack
- [ ] Set effect `visible` (for the hidden-backup pattern)
- [ ] Insert new fill effect at top of mask stack

### 1.5 UDIM / UV tile iteration
_`textureset/uvtile.md`._

- [ ] Enumerate UV tiles of a texture set
- [ ] Tile ID / UDIM number
- [ ] Export path tokenization (`$udim`)

### 1.6 Per-layer/per-effect export to PNG
_`export.md`._

- [ ] Export a full channel
- [ ] Export a single layer's channel contribution (isolate one node)
- [ ] Export a single effect's output (isolate one effect)
- [ ] Export a mask
- [ ] Bit depth, padding, dilation parameters
- [ ] UDIM-aware export filename templates

### 1.7 Resource import (embedded)
_`resource.md`, `source/` subfolder._

- [ ] `import_session_resource` or equivalent
- [ ] `import_project_resource` with `embedded=True` flag
- [ ] How to assign an imported resource to a paint layer's content
- [ ] How to assign to a mask's fill effect

### 1.8 Layer-stack mutation
_`layerstack/edition.md`._

- [ ] Insert paint layer at position
- [ ] Insert fill layer at position
- [ ] Set effect visibility
- [ ] Reorder effects
- [ ] Delete effect

### 1.9 UI (PySide6)
_`ui.md`._

- [ ] Register docked panel
- [ ] Add menu action / toolbar button
- [ ] Access main window for modal dialog parenting

### 1.10 Events / file watching
_`event.md`, `async_utils.md`._

- [ ] Project-open / project-close events
- [ ] QFileSystemWatcher availability (Qt included with SP)
- [ ] Layer-change events (for `last_modified` bookkeeping)

### 1.11 Logging & errors
_`logging.md`, `exception.md`._

- [ ] Info/warn/error log sinks
- [ ] Exception types

---

## 2. SP JS API (fallback — only if Python is missing something)

Source: `pt-python-doc-md/substance_painter/js.md` + `javascript-doc/`.

### 2.1 Capabilities confirmed present in JS but missing in Python
_Populate after §1 is done._

### 2.2 JS invocation bridge
- [ ] How to call `alg.*` from Python (`substance_painter.js.evaluate`?)
- [ ] Return-value marshalling
- [ ] Error propagation

---

## 3. UXP Photoshop API

Source: `uxp-photoshop-main/reference-ps.js`, `uxp-photoshop-main/src/`.

### 3.1 PSD creation & save
- [ ] `app.documents.add(...)` signature
- [ ] `doc.saveAs` / `doc.save` for PSD
- [ ] Color mode, bit depth, ICC profile control
- [ ] Open existing PSD

### 3.2 Layer creation
- [ ] Raster (`ArtLayer`) from PNG file
- [ ] Layer group (`LayerSet`)
- [ ] Clipping mask toggle (`grouped` / `clipping mask`)
- [ ] Layer ordering / move-to-end / move-to-beginning
- [ ] Set opacity, visibility

### 3.3 Blend modes
- [ ] `BlendMode` enum values actually supported in UXP (may differ from ExtendScript)
- [ ] PASSTHROUGH for groups
- [ ] Gap list: which SP modes have no UXP mapping

### 3.4 Layer masks
- [ ] Add layer mask from PNG (grayscale)
- [ ] Detect whether layer has a mask
- [ ] `Apply Layer Mask` detection (pre-sync-back diagnostic)

### 3.5 Metadata (XMP / per-layer info)
- [ ] XMP packet read/write on document
- [ ] Per-layer custom metadata: supported method in UXP
- [ ] Sidecar-JSON fallback policy

### 3.6 Panel UI
_`uxp-photoshop-main/reference-spectrum.js`, `reference-html.js`, `reference-css.js`._

- [ ] Panel registration via manifest
- [ ] Spectrum Web Components used: `sp-button`, `sp-checkbox`, etc.
- [ ] Event model inside modal execution

### 3.7 File I/O + local FS
- [ ] UXP FS API: `require('fs')` or `uxp.storage.localFileSystem`
- [ ] Write PNG + JSON to a path outside the plugin sandbox
- [ ] Hash computation (sha1) availability

### 3.8 Modal execution scope
- [ ] `executeAsModal` wrapper for all doc-mutating calls
- [ ] Long-running export: batching + progress

### 3.9 Document / layer change detection
_For sync-back "last changed" tracking._

- [ ] Event or poll-hash strategy
- [ ] Timestamp / dirty flag per layer

---

## 4. Gaps & decisions

_Fill once §1–3 are populated._

### 4.1 Capabilities missing from chosen API stack
### 4.2 JS fallback scope (SP side)
### 4.3 Design-doc revisions required (if any)

---

## 5. Open questions to resolve during reading

- Does SP Python expose enough of the effect stack for a sub-effect to be
  exported as an isolated PNG? If not, sub-effect clipping-group mapping
  (`design.md §5.2`) may need to fall back to JS or be reduced to
  flatten-per-layer.
- Does UXP support writing per-layer XMP metadata reliably across PS 23,
  24, 25, 26? If not, sidecar JSON becomes the only source of truth.
- What is the exact gamma behavior of PS blend modes in UXP (vs
  ExtendScript legacy)? Needed to calibrate `compensation.py`.
- UXP panel + modal execution: can the sync-back panel show a diff
  dialog while a modal export is running? If not, split into two
  separate user actions.
