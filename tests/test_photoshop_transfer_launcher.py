import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from sp_plugin.rizum_sp_to_ps.photoshop_automation import (
    write_photoshop_transfer_launcher,
)


class PhotoshopTransferLauncherTests(unittest.TestCase):
    def test_preparing_transfer_removes_stale_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "photoshop_transfer.json"
            request.write_text("{}", encoding="utf-8")
            launch = write_photoshop_transfer_launcher(request)
            launch.result_path.write_text('{"success":true}', encoding="utf-8")
            launch.progress_path.write_text('{"phase":"saving_document"}', encoding="utf-8")
            write_photoshop_transfer_launcher(request)
            self.assertFalse(launch.result_path.exists())
            self.assertFalse(launch.progress_path.exists())

    def test_fresh_host_returns_the_real_error_without_global_json(self):
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "photoshop_transfer.json"
            request.write_text("{}", encoding="utf-8")
            launch = write_photoshop_transfer_launcher(request)
            host = Path(__file__).parent / "fixtures" / "photoshop_document_host.cjs"
            completed = subprocess.run(
                ["node", str(host), str(launch.launcher_path)], capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            calls = json.loads(completed.stdout)
            result = json.loads((request.parent / "photoshop_transfer_result.json").read_text())
            self.assertIn("Expected a Painter-to-Photoshop", result["errors"][0]["message"])
            self.assertEqual(calls["globalJson"], "undefined")
            self.assertEqual(calls["dialogs"], "original")
            self.assertEqual(calls["rulerUnits"], "original")

    def test_launcher_embeds_request_path_and_keeps_runtime_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "photoshop_transfer.json"
            request.write_text("{}", encoding="utf-8")

            launch = write_photoshop_transfer_launcher(request)
            script = launch.launcher_path.read_text(encoding="utf-8")

            self.assertIn(str(request.resolve()).replace("\\", "\\\\"), script)
            self.assertNotIn("__RIZUM_TRANSFER_REQUEST_PATH__", script)
            self.assertIn('request_type !== "painter_to_photoshop_transfer"', script)
            self.assertIn("document.save();", script)


    def run_group_transfer(self, insertion, target_id, target_name):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            png = lambda name: str((root / f"{name}.png").resolve())
            for name in ("top", "deep", "bottom"):
                Path(png(name)).write_bytes(b"png")
            layer = lambda name, **fields: {
                "name": name, "kind": "layer", "png": png(name.lower()), "mask_png": None,
                "blend_mode": "NORMAL", "opacity": 100.0, "visible": True, "children": [], **fields,
            }
            request = root / "photoshop_transfer.json"
            request.write_text(json.dumps({
                "request_type": "painter_to_photoshop_transfer",
                "document": {"path": str(root / "document.psd")},
                "layers": [{
                    "order": 0, "name": "Working", "png": None, "mask_png": None,
                    "target_layer_id": target_id, "target_index_path": [], "target_name": target_name,
                    "target_kind": "layer", "insertion": insertion,
                    "blend_mode": "Passthrough", "opacity": 80.0, "visible": True,
                    "children": [
                        layer("Top", blend_mode="MULTIPLY", opacity=50.0),
                        {**layer("Sub"), "kind": "group", "png": None, "blend_mode": "PASSTHROUGH",
                         "children": [layer("Deep")]},
                        layer("Bottom", visible=False, blend_mode="DIVIDE"),
                    ],
                }],
            }), encoding="utf-8")
            launch = write_photoshop_transfer_launcher(request)
            host = Path(__file__).parent / "fixtures" / "photoshop_transfer_host.cjs"
            completed = subprocess.run(
                ["node", str(host), str(launch.launcher_path), str(request)],
                capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(launch.result_path.read_text(encoding="utf-8"))
            self.assertTrue(result["success"], result["errors"])
            self.last_result = result
            return json.loads(completed.stdout)

    @staticmethod
    def outline(layers):
        return [
            (item["name"], PhotoshopTransferLauncherTests.outline(item["layers"])) if "layers" in item else item["name"]
            for item in layers
        ]

    def test_mapped_painter_group_arrives_as_a_folder_of_its_layers(self):
        document = self.run_group_transfer("after", 3, "Base")

        self.assertTrue(document["saved"])
        self.assertEqual(self.outline(document["layers"]), [
            ("Group", ["Detail"]), "Base", ("Working", ["Top", ("Sub", ["Deep"]), "Bottom"]),
        ])
        working = document["layers"][2]
        self.assertEqual((working["blendMode"], working["opacity"]), ("PASSTHROUGH", 80.0))
        top, sub, bottom = working["layers"]
        self.assertEqual((top["blendMode"], top["opacity"], top["rasterized"]), ("MULTIPLY", 50.0, True))
        self.assertEqual(sub["blendMode"], "PASSTHROUGH")
        self.assertFalse(bottom["visible"])
        # A blend mode Photoshop refuses warns and keeps Normal; the folder still lands.
        self.assertEqual(bottom["blendMode"], "BlendMode.NORMAL")
        self.assertEqual(self.last_result["warnings"], ["Bottom: Photoshop refused blend mode DIVIDE here; Normal was kept."])

    def test_before_places_above_the_target_including_the_topmost_layer(self):
        document = self.run_group_transfer("before", 1, "Group")

        self.assertEqual([item["name"] for item in document["layers"]], ["Working", "Group", "Base"])

if __name__ == "__main__":
    unittest.main()
