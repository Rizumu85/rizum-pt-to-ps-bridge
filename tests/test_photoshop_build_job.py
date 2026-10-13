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
from sp_plugin.rizum_sp_to_ps.photoshop_documents import SETTINGS_KEY, DocumentMemory  # noqa: E402
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
        launch = write_photoshop_launcher(self.export_list, self.root / "session" / "photoshop_build")
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
        # The receipts live in the session folder, not beside the export.
        with mock.patch.object(ui, "session_dir", return_value=self.root / "session"):
            return self.panel.start_photoshop_build(self.export_list)

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

    def export_two_channels(self):
        """An export list of a BaseColor and an Opacity PSD for M_veil; returns their paths."""
        psds = []
        requests = []
        for channel in ("BaseColor", "Opacity"):
            psd = self.root / f"Tex_Hero_M_veil_{channel}.psd"
            psd.write_bytes(b"psd")
            request = self.root / f"{channel}.json"
            request.write_text(json.dumps({
                "project": {"uuid": "project-1", "path": "hero.spp"},
                # Renamed in Painter; the link is kept under the material's own name.
                "texture_set": "Veil", "texture_set_original": "M_veil", "stack": "",
                "channel": channel, "psd_file": str(psd),
            }), encoding="utf-8")
            requests.append({"path": str(request)})
            psds.append(str(psd))
        self.export_list.write_text(json.dumps({"build_requests": requests}), encoding="utf-8")
        values = {}
        self.panel._document_store = lambda: SimpleNamespace(
            value=lambda key, default, _type: values.get(key, default),
            setValue=values.__setitem__, sync=lambda: None,
        )
        return psds, values

    def finish_build(self, built):
        launch = self.panel._build_job.launch
        # Photoshop deletes the requests with the working folder before it reports.
        for request in self.root.glob("*.json"):
            request.unlink()
        launch.progress_path.write_text('{"phase":"building"}', encoding="utf-8")
        launch.result_path.write_text(json.dumps({"built": built, "errors": []}), encoding="utf-8")
        self.panel._build_job.poll()

    def test_built_psds_become_the_documents_bridge_opens_for_their_texture_set(self):
        (base, opacity), values = self.export_two_channels()
        self.start()
        self.finish_build([base, opacity])

        memory = DocumentMemory(values[SETTINGS_KEY])
        self.assertEqual(memory.resolve("project-1", "M_veil", "", "BaseColor"), base)
        self.assertEqual(memory.resolve("project-1", "M_veil", "", "Opacity"), opacity)
        # The first PSD of the texture set also serves the channels that have none.
        self.assertEqual(memory.resolve("project-1", "M_veil", "", "Roughness"), base)

    def test_a_psd_photoshop_did_not_save_is_not_linked(self):
        (base, opacity), values = self.export_two_channels()
        self.start()
        self.finish_build([opacity])

        memory = DocumentMemory(values[SETTINGS_KEY])
        self.assertEqual(memory.resolve("project-1", "M_veil", "", "BaseColor"), opacity)
        self.assertNotIn(Path(base).name, values[SETTINGS_KEY])

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
