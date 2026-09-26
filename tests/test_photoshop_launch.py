import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from sp_plugin.rizum_sp_to_ps import ui
from sp_plugin.rizum_sp_to_ps.ui import BridgePanel


class PhotoshopLaunchTests(unittest.TestCase):
    def test_photoshop_starts_without_inheriting_painters_handles(self):
        # An inherited handle to the open .spp kept Painter from renaming it
        # on save, and Painter crashed.
        panel = BridgePanel.__new__(BridgePanel)
        panel.photoshop_executable = lambda: Path("C:/Adobe/Photoshop.exe")
        with mock.patch.object(ui.subprocess, "Popen") as popen:
            launched, message = panel.launch_photoshop("C:/export/_build_in_photoshop.jsx")
        self.assertTrue(launched, message)
        self.assertTrue(popen.call_args.kwargs["close_fds"])

    def test_a_launch_failure_is_reported(self):
        panel = BridgePanel.__new__(BridgePanel)
        panel.photoshop_executable = lambda: Path("C:/Adobe/Photoshop.exe")
        with mock.patch.object(ui.subprocess, "Popen", side_effect=OSError("denied")):
            launched, message = panel.launch_photoshop("C:/export/x.jsx")
        self.assertFalse(launched)
        self.assertIn("denied", message)


if __name__ == "__main__":
    unittest.main()
