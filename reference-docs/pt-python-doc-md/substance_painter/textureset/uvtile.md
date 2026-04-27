# UVTile Class

## `substance_painter.textureset.UVTile`

**Class:** `substance_painter.textureset.UVTile(u: int, v: int, _material_id: int)`

A UV Tile coordinates.

### Parameters

- **u** (*int*) – The U coordinate of the UV Tile.
- **v** (*int*) – The V coordinate of the UV Tile.
- **_material_id** (*int*)

### See also

[`TextureSet.all_uv_tiles()`](textureset.html#substance_painter.textureset.TextureSet.all_uv_tiles)

---

## Properties

### `UVTile.name`

**Property:** `name: str`

The name of the UV Tile.

UV Tile names must be unique within a Texture Set.

- **Type:** str
- **Getter:** Get the UV Tile name.
- **Setter:** Set the UV Tile name.

**Raises:**
- **ProjectError** – If no project is opened.
- **ServiceNotFoundError** – If Substance 3D Painter has not started all its services yet.
- **ValueError** – If the UV Tile is invalid.
- **ValueError** – If the name of the UV Tile contains reserved characters.
- **ValueError** – If the name of the UV Tile is not unique within the Texture Set.

### `UVTile.description`

**Property:** `description: str`

The description of the UV Tile.

- **Type:** str
- **Getter:** Get the UV Tile description.
- **Setter:** Set the UV Tile description.

**Raises:**
- **ProjectError** – If no project is opened.
- **ServiceNotFoundError** – If Substance 3D Painter has not started all its services yet.
- **ValueError** – If the UV Tile is invalid.

---

## Methods

### `UVTile.get_resolution()`

**Method:** `get_resolution() → Resolution`

Get the UV Tile resolution.

**Returns:**
- The resolution of this UV Tile in pixels.

**Return type:** `Resolution`

**Raises:**
- **ProjectError** – If no project is opened.
- **ServiceNotFoundError** – If Substance Painter has not started all its services yet.
- **ValueError** – If the UV Tile is invalid.

> **Note:** The time complexity of this function is linear in the number of UV Tiles in the parent Texture Set. If you need to process multiple UV Tiles, please see `TextureSet.get_uvtiles_resolution`.

**See also:**
- [`UVTile.set_resolution()`](#uvtileset_resolution)
- [`UVTile.reset_resolution()`](#uvtilereset_resolution)
- [`TextureSet.get_uvtiles_resolution()`](textureset.html#substance_painter.textureset.TextureSet.get_uvtiles_resolution)

### `UVTile.set_resolution()`

**Method:** `set_resolution(new_resolution: Resolution)`

Set the resolution of the UV Tile.

See resolution restrictions: [`Resolution`](index.html#substance_painter.textureset.Resolution).

**Parameters:**
- **new_resolution** (*Resolution*) – The new resolution for this UV Tile.

**Raises:**
- **ProjectError** – If no project is opened.
- **ServiceNotFoundError** – If Substance Painter has not started all its services yet.
- **ValueError** – If `new_resolution` is not square.
- **ValueError** – If `new_resolution` is not a valid resolution.
- **ValueError** – If the UV Tile is invalid.

> **Note:** The time complexity of this function is linear in the number of UVTiles in the parent Texture Set. If you need to process multiple UVTiles, please see `TextureSet.set_uvtiles_resolution`.

**See also:**
- [`UVTile.get_resolution()`](#uvtileget_resolution)
- [`UVTile.reset_resolution()`](#uvtilereset_resolution)
- [`TextureSet.set_resolution()`](textureset.html#substance_painter.textureset.TextureSet.set_resolution)
- [`TextureSet.set_uvtiles_resolution()`](textureset.html#substance_painter.textureset.TextureSet.set_uvtiles_resolution)

### `UVTile.reset_resolution()`

**Method:** `reset_resolution()`

Reset the resolution of the UV Tile to match the parent Texture Set.

**Raises:**
- **ProjectError** – If no project is opened.
- **ServiceNotFoundError** – If Substance Painter has not started all its services yet.
- **ValueError** – If the UV Tile is invalid.

> **Note:** The time complexity of this function is linear in the number of UVTiles in the parent Texture Set. If you need to process multiple UVTiles, please see `TextureSet.reset_uvtiles_resolution`.

**See also:**
- [`UVTile.get_resolution()`](#uvtileget_resolution)
- [`UVTile.set_resolution()`](#uvtileset_resolution)
- [`TextureSet.reset_uvtiles_resolution()`](textureset.html#substance_painter.textureset.TextureSet.reset_uvtiles_resolution)

### `UVTile.all_mesh_names()`

**Method:** `all_mesh_names() → List[str]`

Get the list of meshes of the UV Tile.

**Raises:**
- **ProjectError** – If no project is opened.
- **ServiceNotFoundError** – If Substance Painter has not started all its services yet.
- **ValueError** – If the UV Tile is invalid.

**Return type:** *List*[str]

**See also:**
- [`TextureSet.all_mesh_names()`](textureset.html#substance_painter.textureset.TextureSet.all_mesh_names)

---

*© Copyright 2020, Adobe.*