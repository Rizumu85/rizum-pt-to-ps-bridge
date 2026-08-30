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
bun run dev -- --session "C:\path\to\photoshop_selection.json"
```

The selection manifest's Photoshop document path resolves its adjacent
`.rizum.json` Painter snapshot. Pass `--painter <path>` to choose a different
snapshot and `--output <path>` to choose the transfer-manifest destination.
The equivalent environment variables are `PT_BRIDGE_PHOTOSHOP_MANIFEST`,
`PT_BRIDGE_PAINTER_SNAPSHOT`, and `PT_BRIDGE_TRANSFER_OUTPUT`.

Use `bun run typecheck` for the TypeScript boundary and `bun run test` for the
renderer-independent transfer model. `bun run screenshot` performs a native
GPU paint check without taking keyboard focus.
