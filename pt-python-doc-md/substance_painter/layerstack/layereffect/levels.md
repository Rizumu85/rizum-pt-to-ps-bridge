# Levels Effect

`LevelsEffectNode` is an effect used to adjust the color ranges of an image. It allows to balance and tone colors and/or grayscales values.

**See also:** [Levels effect documentation](https://helpx.adobe.com/substance-3d-painter/features/effects/levels.html)

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

# Load noise into Metallic channel
noise_resource = sp.resource.search("s:starterassets "
                                    "u:procedural "
                                    "n:3D Perlin Noise")[0]
my_fill_layer.set_source(sp.layerstack.ChannelType.Metallic, noise_resource.identifier())

# Add a Levels effect in the content stack
inside_content = sp.layerstack.InsertPosition.inside_node(
    my_fill_layer, sp.layerstack.NodeStack.Content)
my_levels_effect = sp.layerstack.insert_levels_effect(inside_content)

# Update the affected channel to Metallic
my_levels_effect.affected_channel = sp.layerstack.ChannelType.Metallic

# Update the Levels effect parameters
parameters = my_levels_effect.get_parameters()
# Note: `parameters` is a LevelsParamsMono because Metallic channel has only a luminance channel
parameters.input_min = 0.25
parameters.input_max = 0.75
my_levels_effect.set_parameters(parameters)

# Select the Levels effect
sp.layerstack.set_selected_nodes([my_levels_effect])
```

## Functions and Classes

### insert_levels_effect()

```python
substance_painter.layerstack.insert_levels_effect(position: InsertPosition) → LevelsEffectNode
```

Insert a levels effect with default parameters.

**Parameters:**
- `position` (InsertPosition): The insert position must be either inside a `LayerNode` with `NodeStack.Content` or `NodeStack.Mask` or above/below an `EffectNode`.

**Returns:**
- `LevelsEffectNode`: The inserted node.

**Raises:**
- `ValueError`: If insertion failed due to an invalid `position`. See `InsertPosition`.

### LevelsEffectNode

```python
class substance_painter.layerstack.LevelsEffectNode(uid)
```

A node allowing manipulation of a Levels effect.

**Base class:** `Node`

**See also:** [Levels effect documentation](https://helpx.adobe.com/substance-3d-painter/features/effects/levels.html)

#### Properties

##### affected_channel

```python
property affected_channel: ChannelType
```

The channel affected by the current level effect.

- **Getter:** Returns the affected channel.
- **Setter:** Set the affected channel.
- **Type:** `ChannelType`

#### Methods

##### get_parameters()

```python
get_parameters() → LevelsParamsMono | LevelsParamsRGB
```

Get the current parameters of this levels effect.

**Returns:**
- `LevelsParams`: The current level parameters.

##### set_parameters()

```python
set_parameters(params: LevelsParamsMono | LevelsParamsRGB) → None
```

Set new parameters for this levels effect.

**Parameters:**
- `params` (LevelsParams): The new parameters.

## Parameters

### LevelsParamsRGB

```python
class substance_painter.levels.LevelsParamsRGB(
    input_min: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    input_max: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    gamma: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    output_min: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    output_max: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    clamp: bool = False
)
```

A levels parameters, when in RGB color mode.

**Parameters:**
- `input_min` (Tuple[float, float, float]): The minimum input threshold.
- `input_max` (Tuple[float, float, float]): The maximum input threshold.
- `gamma` (Tuple[float, float, float]): Gamma.
- `output_min` (Tuple[float, float, float]): The minimum output threshold.
- `output_max` (Tuple[float, float, float]): The maximum output threshold.
- `clamp` (bool): Whether the values should be clamped or not.

### LevelsParamsMono

```python
class substance_painter.levels.LevelsParamsMono(
    input_min: float = 0.0,
    input_max: float = 1.0,
    gamma: float = 1.0,
    output_min: float = 0.0,
    output_max: float = 1.0,
    clamp: bool = False
)
```

A levels parameters, when in Luminance or only one color mode.

**Parameters:**
- `input_min` (float): The minimum input threshold.
- `input_max` (float): The maximum input threshold.
- `gamma` (float): Gamma.
- `output_min` (float): The minimum output threshold.
- `output_max` (float): The maximum output threshold.
- `clamp` (bool): Whether the values should be clamped or not.

### LevelsParams

```python
substance_painter.levels.LevelsParams
```

Alias of `LevelsParamsMono | LevelsParamsRGB`

Levels parameters can be expressed for three channels (RGB) or only one color channel (only one color or luminance). `LevelsParams` is used to regroup the two possible parameters flavors.