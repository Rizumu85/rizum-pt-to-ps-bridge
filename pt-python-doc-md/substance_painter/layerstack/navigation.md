# Layerstack Navigation

The layerstack module allows to query layers and effects and their content.

## Examples

### Search and Select a specific node

```python
# This example shows how to recursively navigate into the layerstack to search for a specific
# substance resource and select the node containing it.

import substance_painter as sp

def match_resource_name(source: sp.source.Source, resource_name: str):
    if type(source) is sp.layerstack.SourceSubstance:
        return source.resource_id.name == resource_name
    return False

def find_node_with_substance(
    node: sp.layerstack.Node, resource_name: str):
    # If the node is a Group, iterate over its sub-layers
    if type(node) is sp.layerstack.GroupLayerNode:
        for child in node.sub_layers():
            result = find_node_with_substance(child, resource_name)
            if result:
                return result

    # If the node is a Layer, iterate over its content stack and mask stack
    if isinstance(node, sp.layerstack.LayerNode):
        for content_effect in node.content_effects():
            result = find_node_with_substance(content_effect, resource_name)
            if result:
                return result
        for mask_effect in node.mask_effects():
            result = find_node_with_substance(mask_effect, resource_name)
            if result:
                return result

    # Check if the node itself contains the resource
    if type(node) is sp.layerstack.FillLayerNode or type(node) is sp.layerstack.FillEffectNode:
        # Check if the Fill is in material mode (the source write to multiple channels)
        if node.source_mode == sp.source.SourceMode.Material:
            if match_resource_name(node.get_material_source(), resource_name):
                return node
        # Check if the Fill is in split mode (each source write to a single channel)
        elif node.source_mode == sp.source.SourceMode.Split:
            # Iterate over the active channels of the Fill
            for channel in node.active_channels:
                if match_resource_name(node.get_source(channel), resource_name):
                    return node
        # This case happens only in the mask stack, where there is no channel
        else:
            source = node.get_source(None) # There is no channel in the mask stack
            if match_resource_name(source, resource_name):
                return node
    elif (type(node) is sp.layerstack.GeneratorEffectNode
        or type(node) is sp.layerstack.FilterEffectNode):
        if match_resource_name(node.get_source(), resource_name):
            return node

    return None

def find_substance_in_layerstack(resource_name: str):
    # Retrieve the list of all texture sets
    texture_sets = sp.textureset.all_texture_sets()

    # Iterate over all texture sets
    for texture_set in texture_sets:
        # Iterate over all stacks in the texture set
        for stack in texture_set.all_stacks():
            # Get all Layer nodes at the root of the stack
            stack_root_nodes = sp.layerstack.get_root_layer_nodes(stack)
            # Iterate over the layers to find the one containing the substance
            for layer in stack_root_nodes:
                # Check if the layer contains the substance
                node = find_node_with_substance(layer, resource_name)
                if node:
                    return node

# Open the French Restaurant Table sample
# Note: you should replace <PATH_TO_PAINTER> with the path where
# Substance 3D Painter is installed on your machine
sp.project.open("<PATH_TO_PAINTER>/resources/samples/FrenchRestaurantTable.spp")

resource_name = "fabric_linen/fabric_linen"
node = find_substance_in_layerstack(resource_name)
if node:
    # Ensure the stack containing the node is active
    stack = node.get_stack()
    if stack != sp.textureset.get_active_stack():
        sp.textureset.set_active_stack(stack)
    # Select the node
    sp.layerstack.set_selected_nodes([node])
```

### Geometry mask manipulation

```python
# This example shows how to manipulate Geometry Masks in the layerstack

import substance_painter as sp

# Open the French Restaurant Table sample
# Note: you should replace <PATH_TO_PAINTER> with the path where
# Substance 3D Painter is installed on your machine
sp.project.open("<PATH_TO_PAINTER>/resources/samples/FrenchRestaurantTable.spp")

# Select the 'Table' texture set
for textureset in sp.textureset.all_texture_sets():
    if textureset.name() == "Table":
        stack = textureset.get_stack()
        break
sp.textureset.set_active_stack(stack)

# Get the root layers from the stack
stack_root_layers = sp.layerstack.get_root_layer_nodes(stack)

# Get the layer at the top of the stack
first_layer = stack_root_layers[0]
# Get the layer's texture set
first_layer_texture_set = first_layer.get_texture_set()
# Avoid error checking if Layer has UDIM (UV Tiles)
if first_layer_texture_set.has_uv_tiles():
    # Define which UV Tile should be activated (will deactivate the other ones)
    first_layer.set_geometry_mask_enabled_uv_tiles(
        [first_layer_texture_set.uv_tile(0, 0),  # UDIM 1001
        first_layer_texture_set.uv_tile(1, 0)])  # UDIM 1002

# Create a Fill Layer at the top of the stack
fill_layer_position = sp.layerstack.InsertPosition.from_textureset_stack(stack)
fill_layer = sp.layerstack.insert_fill(fill_layer_position)

plant_group_meshes = []
# Get the Fill layer's texture set
plant_group_texture_set = fill_layer.get_texture_set()
# List all meshes where name contains 'flower'
for mesh in plant_group_texture_set.all_mesh_names():
    if "flower" in mesh:
        plant_group_meshes.append(mesh)
# Enable Meshes into the Geometry Mask
fill_layer.set_geometry_mask_enabled_meshes(plant_group_meshes)
# Switch layer masking method to Geometry Masking
fill_layer.set_geometry_mask_type(sp.layerstack.GeometryMaskType.Mesh)
# Activate Base Color (to see the result)
fill_layer.active_channels = {sp.textureset.ChannelType.BaseColor}

# Select the modified layers
sp.layerstack.set_selected_nodes([first_layer, fill_layer])
```

## Get Nodes

### get_root_layer_nodes(stack: Stack)

Get the root layers of a stack, ordered like in the layer stack.

**Parameters:**
- `stack` (Stack): Stack to query.

**Raises:**
- `ValueError`: If `stack` is invalid.

**Returns:**
- List of root layers of the stack (LayerNode | GroupLayerNode | PaintLayerNode | InstanceLayerNode | FillLayerNode)

### get_node_by_uid(node_id: int)

Get a node by its internal identifier.

**Parameters:**
- `node_id` (int): The node uid.

**Raises:**
- `ValueError`: If the given uid doesn't correspond to a valid node.

**Returns:**
- The node with the given uid.

## Node Objects

### Node Class

Abstract class to manipulate common properties of a layer stack node. Each node is identified by a node uid.

Calling methods of a Node with an incorrect `uid` throws a ValueError. This could happen when instantiating a Node providing its `uid` by hand, or when the Node no longer refers to existing data in the Layer Stack.

#### Methods

**get_type() → NodeType**
- Check the type of the node.
- Returns: The node type.

**get_texture_set() → TextureSet**
- Get the TextureSet this node belongs to.
- Returns: the TextureSet this node belongs to.

**is_visible() → bool**
- Check whether this node is rendered.
- Returns: Whether this node is rendered.

**set_visible(visible: bool)**
- Enable this node for rendering.
- Parameters: `visible` (bool) - Whether to enable this node for rendering.

**get_name() → str**
- Get the name assigned to this Node.
- Returns: The Node name.

**set_name(name: str)**
- Change this node name.
- Parameters: `name` (str) - New name to use.

**is_in_mask_stack() → bool**
- Check whether this node is part of a mask stack.
- Returns: Whether this node is part of a mask stack.

**has_blending() → bool**
- Check whether this node supports blending information (blending mode + opacity).
- The blending might be per Channel Type for regular nodes, or monochannel for nodes inside a mask stack.
- Returns: Whether this node supports blending information.

**get_blending_mode(channel: ChannelType | None = None) → BlendingMode**
- Get the blending mode for a Node.
- If the node is not in a mask stack, a Channel Type must be provided.
- If the node is in a mask stack, Channel Type must be None.
- Parameters: `channel` (Optional[ChannelType]) - Channel Type to query or None for mask nodes.
- Returns: The blending mode of this node for the given Channel Type or for the mask.
- Raises: `ValueError` if parameters are inconsistent with node type.

**set_blending_mode(blending_mode: BlendingMode, channel: ChannelType | None = None)**
- Set the blending mode for a Node.
- Parameters: 
  - `blending_mode` (BlendingMode) - New blending mode to apply.
  - `channel` (Optional[ChannelType]) - Channel type to update or None for mask nodes.

**get_opacity(channel: ChannelType | None = None) → float**
- Get the opacity for a Node.
- Parameters: `channel` (Optional[ChannelType]) - Channel Type to query or None for mask nodes.
- Returns: The opacity of this node for the given Channel Type or for the mask.

**set_opacity(opacity: float, channel: ChannelType | None = None)**
- Set the opacity for a node.
- Parameters: 
  - `opacity` (float) - New opacity to apply, value between 0.0 and 1.0.
  - `channel` (Optional[ChannelType]) - Channel Type to update or None for mask nodes.

**get_stack() → Stack**
- Get the stack that contains this node.
- Returns: The stack that contains this node.

**get_parent() → Node**
- Get the parent of this node.
- Returns: The parent of this node, or None if this node is a root layer.

**get_next_sibling() → Node**
- Get the next sibling of this node.
- Returns: The next sibling of this node, or None if this node is the first sibling.

**get_previous_sibling() → Node**
- Get the previous sibling of this node.
- Returns: The previous sibling of this node, or None if this node is the last sibling.

**uid() → int**
- Get the object internal uid.
- Returns: The internal identifier of the object as an integer.

### LayerNode Class

Inherits from Node. A Node that is part of the main hierarchy. Every Layer such as a paint or fill layer, as well as groups, are organized into this hierarchy. As such, you can query sub layers (in the case the LayerNode is a group), but also associate content effects and mask effects (such as levels and filters and so on).

#### Additional Methods

**content_effects() → List[EffectNode]**
- Query the content effects of this node, ordered like in the layer stack.
- Returns: The content effects of this node.

**mask_effects() → List[EffectNode]**
- Query the mask effects of this node, ordered like in the layer stack.
- Returns: The mask effects of this node.

**instances() → List[LayerNode]**
- Return the list of instances of this layer.
- Returns: The instances of this node.

**get_geometry_mask_type() → GeometryMaskType**
- Query the geometry mask type currently applied to this node.
- Returns: The type of geometry mask for this layer node.

**set_geometry_mask_type(geometry_mask_type: GeometryMaskType)**
- Set the geometry mask type to apply to this node.
- Parameters: `geometry_mask_type` (GeometryMaskType) - The type of geometry mask for this layer node.
- Raises: `ValueError` when GeometryMaskType.UVTile is requested and the project does not support UV Tiles.

**get_geometry_mask_enabled_meshes() → List[str]**
- Get the list of enabled meshes for the geometry mask.
- Returns: The list of enabled meshes for the geometry mask.

**set_geometry_mask_enabled_meshes(mesh_names: List[str])**
- Set the list of enabled meshes for the geometry mask.
- Parameters: `mesh_names` (List[str]) - The list of meshes to enable for the geometry mask.
- Raises: `ValueError` if a mesh name does not belong to this texture set.

**get_geometry_mask_enabled_uv_tiles() → List[UVTile]**
- Get the list of enabled UV Tiles for the geometry mask.
- Returns: The list of enabled UV Tiles for the geometry mask.

**set_geometry_mask_enabled_uv_tiles(uv_tiles: List[UVTile])**
- Set the list of enabled UV Tiles for the geometry mask.
- Parameters: `uv_tiles` (List[UVTile]) - The list of UV Tiles to enable for the geometry mask.
- Raises: `ValueError` if a UV Tile does not belong to this texture set.

**has_mask() → bool**
- Check whether this node has a mask.
- Returns: Whether this node has a mask.

**add_mask(background: MaskBackground)**
- Add a mask on this node with the specified background.
- Parameters: `background` (MaskBackground)
- Raises: `ValueError` if a mask is already set on this node.

**remove_mask()**
- Remove this node mask, including all its effects.
- Raises: `ValueError` if no mask exists on this node.

**get_mask_background() → MaskBackground**
- Query the type of mask used by this node.
- Returns: The mask background applied to this node.
- Raises: `ValueError` if no mask exists on this node.

**set_mask_background(background: MaskBackground)**
- Set the mask background on this node.
- Parameters: `background` (MaskBackground) - The mask background to be applied on this node mask.
- Raises: `ValueError` if no mask exists on this node.

**is_mask_enabled() → bool**
- Query whether the mask is currently enabled.
- Returns: Whether the mask is currently enabled.
- Raises: `ValueError` if no mask exists on this node.

**enable_mask(enabled: bool)**
- Set whether the mask is currently enabled.
- Parameters: `enabled` (bool) - Whether to enable the mask.
- Raises: `ValueError` if no mask exists on this node.

## Aliases

- `substance_painter.layerstack.HierarchicalNode` = `LayerNode | GroupLayerNode | PaintLayerNode | InstanceLayerNode | FillLayerNode`
- `substance_painter.layerstack.EffectNode` = `GeneratorEffectNode | PaintEffectNode | FillEffectNode | LevelsEffectNode | CompareMaskEffectNode | FilterEffectNode | ColorSelectionEffectNode | AnchorPointEffectNode`

## Enums

### NodeType

For more information about layers and effects, see the Layers and effects section.

| Name | Description |
|------|-------------|
| `PaintLayer` | A layer that can be painted on with brushes and particles. |
| `PaintEffect` | An effect that can be painted on with brushes and particles. |
| `FillLayer` | A layer that takes a material or resources as input. |
| `FillEffect` | An effect that takes a material or resources as input. |
| `GeneratorEffect` | An effect that takes a Generator substance as input. |
| `FilterEffect` | An effect that takes a Filter substance as input. |
| `LevelsEffect` | An effect used to adjust the color ranges of an image. |
| `CompareMaskEffect` | An effect that compare two channels and produce a mask as a result. |
| `ColorSelectionEffect` | An effect that extract one or more colors from a bitmap to build a mask. |
| `GroupLayer` | A layer that contains other layers. |
| `InstanceLayer` | A layer that allows to synchronize layer parameters across multiple layers and Texture Sets |
| `AnchorPointEffect` | An effect that allows to expose any resource or element in the layer stack and reference it in different areas |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### MaskBackground

| Name | Description |
|------|-------------|
| `Black` | Everything is discarded by default. |
| `White` | Everything is included by default. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### BlendingMode

Blending Modes allow to mix the result of a layer with the other layers below in different manners.

| Name | Description |
|------|-------------|
| `Normal` | Displays the Top layer over the Bottom layer without transformation. |
| `PassThrough` | Flattens the Bottom layer into the Top layer. |
| `Disable` | Discards the blending of the layer, displaying only the previous layers. |
| `Replace` | Overwrites the Bottom layer. |
| `Multiply` | Multiplies the Top layer over the Bottom layer. |
| `Divide` | Divides the layers below by the color information of the current layer. |
| `InverseDivide` | Identical to `Divide` but the Top and Bottom layer are exchanged in the blending operation. |
| `Darken` | Keeps the minimum color value between the Top and the Bottom layer. |
| `Lighten` | Keeps the maximum color value between the Top and the Bottom layer. |
| `LinearDodge` | Adds the Top layer color value to the Bottom layer. |
| `Subtract` | Subtracts the Top layer Color from the Bottom layer. |
| `InverseSubtract` | Identical to `Subtract` but the Top and Bottom layer are exchanged in the blending operation. |
| `Difference` | Subtracts the Top layer Color from the Bottom Layer, but take the absolute value of the result |
| `Exclusion` | Similar to `Difference` but it will produce a result with a lower contrast. |
| `SignedAddition` | Both Adds and Subtracts Color information from the Bottom layer based on the Top layer colors. |
| `Overlay` | Combines both `Screen` and `Multiply` Blending Modes. |
| `Screen` | Inverts then multiplies color information from the Top and Bottom layer. This result is then inverted again. |
| `LinearBurn` | Adds the Top and Bottom layer Color information together and then subtract 1 from the result. |
| `ColorBurn` | Divides the Bottom layer by the Top layer. |
| `ColorDodge` | Divides the Bottom Layer by the inverted Top layer. |
| `SoftLight` | Similar to `Overlay`, but applied with a different curve to blend the Color information (less contrasted image). |
| `HardLight` | Similar to `Overlay`, but the order of operations is inverted. |
| `VividLight` | Combines `ColorDodge` and `ColorBurn` blending modes. |
| `LinearLight` | Combines `LinearDodge` and `LinearBurn`. |
| `PinLight` | Lightens and darkens color information based on the Top layer colors. |
| `Tint` | Keeps only the Hue of the Top Layer and uses the Saturation and Value of the Bottom Layer. |
| `Saturation` | Keeps only the Saturation of the Top Layer and uses the Hue and Value of the Bottom Layer. |
| `Color` | Keeps only the Hue and Saturation of the Top Layer and uses the Value of the Bottom Layer. |
| `Value` | Keeps only the Value of the Top Layer and uses the Hue and Saturation of the Bottom Layer. |
| `NormalMapCombine` | Whiteout Blending operation. Preserve details while making sure flat normals still operate properly. |
| `NormalMapDetail` | Detail Oriented Blending operation (Reoriented Normal Mapping), more precise than Normal Map Combine. |
| `NormalMapInverseDetail` | Same as `NormalMapDetail`, but it is the Bottom layer that is transformed to fit the surface of the Top layer. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### GeometryMaskType

| Name | Description |
|------|-------------|
| `Mesh` | The geometry mask will apply to mesh names. |
| `UVTile` | The geometry mask will apply to uv tiles. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

## See Also

- [Blending modes documentation](https://helpx.adobe.com/substance-3d-painter/interface/layer-stack/blending-modes.html)
- [Geometry mask documentation](https://helpx.adobe.com/substance-3d-painter/interface/layer-stack/geometry-mask.html)
- [Layer instancing documentation](https://helpx.adobe.com/substance-3d-painter/interface/layer-stack/layer-instancing.html)