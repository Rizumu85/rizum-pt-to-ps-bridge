# SourceBitmap

`SourceBitmap` is a type of source where you can connect a bitmap resource.

For more information, see modules `resource` and `colormanagement`.

## Example

```python
import substance_painter as sp

# Get the currently displayed stack
stack = sp.textureset.get_active_stack()

# Insert a fill layer
position = sp.layerstack.InsertPosition.from_textureset_stack(stack)
fill = sp.layerstack.insert_fill(position)

# Use the normal as source
normal = sp.resource.search("s:project "
                           "u:texture "
                           "n:normal")[0]
source = fill.set_source(sp.textureset.ChannelType.Normal, normal.identifier())

# Assuming the resource is a DirectX normal map, set the colorspace accordingly
normal_map_format = sp.colormanagement.NormalColorSpace.NormalXYZLeft
source.set_color_space(normal_map_format)

# Select the Paint layer
sp.layerstack.set_selected_nodes([fill])
```

## Class: substance_painter.source.SourceBitmap

A class that represents a bitmap source.

### Properties

#### resource_id
- **Type**: `ResourceID`
- **Description**: The current bitmap used by the source.
- **Getter**: Returns the resource identifier of the bitmap used by the source.

### Methods

#### get_color_space()
Return the color space of the bitmap.

**Returns**: The current color space.
**Return type**: GenericColorSpace | LegacyColorSpace | DataColorSpace | NormalColorSpace | str

**See also**: ColorSpace Enums section.

#### set_color_space(color_space)
Override the default color space of the bitmap.

**Parameters**:
- **color_space** (GenericColorSpace | LegacyColorSpace | DataColorSpace | NormalColorSpace | str): The color space to set.

**Raises**:
- **ValueError**: If the given color space is not supported in the current context or by the current color management engine.

**See also**: ColorSpace Enums section, `list_available_color_spaces()`.

#### reset_color_space()
Remove any override color space and go back to the default one.

#### list_available_color_spaces()
Get the list of available color spaces for the bitmap.

**Returns**: The list of available color spaces.
**Return type**: List[GenericColorSpace | LegacyColorSpace | DataColorSpace | NormalColorSpace | str]

**See also**: ColorSpace Enums section.

#### uid()
Get the object internal uid.

**Returns**: The internal identifier of the object as an integer.
**Return type**: int