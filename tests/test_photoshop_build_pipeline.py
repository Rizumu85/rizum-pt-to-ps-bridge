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

    def test_default_layer_is_deleted_without_a_stale_dom_handle(self):
        self.assertIn('reference.putName(charIDToTypeID("Lyr "), name)', self.source)
        self.assertIn('executeAction(charIDToTypeID("Dlt ")', self.source)
        self.assertIn("deleteLayerByName(document, placeholderName)", self.source)

    def test_all_documents_import_before_the_save_phase(self):
        import_complete = self.source.index("result.timings.import_ms")
        save_loop = self.source.index("for (var saveIndex")
        self.assertLess(import_complete, save_loop)

    def test_result_records_import_and_save_timings(self):
        writer = self.source[self.source.index("function writeResult") :]
        self.assertIn('"\\\"import_ms\\\":"', writer)
        self.assertIn('"\\\"save_ms\\\":"', writer)
        self.assertIn('"\\\"total_ms\\\":"', writer)


if __name__ == "__main__":
    unittest.main()
