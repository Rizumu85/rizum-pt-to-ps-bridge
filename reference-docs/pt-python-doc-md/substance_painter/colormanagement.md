# colormanagement module

Allows to manipulate colors and resources with color management.

This module exposes the `Color` class which allows to express color with proper color management. This `Color` object is used by the different interfaces of the layerstack API such as Fills and Uniform sources.

**See also:** [Colormanagement documentation](https://helpx.adobe.com/substance-3d-painter/features/color-management.html).

## Example

```python
import substance_painter as sp

# Open a project using legacy color management

# Get the currently displayed stack
stack = sp.textureset.get_active_stack()

# Define a color (web standard dark orange #ff8c00)
dark_orange_sRGB = sp.colormanagement.Color(
    # r, g, b components in floating point format
    1.0, 0.54902, 0.0,
    # Specify r,g,b values are encoded in sRGB
    sp.colormanagement.GenericColorSpace.sRGB)

dark_orange_linear = sp.colormanagement.Color(
    # r, g, b components in floating point format
    1.0, 0.26225, 0.0,
    # Specify r,g,b values are encoded in working space (Linear sRGB in legacy mode)
    sp.colormanagement.GenericColorSpace.Working)

# Here print the internal data of the colors. They should match what have been set above.
print('Internal color data:')
print(f'  dark_orange_sRGB: {dark_orange_sRGB.value_raw}, {dark_orange_sRGB.color_space}')
print(f'  dark_orange_linear: {dark_orange_linear.value_raw}, {dark_orange_linear.color_space}')

def _pretty_str(value):
    return f'({value[0]:.5f}, {value[1]:.5f}, {value[2]:.5f})'

# Here use the Color object interface to access data encoded in working space.
# values should be equivalent to dark_orange_linear.value_raw
print('Linear color data:')
print(f'  dark_orange_sRGB.working: {_pretty_str(dark_orange_sRGB.working)}')
print(f'  dark_orange_sRGB.convert(working): {_pretty_str(dark_orange_sRGB.convert(sp.colormanagement.GenericColorSpace.Working))}')
print(f'  dark_orange_linear.working: {_pretty_str(dark_orange_linear.working)}')
print(f'  dark_orange_linear.value_raw: {_pretty_str(dark_orange_linear.value_raw)}')

# Here use the Color object interface to access data encoded in sRGB space.
# values should be equivalent to dark_orange_sRGB.value_raw
print('sRGB color data:')
print(f'  dark_orange_sRGB.sRGB: {_pretty_str(dark_orange_sRGB.sRGB)}')
print(f'  dark_orange_linear.sRGB: {_pretty_str(dark_orange_linear.sRGB)}')
print(f'  dark_orange_linear.convert(sRGB): {_pretty_str(dark_orange_linear.convert(sp.colormanagement.GenericColorSpace.sRGB))}')
print(f'  dark_orange_sRGB.value_raw: {_pretty_str(dark_orange_sRGB.value_raw)}')

def _insert_fill_with_uniform_basecolor(color):
    position = sp.layerstack.InsertPosition.from_textureset_stack(stack)
    fill = sp.layerstack.insert_fill(position)
    fill.set_source(sp.textureset.ChannelType.BaseColor, color)
    return fill

# Insert two fill layers with both colors above
fill_sRGB = _insert_fill_with_uniform_basecolor(dark_orange_sRGB)
fill_linear = _insert_fill_with_uniform_basecolor(dark_orange_linear)

# At this point you should have 2 fill layers inside your stack that look exactly the
# same with the same color visually.

# Additionaly, if you are not confortable with color spaces, you can create a Color object
# without specifying any color space. In this case the color space will be
# deduced depending on the context where this color is used (sRGB on color managed
# channels such as BaseColor, raw otherwise).

# sRGB is the most common color space used for computer screens, this is why many color pickers
# will give you sRGB data. sRGB is also the standard color space for the web, so a lot of color
# data you can get from the web will be sRGB encoded.
# This is why we assume sRGB for color managed channels.

# Since we need the context to deduce the color space, you can't use any methods that
# would do explicit color space conversion. Instead we exposed another flexible property.
# See the example below:

# Define a color (web standard dark orange #ff8c00)
dark_orange_no_colorspace = sp.colormanagement.Color(
    # r, g, b components in floating point format
    1.0, 0.54902, 0.0)

# Print assumed sRGB data and compare with the colors defined above with proper color space
print('sRGB color data for color with undefined color space:')
print(f'  dark_orange_no_colorspace: {dark_orange_no_colorspace.value_raw}, {dark_orange_no_colorspace.color_space}')
print(f'  dark_orange_no_colorspace.value: {_pretty_str(dark_orange_no_colorspace.value)}')
print(f'  dark_orange_sRGB.sRGB: {_pretty_str(dark_orange_sRGB.sRGB)}')
print(f'  dark_orange_linear.sRGB: {_pretty_str(dark_orange_linear.sRGB)}')
# The calls below would raise due to the lack of color space.
# print(f'  dark_orange_no_colorspace.sRGB: {_pretty_str(dark_orange_no_colorspace.sRGB)}')
# print(f'  dark_orange_no_colorspace.working: {_pretty_str(dark_orange_no_colorspace.working)}')
# print(f'  dark_orange_no_colorspace.convert(working): {_pretty_str(dark_orange_no_colorspace.convert(sp.colormanagement.GenericColorSpace.Working))}')

# Insert a fill layer with the color with undefined color space
fill_no_colorspace = _insert_fill_with_uniform_basecolor(dark_orange_no_colorspace)

# At this point you should have 3 fill layers inside your stack that look exactly the
# same with the same color visually.

# Select the Fill layer
sp.layerstack.set_selected_nodes([fill_sRGB, fill_linear, fill_no_colorspace])
```

## Color Class

### `substance_painter.colormanagement.Color`

Describe a color (with a color space).

If you are not confortable with color spaces, you can create a color without specifying the colorspace of the data. In this case the color space will be deduced depending on the context where this color is used (`GenericColorSpace.sRGB` when used on a color managed channel, `GenericColorSpace.Raw` otherwise).

On color managed channel, we assume sRGB because it is the most common color space used for computer screens, this is why many color pickers will give you sRGB data. sRGB is also the standard color space for the web, so a lot of color data you can get from the web will be sRGB encoded.

*A color object returned by the different accessor of our API will always have a defined colorspace.*

**Variables:**
- `value_raw`: raw r,g,b data encoded in `color_space`.
- `color_space`: Color space in which `value_raw` is encoded. If None, will be deduced depending on the context where this color is used (`GenericColorSpace.sRGB` when used on a color managed channel, `GenericColorSpace.Raw` otherwise).

**Parameters:**
- `r` (float): Red component
- `g` (float): Green component  
- `b` (float): Blue component
- `color_space` (GenericColorSpace | str): Color space in which the data are encoded. If not specified, it will be deduced depending on the context where the color is used (`GenericColorSpace.sRGB` when used on a color managed channel, `GenericColorSpace.Raw` otherwise) (default: None).

#### Methods

##### `convert(color_space: GenericColorSpace | str) → Tuple[float, float, float]`

Get r,g,b values encoded in the given color space

**Parameters:**
- `color_space` (GenericColorSpace | str): Color space in which you want the data encoded to.

**Returns:** 
- Tuple[float, float, float]: r,g,b data encoded in the given color space

**Raises:**
- `RuntimeError`: if `Color.color_space` is None

#### Properties

##### `value: Tuple[float, float, float]`

color value

**Getter:** Returns the color encoded in sRGB if `Color.color_space` is defined and not `GenericColorSpace.Raw`, otherwise return `Color.value_raw`.

##### `sRGB: Tuple[float, float, float]`

color value in sRGB space

**Getter:** Returns the color value encoded in sRGB
**Setter:** Set the color value as sRGB encoded value

**Raises:** RuntimeError: if `Color.color_space` is None

##### `working: Tuple[float, float, float]`

color value in working space

**Getter:** Returns the color value encoded in working space  
**Setter:** Set the color value as working space encoded value

**Raises:** RuntimeError: if `Color.color_space` is None

## ColorSpace Enums

Following enums describe the different predefined colorspaces supported by Substance Painter.

Also note that on top of these enums, if you are using OCIO or ACE colormanagement engine in your project, you can also specify plain `strings` with the name of colorspaces available in your configuration.

`GenericColorSpace` and plain `strings` can be used to describe how r,g,b data are encoded in `Color` or when calling the `convert()` function to specify in which colorspace you want the data converted to.

All these enums and plain `strings` can be used to access or override `SourceBitmap` color spaces.

### `substance_painter.colormanagement.GenericColorSpace`

Generic color spaces valid with any color space engine used.

Can be used for `Color.color_space` or resources.

**Members:**

| Name | Description |
|------|-------------|
| `sRGB` | sRGB color space (IEC 61966-2-1:1999 in legacy mode) |
| `Working` | working space used in the current project (Linear sRGB in legacy mode). |
| `Raw` | Raw (no color space conversion). |

**Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### `substance_painter.colormanagement.LegacyColorSpace`

Legacy color spaces.

Don't use them to override your resource's color spaces, use `GenericColorSpace.Working` or `GenericColorSpace.sRGB` instead.

Can be used for resources only. Can't be used for `Color.color_space`.

**Members:**

| Name | Description |
|------|-------------|
| `Linear` | Linear sRGB color space. |
| `sRGB` | sRGB color space (IEC 61966-2-1:1999). |

**Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### `substance_painter.colormanagement.DataColorSpace`

Data color spaces.

Color spaces used for not color managed channels such as metallic or height.

Can be used for resources only. Can't be used for `Color.color_space`.

**Members:**

| Name | Description |
|------|-------------|
| `Data` | Data values, unsigned normalized or float. |
| `DataSigned` | Signed -1..1 data values stored as 0..1 normalized values. |

**Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).

### `substance_painter.colormanagement.NormalColorSpace`

Normal color spaces.

Color spaces used for normal channels to specify how to interpret normal data.

Can be used for resources only. Can't be used for `Color.color_space`.

**Members:**

| Name | Description |
|------|-------------|
| `NormalXYZRight` | Normal map in OpenGL format. |
| `NormalXYZLeft` | Normal map in Direct3D format. |

**Note:** The name used to define members is available as a string via the `.name` attribute (see [python enum.Enum](https://docs.python.org/3/library/enum.html#enum.Enum)).