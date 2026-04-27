# Smart Mask

Smart Masks are presets of the mask effect stack. They can be used to save and re-use complex mask configurations across projects.

**See also:** [Smart Mask documentation](https://helpx.adobe.com/substance-3d-painter/features/smart-materials-and-masks.html)

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

# Add a mask
my_fill_layer.add_mask(sp.layerstack.MaskBackground.Black)

# Insert a Smart Mask in the mask stack
insert_position = sp.layerstack.InsertPosition.inside_node(
    my_fill_layer, sp.layerstack.NodeStack.Mask)
smart_mask = sp.resource.search("s:starterassets "
                                "u:smartmask "
                                "n:Concrete Edges ")[0]
my_smart_mask = sp.layerstack.insert_smart_mask(insert_position, smart_mask.identifier())

# Select all the effects contained in the Smart Mask preset
sp.layerstack.set_selected_nodes(my_smart_mask)
```

## Functions and Classes

### `substance_painter.layerstack.insert_smart_mask(position: InsertPosition, smart_mask: ResourceID) → List[EffectNode]`

Insert a smart mask in a mask stack.

**Parameters:**
- `position` (InsertPosition): The insert position must be either inside a LayerNode with NodeStack.Mask or above/below an EffectNode in the mask stack.
- `smart_mask` (substance_painter.resource.ResourceID): The smart mask to instantiate. The resource must have a Usage.SMART_MASK usage.

**Returns:** The inserted nodes.

**Return type:** List[EffectNode]

**Raises:**
- `ValueError`: If insertion failed due to an invalid `position`. See InsertPosition.
- `ValueError`: If `smart_mask` is not a valid resource or does not have Usage.SMART_MASK usage.

### `substance_painter.layerstack.create_smart_mask(layer: LayerNode, name: str) → Resource`

Create a smart mask with name `name` from the mask stack of the given `layer`.

**Parameters:**
- `layer` (LayerNode): The parent layer of the mask stack to create.
- `name` (str): The name of the smart mask.

**Returns:** The created smart mask as a resource.

**Return type:** Resource