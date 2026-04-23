# Generator Effect

`GeneratorEffectNode` is an effect that takes a Generator substance as input. Generator substances generate a mask or a material based on the mesh topology using the additional maps setup in the TextureSet Settings.

**See also:** [Generator effect documentation](https://helpx.adobe.com/substance-3d-painter/features/effects/generator.html), [Generator substance documentation](https://helpx.adobe.com/substance-3d-painter/content/creating-custom-effects/generators.html).

## Examples

```python
import substance_painter as sp

# Get the currently displayed Stack
stack = sp.textureset.get_active_stack()

# Get top position of the Stack
position_stack_top = sp.layerstack.InsertPosition.from_textureset_stack(stack)

# Insert Fill Layer
my_fill_layer = sp.layerstack.insert_fill(position_stack_top)
my_fill_layer.set_name("My Fill Layer")

# Add a black Mask
my_fill_layer.add_mask(sp.layerstack.MaskBackground.Black)

# Add a Generator effect with Ambient Occlusion mask generator in the Fill layer mask stack
insertion_position = sp.layerstack.InsertPosition.inside_node(my_fill_layer,
                                                              sp.layerstack.NodeStack.Mask)
generator_resource = sp.resource.search("s:starterassets "
                                        "u:generator "
                                        "n:Ambient Occlusion")[0]
my_generator = sp.layerstack.insert_generator_effect(insertion_position,
                                                     generator_resource.identifier())

# Select the Generator effect
sp.layerstack.set_selected_nodes([my_generator])
```

## Functions and Classes

### insert_generator_effect()

```python
substance_painter.layerstack.insert_generator_effect(
    position: InsertPosition, 
    generator_substance: ResourceID | None = None
) → GeneratorEffectNode
```

Insert a Generator effect, either empty or with the given filter resource.

**Parameters:**
- `position` (InsertPosition): The insert position must be either inside a `LayerNode` with `NodeStack.Content` or `NodeStack.Mask` or above/below an `EffectNode`.
- `generator_substance` (Optional[ResourceID]): Resource to use as generator. The resource must have a `Usage.GENERATOR` usage.

**Returns:** The inserted node (GeneratorEffectNode)

**Raises:**
- `ValueError`: If insertion failed due to an invalid position.
- `ValueError`: If generator_substance is not a valid resource or does not have `Usage.GENERATOR` usage.

### GeneratorEffectNode

```python
class substance_painter.layerstack.GeneratorEffectNode(uid)
```

A node allowing manipulation of a Generator effect.

**Inherits from:** ActiveChannelsMixin, Node

#### Methods

##### get_source()

```python
get_source() → SourceSubstance
```

Get the source procedural of the generator, or None if no generator is set.

**Returns:** The generator's source (SourceSubstance)

##### set_source()

```python
set_source(res: ResourceID) → SourceSubstance
```

Create and assign a source from the given resource and return the created source. The resource must have a `Usage.GENERATOR` usage.

**Parameters:**
- `res` (ResourceID): The generator material to apply.

**Returns:** The generator's source (SourceSubstance)

**Raises:**
- `ValueError`: If res is not a valid resource or does not have `Usage.GENERATOR` usage.

##### remove_source()

```python
remove_source() → None
```

Remove the currently used source.

#### Properties

##### active_channels

```python
property active_channels: Set[ChannelType]
```

The set of active channels of the source.

**Getter:** Returns the active channels of the source. To get the list of channels for a given stack, see `substance_painter.textureset.Stack.all_channels()`.

**Setter:** Sets the active channels of the source, channels not listed will be disabled.

**Type:** Set[ChannelType]