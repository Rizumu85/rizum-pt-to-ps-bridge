# resource module

This module allows to manipulate *Substance 3D Painter* resources and shelves.

*Substance 3D Painter* treats textures, materials, brushes, etc. as resources, and uses URLs to identify them. Resources can be in the shelf, or can be embedded directly in a project (like a baked ambient occlusion texture for example).

## Classes

### Type

**class substance_painter.resource.Type(value)**

Enumeration describing the type of a given resource.

**Members:**

| Name | Usage |
|------|-------|
| `ABR_PACKAGE` | A photoshop brushes package. |
| `BRUSH` | A brush. |
| `EXPORT` | An export preset. |
| `FONT` | A text font. |
| `IMAGE` | An image. |
| `PRESET` | A resource preset. |
| `RESOURCE` | A resource. |
| `SCRIPT` | A particle emitter script. |
| `SHADER` | A shader. |
| `SMART_MASK` | A smart mask. |
| `SMART_MATERIAL` | A smart material. |
| `SUBSTANCE` | A substance. |
| `SUBSTANCE_PACKAGE` | A substance package. |
| `VECTORIAL` | A vectorial image. |

### UpdateProjectError

**class substance_painter.resource.UpdateProjectError(old_resource_id, new_resource_id, details)**

Error that occurred during the `replace_project_resources()` operation.

**Parameters:**
- **old_id** – The identifier of the resource that could not be updated.
- **new_id** – The identifier of the resource that was supposed to replace the old one.
- **details** (List[str]) – A list of errors messages.

## Overview

### Manipulating resources

The resource module exposes the class `Resource`, which represents a resource currently available in *Substance 3D Painter* (either in the current project, current session, or in a shelf).

Listing all the resources of a shelf can be done with `Shelf.resources()`, while `search()` allows to search for specific resources. Specific resources can be shown with a filter directly in the Assets window with `Resource.show_in_ui()` and `show_resources_in_ui()`.

```python
import substance_painter.resource

# Get all the resources of a shelf:
my_shelf = substance_painter.resource.Shelf("myshelf")
all_shelf_resources = my_shelf.resources()

for resource in all_shelf_resources:
    print(resource.identifier().name)

# Find all resources that match a name:
aluminium_resources = substance_painter.resource.search("aluminium")

for resource in aluminium_resources:
    print(resource.identifier().name)

# Show a single resource in the shelf:
aluminium_resources[0].show_in_ui()

# Show the list of resources found in the shelf:
substance_painter.resource.show_resources_in_ui(aluminium_resources)
```

### Importing resources

New resources can be imported, either to the current project with `import_project_resource()`, to the current session with `import_session_resource()`, or to a shelf with `Shelf.import_resource()`.

All three functions take a path to the resource to be imported, a `Usage` indicating the type of that resource, and optionally a name and a group.

```python
import substance_painter.resource

# Open a project we want to import into
import substance_painter.project
substance_painter.project.open("C:/projects/MeetMat.spp")

# Import a normal map to the project:
new_resource = substance_painter.resource.import_project_resource(
    "C:/textures/MyBakedNormalMap.png",
    substance_painter.resource.Usage.TEXTURE)

# Import a color LUT to the session:
new_color_lut = substance_painter.resource.import_session_resource(
    "C:/textures/sepia.exr",
    substance_painter.resource.Usage.COLOR_LUT)

# Import an environment map to the shelf.
my_shelf = substance_painter.resource.Shelf("myshelf")
if my_shelf.can_import_resources():
    new_resource = my_shelf.import_resource(
        "C:/textures/Bonifacio Street.exr",
        substance_painter.resource.Usage.ENVIRONMENT)
else:
    print("The shelf is read-only.")
```

### Resource crawling

When *Substance 3D Painter* is opened, it will browse the different shelves to discover and index resources, and display their thumbnail. When it regains focus after switching to another application, it will do so again, in case the user added a new asset to their shelf folder. This process is referred to as **resource crawling**.

It is possible from a Python script to explicitly trigger a new resource crawling with `Shelves.refresh_all()`.

### Resource reloading

Once a resource has been imported in a shelf, in the session or in the project, modifying the imported file has no effect because *Substance 3D Painter* keeps a copy of the file to be able to work with it.

By reloading a resource, the original file is imported again and the resource gets updated in the shelf, session or project.

### Resources used by a project

#### Update outdated resources in a project

It is possible to list the outdated resources of a project with `list_project_outdated_resources()`, and to update them with `replace_project_resources()`.

#### Replace resources in a project

It is possible to list the resources used by in a project with `list_project_resources()`, and to replace them with `replace_project_resources()`.

### Custom preview

When a resource is imported, a thumbnail is automatically generated for it. It is possible to replace that thumbnail with a custom preview by using `Resource.set_custom_preview()`, or reset the preview with `Resource.reset_preview()`.

## Resources

### Resource

**class substance_painter.resource.Resource(handle)**

A *Substance 3D Painter* resource.

#### Methods

**identifier()** → ResourceID
Get this resource identifier.

**location()** → ResourceLocation
Get the location of this Resource.

**retrieve(identifier)** [static]
Retrieve a list of resources matching the given identifier.

**set_custom_preview(preview_image)**
Replace the current preview of this resource with a custom image.

**category()** → str
Get the category of this resource, ex: "wood" for a material.

**usages()** → List[Usage]
Get the usages of this resource.

**gui_name()** → str
Get the GUI name of this resource.

**type()** → Type
Get the type of this resource.

**tags()** → List[str]
Get the tags of this resource.

**show_in_ui()**
Highlight this resource in the application shelf UI (Assets window).

### ResourceID

**class substance_painter.resource.ResourceID(context, name, version=None)**

A *Substance 3D Painter* resource identifier.

The resource is identified by a context, a name, and a version. The context and the name are mandatory while the version is optional.

#### Class Methods

**from_project(name, version=None)**
Create a ResourceID object for a resource located in the current project.

**from_session(name, version=None)**
Create a ResourceID object for a resource located in the current session.

**from_url(url)**
Create a ResourceID object from its URL.

#### Methods

**location()** → ResourceLocation
Get the location of this ResourceID.

**url()** → str
Get the URL form of this ResourceID.

#### Attributes

**context: str**
Context of the resource.

**name: str**
Name of the resource.

**version: str**
Hash identifying the version of the resource.

### ResourceLocation

**class substance_painter.resource.ResourceLocation(value)**

Each resource has a location determined by where its data lives.

**Members:**

| Name | Data location |
|------|---------------|
| `SESSION` | Current session; those ressources will be lost after a restart of the application. |
| `PROJECT` | A Substance 3D Painter project; those resources are embedded in the spp file. |
| `SHELF` | One of the Substance 3D Painter Shelves. |

### Usage

**class substance_painter.resource.Usage(value)**

Enumeration describing how a given resource is meant to be used.

**Members:**

| Name | Usage |
|------|-------|
| `ALPHA` | A brush alpha. |
| `BASE_MATERIAL` | A material. |
| `BRUSH` | A brush definition. |
| `COLOR_LUT` | A color look-up table. |
| `EMITTER` | A particle emitter script. |
| `ENVIRONMENT` | An environment map. |
| `EXPORT` | An export preset. |
| `FILTER` | A layer stack filter. |
| `FONT` | A text font. |
| `GENERATOR` | A mask generator. |
| `PARTICLE` | A particles effect. |
| `PROCEDURAL` | A procedural substance, like a noise. |
| `RECEIVER` | A particle receiver script. |
| `SHADER` | A shader. |
| `SMART_MASK` | A smart mask. |
| `SMART_MATERIAL` | A smart material. |
| `TEXTURE` | A UV space map like bakes. |
| `TOOL` | A painting tool preset. |

## Functions

### search(query)

List Substance 3D Painter resources that match the given query.

**Parameters:**
- **query** (str) – A resource query string.

**Returns:** The list of resources that match the given query.

### list_project_resources()

List the resources used in the current project. Project resources are all the resources used in the project (in the layerstack, shaders, environment map, etc.).

**Returns:** The list of resource identifiers.

### list_project_outdated_resources()

List the resources used in the current project that are outdated.

**Returns:** A dictionary with the old resources identifier as key and the new resources identifier as value.

### replace_project_resources(ids, allow_parameters_mismatch=False)

Replace resources in the current project.

**Parameters:**
- **ids** – A dictionary of resource identifiers to update (key: old, value: new).
- **allow_parameters_mismatch** (bool, optional) – By default (False), prevents resources with parameters from updating if parameters have been renamed or removed.

### import_project_resource(file_path, resource_usage, name=None, group=None)

Import a resource into the current opened project.

### import_session_resource(file_path, resource_usage, name=None, group=None)

Import a resource into the current session.

### show_resources_in_ui(resources)

Highlight a list of resources in the application shelf UI (Assets window).

### is_reload_modified_resources_running()

Check if a reload modified resources operation is currently running.

### reload_modified_resources_async(resource_filter)

Triggers a reload of the modified resources found using the given filter.

## Shelves

### Shelf

**class substance_painter.resource.Shelf(_name)**

Class providing information on a given *Substance 3D Painter* shelf. A shelf is identified by a unique name.

#### Methods

**can_import_resources()** → bool
Check if resources can be imported into this shelf.

**import_resource(file_path, resource_usage, name=None, group=None, uuid=None)**
Import a resource into this shelf.

**is_crawling()** → bool
Check if this shelf is currently discovering resources in folders.

**name()** → str
The shelf name.

**path()** → str
The associated path.

**refresh()**
Forces discovering of resources in shelf folders.

**resources(query='')** → List[Resource]
Get resources contained in this shelf.

### Shelves

**class substance_painter.resource.Shelves**

Collection of static methods to manipulate shelves.

#### Static Methods

**add(name, path)** → Shelf
Add a new shelf.

**all()** → List[Shelf]
List all shelves.

**application_shelf()** → Shelf
This is the shelf containing the default content shipped with the application.

**exists(name)** → bool
Tell whether a shelf with the given name exists.

**refresh_all()**
Forces discovering of resources in all shelves folders.

**remove(name)**
Removes a shelf.

**user_shelf()** → Shelf
This is the shelf located in the user Documents folder where new resources are created by default.

## Reload Filters

### AllResourcesFilter

**class substance_painter.resource.AllResourcesFilter**

Filter used to reload all modified resources known to Substance 3D Painter.

### ProjectFilter

**class substance_painter.resource.ProjectFilter**

Filter used to reload modified resources contained in the project context.

### ResourcesListFilter

**class substance_painter.resource.ResourcesListFilter(resources)**

Filter used to reload modified resources amongst a given list of resources.

### ResourcesUsedByProjectFilter

**class substance_painter.resource.ResourcesUsedByProjectFilter**

Filter used to reload modified resources currently in use by the project.

### SessionFilter

**class substance_painter.resource.SessionFilter**

Filter used to reload modified resources contained in the session.

### ShelvesListFilter

**class substance_painter.resource.ShelvesListFilter(shelves)**

Filter used to reload modified resources contained in designated shelves.