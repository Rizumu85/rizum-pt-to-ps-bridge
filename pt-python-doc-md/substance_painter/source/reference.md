# Substance 3D Painter Python API - Source Module

## Overview

The `source` module allows to manipulate the sources of a layer.

When a layer takes a texture as parameter, the user may want to create this texture on the fly using an uniform color or a substance, reference an existing texture in his project or an anchor point in his stack, etc… Source is a concept that hide this diversity behind a generic interface.

Since source objects are tighly coupled to the context they belong to, they can not be created manually. To create a source, use the dedicated functions to query and edit sources.

### Usage Contexts

- **For fill layers see:**
  - `get_material_source()` and `set_material_source()` in `SourceMode.Material` mode,
  - `get_source()` and `set_source()` otherwise.

- **For fill effects see:**
  - `get_material_source()` and `set_material_source()` in `SourceMode.Material` mode,
  - `get_source()` and `set_source()` otherwise.

- **For generators see** `get_source()` and `set_source()`

- **For filters see** `get_source()` and `set_source()`

- **For substances see** `get_source()` and `set_source()`

## Source Types

### SourceUniformColor
- `get_color()` - Get the color
- `set_color()` - Set the color  
- `uid()` - Get unique identifier

### SourceBitmap
- `resource_id` - Resource identifier
- `get_color_space()` - Get color space
- `set_color_space()` - Set color space
- `reset_color_space()` - Reset color space
- `list_available_color_spaces()` - List available color spaces
- `uid()` - Get unique identifier

### SourceVectorial
- `resource_id` - Resource identifier
- `get_parameters()` - Get parameters
- `set_parameters()` - Set parameters
- `uid()` - Get unique identifier

#### VectorialParams
- `SourceVectorialParams` - Parameters for vectorial sources

#### Enums
- `VectorialResolutionMode` - Resolution mode for vectorial sources
- `CropAreaMode` - Crop area mode

### SourceFont
- `resource_id` - Resource identifier
- `get_parameters()` - Get parameters
- `set_parameters()` - Set parameters
- `uid()` - Get unique identifier

#### FontParams
- `SourceFontParams` - Parameters for font sources

#### Enums
- `FontResolutionMode` - Resolution mode for fonts
- `HorizontalAlignment` - Horizontal text alignment
- `VerticalAlignment` - Vertical text alignment

### SourceSubstance
- `resource_id` - Resource identifier
- `output_mapping` - Output mapping
- `active_output` - Active output
- `mask_output` - Mask output
- `image_inputs` - Image inputs
- `image_outputs` - Image outputs
- `get_source()` - Get source
- `set_source()` - Set source
- `reset_source()` - Reset source
- `remove_source()` - Remove source
- `get_parameters()` - Get parameters
- `set_parameters()` - Set parameters
- `get_properties()` - Get properties
- `get_preset_list()` - Get preset list
- `apply_preset()` - Apply preset

### SourceReference
- `channel_mapping` - Channel mapping
- `referenced_channel` - Referenced channel
- `anchor` - Anchor point
- `alpha_matte` - Alpha matte
- `get_levels()` - Get levels
- `set_levels()` - Set levels

#### Reference Classes
- `ChannelMapping` - Channel mapping configuration

#### Enums
- `AlphaMatte` - Alpha matte options

## Parameters

### ResolutionOverride
Control how resource rendering resolution is driven.

**Parameters:**
- `mode` (ResolutionMode) - Control how the resource rendering resolution is driven
- `value` (Tuple[int, int]) - The resolution to use when mode is `ResolutionMode.Manual`, as [width, height] in pixels. Values must be a power of 2, in range [128, 4096]

## Enumerations

### ResolutionMode
Members:
- `Auto` - Resolution matches the parent context, such as the Texture Set resolution in a fill layer, or 512 pixels in a brush tool
- `Asset` - Resolution uses the pixel size defined in the vector file. Not applicable for Font resources
- `Custom` - Resolution is manually provided
- `Document` - Deprecated since 0.3.4, use `Asset` instead
- `Manual` - Deprecated since 0.3.4, use `Custom` instead

### SourceMode
When working with a fill layer or a fill effect in a multi-channel context, you can either have one source that write to all channels or several sources with each source writing to one channel.

Members:
- `Split` - Split mode is used when a source write to only one channel
- `Material` - Material mode is used when a source write to multiple channels at once

## See Also
See the layerstack module documentation for more information about working with layer stacks.