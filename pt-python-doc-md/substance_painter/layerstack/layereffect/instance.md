# Instance Layer

`InstanceLayerNode` is a type of node that allows to synchronize layer parameters across multiple layers and Texture Sets while still being able to generate a mesh dependent result. Only the source layer can be modified.

> **See also:** [Layer instancing documentation](https://helpx.adobe.com/substance-3d-painter/interface/layer-stack/layer-instancing.html)

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

# Create two instances of the Fill layer
insert_position = sp.layerstack.InsertPosition.below_node(my_fill_layer)
instance1 = sp.layerstack.instantiate(insert_position, my_fill_layer)
instance1.set_name("Instance 1")

instance2 = sp.layerstack.instantiate(insert_position, my_fill_layer)
instance2.set_name("Instance 2")

# Print instances of the parent layer
instances = my_fill_layer.instances()
print("Instances of " + my_fill_layer.get_name() + ":")
for instance in instances:
    print("- " + instance.get_name())

# Print parent of each instance
print("Parent of " + instance1.get_name() + ": " + instance1.instance_source().get_name())
print("Parent of " + instance2.get_name() + ": " + instance2.instance_source().get_name())

# Select the Instances
sp.layerstack.set_selected_nodes([instance1, instance2])
```

## Functions and Classes

### `substance_painter.layerstack.instantiate(position, layer)`

Instantiate the given layer.

See the documentation on layer instancing if you are not familiar with the concept: [Layer instancing documentation](https://helpx.adobe.com/substance-3d-painter/interface/layer-stack/layer-instancing.html).

**Parameters:**
- `position` (`InsertPosition`) – Insert position
- `layer` (`LayerNode`) – Layer to instantiate

**Returns:** The inserted node (`InstanceLayerNode`)

**Raises:** `ValueError` – If insertion failed due to an invalid position. See `InsertPosition`.

### `class substance_painter.layerstack.InstanceLayerNode(uid)`

A node allowing manipulation of an Instance layer.

To retrieve the list of `InstanceLayerNode` from the source layer, see `LayerNode.instances()`

#### `instance_source()`

Return the source layer of this instance.

**Returns:** The source layer if this instance (`LayerNode`)
