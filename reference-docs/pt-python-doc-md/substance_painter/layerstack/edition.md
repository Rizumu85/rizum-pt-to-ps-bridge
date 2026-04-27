# Layerstack Edition

The layerstack module allows the insertion and deletion of layers and effects.

## Example

```python
import substance_painter as sp

# Get the currently displayed stack
stack = sp.textureset.get_active_stack()

# Get all Layer nodes at the root of the stack
stack_root_nodes = sp.layerstack.get_root_layer_nodes(stack)
# Find the layer at the very bottom
bottom_layer = stack_root_nodes[len(stack_root_nodes) - 1]

# Create the position where to insert the Group
# Get the very bottom Layer Position
position_stack_bottom = sp.layerstack.InsertPosition.below_node(bottom_layer)

# Insert the Group Layer
my_group = sp.layerstack.insert_group(position_stack_bottom)
my_group.set_name("My Group")
my_group.set_collapsed(False)

# Insert a Fill Layer into the group and assign a Material from the starter asset library
position_group_content = sp.layerstack.InsertPosition.inside_node(
    my_group, sp.layerstack.NodeStack.Substack)
# Insert Fill Layer
my_fill_layer = sp.layerstack.insert_fill(position_group_content)
my_fill_layer.set_name("My Fill Layer")
# Search and isolate a Substance material
fill_layer_resource = sp.resource.search("s:starterassets "
                                         "u:substance "
                                         "n:Paper\\ Grainy=")[0]
# Apply material from the library Substance ID in the Fill Layer
my_fill_layer.set_material_source(fill_layer_resource.identifier())

# Insert Fill effect into the "my_fill_layer"'s effect stack
position_effect_stack = sp.layerstack.InsertPosition.inside_node(
    my_fill_layer, sp.layerstack.NodeStack.Content)

my_fill_effect = sp.layerstack.insert_fill(position_effect_stack)
my_fill_effect.set_name("My Fill Effect")

# Insert Fill effect into the "my_fill_layer"'s mask effects stack
if not my_fill_layer.has_mask():  # If Layer has no Mask, create it
    mask_background = sp.layerstack.MaskBackground.White  # Create Background Color for the mask
    my_fill_layer.add_mask(mask_background)  # Add a mask to the Fill Layer
position_mask_effect_stack = sp.layerstack.InsertPosition.inside_node(
    my_fill_layer, sp.layerstack.NodeStack.Mask)

my_mask_fill_effect = sp.layerstack.insert_fill(position_mask_effect_stack)
my_mask_fill_effect.set_name("My Mask Fill Effect")

# We can notice, in the lines above, that the same 'insert_fill()' method
# is called to create either a Fill Layer, a Fill Effect or a mask fill effect.
# Paint Layers insertion will work the same using 'insert_paint()'

# Insert a Blur Filter Effect in "my_fill_layer" stack
filter_resource = sp.resource.search("s:starterassets "
                                     "u:filter "
                                     "n:Blur=")[0]
sp.layerstack.insert_filter_effect(position_effect_stack, filter_resource.identifier())

# Insert a Smart Material from the library into "My Group"
# Get the first Smart Material named 'Bronze Armor' in the starter asset library
smart_mat_resource = sp.resource.search("s:starterassets "
                                        "u:smartmaterial "
                                        "n:Bronze\\ Armor=")[0]
# Insert smart material in the group and connect a resource found into the library
sp.layerstack.insert_smart_material(position_group_content, smart_mat_resource.identifier())
```

## Insertion

Insertion of a layer or an effect can be done by using one of the following functions. For more details, see Layers and effects.

- `substance_painter.layerstack.insert_paint()`
- `substance_painter.layerstack.insert_fill()`
- `substance_painter.layerstack.insert_generator_effect()`
- `substance_painter.layerstack.insert_filter_effect()`
- `substance_painter.layerstack.insert_levels_effect()`
- `substance_painter.layerstack.insert_compare_mask_effect()`
- `substance_painter.layerstack.insert_color_selection_effect()`
- `substance_painter.layerstack.insert_group()`
- `substance_painter.layerstack.instantiate()`
- `substance_painter.layerstack.insert_anchor_point_effect()`
- `substance_painter.layerstack.insert_smart_mask()`
- `substance_painter.layerstack.insert_smart_material()`

### `InsertPosition`

`InsertPosition` is the object used by all the insert methods to express where you want the insertion to happen in the layer stack hierarchy.

Create instances using the appropriate static methods depending on what you want to do. See the following examples.

```python
import substance_painter as sp

# Insert at the top of the given textureset layer stack
insert_position = sp.layerstack.InsertPosition.from_textureset_stack(
    sp.textureset.get_active_stack())
new_layer = sp.layerstack.insert_fill(insert_position)
new_layer.set_name("First layer")

# Insert a layer above new_layer
insert_position = sp.layerstack.InsertPosition.above_node(new_layer)
sp.layerstack.insert_fill(insert_position)

# Insert an effect in the content stack of new_layer
insert_position = sp.layerstack.InsertPosition.inside_node(
    new_layer, sp.layerstack.NodeStack.Content)
new_effect = sp.layerstack.insert_fill(insert_position)
new_effect.set_name("First effect")

# Insert an effect below new_effect
insert_position = sp.layerstack.InsertPosition.below_node(new_effect)
sp.layerstack.insert_fill(insert_position)
```

#### Static Methods

- **Parameters:**
  - `node_id` (int)
  - `node_stack` (int | None)

- **`from_textureset_stack(stack)`** - Generate an InsertPosition on the top of a stack. Only a LayerNode can be inserted at the top of the stack. For more details, see Insertion rules when node is a LayerNode.

- **`above_node(node)`** - Generate an InsertPosition to insert above the given node. Only a LayerNode can be inserted above a LayerNode. Only an EffectNode can be inserted above an EffectNode. For more details, see Insertion rules when node is a LayerNode and Insertion rules when node is an EffectNode.

- **`below_node(node)`** - Generate an InsertPosition to insert below the given node. Only a LayerNode can be inserted above a LayerNode. Only an EffectNode can be inserted above an EffectNode. For more details, see Insertion rules when node is a LayerNode and Insertion rules when node is an EffectNode.

- **`inside_node(node, node_stack)`** - Generate an InsertPosition to insert inside the given stack of a node. Only a LayerNode can be inserted inside a GroupLayerNode if `node_stack` is `NodeStack.Substack`. Only an EffectNode can be inserted inside a LayerNode if `node_stack` is `NodeStack.Content` or `NodeStack.Mask`. For more details, see Insertion rules when node is a LayerNode and Insertion rules when node is an EffectNode.

### Insertion Rules

#### When node is a LayerNode

| Node type | From textureset stack / Above node / Below node / Inside node (Substack) | Inside node (Content) | Inside node (Mask) |
|-----------|---------------------------------------------------------------------------|----------------------|-------------------|
| Paint | x | x | x |
| Fill | x | x | x |
| Generator | | x | x |
| Filter | | x | x |
| Levels | | x | x |
| Compare Mask | | | x |
| Color Selection | | | x |
| Group | x | | |
| Anchor Point | | x | x |
| Smart Mask | | | x |
| Smart Material | x | | |
| Instance | x | | |

#### When node is an EffectNode

| Node type | From textureset stack / Inside node | Node in Content stack: Above node / Below node | Node in Mask stack: Above node / Below node |
|-----------|-------------------------------------|-----------------------------------------------|---------------------------------------------|
| Paint | | x | x |
| Fill | | x | x |
| Generator | | x | x |
| Filter | | x | x |
| Levels | | x | x |
| Compare Mask | | | x |
| Color Selection | | | x |
| Group | | | |
| Anchor Point | | x | x |
| Smart Mask | | | x |
| Smart Material | | | |
| Instance | | | |

### `ScopedModification`

`ScopedModification` can be used to group many layerstack modification calls in a single undoable command. The name will be displayed in the software history.

This object is useful to:
- Avoid polluting the history by grouping logically layerstack modifications behind a unique name.
- The computation will only happen when we leave the `with` statement, meaning that we don't waste time computing intermediary results that we don't need.

This object is a context manager usable with the python `with` statement.

```python
import substance_painter as sp

def insert_many_fills():
    # Insert many layers inside the current texture set layer stack
    # and set their projection mode to tri-planar
    insert_position = sp.layerstack.InsertPosition.from_textureset_stack(
        sp.textureset.get_active_stack())
    fill = sp.layerstack.insert_fill(insert_position)
    fill.set_projection_mode(sp.layerstack.ProjectionMode.Triplanar)
    fill = sp.layerstack.insert_fill(insert_position)
    fill.set_projection_mode(sp.layerstack.ProjectionMode.Triplanar)
    fill = sp.layerstack.insert_fill(insert_position)
    fill.set_projection_mode(sp.layerstack.ProjectionMode.Triplanar)

# With the ScopedModification below, only one entry will be added to Painter
# history. A single undo will remove all the fills inserted inside.
with sp.layerstack.ScopedModification("Insert many layers"):
    insert_many_fills()
```

### `NodeStack`

Indicate which node stack you want to insert in:

- **`Substack`** - Insert in the substack of a node (only valid for a Folder node)
- **`Content`** - Insert in the content stack of the node
- **`Mask`** - Insert in the mask stack of the node

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

## Deletion

### `delete_node(node)`

Delete the given node.

**Parameters:**
- `node` (Node) - Node to delete