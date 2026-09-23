# Rizum PT-to-PS Bridge

Rizum PT-to-PS Bridge moves layered work between Substance 3D Painter and
Photoshop. It has three parts:

- **Painter plugin** (`sp_plugin/`): exports layer-aware PNG payloads and
  `build_request.json` bundles, and applies desktop transfers.
- **Photoshop UXP plugin** (`ps_plugin/`): builds editable PSDs from those
  bundles and exports selected Photoshop layers.
- **Desktop mapper** (`desktop/`): a native GPUiX window that shows both layer
  trees so you can map layers between the hosts and press Apply.

This checkout can live in Painter's Python plugin directory, but Photoshop will
not discover a UXP plugin from that location. Load each host side separately.

## Load in Substance Painter

This repository is currently intended to sit at:

```text
E:\Documents\Adobe\Adobe Substance 3D Painter\python\plugins\rizum-pt-to-ps-bridge
```

Substance Painter loads the root `__init__.py` / `rizum_pt_to_ps_bridge.py`
shim, which delegates to `sp_plugin/rizum_sp_to_ps/`.

After enabling the plugin in Painter, open the `Rizum PT-to-PS` dock panel:

- **Export** writes build bundles for the chosen stacks and channels.
- **Bridge** opens the desktop mapper. Build it once first (see below).
- **Settings** sets the Photoshop path, padding, bit depth, and auto-open.

## Build the Desktop Mapper

The Bridge action launches `desktop/dist/pt-bridge.exe`. Build it with
[Bun](https://bun.sh) after cloning or after desktop changes:

```text
cd desktop
bun install
bun run build
```

See `desktop/README.md` for development runs and checks.

## Load in Photoshop for Local Testing

Use Adobe UXP Developer Tool:

1. Open Photoshop.
2. Open Adobe UXP Developer Tool.
3. Choose `Add Plugin`.
4. Select this file:

   ```text
   E:\Documents\Adobe\Adobe Substance 3D Painter\python\plugins\rizum-pt-to-ps-bridge\ps_plugin\manifest.json
   ```

5. Click `Load` in UXP Developer Tool.
6. In Photoshop, open `Plugins` -> `Rizum PT Bridge`.

The Photoshop panel can build a PSD from a Painter `build_request.json`. For
Photoshop-to-Painter transfers, open **Bridge** in Painter, choose
**Connect Photoshop**, map layers, and press Apply.

## Windows Offline Install

The Windows offline installer copies `ps_plugin/` into:

```text
%APPDATA%\Adobe\UXP\Plugins\External\com.rizum.pt-to-ps-bridge
```

It also registers the plugin in:

```text
%APPDATA%\Adobe\UXP\PluginsInfo\v1\PS.json
```

After running the installer, close Photoshop completely and reopen it before
checking `Plugins -> Rizum PT Bridge`.

Run:

```text
installers\install-ps-plugin-windows.bat
```

## Windows Offline Uninstall

The Windows uninstaller removes this plugin's UXP External folder and removes
the matching `pluginId` entry from `PS.json`.

Run:

```text
installers\uninstall-ps-plugin-windows.bat
```

After running the uninstaller, close Photoshop completely and reopen it before
checking that `Plugins -> Rizum PT Bridge` is gone.
