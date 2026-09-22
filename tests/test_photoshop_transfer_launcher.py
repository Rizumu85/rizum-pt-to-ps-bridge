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


if __name__ == "__main__":
    unittest.main()
