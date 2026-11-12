# PT Bridge Desktop

This directory is the native desktop runtime for PT Bridge.

## Runtime direction

- Bun, strict TypeScript, React 19, and an exact-pinned `@gpuix/react`.
- GPUiX renders through GPUI; no browser, webview, Electron, Tauri, WinUI, or
  parallel direct-GPUI implementation is retained.
- Icons come from the repository's vendored `icons/` folder; colours, type and
  metrics live in `src/theme.ts`.
- Transfer state (`src/model.ts`) and file transport (`src/transport.ts`,
  `src/psd.ts`) do not depend on the renderer.

The mapper loads Painter's snapshot (`painter_snapshot.json`) and reads the
connected PSD itself. After the user maps layers and presses Apply it writes
one transfer manifest (`desktop_transfer.json`) and asks Painter to apply it.
It does not poll folders or change Painter in the background.

## Run

```powershell
bun install
bun run dev -- --painter "C:\path\to\painter_snapshot.json" --psd "C:\path\to\document.psd"
```

`--painter` is required; `--psd` connects a Photoshop document at start and
`--output` chooses the transfer-manifest destination. The equivalent
environment variables are `PT_BRIDGE_PAINTER_SNAPSHOT`,
`PT_BRIDGE_PHOTOSHOP_DOCUMENT`, and `PT_BRIDGE_TRANSFER_OUTPUT`. Painter also
passes `--documents` (its map of which PSD each texture set or channel uses;
without `--psd` the window opens the active target's PSD from it),
`--render-scale` (`1`, `2` or `4`, the Render select's starting value) and
`--language` (Painter's language code).

The mapper reads PSD/PSB files itself with ag-psd, so connecting a document
never opens Photoshop. Photoshop-rendered content does not come along: layer
styles are dropped, adjustment layers and gradient or pattern fills are
locked, solid colour fills stay colours, and clipped layers
are merged into their base when transferred. A Photoshop folder arrives in
Painter as a folder of its layers. Only mapped layers are rendered to PNG, at
Apply. `bun tools/make-psd-fixture.ts` regenerates the test PSD.

Under Painter, the mapper talks to its parent over stdio. Requests are single
lines on stdout that start with `@ptbridge `; Painter answers on stdin with
one JSON line each.

- **Connect Photoshop** sends `{"type":"connect_photoshop"}` with the
  `texture_set`, `stack` and `channel` the window shows. Painter replies
  `photoshop_connected` (with `psd`), `photoshop_connect_cancelled`, or
  `photoshop_connect_failed` (with `message`).
- **Apply** writes the transfer manifest and sends
  `{"type":"apply","manifest":…}`. While it works, Painter sends
  `apply_progress` lines (`stage`, `message`, and `completed` / `total` when
  the step is counted); they do not answer the request. The answer is
  `applied` or `apply_failed`, with a `message` and the path of a fresh
  `snapshot`, which the mapper loads so the window stays open for the next
  mapping.
- **Cancel** during an Apply sends `{"type":"cancel_apply"}`. It has no reply
  of its own: Painter stops only while nothing has been written and then
  answers the Apply with `apply_cancelled`.
- A busy or unknown request gets `failed` with a `message`.
- `{"type":"refresh"}` arrives unasked when Painter's Bridge button is pressed
  with the window open; the mapper reads both trees again unless mappings are
  staged.

When Painter closes its end of the pipe, the mapper exits.
GPUiX serves its automation protocol on the same pipes, so replies must stay
single-line JSON. `bun tools/check-windows-input.ts` checks that both protocols
work together with a real Win32 click (`BRIDGE_TEST_COMPILED=1` runs the built
exe).

Use `bun run typecheck` for the TypeScript boundary and `bun run test` for the
tests. The model, transport, i18n and drag tests run without a window; the
context-select, folder-open, layer-interaction and layer-scroll tests open
native test windows, so the files run one at a time. `bun run screenshot`
performs a native GPU paint check without taking keyboard focus.
