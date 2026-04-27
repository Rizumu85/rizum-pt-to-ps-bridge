# Paint Layer and Effect

`PaintLayerNode` and `PaintEffectNode` are types of nodes that can be painted on with brushes and particles.

## Examples

```python
import substance_painter as sp

# Get the currently displayed Stack
stack = sp.textureset.get_active_stack()

# Get top position of the Stack
position_stack_top = sp.layerstack.InsertPosition.from_textureset_stack(stack)

# It is also possible to create a Paint Effect with InsertPosition.inside_node()
# sp.layerstack.InsertPosition.inside_node(node, sp.layerstack.NodeStack.Content)
# sp.layerstack.InsertPosition.inside_node(node, sp.layerstack.NodeStack.Mask)

# Insert Paint Layer
my_paint_layer = sp.layerstack.insert_paint(position_stack_top)
my_paint_layer.set_name("My Paint Layer")

# Choose the passthrough Blending Mode
blending_mode = sp.layerstack.BlendingMode.Passthrough
# Check if node has a Blending feature (e.g.: Levels Effect does not)
if my_paint_layer.has_blending():
    # Apply the Blending Mode to the BaseColor Channel
    my_paint_layer.set_blending_mode(blending_mode, sp.textureset.ChannelType.BaseColor)

# Select the Paint layer
sp.layerstack.set_selected_nodes([my_paint_layer])
```

## Functions and Classes

### insert_paint(position: InsertPosition)

Insert a Paint effect or layer (depending on the insert position).

**Parameters:**
- `position` (InsertPosition): Insert position.

**Returns:** 
- Union[PaintLayerNode, PaintEffectNode]: The inserted node.

**Raises:**
- `ValueError`: If insertion failed due to an invalid position. See InsertPosition.

### class PaintLayerNode(uid)

Bases: LayerNode

A node allowing manipulation of a Paint layer.

> **Note:** Strokes are not accessible from the Python API.

### class PaintEffectNode(uid)

Bases: Node

A node allowing manipulation of a Paint effect.

> **Note:** Strokes are not accessible from the Python API.

---

*Part of Substance 3D Painter Python API 0.3.4 documentation*