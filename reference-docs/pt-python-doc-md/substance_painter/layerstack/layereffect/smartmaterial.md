# Smart Material

Smart Materials are presets of layers. They can be used to save and re-use complex setup of layers across projects that adapt to the 3D model.

> **See also**: [Smart Material documentation](https://helpx.adobe.com/substance-3d-painter/features/smart-materials-and-masks.html)

## Examples

```python
import substance_painter as sp

# Get the currently displayed Stack
stack = sp.textureset.get_active_stack()

# Get top position of the Stack
position_stack_top = sp.layerstack.InsertPosition.from_textureset_stack(stack)

# Insert a Smart Material
smart_material = sp.resource.search("s:starterassets "
                                    "u:smartmaterial "
                                    "n:Aluminium ")[0]
my_smart_material = sp.layerstack.insert_smart_material(
    position_stack_top, smart_material.identifier())

# Print the name of the parent layer node
print(my_smart_material.get_name())

# Select the layers contained by the parent layer
sp.layerstack.set_selected_nodes(my_smart_material.sub_layers())
```

## Functions and Classes

### `substance_painter.layerstack.insert_smart_material(position, smart_material)`

Insert a smart material at the given position.

**Parameters:**
- `position` (`InsertPosition`): The insert position must be either inside a `GroupLayerNode` with `NodeStack.Substack` or above/below a `LayerNode`.
- `smart_material` (`substance_painter.resource.ResourceID`): The smart material to instantiate. The resource must have a `Usage.SMART_MATERIAL` usage.

**Returns:**
- `GroupLayerNode`: The inserted node.

**Raises:**
- `ValueError`: If insertion failed due to an invalid `position`. See `InsertPosition`.
- `ValueError`: If `smart_material` is not a valid resource or does not have `Usage.SMART_MATERIAL` usage.

### `substance_painter.layerstack.create_smart_material(group, name)`

Create a smart material with name `name` from the given `group`.

**Parameters:**
- `group` (`GroupLayerNode`): The root folder of the smart material.
- `name` (`str`): The name of the smart material.

**Returns:**
- `Resource`: The created smart material as a resource.
