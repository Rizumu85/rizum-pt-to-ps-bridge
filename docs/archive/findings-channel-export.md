# Findings: User Channel Export & UDIM Per-Layer PNG

## User Channel Identifiers

`alg.mapexport.save([uid, channel])` accepts three forms for user channels
(source: `reference-docs/pt-javascript-doc-html/alg.mapexport.html`, dataPath
parameter valid map names):

| Form | Example | Notes |
|---|---|---|
| `user<N>` (lowercase, no space) | `user0` | Current `bridge.channel_identifier("User0")` output |
| `user <N>` (lowercase, space) | `user 0` | JS docs list both spellings |
| Custom user label | `SCol`, `TNrm`, `SDF` | `Channel.label()`, returned by `channelIdentifiers(stackPath)` |

`channelIdentifiers(stackPath)` with a stackPath resolves user channels to their
custom labels. Its doc return-value description lists standard channels ending
with `[custom user names]`.

`documentStructure().materials[].stacks[].channels` returns engine-resolved
lowercase identifiers. The old v1.1.8 plugin used these exact strings directly.

Current exporter multi-candidate fallback in `_export_asset_png` tries all
spellings. If user channels still produce transparent per-layer PNGs, the cause
is not the identifier string — it is layer/channel activity mismatch.

## No UDIM Support in `alg.mapexport.save`

`MapInfo` type has no tile or UV coordinate parameter. Fields: `padding`,
`dilation`, `dithering`, `resolution`, `bitDepth`, `keepAlpha`.

Per-layer PNGs always render at full texture-set resolution covering all UV
tiles. No way to isolate a single tile.

## Python Solo-Export Fallback Viability

`reference-docs/pt-python-doc-md/substance_painter/layerstack/navigation.md:198`:

- `node.is_visible() → bool` — getter
- `node.set_visible(visible: bool)` — setter, exists on every `Node`

`reference-docs/pt-python-doc-md/substance_painter/layerstack/edition.md:173`:

- `sp.layerstack.ScopedModification("name")` — context manager, groups mutations
  into a single undo entry, defers computation until `with` block exits

`reference-docs/pt-python-doc-md/substance_painter/export.md`:

- `export_project_textures` supports `"uvTiles"` filter: `[[1, 1], [1, 2]]`

**No solo/isolate API exists** in either Python or JS — no built-in "export only
this layer" or "temporarily solo layer" method.

## ChannelType Enum

`reference-docs/pt-python-doc-md/substance_painter/textureset/index.md`:

User channel enums go up to `User15` (not just `User0`–`User7`):

```
User0, User1, User2, User3, User4, User5, User6, User7,
User8, User9, User10, User11, User12, User13, User14, User15
```

`bridge.py` `CHANNEL_IDENTIFIERS` dict and `channel_identifier()` only handle
`User0`–`User7` via the `startswith("User")` branch, which works for all.

## JS `save` vs `saveChannelMap`

`alg.mapexport.saveChannelMap(stackPath, channel, filePath, mapInfo)` exports a
full stack channel snapshot (same as old plugin's 3-element path:
`[materialName, stackName, channel]`). This is the JS equivalent of Python
`export_project_textures` for a single channel — also no per-layer isolation.

`alg.mapexport.save(dataPath, filePath, mapInfo)` with a 2-element dataPath
`[layerUid, channel]` is the only per-layer export path. Its UDIM blind spot is
structural, not a missing parameter.
