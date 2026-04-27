# Source module

The source module allows to manipulate the sources of a layer.

When a layer takes a texture as parameter, the user may want to create this texture on the fly using an uniform color or a substance, reference an existing texture in his project or an anchor point in his stack, etc. `Source` is a concept that hide this diversity behind a generic interface.

Since source objects are tightly coupled to the context they belong to, they can not be created manually. To create a source, use the dedicated functions to query and edit sources.

- For fill layers see:
  - `get_material_source()` and `set_material_source()` in `SourceMode.Material` mode
  - `get_source()` and `set_source()` otherwise
- For fill effects see:
  - `get_material_source()` and `set_material_source()` in `SourceMode.Material` mode
  - `get_source()` and `set_source()` otherwise
- For generators see `get_source()` and `set_source()`
- For filters see `get_source()` and `set_source()`
- For substances see `get_source()` and `set_source()`

## Overview

- `SourceUniformColor`
- `SourceBitmap`
- `SourceVectorial`
- `SourceFont`
- `SourceSubstance`
- `SourceReference`

## See also

See the `layerstack` module documentation.

## Params

### class substance_painter.source.ResolutionOverride(mode: ResolutionMode, value: Tuple[int, int], log2_offset: int)

Resolution override parameters.

**Parameters:**
- `mode` (ResolutionMode) – Control how the resource rendering resolution is driven.
- `value` (Tuple[int, int]) – The resolution to use when mode is `ResolutionMode.Manual`, as `[width, height]` in pixels. Values must be a power of 2, in range `[128, 4096]`.
- `log2_offset` (int) – Log2 resolution boost or reduce, applied on both width and height. Only used if mode is set to `ResolutionMode.Auto`.

## Enums

### class substance_painter.source.ResolutionMode(value)

**Members:**

| Name | Description |
|------|-------------|
| `Auto` | Resolution matches the parent context, such as the Texture Set resolution in a fill layer, or 512 pixels in a brush tool. |
| `Asset` | Resolution uses the pixel size defined in the vector file. Not applicable for Font resources. |
| `Custom` | Resolution is manually provided. |
| `TextureSet` | Resolution matches the parent textureset's resolution. |
| `UVTile` | Resolution matches the current uvtile's resolution. |
| `Document` | Deprecated since 0.3.4, use `Asset` instead. |
| `Manual` | Deprecated since 0.3.4, use `Custom` instead. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### class substance_painter.source.SourceMode(value)

When working with a fill layer or a fill effect in a multi-channel context, you can either have one source that write to all channels or several sources with each source writing to one channel.

**Members:**

| Name | Description |
|------|-------------|
| `Split` | Split mode is used when a source write to only one channel. |
| `Material` | Material mode is used when a source write to multiple channels at once. |

**See also:** `substance_painter.layerstack.FillLayerNode.source_mode()` and `substance_painter.layerstack.FillEffectNode.source_mode()`.

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).