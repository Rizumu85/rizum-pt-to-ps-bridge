# Compare Mask Effect

`CompareMaskEffectNode` is an effect that allows to quickly and easily compare two channels and produce a mask as a result. It can only be used in a mask effect stack.

**See also:** [Compare Mask effect documentation](https://helpx.adobe.com/substance-3d-painter/features/effects/compare-mask.html)

## Examples

```python
import substance_painter as sp

# Get the currently displayed Stack
stack = sp.textureset.get_active_stack()

# Get top position of the Stack
position_stack_top = sp.layerstack.InsertPosition.from_textureset_stack(stack)

# Insert Fill Layer
my_fill_layer_base = sp.layerstack.insert_fill(position_stack_top)
my_fill_layer_base.set_name("Base")

# Set a material in the Fill layer
aluminium_material = sp.resource.search("s:starterassets "
                                        "u:substance "
                                        "n:Clay")[0]
my_fill_layer_base.set_material_source(aluminium_material.identifier())

# Insert second Fill Layer
my_fill_layer_snow = sp.layerstack.insert_fill(position_stack_top)
my_fill_layer_snow.set_name("Snow")

# Add a mask and a Compare Mask in the mask stack
my_fill_layer_snow.add_mask(sp.layerstack.MaskBackground.Black)
inside_mask = sp.layerstack.InsertPosition.inside_node(
    my_fill_layer_snow, sp.layerstack.NodeStack.Mask)
my_compare_mask_effect = sp.layerstack.insert_compare_mask_effect(inside_mask)

# Update the Compare Mask parameters
parameters = my_compare_mask_effect.get_parameters()
parameters.channel = sp.layerstack.ChannelType.Roughness
parameters.hardness = 0.5
my_compare_mask_effect.set_parameters(parameters)

# Select the Compare Mask effect
sp.layerstack.set_selected_nodes([my_compare_mask_effect])
```

## Functions and Classes

### insert_compare_mask_effect

```python
substance_painter.layerstack.insert_compare_mask_effect(position: InsertPosition) → CompareMaskEffectNode
```

Insert a compare mask effect with default parameters.

**Parameters:**
- `position` (InsertPosition): The insert position must be either inside a `LayerNode` with `NodeStack.Mask` or above/below an `EffectNode` in the mask stack.

**Returns:**
- `CompareMaskEffectNode`: The inserted node.

**Raises:**
- `ValueError`: If insertion failed due to an invalid position.

### CompareMaskEffectNode

```python
class substance_painter.layerstack.CompareMaskEffectNode(uid)
```

A node allowing manipulation of a Compare Mask effect.

**Base class:** `Node`

**See also:** [Compare Mask effect documentation](https://helpx.adobe.com/substance-3d-painter/features/effects/compare-mask.html)

#### Methods

##### get_parameters()

```python
get_parameters() → CompareMaskEffectParams
```

Get the current parameters of this compare mask effect.

**Returns:**
- `CompareMaskEffectParams`: The current parameters of this compare mask effect.

##### set_parameters()

```python
set_parameters(params: CompareMaskEffectParams) → None
```

Set new parameters of this compare mask effect.

**Parameters:**
- `params` (CompareMaskEffectParams): The new parameters.

## Parameters

### CompareMaskEffectParams

```python
class substance_painter.layerstack.CompareMaskEffectParams(
    channel: ChannelType,
    left_operand: CompareMaskEffectOperand,
    right_operand: CompareMaskEffectOperand,
    operation: CompareMaskEffectOperation,
    constant: float,
    tolerance: float,
    hardness: float
)
```

A compare mask effect parameters.

**Parameters:**
- `channel` (ChannelType): The channel to compare between the source and the target to create a mask from. Only used when some operands refers to Layers.
- `left_operand` (CompareMaskEffectOperand): The left operand of the comparison.
- `right_operand` (CompareMaskEffectOperand): The right operand of the comparison.
- `operation` (CompareMaskEffectOperation): The comparison operation to perform.
- `constant` (float): Value to compare against when some operand is `CompareMaskEffectOperand.Constant`. Between 0.0 and 1.0.
- `tolerance` (float): Tolerance value to use when operation is `CompareMaskEffectOperation.WithinTolerance`. Between 0.0 and 1.0.
- `hardness` (float): Controls the smoothness/hardness of the resulting mask comparison. Between 0.0 and 1.0.

### CompareMaskEffectOperand

```python
class substance_painter.layerstack.CompareMaskEffectOperand(value)
```

**See also:** [Compare Mask effect documentation](https://helpx.adobe.com/substance-3d-painter/features/effects/compare-mask.html) for a complete description of the compare mask effect.

**Members:**

| Name | Description |
|------|-------------|
| `LayersBelow` | Flattened version of all the layers below the current one. |
| `ThisLayer` | This layer only. |
| `ThisMask` | Existing content of the mask. |
| `Constant` | Uniform value. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### CompareMaskEffectOperation

```python
class substance_painter.layerstack.CompareMaskEffectOperation(value)
```

**Members:**

| Name | Description |
|------|-------------|
| `LesserThan` | Output white values if source has lower values than the target. |
| `WithinTolerance` | Output white values if source has similar values than the target. |
| `GreaterThan` | Output white values if source has higher values than the target. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).
