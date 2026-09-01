import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from sp_plugin.rizum_sp_to_ps import exporter


class DesktopNodeExportTests(unittest.TestCase):
    def test_group_mapping_renders_one_visual_object_through_export_pipeline(self):
        preview = {
            "texture_set": "M_body",
            "stack": "",
            "channel": "BaseColor",
            "udim": 1001,
            "layers": [
                {
                    "uid_hex": "2b",
                    "name": "Working",
                    "kind": "GroupLayer",
                    "children": [{"uid_hex": "2c", "name": "Child"}],
                    "content_effects": [{"uid_hex": "2d", "name": "Effect"}],
                    "mask_effects": [],
                }
            ],
        }
        captured = {}

        def build_request(item_preview, bundle, _settings):
            captured["node"] = deepcopy(item_preview["layers"][0])
            layer = deepcopy(item_preview["layers"][0])
            layer["asset"] = {"path": str(Path(bundle) / "png" / "layer.png")}
            layer["mask_asset"] = {"path": str(Path(bundle) / "png" / "mask.png")}
            return {"layers": [layer]}

        def export_assets(request, **_kwargs):
            Path(request["layers"][0]["asset"]["path"]).write_bytes(b"png")
            Path(request["layers"][0]["mask_asset"]["path"]).write_bytes(b"mask")

        closer = SimpleNamespace(close=lambda: None)
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            exporter, "_load_painter_modules", return_value={}
        ), mock.patch.object(
            exporter, "_iter_stack_records", return_value=[]
        ), mock.patch.object(
            exporter, "_build_export_requests", return_value=[preview]
        ), mock.patch.object(
            exporter, "build_request_from_preview", side_effect=build_request
        ), mock.patch.object(
            exporter, "export_request_assets", side_effect=export_assets
        ), mock.patch.object(
            exporter.stack_node_export, "StackNodeExporter", return_value=closer
        ), mock.patch.object(
            exporter.geometry_mask, "GeometryMaskBaker", return_value=closer
        ):
            result = exporter.export_desktop_nodes(
                directory,
                {"texture_set": "M_body", "stack": "", "channel": "BaseColor"},
                ["2b"],
                {"channels": ["Normal"]},
            )

        self.assertEqual(captured["node"]["bake_policy"], "bake")
        self.assertEqual(captured["node"]["children"], [])
        self.assertEqual(captured["node"]["content_effects"], [])
        self.assertEqual(result[0]["name"], "Working")
        self.assertTrue(result[0]["png"].endswith("layer.png"))
        self.assertTrue(result[0]["mask_png"].endswith("mask.png"))


if __name__ == "__main__":
    unittest.main()
