# Layerstack Module

The `layerstack` module allows to manipulate the layer stack of Substance 3D Painter.

This module exposes the corresponding `Node` and `LayerNode` classes. They allow to discover and manipulate layer stack structure and effects, retrieve and set information of their state and settings.

To manipulate the layerstack, a project must be opened and must be in edition state.

`get_root_layer_nodes()` is the entry point to start querying some layer stack.

## Overview

- [Layerstack navigation](#layerstack-navigation)
- [Layerstack edition](#layerstack-edition)  
- [Layerstack selection](#layerstack-selection)
- [Layers and effects](#layers-and-effects)

### Layerstack Navigation

Functions and classes for navigating the layer stack structure:

- `get_root_layer_nodes()` - Get root layer nodes
- `get_node_by_uid()` - Get node by UID
- `Node` - Base node class
- `LayerNode` - Layer node class
- `HierarchicalNode` - Hierarchical node class
- `EffectNode` - Effect node class

#### Enums

- `NodeType` - Node type enumeration
- `MaskBackground` - Mask background enumeration
- `BlendingMode` - Blending mode enumeration
- `GeometryMaskType` - Geometry mask type enumeration

### Layerstack Edition

Functions and classes for editing the layer stack:

- `InsertPosition` - Position for insertion
- `ScopedModification` - Scoped modification context
- `NodeStack` - Node stack management
- `delete_node()` - Delete a node

### Layerstack Selection

Functions for managing layer stack selection:

- `get_selected_nodes()` - Get currently selected nodes
- `get_selection_type()` - Get selection type
- `set_selected_nodes()` - Set selected nodes
- `set_selection_type()` - Set selection type
- `SelectionType` - Selection type enumeration

### Layers and Effects

Specific layer and effect types:

#### Paint Layer and Effect
- Paint layer manipulation functions and classes

#### Fill Layer and Effect  
- Fill layer manipulation functions and classes
- Parameters and enums for fill layers

#### Generator Effect
- Generator effect functions and classes

#### Filter Effect
- Filter effect functions and classes

#### Levels Effect
- Levels effect functions and classes
- Level parameters

#### Compare Mask Effect
- Compare mask effect functions and classes
- Compare mask parameters

#### Color Selection Effect
- Color selection effect functions and classes
- Color selection parameters

#### Group Layer
- Group layer functions and classes

#### Instance Layer
- Instance layer functions and classes

#### Anchor Point
- Anchor point functions and classes

#### Smart Mask
- Smart mask functions and classes

#### Smart Material
- Smart material functions and classes

## See Also

[Layerstack documentation](https://helpx.adobe.com/substance-3d-painter/interface/layer-stack.html)