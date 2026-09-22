import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from sp_plugin.rizum_sp_to_ps.photoshop_automation import (
    write_photoshop_document_launcher,
)


class PhotoshopDocumentLauncherTests(unittest.TestCase):
    def run_script(self, launcher):
        host = Path(__file__).parent / "fixtures" / "photoshop_document_host.cjs"
        result = subprocess.run(
            ["node", str(host), str(launcher)], capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_launcher_embeds_request_and_declares_manifest_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = root / "external artwork.psd"
            document.write_bytes(b"8BPS")

            launch = write_photoshop_document_launcher(document, root / "bridge")
            request = json.loads(launch.request_path.read_text(encoding="utf-8"))
            script = launch.launcher_path.read_text(encoding="utf-8")

            self.assertEqual(request["request_type"], "photoshop_document_export")
            self.assertEqual(Path(request["psd_file"]), document.resolve())
            self.assertEqual(Path(request["manifest_file"]), launch.manifest_path)
            self.assertEqual(Path(request["result_file"]), launch.result_path)
            self.assertNotIn("__RIZUM_DOCUMENT_REQUEST_PATH__", script)
            self.assertIn('request_type !== "photoshop_document_export"', script)
            self.assertIn('request_type: "photoshop_selection"', script)
            self.assertIn("source.duplicate", script)
            self.assertNotIn("__RIZUM_JSON_RUNTIME__", script)

    def test_fresh_host_without_json_opens_psd_and_returns_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = root / "external \u753b\u7a3f.psd"
            document.write_bytes(b"8BPS")
            launch = write_photoshop_document_launcher(document, root / "bridge")
            calls = self.run_script(launch.launcher_path)
            result = json.loads(launch.result_path.read_text(encoding="utf-8"))
            manifest = json.loads(launch.manifest_path.read_text(encoding="utf-8"))
            progress = json.loads(launch.progress_path.read_text(encoding="utf-8"))
            self.assertEqual(calls["opened"], [str(document)])
            self.assertEqual(calls["globalJson"], "undefined")
            self.assertEqual(calls["dialogs"], "original")
            self.assertEqual(calls["closed"], [str(document) + ".duplicate"])
            self.assertNotIn(str(document), calls["saved"])
            self.assertTrue(result["success"])
            self.assertEqual(result["exported_count"], 3)
            self.assertEqual(manifest["layers"][1]["parent_id"], 1)
            self.assertTrue(all((launch.manifest_path.parent / row["png"]).is_file() for row in manifest["layers"]))
            self.assertEqual(progress["completed"], progress["total"])

    def test_invalid_request_still_publishes_failure_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = root / "external.psd"
            document.touch()
            launch = write_photoshop_document_launcher(document, root / "bridge")
            launch.request_path.write_text("not json", encoding="utf-8")
            calls = self.run_script(launch.launcher_path)
            result = json.loads(launch.result_path.read_text(encoding="utf-8"))
            self.assertFalse(result["success"])
            self.assertIn("JSON.parse", result["errors"][0]["error"])
            self.assertEqual(calls["opened"], [])
            self.assertEqual(calls["dialogs"], "original")

    def test_relaunch_removes_old_progress_and_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = root / "external.psd"
            document.touch()
            launch = write_photoshop_document_launcher(document, root / "bridge")
            self.run_script(launch.launcher_path)
            write_photoshop_document_launcher(document, root / "bridge")
            self.assertFalse(launch.result_path.exists())
            self.assertFalse(launch.manifest_path.exists())
            self.assertFalse(launch.progress_path.exists())

    def test_rejects_non_photoshop_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "image.png"
            source.write_bytes(b"png")

            with self.assertRaises(ValueError):
                write_photoshop_document_launcher(source, Path(directory) / "out")


if __name__ == "__main__":
    unittest.main()
