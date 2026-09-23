# API Review: Cross-Cutting Observations

All findings sourced from `reference-docs/pt-python-doc-md/substance_painter/` and
`reference-docs/pt-javascript-doc-html/`. Specific file:line references inline.

---

## 1. Engine Suspension During Export

**`application.md:49-64`** — `disable_engine_computations()` context manager.

```python
with application.disable_engine_computations():
    # texture/viewport updates paused
```

Currently unused. For solo export or any bulk layerstack mutation, wrapping in
this context manager prevents Painter from recomputing textures and refreshing
the viewport after every individual visibility toggle. This is the
application-level equivalent of `ScopedModification` for the engine.

**Recommendation:** The solo export fallback in `recommended-implementation.md`
should wrap the visibility mutation block in `disable_engine_computations()`.
This directly addresses the thumbnail-regeneration risk flagged in the earlier
findings.

---

## 2. `normal_map_format` for Already-Open Projects — Resolved

**`plan.md` Direction 1 has an open item:**

> Decide how to populate `normal_map_format` for already-open Painter projects,
> because the local docs do not expose a direct getter.

Python API: `project.Settings` accepts `normal_map_format` at creation time
(`project.md:184-186`), but there is no `project.get_normal_map_format()` on an
already-open project.

JS API: the `alg.project.settings` namespace exists but the local doc file
wasn't expanded. `alg.texturesets.structure(textureSetName)` returns per-texture-set
data including `"normalMapBitmap"` with `"colorSpace": "DataColorSpace_Auto"`,
but this is the mesh map's color space interpretation, not the project-level
normal format enum.

Python `colormanagement.NormalColorSpace` (`colormanagement.md:234-246`) has:
- `NormalXYZRight` — OpenGL
- `NormalXYZLeft` — DirectX

But there's no getter to ask "which one is this project using?"

**Recommendation:** Add `alg.project.settings` JS docs to the reference set
for definitive answer. If unavailable there, the most reliable inference path is:
read a normal-channel resource's color space via `SourceBitmap.get_color_space()`
on a fill layer that uses a normal map, and map `NormalXYZRight` → OpenGL,
`NormalXYZLeft` → DirectX. Fall back to a one-time user prompt saved in
`project.Metadata` (see §3).

---

## 3. Project-Scoped Persistent Settings

**`project.md:522-580`** — `project.Metadata(context)` class.

```python
metadata = sp.project.Metadata("rizum-pt-to-ps-bridge")
metadata.set("last_export_preset", "PBR Metallic Roughness")
metadata.set("normal_map_format", "OpenGL")
```

Data survives inside the `.spp` file. Supports `bool`, `int`, `float`, `str`,
`list`, `dict`. Context-scoped so plugins don't collide.

Currently the plugin uses `alg.settings` (global Painter prefs) for padding,
dilation, bit depth, and the Photoshop executable path. Per-project settings
(export preset choice, normal map format override, last-used naming preset)
belong in `project.Metadata`, not global settings.

**Recommendation:**
- Keep `alg.settings` for: Photoshop path, launch-Photoshop toggle.
- Move to `project.Metadata`: last export preset name, normal map format
  (once resolved), last-used channel filter, dilation/padding defaults.
- On export, read `project.Metadata` first, fall back to `alg.settings` for
  migration from older plugin versions.

---

## 4. `TextureStateEvent.cache_key` — Baseline Change Detection

**`event.md:117-145`** — `TextureStateEvent`.

```python
sp.event.DISPATCHER.connect(sp.event.TextureStateEvent, callback)
# event.action: ADD | UPDATE | REMOVE
# event.stack_id, event.tile_indices, event.channel_type, event.cache_key
```

Cache keys are **persistent across sessions** (`event.md:126`). The current
build request sets `"baseline_cache_key": None` everywhere (`exporter.py:384`).

The old sync-back design needed cache keys to detect manual Painter edits. That
path is deprecated, but cache keys still have value: they can be written into
`build_request.json` as a **fingerprint of the exported stack state**. Later,
the Photoshop panel could show "Painter stack unchanged since export" or "Painter
stack has been modified" by comparing the stored cache key against a fresh read.

**Recommendation:** Populate `baseline_cache_key` from the current
`TextureStateEvent.cache_key` for the stack/channel being exported. Low cost,
no host mutation, and enables future integrity checks. The event's
`set_cache_key_invalidation_throttling_period()` defaults to 500ms minimum, so
cache keys are stable enough for this use.

Implementation: subscribe to `TextureStateEvent` once at plugin startup with a
weak reference. Maintain an in-memory dict of `(stack_id, tile, channel_type) →
cache_key` updated by each event. On export, read the current cache key from
this dict rather than querying synchronously.

---

## 5. `is_in_edition_state()` Gate

**`project.md:145-152`** — `project.is_in_edition_state()`.

Returns `True` when the project is "ready to work with." All layerstack mutation
and export operations should be gated behind this check. Currently the plugin
only checks `project.is_open()`.

**Recommendation:** Before starting any export, call
`project.is_in_edition_state()`. If `False`, show an in-panel message:
"Project is still loading or in a non-editable state." This prevents errors
from racing project load.

---

## 6. `execute_when_not_busy()` — Deferred Work Scheduling

**`project.md:103-108`** — `project.execute_when_not_busy(callback)`.

Schedules a callback to run when Painter is not busy (not exporting, baking,
or in a non-edition state). `is_busy()` is the polling equivalent.
`BusyStatusChanged` event fires on transitions.

**Recommendation:** If the user triggers export while Painter is busy (e.g.
another export is running, baking is in progress), use
`execute_when_not_busy()` to defer the export rather than failing. This is
especially useful for the "Export and Build in Photoshop" one-click path.

---

## 7. `async_utils.StopSource` — Native Cancellation

**`async_utils.md:1-29`** — `StopSource` class.

```python
stop = sp.async_utils.StopSource()
# pass to async operations
stop.request_stop()    # signal cancellation
stop.stop_requested()  # poll
```

The current progress dialog has a Cancel button that sets a flag checked between
requests (`ExportCancelled` exception). `StopSource` is Painter's native
cancellation primitive and integrates with its async infrastructure.

**Recommendation:** Not urgent for Phase 1 since the existing `ExportCancelled`
pattern works. Keep `StopSource` in mind for a future async export rewrite where
individual PNG writes could be cancelled mid-flight through Painter's own
cancellation plumbing.

---

## 8. Color Management Intelligence

**`colormanagement.md`** — Multiple color space enums beyond the obvious:

| Enum | Purpose | Relevance |
|---|---|---|
| `GenericColorSpace.sRGB` | sRGB-encoded color data | BaseColor, Emissive, Diffuse |
| `GenericColorSpace.Working` | Linear working space | Most channel data internally |
| `GenericColorSpace.Raw` | No conversion | Pass-through data |
| `DataColorSpace.Data` | Unsigned normalized/float | Metallic, Roughness, Height |
| `DataColorSpace.DataSigned` | Signed -1..1 stored as 0..1 | Normal maps (raw storage) |
| `NormalColorSpace.NormalXYZRight` | OpenGL normal | Normal channel interpretation |
| `NormalColorSpace.NormalXYZLeft` | DirectX normal | Normal channel interpretation |
| `LegacyColorSpace.Linear` | Legacy linear sRGB | Older projects |
| `LegacyColorSpace.sRGB` | Legacy sRGB | Older projects |

The current `_channel_role()` function (`exporter.py:535-545`) uses a simple
name-based heuristic: `normal` → `"normal"`, `opacity/alpha` → `"opacity"`,
`User*` → `"user"`, `is_color` → `"color"`, else `"data"`.

A more precise approach: read the channel's actual color space from
`SourceBitmap.get_color_space()` on a fill layer that writes to this channel.
If the source's color space is `DataColorSpace.Data` or `DataColorSpace.DataSigned`,
the channel is definitively data. If it's `GenericColorSpace.sRGB`, it's color.
This is especially useful for custom shaders where the channel role isn't
obvious from the name.

**Recommendation:** Not Phase 1. The current name-based heuristic covers
standard PBR channels correctly. Add a note in `analysis.md` that per-channel
color space introspection via `SourceBitmap.get_color_space()` is available
for future fidelity work.

---

## 9. `SourceBitmap.get_color_space()` — Normal Map Orientation Detection

**`source/bitmap.md:46-50`** — `get_color_space()` returns
`NormalColorSpace` for normal maps.

If a fill layer uses a normal map as a source, `source.get_color_space()`
returns `NormalColorSpace.NormalXYZRight` (OpenGL) or
`NormalColorSpace.NormalXYZLeft` (DirectX). This is one way to infer the
project's normal map format on an already-open project (see §2).

**Recommendation:** For the `normal_map_format` open question, add a
heuristic: iterate fill layers in the first texture set, find one with a normal
channel source, call `get_color_space()`, and map the result. Fall back to
`project.Metadata` or user prompt.

---

## 10. `ChannelType` Enum Goes to User15

**`textureset/index.md:100`** — Python `ChannelType` enum:

```
User0, User1, User2, User3, User4, User5, User6, User7,
User8, User9, User10, User11, User12, User13, User14, User15
```

JS API docs only list `user0`–`user7` in the `save()` valid map names.
The Python API is newer and supports 16 user channels.

Current `bridge.py` `channel_identifier()` handles all via `startswith("User")`
→ `.lower()`, so no code change needed. But the JS `save()` may reject
`user8`–`user15` on older Painter builds. The multi-candidate fallback
already handles this gracefully (tries, fails silently, moves to next).

**Recommendation:** Add a comment in `bridge.py` noting the JS/Python
channel count discrepancy. No code change required.

---

## 11. JS `alg.texturesets.structure()` — Per-Texture-Set Detail

**`alg.texturesets.html:1334-1555`** — `structure(textureSetName)` returns:

```javascript
{
  "additionalAmbientOcclusionMapBlending": "...",
  "additionalMaps": [{ "urlToBitmapRes": "...", "usage": "..." }],
  "additionalNormalMapBlending": "...",
  "normalMapBitmap": { "colorSpace": "...", "uid": 431, "urlToBitmapRes": "..." },
  "paddingMode": "DataPaddingMode_Dilation3D",
  "resolutionLog2": [11, 11],
  ...
}
```

This is richer than `documentStructure()` for mesh-map details. It exposes
the mesh map URLs (baked maps), padding mode, and resolution in log2.

**Recommendation:** Not needed for Phase 1 traversal (Python API covers it).
Useful if the future desktop bridge wants to display mesh map provenance
without opening the project in Painter.

---

## 12. `alg.texturesets.addChannel / editChannel / removeChannel`

**`alg.texturesets.html:180-993`** — JS API for channel CRUD.

The JS `addChannel` takes a channel identifier string (from
`channelIdentifiers()`), a format string (e.g. `"L8"`), and an optional label
for user channels. This confirms the JS channel type strings match the
`channelIdentifiers()` return values — the same ones used in `save()`.

**Recommendation:** No action. Confirms the channel identifier resolution
logic is consistent with how Painter's own JS API names channels.

---

## 13. `LayerStacksModelDataChanged` Event

**`event.md:194-218`** — Fires on every layerstack change.

The design explicitly says no background polling. An event-driven refresh
(via `DISPATCHER.connect`) is not polling — it fires only when something
actually changes. However, during painting, this event fires extremely
frequently and the callback could still cause UI jank.

**Recommendation:** Keep the current design of user-triggered refresh only.
If the target picker needs to stay in sync with the layerstack, use
`LayerStacksModelDataChanged` with a debounce (update UI only after 2 seconds
of inactivity). This is a Phase 2 optimization, not Phase 1.

---

## 14. `resource.import_project_resource()` and the Deprecated Inbox

**`resource.md:287-288`** — `import_project_resource(file_path, resource_usage, name, group)`.

This is the API the deprecated inbox/apply path used. The plan correctly
deprecated it due to 4K thumbnail stalls and crashes.

**Recommendation:** No action. Confirms the deprecation was based on a real
API path with known host issues.

---

## 15. `project.ProjectWorkflow` Enum

**`project.md:303-311`**:

```python
class ProjectWorkflow:
    Default              # no UDIM
    TextureSetPerUVTile  # legacy UDIM (one TS per tile)
    UVTile               # modern UDIM (one TS with multiple tiles)
```

Currently the plugin detects UDIM per-texture-set via `texture_set.has_uv_tiles()`.
The project-level workflow tells us which UDIM variant is in use, which affects
how texture sets map to UV tiles.

**Recommendation:** Store `ProjectWorkflow` in the build request metadata.
If `TextureSetPerUVTile`, each texture set already corresponds to one UV tile
and the per-tile export problem is naturally solved. If `UVTile`, the solo
export fallback is needed.

---

## 16. Missing JS Docs for `alg.project.settings`

The local JS docs include `alg.project.settings.html` in the namespace listing
but the file was not expanded/readable. The Python `project.Settings` is for
project *creation*. The JS `alg.project.settings` might expose *current* project
settings including `normal_map_format`.

**Recommendation:** Add `alg.project.settings.html` to the reference docs
if available from a live Painter install (Help → Scripting Documentation →
JavaScript API → alg.project.settings). This is the most likely place for a
`normal_map_format` getter.

---

## 17. Solidity of the Current Approach

After reading all available API surface:

| Concern | Status |
|---|---|
| User channel identifiers | Covered — multi-candidate fallback handles all documented forms |
| UDIM per-layer PNG | Gap confirmed — `save()` has no tile param; solo export fallback is the only path |
| `normal_map_format` for open projects | No direct getter found in Python or expanded JS docs; `alg.project.settings` is the unchecked candidate |
| Color fidelity metadata | `colormanagement` enums provide precise channel classification beyond name heuristics |
| Engine suspension during export | `disable_engine_computations()` exists but unused — should wrap solo export |
| Persistent per-project settings | `project.Metadata` exists but unused — better than `alg.settings` for project-scoped prefs |
| Baseline change detection | `TextureStateEvent.cache_key` exists but unused — populate the currently-None field |
| Edit-state safety | `is_in_edition_state()` exists but unchecked — gate all export operations |
| Cancellation | Current `ExportCancelled` pattern works; `StopSource` available for future async rewrite |
| No missing API for core Phase 1 flow | The JS bridge + Python traversal covers everything needed |
