# logging module

This module exposes several functions to output messages to the Substance Painter logger. Depending on the severity of the message, use `info()`, `warning()` or `error()`.

For a finer control over the logging parameters, namely severity and channel, use `log()`. The functions `info()`, `warning()` and `error()` will output to the 'Python' log channel, while `log()` allows to specify a different channel.

Messages with severity levels `INFO`, `WARNING` and `ERROR` are meant for the end user, and will appear in the log window of Substance 3D Painter. Messages with severity levels `DBG_INFO`, `DBG_WARNING` and `DBG_ERROR` are meant for the developer, and will appear in the log file.

## Example

```python
import substance_painter.logging

# Simple log functions:
substance_painter.logging.info("Everyone knows that 2 + 2 is {0}.".format(2+2))
substance_painter.logging.warning("Maybe the user should look at this.")
substance_painter.logging.error("Letting the user know that something went wrong.")

# Log function with more options:
substance_painter.logging.log(
    substance_painter.logging.INFO,
    "Python",
    "An informative log message to the 'Python' channel.")

substance_painter.logging.log(
    substance_painter.logging.ERROR,
    "MyPlugin",
    "An error log message to the 'MyPlugin' channel.")
```

## Functions

### error()

`substance_painter.logging.error(message: str)`

Logs a message with level `ERROR` on the Substance 3D Painter logger.

**Parameters:**
- **message** (str) – The error message to log.

### info()

`substance_painter.logging.info(message: str)`

Logs a message with level `INFO` on the Substance 3D Painter logger.

**Parameters:**
- **message** (str) – The message to log.

### log()

`substance_painter.logging.log(severity, channel: str, message: str)`

Logs a message with level `severity` on the Substance 3D Painter logger.

**Parameters:**
- **severity** – the severity level, can be `INFO`, `WARNING` or `ERROR` for messages relevant to the end user, or `DBG_INFO`, `DBG_WARNING` or `DBG_ERROR` for messages relevant to the developer.
- **channel** (str) – the channel to log into. This can be any name allowing to identify the origin of the message, for example the name of your plugin.
- **message** (str) – the message to log.

### warning()

`substance_painter.logging.warning(message: str)`

Logs a message with level `WARNING` on the Substance 3D Painter logger.

**Parameters:**
- **message** (str) – The warning message to log.