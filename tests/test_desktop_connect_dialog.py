import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PySide6 import QtCore, QtWidgets

from sp_plugin.rizum_sp_to_ps.desktop_bridge import DesktopBridgeController
from sp_plugin.rizum_sp_to_ps.desktop_transfer import TransferResult
from sp_plugin.rizum_sp_to_ps.photoshop_automation import write_photoshop_transfer_launcher


class DesktopConnectDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings = QtCore.QSettings(
            str(Path(self.directory.name) / "settings.ini"), QtCore.QSettings.Format.IniFormat
        )
        self.widget = QtWidgets.QWidget()
        self.panel = SimpleNamespace(
            QtCore=SimpleNamespace(QSettings=lambda *_: self.settings, QTimer=QtCore.QTimer, Qt=QtCore.Qt, QProcess=QtCore.QProcess),
            QtWidgets=QtWidgets, widget=self.widget,
            dock_bridge_button=QtWidgets.QPushButton(self.widget),
            user_settings={}, launch_photoshop=Mock(return_value=(True, "")),
        )
        self.controller = DesktopBridgeController(self.panel, Mock())
        self.controller._launch_desktop = Mock()
        # Connections start from an open mapper, which stays open for the reply.
        self.process = Mock()
        self.controller._process = self.process

    def tearDown(self):
        if not self.controller._closing:
            self.controller.close()
        self.widget.close()
        self.widget.deleteLater()
        self.app.processEvents()
        self.directory.cleanup()

    def replies(self):
        return [json.loads(call.args[0].decode("utf-8")) for call in self.process.write.call_args_list]

    def choose(self, path, during=None):
        def picker(*_args):
            if during:
                during()
            return (str(path) if path else "", "")
        with patch.object(QtWidgets.QFileDialog, "getOpenFileName", side_effect=picker) as dialog:
            self.controller._connect_photoshop()
        return dialog

    def test_picker_uses_the_system_dialog_filtered_to_photoshop_documents(self):
        dialog = self.choose(None)
        args = dialog.call_args.args
        self.assertEqual(args[1], "Connect Photoshop Document")
        self.assertEqual(args[3], "Photoshop Document (*.psd *.psb)")

    def test_accepting_a_psd_connects_the_open_mapper_without_photoshop(self):
        source = Path(self.directory.name) / "external.psd"
        source.touch()
        self.choose(source)
        self.assertEqual(self.replies(), [{"type": "photoshop_connected", "psd": str(source)}])
        self.panel.launch_photoshop.assert_not_called()
        self.assertEqual(self.controller._recent_photoshop_document(), source)
        self.assertTrue(self.settings.value("photoshop_document_dir", "", str).endswith(Path(self.directory.name).name))

    def test_remembered_psd_that_moved_opens_bridge_disconnected(self):
        source = Path(self.directory.name) / "external.psd"
        source.touch()
        self.choose(source)
        source.unlink()
        self.assertIsNone(self.controller._recent_photoshop_document())

    def test_cancel_replies_to_open_mapper(self):
        self.choose(None, during=lambda: self.assertFalse(self.panel.dock_bridge_button.isEnabled()))
        self.assertEqual(self.replies(), [{"type": "photoshop_connect_cancelled"}])
        self.controller._launch_desktop.assert_not_called()

    def test_mapper_closed_while_picking_ignores_the_answer(self):
        source = Path(self.directory.name) / "external.psd"
        source.touch()
        self.choose(source, during=self.controller._take_process)
        self.assertEqual(self.replies(), [])
        self.assertTrue(self.panel.dock_bridge_button.isEnabled())
        self.assertIsNone(self.controller._recent_photoshop_document())

    def begin_transfer(self):
        # Apply is terminal for the mapper; Painter continues without it.
        self.controller._process = None
        request = Path(self.directory.name) / "photoshop_transfer.json"
        request.write_text("{}", encoding="utf-8")
        launch = write_photoshop_transfer_launcher(request)
        transfer = TransferResult(2, 3, (), (), launch)
        self.controller._start_photoshop_job(launch, "Insert 3 layers", transfer)
        return launch

    def poll(self):
        if self.controller._photoshop_job is not None:
            self.controller._photoshop_job.poll()

    def failure_message(self):
        args = self.controller._show_message_callback.call_args.args
        self.assertEqual(args[-2], "Bridge transfer incomplete")
        return args[-1]

    def test_pending_job_has_visible_nonmodal_progress_and_blocks_duplicates(self):
        self.begin_transfer()
        progress = self.controller._photoshop_progress_dialog
        self.assertTrue(progress.dialog.isVisible())
        self.assertFalse(progress.dialog.isModal())
        self.assertEqual(progress.progress_bar.maximum(), 0)
        self.assertIsNone(progress.cancel_button)
        self.assertFalse(self.panel.dock_bridge_button.isEnabled())
        self.controller.open()
        self.controller._launch_desktop.assert_not_called()

    def test_script_progress_updates_layer_count(self):
        launch = self.begin_transfer()
        launch.progress_path.write_text(json.dumps({
            "phase": "transferring_layers", "completed": 2, "total": 5,
        }), encoding="utf-8")
        self.poll()
        progress = self.controller._photoshop_progress_dialog
        self.assertEqual(progress.progress_bar.value(), 2)
        self.assertEqual(progress.progress_bar.maximum(), 5)
        self.assertIn("2 / 5", progress.status_label.text())
        self.assertTrue(self.controller._photoshop_job.started)

    def test_missing_start_ack_times_out(self):
        self.begin_transfer()
        progress = self.controller._photoshop_progress_dialog
        self.controller._photoshop_job._started_at -= 121
        self.poll()
        self.assertFalse(progress.dialog.isVisible())
        self.assertIsNone(self.controller._photoshop_job)
        self.assertIn("2 minutes", self.failure_message())

    def test_acknowledged_job_uses_long_timeout(self):
        launch = self.begin_transfer()
        launch.progress_path.write_text('{"phase":"opening_document"}', encoding="utf-8")
        self.controller._photoshop_job._started_at -= 121
        self.poll()
        self.controller._show_message_callback.assert_not_called()
        self.controller._photoshop_job._started_at -= 1800
        self.poll()
        self.assertIn("30 minutes", self.failure_message())

    def test_corrupt_published_receipt_is_not_an_endless_wait(self):
        launch = self.begin_transfer()
        launch.result_path.write_text("not json", encoding="utf-8")
        self.poll()
        self.assertIn("could not be read", self.failure_message())
        self.assertIsNone(self.controller._photoshop_job)

    def test_launch_failure_cleans_progress_and_reports(self):
        self.panel.launch_photoshop.return_value = (False, "Photoshop unavailable")
        self.begin_transfer()
        self.assertIsNone(self.controller._photoshop_progress_dialog)
        self.assertIsNone(self.controller._photoshop_job)
        self.assertIn("Photoshop unavailable", self.failure_message())

    def test_unload_closes_pending_job(self):
        self.begin_transfer()
        progress = self.controller._photoshop_progress_dialog
        self.controller.close()
        self.assertFalse(progress.dialog.isVisible())
        self.assertIsNone(self.controller._photoshop_job)
        self.poll()
        self.controller._show_message_callback.assert_not_called()

    def test_apply_waits_for_photoshop_receipt_instead_of_reporting_launch_as_success(self):
        launch = self.begin_transfer()
        self.poll()
        self.controller._show_message_callback.assert_not_called()
        self.assertFalse(self.panel.dock_bridge_button.isEnabled())
        launch.result_path.write_text(json.dumps({
            "success": True, "inserted": ["A", "B", "C"], "saved": True,
        }), encoding="utf-8")
        self.poll()
        args = self.controller._show_message_callback.call_args.args
        self.assertEqual(args[-2], "Bridge complete")
        self.assertIn("Imported 2", args[-1])
        self.assertIn("inserted 3", args[-1])
        self.assertIsNone(self.controller._photoshop_progress_dialog)

    def apply_request(self, result=None, error=None):
        manifest = Path(self.directory.name) / "desktop_transfer.json"
        manifest.write_text("{}", encoding="utf-8")
        self.controller._snapshot_path = Path(self.directory.name) / "painter_snapshot.json"
        def apply(*_args, **_kwargs):
            self.assertFalse(self.panel.dock_bridge_button.isEnabled())
            if error:
                raise error
            return result
        with (
            patch("sp_plugin.rizum_sp_to_ps.desktop_bridge.desktop_transfer.apply_transfer_manifest", side_effect=apply),
            patch("sp_plugin.rizum_sp_to_ps.desktop_bridge.exporter.write_painter_snapshot") as snapshot,
        ):
            self.controller._apply_desktop_transfer(manifest)
            if self.controller._photoshop_job is not None:
                launch = self.controller._photoshop_job.launch
                launch.result_path.write_text(json.dumps({
                    "success": True, "inserted": ["A"], "saved": True,
                }), encoding="utf-8")
                self.poll()
        return snapshot

    def test_apply_replies_to_the_open_mapper_with_a_fresh_snapshot(self):
        snapshot = self.apply_request(TransferResult(2, 0, (), ("Tint: Normal was kept.",), None))
        reply = self.replies()[-1]
        self.assertEqual(reply["type"], "applied")
        self.assertIn("Imported 2 Photoshop layer(s)", reply["message"])
        self.assertIn("Normal was kept", reply["message"])
        self.assertEqual(reply["snapshot"], str(self.controller._snapshot_path))
        snapshot.assert_called_once()
        self.controller._show_message_callback.assert_not_called()
        self.assertEqual(self.controller._process, self.process)

    def test_apply_waits_for_photoshop_before_replying(self):
        request_path = Path(self.directory.name) / "photoshop_transfer.json"
        request_path.write_text("{}", encoding="utf-8")
        launch = write_photoshop_transfer_launcher(request_path)
        self.apply_request(TransferResult(0, 1, (), (), launch))
        reply = self.replies()[-1]
        self.assertEqual(reply["type"], "applied")
        self.assertIn("inserted 1 Painter layer(s) into Photoshop", reply["message"])
        self.assertIsNone(self.controller._photoshop_job)

    def test_failed_apply_still_refreshes_the_mapper(self):
        self.apply_request(error=RuntimeError("Painter target moved"))
        reply = self.replies()[-1]
        self.assertEqual(reply["type"], "apply_failed")
        self.assertEqual(reply["message"], "Painter target moved")
        self.assertIn("snapshot", reply)
        self.assertFalse(self.panel.dock_bridge_button.isEnabled())

    def test_closing_the_mapper_needs_no_apply(self):
        process = SimpleNamespace()
        self.controller._process = process
        with patch("sp_plugin.rizum_sp_to_ps.desktop_bridge.desktop_transfer.apply_transfer_manifest") as apply:
            self.controller._desktop_finished(process, 0, "")
        apply.assert_not_called()
        self.controller._show_message_callback.assert_not_called()
        self.assertTrue(self.panel.dock_bridge_button.isEnabled())

    def test_partial_transfer_reports_both_hosts_without_reapplying_painter(self):
        launch = self.begin_transfer()
        launch.result_path.write_text(json.dumps({
            "success": False, "inserted": ["A"],
            "errors": [{"name": "B", "message": "Missing target"}],
        }), encoding="utf-8")
        self.poll()
        message = self.failure_message()
        self.assertIn("Already imported 2", message)
        self.assertIn("Inserted 1 of 3", message)
        self.assertIn("Missing target", message)
        self.controller._launch_desktop.assert_not_called()

    def test_success_with_missing_inserts_is_not_reported_as_complete(self):
        launch = self.begin_transfer()
        launch.result_path.write_text('{"success":true,"inserted":[]}', encoding="utf-8")
        self.poll()
        self.failure_message()

    def test_unsaved_photoshop_changes_are_reported_as_unsaved(self):
        launch = self.begin_transfer()
        launch.result_path.write_text(json.dumps({
            "success": True, "inserted": ["A", "B", "C"], "saved": False,
        }), encoding="utf-8")
        self.poll()
        self.assertIn("not been saved", self.controller._show_message_callback.call_args.args[-1])


if __name__ == "__main__":
    unittest.main()
