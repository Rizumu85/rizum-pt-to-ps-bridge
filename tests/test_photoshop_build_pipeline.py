import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = (
    PROJECT_ROOT / "sp_plugin" / "rizum_sp_to_ps" / "photoshop_build.jsx"
)


class PhotoshopBuildPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = BUILD_SCRIPT.read_text(encoding="utf-8")

    def test_pngs_are_placed_without_temporary_photoshop_documents(self):
        self.assertIn('executeAction(charIDToTypeID("Plc ")', self.source)
        self.assertNotIn("app.open(file)", self.source)
        self.assertNotIn("placed.id", self.source)
        self.assertNotIn("layer.id", self.source)
        self.assertNotIn("defaultLayer.remove()", self.source)
        self.assertNotIn("var anchor", self.source)
        self.assertIn(
            "placed.move(parent, ElementPlacement.PLACEATBEGINNING)", self.source
        )
        self.assertEqual(self.source.count("rasterizeAllLayers()"), 1)

    def test_placeholder_cleanup_accepts_a_host_consumed_layer(self):
        helper = self.source[
            self.source.index("function removeBuildPlaceholder") :
            self.source.index("function savePsd")
        ]
        self.assertIn("candidate.remove()", helper)
        self.assertNotIn("placeholder layer was not found", helper)
        self.assertTrue(helper.rstrip().endswith("}"))
        self.assertGreaterEqual(helper.count("state.placeholderRemoved = true"), 2)
        self.assertNotIn('executeAction(charIDToTypeID("Dlt ")', self.source)

    def test_all_documents_import_before_the_save_phase(self):
        import_complete = self.source.index("result.timings.import_ms")
        save_loop = self.source.index("for (var saveIndex")
        self.assertLess(import_complete, save_loop)

    def test_result_records_import_and_save_timings(self):
        writer = self.source[self.source.index("function writeResult") :]
        self.assertIn('"\\\"import_ms\\\":"', writer)
        self.assertIn('"\\\"save_ms\\\":"', writer)
        self.assertIn('"\\\"total_ms\\\":"', writer)

    def test_optional_uv_map_is_imported_after_the_layer_tree(self):
        builder = self.source[
            self.source.index("function buildRequest") :
            self.source.index("function placeNodes")
        ]
        self.assertIn("request.uv_map_asset", builder)
        self.assertIn('"Imported UV Map"', builder)
        self.assertLess(builder.index("placeNodes("), builder.index("placePngLayer("))
        self.assertLess(builder.index("placePngLayer("), builder.index("rasterizeAllLayers()"))


if __name__ == "__main__":
    unittest.main()
