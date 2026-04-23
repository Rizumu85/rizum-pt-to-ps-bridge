# Event Module

The `event` module defines application events and allows to subscribe to notifications.

## Event

**class substance_painter.event.Event**

Base event class.

## Event Dispatcher

**substance_painter.event.DISPATCHER**

The event dispatcher instance that will be used by the application.

**class substance_painter.event.Dispatcher**

The Event Dispatcher.

### Methods

**connect(event_cls, callback)**

Connect a callback to handle the given event type.

The callback is stored as a weak reference, it is automatically disconnected once the callback gets garbage collected.

**Parameters:**
- `event_cls` (Type[Event]): An event class
- `callback` (Callable[[Event], Any]): A method or a bound method that will be called when an instance of the given event class is triggered

**connect_strong(event_cls, callback)**

Connect a callback to handle the given event type.

The callback is stored as a strong reference, it is never automatically disconnected.

**Parameters:**
- `event_cls` (Type[Event]): An event class
- `callback` (Callable[[Event], Any]): A method or a bound method that will be called when an instance of the given event class is triggered

**disconnect(event_cls, callback)**

Disconnect a previously connected callback.

**Parameters:**
- `event_cls` (Type[Event]): An event class
- `callback` (Callable[[Event], Any]): A method or a bound method that has been connected to the given event class

## Export Events

**class substance_painter.event.ExportTexturesAboutToStart(textures)**

Event triggered just before a textures export.

**Parameters:**
- `textures` (Dict[Tuple[str, str], List[str]]): List of texture files to be written to disk, grouped by stack (Texture Set name, stack name)

**class substance_painter.event.ExportTexturesEnded(status, message, textures)**

Event triggered after textures export is finished.

**Parameters:**
- `status` (ExportStatus): Status code
- `message` (str): Human readable status message
- `textures` (Dict[Tuple[str, str], List[str]]): List of texture files written to disk, grouped by stack (Texture Set name, stack name)

## Project Events

> **Note:** Project loading is done asynchronously. When the event `ProjectOpened` or `ProjectCreated` is triggered, the project may still be loading. The event `ProjectEditionEntered` is triggered when the project is ready to work with.

**class substance_painter.event.ProjectOpened**

Event triggered when an existing project has been opened.

**class substance_painter.event.ProjectCreated**

Event triggered when a new project has been created.

**class substance_painter.event.ProjectAboutToClose**

Event triggered just before closing the current project.

**class substance_painter.event.ProjectClosed**

Event triggered just before closing the current project.

**class substance_painter.event.ProjectAboutToSave(file_path)**

Event triggered just before saving the current project.

**Parameters:**
- `file_path` (str): The destination file

**class substance_painter.event.ProjectSaved**

Event triggered once the current project is saved.

**class substance_painter.event.ProjectEditionEntered**

Event triggered when the project is fully loaded and ready to work with.

When edition is entered, it is for example possible to query/edit the project properties, to bake textures or do project export.

**class substance_painter.event.ProjectEditionLeft**

Event triggered when the current project can no longer be edited.

**class substance_painter.event.BusyStatusChanged(busy)**

Event triggered when Substance 3D Painter busy state changed.

**Parameters:**
- `busy` (bool): Whether Substance 3D Painter is busy now

**class substance_painter.event.TextureStateEvent(action, stack_id, tile_indices, channel_type, cache_key)**

Event triggered when a document texture is added, removed or updated.

**Parameters:**
- `action` (TextureStateEventAction): Performed action (add, remove, update)
- `stack_id` (int): The stack the texture belongs to, can be used to create a Stack instance
- `tile_indices` (Tuple[int, int]): The uv tile indices
- `channel_type` (ChannelType): The document channel type
- `cache_key` (int): The texture current cache key. Those cache keys are persistent across sessions

### Static Methods

**cache_key_invalidation_throttling_period()**

Get the minimum duration between two texture update events (for a given texture).

**Returns:** The minimum duration between two update events (timedelta)

**set_cache_key_invalidation_throttling_period(period)**

Set the minimum duration between two texture update events (for a given texture).

**Warning:** This setting is global and every work made in a callback associated to this event may greatly hurt the painting experience.

**Parameters:**
- `period` (timedelta): The minimum duration between two update events, can't be lower than 500ms

**Raises:** ValueError if period is below 500ms

**class substance_painter.event.TextureStateEventAction**

The TextureStateEvent possible actions.

**Members:** `ADD`, `UPDATE`, `REMOVE`

## Shelf Events

**class substance_painter.event.ShelfCrawlingStarted(shelf_name)**

Event triggered when a shelf starts reading the file system to discover new resources.

**Parameters:**
- `shelf_name` (str): Name of the shelf discovering resources

**class substance_painter.event.ShelfCrawlingEnded(shelf_name)**

Event triggered when a shelf has finished discovering new resources and loading their thumbnails.

**Parameters:**
- `shelf_name` (str): Name of the shelf that has finished discovering resources

## Baking Events

**class substance_painter.event.BakingProcessAboutToStart(stop_source)**

Event triggered when a baking is about to start.

**Parameters:**
- `stop_source` (StopSource): The baking stop source, can be compared with the StopSource returned from the baking launch methods to identify the baking process

**class substance_painter.event.BakingProcessProgress(progress)**

Event triggered when baking process progress changes.

**Parameters:**
- `progress` (float): The baking progress, between [0.0, 1.0]

**class substance_painter.event.BakingProcessEnded(status)**

Event triggered after baking is finished.

**Parameters:**
- `status` (BakingStatus): Status of the baking process

## Layer Stack Events

**class substance_painter.event.LayerStacksModelDataChanged**

Event triggered whenever the status of the Layer Stacks changes.

### Example Usage

```python
import substance_painter as sp

# Define a callback function that will be called
# when the LayerStacksModelDataChanged event is triggered
def on_layerstack_changed(event: sp.event.LayerStacksModelDataChanged):
    stack = sp.textureset.get_active_stack()
    # Get the list of selected nodes
    selection = sp.layerstack.get_selected_nodes(stack)
    # Print the selection
    print(selection)

# Connect to the LayerStacksModelDataChanged event
sp.event.DISPATCHER.connect(sp.event.LayerStacksModelDataChanged, on_layerstack_changed)
# After this, each event in the layerstack will trigger the callback

# Later, it is possible to disconnect the event
# sp.event.DISPATCHER.disconnect(sp.event.LayerStacksModelDataChanged, on_layerstack_changed)
```

## Application Wide Events

**class substance_painter.event.EngineComputationsStatusChanged(engine_computations_enabled)**

Event triggered whenever the status of the engine computations changes.

**Parameters:**
- `engine_computations_enabled` (bool)

## Display Events

**class substance_painter.event.CameraPropertiesChanged(camera_id)**

Event triggered when the camera properties change.

**Parameters:**
- `camera_id` (int)

## Resources Related Events

**class substance_painter.event.ReloadResourcesStarted(filter)**

Event triggered when a resource reload operation has started.

**Parameters:**
- `filter`: The filter object used to choose the resources that are being reloaded

**class substance_painter.event.ReloadResourcesEnded(filter, reloaded_resources, resource_errors)**

Event triggered when a resource reload operation has completed.

**Parameters:**
- `filter`: The filter object used to choose which resources to reload
- `reloaded_resources` (List[ReloadedResourceResult]): The list of resources that were successfully reloaded
- `resource_errors` (List[ReloadedResourceError]): The list of resources that could not be reloaded, along with the corresponding reason

**class substance_painter.event.ReloadedResourceResult(old_resource_id, new_resource_id)**

Per resource result of a successful resource reload operation.

**Parameters:**
- `old_resource_id` (ResourceID): The ResourceID of the resource that was asked to be reloaded
- `new_resource_id` (ResourceID): The ResourceID of the newly added resource

**class substance_painter.event.ReloadedResourceError(resource_id, error_msg)**

Per resource result of an unsuccessful resource reload operation.

**Parameters:**
- `resource_id` (ResourceID): The ResourceID of the resource that was asked to be reloaded
- `error_msg` (str): The error message detailing what prevented the resource from being reloaded
