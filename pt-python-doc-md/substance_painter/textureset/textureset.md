# TextureSet Class

## substance_painter.textureset.TextureSet

A Substance 3D Painter Texture Set. A Texture Set has a resolution and a number of stacks, and can be layered or not. It optionally also has a number of UV Tiles.

It uses a set of baked Mesh map textures. Each Mesh map has a defined MeshMapUsage.

If the corresponding material is not layered, the Texture Set has just one stack, which is transparent to the user. If the material is layered, the Texture Set has several stacks.

### Example

```python
import substance_painter.textureset

# Get the Texture Set "TextureSetName":
my_texture_set = substance_painter.textureset.TextureSet.from_name("TextureSetName")

# Show the resolution of the Texture Set:
resolution = my_texture_set.get_resolution()
print("The resolution is {0}x{1}".format(resolution.width, resolution.height))

# Change the resolution of the Texture Set:
my_texture_set.set_resolution(substance_painter.textureset.Resolution(512, 512))

# Show information about layering:
if my_texture_set.is_layered_material():
    print("{0} is a layered material".format(my_texture_set.name()))

    # Get the stack called "Mask1" from the Texture Set:
    mask_stack = my_texture_set.get_stack("Mask1")

    # Print "TextureSetName/Mask1":
    print(mask_stack)

else:
    print("{0} is not a layered material".format(my_texture_set.name()))

# Show information about UV Tiles:
if my_texture_set.has_uv_tiles():
    print("{0} has UV Tiles:".format(my_texture_set.name()))
    for tile in my_texture_set.all_uv_tiles():
        print("Tile {0} {1}".format(tile.u, tile.v))

# List all the stacks of the Texture Set "TextureSetName":
for stack in my_texture_set.all_stacks():
    print(stack)

# Query ambiant occlusion Mesh map of the Texture Set "TextureSetName":
usage = substance_painter.textureset.MeshMapUsage.AO
meshMapResource = my_texture_set.get_mesh_map_resource(usage)

if meshMapResource is None :
    print("{0} does not have a Mesh map defined for usage {1}"
        .format(my_texture_set.name(), usage))
else:
    print("{0} uses {1} Mesh map for usage {2}"
        .format(my_texture_set.name(), meshMapResource, usage))

# Unset ambiant occlusion Mesh map of the Texture Set "TextureSetName":
my_texture_set.set_mesh_map_resource(usage, None)
```

**See also:** Stack, UVTile, MeshMapUsage, [Texture Set documentation](https://www.adobe.com/go/painter-texture-set)

**Parameters:** material_id (int)

---

## Methods

### from_name(texture_set_name)

Get the Texture Set from its name.

**Parameters:**
- `texture_set_name` (str) - The name of the Texture Set.

**Note:** The Texture Set name is case sensitive.

**Raises:**
- `ProjectError` - If no project is opened.
- `ServiceNotFoundError` - If Substance 3D Painter has not started all its services yet.
- `TypeError` - If `texture_set_name` is missing or not a string.
- `ValueError` - If `texture_set_name` is empty.
- `ValueError` - If there is no Texture Set with the name `texture_set_name`.

---

### Properties

#### original_name

The original name of the Texture Set, as it was when it was imported.

**Type:** str

**Raises:**
- `ProjectError` - If no project is opened.
- `ServiceNotFoundError` - If Substance 3D Painter has not started all its services yet.
- `ValueError` - If the Texture Set is invalid.

#### name

The name of the Texture Set. Texture Set names must be unique.

**Type:** str

**Raises:**
- `ProjectError` - If no project is opened.
- `ServiceNotFoundError` - If Substance 3D Painter has not started all its services yet.
- `ValueError` - If the Texture Set is invalid.
- `ValueError` - If the name of the Texture Set contains reserved characters.
- `ValueError` - If the name of the Texture Set is not unique.

#### description

The description of the Texture Set.

**Type:** str

**Raises:**
- `ProjectError` - If no project is opened.
- `ServiceNotFoundError` - If Substance 3D Painter has not started all its services yet.
- `ValueError` - If the Texture Set is invalid.

---

### Methods

#### is_layered_material()

Query if this Texture Set uses material layering.

**Returns:** `True` if the Texture Set uses material layering, `False` otherwise.

**Return type:** bool

**Raises:**
- `ProjectError` - If no project is opened.
- `ServiceNotFoundError` - If Substance 3D Painter has not started all its services yet.
- `ValueError` - If the Texture Set is invalid.

#### all_stacks()

List all the stacks from this Texture Set.

**Returns:** All the stacks of this Texture Set.

**Return type:** list[Stack]

**Raises:**
- `ProjectError` - If no project is opened.
- `ServiceNotFoundError` - If Substance 3D Painter has not started all its services yet.
- `ValueError` - If the Texture Set is invalid.

**See also:** TextureSet.get_stack()

#### get_stack(stack_name='')

Get a stack of this Texture Set from its name.

**Parameters:**
- `stack_name` (str) - The stack name. Leave empty if the Texture Set does not use material layering.

**Returns:** The stack.

**Return type:** Stack

**Note:** The stack name is case sensitive.

**Raises:**
- `ProjectError` - If no project is opened.
- `ServiceNotFoundError` - If Substance 3D Painter has not started all its services yet.
- `ValueError` - If the Texture Set is invalid.

**See also:** TextureSet.all_stacks()

#### get_resolution()

Get the Texture Set resolution.

**Returns:** The resolution of this Texture Set in pixels.

**Return type:** Resolution

**Raises:**
- `ProjectError` - If no project is opened.
- `ServiceNotFoundError` - If Substance 3D Painter has not started all its services yet.
- `ValueError` - If the Texture Set is invalid.

**See also:** TextureSet.set_resolution(), set_resolutions()

#### set_resolution(new_resolution)

Set the resolution of the Texture Set.

See resolution restrictions: Resolution.

**Note:** For any Texture Set, you can find its accepted resolutions in the "Texture Set Settings" window, in the "Size" menu.

**Parameters:**
- `new_resolution` (Resolution) - The new resolution for this Texture Set.

**Raises:**
- `ProjectError` - If no project is opened.
- `ServiceNotFoundError` - If Substance 3D Painter has not started all its services yet.
- `ValueError` - If `new_resolution` is not a valid resolution.
- `ValueError` - If the Texture Set is invalid.

**See also:** TextureSet.get_resolution(), set_resolutions()

#### has_uv_tiles()

Check if the Texture Set uses the UV Tiles workflow.

**Returns:** `True` if the Texture Set uses the UV Tiles workflow, `False` otherwise.

**Return type:** bool

**Raises:**
- `ProjectError` - If no project is opened.

**See also:** all_uv_tiles()

#### uv_tile(u_coord, v_coord)

Get the Texture Set UV Tile at (u, v) coordinates.

**Parameters:**
- `u_coord` (int) - The u coordinate of the UV Tile.
- `v_coord` (int) - The v coordinate of the UV Tile.

**Returns:** The Texture Set UV Tile at (u, v) coordinate.

**Return type:** UVTile

**Raises:**
- `ProjectError` - If no project is opened.

#### all_uv_tiles()

Get the list of the Texture Set UV Tiles, ordered by U then V coordinates.

**Returns:** List of the Texture Set UV Tiles, ordered by U then V coordinates.

**Return type:** List[UVTile]

**Raises:**
- `ProjectError` - If no project is opened.

**See also:** has_uv_tiles()

#### get_uvtiles_resolution()

Get all UV Tiles that have a different resolution from the Texture Set, associated to their effective resolution.

**Returns:** The dictionary of uvtiles and their associated resolution.

**Return type:** Dict[UVTile, Resolution]

**Raises:**
- `ProjectError` - If no project is opened.

**See also:** UVTile.get_resolution()

#### set_uvtiles_resolution(resolutions)

Set the resolution of the given UV Tiles to the associated resolution.

**Parameters:**
- `resolutions` (Dict[UVTile, Resolution]) - The dictionary of UV Tiles and their associated resolution.

**Raises:**
- `ProjectError` - If no project is opened.

**See also:** UVTile.set_resolution()

#### reset_uvtiles_resolution(uvtiles)

Reset the resolution of the given UV Tiles to the parent Texture Set's resolution.

**Parameters:**
- `uvtiles` (List[UVTile]) - The list of UV Tiles to be reset.

**Raises:**
- `ProjectError` - If no project is opened.

**See also:** UVTile.reset_resolution()

#### all_mesh_names()

Get the list of meshes of the Texture Set. When using UV Tiles, the result is the union of the mesh names of every UV Tiles.

**Return type:** List[str]

**Raises:**
- `ProjectError` - If no project is opened.
- `ServiceNotFoundError` - If Substance Painter has not started all its services yet.

**See also:** UVTile.all_mesh_names()

#### get_mesh_map_resource(usage)

Query the Mesh map for the given usage of the Texture Set.

**Parameters:**
- `usage` (MeshMapUsage) - Which Mesh map usage is queried.

**Returns:** The Mesh map resource or None.

**Return type:** ResourceID

#### set_mesh_map_resource(usage, new_mesh_map)

Replace the Mesh map for the given usage of the Texture Set.

**Parameters:**
- `usage` (MeshMapUsage) - Which Mesh map usage to replace.
- `new_mesh_map` (ResourceID, optional) - The new Mesh map or None to unset.

**Raises:**
- `ResourceNotFoundError` - If the resource `new_mesh_map` is not found or is not of type IMAGE.
- `ValueError` - If the resource is already used for another Mesh map usage for the Texture Set.

**Return type:** None