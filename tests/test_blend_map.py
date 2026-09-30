import unittest
from types import SimpleNamespace

from sp_plugin.rizum_sp_to_ps.blend_map import (
    DIRECT_BLEND_MODES,
    map_blend_mode,
    photoshop_to_painter_blend_modes,
)

# Painter 12.1's layerstack.BlendingMode member names, as the host reports them.
PAINTER_MODE_NAMES = (
    "Normal", "Passthrough", "Disable", "Replace", "Multiply", "Divide",
    "InverseDivide", "Darken", "Lighten", "LinearDodge", "Subtract",
    "InverseSubtract", "Difference", "Exclusion", "SignedAddition", "Overlay",
    "Screen", "LinearBurn", "ColorBurn", "ColorDodge", "SoftLight", "HardLight",
    "VividLight", "LinearLight", "PinLight", "Tint", "Saturation", "Color", "Value",
)


class BlendMapTests(unittest.TestCase):
    def test_pass_through_groups_stay_folders(self):
        # Painter spells the enum member "Passthrough"; a mismatch bakes every
        # default-mode group flat.
        decision = map_blend_mode(SimpleNamespace(name="Passthrough"))
        self.assertEqual((decision["ps_blend_mode"], decision["bake_policy"]), ("PASSTHROUGH", "keep_editable"))

    def test_direct_modes_use_painter_member_names(self):
        self.assertEqual(set(DIRECT_BLEND_MODES) - set(PAINTER_MODE_NAMES), set())

    def test_photoshop_pass_through_imports_as_the_painter_member(self):
        self.assertEqual(photoshop_to_painter_blend_modes()["passthrough"], "Passthrough")


if __name__ == "__main__":
    unittest.main()
