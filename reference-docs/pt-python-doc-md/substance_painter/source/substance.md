# SourceSubstance

`SourceSubstance` is a type of source where you can connect a substance resource.

For more information, see modules `resource` and `colormanagement`.

## Example

```python
import substance_painter as sp

# Get the currently displayed stack
stack = sp.textureset.get_active_stack()

# Insert a fill layer
position = sp.layerstack.InsertPosition.from_textureset_stack(stack)
fill = sp.layerstack.insert_fill(position)

# Apply "Graphic to Material" in `Material` mode
graphic_to_material = sp.resource.search("s:starterassets "
                                         "u:substance "
                                         'n:"graphictomaterial"')[0]
source = fill.set_material_source(graphic_to_material.identifier())

# Substances can have image inputs which are sources themselves
# In this case, we use the input identifier instead of the channel type to query and edit the source
logo = sp.resource.search("s:starterassets "
                          "u:alpha "
                          'n:"logo painter"')[0]

assert "custom_image" in source.image_inputs
input_source = source.set_source("custom_image", logo)

# `input_source` is now a BitmapSource
# see BitmapSource example for further information on its interface

# In `Material` mode, you can specify how the outputs of the substance are plugged in the fill's channels
default_mapping = {
    sp.textureset.ChannelType.BaseColor: "basecolor",
    sp.textureset.ChannelType.Metallic: "metallic",
    sp.textureset.ChannelType.Roughness: "roughness",
    sp.textureset.ChannelType.Height: "height"
}
for dst_chn, identifier in default_mapping.items():
    assert identifier in source.image_outputs
    source.output_mapping[dst_chn] = identifier

# If not in `Material` mode, choose which output of the substance is active
# source.active_output = "basecolor"

# Retrieve and edit the substance parameters
params = source.get_parameters()
for prop_name in params.keys():
    print(prop_name)

new_params = {
    "outline_color": sp.colormanagement.Color(0.9, 0.7, 0.4),
    "roughness": params["roughness"] / 2,
    # Boolean parameters are treated as integer, if you use `True` or `False` you will get an error message:
    # >>> Bad value for property 'channel_roughness': expected value of type <int32> but got <bool>
    "channel_roughness": 1,
}
source.set_parameters(new_params)

# Query embedded presets and apply the first one
presets = source.get_preset_list()
for preset_name in presets:
    print(preset_name)

if presets:
    source.apply_preset(presets[0])

# Select the Fill layer
sp.layerstack.set_selected_nodes([fill])
```

## SourceSubstance Class

### class substance_painter.source.SourceSubstance(uid)

A class that represents a procedural source.

#### Properties

**property resource_id: ResourceID**
- The current substance resource of the source.
- **Getter**: Returns the resource of the source.
- **Type**: ResourceID

**property output_mapping: OutputMapping**
- The output mapping property in multiple output context.
- **Getter**: Returns the output mapping property.
- **Setter**: Sets the output mapping property.
- **Type**: OutputMapping

**property active_output: str**
- The active output of the source in single output context.
- **Getter**: Returns the output identifier.
- **Setter**: Sets the output identifier.
- **Type**: str

**property mask_output: str**
- The mask output identifier of the source in multiple output context.
- **Getter**: Returns the mask output identifier.
- **Setter**: Sets the mask output identifier.
- **Type**: str

**property image_inputs: List[str]**
- The list of image inputs identifier from the current graph.
- **Getter**: Returns the list of image inputs identifier.
- **Type**: List[str]
- **See also**: `substance_painter.properties.Property`

**property image_outputs: List[str]**
- The list of image outputs identifier from the current graph.
- **Getter**: Returns the list of image outputs identifier.
- **Type**: List[str]

**property resolution: ResolutionOverride**
- The resolution parameters for this substance.
- **Getter**: Returns the resolution parameters.
- **Setter**: Sets the resolution parameters.
- **Type**: ResolutionOverride
- **Raises**: ValueError – If the source is used in a `substance_painter.layerstack.FilterEffectNode`.

#### Methods

**get_source(identifier: str) → SourceUniformColor | SourceBitmap | SourceVectorial | SourceSubstance | SourceReference | SourceFont**
- Get the source for the given input identifier.
- **Parameters**: identifier (str) – The input identifier.
- **Returns**: the source for the input.

**set_source(identifier: str, source: ResourceID | Color | AnchorPointEffectNode) → SourceUniformColor | SourceBitmap | SourceVectorial | SourceSubstance | SourceReference | SourceFont**
- Set the source for the given input identifier.
- **Parameters**:
  - identifier (str) – The input identifier.
  - source (ResourceID | Color | AnchorPointEffectNode) – The source parameter.
- **Returns**: The source for the input.

**reset_source(identifier: str) → None**
- Reset the source for the given input identifier.
- **Parameters**: identifier (str) – The input identifier.

**remove_source(identifier: str) → None**
- Remove the source for the given input identifier.
- **Parameters**: identifier (str) – The input identifier.

**get_parameters() → Dict[str, bool | int | Tuple[int, int] | Tuple[int, int, int] | Tuple[int, int, int, int] | float | Tuple[float, float] | Tuple[float, float, float] | Color | Tuple[Color, float] | Tuple[float, float, float, float] | str]**
- Get source procedural parameters. For each property of the source, the resulting dictionary holds an entry with the property name as key and the property value as value.
- **Returns**: The source procedural parameters.
- **See also**: `substance_painter.source.SourceSubstance.get_properties()`

**set_parameters(property_values: Dict[str, bool | int | Tuple[int, int] | Tuple[int, int, int] | Tuple[int, int, int, int] | float | Tuple[float, float] | Tuple[float, float, float] | Color | Tuple[Color, float] | Tuple[float, float, float, float] | str]) → None**
- Set source procedural parameters.
- **Parameters**: property_values – A dict of properties to be set with their corresponding values.

> **Warning**: Boolean parameters are treated as integer, if you use `True` or `False` you will get an error message:
> `>>> Bad value for property '<property_name>': expected value of type <int32> but got <bool>`

**get_properties() → Dict[str, Property]**
- Get source procedural properties.
- **Returns**: The source procedural properties.
- **See also**: `substance_painter.properties.Property`

**get_preset_list() → List[str]**
- Get the list of all available presets for this source.
- **Returns**: An array of all preset's names available.
- **See also**: `substance_painter.source.SourceSubstance.apply_preset()`

**apply_preset(name: str)**
- Apply a preset given its name. If no preset is found with this name nothing is done.
- **Parameters**: name (str) – The name of the preset to apply.
- **See also**: `substance_painter.source.SourceSubstance.get_preset_list()`

## OutputMapping Class

### class substance_painter.source.OutputMapping(uid)

This class gives access to the output mapping of a source procedural in a dict-like fashion.

Example:
```python
import substance_painter as sp
mapping = a_substance_source.output_mapping
mapping[sp.textureset.ChannelType.BaseColor] = sp.textureset.ChannelType.Specular
for channel in mapping:
    print(mapping[channel])
```