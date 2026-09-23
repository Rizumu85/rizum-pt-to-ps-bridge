# Deprecated Automatic Sync-Back Design

Archived from `design.md`. This automatic Photoshop-to-Painter inbox was
implemented experimentally through `0.1.46` and abandoned after host testing
showed thumbnail stalls, viewport slowdown, and crashes. It is kept only as
the record of why return transfers must stay explicit.

### 6.4 Deprecated automatic inbox design

The notes below describe the earlier automatic sync-back design that was
implemented experimentally through `0.1.46`, then superseded by the manual
export workflow above after Painter host testing showed unacceptable
performance and crash risk.

#### Historical 6.1 Push (UXP side)

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

Implementation note for the first write-out slice: selection is automatic.
Only layers whose normalized diff status is `changed` are exported. Unchanged
layers are omitted, and Painter apply remains disabled until the inbox writer
is validated.

#### Historical 6.2 Apply (SP side)

Python plugin watches the inbox with `QFileSystemWatcher`. New manifest →
non-blocking toast. User opens the diff dialog, reviews each update with
old/new thumbnails, clicks Apply. Python imports PNGs as **embedded project
resources** (`resource.import_project_resource(..., Usage.TEXTURE)`) and
mutates the layer stack accordingly. Manifest renamed to
`manifest.applied.json`; PNGs may remain on disk for audit/debugging, but the
applied data lives inside the `.spp`.

**PNGs are transport only.** Once applied, data lives inside `.spp`. Deleting
the inbox folder is always safe.

Implementation note for the first Painter-side sync slice: the Painter panel
only scans and validates pending push manifests. It reports manifest count,
target texture set/stack/channel/UDIM, pending layer updates, and missing PNGs.
It does not import resources or mutate the layer stack until inbox discovery is
validated in the host.

Implementation note for the first apply slice: applying is still intentionally
minimal and user-triggered. The panel applies only the newest valid manifest
and imports each PNG as a project `Usage.TEXTURE`. After `0.1.43` host testing
showed that inserting a Fill effect inside an existing target node can crash
Painter during viewport refresh, the safer validation strategy is to insert a
standalone Fill layer above the target node and set that layer's source to the
incoming PNG/channel. This keeps the original node internals untouched. A full
diff dialog, conflict detection, mask reconciliation, and automatic watcher are
still later M4 work.

Host validation then showed that even the standalone Fill-layer path is too
heavy for the current 4K payload: Painter can remain in thumbnail generation,
viewport navigation becomes unusably slow, and deleting the generated layer can
crash. Until a safer import/apply strategy is designed, the Painter panel must
not mutate the project from the inbox button. It may validate pending manifests
and PNGs, but actual resource import and layer-stack mutation are disabled.

#### Historical 6.3 Mask sync-back

**Non-destructive, implicit** (no per-layer opt-in needed):

- SP's existing mask effect stack → every effect set `visible=false` as a
  hidden backup
- PS's flat mask → inserted as a single new fill effect at the **top** of the
  SP mask stack, visible

User can recover the original stack by deleting the top effect and re-enabling
the hidden ones.

#### Historical 6.4 "Apply Layer Mask" in PS

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

#### Historical 6.5 Manifest schema

```json
{
  "psd_file": "absolute/path/to.psd",
  "timestamp": "ISO-8601",
  "texture_set": "Body",
  "stack": "",
  "channel": "BaseColor",
  "udim": 1001,
  "normal_map_format": "OpenGL",
  "baseline_cache_key": 123456789,
  "baseline_export_timestamp": "ISO-8601",
  "layers": [
    {
      "uid": "<sp_uid>",
      "channel": "BaseColor",
      "png": "uid_<sp_uid>.png",
      "mode": "update",
      "ps_name": "…",
      "ps_hash": "sha1:…",
      "baseline_cache_key": 123456789,
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

#### Historical 6.6 Confirmed sync rules

1. Per-layer selective push, not global
2. New layers in PS can be inserted as new paint layers in SP; position chosen
   by "insert after" picker in UXP panel (default: nearest tagged neighbor)
3. PS → SP deletion is **not** supported in Phase 1. `deleted_uids` stays
   empty. User deletes in SP manually if wanted.
4. Mask sync-back is implicit & non-destructive per §6.3
5. Conflict detection: SP Python docs do not expose per-layer
   `last_modified`. Store baseline `TextureStateEvent.cache_key` values per
   stack/channel/UDIM tile when exporting; if the current cache key differs
   at apply time, show a conservative conflict warning for affected incoming
   layers and ask: use PS / keep SP / keep both.

### 7.4 Deprecated automatic sync-back matching

The matching rules below are historical notes from the attempted automatic
Photoshop-to-Painter push path. They are not part of the active Phase 1 manual
export workflow.

1. UXP reads every PS layer, matches suffix regex → gets `sp_uid`
2. Cross-references sidecar JSON for `sp_kind` and `sync_direction`
3. `sync_direction == "sp_to_ps_only"` layers marked "⊘ cannot sync"
4. SP-side `sync_inbox.py` uses `sp_uid` from manifest to find the node
   via `sp.layerstack.get_node_by_uid(int(uid, 16))`

The first M4 implementation is preview-only. **Push to Painter** asks the user
to select the `.rizum.json` sidecar, scans the active Photoshop document, and
shows matched/missing/new-layer categories. It must not export PNGs or write
`_pt_sync_inbox` files until this matching report is validated in Photoshop.

The preview may also show mask and diff status. Diff status is informational
until sidecar `baseline_hash` values are populated. Mask status is best-effort:
Photoshop layer-mask state is queried when possible, but a failed query should
produce `unknown` instead of blocking the preview.

Baseline hashes are written during PSD build from the source PNG payloads that
created Photoshop raster layers. Group records do not get baseline hashes
because they have no direct pixel payload. Until current Photoshop layer pixels
are exported and hashed, Push preview should report baseline-bearing records as
`current_hash_pending` rather than claiming changed/unchanged.

Sidecar JSON reads/writes should run outside Photoshop `executeAsModal`.
However, normalized pixel baseline hashing opens source PNG payloads as
temporary Photoshop documents, so that open/read/close sequence must run inside
`executeAsModal`. Current Photoshop layer pixel reads also require modal scope
in the user's Photoshop runtime.

Push preview should not depend solely on the sidecar already containing
`baseline_hash`. If a raster record has `asset_path` but no hash, preview may
compute a temporary baseline hash from the source PNG and report the source as
`asset_path`. This keeps preview useful with older or partially populated
sidecars while still leaving the sidecar file unchanged.

Do not depend on Web Crypto for SHA-1 in Photoshop UXP. The user's Photoshop
runtime does not expose `crypto.subtle.digest`, so baseline hashing uses the
project's local pure JavaScript SHA-1 helper.

Pixel diffing must compare hashes produced from the same representation.
Baseline hashes for editable raster records are normalized Photoshop Imaging
API pixel hashes of the source PNG payloads, not hashes of PNG file bytes.
Push preview computes the current Photoshop layer pixel hash with the same
normalization before reporting `changed` or `unchanged`.

If Photoshop reports an empty image region while hashing a layer, the hash
helper returns a stable empty-pixel hash. This keeps fully transparent/empty
layers comparable instead of reporting false hash errors.

For records with `mask_path`, the baseline pixel hash applies the same mask to
the temporary source PNG before hashing. Photoshop's current-layer pixel read
includes the active user mask in this runtime, so masked baselines must be
hashed the same way to avoid false `changed` reports.
