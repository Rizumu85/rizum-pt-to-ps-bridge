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

    def test_document_color_policy_is_applied_before_any_png_is_placed(self):
        builder = self.source[
            self.source.index("function buildRequest") :
            self.source.index("function placeNodes")
        ]
        self.assertLess(
            builder.index("configureDocumentColorManagement"),
            builder.index("placeNodes("),
        )
        self.assertNotIn("convertProfile", self.source)
        self.assertIn("document.colorProfileType = ColorProfileType.NONE", self.source)
        self.assertIn("document.colorProfileName = expectedProfile", self.source)

    def test_psd_profile_embedding_follows_the_channel_policy(self):
        save_helper = self.source[
            self.source.index("function savePsd") :
            self.source.index("function validateRequest")
        ]
        self.assertIn("policy.embed_profile === true", save_helper)
        self.assertNotIn("options.embedColorProfile = true", save_helper)

    def test_build_request_requires_an_explicit_value_preserving_policy(self):
        validator = self.source[
            self.source.index("function validateRequest") :
            self.source.index("function buildRequestPaths")
        ]
        self.assertIn("validateColorManagement(request.color_management)", validator)
        self.assertIn("policy.preserve_rgb_numbers !== true", validator)

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

    def test_successful_build_removes_temporary_export_artifacts(self):
        finally_start = self.source.index("} finally {")
        finally_block = self.source[
            finally_start : self.source.index(
                "if (result.errors.length > 0) {\n        alert",
                finally_start,
            )
        ]
        cleanup = self.source[
            self.source.index("function cleanupSuccessfulExport") :
            self.source.index("function jsonQuote")
        ]

        self.assertIn("cleanupSuccessfulExport", finally_block)
        self.assertIn("removeFolderTree(bundle)", cleanup)
        self.assertIn("removeFileIfPresent(File(exportListPath))", cleanup)
        self.assertIn("removeFileIfPresent(File($.fileName))", cleanup)


if __name__ == "__main__":
    unittest.main()
