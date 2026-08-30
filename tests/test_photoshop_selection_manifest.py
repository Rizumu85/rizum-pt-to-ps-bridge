import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = PROJECT_ROOT / "ps_plugin" / "src" / "export-selected.js"


class PhotoshopSelectionManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = EXPORT_SCRIPT.read_text(encoding="utf-8")

    def test_manifest_is_written_after_photoshop_modal_work_finishes(self):
        modal_end = self.source.index('{ commandName: "Rizum export selected layers" }')
        manifest_write = self.source.index("writeSelectionManifest(folder, result)")

        self.assertLess(modal_end, manifest_write)

    def test_manifest_carries_stable_layer_and_asset_references(self):
        writer = self.source[
            self.source.index("async function writeSelectionManifest") :
            self.source.index("async function exportLayerPixels")
        ]

        self.assertIn('request_type: "photoshop_selection"', writer)
        self.assertIn("source_id: layer.source_id", writer)
        self.assertIn("painter_snapshot: sidecarPathForPsd", writer)
        self.assertIn("ps_layer_id: layer.ps_layer_id", writer)
        self.assertIn("png: layer.png", writer)
        self.assertIn("mask_png: layer.mask_png", writer)


if __name__ == "__main__":
    unittest.main()
