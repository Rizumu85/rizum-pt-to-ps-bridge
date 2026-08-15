import tempfile
import unittest
from pathlib import Path

from sp_plugin.rizum_sp_to_ps.exporter import build_request_from_preview


class UvMapExportTests(unittest.TestCase):
    def test_enabled_setting_adds_a_tile_specific_uv_map_asset(self):
        preview = {
            "texture_set": "M_body",
            "texture_set_original": "M_body",
            "stack": "",
            "channel": "BaseColor",
            "channel_label": "Base Color",
            "bit_depth": 8,
            "uv_tile": {
                "u": 0,
                "v": 0,
                "udim": 1001,
                "is_udim": False,
                "resolution": {"width": 64, "height": 32},
            },
            "layers": [],
        }

        with tempfile.TemporaryDirectory() as directory:
            request = build_request_from_preview(
                preview,
                Path(directory),
                {"export_uv_map": True},
            )

        asset = request["uv_map_asset"]
        self.assertEqual(asset["label"], "UV Map")
        self.assertEqual(asset["texture_set"], "M_body")
        self.assertEqual(asset["uv_tile"]["udim"], 1001)
        self.assertEqual(asset["resolution"], [64, 32])
        self.assertTrue(request["export_settings"]["export_uv_map"])


if __name__ == "__main__":
    unittest.main()
