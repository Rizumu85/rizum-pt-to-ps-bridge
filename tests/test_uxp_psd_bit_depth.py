import tempfile
import unittest
from pathlib import Path

from sp_plugin.rizum_sp_to_ps.exporter import build_request_from_preview


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SOURCE = PROJECT_ROOT / "ps_plugin" / "src" / "build-psd.js"


def _preview(bit_depth):
    return {
        "texture_set": "M_body",
        "stack": "",
        "channel": "BaseColor",
        "channel_role": "color",
        "channel_format": f"sRGB{bit_depth}",
        "bit_depth": bit_depth,
        "is_color": True,
        "uv_tile": {
            "is_udim": False,
            "resolution": {"width": 32, "height": 32},
        },
        "layers": [],
    }


class BuildRequestPsdBitDepthTests(unittest.TestCase):
    def test_texture_set_depth_becomes_the_psd_depth(self):
        with tempfile.TemporaryDirectory() as directory:
            request = build_request_from_preview(
                _preview(16), Path(directory) / "bundle"
            )

        self.assertEqual(request["export_settings"]["bit_depth"], 16)

    def test_explicit_depth_overrides_the_texture_set_depth(self):
        with tempfile.TemporaryDirectory() as directory:
            request = build_request_from_preview(
                _preview(16), Path(directory) / "bundle", {"bit_depth": 8}
            )

        self.assertEqual(request["export_settings"]["bit_depth"], 8)


class UxpPsdBitDepthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = BUILD_SOURCE.read_text(encoding="utf-8")

    def test_document_create_options_use_the_resolved_export_depth(self):
        self.assertIn("const psdBitDepth = resolvePsdBitDepth(request)", self.source)
        self.assertIn("depth: psdBitDepth", self.source)
        self.assertIn(
            "verifyDocumentBitDepth(document, psdBitDepth, constants)",
            self.source,
        )

    def test_only_png_compatible_psd_depths_are_accepted(self):
        self.assertIn("bitDepth !== 8 && bitDepth !== 16", self.source)
        self.assertIn("constants.BitsPerChannelType.SIXTEEN", self.source)
        self.assertIn("constants.BitsPerChannelType.EIGHT", self.source)


if __name__ == "__main__":
    unittest.main()
