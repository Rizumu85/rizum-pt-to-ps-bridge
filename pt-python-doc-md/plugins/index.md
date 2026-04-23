# Writing plugins

The Substance 3D Painter Python API allows users to write their own plugins, to do certain tasks. A Substance 3D Painter plugin is a standard Python module, placed in a path added to `substance_painter_plugins.path`.

Plugins can be loaded or unloaded with the `substance_painter_plugins` module.

## substance_painter_plugins module

### Functions

**`path`**
- Plugin search path configuration

**`plugins`**
- Currently loaded plugins

**`start_plugin()`**
- Start a plugin

**`close_plugin()`**
- Close a plugin

**`is_plugin_started()`**
- Check if a plugin is started

**`reload_plugin()`**
- Reload a plugin

**`startup_module_names()`**
- Get startup module names

**`plugin_module_names()`**
- Get plugin module names

**`load_startup_modules()`**
- Load startup modules

**`close_all_plugins()`**
- Close all plugins

**`update_sys_path()`**
- Update system path

## Examples of plugins

Here are some simple examples showing how to write a Substance 3D Painter plugin in Python:

### Hello Plugin
- Basic plugin example

### Versioning Plugin
- Plugin with versioning functionality