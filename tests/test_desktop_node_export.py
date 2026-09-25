import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from sp_plugin.rizum_sp_to_ps import exporter


class DesktopNodeExportTests(unittest.TestCase):
    def export(self, layer, render):
        """Run export_desktop_nodes on one preview layer; render(node, png_dir) writes assets."""
        preview = {
            "texture_set": "M_body",
            "stack": "",
            "channel": "BaseColor",
            "udim": 1001,
            "layers": [layer],
        }
        captured = {}

        def build_request(item_preview, bundle, _settings):
            captured["node"] = deepcopy(item_preview["layers"][0])
            node = deepcopy(item_preview["layers"][0])
            render(node, Path(bundle) / "png")
            return {"layers": [node]}

        def export_assets(request, **_kwargs):
            def write(node):
                for key in ("asset", "mask_asset"):
                    if node.get(key):
                        Path(node[key]["path"]).write_bytes(b"png")
                for child in node.get("children") or []:
                    write(child)
            write(request["layers"][0])

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
                [layer["uid_hex"]],
                {"channels": ["Normal"]},
            )
            return captured["node"], result

    def test_group_crosses_as_a_folder_of_its_layers(self):
        layer = {
            "uid_hex": "2b", "name": "Working", "kind": "GroupLayer", "bake_policy": "native",
            "ps_blend_mode": "PASSTHROUGH", "opacity": {"BaseColor": 1.0},
            "children": [
                {"uid_hex": "2c", "name": "Top", "ps_blend_mode": "MULTIPLY", "opacity": {"BaseColor": 0.5}},
                {"uid_hex": "2e", "name": "Bottom", "visible": False},
            ],
            "content_effects": [],
            "mask_effects": [],
        }

        def render(node, png):
            node["mask_asset"] = {"path": str(png / "group_mask.png")}
            for child in node["children"]:
                child["asset"] = {"path": str(png / f"{child['uid_hex']}.png")}

        node, result = self.export(layer, render)

        self.assertEqual(node["bake_policy"], "native")
        self.assertEqual([child["name"] for child in node["children"]], ["Top", "Bottom"])
        group = result[0]
        self.assertEqual(group["kind"], "group")
        self.assertIsNone(group["png"])
        self.assertTrue(group["mask_png"].endswith("group_mask.png"))
        top, bottom = group["children"]
        self.assertEqual((top["name"], top["kind"], top["blend_mode"], top["opacity"]), ("Top", "layer", "MULTIPLY", 50.0))
        self.assertTrue(top["png"].endswith("2c.png"))
        self.assertFalse(bottom["visible"])

    def test_single_layer_still_crosses_as_its_rendered_pixels(self):
        layer = {
            "uid_hex": "2c", "name": "Paint", "bake_policy": "hidden",
            "content_effects": [{"uid_hex": "2d", "name": "Effect"}], "mask_effects": [],
        }

        def render(node, png):
            node["asset"] = {"path": str(png / "layer.png")}

        node, result = self.export(layer, render)

        self.assertEqual(node["bake_policy"], "bake")
        self.assertEqual(node["content_effects"], [])
        self.assertEqual(result[0]["kind"], "layer")
        self.assertTrue(result[0]["png"].endswith("layer.png"))
        self.assertEqual(result[0]["children"], [])

    def test_group_with_nothing_to_render_is_refused(self):
        layer = {"uid_hex": "2b", "name": "Empty", "children": [{"uid_hex": "2c", "name": "Hidden"}]}
        with self.assertRaisesRegex(RuntimeError, "no visible pixels"):
            self.export(layer, lambda _node, _png: None)


if __name__ == "__main__":
    unittest.main()
