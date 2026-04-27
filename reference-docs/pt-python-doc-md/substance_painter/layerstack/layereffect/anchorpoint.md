# Anchor Point

`AnchorPointEffectNode` is a type of node that allows to expose any resource or element in the layer stack and reference it in different areas of the layer stack for different purposes and with a different set of adjustments.

**See also:** [Anchor Point documentation](https://helpx.adobe.com/substance-3d-painter/features/effects/anchor-point.html)

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

# Apply a material
aluminium_material = sp.resource.search("s:starterassets "
                                        "u:substance "
                                        "n:metal")[0]
my_fill_layer.set_material_source(aluminium_material.identifier())

# Add an anchor point
insert_position = sp.layerstack.InsertPosition.inside_node(
    my_fill_layer, sp.layerstack.NodeStack.Content)
anchor_point = sp.layerstack.insert_anchor_point_effect(insert_position, "My Anchor Point")

# Insert Fill Layer
my_fill_layer2 = sp.layerstack.insert_fill(position_stack_top)
my_fill_layer2.set_name("My Fill Layer 2")

# Add a black mask and a fill effect in the mask stack
my_fill_layer2.add_mask(sp.layerstack.MaskBackground.Black)
insert_position = sp.layerstack.InsertPosition.inside_node(
    my_fill_layer2, sp.layerstack.NodeStack.Mask)
my_fill_effect = sp.layerstack.insert_fill(insert_position)

# Load the anchor point on the Fill effect
my_fill_effect.set_source(None, anchor_point) # Use None as the mask stack is mono-channel

# Print the parent of the Anchor Point
print("Parent of " + anchor_point.get_name() + ": " + anchor_point.get_parent().get_name())

# Select the Fill effect
sp.layerstack.set_selected_nodes([my_fill_effect])
```

## Functions and Classes

### insert_anchor_point_effect

```python
substance_painter.layerstack.insert_anchor_point_effect(position: InsertPosition, name: str) → AnchorPointEffectNode
```

Insert an anchor point effect.

**Parameters:**
- **position** (`InsertPosition`) – The insert position must be either inside a `LayerNode` with `NodeStack.Content` or `NodeStack.Mask` or above/below an `EffectNode`.
- **name** (`str`) – Name of the anchor point.

**Returns:**
- `AnchorPointEffectNode` – The new anchor point.

**Raises:**
- `ValueError` – If insertion failed due to an invalid position. See `InsertPosition`.

### AnchorPointEffectNode

```python
class substance_painter.layerstack.AnchorPointEffectNode(uid)
```

A node allowing manipulation of an Anchor Point effect.