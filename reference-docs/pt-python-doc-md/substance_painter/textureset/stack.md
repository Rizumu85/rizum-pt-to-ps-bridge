# Stack Class

## substance_painter.textureset.Stack

**class substance_painter.textureset.Stack(stack_id: int | None = None)**

A `Substance 3D Painter` paintable stack.

A stack can contain a number of channels (BaseColor, Specular, Roughness, etc.), that correspond to the material. The stack belongs to a Texture Set, which may contain one or more stacks.

Typically, only one stack is used and that stack is transparent to the user. Selecting the Texture Set will select its stack. However, a Texture Set can use layered materials with custom shaders, in which case a specific stack needs to be selected.

If the Texture Set doesn't use material layering, you can retrieve its stack as follows:

```python
import substance_painter.textureset

# Get the unnamed stack of "TextureSetName":
paintable_stack = substance_painter.textureset.Stack.from_name("TextureSetName")

# Alternatively, get the stack from a Texture Set instance:
my_texture_set = substance_painter.textureset.TextureSet.from_name("TextureSetName")
paintable_stack = my_texture_set.get_stack()
```

If the Texture Set *does* use material layering, you can retrieve its stacks as follows:

```python
import substance_painter.textureset

# Get the stack called "Mask1" from the Texture Set "TextureSetName":
paintable_stack = substance_painter.textureset.Stack.from_name("TextureSetName", "Mask1")

# Alternatively, get the stack from a Texture Set instance:
my_texture_set = substance_painter.textureset.TextureSet.from_name("TextureSetName")
paintable_stack = my_texture_set.get_stack("Mask1")

# Show the name of the stack:
print(paintable_stack.name())
```

It is possible to query, add, remove or edit the channels of a stack:

```python
import substance_painter.textureset

# Get the unnamed stack of "TextureSetName":
paintable_stack = substance_painter.textureset.Stack.from_name("TextureSetName")

# List all the channels of the "TextureSetName" Texture Set:
for k,v in paintable_stack.all_channels().items():
    print("{0}: {1}".format(k, str(v.format())))

# Add a scattering channel to the "TextureSetName" Texture Set:
paintable_stack.add_channel(substance_painter.textureset.ChannelType.Scattering,
                            substance_painter.textureset.ChannelFormat.L8)

# Query details of the added scattering channel:
if paintable_stack.has_channel(substance_painter.textureset.ChannelType.Scattering):
    channel = paintable_stack.get_channel(
        substance_painter.textureset.ChannelType.Scattering)
    print("The Texture Set now has a scattering channel with {0} bits per pixel."
        .format(channel.bit_depth()))

# Change the scattering channel to 16 bits inside the "TextureSetName" Texture Set:
paintable_stack.edit_channel(
    channel_type = substance_painter.textureset.ChannelType.Scattering,
    channel_format = substance_painter.textureset.ChannelFormat.L16)

# Remove the scattering channel from "TextureSetName":
paintable_stack.remove_channel(substance_painter.textureset.ChannelType.Scattering)
```

**See also:** TextureSet, [Texture Set documentation](https://www.adobe.com/go/painter-texture-set).

**Parameters:**
- **stack_id** (int)

## Methods

### from_name

**static from_name(texture_set_name: str, stack_name: str = '') → Stack**

Get a stack from its name.

**Parameters:**
- **texture_set_name** (str) – Texture Set name.
- **stack_name** (str) – Stack name. Leave empty if the Texture Set does not use material layering.

> **Note:** The Texture Set and stack names are case sensitive.

**Raises:**
- **ProjectError** – If no project is opened.
- **ServiceNotFoundError** – If Substance 3D Painter has not started all its services yet.
- **ValueError** – If `texture_set_name` is not string.
- **ValueError** – If there is no Texture Set with the name `texture_set_name`.
- **ValueError** – If there is no stack with the name `stack_name`.

**See also:** TextureSet.all_stacks(), TextureSet.get_stack().

### name

**name() → str**

Get the stack name. A stack name is empty if the Texture Set it belongs to uses material layering.

**Returns:** The stack name.

**Return type:** str

**Raises:**
- **ProjectError** – If no project is opened.
- **ServiceNotFoundError** – If Substance 3D Painter has not started all its services yet.
- **ValueError** – If the stack is invalid.

### material

**material() → TextureSet**

Get the Texture Set this stack belongs to.

**Returns:** The Texture Set this stack belongs to.

**Return type:** TextureSet

**Raises:**
- **ProjectError** – If no project is opened.
- **ServiceNotFoundError** – If Substance 3D Painter has not started all its services yet.
- **ValueError** – If the stack is invalid.

**See also:** TextureSet, all_texture_sets().

### all_channels

**all_channels() → Dict[ChannelType, Channel]**

List all the channels of a stack.

**Returns:** Map of all the channels of the stack.

**Return type:** dict[ChannelType, Channel]

**Raises:**
- **ProjectError** – If no project is opened.
- **ServiceNotFoundError** – If Substance 3D Painter has not started all its services yet.

**See also:** Stack.add_channel(), Stack.remove_channel().

### add_channel

**add_channel(channel_type: ChannelType, channel_format: ChannelFormat, label: str | None = None) → Channel**

Add a new channel to a stack.

> **Note:** `add_channel` is not available with material layering.

**Parameters:**
- **channel_type** (ChannelType) – The channel type.
- **channel_format** (ChannelFormat) – The texture format of the new channel.
- **label** (str, optional) – The label of the channel in case of User channel as type.

**Returns:** The created channel.

**Return type:** Channel

**Raises:**
- **ProjectError** – If no project is opened.
- **ValueError** – If a channel of type `channel_type` already exists in this Texture Set.
- **ValueError** – If a label was provided but `channel_type` is not a user type. Standard channel types have fixed labels.
- **ValueError** – If the stack is invalid.
- **ValueError** – If the Texture Set uses material layering.

**See also:** Stack.all_channels(), Stack.remove_channel(), Stack.edit_channel().

### remove_channel

**remove_channel(channel_type: ChannelType) → None**

Remove a channel from a stack.

> **Note:** `remove_channel` is not available with material layering.

**Parameters:**
- **channel_type** (ChannelType) – The channel type.

**Raises:**
- **ProjectError** – If no project is opened.
- **ValueError** – If there is no channel of type `channel_type` in this Texture Set.
- **ValueError** – If the stack is invalid.
- **ValueError** – If the Texture Set uses material layering.

**See also:** Stack.all_channels(), Stack.add_channel(), Stack.edit_channel().

### edit_channel

**edit_channel(channel_type: ChannelType, channel_format: ChannelFormat, label: str | None = None) → None**

Change the texture format and label of a channel.

**Parameters:**
- **channel_type** (ChannelType) – The channel type.
- **channel_format** (ChannelFormat) – The new texture format of the channel.
- **label** (str, optional) – The label of the channel in case of User channel as type.

**Raises:**
- **ProjectError** – If no project is opened.
- **ValueError** – If there is no stack labeled `stack_id` in this Texture Set.
- **ValueError** – If there is no channel of type `channel_type` in this Texture Set.
- **ValueError** – If a label was provided but `channel_type` is not a user type. Standard channel types have fixed labels.
- **ValueError** – If the stack is invalid.

**See also:** Stack.add_channel(), Stack.remove_channel().

### has_channel

**has_channel(channel_type: ChannelType) → bool**

Check if a channel exists in a stack.

**Parameters:**
- **channel_type** (ChannelType) – The channel type.

**Returns:** `True` if the stack has a channel of the given type, `False` otherwise.

**Return type:** bool

**Raises:**
- **ProjectError** – If no project is opened.
- **ValueError** – If the stack is invalid.

**See also:** Stack.add_channel(), Stack.remove_channel().

### get_channel

**get_channel(channel_type: ChannelType) → Channel**

Get an existing channel from its type.

**Parameters:**
- **channel_type** (Channel) – The channel type.

**Returns:** The channel.

**Return type:** Channel

**Raises:**
- **ProjectError** – If no project is opened.
- **ServiceNotFoundError** – If Substance 3D Painter has not started all its services yet.
- **ValueError** – If the channel doesn't exists.

**See also:** Stack.has_channel(), Stack.add_channel(), Stack.remove_channel().