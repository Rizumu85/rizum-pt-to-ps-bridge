# SourceFont

`SourceFont` is a type of source where you can connect a font resource.

For more information, see module `resource`.

## Example

```python
import substance_painter as sp

# Get the currently displayed stack
stack = sp.textureset.get_active_stack()

# Insert a fill layer
position = sp.layerstack.InsertPosition.from_textureset_stack(stack)
fill = sp.layerstack.insert_fill(position)

# Setup warp projection
params = sp.layerstack.WarpProjectionParams(
    uv_wrapping_mode=sp.layerstack.UVWrapMode.RepeatNone,
    projection_depth=0.3,
)
fill.set_projection_parameters(params)

# Pick a font resource
font = sp.resource.search("u:font")[0]
source = fill.set_source(sp.textureset.ChannelType.BaseColor, font.identifier())

# Customize font parameters
params = source.get_parameters()
params.text = "Hello World"
params.color = sp.colormanagement.Color(0.8, 0.2, 0.2)
source.set_parameters(params)

# Select the Fill layer
sp.layerstack.set_selected_nodes([fill])
```

## SourceFont Class

**class substance_painter.source.SourceFont(uid)**

A class that represents a text source.

### Properties

**property resource_id: ResourceID**

The current font resource of the source.

- **Getter**: Returns the resource identifier of the font used by the source.
- **Type**: ResourceID

### Methods

**get_parameters() → SourceFontParams**

Get the source parameters.

- **Returns**: The source parameters.
- **Return type**: SourceFontParams

**set_parameters(params: SourceFontParams) → None**

Set the source parameters.

- **Parameters**: 
  - **params** (SourceFontParams) – The source parameters.
- **Raises**: 
  - **ValueError** – If the parameters requirements are not met, see `SourceFontParams`.
- **Return type**: None

**uid() → int**

Get the object internal uid.

- **Returns**: The internal identifier of the object as an integer.
- **Return type**: int

## Params

**class substance_painter.source.SourceFontParams(text, auto_size, size, horizontal_alignment, vertical_alignment, color, background_color, background_opacity, line_spacing, character_spacing, offset, resolution)**

The source font parameters.

### Parameters

- **text** (str | None) – The text to render.
- **auto_size** (bool) – Automatically adjust size to fit the render resolution.
- **size** (float | None) – Manual size of the font, normalized and proportional to the resolution. Value must be positive.
- **horizontal_alignment** (HorizontalAlignment) – The horizontal position of the text (left, center, right).
- **vertical_alignment** (VerticalAlignment) – The vertical position of the text (top, middle, bottom).
- **color** (Color) – The text color as RGB values. Values must be in range [0, 1].
- **background_color** (Color) – The RGB background color. Values must be in range [0, 1].
- **background_opacity** (float | None) – The background opacity value. Value must be in range [0, 1].
- **line_spacing** (float) – Distance between lines of text ("leading") relative to the font size.
- **character_spacing** (float) – The amount of space between adjacent characters relative to the font size. Can be negative to subtract spacing.
- **offset** (Tuple[float, float]) – Horizontal and vertical offset of the text. Normalized to the font size.
- **resolution** (ResolutionOverride) – Resolution parameters of the resource.
- **resolution_mode** (FontResolutionMode) – Deprecated since 0.3.4. Use `mode` attribute from **resolution** parameter instead.
- **resolution_value** (Tuple[int, int]) – Deprecated since 0.3.4. Use `value` attribute from **resolution** parameter instead.

## Enums

**class substance_painter.source.FontResolutionMode(value)**

Members:

| Name | Description |
|------|-------------|
| `Auto` | Resolution is automatically computed. |
| `Manual` | Resolution is manually provided. |

> **Warning**: Deprecated since 0.3.4, use `ResolutionMode` instead.

**class substance_painter.source.HorizontalAlignment(value)**

Members:

| Name | Description |
|------|-------------|
| `Left` | Align the text to the left. |
| `Center` | Center the text horizontally. |
| `Right` | Align the text to the right. |

**class substance_painter.source.VerticalAlignment(value)**

Members:

| Name | Description |
|------|-------------|
| `Top` | Align the text from the top. |
| `Middle` | Center the text vertically. |
| `Bottom` | Align the text from the bottom. |

> **Note**: The name used to define members is available as a string via the `.name` attribute (see python enum.Enum).