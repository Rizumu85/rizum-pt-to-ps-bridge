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

The current milestone is an interactive native shell with expandable groups,
hover states, drag-to-map behavior, and working Cancel, Undo, and Apply actions.
Painter/Photoshop file transport is intentionally not connected yet.

## Run

```powershell
bun install
bun run dev
```

Use `bun run typecheck` for the TypeScript boundary and `bun run test` for the
renderer-independent transfer model. `bun run screenshot` performs a native
GPU paint check without taking keyboard focus.
