import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

from sp_plugin.rizum_sp_to_ps import ui  # noqa: E402
from sp_plugin.rizum_sp_to_ps.export_ui import ExportDialog  # noqa: E402
from sp_plugin.rizum_sp_to_ps.photoshop_automation import (  # noqa: E402
    find_photoshop_executable,
    write_photoshop_launcher,
)


class PhotoshopBuildJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.export_list = self.root / "_last_export.json"
        self.export_list.write_text("{}", encoding="utf-8")
        self.panel = ui.BridgePanel.__new__(ui.BridgePanel)
        self.panel.QtCore = QtCore
        self.panel.QtWidgets = QtWidgets
        self.panel.widget = QtWidgets.QWidget()
        self.panel._closing = False
        self.panel._build_job = None
        self.panel.user_settings = {}

    def tearDown(self):
        if self.panel._build_job is not None:
            self.panel._build_job.stop()
        self.panel.widget.deleteLater()
        self.directory.cleanup()

    def test_build_receipts_stay_out_of_the_export_folder(self):
        launch = write_photoshop_launcher(self.export_list, self.root / "_desktop_bridge" / "photoshop_build")
        script = launch.launcher_path.read_text(encoding="utf-8")

        self.assertEqual(launch.result_path.parent.name, "photoshop_build")
        self.assertIn(json.dumps(str(launch.progress_path)), script)
        self.assertIn(json.dumps(str(launch.result_path)), script)
        self.assertNotIn("__RIZUM_BUILD_", script)

    def test_configured_photoshop_wins_over_detection(self):
        configured = self.root / "Photoshop.exe"
        configured.write_bytes(b"")
        self.assertEqual(find_photoshop_executable(str(configured)), configured)

    def start(self, launched=(True, "")):
        self.panel.launch_photoshop = mock.Mock(return_value=launched)
        return self.panel.start_photoshop_build(self.export_list, self.root)

    def test_successful_build_is_quiet_and_cleans_its_receipts(self):
        self.assertEqual(self.start(), (True, ""))
        launch = self.panel._build_job.launch
        launch.progress_path.write_text('{"phase":"building"}', encoding="utf-8")
        launch.result_path.write_text('{"built":["a.psd"],"errors":[]}', encoding="utf-8")
        with mock.patch.object(ui, "show_modal_message") as modal:
            self.panel._build_job.poll()
        modal.assert_not_called()
        self.assertIsNone(self.panel._build_job)
        self.assertFalse(launch.result_path.exists())

    def test_script_that_never_starts_is_reported_in_painter(self):
        self.start()
        self.panel._build_job._started_at -= 121
        with mock.patch.object(ui, "show_modal_message") as modal:
            self.panel._build_job.poll()
        self.assertIn("did not start the script", modal.call_args.args[-1])

    def test_failed_launch_starts_no_job(self):
        self.assertEqual(self.start((False, "Photoshop was not found.")), (False, "Photoshop was not found."))
        self.assertIsNone(self.panel._build_job)

    def test_export_is_refused_before_writing_pngs_without_photoshop(self):
        panel = SimpleNamespace(
            QtCore=QtCore, QtGui=QtGui, QtWidgets=QtWidgets, widget=QtWidgets.QWidget(),
            user_settings={}, photoshop_executable=lambda: None,
            _run_export_selections=mock.Mock(),
            active_target_key=lambda: ("M_body", ""),
        )
        export = ExportDialog(panel)
        export.selected_exports = lambda: [({"texture_set": "M_body", "stack": ""}, ["BaseColor"])]
        with mock.patch("sp_plugin.rizum_sp_to_ps.export_ui.show_modal_message") as modal:
            export.export_checked()
        panel._run_export_selections.assert_not_called()
        self.assertIn("Photoshop was not found", modal.call_args.args[-1])
        panel.widget.deleteLater()


if __name__ == "__main__":
    unittest.main()
