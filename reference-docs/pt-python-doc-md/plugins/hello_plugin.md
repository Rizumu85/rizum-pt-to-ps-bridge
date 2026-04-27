# Hello Plugin

The hello world of python scripting in Substance 3D Painter.

## hello_plugin.py

```python
"""The hello world of python scripting in Substance 3D Painter
"""

from PySide6 import QtWidgets
import substance_painter.ui

plugin_widgets = []
"""Keep track of added ui elements for cleanup"""

def start_plugin():
    """This method is called when the plugin is started."""
    # Create a simple text widget
    hello_widget = QtWidgets.QTextEdit()
    hello_widget.setText("Hello from python scripting!")
    hello_widget.setReadOnly(True)
    hello_widget.setWindowTitle("Hello Plugin")
    # Add this widget as a dock to the interface
    substance_painter.ui.add_dock_widget(hello_widget)
    # Store added widget for proper cleanup when stopping the plugin
    plugin_widgets.append(hello_widget)

def close_plugin():
    """This method is called when the plugin is stopped."""
    # We need to remove all added widgets from the UI.
    for widget in plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)
    plugin_widgets.clear()

if __name__ == "__main__":
    start_plugin()
```

## Overview

This is a simple example plugin that demonstrates the basic structure of a Substance 3D Painter Python plugin. The plugin creates a simple text widget and adds it to the Painter interface as a dock widget.

### Key Components

1. **Plugin State Management**: The `plugin_widgets` list keeps track of UI elements for proper cleanup
2. **start_plugin()**: Called when the plugin is activated - creates and adds UI elements
3. **close_plugin()**: Called when the plugin is deactivated - removes UI elements and cleans up
4. **UI Integration**: Uses `substance_painter.ui` module to add dock widgets to the interface

### Plugin Lifecycle

- When started, the plugin creates a read-only text widget displaying "Hello from python scripting!"
- The widget is added as a dock to the Substance 3D Painter interface
- When stopped, all UI elements are properly removed and cleaned up

This example serves as a foundation for more complex plugins and demonstrates the essential plugin structure required for Substance 3D Painter.