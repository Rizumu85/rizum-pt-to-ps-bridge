# properties module

The `properties` module introduces the description of dynamic attributes.

## Property Class

### `substance_painter.properties.Property(handle: _substance_painter.data_tweak.PythonTweak)`

Read only access to a property data.

**Parameters:**
- `handle`: _substance_painter.data_tweak.PythonTweak

#### Methods

##### `value() → bool | int | Tuple[int, int] | Tuple[int, int, int] | Tuple[int, int, int, int] | float | Tuple[float, float] | Tuple[float, float, float] | Color | Tuple[Color, float] | Tuple[float, float, float, float] | str`

Get the current property value.

**Returns:**
- The current value (PropertyValue)

##### `name() → str`

Get the property name.

**Returns:**
- The property name (str)

##### `short_name() → str`

Get the shortened property name.

**Returns:**
- The property short name (str)

##### `label() → str`

Get the property label.

**Returns:**
- The property label (str)

##### `widget_type() → str`

Get the widget type that should be used to edit the property.

**Returns:**
- One of: 'Slider', 'Angle', 'Color', 'Togglebutton', 'Combobox', 'RandomSeed', 'File', 'FileList', 'LineEdit', 'Resource', 'TextEdit' (str)

##### `enum_values() → Dict[str, int]`

The possible enum values with corresponding text for 'Combobox' widget type.

**Returns:**
- Enum label to enum value dictionary (Dict[str, int])

##### `enum_value(enum_label: str) → int`

Get the enum value for the given enum label for 'Combobox' widget type.

**Parameters:**
- `enum_label` (str): A valid enum label

**Returns:**
- The enum value for the corresponding label (int)

##### `properties() → Dict[str, Any]`

Get a json object that describes all available meta properties of this property. For example: value range, editor step, possible values, tooltip, etc.

**Returns:**
- A json object (Dict[str, Any])
