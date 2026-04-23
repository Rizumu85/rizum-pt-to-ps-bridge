# Fill layer and effect

`FillLayerNode` and `FillEffectNode` are types of nodes that cannot be painted on, instead a material can be loaded into it or resources can be loaded into channels individually.

## Examples

### Apply grunge in a fill effect

```python
import substance_painter as sp

# Get the currently displayed Stack
stack = sp.textureset.get_active_stack()

# Get top position of the Stack
position_stack_top = sp.layerstack.InsertPosition.from_textureset_stack(stack)

# It is also possible to create a Fill Effect with InsertPosition.inside_node()
# sp.layerstack.InsertPosition.inside_node(node, sp.layerstack.NodeStack.Content)
# sp.layerstack.InsertPosition.inside_node(node, sp.layerstack.NodeStack.Mask)

# Insert Fill Layer
my_fill_layer = sp.layerstack.insert_fill(position_stack_top)
my_fill_layer.set_name("My Fill Layer")

# The Fill layer is created with the SourceMode 'Split'
# Check if the BaseColor channel is available
if sp.layerstack.ChannelType.BaseColor in my_fill_layer.get_stack().all_channels().keys():
    # Change BaseColor color
    my_fill_layer.set_source(
        sp.layerstack.ChannelType.BaseColor, sp.colormanagement.Color(0.0, 0.3, 0.2))

# Check if the Roughness channel is available
if sp.layerstack.ChannelType.Roughness in my_fill_layer.get_stack().all_channels().keys():
    # Load noise into roughness
    noise_resource = sp.resource.search("s:starterassets "
                                        "u:procedural "
                                        "n:3D Perlin Noise Fractal")[0]
    my_fill_layer.set_source(sp.layerstack.ChannelType.Roughness, noise_resource.identifier())

# Add a Fill effect in the content stack
inside_content = sp.layerstack.InsertPosition.inside_node(
    my_fill_layer, sp.layerstack.NodeStack.Content)
my_fill_effect = sp.layerstack.insert_fill(inside_content)

# Note: Fill layers and Fill effects in the content stack are multi-channels
# and get/set_material_source() functions require to be in multi-channel mode
# To check the mode, use `source_mode` attribute
#   - SourceMode.Material or SourceMode.Split are multi-channels
#   - None is mono-channel (ex: a fill in the mask stack)
if my_fill_effect.source_mode is not None:
    # Apply material in material mode
    aluminium_material = sp.resource.search("s:starterassets "
                                            "u:substance "
                                            "n:metal")[0]
    my_fill_effect.set_material_source(aluminium_material.identifier())
    # SourceMode is automatically updated to 'Material'

# Add a mask and a fill effect in the mask stack
my_fill_layer.add_mask(sp.layerstack.MaskBackground.Black)
inside_mask = sp.layerstack.InsertPosition.inside_node(
    my_fill_layer, sp.layerstack.NodeStack.Mask)
my_fill_effect_mask = sp.layerstack.insert_fill(inside_mask)

# Note: all Fill effects in the mask stack are mono-channel
# get/set_material_source() functions are not allowed

# Apply grunge in the fill effect
grunge = sp.resource.search("s:starterassets "
                            "u:procedural "
                            "n:Grunge Rust Fine")[0]
# There is no channel to specify in the mask stack, use 'None' instead
my_fill_effect_mask.set_source(None, grunge.identifier())

# Change projection to triplanar
my_fill_layer.set_projection_mode(sp.layerstack.ProjectionMode.Triplanar)

# Adjust scale of the projection
projection_params = my_fill_layer.get_projection_parameters()
projection_params.projection_3d.scale = [0.5, 0.5, 0.5]
my_fill_layer.set_projection_parameters(projection_params)

# Select the Fill layer
sp.layerstack.set_selected_nodes([my_fill_layer])
```

## Functions and classes

### insert_fill()

```python
substance_painter.layerstack.insert_fill(position: InsertPosition) → FillLayerNode | FillEffectNode
```

Insert a Fill effect or layer (depending on the insert position).

**Parameters:**
- **position** (InsertPosition) – Insert position.

**Returns:** The inserted node.

**Return type:** Union[FillLayerNode, FillEffectNode]

**Raises:** ValueError – If insertion failed due to an invalid `position`. See InsertPosition.

### class FillLayerNode

A node allowing manipulation of a Fill layer.

Bases: `FillParamsEditorMixin`, `SourceEditorMixin`, `LayerNode`

#### Properties

##### active_channels

The set of active channels of the source.

**Type:** Set[ChannelType]

**Getter:** Returns the active channels of the source. To get the list of channels for a given stack, see `substance_painter.textureset.Stack.all_channels()`.

**Setter:** Sets the active channels of the source, channels not listed will be disabled.

##### source_mode

The current context in which the source is edited:

- `Material`: only one source is used to write to several channels, see `get_material_source()` and `set_material_source()`.
- `Split`: each source write to a single channel, see `get_source()` and `set_source()`.
- `None`: the current context is not multi-channel (ex: a mask), see `get_source()` and `set_source()`.

For more details, see the example above.

**Type:** SourceMode

#### Methods

##### get_material_source()

```python
get_material_source() → SourceSubstance | SourceReference
```

Get the source in material mode.

**Returns:** the source.

**Raises:**
- RuntimeError – If the source is not in `SourceMode.Material`. See `source_mode`.
- EditionContextException – If the current context in not multi-channel.

##### get_projection_mode()

```python
get_projection_mode() → ProjectionMode
```

Get the current projection mode.

**Returns:** The current projection mode.

##### get_projection_parameters()

```python
get_projection_parameters() → UVProjectionParams | TriplanarProjectionParams | PlanarProjectionParams | WarpProjectionParams | SphericalProjectionParams | CylindricalProjectionParams | UVSetToUVSetProjectionParams | None
```

Get the current projection parameters. Each kind of Projection Mode returns a specific kind of ProjectionParams, supporting a different set of features. `Fill` mode support no parameters, and returns None.

**Returns:** The current projection parameters, or None for `Fill`.

**See also:** `get_projection_mode()`, [Fill projections documentation](https://helpx.adobe.com/substance-3d-painter/painting/fill-projections.html)

##### get_source()

```python
get_source(channeltype: ChannelType | None = None) → SourceUniformColor | SourceBitmap | SourceVectorial | SourceSubstance | SourceReference | SourceFont
```

Get the source for the given channel type.

**Parameters:** **channeltype** – Must be None in mono channel context.

**Returns:** the source at channel type.

**Raises:**
- EditionContextException – If the `channeltype` is not valid in the current context. See `active_channels`.
- RuntimeError – If the source is in `SourceMode.Material`. See `source_mode`.

##### reset_material_source()

```python
reset_material_source() → None
```

Reset the source in material mode.

**Raises:** EditionContextException – If the current context in not multi-channel.

##### reset_source()

```python
reset_source(channeltype: ChannelType | None = None) → None
```

Reset the source at channel type.

**Parameters:** **channeltype** – Must be None in mono channel context.

**Raises:** EditionContextException – If the `channeltype` is not valid in the current context. See `active_channels`.

##### set_material_source()

```python
set_material_source(source: ResourceID | AnchorPointEffectNode) → SourceSubstance | SourceReference
```

Set the source in material mode.

**Parameters:** **source** – the source parameter.

**Returns:** the source.

**Raises:**
- ValueError – If the `source` parameter is not valid.
- EditionContextException – If the current context in not multi-channel.

##### set_projection_mode()

```python
set_projection_mode(projection_mode: ProjectionMode)
```

Switch to a new projection mode.

**Parameters:** **projection_mode** – The new projection mode.

**Raises:** ValueError – If the projection mode is not supported in the current context.

##### set_projection_parameters()

```python
set_projection_parameters(projection_parameters: UVProjectionParams | TriplanarProjectionParams | PlanarProjectionParams | WarpProjectionParams | SphericalProjectionParams | CylindricalProjectionParams | UVSetToUVSetProjectionParams)
```

Set projection parameters and update the current projection mode accordingly.

**Parameters:** **projection_parameters** – The new parameters to apply.

**Raises:** ValueError – If the projection parameters are not supported in the current context.

**See also:** `get_projection_parameters()`, [Fill projections documentation](https://helpx.adobe.com/substance-3d-painter/painting/fill-projections.html)

##### set_source()

```python
set_source(channeltype: ChannelType | None, source: ResourceID | Color | AnchorPointEffectNode) → SourceUniformColor | SourceBitmap | SourceVectorial | SourceSubstance | SourceReference | SourceFont
```

Set the source for the given channel type.

**Parameters:**
- **channeltype** – Must be None in mono channel context.
- **source** – the source parameter.

**Returns:** the source at channel type.

**Raises:**
- EditionContextException – If the `channeltype` is not valid in the current context. See `active_channels`.
- ValueError – If the `source` parameter is not valid.

##### set_sources_from_preset()

```python
set_sources_from_preset(preset: ResourceID) → None
```

Setup the fill with the given preset.

**Parameters:** **preset** – the resource preset.

**Raises:** ValueError – If `preset` is not a valid resource preset.

### class FillEffectNode

A node allowing manipulation of a Fill effect.

Bases: `FillParamsEditorMixin`, `SourceEditorMixin`, `Node`

#### Properties

##### active_channels

The set of active channels of the source.

**Type:** Set[ChannelType]

**Getter:** Returns the active channels of the source. To get the list of channels for a given stack, see `substance_painter.textureset.Stack.all_channels()`.

**Setter:** Sets the active channels of the source, channels not listed will be disabled.

##### source_mode

The current context in which the source is edited:

- `Material`: only one source is used to write to several channels, see `get_material_source()` and `set_material_source()`.
- `Split`: each source write to a single channel, see `get_source()` and `set_source()`.
- `None`: the current context is not multi-channel (ex: a mask), see `get_source()` and `set_source()`.

For more details, see the example above.

**Type:** SourceMode

#### Methods

##### get_material_source()

```python
get_material_source() → SourceSubstance | SourceReference
```

Get the source in material mode.

**Returns:** the source.

**Raises:**
- RuntimeError – If the source is not in `SourceMode.Material`. See `source_mode`.
- EditionContextException – If the current context in not multi-channel.

##### get_projection_mode()

```python
get_projection_mode() → ProjectionMode
```

Get the current projection mode.

**Returns:** The current projection mode.

##### get_projection_parameters()

```python
get_projection_parameters() → UVProjectionParams | TriplanarProjectionParams | PlanarProjectionParams | WarpProjectionParams | SphericalProjectionParams | CylindricalProjectionParams | UVSetToUVSetProjectionParams | None
```

Get the current projection parameters. Each kind of Projection Mode returns a specific kind of ProjectionParams, supporting a different set of features. `Fill` mode support no parameters, and returns None.

**Returns:** The current projection parameters, or None for `Fill`.

**See also:** `get_projection_mode()`, [Fill projections documentation](https://helpx.adobe.com/substance-3d-painter/painting/fill-projections.html)

##### get_source()

```python
get_source(channeltype: ChannelType | None = None) → SourceUniformColor | SourceBitmap | SourceVectorial | SourceSubstance | SourceReference | SourceFont
```

Get the source for the given channel type.

**Parameters:** **channeltype** – Must be None in mono channel context.

**Returns:** the source at channel type.

**Raises:**
- EditionContextException – If the `channeltype` is not valid in the current context. See `active_channels`.
- RuntimeError – If the source is in `SourceMode.Material`. See `source_mode`.

##### get_symmetry_parameters()

```python
get_symmetry_parameters() → MirrorSymmetryParams | RadialSymmetryParams
```

Get the current symmetry parameters. Each kind of symmetry mode returns a specific kind of SymmetryParams, supporting a different set of features. Symmetry is only available for 3D projection modes. See `substance_painter.layerstack.is_3d_projection_mode()`.

**Returns:** The current symmetry parameters.

**Raises:** ValueError – If the symmetry is not supported in the current context.

##### is_symmetry_enabled()

```python
is_symmetry_enabled() → bool
```

Check if symmetry is enabled. Symmetry is only available for 3D projection modes. See `substance_painter.layerstack.is_3d_projection_mode()`.

**Returns:** True if symmetry is enabled, False otherwise.

**Raises:** ValueError – If the symmetry is not supported in the current context.

##### reset_material_source()

```python
reset_material_source() → None
```

Reset the source in material mode.

**Raises:** EditionContextException – If the current context in not multi-channel.

##### reset_source()

```python
reset_source(channeltype: ChannelType | None = None) → None
```

Reset the source at channel type.

**Parameters:** **channeltype** – Must be None in mono channel context.

**Raises:** EditionContextException – If the `channeltype` is not valid in the current context. See `active_channels`.

##### set_material_source()

```python
set_material_source(source: ResourceID | AnchorPointEffectNode) → SourceSubstance | SourceReference
```

Set the source in material mode.

**Parameters:** **source** – the source parameter.

**Returns:** the source.

**Raises:**
- ValueError – If the `source` parameter is not valid.
- EditionContextException – If the current context in not multi-channel.

##### set_projection_mode()

```python
set_projection_mode(projection_mode: ProjectionMode)
```

Switch to a new projection mode.

**Parameters:** **projection_mode** – The new projection mode.

**Raises:** ValueError – If the projection mode is not supported in the current context.

##### set_projection_parameters()

```python
set_projection_parameters(projection_parameters: UVProjectionParams | TriplanarProjectionParams | PlanarProjectionParams | WarpProjectionParams | SphericalProjectionParams | CylindricalProjectionParams | UVSetToUVSetProjectionParams)
```

Set projection parameters and update the current projection mode accordingly.

**Parameters:** **projection_parameters** – The new parameters to apply.

**Raises:** ValueError – If the projection parameters are not supported in the current context.

**See also:** `get_projection_parameters()`, [Fill projections documentation](https://helpx.adobe.com/substance-3d-painter/painting/fill-projections.html)

##### set_source()

```python
set_source(channeltype: ChannelType | None, source: ResourceID | Color | AnchorPointEffectNode) → SourceUniformColor | SourceBitmap | SourceVectorial | SourceSubstance | SourceReference | SourceFont
```

Set the source for the given channel type.

**Parameters:**
- **channeltype** – Must be None in mono channel context.
- **source** – the source parameter.

**Returns:** the source at channel type.

**Raises:**
- EditionContextException – If the `channeltype` is not valid in the current context. See `active_channels`.
- ValueError – If the `source` parameter is not valid.

##### set_sources_from_preset()

```python
set_sources_from_preset(preset: ResourceID) → None
```

Setup the fill with the given preset.

**Parameters:** **preset** – the resource preset.

**Raises:** ValueError – If `preset` is not a valid resource preset.

##### set_symmetry_enabled()

```python
set_symmetry_enabled(enabled: bool)
```

Set the symmetry enabled state. Symmetry is only available for 3D projection modes. See `substance_painter.layerstack.is_3d_projection_mode()`.

**Parameters:** **enabled** – True to enable symmetry, False to disable it.

**Raises:** ValueError – If the symmetry is not supported in the current context.

##### set_symmetry_parameters()

```python
set_symmetry_parameters(symmetry_parameters: MirrorSymmetryParams | RadialSymmetryParams)
```

Set the symmetry parameters and update the current symmetry mode accordingly. This does not enable symmetry. Explicitly use `set_symmetry_enabled()` to enable it. Symmetry is only available for 3D projection modes. See `substance_painter.layerstack.is_3d_projection_mode()`.

Example to set and enable radial symmetry:

```python
symmetry_parameters = sp.layerstack.RadialSymmetryParams()
symmetry_parameters.axis = sp.layerstack.SymmetryAxis.X
symmetry_parameters.flip_u = False
symmetry_parameters.flip_v = True
symmetry_parameters.axis_position = [0, 0.1, -0.1]
symmetry_parameters.angle_span = 70
symmetry_parameters.count = 10
my_layer.set_symmetry_parameters(symmetry_parameters)
my_layer.set_symmetry_enabled(True)
```

**Parameters:** **symmetry_parameters** – The new parameters to apply.

**Raises:** ValueError – If the symmetry is not supported in the current context.

## Params

### class UVProjectionParams

Parameters that control the fill behaviour when the projection mode is `ProjectionMode.UV`.

For a complete description of the parameters, see [UV Projection documentation](https://helpx.adobe.com/substance-3d-painter/painting/fill-projections/uv-projection.html).

**Parameters:**
- **filtering_mode** (FilteringMode) – How to filter the image.
- **uv_wrapping_mode** (UVWrapMode) – UV Wrapping behaviour.
- **uv_transformation** (UVTransformationParams) – UV transformation.

### class TriplanarProjectionParams

Parameters that control the fill behaviour when the projection mode is `ProjectionMode.Triplanar`.

For a complete description of the parameters, see [Triplanar Projection documentation](https://helpx.adobe.com/substance-3d-painter/painting/fill-projections/tri-planar-projection.html).

**Parameters:**
- **filtering_mode** (FilteringMode) – How to filter the image.
- **shape_crop_mode** (ShapeCropMode) – How the fill is cropped.
- **hardness** (float) – How hard is the transition between planes of the projection.
- **uv_transformation** (UVTransformationParams) – UV transformation.
- **projection_3d** (Projection3DParams) – 3D projection.

### class PlanarProjectionParams

Parameters that control the fill behaviour when the projection mode is `ProjectionMode.Planar`.

For a complete description of the parameters, see [Planar Projection documentation](https://helpx.adobe.com/substance-3d-painter/painting/fill-projections/planar-projection.html).

**Parameters:**
- **filtering_mode** (FilteringMode) – How to filter the image.
- **uv_wrapping_mode** (UVWrapMode) – UV Wrapping behaviour.
- **shape_crop_mode** (ShapeCropMode) – How the fill is cropped.
- **depth_culling** (ProjectionCullingParams) – Depth culling settings.
- **backface_culling** (ProjectionCullingParams) – Backface culling settings.
- **backface_culling_angle** (float) – Minimum angle which determines when faces that are looking away should be ignored, between 45 and 135.
- **uv_transformation** (UVTransformationParams) – UV transformation.
- **projection_3d** (Projection3DParams) – 3D projection.

### class SphericalProjectionParams

Parameters that control the fill behaviour when the projection mode is `ProjectionMode.Spherical`.

For a complete description of the parameters, see [Spherical Projection documentation](https://helpx.adobe.com/substance-3d-painter/painting/fill-projections/spherical-projection.html).

**Parameters:**
- **filtering_mode** (FilteringMode) – How to filter the image.
- **uv_wrapping_mode** (UVWrapMode) – UV Wrapping behaviour.
- **shape_crop_mode** (ShapeCropMode) – How the fill is cropped.
- **uv_transformation** (UVTransformationParams) – UV transformation. Spherical projection do not support UV transformation physical size options.
- **projection_3d** (Projection3DParams) – 3D projection.

### class CylindricalProjectionParams

Parameters that control the fill behaviour when the projection mode is `ProjectionMode.Cylindrical`.

For a complete description of the parameters, see [Cylindrical Projection documentation](https://helpx.adobe.com/substance-3d-painter/painting/fill-projections/cylindrical-projection.html).

**Parameters:**
- **filtering_mode** (FilteringMode) – How to filter the image.
- **uv_wrapping_mode** (UVWrapMode) – UV Wrapping behaviour.
- **shape_crop_mode** (ShapeCropMode) – How the fill is cropped.
- **angle** (float) – Size of the projection on the perimeter of the cylinder.
- **backface_culling** (ProjectionCullingParams) – Backface culling parameters.
- **uv_transformation** (UVTransformationParams) – UV transformation.
- **projection_3d** (Projection3DParams) – 3D projection.

### class WarpProjectionParams

Parameters that control the fill behaviour when the projection mode is `ProjectionMode.Warp`.

For a complete description of the parameters, see [Warp Projection documentation](https://helpx.adobe.com/substance-3d-painter/painting/fill-projections/warp-projection.html).

**Parameters:**
- **filtering_mode** (FilteringMode) – How to filter the image.
- **uv_wrapping_mode** (UVWrapMode) – UV Wrapping behaviour.
- **shape_crop_mode** (ShapeCropMode) – How the fill is cropped.
- **projection_depth** (float) – How far the projection goes along its Z axis.
- **depth_culling** (ProjectionCullingParams) – Depth culling parameters.
- **uv_transformation** (UVTransformationParams) – UV transformation.
- **projection_3d** (Projection3DParams) – 3D projection.

### class UVSetToUVSetProjectionParams

Parameters that control the fill behaviour when the projection mode is `ProjectionMode.UVSetToUVSet`.

For a complete description of the parameters, see [UVSetToUVSet Projection documentation](https://helpx.adobe.com/substance-3d-painter/painting/fill-projections/uv-set-to-uv-set-projection.html).

**Parameters:**
- **source_uv_set** (int) – Mesh UV set index used as projection source (0: no effect).
- **filtering_mode** (FilteringMode) – How to filter the image.
- **uv_wrapping_mode** (UVWrapMode) – UV Wrapping behaviour.
- **uv_transformation** (UVTransformationParams) – UV transformation.

### class UVTransformationParams

UV projection transformation parameters.

**Parameters:**
- **scale_mode** (ScaleMode) – How `scale` should be interpreted. For a `ProjectionMode.Spherical` projection, only `ScaleMode.Factors` is supported. Using `ScaleMode.MaterialPhysicalSize` is only possible when applied to a resource with physical size information.
- **scale** (List[float]) – The u/v stretch applied to the texture. When `scale_mode` is `ScaleMode.Factors`, use plain factor for stretching. When `scale_mode` is `ScaleMode.MaterialPhysicalSize`, scale must be None and the value will be forced to the actual material physical size. When `scale_mode` is `ScaleMode.CustomPhysicalSize`, then scale is expressed in centimeters and overrides the size defined by the material.
- **rotation** (float) – Rotation applied to the texture.
- **offset** (List[float]) – Offset applied to the texture. The offset is unavailable for a `ProjectionMode.Triplanar` projection.

### class Projection3DParams

3D projection transformation parameters.

**Parameters:**
- **offset** (List[float]) – 3D offset.
- **rotation** (List[float]) – 3D rotation.
- **scale** (List[float]) – 3D scale. Z scaling is unavailable when projection mode is `ProjectionMode.Planar` and depth culling is disabled.

### class ProjectionCullingParams

Projection culling parameters. Either a depth culling or a backface culling.

**Parameters:**
- **enabled** (bool) – Whether the culling is enabled or not.
- **hardness** (float) – Hardness of the culling, between 0 and 1.

### ProjectionParams

Each Projection Mode has its own projection parameters. `ProjectionParams` is used to regroup them.

### class MirrorSymmetryParams

Parameters that control the mirror symmetry behaviour.

**Parameters:**
- **axis** (SymmetryAxis) – Axis along which to mirror.
- **flip_u** (bool) – Whether to flip UVs along the U axis.
- **flip_v** (bool) – Whether to flip UVs along the V axis.
- **axis_position** (List[float]) – Position of the mirror plane along each axis, clamped between [-10, -10, -10] and [10, 10, 10].

### class RadialSymmetryParams

Parameters that control the radial symmetry behaviour.

When setting symmetry, some parameters will get clamped:

**Parameters:**
- **axis** (SymmetryAxis) – Axis along which to mirror.
- **flip_u** (bool) – Whether to flip UVs along the U axis.
- **flip_v** (bool) – Whether to flip UVs along the V axis.
- **axis_position** (List[float]) – Position of the mirror plane along each axis, clamped between [-10, -10, -10] and [10, 10, 10].
- **count** (int) – Number of copies, clamped between 2 and 16.
- **angle_span** (float) – Angle span of the copies, in degrees, clamped between -360 and 360.

### SymmetryParams

Each Symmetry Mode has its own symmetry parameters. `SymmetryParams` is used to regroup them.

## Utility functions

### is_3d_projection_mode()

```python
substance_painter.layerstack.is_3d_projection_mode(projection_mode: ProjectionMode) → bool
```

Check if the projection mode is a 3D projection.

**Parameters:**
- **projection_mode** (ProjectionMode) – Projection mode to check.

**Returns:** True if the current projection mode is a 3D projection.

## Enums

### class ProjectionMode

See [Fill projections documentation](https://helpx.adobe.com/substance-3d-painter/painting/fill-projections.html) for a complete description of all Projection modes.

Symmetry is only available for 3D projection modes. See `substance_painter.layerstack.is_3d_projection_mode()`.

**Members:**

| Name | Description |
|------|-------------|
| `Fill` | Fill (match per UV Tile) is a special 2D projection useful for UV Tile projects. |
| `UV` | 2D projection that only works in the 2D texture space. |
| `Triplanar` | 3D projection that combines multiple planar projections together. |
| `Planar` | 3D projection that projects an image in a direction as a plane. |
| `Spherical` | 3D projection that projects images and patterns around an object following a sphere area. |
| `Cylindrical` | 3D projection that projects images and patterns around an object following a cylinder area. |
| `Warp` | 3D projection that deforms a texture by editing points of a grid. |
| `UVSetToUVSet` | Projection from an additional UV set to the current UV set. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### class FilteringMode

**Members:**

| Name | Description |
|------|-------------|
| `BilinearHQ` | Advanced bilinear filtering. |
| `BilinearSharp` | Simple bilinear filtering. |
| `Nearest` | No filtering. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### class UVWrapMode

**Members:**

| Name | Description |
|------|-------------|
| `RepeatNone` | No repeat. |
| `RepeatHorizontally` | Repeat horizontally. |
| `RepeatVertically` | Repeat vertically. |
| `Repeat` | Repeat horizontally and vertically. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### class ShapeCropMode

**Members:**

| Name | Description |
|------|-------------|
| `CroppedToShape` | The projection is confined within the projection area. |
| `ExtendsOutsideShape` | The projection continues beyond the projection area. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### class ScaleMode

**Members:**

| Name | Description |
|------|-------------|
| `Factors` | The texture is repeated by a number of times. |
| `MaterialPhysicalSize` | Automatic adjustment of the texture according to the mesh size and texture size. |
| `CustomPhysicalSize` | Specify a physical size manually and adapt to the mesh size. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### class SymmetryMode

Symmetry (Mirror or Radial) is only applied when a 3D projection mode is set on a Fill Layer. See `ProjectionMode` for projection modes description.

**Members:**

| Name | Description |
|------|-------------|
| `Mirror` | Axial symmetry. |
| `Radial` | Radial symmetry. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### class SymmetryAxis

**Members:**

| Name | Description |
|------|-------------|
| `X` | The X axis. |
| `Y` | The Y axis. |
| `Z` | The Z axis. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).