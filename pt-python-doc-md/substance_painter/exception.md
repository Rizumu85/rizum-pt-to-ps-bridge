# Exception Module

This module declares *Substance 3D Painter* specific exceptions.

## Classes

### ProjectError

**Class:** `substance_painter.exception.ProjectError(value)`

Raised when an operation or function is incompatible with the current project, or when the current state of the project is invalid.

Trying to save a project when there is no project opened would raise a `ProjectError`.

**Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### ResourceNotFoundError

**Class:** `substance_painter.exception.ResourceNotFoundError(value)`

Raised when a Substance 3D Painter resource could not be found.

Providing an invalid resource ID would raise a `ResourceNotFoundError`.

**Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### ServiceNotFoundError

**Class:** `substance_painter.exception.ServiceNotFoundError(value)`

Raised when an operation or function relies on a service which could not be found. It could mean that the service has not been started yet.

Trying to execute a command while Substance 3D Painter is starting could raise `ServiceNotFoundError`.

**Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

## Usage Examples

```python
import substance_painter.exception as sp_exception

try:
    # Some operation that might fail
    substance_painter.project.save()
except sp_exception.ProjectError as e:
    print(f"Project error: {e}")

try:
    # Some operation with resources
    resource = substance_painter.resource.Resource.retrieve(invalid_id)
except sp_exception.ResourceNotFoundError as e:
    print(f"Resource not found: {e}")

try:
    # Some operation requiring services
    some_service_operation()
except sp_exception.ServiceNotFoundError as e:
    print(f"Service not available: {e}")
```

---

*Documentation for Substance 3D Painter Python API 0.3.4*