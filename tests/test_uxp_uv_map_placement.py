import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UXP_BUILD_SCRIPT = PROJECT_ROOT / "ps_plugin" / "src" / "build-psd.js"


class UxpUvMapPlacementTests(unittest.TestCase):
    def test_uxp_builder_places_the_uv_map_after_painter_layers(self):
        source = UXP_BUILD_SCRIPT.read_text(encoding="utf-8")
        builder = source[
            source.index("async function createPsdSkeletonFromRequest") :
            source.index("async function placeTopLevelBuildItems")
        ]

        self.assertLess(
            builder.index("await placeTopLevelBuildItems"),
            builder.index("await placeUvMapLayer"),
        )
        self.assertIn("constants.ElementPlacement.PLACEBEFORE", builder)
        self.assertIn("build.uvMapPlaced = true", builder)


if __name__ == "__main__":
    unittest.main()
