# PT Bridge Desktop

This directory is the native desktop runtime for PT Bridge.

## Runtime direction

- Bun, strict TypeScript, React 19, and an exact-pinned `@gpuix/react`.
- GPUiX renders through GPUI; no browser, webview, Electron, Tauri, WinUI, or
  parallel direct-GPUI implementation is retained.
- `mockups/pt-bridge-ui-v4.html` and the vendored PT Bridge icons remain the
  visual authority. Rizum Glass contributes migration discipline and runtime
  patterns, not product colors or component styling.
- Renderer-bound window measurements will live behind one lifecycle-safe
  adapter when the desktop app needs them. Transfer state and file transport
  must remain independent from renderer availability.

The native shell loads a Photoshop selection manifest plus a Painter snapshot,
then writes one explicit desktop transfer manifest after the user maps layers
and presses Apply. It does not poll folders or mutate Painter in the background.

## Run

```powershell
bun install
bun run dev -- --painter "C:\path\to\painter_snapshot.json" --psd "C:\path\to\document.psd"
```

`--painter` is required; `--psd` connects a Photoshop document at start and
`--output` chooses the transfer-manifest destination. The equivalent
environment variables are `PT_BRIDGE_PAINTER_SNAPSHOT`,
`PT_BRIDGE_PHOTOSHOP_DOCUMENT`, and `PT_BRIDGE_TRANSFER_OUTPUT`.

The mapper reads PSD/PSB files itself with ag-psd, so connecting a document
never opens Photoshop. Photoshop-rendered content does not come along: layer
styles are dropped, adjustment layers and gradient or pattern fills are
locked, solid colour fills stay colours, and clipped layers
are merged into their base when transferred. A Photoshop folder arrives in
Painter as a folder of its layers. Only mapped layers are rendered to PNG, at
Apply. `bun tools/make-psd-fixture.ts` regenerates the test PSD.

Under Painter, the mapper talks to its parent over stdio. **Connect Photoshop**
writes one `@ptbridge {"type":"connect_photoshop"}` line to stdout, and Painter
replies on stdin with one JSON line: `photoshop_connected` (with `psd`),
`photoshop_connect_cancelled`, or `photoshop_connect_failed` (with `message`).
GPUiX serves its automation protocol on the same pipes, so replies must stay
single-line JSON. `bun tools/check-windows-input.ts` checks that both protocols
work together with a real Win32 click (`BRIDGE_TEST_COMPILED=1` runs the built
exe).

Use `bun run typecheck` for the TypeScript boundary and `bun run test` for the
renderer-independent transfer model. `bun run screenshot` performs a native
GPU paint check without taking keyboard focus.
