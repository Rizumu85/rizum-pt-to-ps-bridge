# Baking Module

The `baking` module allows to set baking parameters and launch baking of mesh maps.

## Example

```python
import substance_painter.baking as baking
import substance_painter.textureset as textureset
from substance_painter.baking import BakingParameters, MeshMapUsage, CurvatureMethod
from PySide2 import QtCore

# set baking parameters
baking_params = BakingParameters.from_texture_set_name("Name for ts")
texture_set = baking_params.texture_set()
common_params = baking_params.common()
# use QUrl to correctly format the file path with file:/// prefix
highpoly_mesh_path = QtCore.QUrl.fromLocalFile("C:/Documents/highpoly.fbx").toString()
ao_params = baking_params.baker(MeshMapUsage.AO)
BakingParameters.set({
    common_params['OutputSize'] : (10,10),
    common_params['HipolyMesh'] : highpoly_mesh_path,
    ao_params['Distribution'] : ao_params['Distribution'].enum_value('Cosine')})

# check if common parameters are shared between Texture Sets (True at project creation)
common_params_are_shared = bool(baking.get_link_group_common_parameters())

# unlink common parameters. The common parameters for all Texture Sets become independent
baking.unlink_all_common_parameters()

# recheck whether common parameters are shared between Texture Sets (now False)
common_params_are_linked = bool(baking.get_link_group_common_parameters())

ts1 = textureset.TextureSet.from_name("Name for ts1")
ts2 = textureset.TextureSet.from_name("Name for ts2")

# get the list of Texture Sets which are linked for AO with ts1
# it's not yet linked, so returns only [ts1]
linked_with_ts1 = baking.get_linked_texture_sets(ts1, MeshMapUsage.AO)

# link AO baking parameters for ts1 and ts2 together into a group,
# keeping ts1 parameters for both
baking.set_linked_group([ts1,ts2], ts1, MeshMapUsage.AO)

# get the new list of Texture Sets which are linked with ts1
# now they are linked, so it returns [ts1, ts2]
linked_with_ts1 = baking.get_linked_texture_sets(ts1, MeshMapUsage.AO)

# finally unlink AO baking parameters
baking.unlink_all(MeshMapUsage.AO)

# get curvature method
curvature_method = baking_params.get_curvature_method()

# set curvature method
baking_params.set_curvature_method(CurvatureMethod.FromMesh)

# check whether the baking is enabled on the Texture Set level and enable it
baking_params.is_textureset_enabled()
baking_params.set_textureset_enabled(True)

# check if AO usage is enabled for baking and enable it
baking_params.is_baker_enabled(MeshMapUsage.AO)
baking_params.set_baker_enabled(MeshMapUsage.AO, True)

# get all usages enabled for baking
baking_params.get_enabled_bakers()

# set usages enabled for baking
baking_params.set_enabled_bakers([MeshMapUsage.AO, MeshMapUsage.Normal])

# check if one UV Tile is enabled for baking, disable it
baking_params.is_uv_tile_enabled(texture_set.uv_tile(0,0))
baking_params.set_uv_tile_enabled(texture_set.uv_tile(0,0), False)

# get all UV Tiles enabled for baking
baking_params.get_enabled_uv_tiles()
# set UV Tiles enabled for baking
baking_params.set_enabled_uv_tiles([texture_set.uv_tile(0,0), texture_set.uv_tile(0,1)])
```

**See also:**
- `substance_painter.textureset.TextureSet`
- `substance_painter.textureset.MeshMapUsage`
- `substance_painter.textureset.UVTile`

## Notes (Substance 3D Painter 11.1.0)

- In the Curvature From Map baker, the `substance_painter.properties.Property` named `PerVertex` (boolean type) has been removed. The behavior is now always equivalent to `PerVertex = False` (Per Fragment mode in the UI).
- The `substance_painter.properties.Property` entries `TonemappingMin` and `TonemappingMax` (float type) have been removed in favor of `TonemappingBounds` (array of 2 float).

## Classes

### BakingStatus

Status code of the baking process.

**Members:**

| Name | Description |
|------|-------------|
| `Success` | The baking was successful. |
| `Cancel` | The baking was cancelled by the user. |
| `Fail` | The baking could not complete; the cause is detailed in the log. |

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### CurvatureMethod

**Members:** `FromMesh`, `FromNormalMap`

> **Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### BakingParameters

Baking parameters for a given texture set.

**Parameters:**
- `material_id` (int)

#### Example

```python
# This example shows how to discover the names of the baking parameters
import substance_painter as sp

# Get the first texture set of the current project
textureset = sp.textureset.all_texture_sets()[0]
# Retrieve baking parameters
baking_params = sp.baking.BakingParameters.from_texture_set(textureset)

# Print the keys of the common baking parameters
print(f'Common: {baking_params.common().keys()}')
# Print the keys of the baking parameters of the AO mesh map
print(f'AO: {baking_params.baker(sp.baking.MeshMapUsage.AO).keys()}')
```

**See also:**
- `substance_painter.textureset.TextureSet`
- `substance_painter.textureset.MeshMapUsage`

#### Methods

##### from_texture_set(texture_set)
*static method*

Get the baking parameters for the given texture set object.

**Parameters:**
- `texture_set` (TextureSet) – The texture set.

**Returns:**
- BakingParameters – The baking parameters for the given texture set.

**See also:** `substance_painter.textureset.TextureSet`

##### from_texture_set_name(texture_set_name)
*static method*

Get the baking parameters for the given texture set name.

**Parameters:**
- `texture_set_name` (str) – The texture set name.

**Returns:**
- BakingParameters – The baking parameters for the given texture set.

**See also:** `substance_painter.properties.Property`

##### texture_set()

Get the associated texture set.

**Returns:**
- TextureSet – The texture set associated with this BakingParameters instance.

**See also:** `substance_painter.textureset.TextureSet`

##### common()

Get the parameters common to all bakers, like baking resolution.

**Returns:**
- Dict[str, Property] – The common parameters.

**See also:** `substance_painter.properties.Property`

##### baker(baked_map)

Get the parameters specific to a given baked map.

**Parameters:**
- `baked_map` (MeshMapUsage) – The baked map usage.

**Returns:**
- Dict[str, Property] – The corresponding baked map parameters.

**See also:**
- `substance_painter.textureset.MeshMapUsage`
- `substance_painter.properties.Property`

##### set(property_values)
*static method*

Set property values in batch.

**Parameters:**
- `property_values` (Dict[Property, PropertyValue]) – A dict of properties to be set with their corresponding new values.

**See also:** `substance_painter.properties.Property`

##### get_curvature_method()

Get the curvature method used for baking.

**Returns:**
- CurvatureMethod – The curvature method used for baking.

**See also:** `set_curvature_method`

##### set_curvature_method(method)

Set the curvature method to use for baking.

**Parameters:**
- `method` (CurvatureMethod) – The new method to use for baking.

**See also:** `get_curvature_method`

##### is_baker_enabled(usage)

Whether some usage is enabled for baking.

**Parameters:**
- `usage` (MeshMapUsage) – The baked map usage.

**Returns:**
- bool – True if the corresponding usage is enabled for baking.

##### set_baker_enabled(usage, enable)

Enable or disable a usage for baking.

**Parameters:**
- `usage` (MeshMapUsage) – The baked map usage.
- `enable` (bool) – Enable or disable.

##### get_enabled_bakers()

Get all usages enabled for baking.

**Returns:**
- List[MeshMapUsage] – Enabled usages.

##### set_enabled_bakers(enabled_usages)

Set usages enabled for baking. Usages not in this list will be disabled.

**Parameters:**
- `enabled_usages` (List[MeshMapUsage]) – Enabled usages.

##### is_textureset_enabled()

Whether this Texture Set is enabled for baking.

**Returns:**
- bool – True if this Texture Set is enabled for baking.

##### set_textureset_enabled(enable)

Enable or disable this Texture Set for baking.

**Parameters:**
- `enable` (bool) – Enable or disable.

##### is_uv_tile_enabled(uv_tile)

Whether a UV Tile is enabled for baking.

**Parameters:**
- `uv_tile` (UVTile) – The UV Tile.

**Returns:**
- bool – True if the UV Tile is enabled for baking.

**See also:**
- `substance_painter.textureset.TextureSet`
- `substance_painter.textureset.UVTile`

##### set_uv_tile_enabled(uv_tile, enable)

Enable or disable an UV Tile for baking.

**Parameters:**
- `uv_tile` (UVTile) – The UV Tile.
- `enable` (bool) – Enable or disable.

**See also:**
- `substance_painter.textureset.TextureSet`
- `substance_painter.textureset.UVTile`

##### get_enabled_uv_tiles()

Get all UV Tiles enabled for baking.

**Returns:**
- List[UVTile] – Enabled UV Tiles.

**See also:**
- `substance_painter.textureset.TextureSet`
- `substance_painter.textureset.UVTile`

##### set_enabled_uv_tiles(enabled_uv_tiles)

Set UV Tiles enabled for baking. All other tiles will be disabled.

**Parameters:**
- `enabled_uv_tiles` (List[UVTile]) – Enabled UV Tiles.

**See also:**
- `substance_painter.textureset.TextureSet`
- `substance_painter.textureset.UVTile`

## Functions

### set_linked_group(group, reference, usage)

Make a group of Texture Sets share the same baking parameters for the given 'usage'. After that, editing the 'usage' parameters of one of the group's Texture Set will impact the whole group.

**Parameters:**
- `group` (List[TextureSet]) – Texture Sets to be included in the new group.
- `reference` (TextureSet) – Texture Set which parameters are applied to the whole group.
- `usage` (MeshMapUsage) – Usage of the group.

### set_linked_group_common_parameters(group, reference)

Make a group of Texture Sets share the same baking common parameters. After that, editing a common parameter of one of the group's Texture Set will impact the whole group.

**Parameters:**
- `group` (List[TextureSet]) – Texture Sets to be included in the new group.
- `reference` (TextureSet) – Texture Set which parameters are applied to the whole group.

### unlink_all(usage)

Unlink all Texture Sets for a given usage. That is, remove the group if it exists, so that all Texture Sets have their own copy of the parameters.

**Parameters:**
- `usage` (MeshMapUsage) – Usage to unlink.

### unlink_all_common_parameters()

Unlink all Texture Sets for common parameters. That is, remove the group if exists, so that all Texture Sets have their own copy of the parameters.

### get_link_group(usage)

Get the list of Texture Sets that share baking parameters for a given usage.

**Parameters:**
- `usage` (MeshMapUsage) – Usage to query.

**Returns:**
- List[TextureSet] – All linked Texture Sets for the usage. Empty list if no Texture Set are linked.

### get_link_group_common_parameters()

Get the list of Texture Sets that share common baking parameters.

**Returns:**
- List[TextureSet] – All linked Texture Sets for common parameters. Empty list if no Texture Set are linked.

### get_linked_texture_sets(texture_set, usage)

Get the list of Texture Sets that share the same parameters as some Texture Set, for a given usage.

**Parameters:**
- `texture_set` (TextureSet) – The Texture Set to query
- `usage` (MeshMapUsage) – The usage to query

**Returns:**
- List[TextureSet] – The list of Texture Sets sharing parameters with the input Texture Set. Contains at least the input Texture Set if no group exists for the usage.

### get_linked_texture_sets_common_parameters(texture_set)

Get the list of Texture Sets that share the same parameters as some Texture Set, for common parameters.

**Parameters:**
- `texture_set` (TextureSet) – The Texture Set to query

**Returns:**
- List[TextureSet] – The list of Texture Sets sharing common parameters with the input Texture Set. Contains at least the input Texture Set if no group exists for common parameters.

### bake_async(texture_set)

Launch the baking process for a Texture Set, using the current baking configuration. The configuration is set by setting baking parameters, enabling Texture Set, selecting UV Tiles for baking, setting curvature method etc. This function is asynchronous. When the baking process is finished, the `substance_painter.event.BakingProcessEnded` event is sent.

**Parameters:**
- `texture_set` (TextureSet) – The Texture Set to bake.

**Returns:**
- StopSource – Can be used to cancel the asynchronous computation.

**See also:**
- `BakingParameters`
- `substance_painter.event.BakingProcessAboutToStart`
- `substance_painter.event.BakingProcessProgress`
- `substance_painter.event.BakingProcessEnded`
- `substance_painter.async_utils.StopSource`

### bake_selected_textures_async()

Launch the baking process, using the current baking configuration. The configuration is set by setting baking parameters, enabling Texture Set, selecting UV Tiles for baking, setting curvature method etc. This function is asynchronous. When the baking process is finished, the `substance_painter.event.BakingProcessEnded` event is sent.

**Returns:**
- StopSource – Can be used to cancel the asynchronous computation.

**See also:**
- `BakingParameters`
- `substance_painter.event.BakingProcessAboutToStart`
- `substance_painter.event.BakingProcessProgress`
- `substance_painter.event.BakingProcessEnded`
- `substance_painter.async_utils.StopSource`