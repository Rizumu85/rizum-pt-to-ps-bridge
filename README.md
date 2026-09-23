# Rizum PT-to-PS Bridge

Rizum PT-to-PS Bridge moves layered work between Substance 3D Painter and
Photoshop. It has three parts:

- **Painter plugin** (`sp_plugin/`): exports layer-aware PNG payloads and
  `build_request.json` bundles, and applies desktop transfers.
- **Photoshop automation** (`sp_plugin/rizum_sp_to_ps/*.jsx`): ExtendScript
  that Painter runs in Photoshop to build PSDs, connect a PSD to the mapper,
  and insert mapped layers. Nothing is installed in Photoshop.
- **Desktop mapper** (`desktop/`): a native GPUiX window that shows both layer
  trees so you can map layers between the hosts and press Apply.

## Load in Substance Painter

This repository is currently intended to sit at:

```text
E:\Documents\Adobe\Adobe Substance 3D Painter\python\plugins\rizum-pt-to-ps-bridge
```

Substance Painter loads the root `__init__.py` / `rizum_pt_to_ps_bridge.py`
shim, which delegates to `sp_plugin/rizum_sp_to_ps/`.

After enabling the plugin in Painter, open the `Rizum PT-to-PS` dock panel:

- **Export** writes build bundles for the chosen stacks and channels, then
  opens Photoshop and builds the PSDs.
- **Bridge** opens the desktop mapper. Build it once first (see below).
- **Settings** sets the Photoshop executable path, padding, and bit depth.
  Set the Photoshop path before the first export.

## Build the Desktop Mapper

The Bridge action launches `desktop/dist/pt-bridge.exe`. Build it with
[Bun](https://bun.sh) after cloning or after desktop changes:

```text
cd desktop
bun install
bun run build
```

See `desktop/README.md` for development runs and checks.

## Run All Checks

```text
pwsh tools/run-checks.ps1
```

Runs the Painter Python tests plus the desktop typecheck and tests.
