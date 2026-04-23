# Application Module

This module contains application wide functionalities.

## Functions

### `version_info()` → `Tuple[int, int, int]`

Get the version_info of Substance 3D Painter. Returns a tuple containing major, minor, patch.

**Returns:**
- The major, minor and patch version of Substance 3D Painter.

**Return type:** `Tuple[int, int, int]`

---

### `version()` → `str`

Get the version of Substance 3D Painter. Do not extract version information out of it, rather use `version_info()`.

**Returns:**
- Version of Substance 3D Painter.

**Return type:** `str`

---

### `engine_computations_status()` → `bool`

Check whether engine computations are enabled.

**Returns:**
- Whether engine computations are enabled.

**Return type:** `bool`

---

### `enable_engine_computations(enable: bool)`

Enable or disable engine computations.

**Parameters:**
- `enable` (bool)

---

### `disable_engine_computations()`

Context manager to disable engine computations.

Allows to regroup computation intensive tasks without triggering the engine so that textures are not computed or updated in the layer stack or the viewport.

This is equivalent to disabling and then reenabling the engine by calling `enable_engine_computations()`.

**Example:**
```python
import substance_painter.application as mapplication

with mapplication.disable_engine_computations():
    # Do some computation intensive tasks
    pass
```

---

### `close()`

Close Substance 3D Painter.

> **Warning:** Any unsaved data will be lost.

---

## Usage

```python
import substance_painter.application as application

# Get version information
version_tuple = application.version_info()  # Returns (major, minor, patch)
version_string = application.version()      # Returns version string

# Check engine status
is_enabled = application.engine_computations_status()

# Control engine computations
application.enable_engine_computations(True)   # Enable
application.enable_engine_computations(False)  # Disable

# Use context manager for temporary disabling
with application.disable_engine_computations():
    # Perform intensive operations without engine updates
    pass

# Close application (use with caution)
application.close()
```
