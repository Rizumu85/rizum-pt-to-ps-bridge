# SourceVectorial

`SourceVectorial` is a type of source where you can connect a vectorial resource.

For more information, see module `resource`.

**See also:** [Vectorial graphic documentation](https://helpx.adobe.com/substance-3d-painter/painting/vector-graphic-svg.html).

## Example

```python
import substance_painter as sp

# Get the currently displayed stack
stack = sp.textureset.get_active_stack()

# Insert a fill layer
position = sp.layerstack.InsertPosition.from_textureset_stack(stack)
fill = sp.layerstack.insert_fill(position)

# Setup triplanar projection
fill.set_projection_mode(sp.layerstack.ProjectionMode.Triplanar)
params = fill.get_projection_parameters()
params.projection_3d.scale = [0.5, 0.5, 0.5]
fill.set_projection_parameters(params)

# Pick a vectorial resource
svg = sp.resource.search("u:vectorial")[0]
source = fill.set_source(sp.textureset.ChannelType.BaseColor, svg.identifier())

# Customize vectorial parameters
params = source.get_parameters()
params.resolution.mode = sp.source.ResolutionMode.Manual
params.resolution.value = [2048, 2048]
source.set_parameters(params)

# Select the Fill layer
sp.layerstack.set_selected_nodes([fill])
```

## Class: substance_painter.source.SourceVectorial(uid)

A class that represents a vectorial source.

### Properties

#### resource_id
**Type:** ResourceID  
**Getter:** Returns the resource identifier of the vectorial used by the source.

The current vectorial resource of the source.

### Methods

#### get_parameters()
Get the source parameters.

**Returns:**
- **SourceVectorialParams**: The source parameters.

#### set_parameters(params)
Set the source parameters.

**Parameters:**
- **params** (SourceVectorialParams): The source parameters.

**Raises:**
- **ValueError**: If the parameters requirements are not met, see SourceVectorialParams.

**Returns:**
- None

#### uid()
Get the object internal uid.

**Returns:**
- **int**: The internal identifier of the object as an integer.

## Params

### Class: substance_painter.source.SourceVectorialParams

The source vectorial parameters.

**Parameters:**
- **artboard_id** (str | None): The artboard id, for .ai file.
- **scope** (str | None): The root element of the hierarchy you want to import.
- **resolution** (ResolutionOverride): Resolution parameters of the resource.
- **resolution_mode** (ResolutionMode): Deprecated since 0.3.4. Use `mode` attribute from **resolution** parameter instead.
- **resolution_value** (Tuple[int, int]): Deprecated since 0.3.4. Use `value` attribute from **resolution** parameter instead.
- **crop_area_mode** (CropAreaMode): The crop area mode.
- **crop_area_value** (Tuple[float, float, float, float]): The crop area to use when `crop_area_mode` is `CropAreaMode.Manual`, formatted as [left corner x, left corner y, crop area width, crop area height]. `width` and `height` values must be positive.
- **fit_to_square** (bool): Force the crop area to be square. Default: True

## Enums

### substance_painter.source.VectorialResolutionMode
Alias for ResolutionMode.

**Warning:** Deprecated since 0.3.4, use ResolutionMode instead.

**Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### Class: substance_painter.source.CropAreaMode

**Members:**

| Name | Description |
|------|-------------|
| `DocumentBounds` | The crop area is automatically calculated based on the vector document. This corresponds to the `Asset bounds` option available in Painter's UI. |
| `Manual` | The crop area is explicitly defined by the user. This corresponds to the `Custom area` option available in Painter's UI. |

**Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).