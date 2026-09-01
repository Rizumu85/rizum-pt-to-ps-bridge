import tempfile
import unittest
from pathlib import Path

from sp_plugin.rizum_sp_to_ps.photoshop_automation import (
    write_photoshop_transfer_launcher,
)


class PhotoshopTransferLauncherTests(unittest.TestCase):
    def test_launcher_embeds_request_path_and_keeps_runtime_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "photoshop_transfer.json"
            request.write_text("{}", encoding="utf-8")

            launcher = write_photoshop_transfer_launcher(request)
            script = launcher.read_text(encoding="utf-8")

            self.assertIn(str(request.resolve()).replace("\\", "\\\\"), script)
            self.assertNotIn("__RIZUM_TRANSFER_REQUEST_PATH__", script)
            self.assertIn('request_type !== "painter_to_photoshop_transfer"', script)
            self.assertIn("document.save();", script)


if __name__ == "__main__":
    unittest.main()
