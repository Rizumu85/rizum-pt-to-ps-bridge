# Channel Class

## substance_painter.textureset.Channel

```python
class substance_painter.textureset.Channel(channel_id: int | None = None)
```

A Substance 3D Painter channel.

A channel can be one of the predefined types (`BaseColor`, `Specular`, `Roughness`, etc.) or a user defined type (`User0` to `User7`), corresponding to the material. The channel belongs to a stack. The stack can have one or more of them, but it can have only one channel of each `ChannelType`.

### Example

```python
import substance_painter.textureset

# Get the unnamed stack of "TextureSetName":
paintable_stack = substance_painter.textureset.Stack.from_name("TextureSetName")

# Get the channel "BaseColor" of that stack:
base_color_channel = paintable_stack.get_channel(
    substance_painter.textureset.ChannelType.BaseColor)

# Print the color format and bit depth of the base color channel:
print("The channel format uses {0} {1}.".format(
    "RGB" if base_color_channel.is_color() else "L",
    base_color_channel.bit_depth()))

# Change the format and bit depth of the base color channel:
base_color_channel.edit(
    channel_format = substance_painter.textureset.ChannelFormat.RGB16)
```

**Parameters:**
- `channel_id` (int)

## Methods

### format()

```python
format() → ChannelFormat
```

Get the channel format. The format indicates both if the channel is color or grayscale, its dynamic range, its bits per component, and if the storage is linear or sRGB.

**Returns:**
- `ChannelFormat` - This channel format.

### label()

```python
label() → str
```

Get the user label for User channels (`User0` to `User7`).

**Returns:**
- `str` - This channel user label. This is the empty string for non User channels.

**See also:**
- `Channel.type()`
- `ChannelType`

### is_color()

```python
is_color() → bool
```

Check if the channel is in color or grayscale format.

**Returns:**
- `bool` - `True` if the channel format is a color format.

### is_floating()

```python
is_floating() → bool
```

Check if the channel is in floating point or normalized fixed point format.

**Returns:**
- `bool` - `True` if the channel format is a floating point format.

### bit_depth()

```python
bit_depth() → int
```

Get the number of bits per component.

**Returns:**
- `int` - The channel bit depth per component.

### type()

```python
type() → ChannelType
```

Get the channel type.

**Returns:**
- `ChannelType` - This channel type.

**See also:**
- `Channel.label()`

### edit()

```python
edit(channel_format: ChannelFormat, label: str | None = None) → None
```

Change the channel format and label.

**Parameters:**
- `channel_format` (ChannelFormat) - The new texture format of the channel.
- `label` (str, optional) - Label of the channel in case of User channel as type.

**Raises:**
- `ProjectError` - If no project is opened.
- `ValueError` - If there is no stack labeled `stack_id` in this Texture Set.
- `ValueError` - If there is no channel of type `channel_type` in this Texture Set.
- `ValueError` - If a label was provided but `channel_type` is not a user type. Standard channel types have fixed labels.
- `ValueError` - If the channel is invalid.

**Returns:**
- `None`