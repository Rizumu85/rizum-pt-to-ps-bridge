# Filter Effect

`FilterEffectNode` is an effect that takes a Filter substance as input. Filter substances transforms the content of a layer or mask.

**See also**: [Filter effect documentation](https://helpx.adobe.com/substance-3d-painter/features/effects/filter.html), [Generic filter documentation](https://helpx.adobe.com/substance-3d-painter/content/creating-custom-effects/generic-filter.html), [Channel specific filter documentation](https://helpx.adobe.com/substance-3d-painter/content/creating-custom-effects/channel-specific-filter.html).

## Examples

```python
import substance_painter as sp

# Get the currently displayed Stack
stack = sp.textureset.get_active_stack()

# Get top position of the Stack
position_stack_top = sp.layerstack.InsertPosition.from_textureset_stack(stack)

# Insert Paint Layer
my_paint_layer = sp.layerstack.insert_paint(position_stack_top)
my_paint_layer.set_name("My Paint Layer")

# Choose the passthrough Blending Mode
blending_mode = sp.layerstack.BlendingMode.Passthrough
# Check if node has a Blending feature (e.g.: Levels Effect does not)
if my_paint_layer.has_blending():
    # Apply the Blending Mode to the BaseColor Channel
    my_paint_layer.set_blending_mode(blending_mode, sp.textureset.ChannelType.BaseColor)

# Add a Filter effect with a Sharpen filter in the Paint layer content stack
insert_position = sp.layerstack.InsertPosition.inside_node(
    my_paint_layer, sp.layerstack.NodeStack.Content)

filter_resource = sp.resource.search("s:starterassets "
                                     "u:filter "
                                     "n:Sharpen")[0]
my_filter_effect = sp.layerstack.insert_filter_effect(insert_position, filter_resource.identifier())

# Select the Filter effect
sp.layerstack.set_selected_nodes([my_filter_effect])
```

## Functions and Classes

### `substance_painter.layerstack.insert_filter_effect(position, filter_substance=None)`

Insert a filter effect, either empty or with the given filter resource.

**Parameters:**
- `position` (InsertPosition): The insert position must be either inside a `LayerNode` with `NodeStack.Content` or `NodeStack.Mask` or above/below an `EffectNode`.
- `filter_substance` (Optional[ResourceID]): Resource to use as filter. The resource must have a `Usage.FILTER` usage.

**Returns:** The inserted node (FilterEffectNode)

**Raises:**
- `ValueError`: If insertion failed due to an invalid position. See `InsertPosition`.
- `ValueError`: If `filter_substance` is not a valid resource or does not have `Usage.FILTER` usage.

### `class FilterEffectNode(uid)`

A node allowing manipulation of a Filter effect.

**Base classes:** `ActiveChannelsMixin`, `Node`

#### Methods

##### `get_source()`

Get the source procedural of the filter, or None if no filter is set.

**Returns:** The filter's source (SourceSubstance)

##### `set_source(res)`

Create and assign a source from the given resource and return the created source. The resource must have a `Usage.FILTER` usage.

**Parameters:**
- `res` (ResourceID): The filter material to apply.

**Returns:** The filter's source (SourceSubstance)

**Raises:**
- `ValueError`: If `res` is not a valid resource or does not have `Usage.FILTER` usage.

##### `remove_source()`

Remove the currently used source.

**Returns:** None

#### Properties

##### `active_channels`

The set of active channels of the source.

**Type:** Set[ChannelType]

**Getter:** Returns the active channels of the source. To get the list of channels for a given stack, see `substance_painter.textureset.Stack.all_channels()`.

**Setter:** Sets the active channels of the source, channels not listed will be disabled.