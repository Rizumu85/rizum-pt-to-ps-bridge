# Layerstack Selection

The layerstack module allows the selection of layers and effects.

## Examples

### Specific channel activation

```python
# This example shows how to activate specific channels on selected nodes in the layerstack.
# Before running this example, open a project and select some layers/effects from the UI

import substance_painter as sp

# Get the active stack
stack = sp.textureset.get_active_stack()
# Get the selected nodes in the layerstack
selected_nodes = sp.layerstack.get_selected_nodes(stack)
updated_nodes = []

# Iterate over the selected nodes
for node in selected_nodes:
    if type(node) is sp.layerstack.FillLayerNode or type(node) is sp.layerstack.FillEffectNode:
        # Set the active channels of the Fill to BaseColor
        node.active_channels = {sp.layerstack.ChannelType.BaseColor}
        updated_nodes.append(node)

# Select the edited nodes
sp.layerstack.set_selected_nodes(updated_nodes)
```

## Get Selection

### `get_selected_nodes(stack: Stack)`

Get the selected nodes of a Stack, ordered like in the layer stack.

**Parameters:**
- `stack` (Stack): Stack to query.

**Returns:**
- List of selected nodes of the stack.

**Return type:**
- List[LayerNode | GroupLayerNode | PaintLayerNode | InstanceLayerNode | FillLayerNode | GeneratorEffectNode | PaintEffectNode | FillEffectNode | LevelsEffectNode | CompareMaskEffectNode | FilterEffectNode | ColorSelectionEffectNode | AnchorPointEffectNode]

### `get_selection_type(layer: LayerNode)`

Return which part of a layer is selected (content, mask, etc…).

**Parameters:**
- `layer` (LayerNode): Layer to query.

**Raises:**
- ValueError: If the layer doesn't belong to the currently selected texture set.

**Returns:**
- The part of the layer that is selected.

**Return type:**
- SelectionType

## Set Selection

### `set_selected_nodes(nodes: List[GeneratorEffectNode | PaintEffectNode | FillEffectNode | LevelsEffectNode | CompareMaskEffectNode | FilterEffectNode | ColorSelectionEffectNode | AnchorPointEffectNode] | List[LayerNode])`

Select the given nodes in the layer stack UI.

**Parameters:**
- `nodes` (List[GeneratorEffectNode | PaintEffectNode | FillEffectNode | LevelsEffectNode | CompareMaskEffectNode | FilterEffectNode | ColorSelectionEffectNode | AnchorPointEffectNode] | List[LayerNode]): Nodes to select.

**Raises:**
- ValueError: If the nodes don't belong to the currently selected texture set.
- RuntimeError: If called from a ScopedModification section

### `set_selection_type(layer: LayerNode, layer_selection_type: SelectionType)`

Select which part of the layer you want to select.

**Parameters:**
- `layer` (LayerNode): Layer to select.
- `layer_selection_type` (SelectionType): Part of the layer you want to select (content, mask, etc…).

**Raises:**
- ValueError: If the layer doesn't belong to the currently selected texture set.
- RuntimeError: If called from a ScopedModification section

## Enums

### SelectionType

| Name | Description |
|------|-------------|
| `Content` | Select the layer content |
| `Mask` | Select the layer mask |
| `GeometryMask` | Select the layer geometry mask |
| `Properties` | Select the layer properties. Only available for instances. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).
