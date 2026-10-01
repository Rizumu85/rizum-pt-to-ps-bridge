import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from sp_plugin.rizum_sp_to_ps.photoshop_automation import write_photoshop_backdrop_launcher

HOST = Path(__file__).parent / "fixtures" / "photoshop_backdrop_host.cjs"
# Top first, as Photoshop lists layers.
DOCUMENT = [
    ["Pass", "group", "PASSTHROUGH", [["Pass top", "layer"], ["Pass bottom", "layer"]]],
    ["Iso", "group", "MULTIPLY", [["Iso top", "layer"], ["Iso bottom", "layer"]]],
    ["Base", "layer"],
]


class PhotoshopBackdropTests(unittest.TestCase):
    def read(self, *points):
        """What the saved backdrop of each point shows: visible layers with their folders."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = root / "photoshop_backdrop.json"
            request.write_text(json.dumps({
                "request_type": "photoshop_backdrop_request",
                "document": {"path": str(root / "document.psd")},
                "points": [
                    {"key": str(index), "target_layer_id": None, "target_index_path": path,
                     "target_name": name, "insertion": insertion}
                    for index, (path, name, insertion) in enumerate(points)
                ],
            }), encoding="utf-8")
            launch = write_photoshop_backdrop_launcher(request)
            completed = subprocess.run(
                ["node", str(HOST), str(launch.launcher_path), str(request)],
                capture_output=True, text=True, encoding="utf-8",
                env={**os.environ, "FAKE_DOCUMENT": json.dumps(DOCUMENT)},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            host = json.loads(completed.stdout)
            # The mapped PSD is read, never changed, and no duplicate stays open.
            self.assertEqual(host, {"untouched": True, "open": 1})
            result = json.loads(launch.result_path.read_text(encoding="utf-8"))
            self.assertTrue(result["success"], result["errors"])
            return [json.loads(Path(item["png"]).read_text(encoding="utf-8")) for item in result["backdrops"]]

    def test_the_backdrop_is_everything_below_the_insertion_place(self):
        before_base, after_base, before_pass_bottom = self.read(
            ([2], "Base", "before"), ([2], "Base", "after"), ([0, 1], "Pass bottom", "before"),
        )
        self.assertEqual(before_base, ["Base"])
        self.assertEqual(after_base, [])
        # A Pass Through folder hides nothing of what is below it.
        self.assertEqual(before_pass_bottom, [
            "Pass bottom < Pass:PASSTHROUGH:100:mask",
            "Iso top < Iso:MULTIPLY:100:mask", "Iso bottom < Iso:MULTIPLY:100:mask", "Base",
        ])

    def test_inside_an_isolated_folder_only_its_own_content_counts(self):
        before_iso_bottom, inside_iso = self.read(([1, 1], "Iso bottom", "before"), ([1], "Iso", "inside"))
        # Photoshop blends the insert against the folder's content alone, so
        # the folder is read as a plain Normal folder with nothing around it.
        self.assertEqual(before_iso_bottom, ["Iso bottom < Iso:NORMAL:100:nomask"])
        self.assertEqual(inside_iso, [])


if __name__ == "__main__":
    unittest.main()
