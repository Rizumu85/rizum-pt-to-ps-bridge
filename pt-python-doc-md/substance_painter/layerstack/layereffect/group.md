# Group Layer

`GroupLayerNode` is a type of layer that can contain other layers. It is used to group layers together to organize the layerstack.

## Examples

```python
import substance_painter as sp

# Get the currently displayed Stack
stack = sp.textureset.get_active_stack()

# Get top position of the Stack
position_stack_top = sp.layerstack.InsertPosition.from_textureset_stack(stack)

# Insert Group layer
my_group_layer = sp.layerstack.insert_group(position_stack_top)
my_group_layer.set_name("My Group Layer")

# Insert Paint layer inside the Group layer
insert_position = sp.layerstack.InsertPosition.inside_node(
    my_group_layer, sp.layerstack.NodeStack.Substack)
my_paint_layer = sp.layerstack.insert_paint(insert_position)

# Insert Fill layer inside the Group layer
my_fill_layer = sp.layerstack.insert_fill(insert_position)
my_fill_layer.set_name("My Fill Layer")

# Expand the Group layer
if (my_group_layer.is_collapsed()):
    my_group_layer.set_collapsed(False)

# Select the Group layer
sp.layerstack.set_selected_nodes([my_group_layer])
```

## Functions and Classes

### `substance_painter.layerstack.insert_group(position: InsertPosition) → GroupLayerNode`

Insert a group layer.

**Parameters:**
- `position` (InsertPosition): The insert position must be either inside a `GroupLayerNode` with `NodeStack.Substack` or above/below a `LayerNode`.

**Returns:**
- `GroupLayerNode`: The inserted node.

**Raises:**
- `ValueError`: If insertion failed due to an invalid position. See `InsertPosition`.

### `class substance_painter.layerstack.GroupLayerNode(uid)`

Bases: `LayerNode`

A node allowing manipulation of a Group layer of the Layer Stack.

#### Methods

##### `sub_layers() → List[LayerNode]`

Query sub layers of this node. Only get the direct children, ordered like in the layer stack.

**Returns:**
- `List[LayerNode]`: The sub layers of this node.

##### `is_collapsed() → bool`

Query if the group is in collapsed state.

**Returns:**
- `bool`: Whether this group is collapsed.

##### `set_collapsed(collapsed: bool)`

Set the collapsed state of the group.

**Parameters:**
- `collapsed` (bool): Whether to collapse the group.
