# Changelog



## 0.3.5 (Substance 3D painter 11.1.0)

- **substance_painter.baking**
  - The `substance_painter.properties.Property` named `PerVertex` (boolean type) has been removed from the Curvature From Map baker. The new behavior is now always forced to `PerVertex = False` (or in the UI, the Per Fragment mode).
  - The two `substance_painter.properties.Property` named `TonemappingMin` and `TonemappingMax` (float type) have been removed in favor of a new `substance_painter.properties.Property` named `TonemappingBounds` (array of 2 float).

- **substance_painter.layerstack**
  - Add `substance_painter.layerstack.is_3d_projection_mode()` to query which projection mode is compatible with symmetry.
  - Add `substance_painter.layerstack.FillLayerNode.get_symmetry_parameters()` to get symmetry parameters on Fill layers.
  - Add `substance_painter.layerstack.FillEffectNode.get_symmetry_parameters()` to get symmetry parameters on Fill effects.
  - Add `substance_painter.layerstack.FillLayerNode.set_symmetry_parameters()` to set symmetry parameters on Fill layers.
  - Add `substance_painter.layerstack.FillEffectNode.set_symmetry_parameters()` to set symmetry parameters on Fill effects.

- **substance_painter.source**
  - Add member `log2_offset` in `substance_painter.source.ResolutionOverride` to configure scaling in Auto mode.
  - Add property `substance_painter.source.SourceSubstance.resolution` to edit resolution override of the substance.

## 0.3.4 (Substance 3D painter 11.0.0)

- **substance_painter.baking**
  - Add support for automatic cage feature in the baking parameters. The `Property` named `UseCage` (boolean type) has been removed in favor of a new `Property` named `CageMode` (enum type).

- **substance_painter.event**
  - Add a new event `ReloadResourcesStarted` to be notified when resource reloading starts.
  - Add a new event `ReloadResourcesEnded` to be notified when resource reloading ends.

- **substance_painter.layerstack**
  - Add `create_smart_material()` to save a smart material.
  - Add `create_smart_mask()` to save a smart mask.

- **substance_painter.resource**
  - Add `list_project_resources()`, `list_project_outdated_resources()` and `replace_project_resources()` to list and replace resources in the project.
  - Function `list_layer_stack_resources()` is now **deprecated**, use `list_project_resources()` instead.
  - Function `update_layer_stack_resource()` is now **deprecated**, use `replace_project_resources()` instead.
  - Add `is_reload_modified_resources_running()` to check if the resource reloading process is currently running.
  - Add `reload_modified_resources_async()` to trigger the resource reloading process.
  - Add `Shelf.refresh()` to refresh a particular shelf only.

- **substance_painter.textureset**
  - Add properties `TextureSet.name` and `TextureSet.description` to read/edit textureset's name and description.
  - Add properties `UVTile.name` and `UVTile.description` to read/edit uvtile's name and description.
  - Function `TextureSet.name()` is now **deprecated**, use property `TextureSet.name` instead.

- **substance_painter.source**
  - Add `ResolutionOverride` to configure resolution related parameters of a source vectorial or a source font.
  - Members `resolution_mode` and `resolution_value` in `SourceVectorialParams` are now **deprecated**, use `SourceVectorialParams.resolution` instead.
  - Members `resolution_mode` and `resolution_value` in `SourceFontParams` are now **deprecated**, use `SourceFontParams.resolution` instead.
  - Rename `VectorialResolutionMode` to `ResolutionMode`.
  - `VectorialResolutionMode` is now **deprecated** and an alias to `ResolutionMode`.

## 0.3.3 (Substance 3D painter 10.1.1)

- **substance_painter.resource**
  - Fix members order of enumeration `Usage`.
  - Fix members order and add VECTORIAL to enumeration `Type`.

## 0.3.2 (Substance 3D painter 10.1.0)

- **substance_painter.project**
  - Add `GltfSettings` to pass gltf specific options.
  - Add a member `mesh_settings` in `Settings` with type `GltfSettings` or `UsdSettings`.
  - Member `usd_settings` in `Settings` is now **deprecated**, use `mesh_settings` instead.
  - Add a member `mesh_settings` in `MeshReloadingSettings` with type `UsdSettings`.
  - Member `usd_settings` in `MeshReloadingSettings` is now **deprecated**, use `mesh_settings` instead.

## 0.3.1 (Substance 3D painter 10.0.1)

- **substance_painter.layerstack**
  - Fix `set_selection_type()` to allow properties selection of an instance parent layer.
  - Fix `FillLayerNode.set_source()`, `FillLayerNode.set_material_source()`, `FillEffectNode.set_source()` and `FillEffectNode.set_material_source()` to forbid creation of cycles with anchor points. It will now throw a `ValueError`.

- **substance_painter.source**
  - Fix `SourceSubstance.set_source()` to forbid creation of cycles with anchor points. It will now throw a `ValueError`.
  - Add `SourceBitmap.list_available_color_spaces()` to query available colorspaces for a bitmap.

## 0.3.0 (Substance 3D painter 10.0.0)

This version introduces new modules to be able to edit your project layerstack. With this new modules you will be able to navigate, access, edit, remove and add every type of layers and effects available in the UI of Substance Painter.

- **substance_painter.layerstack**
  - New module to manipulate the layer stack.

- **substance_painter.source**
  - New module to manipulate layer's sources.

- **substance_painter.colormanagement**
  - New module with colormanagement facilities for layerstack edition.

- **substance_painter.resource**
  - Add ability to get substance presets details using `Resource.internal_properties()` function.

- **substance_painter.export**
  - Add `PredefinedExportPreset` and `list_predefined_export_presets()` to retrieve predefined export presets and list their output maps.
  - Add `ResourceExportPreset` and `list_resource_export_presets()` to retrieve resource export presets (editable presets from shelves) and list their output maps.

## 0.2.12 (Substance 3D painter 9.1.1)

- **substance_painter.project**
  - Add `get_uuid()` to query the project UUID.

## 0.2.11 (Substance 3D painter 9.1.0)

- **substance_painter.application**
  - Add ability to disable engine computations
  - Add `close()` to close Substance 3D Painter.

- **substance_painter.display**
  - Add `Camera` to manipulate camera settings.

- **substance_painter.event**
  - Add a new event `EngineComputationsStatusChanged` to be notified when engine computations status changes.
  - Add a new event `CameraPropertiesChanged` to be notified when the properties of a camera change.

- **substance_painter.export**
  - Add ability to export the mesh of the current project.
  - Add ability to get the default export path used for exporting textures.

- **substance_painter.project**
  - Add `BoundingBox` and `get_scene_bounding_box()` to query dimensions of the scene.

## 0.2.10 (Substance 3D painter 9.0.0)

- **substance_painter.export**
  - Fix textures exported in EXR with 32f bit depth were incorrectly saved in 16f.

- **substance_painter.project**
  - Add `UsdSettings` in `Settings` to support USD parameters for project creation.
  - Add `UsdSettings` in `MeshReloadingSettings` to support USD parameters for mesh reloading.

## 0.2.9 (Substance 3D Painter 8.3.1)

- **substance_painter.async_utils**
  - New module to expose primitives used in async computations.

- **substance_painter.event**
  - Add a new event `BakingProcessProgress` to be notified about baking process progress.
  - Add a new event `BakingProcessAboutToStart` to be notified of the start of a baking process.
  - Allow to configure throttling period for `TextureStateEvent`.

- **substance_painter.baking**
  - Add `bake_selected_textures_async()` to bake all selected texture set.
  - Fix `bake_async()` to take UV Tiles selection into account.
  - Now async functions return a `StopSource` to allow for cancellation.

## 0.2.8 (Substance 3D Painter 8.3.0)

- **substance_painter.application**
  - New module to expose functionalities on the application level.
  - Add `version_info()` to query Substance 3D Painter version as a tuple.
  - Add `version()` to query Substance 3D Painter version as a string.

- **substance_painter.event**
  - Add a new event `BakingProcessEnded` to be notified of the end of the baking process.

- **substance_painter.project**
  - Add `last_saved_substance_painter_version()` to query which Substance 3D Painter version was used to last save the project.

- **substance_painter.textureset**
  - Add `TextureSet.uv_tile()` to get a specific UV Tile.

- **substance_painter.ui**
  - Add Baking to `UIMode`.
  - Add `get_current_mode()` to query the current UI mode.
  - Add `switch_to_mode()` to switch to some UI mode.

This version introduces the modules:
- **substance_painter.baking**
- **substance_painter.properties**

## 0.2.7 (Substance 3D Painter 8.2.0)

- **substance_painter.resource**
  - Add new values to `Type` enumeration.
  - Add `Resource.children()` to query child resources of a resource.
  - Add `Resource.parent()` to query parent resource of a resource.

- **substance_painter.textureset**
  - Add `MeshMapUsage` to enumerate possible Mesh map usages.
  - Add `TextureSet.get_mesh_map_resource()` to query the resource set as some Mesh map usage.
  - Add `TextureSet.set_mesh_map_resource()` to replace the resource for some Mesh map usage.

- **substance_painter.ui**
  - Add `get_layout()` to save UI layout state.
  - Add `get_layout_mode()` to query the UI mode of a saved state.
  - Add `set_layout()` to restore a saved UI state.
  - Add `reset_layout()` to reset UI state to default.

- **substance_painter.event**
  - Add a new event `TextureStateEvent` to be notified of document textures edition.

## 0.2.6 (Substance 3D Painter 8.1.2)

- **substance_painter.project**
  - `create()` and `Settings` now supports using a custom unit scale for mesh size.

- **substance_painter.textureset**
  - Add `TextureSet.all_mesh_names()` to query the list of mesh names used in a Texture Set.
  - Add `UVTile.all_mesh_names()` to query the list of mesh names used in a UV Tile.

- **substance_painter.resource**
  - Add `Usage` enumeration to describe resource usages.
  - Add `Type` enumeration to describe resource types.
  - Add `Resource.category()` to query the category of a resource.
  - Add `Resource.usages()` to query the usages of a resource.
  - Add `Resource.gui_name()` to query the name of a resource.
  - Add `Resource.type()` to query the type of a resource.
  - Add `Resource.tags()` to query the tags of a resource.
  - Add `Resource.internal_properties()` to query a dictionary of a resource internal properties.

## 0.2.5 (Substance 3D Painter 8.1.0)

This version upgrades to Python 3.9.9.

- **substance_painter.project**
  - `create()` supports PAINTER_ACE_CONFIG environment variable, to setup the project color management mode.
  - `create()` now raise an error if OCIO or PAINTER_ACE_CONFIG environment variable is set to an invalid configuration.

## 0.2.4 (Substance 3D Painter 7.4.3)

This version exposes the tone mapping operator to the Python API, and adds a hook to execute code when Substance 3D Painter is not busy.

- **substance_painter.display**
  - Add `get_tone_mapping()` to query the project tone mapping.
  - Add `set_tone_mapping()` to set the project tone mapping.

- **substance_painter.project**
  - Add `execute_when_not_busy()` to execute code when Substance 3D Painter is no longer busy.

## 0.2.3 (Substance 3D Painter 7.4.0)

This version makes it possible to work with JavaScript from the Python API. It also allows creating projects with OCIO color management capabilities.

- **substance_painter.js**
  - Add `evaluate()` to evaluate some JavaScript code.

- **substance_painter.project**
  - `create()` supports OCIO environment variable, to setup the project color management mode.

## 0.2.2 (Substance 3D Painter 7.3.0)

This version adds functions to help with scripted project loading, project mesh reloading and UV Tiles manipulation. It also improves error handling in several modules.

- **substance_painter.display**
  - `set_color_lut_resource()` and `set_environment_resource()` throw a TypeError instead of a ValueError when an argument has a type different from expected.

- **substance_painter.event**
  - Add `Dispatcher.connect_strong()` to connect strong reference callbacks to the event dispatcher.

- **substance_painter.project**
  - Add `is_busy()` to query whether Substance 3D Painter is busy.
  - Project saving functions are disabled when Substance 3D Painter is busy.
  - Add `last_imported_mesh_path()` to query the path to the last imported mesh.
  - Add `reload_mesh()` to load a new mesh in the current opened project.
  - `create()` throws a TypeError instead of a ValueError when its settings argument has a type different from expected.

- **substance_painter.resource**
  - Add `show_resources_in_ui()` to highlight a list of resources in the application UI.
  - `update_layer_stack_resource()` throws a TypeError when an argument has a type different from expected.

- **substance_painter.textureset**
  - Add `UVTile` to interact with UV Tiles. Add ability to manipulate UV Tiles resolutions.
  - `TextureSet.from_name()` throws a TypeError instead of a ValueError when its argument has a type different from expected.

## 0.2.1 (Substance 3D Painter 7.2.1)

This version adds functions to list and update resources used by the layer stack.

- **substance_painter.resource**
  - Add `list_layer_stack_resources()` to list resources used by the layer stack and mesh maps.
  - Add `update_layer_stack_resource()` to update resources used by the layer stack and mesh maps.

## 0.2.0 (Substance 3D Painter 7.2.0)

- **substance_painter.resource**
  - Add `Resource.show_in_ui()` to highlight a resource in the UI.
  - Modify `Shelves.user_shelf()` to take user settings into account.

- **substance_painter.textureset**
  - Modify `ChannelType` to include the new available texture channels.

- **substance_painter.ui**
  - Add `add_plugins_toolbar_widget()` to add a widget to the plugins toolbar.

## 0.1.0 (Substance Painter 7.1.0)

This version adds several features to manage resources, shelves and UV Tiles.

- **substance_painter.event**
  - Add `ProjectEditionEntered` event.
  - Add `ProjectEditionLeft` event.
  - Add `ShelfCrawlingStarted` event.
  - Add `ShelfCrawlingEnded` event.

- **substance_painter.project**
  - Add `is_in_edition_state()`.

- **substance_painter.resource**
  - Add `Resource` to manipulate substance painter resources.
  - Add `search()` to search for available resources.
  - Add `Shelf`.
  - Add `Shelves` for shelves manipulation facilities.

- **substance_painter.textureset**
  - Add `TextureSet.all_uv_tiles()`.
  - Add `TextureSet.has_uv_tiles()`.
  - Add `UVTile`.

## 0.0.3 (Substance Painter 6.2.2)

- **substance_painter.export**
  - Document the use of existing export presets.
  - Add a module overview example.

- **substance_painter.textureset**
  - Add `Channel.type()`.
  - Add `Stack.all_channels()`.

## 0.0.2 (Substance Painter 6.2.0)

This version adapts the module `substance_painter.project` to the new UV Tile workflow.

- **substance_painter.project**
  - Add `ProjectWorkflow`.
  - Change the constructor of `Settings`.

## 0.0.1 (Substance Painter 6.1.0)

Initial version of the Substance Painter Python API.

It uses Python 3.7.6 and introduces the modules:
- `substance_painter`
- `substance_painter.display`
- `substance_painter.event`
- `substance_painter.exception`
- `substance_painter.export`
- `substance_painter.logging`
- `substance_painter.project`
- `substance_painter.resource`
- `substance_painter.textureset`
- `substance_painter.ui`
- `substance_painter_plugins`