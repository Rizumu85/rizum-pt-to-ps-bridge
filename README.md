# Rizum PT-to-PS Bridge

Rizum PT-to-PS Bridge is a two-plugin workflow between Substance 3D Painter and
Photoshop. The Painter plugin exports layer-aware PNG payloads and JSON build
requests. The Photoshop UXP plugin reads those requests, builds editable PSDs,
and can export user-selected Photoshop layers or layer/mask PNG pairs for
manual import back into Painter.

This checkout can live in Painter's Python plugin directory, but Photoshop will
not discover a UXP plugin from that location. Load each host side separately.

## Load in Substance Painter

This repository is currently intended to sit at:

```text
E:\Documents\Adobe\Adobe Substance 3D Painter\python\plugins\rizum-pt-to-ps-bridge
```

Substance Painter loads the root `__init__.py` / `rizum_pt_to_ps_bridge.py`
shim, which delegates to `sp_plugin/rizum_sp_to_ps/`.

After enabling the plugin in Painter, open the `Rizum PT-to-PS` dock panel and
use `Run M1 Smoke Test` to write a `build_request.json` bundle.

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
Photoshop-to-Painter return data, select layers in Photoshop and use either
`Export Selected (Applied Mask)` or `Export Selected + Masks`, then manually
import the written PNG files into Painter.

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
