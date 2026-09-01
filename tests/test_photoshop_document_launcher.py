import json
import tempfile
import unittest
from pathlib import Path

from sp_plugin.rizum_sp_to_ps.photoshop_automation import (
    write_photoshop_document_launcher,
)


class PhotoshopDocumentLauncherTests(unittest.TestCase):
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

    def test_rejects_non_photoshop_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "image.png"
            source.write_bytes(b"png")

            with self.assertRaises(ValueError):
                write_photoshop_document_launcher(source, Path(directory) / "out")


if __name__ == "__main__":
    unittest.main()
