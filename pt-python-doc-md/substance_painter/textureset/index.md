# Textureset Module

## Overview

The `textureset` module allows to manipulate the stacks and Texture Sets of the currently opened project.

A Texture Set has a resolution and one or more stacks, depending on whether the material is layered or not. If the material is layered, the Texture Set has several stacks. A stack contains one or more channels, corresponding to the different types that the material can have (BaseColor, Specular, Roughness, etc.). There can be only one channel of each type. A Texture Set may also have UV Tiles.

This module exposes the corresponding `TextureSet`, `Stack`, `Channel` and `UVTile` classes, allowing to retrieve and set information of the paintable stacks and the Texture Sets of the project, as well as their storage format.

`substance_painter.layerstack.get_root_layer_nodes()` is the entry point for querying the corresponding layer stack.

For instance, it is possible to change the channels of the stacks, or set the resolution of the Texture Sets.

## Example

```python
import substance_painter.textureset

# Show the resolution of the current Texture Set:
active_stack = substance_painter.textureset.get_active_stack()
material_resolution = active_stack.material().get_resolution()
print("Resolution: {0}x{1}".format(material_resolution.width, material_resolution.height))

# Change the resolution of the current Texture Set:
new_resolution = substance_painter.textureset.Resolution(512, 512)
active_stack.material().set_resolution(new_resolution)

# Change the resolution of all Texture Sets:
all_texture_sets = substance_painter.textureset.all_texture_sets()
substance_painter.textureset.set_resolutions(all_texture_sets, new_resolution)

# List all the Texture Sets:
for texture_set in substance_painter.textureset.all_texture_sets():
    print("Texture Set '{0}': {1}".format(texture_set.name(),
        "layered" if texture_set.is_layered_material() else "not layered"))

    # Get all uv tiles in the first row
    row0 = [uvtile for uvtile in textureset.all_uv_tiles() if uvtile.v == 0]

    # Set their resolution to 2k
    new_resolution = substance_painter.textureset.Resolution(2048, 2048)
    resolutions = {uvtile:new_resolution for uvtile in row0}
    textureset.set_uvtiles_resolution(resolutions)

    # Set 1001 in 4k if its width is not high enough
    uvtile_1001 = next((uvtile for uvtile in row0 if uvtile.u == 0), None)
    new_resolution = substance_painter.textureset.Resolution(4096, 4096)
    if uvtile_1001.get_resolution().width < new_resolution.width:
        uvtile_1001.set_resolution(new_resolution)

    # Reset all uv tiles resolution:
    all_uv_tiles = texture_set.all_uv_tiles()
    texture_set.reset_uvtiles_resolution(all_uv_tiles)

# List all the stacks of the current Texture Set:
for stack in active_stack.material().all_stacks():
    if stack.name():
        print("Stack '{0}'".format(stack.name()))
    else:
        print("Stack has no name")

# Find a stack called "Mask1" and set it as active:
mask_stack = substance_painter.textureset.Stack.from_name("DefaultMaterial", "Mask1")
if mask_stack != None:
    substance_painter.textureset.set_active_stack(mask_stack)

# Show the current active stack:
print(substance_painter.textureset.get_active_stack())
```

## Classes

### ChannelFormat

The texture format of a channel.

**Members:**

| Name | Type | Dynamic range | Bits per component | Storage |
|------|------|---------------|-------------------|---------|
| `sRGB8` | Color | normalized fixed point | 8 | sRGB |
| `L8` | Grayscale | normalized fixed point | 8 | linear |
| `RGB8` | Color | normalized fixed point | 8 | linear |
| `L16` | Grayscale | normalized fixed point | 16 | linear |
| `RGB16` | Color | normalized fixed point | 16 | linear |
| `L16F` | Grayscale | HDR floating point | 16 | linear |
| `RGB16F` | Color | HDR floating point | 16 | linear |
| `L32F` | Grayscale | HDR floating point | 32 | linear |
| `RGB32F` | Color | HDR floating point | 32 | linear |

> **Note:** The name used to define members is available as a string via the `.name` attribute.

### ChannelType

All possible types of channel in a document. To get the actual list of channel types in use for a particular Stack, call `substance_painter.textureset.Stack.all_channels()`.

**Members:**

`BaseColor`, `Height`, `Specular`, `SpecularEdgeColor`, `Opacity`, `Emissive`, `Displacement`, `Glossiness`, `Roughness`, `Anisotropylevel`, `Anisotropyangle`, `Transmissive`, `Reflection`, `Ior`, `Metallic`, `Normal`, `AO`, `Diffuse`, `Specularlevel`, `BlendingMask`, `Translucency`, `Scattering`, `ScatterColor`, `SheenOpacity`, `SheenRoughness`, `SheenColor`, `CoatOpacity`, `CoatColor`, `CoatRoughness`, `CoatSpecularLevel`, `CoatNormal`, `User0`, `User1`, `User2`, `User3`, `User4`, `User5`, `User6`, `User7`, `User8`, `User9`, `User10`, `User11`, `User12`, `User13`, `User14`, `User15`

> **Note:** The name used to define members is available as a string via the `.name` attribute.

### MeshMapUsage

**Members:**

`AO`, `BentNormals`, `Curvature`, `Height`, `ID`, `Normal`, `Opacity`, `Position`, `Thickness`, `WorldSpaceNormal`

> **Note:** The name used to define members is available as a string via the `.name` attribute.

### Resolution

Two dimensional resolution.

For Texture Sets and UV Tiles, there are restrictions. The resolution must be a power of 2, for example 256, 512, 1024, 2048, etc. It must also be within the range of accepted resolutions.

For UV Tiles, resolution must be square (ie width = height).

**Parameters:**
- `width` (int): The width in pixels.
- `height` (int): The height in pixels.

## Functions

### all_texture_sets()

List all the Texture Sets of the current project.

**Returns:**
- `list[TextureSet]`: List of all the Texture Sets of this project.

**Raises:**
- `ProjectError`: If no project is opened.
- `ServiceNotFoundError`: If Substance 3D Painter has not started all its services yet.

### get_active_stack()

Get the currently paintable Texture Set stack.

**Returns:**
- `Stack`: The currently paintable stack.

**Raises:**
- `ProjectError`: If no project is opened.
- `RuntimeError`: If there is no active stack.
- `ServiceNotFoundError`: If Substance 3D Painter has not started all its services yet.

### set_active_stack(stack)

Set the Texture Set stack to be currently paintable.

**Parameters:**
- `stack` (Stack): The stack to select.

**Raises:**
- `ProjectError`: If no project is opened.
- `ServiceNotFoundError`: If Substance 3D Painter has not started all its services yet.
- `ValueError`: If `stack` is not a valid Stack.

### set_resolutions(texturesets, new_resolution)

Set the same resolution to multiple Texture Sets.

See resolution restrictions: `Resolution`.

> **Note:** For any Texture Set, you can find its accepted resolutions in the "Texture Set Settings" window, in the "Size" menu.

**Parameters:**
- `texturesets` (list[TextureSet]): The list of Texture Sets to change.
- `new_resolution` (Resolution): The new resolution for the Texture Sets.

**Raises:**
- `ProjectError`: If no project is opened.
- `ServiceNotFoundError`: If Substance 3D Painter has not started all its services yet.
- `ValueError`: If a Texture Set in `texturesets` is invalid.
- `ValueError`: If there are duplicated Texture Sets in `texturesets`.
- `ValueError`: If `new_resolution` is not a valid resolution.

## See Also

- [Texture Set documentation](https://www.adobe.com/go/painter-texture-set)
- [UV Tiles documentation](https://www.adobe.com/go/painter-uv-tiles)
- `Stack` class
- `TextureSet` class
- `UVTile` class
- `Channel` class