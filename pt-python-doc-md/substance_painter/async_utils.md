# async_utils module

The `async_utils` module provide primitives used in async computations.

## StopSource

**Class:** `substance_painter.async_utils.StopSource(stop_source: _substance_painter.async_utils.StopSource)`

An object that can be used to cancel an asynchronous computation.

**Parameters:**
- `stop_source` (_substance_painter.async_utils.StopSource)

### Methods

#### request_stop()

Makes a stop request.

**Returns:**
- `bool` - True if the stop request was possible.

#### stop_requested()

Check if a stop request as been made.

**Returns:**
- `bool` - True if a stop request has been made.
