# Color Selection Effect

`ColorSelectionEffectNode` is an effect that allows to extract one or more colors from a bitmap (usually a mesh based ID map) to build a black and white mask. It can only be used in a mask effect stack.

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

# Add a mask and a Color Selection effect in the mask stack
my_fill_layer.add_mask(sp.layerstack.MaskBackground.Black)
inside_mask = sp.layerstack.InsertPosition.inside_node(
    my_fill_layer, sp.layerstack.NodeStack.Mask)
my_color_selection_effect = sp.layerstack.insert_color_selection_effect(inside_mask)

# Update the Color Selection effect parameters
parameters = my_color_selection_effect.get_parameters()
# Add red, green and blue colors
parameters.colors = [
    sp.colormanagement.Color(1.0, 0.0, 0.0),
    sp.colormanagement.Color(0.0, 1.0, 0.0),
    sp.colormanagement.Color(0.0, 0.0, 1.0)]
my_color_selection_effect.set_parameters(parameters)

# Select the Color Selection effect
sp.layerstack.set_selected_nodes([my_color_selection_effect])
```

## Functions and Classes

### insert_color_selection_effect

```python
substance_painter.layerstack.insert_color_selection_effect(position: InsertPosition) → ColorSelectionEffectNode
```

Insert a color selection effect.

**Parameters:**
- `position` (InsertPosition): The insert position must be either inside a `LayerNode` with `NodeStack.Mask` or above/below an `EffectNode` in the mask stack.

**Returns:**
- `ColorSelectionEffectNode`: The inserted node.

**Raises:**
- `ValueError`: If insertion failed due to an invalid `position`. See `InsertPosition`.

### ColorSelectionEffectNode

```python
class substance_painter.layerstack.ColorSelectionEffectNode(uid)
```

Bases: `Node`

A node allowing manipulation of a Color Selection effect.

#### Methods

##### get_parameters()

```python
get_parameters() → ColorSelectionEffectParams
```

Get the current parameters of this color selection effect.

**Returns:**
- `ColorSelectionEffectParams`: The current parameters of this color selection effect.

##### set_parameters()

```python
set_parameters(params: ColorSelectionEffectParams) → None
```

Set new parameters of this compare mask effect.

**Parameters:**
- `params` (ColorSelectionEffectParams): The new parameters.

**Raises:**
- `ResourceNotFoundError`: If the resource `params.id_mask` is not found or is not of `Type.IMAGE`.

## Parameters

### ColorSelectionEffectParams

```python
class substance_painter.layerstack.ColorSelectionEffectParams(
    id_mask: ResourceID | None,
    output_value: float,
    hardness: float,
    tolerance: float,
    background_color: ColorSelectionBackgroundColor,
    colors: List[Color]
)
```

A color selection effect parameters.

**Parameters:**
- `id_mask` (ResourceID | None): Which color map to use. Typically the ID Mask baked map. Must have `Usage.TEXTURE` and be part of the project.
- `output_value` (float): Output value when selection matches. Between 0.0 and 1.0.
- `hardness` (float): Hardness of the selection. Between 0.0 and 1.0.
- `tolerance` (float): Tolerance of the selection. Between 0.0 and 1.0.
- `background_color` (ColorSelectionBackgroundColor): Output value when selection does not match.
- `colors` (List[Color]): List of colors to match in the id_mask.

### ColorSelectionBackgroundColor

```python
class substance_painter.layerstack.ColorSelectionBackgroundColor(value)
```

**Members:**

| Name | Description |
|------|-------------|
| `Transparent` | Filter background is transparent. |
| `Black` | Filter background is black. |
| `White` | Filter background is white. |
| `Gray` | Filter background is grey. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).
