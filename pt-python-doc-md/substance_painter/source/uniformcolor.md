# SourceUniformColor

`SourceUniformColor` is a type of source that outputs a uniform texture from a given color.

For more information, see module `colormanagement`.

## Example

```python
import random
import substance_painter as sp

# Get the currently displayed stack
stack = sp.textureset.get_active_stack()
position = sp.layerstack.InsertPosition.from_textureset_stack(stack)

# Insert a fill layer and setup an uniform color source plugged to the basecolor
fill = sp.layerstack.insert_fill(position)
grey = sp.colormanagement.Color(0.5, 0.5, 0.5)
fill.set_source(sp.textureset.ChannelType.BaseColor, grey)

# Edit the color parameter
src = fill.get_source(sp.textureset.ChannelType.BaseColor)
color = src.get_color()
new_color = sp.colormanagement.Color(
    color.value[0] + random.uniform(-0.5, 0.5),
    color.value[1] + random.uniform(-0.5, 0.5),
    color.value[2] + random.uniform(-0.5, 0.5))
src.set_color(new_color)

# Select the Fill layer
sp.layerstack.set_selected_nodes([fill])
```

## Class: substance_painter.source.SourceUniformColor(uid)

A class that represents a uniform color source.

### get_color()
Get the uniform color of the source.

**Returns:**
- **Color**: The uniform color used by the source.

### set_color(color)
Set the uniform color of the source.

**Parameters:**
- **color** (Color): The desired uniform color.

**Returns:**
- None

### uid()
Get the object internal uid.

**Returns:**
- **int**: The internal identifier of the object as an integer.