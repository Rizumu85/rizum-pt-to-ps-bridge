# Export Module

This module exposes functions to export assets (textures and meshes) from a project under a variety of formats. It is the scripting equivalent of the "Export textures" and the "Export mesh" windows.

For the export textures, the export configuration is defined with a JSON file, but can also use existing export presets.

## ExportStatus

Status code of the export process.

**Members:**

| Name | Description |
|------|-------------|
| `Success` | The export was successful. |
| `Cancelled` | The export was cancelled by the user. |
| `Warning` | The export completed with warnings. |
| `Error` | The export could not complete; the cause is detailed in the log. |

**Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

## Export Textures

### list_project_textures(json_config)

Get list of textures that would be exported according to the given JSON configuration.

**Parameters:**
- `json_config` (dict): JSON object representing the export configuration to be used. See [JSON configuration](#full-json-config-dict-possibilities).

**Returns:**
- `Dict[Tuple[str, str], List[str]]`: List of texture files that would be exported, grouped by stack (Texture Set name, stack name).

**Raises:**
- `ProjectError`: If no project is opened.
- `ValueError`: If `json_config` is ill-formed, or is invalid in the context of the current project. Contains a human readable message.

**See also:** `export_project_textures()`

### TextureExportResult

Result of the export textures process.

**Parameters:**
- `status` (ExportStatus): Status code.
- `message` (str): Human readable status message.
- `textures` (Dict[Tuple[str, str], List[str]]): List of texture files written to disk, grouped by stack (Texture Set name, stack name).

### export_project_textures(json_config)

Export document textures according to the given JSON configuration. The return value contains the list of texture files written to disk.

The status of the return value can never be `Error`, any error causing the export to fail will raise an exception instead. However if the export fails, the associated event `ExportTextureEnded` will indeed receive `Error` as a status. If the export is cancelled by the user, the function return value will have the status `Cancelled` and contain the list of texture files written to disk before export was cancelled.

**Parameters:**
- `json_config` (dict): JSON object representing the export configuration to be used. See [JSON configuration](#full-json-config-dict-possibilities).

**Returns:**
- `TextureExportResult`: Result of the export process.

**Raises:**
- `ProjectError`: If no project is opened.
- `ValueError`: If `json_config` is ill-formed, or is invalid in the context of the current project. Contains a human readable message detailing the problem.

**See also:** `substance_painter.event.ExportTexturesAboutToStart`, `substance_painter.event.ExportTexturesEnded`

**Example:**

```python
import substance_painter.export

# Open a project we want to export from (see substance_painter.project
# for details). This step is not necessary if there is already a project
# opened in Substance 3D Painter.
import substance_painter.project
substance_painter.project.open("C:/projects/MeetMat.spp")

# Choose an export preset to use (see substance_painter.resource). This
# step is not mandatory as you can alternatively describe the export
# preset entirely in JSON (see the full example at the bottom of the
# page).
# Note: in this example the preset file format and bit depth are
# overridden below for '03_Base', but otherwise follow the export preset
# configuration.
import substance_painter.resource
export_preset = substance_painter.resource.ResourceID(
    context="starter_assets", name="Arnold (AiStandard)")

# Set the details of the export (a comprehensive example of all the
# configuration options is presented at the bottom of the page):
export_config = {
    "exportShaderParams": False,
    "exportPath": "C:/export",
    "defaultExportPreset" : export_preset.url(),
    "exportList": [
        {
            "rootPath": "01_Head"
        },
        {
            "rootPath": "02_Body"
        },
        {
            "rootPath": "03_Base"
        }],
    "exportParameters": [
        # No filters: those parameters apply to all exported maps
        {
            "parameters": {
                "dithering": True,
                "paddingAlgorithm": "infinite"
            }
        },
        # Force file format and bitDepth for all maps in '03_Base'
        {
            "filter": {"dataPaths": ["03_Base"]},
            "parameters": {
                "fileFormat" : "png",
                "bitDepth" : "8"
            }
        },
        # Force 2K size for all maps in '01_Head'
        {
            "filter": {"dataPaths": ["01_Head"]},
            "parameters": {
                "sizeLog2": 11
            }
        }]
    }

# Display the list of textures that should be exported, according to the
# configuration:
export_list = substance_painter.export.list_project_textures(export_config)
for k,v in export_list.items():
    print("Stack {0}:".format(k))
    for to_export in v:
        print(to_export)

# Actual export operation:
export_result = substance_painter.export.export_project_textures(export_config)

# In case of error, display a human readable message:
if export_result.status != substance_painter.export.ExportStatus.Success:
    print(export_result.message)

# Display the details of what was exported:
for k,v in export_result.textures.items():
    print("Stack {0}:".format(k))
    for exported in v:
        print(exported)
```

**See also:** `substance_painter.project`, `substance_painter.resource`, [Export documentation](https://www.adobe.com/go/painter-export)

### get_default_export_path()

Get the application default export path used for exporting textures. This path does not depend on the project and is the default value used when creating a new project.

**Returns:**
- `str`: The default export path of the application.

### PredefinedExportPreset

An export preset (output template) controls the behavior of the export process. A predefined preset has a dynamic list of maps exported depending on the project and can have pre/post processes that generates custom data (e.g. glTF). This type of export preset is embedded in the application and cannot be edited.

**Parameters:**
- `name` (str): The name of the preset.
- `url` (str): The URL of the preset.

**See also:** [Predefined presets documentation](https://helpx.adobe.com/substance-3d-painter/getting-started/export/export-presets/predefined-presets.html)

#### list_output_maps(stack)

Get the list of output maps based on the channels available on the given stack. The output maps have the same format as the `maps` list in the JSON configuration.

**Parameters:**
- `stack` (substance_painter.textureset.Stack): The stack to get the output maps from.

**Returns:**
- `dict`: The list of output maps on the channels available on the given stack. The output maps have the same format as the `maps` list in the JSON configuration. See [JSON configuration](#full-json-config-dict-possibilities).

**Raises:**
- `ProjectError`: If no project is opened.
- `ValueError`: If the given stack is invalid.

**See also:** `substance_painter.textureset`

**Example:**

```python
import substance_painter.export
import substance_painter.project
import substance_painter.textureset

# A project needs to be opened to introspect the output maps of a predefined export preset
substance_painter.project.open("C:/projects/MeetMat.spp")

# Retrieve all predefined export presets
predefined_presets = substance_painter.export.list_predefined_export_presets()

# Retrieve data of the first preset
predefined_preset = predefined_presets[0]
print("Name: " + predefined_preset.name + ", url: " + predefined_preset.url)
stack = substance_painter.textureset.get_active_stack()
print(predefined_preset.list_output_maps(stack))
```

### list_predefined_export_presets()

Get the list of predefined export presets (output templates).

**Returns:**
- `List[PredefinedExportPreset]`: The list of predefined export presets.

**See also:** Example in `PredefinedExportPreset`

### ResourceExportPreset

An export preset (output template) controls the behavior of the export process. A shelf export preset is a resource with the `Export` `substance_painter.resource.Type`. It can be modified by the user via the UI.

**Parameters:**
- `resource_id` (ResourceID): The resource ID of the export preset.

**See also:** `substance_painter.resource`, [Creating export presets](https://helpx.adobe.com/substance-3d-painter/getting-started/export/creating-export-presets.html)

#### list_output_maps()

Get the list of output maps for the given preset. The output maps have the same format as the `maps` list in the JSON configuration.

**Returns:**
- `dict`: The list of output maps for the given preset. The output maps have the same format as the `maps` list in the JSON configuration. See [JSON configuration](#full-json-config-dict-possibilities).

**Raises:**
- `ValueError`: If the given preset is invalid.

**Example:**

```python
import substance_painter.export
import substance_painter.project

substance_painter.project.open("C:/projects/MeetMat.spp")

# Retrieve all resource export presets
resource_presets = substance_painter.export.list_resource_export_presets()

# Retrieve PBR Metalllic Roughness export preset
preset = ""
match = "PBR Metallic Roughness"
for resource_preset in resource_presets :
    if resource_preset.resource_id.name == "PBR Metallic Roughness":
        print("Name: {}, url: {}".format(
            resource_preset.resource_id.name,
            resource_preset.resource_id.url()))
        preset = resource_preset
        break

maps = preset.list_output_maps()
# Add new output map 2D View
maps.append({
    'channels': [{
        'destChannel': 'R',
        'srcChannel': 'R',
        'srcMapName': 'View_2D',
        'srcMapType': 'virtualMap',
        'srcPath': ''
    }, {
        'destChannel': 'G',
        'srcChannel': 'G',
        'srcMapName': 'View_2D',
        'srcMapType': 'virtualMap',
        'srcPath': ''
    }, {
        'destChannel': 'B',
        'srcChannel': 'B',
        'srcMapName': 'View_2D',
        'srcMapType': 'virtualMap',
        'srcPath': ''
    }, {
        'destChannel': 'A',
        'srcChannel': 'A',
        'srcMapName': 'View_2D',
        'srcMapType': 'virtualMap',
        'srcPath': ''
    }],
    'fileName':
    '$mesh_$textureSet_2D_View',
    'parameters': {
        'bitDepth': '8',
        'dithering': False,
        'fileFormat': 'png'
    }
})

# Create a new preset
newPresetName = "PBR Metallic Roughness 2D View"
newPreset = {
    "name": newPresetName,
    "maps": maps
}
# Use the preset in the export configuration
export_config = {
    "exportShaderParams": False,
    "exportPath": "C:/export",
    "defaultExportPreset" : newPresetName,
    "exportPresets": [newPreset],
    "exportList": [
        {
            "rootPath": "01_Head"
        },
        {
            "rootPath": "02_Body"
        },
        {
            "rootPath": "03_Base"
        }],
    "exportParameters": [
        {
            "parameters": {
                "dithering": True,
                "paddingAlgorithm": "infinite"
            }
        }]
    }

substance_painter.export.export_project_textures(export_config)
```

### list_resource_export_presets()

Get the list of export presets (output templates). This list contains all export presets available in the shelves (presets provided by default and custom ones if any).

**Returns:**
- `List[ResourceExportPreset]`: The list of export presets.

**See also:** Example in `ResourceExportPreset`

## Full JSON Config Dict Possibilities

```javascript
{
    // Path to the root folder where texture files will be exported.
    "exportPath": "C:/export",
    // Whether to export shader instances to a JSON file.
    "exportShaderParams": true,
    // (optional) Export preset to be used when no export preset is provided in
    // "exportList.exportPreset".
    // The value can be the name of a preset defined in the "exportPresets" part
    // of the configuration JSON:
    "defaultExportPreset": "preset1",
    // Alternatively the value can be a URL to an existing preset file (see
    // substance_painter.resource) listed in the export dialog:
    // "defaultExportPreset" : substance_painter.resource.ResourceID(
    //     context="starter_assets",
    //     name="PBR Metallic Roughness").url(),
    // (optional) List of export presets definitions.
    "exportPresets": [
        {
            // Defines the name of the export preset. This name can be referenced in
            // "defaultExportPreset" and/or "exportList.exportPreset".
            "name": "preset1",
            // List of maps making up this export preset.
            "maps": [
                {
                    // Filename of the texture file written to disk; may contain wildcards
                    // resolved at export time.
                    // (e.g. "$project_$mesh_$textureSet_$udim_$sceneMaterial_BaseColor")
                    //
                    //     $project: Project name.
                    //     $mesh: Filename of the imported mesh.
                    //     $textureSet: Current Texture Set.
                    //     $sceneMaterial: Current material name, as found in the imported
                    //     mesh.
                    //     $udim: Current UV Tile (e.g. 1001).
                    "fileName": "$textureSet_color",
                    // List of source/destination defining which channels will make up the
                    // texture file.
                    "channels": [
                        {
                            // Channel to write to.
                            //     L (Luminance), R (Red), G (Green), B (Blue), A (Alpha)
                            //
                            // In addition to alpha channel, either R+G+B must be specified, or
                            // either L only.
                            "destChannel": "R",
                            // Channel to read from.
                            //     L, R, G, B, A
                            //
                            // When the source map is color, L will generate a mix of R+G+B.
                            "srcChannel": "R",
                            // The type of map to read from:
                            //     documentMap: Maps present in the document (e.g. "baseColor").
                            //     meshMap: Baked mesh maps (e.g. "normal").
                            //     virtualMap: Generated map (e.g. "f0").
                            //     defaultMap: Constant color (e.g. "black").
                            "srcMapType": "documentMap",
                            // Name of the map of type scrMapType.
                            //
                            // For type documentMap:
                            //     basecolor, height, specular, opacity, emissive, displacement,
                            //     glossiness, roughness, anisotropylevel, anisotropyangle,
                            //     transmissive, scattering, reflection, ior, metallic, normal,
                            //     ambientOcclusion, diffuse, specularlevel, blendingmask, user0,
                            //     user1, user2, user3, user4, user5, user6, user7.
                            //
                            // For type meshMap:
                            //     ambient_occlusion, id, curvature, normal_base,
                            //     world_space_normals, position, thickness.
                            //
                            // For type virtualMap:
                            //     Normal_OpenGL, Normal_DirectX, AO_Mixed, Diffuse, Specular,
                            //     Glossiness, Unity4Diff, Unity4Gloss, reflection, 1/ior,
                            //     Glossiness2, f0, View_2D.
                            //
                            // For type defaultMap:
                            //    black, white.
                            "srcMapName": "baseColor"
                        }
                    ],
                    // (optional) Export parameters to be used for this export preset map.
                    //
                    // When "parameters" is not provided, the existing parameters are used.
                    // When "parameters" is provided, it overrides the existing parameters.
                    //
                    // Each individual parameter is optional and, when defined, overrides
                    // previously defined parameters. See in exportList.parameters how the
                    // rules are applied.
                    //
                    // It is important to understand that even though this section is
                    // optional, if after evaluating all the rules some parameters remain
                    // undefined, the configuration is invalid.
                    "parameters": {
                        // (optional) File format (and file extension) of the generated
                        // texture file.
                        "fileFormat": "png",
                        // (optional) Bit depth.
                        //
                        // The bit depth must be supported by the file format.
                        "bitDepth": "16",
                        // (optional) Whether to use dithering.
                        "dithering": false,
                        // (optional) Size of the texture file in log2.
                        // (i.e. 10 means 2^10 = 1024)
                        //
                        // When "sizeLog2" is not provided, the texture size from the project
                        // is used.
                        //
                        // It can either be a single integer, or an array of two integers.
                        //
                        // If it's a single integer, it represents the biggest of width and
                        // height, and will maintain the aspect ratio.
                        // (i.e. 10 means a 2048x4086 map will be exported as 512x1024)
                        //
                        // If it's an array of two integers, the original aspect ratio will be
                        // ignored.
                        // (i.e. [10, 12] means a 2048x4086 map will be exported as 1024x4096)
                        "sizeLog2": 10,
                        // (optional) Padding algorithm used to fill holes in rendered
                        // texture.
                        //
                        // The possible values are:
                        //     passthrough, color, transparent, diffusion, infinite.
                        "paddingAlgorithm": "diffusion",
                        // (optional) When padding algorithm needs it, distance in pixels used
                        // by the padding algorithm.
                        //
                        // Dilation distance is needed for transparent, color and diffusion
                        // padding algorithms.
                        "dilationDistance": 16
                    }
                }
            ]
        }
    ],
    // List of subparts of the document to export.
    "exportList": [
        {
            // Root path of the document structure this subpart applies to.
            //
            // For Texture Sets without stacks, this is a Texture Set name.
            // (e.g. "O1_Head")
            // For Texture Sets with stacks, this is Texture Set name + stack name
            // separated by /
            "rootPath": "02_Body/Mask",
            // (optional) In the selected rootPath, which maps to export.
            //
            // When "filter" is not provided, export everything.
            "filter": {
                // Which maps to export, as an array of map names.
                //
                // The map names are to be used as defined in
                // exportPresets.maps.fileName, including wildcards.
                // (e.g. ["$textureSet_color", "$textureSet_normal"])
                "outputMaps": [
                    "$textureSet_color"
                ],
                // Which UV Tiles to export, as an array of tile coordinates.
                // A tile coordinate is a 2 dimensional array of U and V coordinates.
                // (e.g. [[1, 1], [1, 2]] to export tiles U=1, V=1 and U=1, V=2)
                "uvTiles": [
                    [
                        1,
                        1
                    ]
                ]
            },
            // (optional) Export preset to use. If undefined, fall back to
            // "defaultExportPreset" value.
            // The value can be the name of a preset defined in "exportPresets":
            "exportPreset": "preset1"
            // Alternatively the value can be a URL to an existing preset file (see
            // substance_painter.resource) listed in the export dialog:
            // "defaultExportPreset" : substance_painter.resource.ResourceID(
            //     context="starter_assets",
            //     name="PBR Metallic Roughness").url(),
        }
    ],
    // List of rules used to override export parameters of texture files.
    //
    // For each exported texture file, the export process will go through this
    // list, in the order they are provided, to override export parameters.
    // Available export parameters are:
    //    fileFormat, bitDepth, dithering, sizeLog2, paddingAlgorithm and
    //    dilationDistance.
    // (see exportPresets.map.parameters)
    //
    // For each possible export parameter of each texture file:
    // First, the parameter is initialized with the value provided by the
    // exportPreset.maps.parameters, if any.
    // Then, the export process iterates the rules of exportParameters and tries
    // to match the texture file with the filter.
    // If the filter matches, the parameter is overridden by this rule, else it
    // stays untouched.
    //
    // At the end of the process, every parameter of every texture file must be
    // defined for the export process to be able to continue.
    // To achieve this, a good practice may be to define a default value for all
    // the parameters:
    // - For each preset map
    // - With a global exportParameters rule using a filter that always matches
    "exportParameters": [
        {
            // (optional) Select which texture files match the current rule.
            // (i.e. for which texture files this rule will override parameters)
            //
            // When "filter" is not provided, select everything.
            //
            // Examples:
            //     Filter that matches all:
            //         "filter" : {}
            //
            //     Filter that matches some Texture Sets:
            //         "filter" : {"dataPaths": ["01_Head", "02_Body"]}
            //
            //     Filter that matches some outputMaps:
            //         "filter" : {"outputMaps": ["$textureSet_color"]}
            //
            //     Filter that matches nothing:
            //         "filter" : {"dataPaths": []}
            //
            //     Use of a combined filter to match a Texture Set for some
            //     outputMaps:
            //         "filter" : {"dataPaths": ["01_Head"],
            //     "outputMaps" : ["$textureSet_color"]}
            "filter": {
                // List of rootPaths to match.
                //
                // This can be a mix of:
                // - Texture Set names only, even for Texture Sets with stacks
                // - Stack names, when stacks are used
                "dataPaths": [
                    "01_Head",
                    "02_Body/Mask"
                ],
                // List of map names to match.
                //
                // The map names are to be used as defined in "exportPresets.maps.fileName",
                // including wildcards.
                "outputMaps": [
                    "$textureSet_color"
                ],
                // List of UV Tiles to match, as an array of tile coordinates.
                // A tile coordinate is a 2 dimensional array of U and V coordinates.
                // (e.g. [[1, 1], [1, 2]] to export tiles U=1, V=1 and U=1, V=2)
                "uvTiles": [
                    [
                        1,
                        1
                    ]
                ]
            },
            // (optional) Parameters to apply to the matched texture files as per the
            // current rule.
            //
            // When "parameters" is not provided, the existing parameters are used.
            // When "parameters" is provided, it overrides the existing parameters.
            //
            // Each individual parameter is optional and, when defined, overrides
            // previously defined parameters (coming from the selected preset).
            //
            // It is important to understand that even though this section is
            // optional, if after evaluating all the rules some parameters remain
            // undefined, the configuration is invalid.
            //
            // In this example, we're setting a different texture size for the color
            // map of both 01_Head and 02_Body/Mask, leaving settings on maps and
            // other data paths, and leaving the other parameters untouched.
            "parameters": {
                "sizeLog2": 11
            }
        }
    ]
}
```

## Events

Exporting textures, whether initiated through the Python API or in the UI, can trigger the following events. See `substance_painter.event` for more details.

### ExportTexturesAboutToStart

Event triggered just before a textures export.

**Parameters:**
- `textures` (Dict[Tuple[str, str], List[str]]): List of texture files to be written to disk, grouped by stack (Texture Set name, stack name).

### ExportTexturesEnded

Event triggered after textures export is finished.

**Parameters:**
- `status` (ExportStatus): Status code.
- `message` (str): Human readable status message.
- `textures` (Dict[Tuple[str, str], List[str]]): List of texture files written to disk, grouped by stack (Texture Set name, stack name).

## Export Mesh

### scene_is_triangulated()

Check if the scene has only triangles (polygons with only 3 sides).

**Returns:**
- `bool`: True if the current scene has only triangles, False otherwise.

**Raises:**
- `ProjectError`: If no project is opened.

### scene_has_tessellation()

Check if the scene has displacement/tessellation enabled.

**Returns:**
- `bool`: True if the current scene has displacement/tessellation, False otherwise.

**Raises:**
- `ProjectError`: If no project is opened.

### MeshExportOption

Options available for the mesh export.

**Members:**

| Name | Description |
|------|-------------|
| `BaseMesh` | Export without displacement/tesselation. |
| `TriangulatedMesh` | Export without displacement/tesselation and apply triangulation. Triangulation converts all mesh polygons with more than 3 sides to triangles (but doesn't change the triangular ones). Only available if the mesh contains such polygons. |
| `TessellationNormalsBaseMesh` | Export with displacement/tessellation. Only available if displacement or tessellation has been used in the shaders. |
| `TessellationRecomputeNormals` | Export with displacement/tessellation and recompute vertex normals. Only available if displacement or tessellation has been used in the shaders. |

**Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### MeshExportResult

Result of the export mesh process.

**Parameters:**
- `status` (ExportStatus): Status code.
- `message` (str): Human readable status message.

### export_mesh(file_path, option)

Export the current mesh to the given file path.

**Parameters:**
- `file_path` (string): The complete file path where to export the mesh. The file format is deduced from the extension. Supported extensions are: `.usd`, `.obj`, `.fbx`, `.dae`, `.ply`, `.gltf`.
- `option` (MeshExportOption): The export option to use.

**Returns:**
- `MeshExportResult`: Result of the export process.

**Raises:**
- `ProjectError`: If no project is opened.
- `ValueError`: If `file_path` or `option` are invalid in the context of the current project. Contains a human readable message detailing the problem.

**Example:**

```python
import substance_painter.export

# Open a project we want to export from (see substance_painter.project
# for details). This step is not necessary if there is already a project
# opened in Substance 3D Painter.
import substance_painter.project
substance_painter.project.open("C:/projects/MeetMat.spp")

# Choose an export option to use
export_option = substance_painter.export.MeshExportOption.BaseMesh
if not substance_painter.export.scene_is_triangulated():
    export_option = substance_painter.export.MeshExportOption.TriangulatedMesh
if substance_painter.export.scene_has_tessellation():
    export_option = substance_painter.export.MeshExportOption.TessellationNormalsBaseMesh

# Actual export mesh operation:
filename = "C:/projects/MeetMat.obj"
export_result = substance_painter.export.export_mesh(filename, export_option)

# In case of error, display a human readable message:
if export_result.status != substance_painter.export.ExportStatus.Success:
    print(export_result.message)
```

**See also:** `substance_painter.project`, [Export documentation](https://www.adobe.com/go/painter-export)
